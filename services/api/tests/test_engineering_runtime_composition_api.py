from __future__ import annotations

from types import SimpleNamespace

from parallax_api.code.autonomy import AutonomyStopReason
from parallax_api.routes import engineering_runs
from parallax_api.schemas import EngineeringOperation


class FakeAllocator:
    pass


class FakeService:
    def __init__(self, run=None):
        self._run = run
        self.owner_subject = "owner:runtime-composition-test"
        self.runs = SimpleNamespace(session=object())

    def get(self, run_id):
        if self._run is None or self._run.id != run_id:
            raise AssertionError("unexpected run lookup")
        return self._run


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
    run = SimpleNamespace(id="run-1", project_id="11111111-1111-4111-8111-111111111111")
    service = FakeService(run)
    allocator = FakeAllocator()
    legacy = object()
    source_delivery = object()
    captured = {}

    class Composition:
        def __init__(self, svc, bound_allocator, legacy_executor, *, source_delivery=None, max_steps=8):
            captured["init"] = (svc, bound_allocator, legacy_executor, source_delivery, max_steps)

        def run(self, **kwargs):
            captured["run"] = kwargs
            return SimpleNamespace(
                run=run,
                stop_reason=AutonomyStopReason.REVIEW_REQUIRED,
                steps=(),
            )

    def build_delivery(session, *, owner_subject, allocator, project_id):
        captured["delivery"] = (session, owner_subject, allocator, project_id)
        return source_delivery

    monkeypatch.setattr(engineering_runs, "VercelSandboxExecutor", lambda: legacy)
    monkeypatch.setattr(engineering_runs, "EngineeringRuntimeComposition", Composition)
    monkeypatch.setattr(engineering_runs, "production_source_delivery", build_delivery)
    monkeypatch.setattr(engineering_runs, "present", lambda value, svc: {"id": value.id})

    response = engineering_runs.autonomous(
        "run-1",
        EngineeringOperation(operation_key="route:composition", expected_revision=7),
        service,
        allocator,
    )

    assert captured["delivery"] == (
        service.runs.session,
        service.owner_subject,
        allocator,
        run.project_id,
    )
    assert captured["init"] == (
        service,
        allocator,
        legacy,
        source_delivery,
        engineering_runs._AUTONOMY_REQUEST_MAX_STEPS,
    )
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
        def __init__(self, svc, executor, *, max_steps=8):
            captured["init"] = (svc, executor, max_steps)

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

    assert captured["init"] == (service, legacy, engineering_runs._AUTONOMY_REQUEST_MAX_STEPS)
    assert captured["run"]["run_id"] == "run-2"
    assert response["stop_reason"] == AutonomyStopReason.IMPLEMENTATION_REQUIRED.value
