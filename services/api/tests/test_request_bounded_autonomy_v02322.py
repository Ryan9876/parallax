from __future__ import annotations

from types import SimpleNamespace

import pytest

from parallax_api.code.autonomy import AutonomyCoordinator, AutonomyStopReason
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.execution import ExecutionSpec
import parallax_api.code.agentic_candidate_recovery as candidate_recovery
import parallax_api.routes.engineering_runs as engineering_routes
from parallax_api.schemas import EngineeringOperation


class _OneStepService:
    def __init__(self):
        self.run = SimpleNamespace(
            id="run-1",
            state=WorkflowStage.VERIFY.value,
            revision=4,
            attempts=[],
        )
        self.completed: list[WorkflowStage] = []

    def get(self, run_id: str):
        assert run_id == self.run.id
        return self.run

    def acceptance_map_for_run(self, _run):
        return [{"id": "AC-01"}]

    def complete_stage(self, *, stage: WorkflowStage, **_kwargs):
        self.completed.append(stage)
        self.run.state = WorkflowStage.REVIEW.value
        self.run.revision += 1
        return SimpleNamespace(run=self.run, attempt_id="attempt-verify", replayed=False)


class _Executor:
    def probe(self, *, operation_key: str):
        raise AssertionError(operation_key)

    def execute(self, spec: ExecutionSpec):
        return {"tool_id": spec.tool_id, "protected_success": True}


class _Registry:
    def spec_for(self, stage: WorkflowStage, *, operation_key: str):
        return ExecutionSpec(
            tool_id="verify",
            args=(),
            working_directory=".",
            timeout_seconds=1,
            environment_names=(),
            stage=stage,
            operation_key=operation_key,
        )


def test_one_step_verify_returns_review_boundary_instead_of_max_steps():
    service = _OneStepService()
    result = AutonomyCoordinator(
        service,
        _Executor(),
        registry=_Registry(),
        max_steps=1,
    ).run(
        run_id="run-1",
        operation_key="p2322-one-step",
        expected_revision=4,
    )

    assert service.completed == [WorkflowStage.VERIFY]
    assert result.run.state == WorkflowStage.REVIEW.value
    assert result.stop_reason is AutonomyStopReason.REVIEW_REQUIRED
    assert [step.stage for step in result.steps] == [WorkflowStage.VERIFY.value]


class _RouteService:
    owner_subject = "owner-a"

    def __init__(self):
        self.runs = SimpleNamespace(session=object())
        self.run = SimpleNamespace(id="run-route", project_id="project-route")

    def get(self, run_id: str):
        assert run_id == self.run.id
        return self.run


class _RouteRuntime:
    def __init__(self, captured: dict[str, object]):
        self.captured = captured

    def run(self, *, run_id: str, operation_key: str, expected_revision: int):
        self.captured["run"] = (run_id, operation_key, expected_revision)
        return SimpleNamespace(
            run=SimpleNamespace(id=run_id),
            stop_reason=AutonomyStopReason.MAX_STEPS_REACHED,
            steps=(),
        )


def test_production_agentic_route_pins_one_lifecycle_stage(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}
    service = _RouteService()
    runtime = _RouteRuntime(captured)

    monkeypatch.setenv("PARALLAX_AGENTIC_RUNTIME_ENABLED", "1")
    monkeypatch.setattr(engineering_routes, "production_source_delivery", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(engineering_routes, "present", lambda run, _svc: {"id": run.id})

    def build_runtime(*_args, **kwargs):
        captured["max_steps"] = kwargs.get("max_steps")
        return runtime

    monkeypatch.setattr(candidate_recovery, "build_resilient_live_agentic_runtime_composition", build_runtime)

    response = engineering_routes.autonomous(
        "run-route",
        EngineeringOperation(operation_key="p2322-route", expected_revision=9),
        svc=service,
        allocator=object(),
        oidc_token="oidc",
    )

    assert captured["max_steps"] == 1
    assert captured["run"] == ("run-route", "p2322-route", 9)
    assert response["stop_reason"] == AutonomyStopReason.MAX_STEPS_REACHED.value


def test_production_nonagentic_route_pins_one_lifecycle_stage(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}
    service = _RouteService()
    runtime = _RouteRuntime(captured)

    monkeypatch.delenv("PARALLAX_AGENTIC_RUNTIME_ENABLED", raising=False)
    monkeypatch.setattr(engineering_routes, "production_source_delivery", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(engineering_routes, "present", lambda run, _svc: {"id": run.id})

    class RuntimeFactory:
        def __init__(self, *_args, **kwargs):
            captured["max_steps"] = kwargs.get("max_steps")

        def run(self, **kwargs):
            return runtime.run(**kwargs)

    monkeypatch.setattr(engineering_routes, "EngineeringRuntimeComposition", RuntimeFactory)

    response = engineering_routes.autonomous(
        "run-route",
        EngineeringOperation(operation_key="p2322-route-nonagentic", expected_revision=11),
        svc=service,
        allocator=object(),
        oidc_token="oidc",
    )

    assert captured["max_steps"] == 1
    assert captured["run"] == ("run-route", "p2322-route-nonagentic", 11)
    assert response["stop_reason"] == AutonomyStopReason.MAX_STEPS_REACHED.value
