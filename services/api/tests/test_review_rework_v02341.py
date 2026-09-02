from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from parallax_api.code.domain import AttemptStatus, WorkflowStage
from parallax_api.code.protected import ProtectedEvidenceError
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.state_machine import RunTransitionError
from parallax_api.code.worker_recovery import RecoveryAction, WorkerCheckpoint, WorkerLifecycleState
from parallax_api.code.worker_service import WorkerRecoveryService
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.worker_executions import WorkerExecutionRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.schemas import EngineeringReviewRework
from parallax_api.services.conversations import ConversationService

OWNER = "owner-review-rework"
OLD_LINEAGE = "src:" + "1" * 64
REVIEWED_LINEAGE = "src:" + "2" * 64
WORKSPACE_DIGEST = "3" * 64


def _session(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'review-rework.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _fixture(tmp_path):
    Session = _session(tmp_path)
    session = Session()
    projects = ProjectRepository(session)
    project = projects.create(
        owner_subject=OWNER,
        slug="review-rework",
        name="Review Rework",
        description=None,
        repository_ref=None,
    )
    conversations = ConversationRepository(session)
    conversation = ConversationService(
        conversations,
        projects,
        owner_subject=OWNER,
        require_project_binding=True,
        active_spec_id="P2-V0.23.41",
    ).create("code", project.id)
    work_specs = WorkSpecificationRepository(session)
    draft = work_specs.create_draft(
        conversation_id=conversation.id,
        draft=WorkSpecificationDraft(
            title="Review rework contract",
            objective="Correct an accepted candidate without widening scope.",
            constraints=["Preserve human REVIEW."],
            acceptance_criteria=["Import fails safely.", "Automated tests cover core behavior."],
            risks=[],
            open_questions=[],
            confidence=0.99,
            program_version="review-rework-test",
        ),
        model_id="test-model",
    )
    specification = work_specs.approve(draft)
    service = EngineeringRunService(
        EngineeringRunRepository(session),
        conversations,
        work_specs,
        projects,
        owner_subject=OWNER,
        require_project_binding=True,
    )
    run = service.activate_run(
        conversation_id=conversation.id,
        work_specification_id=specification.id,
    )
    run = service.runs.record(
        run,
        stage=WorkflowStage.IMPLEMENT.value,
        operation_key="fixture-implement",
        status=AttemptStatus.PASSED.value,
        next_state=WorkflowStage.REVIEW.value,
        evidence={
            "project_ref": project.id,
            "run_id": run.id,
            "base_source_lineage_ref": OLD_LINEAGE,
            "source_lineage_ref": REVIEWED_LINEAGE,
            "workspace_digest": WORKSPACE_DIGEST,
            "artifacts": [{"path": "index.html", "sha256": "4" * 64, "size": 1}],
        },
    ).run
    return session, service, run


def _ready_worker(session, run):
    workers = WorkerRecoveryService(WorkerExecutionRepository(session), EngineeringRunRepository(session))
    lease = workers.acquire(run_id=run.id)
    ready = workers.checkpoint(
        lease,
        WorkerCheckpoint(
            project_id=run.project_id,
            run_id=run.id,
            work_specification_id=run.work_specification_id,
            work_specification_revision=run.work_specification_revision,
            work_specification_digest=run.work_specification_digest,
            plan_ref="agentic-plan:test",
            current_step="CANDIDATE_SELECTED",
            source_lineage_ref=OLD_LINEAGE,
            last_known_good_lineage_ref=OLD_LINEAGE,
            evidence_refs=("candidate:" + "5" * 64,),
        ),
        authoritative_source_lineage_ref=OLD_LINEAGE,
        state=WorkerLifecycleState.READY_FOR_INTEGRATION,
    )
    assert ready.execution.state == WorkerLifecycleState.READY_FOR_INTEGRATION.value
    return workers


def test_review_rework_schema_is_bounded_and_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        EngineeringReviewRework.model_validate({
            "operation_key": "rework",
            "expected_revision": 1,
            "acceptance_ids": ["AC-01"],
            "finding": "fix it",
            "source_lineage_ref": REVIEWED_LINEAGE,
        })
    with pytest.raises(ValidationError):
        EngineeringReviewRework.model_validate({
            "operation_key": "rework",
            "expected_revision": 1,
            "acceptance_ids": [],
            "finding": "fix it",
        })


def test_review_rework_is_review_only_acceptance_linked_and_idempotent(tmp_path):
    session, service, run = _fixture(tmp_path)
    try:
        ids = [item["id"] for item in service.acceptance_map_for_run(run)]
        with pytest.raises(RunTransitionError, match="duplicates"):
            service.review_rework(
                run_id=run.id,
                operation_key="duplicate",
                expected_revision=run.revision,
                acceptance_ids=[ids[0], ids[0]],
                finding="Fix import safety.",
            )
        with pytest.raises(RunTransitionError, match="outside"):
            service.review_rework(
                run_id=run.id,
                operation_key="unknown",
                expected_revision=run.revision,
                acceptance_ids=["AC-99"],
                finding="Fix import safety.",
            )
        with pytest.raises(RunTransitionError, match="1 to 1200"):
            service.review_rework(
                run_id=run.id,
                operation_key="blank",
                expected_revision=run.revision,
                acceptance_ids=[ids[0]],
                finding="   ",
            )

        original_revision = run.revision
        result = service.review_rework(
            run_id=run.id,
            operation_key="human-review-rework",
            expected_revision=original_revision,
            acceptance_ids=[ids[1], ids[0]],
            finding="  Fix invalid import handling and add the required automated coverage.  ",
        )
        assert result.run.state == WorkflowStage.PLAN.value
        assert result.run.revision == original_revision + 1
        context = service.review_rework_context_for_run(result.run)
        assert context is not None
        assert context.acceptance_ids == tuple(sorted(ids))
        assert context.finding == "Fix invalid import handling and add the required automated coverage."
        assert context.base_source_lineage_ref == REVIEWED_LINEAGE
        assert context.workspace_digest == WORKSPACE_DIGEST
        assert len(context.digest) == 64

        replay = service.review_rework(
            run_id=run.id,
            operation_key="human-review-rework",
            expected_revision=original_revision,
            acceptance_ids=[ids[0]],
            finding="ignored on operation replay",
        )
        assert replay.replayed is True
        assert replay.attempt_id == result.attempt_id
        assert replay.run.revision == result.run.revision

        with pytest.raises(RunTransitionError, match="REVIEW rework requires"):
            service.review_rework(
                run_id=run.id,
                operation_key="second-operation",
                expected_revision=result.run.revision,
                acceptance_ids=[ids[0]],
                finding="Cannot start a second rework from PLAN.",
            )
    finally:
        session.close()


def test_rework_plan_requires_exact_current_context_and_worker_reset_invalidates_candidate(tmp_path):
    session, service, run = _fixture(tmp_path)
    try:
        workers = _ready_worker(session, run)
        ids = [item["id"] for item in service.acceptance_map_for_run(run)]
        transition = service.review_rework(
            run_id=run.id,
            operation_key="human-review-rework",
            expected_revision=run.revision,
            acceptance_ids=ids,
            finding="Fix the two REVIEW findings.",
        )
        context = service.review_rework_context_for_run(transition.run)
        assert context is not None

        prepared = workers.prepare_review_rework(
            run_id=run.id,
            authoritative_source_lineage_ref=context.base_source_lineage_ref,
        )
        assert prepared is not None
        assert prepared.state == WorkerLifecycleState.RECOVERING.value
        assert prepared.checkpoint_json == "{}"
        assert prepared.current_step is None
        assert prepared.source_lineage_ref == REVIEWED_LINEAGE
        assert prepared.last_known_good_lineage_ref == REVIEWED_LINEAGE
        assert prepared.next_recovery_action == RecoveryAction.REASSIGN.value
        assert prepared.lease_owner_id is None and prepared.lease_expires_at is None
        prepared_revision = prepared.revision
        replayed_prepare = workers.prepare_review_rework(
            run_id=run.id,
            authoritative_source_lineage_ref=context.base_source_lineage_ref,
        )
        assert replayed_prepare is not None and replayed_prepare.revision == prepared_revision

        basic_plan = {
            "acceptance_ids_covered": sorted(ids),
            "work_items": [{"acceptance_id": value, "action": "correct reviewed behavior"} for value in sorted(ids)],
            "validation_checks": [{"acceptance_id": value, "check": "revalidate reviewed behavior"} for value in sorted(ids)],
            "planner": "test",
            "executor_preflight": "passed",
        }
        with pytest.raises(ProtectedEvidenceError, match="context digest"):
            service.complete_stage(
                run_id=run.id,
                stage=WorkflowStage.PLAN,
                operation_key="stale-rework-plan",
                expected_revision=transition.run.revision,
                passed=True,
                evidence=basic_plan,
            )

        good_plan = {
            **basic_plan,
            "review_rework_context_digest": context.digest,
            "review_rework_acceptance_ids": list(context.acceptance_ids),
        }
        accepted = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.PLAN,
            operation_key="fresh-rework-plan",
            expected_revision=transition.run.revision,
            passed=True,
            evidence=good_plan,
        )
        assert accepted.run.state == WorkflowStage.IMPLEMENT.value
    finally:
        session.close()
