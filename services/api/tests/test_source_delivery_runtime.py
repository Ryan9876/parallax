from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from parallax_api.code.autonomy import AutonomyResult, AutonomyStopReason
from parallax_api.code.runtime_composition import EngineeringRuntimeComposition, RuntimeCompositionError
from parallax_api.code.source_delivery_composition import SourceDeliveryComposition


class FakeService:
    def __init__(self, run):
        self.run = run

    def get(self, run_id):
        assert run_id == self.run.id
        return self.run


class FakeAllocator:
    def resolve(self, identity, lineage_id=None):
        raise AssertionError("workspace resolution is not expected in composition-order test")

    def accept_implementation(self, workspace, *, expected_parent_lineage_id):
        raise AssertionError("implementation acceptance is not expected in composition-order test")

    def reconstruct(self, identity, lineage_id):
        raise AssertionError("reconstruction is not expected in composition-order test")

    def initialize(self, identity, provider):
        raise AssertionError("bootstrap is replaced by a focused fake")

    def current_lineage(self, identity):
        raise AssertionError("bootstrap is replaced by a focused fake")

    def cleanup(self, workspace):
        return None


class FakeExecutor:
    def execute(self, spec):
        return {}

    def probe(self, *, operation_key):
        return {}


class FakeLineageExecutor:
    def execute_on_lineage(self, spec, *, project_ref, run_id, source_lineage_ref, execution_contract):
        return {}


class RecorderBootstrap:
    def __init__(self, events):
        self.events = events

    def ensure(self, run, *, operation_key):
        self.events.append(("bootstrap", run.id, operation_key))
        return SimpleNamespace()


class RecorderDelivery:
    def __init__(self, events, *, fail=False):
        self.events = events
        self.fail = fail

    def deliver(self, run, *, operation_key):
        self.events.append(("delivery", run.id, operation_key))
        if self.fail:
            raise RuntimeError("provider unavailable")
        return SimpleNamespace(lineage_id="src:" + "a" * 64)


class PersistingDelivery(RecorderDelivery):
    def __init__(self, events, *, service, refreshed_run):
        super().__init__(events)
        self.service = service
        self.refreshed_run = refreshed_run

    def deliver(self, run, *, operation_key):
        result = super().deliver(run, operation_key=operation_key)
        self.service.run = self.refreshed_run
        return result


class RecorderCoordinator:
    def __init__(self, events, result_run, stop_reason):
        self.events = events
        self.result_run = result_run
        self.stop_reason = stop_reason

    def run(self, *, run_id, operation_key, expected_revision):
        self.events.append(("coordinator", run_id, operation_key, expected_revision))
        return AutonomyResult(run=self.result_run, stop_reason=self.stop_reason, steps=())


def make_runtime(*, source_delivery=None, stop_reason=AutonomyStopReason.REVIEW_REQUIRED):
    project_id, run_id = str(uuid4()), str(uuid4())
    run = SimpleNamespace(id=run_id, project_id=project_id, state="REVIEW", revision=7, attempts=[])
    events = []
    runtime = EngineeringRuntimeComposition(
        FakeService(run),
        FakeAllocator(),
        FakeExecutor(),
        lineage_executor=FakeLineageExecutor(),
        source_delivery=source_delivery,
    )
    runtime.coordinator = RecorderCoordinator(events, run, stop_reason)
    return runtime, run, events


def test_runtime_bootstraps_before_autonomy_and_delivers_only_at_review():
    events = []
    source_delivery = SourceDeliveryComposition(
        bootstrap=RecorderBootstrap(events),
        delivery=RecorderDelivery(events),
    )
    runtime, run, _ = make_runtime(source_delivery=source_delivery)
    runtime.coordinator.events = events

    result = runtime.run(run_id=run.id, operation_key="operation-1", expected_revision=3)

    assert result.stop_reason is AutonomyStopReason.REVIEW_REQUIRED
    assert [event[0] for event in events] == ["bootstrap", "coordinator", "delivery"]
    assert runtime.last_delivery_result is not None


def test_runtime_returns_canonical_post_delivery_run_snapshot():
    runtime, run, events = make_runtime(source_delivery=None)
    refreshed_run = SimpleNamespace(
        id=run.id,
        project_id=run.project_id,
        state="REVIEW",
        revision=run.revision,
        attempts=[SimpleNamespace(stage="SOURCE_DELIVERY", status="RECORDED")],
    )
    runtime.source_delivery = SourceDeliveryComposition(
        bootstrap=RecorderBootstrap(events),
        delivery=PersistingDelivery(
            events,
            service=runtime.service,
            refreshed_run=refreshed_run,
        ),
    )

    result = runtime.run(run_id=run.id, operation_key="operation-refresh", expected_revision=run.revision)

    assert result.run is refreshed_run
    assert result.run.state == "REVIEW"
    assert result.run.revision == run.revision
    assert [item.stage for item in result.run.attempts] == ["SOURCE_DELIVERY"]
    assert [event[0] for event in events] == ["bootstrap", "coordinator", "delivery"]


def test_runtime_does_not_publish_when_autonomy_stops_before_review():
    events = []
    source_delivery = SourceDeliveryComposition(
        bootstrap=RecorderBootstrap(events),
        delivery=RecorderDelivery(events),
    )
    runtime, run, _ = make_runtime(
        source_delivery=source_delivery,
        stop_reason=AutonomyStopReason.EXECUTION_FAILED,
    )
    runtime.coordinator.events = events

    result = runtime.run(run_id=run.id, operation_key="operation-2", expected_revision=4)

    assert result.stop_reason is AutonomyStopReason.EXECUTION_FAILED
    assert [event[0] for event in events] == ["bootstrap", "coordinator"]
    assert runtime.last_delivery_result is None


def test_runtime_provider_delivery_failure_does_not_fabricate_review_success():
    events = []
    source_delivery = SourceDeliveryComposition(
        bootstrap=RecorderBootstrap(events),
        delivery=RecorderDelivery(events, fail=True),
    )
    runtime, run, _ = make_runtime(source_delivery=source_delivery)
    runtime.coordinator.events = events

    with pytest.raises(RuntimeCompositionError, match="verified source delivery failed"):
        runtime.run(run_id=run.id, operation_key="operation-3", expected_revision=5)

    assert [event[0] for event in events] == ["bootstrap", "coordinator", "delivery"]
    assert runtime.last_delivery_result is None


def test_runtime_without_source_delivery_preserves_existing_wave2_behavior():
    runtime, run, events = make_runtime(source_delivery=None)
    result = runtime.run(run_id=run.id, operation_key="operation-4", expected_revision=6)

    assert result.stop_reason is AutonomyStopReason.REVIEW_REQUIRED
    assert [event[0] for event in events] == ["coordinator"]
    assert runtime.last_delivery_result is None
