from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.domain import WorkflowStage
from parallax_api.code.run_events import (
    RunEventOutcome,
    RunEventPersistenceError,
    RunEventType,
)
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.worker_recovery import WorkerStallEvidence
from parallax_api.code.worker_service import WorkerRecoveryService
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.run_events import PersistentRunEventSink, RunEventRepository
from parallax_api.repositories.worker_executions import WorkerExecutionRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


OWNER = "owner-a"


def session_factory(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'runtime-events.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def setup_bound_contract(session):
    project = ProjectRepository(session).create(
        owner_subject=OWNER,
        slug="runtime-events",
        name="Runtime Events",
        description=None,
        repository_ref="github:acme/runtime-events",
    )
    conversation = ConversationRepository(session).create(
        "code",
        spec_id="P2-V0.17.1",
        project_id=project.id,
    )
    work_specs = WorkSpecificationRepository(session)
    draft = work_specs.create_draft(
        conversation_id=conversation.id,
        draft=WorkSpecificationDraft(
            title="Runtime event projection",
            objective="Project authoritative runtime work into bounded observation events.",
            constraints=["Do not create a second execution authority."],
            acceptance_criteria=[
                "Events remain Project scoped.",
                "Retries do not duplicate authoritative mutation.",
            ],
            risks=["Telemetry must never fabricate success."],
            open_questions=[],
            confidence=0.99,
            program_version="run-event-test",
        ),
        model_id="test-model",
    )
    specification = work_specs.approve(draft)
    return project, conversation, specification


def service_for(session, *, event_sink=None):
    return EngineeringRunService(
        EngineeringRunRepository(session),
        ConversationRepository(session),
        WorkSpecificationRepository(session),
        ProjectRepository(session),
        owner_subject=OWNER,
        require_project_binding=True,
        event_sink=event_sink,
    )


def activate(session, *, event_sink=None):
    project, conversation, specification = setup_bound_contract(session)
    service = service_for(session, event_sink=event_sink)
    run = service.activate_run(
        conversation_id=conversation.id,
        work_specification_id=specification.id,
    )
    return project, specification, service, run


def plan_evidence(service: EngineeringRunService, run):
    ids = sorted(item["id"] for item in service.acceptance_map_for_run(run))
    return ids, {
        "acceptance_ids_covered": ids,
        "work_items": [{"acceptance_id": item, "action": "implement"} for item in ids],
        "validation_checks": [{"acceptance_id": item, "check": "verify"} for item in ids],
    }


def execution_evidence(ids: list[str], *, key: str, lineage: str):
    return {
        "protected_success": True,
        "exit_code": 0,
        "timed_out": False,
        "redacted": True,
        key: ids,
        "source_lineage_ref": lineage,
        "lineage_bound_execution": True,
        "tool_id": "protected-test-command",
        "stdout_excerpt": "bounded attempt evidence is not copied into the run-event table",
    }


def test_stage_lineage_execution_and_review_events_follow_authoritative_results_only(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        repository = RunEventRepository(session)
        sink = PersistentRunEventSink(repository)
        project, _, service, run = activate(session, event_sink=sink)
        ids, plan = plan_evidence(service, run)

        plan_result = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.PLAN,
            operation_key="runtime-events:plan",
            expected_revision=run.revision,
            passed=True,
            evidence=plan,
            program_id="protected-plan-test",
        )
        base_lineage = "src:" + "a" * 64
        accepted_lineage = "src:" + "b" * 64
        implementation = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.IMPLEMENT,
            operation_key="runtime-events:implement",
            expected_revision=plan_result.run.revision,
            passed=True,
            evidence={
                "artifacts": [{"path": "app.py", "sha256": "c" * 64, "size": 10}],
                "base_revision": "d" * 64,
                "workspace_digest": "e" * 64,
                "project_ref": project.id,
                "run_id": run.id,
                "base_source_lineage_ref": base_lineage,
                "source_lineage_ref": accepted_lineage,
            },
            program_id="protected-implementation-test",
        )
        build = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.BUILD,
            operation_key="runtime-events:build",
            expected_revision=implementation.run.revision,
            passed=True,
            evidence=execution_evidence(ids, key="acceptance_ids_targeted", lineage=accepted_lineage),
            tool_id="python",
        )
        test = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.TEST,
            operation_key="runtime-events:test",
            expected_revision=build.run.revision,
            passed=True,
            evidence=execution_evidence(ids, key="acceptance_ids_verified", lineage=accepted_lineage),
            tool_id="python",
        )
        verify = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.VERIFY,
            operation_key="runtime-events:verify",
            expected_revision=test.run.revision,
            passed=True,
            evidence=execution_evidence(ids, key="acceptance_ids_verified", lineage=accepted_lineage),
            tool_id="python",
        )

        assert verify.run.state == WorkflowStage.REVIEW.value
        events = repository.list_for_run(project_id=project.id, run_id=run.id, limit=100)
        assert [event.sequence for event in events] == list(range(1, len(events) + 1))
        assert sum(event.append.event_type is RunEventType.RUN_CREATED for event in events) == 1
        assert sum(event.append.event_type is RunEventType.SOURCE_LINEAGE_ACCEPTED for event in events) == 1
        assert sum(event.append.event_type is RunEventType.REVIEW_REQUIRED for event in events) == 1
        lineage_event = next(
            event for event in events if event.append.event_type is RunEventType.SOURCE_LINEAGE_ACCEPTED
        )
        assert lineage_event.append.source_lineage_ref == accepted_lineage
        assert lineage_event.append.parent_source_lineage_ref == base_lineage
        review = next(event for event in events if event.append.event_type is RunEventType.REVIEW_REQUIRED)
        assert review.append.outcome is RunEventOutcome.HUMAN_REQUIRED

        serialized = json.dumps([event.append.canonical_payload() for event in events], sort_keys=True)
        assert "stdout_excerpt" not in serialized
        assert "bounded attempt evidence is not copied" not in serialized


