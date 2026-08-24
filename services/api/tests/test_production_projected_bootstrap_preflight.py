from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import production_projected_bootstrap_preflight as preflight
from parallax_api.code.autonomy import AutonomyStopReason
from parallax_api.models import EngineeringRun


class _RecordingBootstrap:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def ensure(self, run: EngineeringRun, *, operation_key: str):
        self.calls.append((run.id, operation_key))
        return SimpleNamespace()


class _UnusedAllocator:
    def initialize(self, *args, **kwargs):
        raise AssertionError("runtime canary unit test must not initialize through the dummy allocator")

    def current_lineage(self, *args, **kwargs):
        raise AssertionError("runtime canary unit test must not read through the dummy allocator")

    def resolve(self, *args, **kwargs):
        raise AssertionError("runtime canary unit test must not resolve implementation lineage")

    def accept_implementation(self, *args, **kwargs):
        raise AssertionError("runtime canary unit test must not accept implementation lineage")

    def reconstruct(self, *args, **kwargs):
        raise AssertionError("runtime canary unit test must not reconstruct implementation lineage")

    def cleanup(self, *args, **kwargs):
        raise AssertionError("runtime canary unit test must not acquire cleanup leases")


def _run() -> EngineeringRun:
    return EngineeringRun(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        spec_id="P2-V0.16.5",
        project_id=str(uuid4()),
        state="PLAN",
        revision=1,
    )


def test_runtime_canary_bootstraps_then_stops_before_stage_mutation() -> None:
    run = _run()
    bootstrap = _RecordingBootstrap()
    composition = SimpleNamespace(bootstrap=bootstrap, delivery=SimpleNamespace())
    allocator = _UnusedAllocator()

    first = preflight._runtime_for(run, allocator, composition).run(
        run_id=run.id,
        operation_key="canary:first",
        expected_revision=1,
    )
    recreated = preflight._runtime_for(run, allocator, composition).run(
        run_id=run.id,
        operation_key="canary:recreated",
        expected_revision=1,
    )

    assert first.stop_reason is AutonomyStopReason.EXECUTOR_UNAVAILABLE
    assert recreated.stop_reason is AutonomyStopReason.EXECUTOR_UNAVAILABLE
    assert [item.outcome for item in first.steps] == ["FAILED"]
    assert [item.stage for item in first.steps] == ["EXECUTOR"]
    assert [item.stage for item in recreated.steps] == ["EXECUTOR"]
    assert bootstrap.calls == [
        (run.id, "canary:first"),
        (run.id, "canary:recreated"),
    ]
    assert run.state == "PLAN"
    assert run.revision == 1
