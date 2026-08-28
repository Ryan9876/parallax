from __future__ import annotations

from datetime import datetime, timezone

from parallax_api.code.agent_run_projection import ProjectionKnownState
from parallax_api.code.agentic_observability import RuntimeMetricId, build_agentic_run_observability
from parallax_api.code.run_events import (
    RunEvent,
    RunEventAppend,
    RunEventOutcome,
    RunEventSubsystem,
    RunEventType,
)
from parallax_api.models import EngineeringRun


PROJECT = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"
SPEC = "33333333-3333-4333-8333-333333333333"
NOW = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)


def test_incomplete_bounded_event_window_is_explicit_and_downgrades_event_dependent_truth() -> None:
    run = EngineeringRun(
        id=RUN,
        conversation_id="77777777-7777-4777-8777-777777777777",
        spec_id="P2-V0.20.5",
        project_id=PROJECT,
        work_specification_id=SPEC,
        work_specification_revision=1,
        work_specification_digest="a" * 64,
        state="REVIEW",
        revision=9,
        created_at=NOW,
        updated_at=NOW,
    )
    run.attempts = []
    evaluation = RunEvent(
        id="10000000-0000-4000-8000-000000000001",
        sequence=1,
        created_at=NOW,
        append=RunEventAppend(
            project_id=PROJECT,
            run_id=RUN,
            event_key="evaluation:partial",
            event_type=RunEventType.EVALUATION_RESULT,
            outcome=RunEventOutcome.SUCCEEDED,
            subsystem=RunEventSubsystem.EVALUATION,
            occurred_at=NOW,
            stage="VERIFY",
            evidence_ref="evaluation:partial",
            summary="bounded evaluation evidence",
            metadata={"evaluation_id": "eval-partial", "score_class": "PASS"},
        ),
    )

    projection = build_agentic_run_observability(
        run=run,
        acceptance_ids=("AC-01",),
        events=(evaluation,),
        event_plane_available=True,
        event_plane_complete=False,
        authoritative_latest_event_sequence=201,
    )
    by_metric = {item.metric: item for item in projection.metrics}

    assert projection.coverage.event_plane_available is True
    assert projection.coverage.event_plane_complete is False
    assert projection.latest_event_sequence == 201
    assert projection.quality.evaluation_outcome is None
    assert projection.quality.preview_status is None
    assert by_metric[RuntimeMetricId.HUMAN_INTERVENTION_COUNT].state is ProjectionKnownState.ESTIMATED
