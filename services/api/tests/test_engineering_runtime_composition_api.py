from __future__ import annotations

from types import SimpleNamespace

from parallax_api.code.autonomy import AutonomyStopReason
from parallax_api.routes import engineering_runs
from parallax_api.schemas import EngineeringOperation


class FakeAllocator:
    pass


class FakeService:
    pass


def test_runtime_lineage_allocator_uses_request_database_binding(monkeypatch):
    engine = object()
    allocator = FakeAllocator()
    session = SimpleNamespace(get_bind=lambda: engine)
    calls = []

    def build(bound_engine):
        calls.append(bound_engine)
        return allocator

    monkeypatch.setattr(engineering_runs, "production_durable_lineage_allocator", build)
    assert engineering_runs.runtime_lineage_allocator(session) is allocator
    assert calls == [engine]


def test_autonomous_route_injects_composed_runtime_when_durable_allocator_exists(monkeypatch):
    service = FakeService()
    allocator = FakeAllocator()
    legacy = object()
    run = SimpleNamespace(id="run-1")
    captured = {}

    class Composition:
        def __init__(self, svc, bound_allocator, legacy_executor):
            captured["init"] = (svc, bound_allocator, legacy_executor)

        def run(self, **kwargs):
            captured["run"] = kwargs
            return SimpleNamespace(
                run=run,
                stop_reason=AutonomyStopReason.REVIEW_REQUIRED,
                steps=(),
            )

    monkeypatch.setattr(engineering_runs, "VercelSandboxExecutor", lambda: legacy)
    monkeypatch.setattr(engineering_runs, "EngineeringRuntimeComposition", Composition)
    monkeypatch.setattr(engineering_runs, "present", lambda value, svc: {"id": value.id})

    response = engineering_runs.autonomous(
        "run-1",
        EngineeringOperation(operation_key="route:composition", expected_revision=7),
        service,
        allocator,
    )

    assert captured["init"] == (service, allocator, legacy)
    assert captured["run"] == {
        "run_id": "run-1",
        "operation_key": "route:composition",
        "expected_revision": 7,
    }
    assert response["run"] == {"id": "run-1"}
    assert response["stop_reason"] == AutonomyStopReason.REVIEW_REQUIRED.value


def test_autonomous_route_preserves_fail_closed_legacy_composition_when_68_is_absent(monkeypatch):
    service = FakeService()
    legacy = object()
    run = SimpleNamespace(id="run-2")
    captured = {}

    class LegacyCoordinator:
        def __init__(self, svc, executor):
            captured["init"] = (svc, executor)

        def run(self, **kwargs):
            captured["run"] = kwargs
            return SimpleNamespace(
                run=run,
                stop_reason=AutonomyStopReason.IMPLEMENTATION_REQUIRED,
                steps=(),
            )

    class ForbiddenComposition:
        def __init__(self, *args, **kwargs):
            raise AssertionError("durable runtime composition must not be constructed without #68 allocator")

    monkeypatch.setattr(engineering_runs, "VercelSandboxExecutor", lambda: legacy)
    monkeypatch.setattr(engineering_runs, "AutonomyCoordinator", LegacyCoordinator)
    monkeypatch.setattr(engineering_runs, "EngineeringRuntimeComposition", ForbiddenComposition)
    monkeypatch.setattr(engineering_runs, "present", lambda value, svc: {"id": value.id})

    response = engineering_runs.autonomous(
        "run-2",
        EngineeringOperation(operation_key="route:pre68", expected_revision=3),
        service,
        None,
    )

    assert captured["init"] == (service, legacy)
    assert captured["run"]["run_id"] == "run-2"
    assert response["stop_reason"] == AutonomyStopReason.IMPLEMENTATION_REQUIRED.value
