from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.autonomy import AutonomyCoordinator, AutonomyStopReason
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.execution import ExecutionPolicyError, ExecutionSpec
from parallax_api.code.sandbox_execution import ProtectedCommandRegistry
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.state_machine import RevisionConflict
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


class FakeExecutor:
    def __init__(self, *, fail_stage: WorkflowStage | None = None):
        self.fail_stage = fail_stage
        self.specs: list[ExecutionSpec] = []

    def execute(self, spec: ExecutionSpec) -> dict[str, object]:
        self.specs.append(spec)
        passed = spec.stage is not self.fail_stage
        return {
            "tool_id": spec.tool_id,
            "invocation_digest": "a" * 64,
            "exit_code": 0 if passed else 1,
            "duration_ms": 12,
            "stdout_digest": "b" * 64,
            "stdout_excerpt": "ok" if passed else "",
            "stderr_digest": "c" * 64,
            "stderr_excerpt": "" if passed else "failed",
            "timed_out": False,
            "redacted": False,
            "artifacts": [],
            "protected_success": passed,
            "executor": "recorded-test",
            "network_policy": "deny-all",
            "persistent": False,
        }


def service_for(tmp_path, name="autonomy.db"):
    engine = make_engine(f"sqlite:///{tmp_path / name}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    conversations = ConversationRepository(session)
    runs = EngineeringRunRepository(session)
    work_specs = WorkSpecificationRepository(session)
    service = EngineeringRunService(runs, conversations, work_specs)
    return session, service, conversations, work_specs


def activated_run(service, conversations, work_specs):
    conversation = conversations.create("code", spec_id="P2-V0.13.0")
    draft = WorkSpecificationDraft(
        title="Bounded autonomy test",
        objective="Prove bounded autonomous progression.",
        constraints=["Do not cross protected authority boundaries."],
        acceptance_criteria=[
            "Autonomous progression is protected.",
            "Execution evidence is observable and bounded.",
        ],
        risks=["Autonomy could exceed authority."],
        open_questions=[],
        confidence=0.95,
        program_version="autonomy-test",
    )
    specification = work_specs.create_draft(
        conversation_id=conversation.id,
        draft=draft,
        model_id="test-model",
    )
    specification = work_specs.approve(specification)
    return service.activate_run(
        conversation_id=conversation.id,
        work_specification_id=specification.id,
    )


def implementation_evidence():
    return {
        "artifacts": [{"path": "src/change.py", "sha256": "d" * 64, "size": 1}],
        "base_revision": "base",
        "workspace_digest": "workspace",
    }


def test_autonomy_advances_plan_then_stops_at_implementation_boundary(tmp_path):
    session, service, conversations, work_specs = service_for(tmp_path)
    try:
        run = activated_run(service, conversations, work_specs)
        executor = FakeExecutor()
        result = AutonomyCoordinator(service, executor).run(
            run_id=run.id,
            operation_key="auto-plan",
            expected_revision=run.revision,
        )

        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_REQUIRED
        assert result.run.state == "IMPLEMENT"
        assert [step.stage for step in result.steps] == ["PLAN"]
        assert executor.specs == []
        plan_attempt = [item for item in result.run.attempts if item.stage == "PLAN"][-1]
        assert "AC-01" in plan_attempt.evidence_json
        assert "AC-02" in plan_attempt.evidence_json
    finally:
        session.close()


def test_autonomy_rejects_stale_initial_revision(tmp_path):
    session, service, conversations, work_specs = service_for(tmp_path, "stale.db")
    try:
        run = activated_run(service, conversations, work_specs)
        with pytest.raises(RevisionConflict):
            AutonomyCoordinator(service, FakeExecutor()).run(
                run_id=run.id,
                operation_key="stale",
                expected_revision=run.revision - 1,
            )
    finally:
        session.close()


def test_autonomy_runs_build_test_verify_and_stops_before_review(tmp_path):
    session, service, conversations, work_specs = service_for(tmp_path, "success.db")
    try:
        run = activated_run(service, conversations, work_specs)
        plan = AutonomyCoordinator(service, FakeExecutor()).run(
            run_id=run.id,
            operation_key="plan-only",
            expected_revision=run.revision,
        )
        implemented = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.IMPLEMENT,
            operation_key="human-implementation-evidence",
            expected_revision=plan.run.revision,
            passed=True,
            evidence=implementation_evidence(),
        )

        executor = FakeExecutor()
        result = AutonomyCoordinator(service, executor).run(
            run_id=run.id,
            operation_key="auto-execute",
            expected_revision=implemented.run.revision,
        )

        assert result.stop_reason is AutonomyStopReason.REVIEW_REQUIRED
        assert result.run.state == "REVIEW"
        assert [step.stage for step in result.steps] == ["BUILD", "TEST", "VERIFY"]
        assert [spec.stage for spec in executor.specs] == [
            WorkflowStage.BUILD,
            WorkflowStage.TEST,
            WorkflowStage.VERIFY,
        ]
        assert all(spec.environment_names == () for spec in executor.specs)
    finally:
        session.close()


def test_execution_failure_becomes_durable_failed_run(tmp_path):
    session, service, conversations, work_specs = service_for(tmp_path, "failure.db")
    try:
        run = activated_run(service, conversations, work_specs)
        plan = AutonomyCoordinator(service, FakeExecutor()).run(
            run_id=run.id,
            operation_key="plan-before-failure",
            expected_revision=run.revision,
        )
        implemented = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.IMPLEMENT,
            operation_key="implementation-before-failure",
            expected_revision=plan.run.revision,
            passed=True,
            evidence=implementation_evidence(),
        )

        result = AutonomyCoordinator(
            service,
            FakeExecutor(fail_stage=WorkflowStage.TEST),
        ).run(
            run_id=run.id,
            operation_key="auto-failure",
            expected_revision=implemented.run.revision,
        )

        assert result.stop_reason is AutonomyStopReason.EXECUTION_FAILED
        assert result.run.state == "FAILED"
        assert result.run.resume_stage == "TEST"
        assert result.run.last_failure_code == "AUTONOMOUS_TEST_FAILED"
        assert [step.outcome for step in result.steps] == ["PASSED", "FAILED"]
    finally:
        session.close()


def test_paused_run_does_not_mutate_during_autonomy_request(tmp_path):
    session, service, conversations, work_specs = service_for(tmp_path, "paused.db")
    try:
        run = activated_run(service, conversations, work_specs)
        paused = service.pause(
            run_id=run.id,
            operation_key="pause-before-autonomy",
            expected_revision=run.revision,
        )
        result = AutonomyCoordinator(service, FakeExecutor()).run(
            run_id=run.id,
            operation_key="auto-paused",
            expected_revision=paused.run.revision,
        )
        assert result.stop_reason is AutonomyStopReason.PAUSED
        assert result.run.revision == paused.run.revision
        assert result.steps == ()
    finally:
        session.close()


def test_protected_registry_has_no_caller_supplied_command_surface():
    registry = ProtectedCommandRegistry()
    spec = registry.spec_for(WorkflowStage.BUILD, operation_key="registered-build")
    assert spec.tool_id == "build"
    assert spec.environment_names == ()
    assert "compileall" in spec.args

    with pytest.raises(ExecutionPolicyError):
        registry.spec_for(WorkflowStage.IMPLEMENT, operation_key="not-allowed")
