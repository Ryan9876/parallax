from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.domain import WorkflowStage
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.state_machine import RevisionConflict, RunTransitionError, SpecBindingError
from parallax_api.db import Base, make_engine
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository


def session_factory(tmp_path, name="code.db"):
    engine = make_engine(f"sqlite:///{tmp_path / name}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def service_for(session):
    conversations = ConversationRepository(session)
    runs = EngineeringRunRepository(session)
    return EngineeringRunService(runs, conversations), conversations, runs


def code_conversation(conversations, spec_id="P2-V0.4.0"):
    return conversations.create("code", spec_id=spec_id)


def test_engineering_run_persists_with_immutable_conversation_spec_binding(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        service, conversations, _ = service_for(session)
        conversation = code_conversation(conversations)
        run = service.create_run(
            conversation_id=conversation.id,
            spec_id="P2-V0.4.0",
            workspace_ref="workspace:test",
        )
        run_id = run.id
        conversation_id = conversation.id
        assert run.state == "SPECIFY"
        assert run.revision == 0
        assert run.spec_id == "P2-V0.4.0"

    with Session() as session:
        service, conversations, _ = service_for(session)
        restored = service.get(run_id)
        assert restored.conversation_id == conversation_id
        assert restored.spec_id == "P2-V0.4.0"
        assert restored.workspace_ref == "workspace:test"

        with pytest.raises(SpecBindingError):
            service.create_run(
                conversation_id=conversation_id,
                spec_id="P2-V9.9.9",
            )


def test_stage_order_idempotency_and_revision_conflicts_are_protected(tmp_path):
    Session = session_factory(tmp_path, "order.db")
    with Session() as session:
        service, conversations, runs = service_for(session)
        conversation = code_conversation(conversations)
        run = service.create_run(conversation_id=conversation.id, spec_id=conversation.spec_id)

        with pytest.raises(RunTransitionError):
            service.complete_stage(
                run_id=run.id,
                stage=WorkflowStage.PLAN,
                operation_key="plan-too-early",
                expected_revision=0,
                passed=True,
            )

        first = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.SPECIFY,
            operation_key="specify-1",
            expected_revision=0,
            passed=True,
            evidence={"spec_id": "P2-V0.4.0", "approved": True},
        )
        assert first.run.state == "PLAN"
        assert first.run.revision == 1
        assert first.replayed is False

        replay = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.SPECIFY,
            operation_key="specify-1",
            expected_revision=0,
            passed=True,
        )
        assert replay.replayed is True
        assert replay.run.revision == 1
        assert len(runs.get(run.id).attempts) == 1

        with pytest.raises(RevisionConflict):
            service.complete_stage(
                run_id=run.id,
                stage=WorkflowStage.PLAN,
                operation_key="plan-stale",
                expected_revision=0,
                passed=True,
            )

        plan = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.PLAN,
            operation_key="plan-1",
            expected_revision=1,
            passed=True,
            evidence={"acceptance_ids": ["AC-01", "AC-02"]},
        )
        assert plan.run.state == "IMPLEMENT"
        assert plan.run.revision == 2


def test_failed_stage_is_durable_and_resume_retries_without_overwriting_evidence(tmp_path):
    Session = session_factory(tmp_path, "retry.db")
    with Session() as session:
        service, conversations, runs = service_for(session)
        conversation = code_conversation(conversations)
        run = service.create_run(conversation_id=conversation.id, spec_id=conversation.spec_id)

        revision = 0
        for stage in (WorkflowStage.SPECIFY, WorkflowStage.PLAN, WorkflowStage.IMPLEMENT):
            result = service.complete_stage(
                run_id=run.id,
                stage=stage,
                operation_key=f"{stage.value.lower()}-pass",
                expected_revision=revision,
                passed=True,
                evidence={"stage": stage.value},
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

        with pytest.raises(RunTransitionError):
            service.complete_stage(
                run_id=run.id,
                stage=WorkflowStage.TEST,
                operation_key="test-illegal",
                expected_revision=failed.run.revision,
                passed=True,
            )

        resumed = service.resume(
            run_id=run.id,
            operation_key="resume-build",
            expected_revision=failed.run.revision,
        )
        assert resumed.run.state == "BUILD"
        assert resumed.run.resume_stage is None

        passed = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.BUILD,
            operation_key="build-pass",
            expected_revision=resumed.run.revision,
            passed=True,
            evidence={"exit_code": 0, "stdout_digest": "sha256:passed"},
        )
        assert passed.run.state == "TEST"
        build_attempts = [attempt for attempt in runs.get(run.id).attempts if attempt.stage == "BUILD"]
        assert [attempt.status for attempt in build_attempts] == ["FAILED", "RESUMED", "PASSED"]
        assert build_attempts[0].evidence_json != build_attempts[-1].evidence_json


def test_complete_requires_every_stage_and_terminal_states_block_mutation(tmp_path):
    Session = session_factory(tmp_path, "complete.db")
    with Session() as session:
        service, conversations, _ = service_for(session)
        conversation = code_conversation(conversations)
        run = service.create_run(conversation_id=conversation.id, spec_id=conversation.spec_id)

        revision = 0
        for stage in (
            WorkflowStage.SPECIFY,
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
                evidence={"protected_pass": True, "stage": stage.value},
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
