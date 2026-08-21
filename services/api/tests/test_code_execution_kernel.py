from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.domain import WorkflowStage
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.state_machine import RevisionConflict, RunTransitionError, SpecBindingError
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


def session_factory(tmp_path, name="code.db"):
    engine = make_engine(f"sqlite:///{tmp_path / name}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def service_for(session):
    conversations = ConversationRepository(session)
    runs = EngineeringRunRepository(session)
    work_specs = WorkSpecificationRepository(session)
    return EngineeringRunService(runs, conversations, work_specs), conversations, runs, work_specs


def work_spec_draft(label="Approved implementation contract"):
    return WorkSpecificationDraft(
        title=label,
        objective="Implement the approved outcome while preserving protected execution evidence.",
        constraints=["Preserve the conversation and protected trust boundaries."],
        acceptance_criteria=[
            "The requested behavior is implemented and observable.",
            "Protected verification proves the requested behavior without unsupported release claims.",
        ],
        risks=["Execution evidence could drift from the approved objective."],
        open_questions=[],
        confidence=0.95,
        program_version="work-spec-code-test",
    )


def code_context(conversations, work_specs, spec_id="P2-V0.8.0", *, approve=True, label="Approved implementation contract"):
    conversation = conversations.create("code", spec_id=spec_id)
    specification = work_specs.create_draft(
        conversation_id=conversation.id,
        draft=work_spec_draft(label),
        model_id="test-model",
    )
    if approve:
        specification = work_specs.approve(specification)
    return conversation, specification


def passing_evidence(stage):
    if stage is WorkflowStage.PLAN:
        return {
            "acceptance_ids_covered": ["AC-01", "AC-02"],
            "work_items": ["implement"],
            "validation_checks": ["test"],
        }
    if stage is WorkflowStage.IMPLEMENT:
        return {
            "artifacts": [{"path": "src/app.py", "sha256": "a" * 64, "size": 1}],
            "base_revision": "base",
            "workspace_digest": "work",
        }
    if stage is WorkflowStage.BUILD:
        return {
            "protected_success": True,
            "exit_code": 0,
            "timed_out": False,
            "acceptance_ids_targeted": ["AC-01", "AC-02"],
        }
    if stage in {WorkflowStage.TEST, WorkflowStage.VERIFY}:
        return {
            "protected_success": True,
            "exit_code": 0,
            "timed_out": False,
            "acceptance_ids_verified": ["AC-01", "AC-02"],
        }
    if stage is WorkflowStage.REVIEW:
        return {
            "acceptance_ids_verified": ["AC-01", "AC-02"],
            "recommendation": "PASS",
            "workspace_digest": "work",
        }
    return {"protected_pass": True, "stage": stage.value}


def test_engineering_run_persists_with_exact_approved_work_spec_binding(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        service, conversations, _, work_specs = service_for(session)
        conversation, specification = code_context(conversations, work_specs)
        run = service.create_run(
            conversation_id=conversation.id,
            spec_id=conversation.spec_id,
            work_specification_id=specification.id,
            workspace_ref="workspace:test",
        )
        run_id = run.id
        conversation_id = conversation.id
        specification_id = specification.id
        assert run.state == "SPECIFY"
        assert run.revision == 0
        assert run.spec_id == "P2-V0.8.0"
        assert run.work_specification_id == specification.id
        assert run.work_specification_revision == 1
        assert len(run.work_specification_digest or "") == 64

    with Session() as session:
        service, _, _, _ = service_for(session)
        restored = service.get(run_id)
        assert restored.conversation_id == conversation_id
        assert restored.work_specification_id == specification_id
        assert restored.work_specification_revision == 1
        assert restored.workspace_ref == "workspace:test"
        assert [item["id"] for item in service.acceptance_map_for_run(restored)] == ["AC-01", "AC-02"]


def test_activation_requires_approval_and_is_idempotent(tmp_path):
    Session = session_factory(tmp_path, "activation.db")
    with Session() as session:
        service, conversations, runs, work_specs = service_for(session)
        conversation, draft = code_context(conversations, work_specs, approve=False)

        with pytest.raises(SpecBindingError):
            service.activate_run(conversation_id=conversation.id, work_specification_id=draft.id)

        approved = work_specs.approve(draft)
        first = service.activate_run(conversation_id=conversation.id, work_specification_id=approved.id)
        assert first.state == "PLAN"
        assert first.revision == 1
        assert [item.stage for item in first.attempts] == ["SPECIFY"]

        replay = service.activate_run(conversation_id=conversation.id, work_specification_id=approved.id)
        assert replay.id == first.id
        assert replay.revision == 1
        assert len(runs.get(first.id).attempts) == 1


def test_new_approved_revision_creates_new_execution_target_without_retargeting_old_run(tmp_path):
    Session = session_factory(tmp_path, "revisions.db")
    with Session() as session:
        service, conversations, _, work_specs = service_for(session)
        conversation, first_spec = code_context(conversations, work_specs)
        first_run = service.activate_run(conversation_id=conversation.id, work_specification_id=first_spec.id)
        first_digest = first_run.work_specification_digest

        second_draft = work_specs.create_draft(
            conversation_id=conversation.id,
            draft=work_spec_draft("Second approved implementation contract"),
            model_id="test-model",
        )
        assert work_specs.get(first_spec.id).status == "APPROVED"
        second_spec = work_specs.approve(second_draft)
        assert work_specs.get(first_spec.id).status == "SUPERSEDED"

        restored_first = service.get(first_run.id)
        assert restored_first.work_specification_id == first_spec.id
        assert restored_first.work_specification_digest == first_digest

        second_run = service.activate_run(conversation_id=conversation.id, work_specification_id=second_spec.id)
        assert second_run.id != first_run.id
        assert second_run.work_specification_id == second_spec.id
        assert second_run.work_specification_revision == 2
        assert service.get(first_run.id).work_specification_id == first_spec.id


def test_stage_order_idempotency_revision_and_server_owned_acceptance_are_protected(tmp_path):
    Session = session_factory(tmp_path, "order.db")
    with Session() as session:
        service, conversations, _, work_specs = service_for(session)
        conversation, specification = code_context(conversations, work_specs)
        run = service.activate_run(conversation_id=conversation.id, work_specification_id=specification.id)
        assert run.state == "PLAN"
        assert run.revision == 1

        with pytest.raises(RevisionConflict):
            service.complete_stage(
                run_id=run.id,
                stage=WorkflowStage.PLAN,
                operation_key="plan-stale",
                expected_revision=0,
                passed=True,
                evidence=passing_evidence(WorkflowStage.PLAN),
            )

        with pytest.raises(ValueError):
            service.complete_stage(
                run_id=run.id,
                stage=WorkflowStage.PLAN,
                operation_key="plan-incomplete-acceptance",
                expected_revision=1,
                passed=True,
                evidence={
                    "required_acceptance_ids": ["AC-01"],
                    "acceptance_ids_covered": ["AC-01"],
                    "work_items": ["implement"],
                    "validation_checks": ["test"],
                },
            )

        plan = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.PLAN,
            operation_key="plan-1",
            expected_revision=1,
            passed=True,
            evidence=passing_evidence(WorkflowStage.PLAN),
        )
        assert plan.run.state == "IMPLEMENT"
        assert plan.run.revision == 2


def test_failed_stage_is_durable_and_resume_retries_without_overwriting_evidence(tmp_path):
    Session = session_factory(tmp_path, "retry.db")
    with Session() as session:
        service, conversations, runs, work_specs = service_for(session)
        conversation, specification = code_context(conversations, work_specs)
        run = service.activate_run(conversation_id=conversation.id, work_specification_id=specification.id)

        revision = run.revision
        for stage in (WorkflowStage.PLAN, WorkflowStage.IMPLEMENT):
            result = service.complete_stage(
                run_id=run.id,
                stage=stage,
                operation_key=f"{stage.value.lower()}-pass",
                expected_revision=revision,
                passed=True,
                evidence=passing_evidence(stage),
            )
            revision = result.run.revision

        failed = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.BUILD,
            operation_key="build-fail",
            expected_revision=revision,
            passed=False,
            failure_code="BUILD_EXIT_1",
            evidence={"exit_code": 1, "stdout_digest": "sha256:failed"},
        )
        assert failed.run.state == "FAILED"
        assert failed.run.resume_stage == "BUILD"
        assert failed.run.last_failure_code == "BUILD_EXIT_1"

        resumed = service.resume(
            run_id=run.id,
            operation_key="resume-build",
            expected_revision=failed.run.revision,
        )
        passed = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.BUILD,
            operation_key="build-pass",
            expected_revision=resumed.run.revision,
            passed=True,
            evidence=passing_evidence(WorkflowStage.BUILD),
        )
        assert passed.run.state == "TEST"
        build_attempts = [attempt for attempt in runs.get(run.id).attempts if attempt.stage == "BUILD"]
        assert [attempt.status for attempt in build_attempts] == ["FAILED", "RESUMED", "PASSED"]
        assert build_attempts[0].evidence_json != build_attempts[-1].evidence_json


def test_complete_requires_acceptance_coverage_through_build_test_verify_and_review(tmp_path):
    Session = session_factory(tmp_path, "complete.db")
    with Session() as session:
        service, conversations, _, work_specs = service_for(session)
        conversation, specification = code_context(conversations, work_specs)
        run = service.activate_run(conversation_id=conversation.id, work_specification_id=specification.id)

        revision = run.revision
        for stage in (
            WorkflowStage.PLAN,
            WorkflowStage.IMPLEMENT,
            WorkflowStage.BUILD,
            WorkflowStage.TEST,
            WorkflowStage.VERIFY,
            WorkflowStage.REVIEW,
        ):
            result = service.complete_stage(
                run_id=run.id,
                stage=stage,
                operation_key=f"{stage.value.lower()}-pass",
                expected_revision=revision,
                passed=True,
                evidence=passing_evidence(stage),
            )
            revision = result.run.revision

        assert result.run.state == "COMPLETE"
        assert result.run.completed_at is not None
        with pytest.raises(RunTransitionError):
            service.cancel(
                run_id=run.id,
                operation_key="cancel-complete",
                expected_revision=revision,
            )