def test_authoritative_attempt_survives_event_failure_and_retry_does_not_duplicate_mutation(tmp_path):
    class FailingSink:
        def emit(self, event):
            raise RunEventPersistenceError("injected event persistence failure")

    Session = session_factory(tmp_path)
    with Session() as session:
        project, _, setup_service, run = activate(session, event_sink=None)
        ids, plan = plan_evidence(setup_service, run)
        original_revision = run.revision
        failing = service_for(session, event_sink=FailingSink())

        with pytest.raises(RunEventPersistenceError, match="injected"):
            failing.complete_stage(
                run_id=run.id,
                stage=WorkflowStage.PLAN,
                operation_key="event-failure:plan",
                expected_revision=original_revision,
                passed=True,
                evidence=plan,
            )

        authoritative = service_for(session).get(run.id)
        assert authoritative.state == WorkflowStage.IMPLEMENT.value
        plan_attempts = [item for item in authoritative.attempts if item.stage == WorkflowStage.PLAN.value]
        assert len(plan_attempts) == 1
        authoritative_revision = authoritative.revision

        repository = RunEventRepository(session)
        recovered = service_for(session, event_sink=PersistentRunEventSink(repository))
        replay = recovered.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.PLAN,
            operation_key="event-failure:plan",
            expected_revision=original_revision,
            passed=True,
            evidence=plan,
        )
        assert replay.replayed is True
        assert replay.run.revision == authoritative_revision
        assert len([item for item in replay.run.attempts if item.stage == WorkflowStage.PLAN.value]) == 1

        events = repository.list_for_run(project_id=project.id, run_id=run.id)
        assert sum(event.append.event_type is RunEventType.STAGE_RESULT for event in events) == 1
        assert sum(event.append.event_type is RunEventType.OPERATION_REPLAY for event in events) == 1
        again = recovered.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.PLAN,
            operation_key="event-failure:plan",
            expected_revision=original_revision,
            passed=True,
            evidence=plan,
        )
        assert again.replayed is True
        assert len(repository.list_for_run(project_id=project.id, run_id=run.id)) == len(events)


def test_worker_stall_recovery_and_reassignment_are_projected_without_lease_renewal_chatter(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        repository = RunEventRepository(session)
        sink = PersistentRunEventSink(repository)
        project, _, service, run = activate(session, event_sink=sink)
        workers = WorkerRecoveryService(
            WorkerExecutionRepository(session),
            service.runs,
            event_sink=sink,
        )

        lease = workers.acquire(run_id=run.id, lease_seconds=60)
        after_acquire = repository.list_for_run(project_id=project.id, run_id=run.id)
        worker_count = sum(event.append.event_type is RunEventType.WORKER_STATE for event in after_acquire)
        assert worker_count == 1

        workers.renew(lease, lease_seconds=60)
        after_renew = repository.list_for_run(project_id=project.id, run_id=run.id)
        assert sum(event.append.event_type is RunEventType.WORKER_STATE for event in after_renew) == worker_count

        decision = workers.classify_and_stall(
            run_id=run.id,
            evidence=WorkerStallEvidence(process_lost=True),
            blocker_code="PROCESS_LOSS",
        )
        assert decision.human_required is False
        recovering = workers.begin_recovery(run_id=run.id)
        assert recovering.state == "RECOVERING"
        reassigned = workers.reassign(run_id=run.id, lease_seconds=60)
        assert reassigned.generation == 2

        worker_events = [
            event
            for event in repository.list_for_run(project_id=project.id, run_id=run.id, limit=100)
            if event.append.event_type is RunEventType.WORKER_STATE
        ]
        assert [event.append.outcome.value for event in worker_events] == [
            "STARTED",
            "INFO",
            "RECOVERING",
            "RECOVERING",
        ]
        assert all(event.append.worker_execution_id == lease.execution_id for event in worker_events)
