from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from parallax_api.code.agent_run_projection import DeterministicDisposition, ProjectionKnownState, ProjectionMetric
from parallax_api.code.agentic_observability import (
    AgenticObservabilityError,
    AgenticObservabilityScopeError,
    RuntimeMetricId,
    build_agentic_run_observability,
    query_time_retention_cleanup,
    safe_agentic_observability_json,
)
from parallax_api.code.run_events import (
    RunEvent,
    RunEventAppend,
    RunEventOutcome,
    RunEventSubsystem,
    RunEventType,
)
from parallax_api.models import EngineeringAttempt, EngineeringRun
from parallax_api.repositories.worker_executions import EngineeringWorkerExecution


PROJECT = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT = "99999999-9999-4999-8999-999999999999"
RUN = "22222222-2222-4222-8222-222222222222"
OTHER_RUN = "88888888-8888-4888-8888-888888888888"
SPEC = "33333333-3333-4333-8333-333333333333"
NOW = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)


def _attempt(
    suffix: int,
    *,
    stage: str,
    attempt_number: int,
    status: str = "PASSED",
    failure_code: str | None = None,
) -> EngineeringAttempt:
    return EngineeringAttempt(
        id=f"00000000-0000-4000-8000-{suffix:012d}",
        run_id=RUN,
        stage=stage,
        attempt_number=attempt_number,
        operation_key=f"operation-{suffix}",
        status=status,
        evidence_json='{"prompt":"must-not-leak","authorization":"Bearer must-not-leak"}',
        failure_code=failure_code,
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=suffix),
    )


def _run(*, project_id: str | None = PROJECT, state: str = "REVIEW", fail_test: bool = False) -> EngineeringRun:
    run = EngineeringRun(
        id=RUN,
        conversation_id="77777777-7777-4777-8777-777777777777",
        spec_id="P2-V0.20.5",
        project_id=project_id,
        work_specification_id=SPEC,
        work_specification_revision=1,
        work_specification_digest="a" * 64,
        state=state,
        resume_stage="TEST" if fail_test else None,
        revision=7,
        workspace_ref=None,
        last_failure_code="TEST_FAILED" if fail_test else None,
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=125),
        completed_at=None,
    )
    run.attempts = [
        _attempt(1, stage="BUILD", attempt_number=1),
        _attempt(2, stage="TEST", attempt_number=1, status="FAILED" if fail_test else "PASSED", failure_code="TEST_FAILED" if fail_test else None),
        _attempt(3, stage="TEST", attempt_number=2),
        _attempt(4, stage="VERIFY", attempt_number=1),
        _attempt(5, stage="REVIEW", attempt_number=1, status="PAUSED"),
    ]
    return run


def _event(
    sequence: int,
    *,
    event_key: str | None = None,
    event_type: RunEventType = RunEventType.RUN_CONTROL,
    outcome: RunEventOutcome = RunEventOutcome.PROGRESSED,
    project_id: str = PROJECT,
    run_id: str = RUN,
    attempt_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> RunEvent:
    subsystem = RunEventSubsystem.REVIEW if event_type is RunEventType.REVIEW_REQUIRED else RunEventSubsystem.RUN
    return RunEvent(
        id=f"10000000-0000-4000-8000-{sequence:012d}",
        sequence=sequence,
        created_at=NOW,
        append=RunEventAppend(
            project_id=project_id,
            run_id=run_id,
            event_key=event_key or f"event:{sequence}",
            event_type=event_type,
            outcome=outcome,
            subsystem=subsystem,
            occurred_at=NOW + timedelta(seconds=sequence),
            stage="REVIEW",
            attempt_id=attempt_id,
            evidence_ref=f"evidence:{sequence}",
            summary="bounded observability evidence",
            metadata=metadata or {},
        ),
    )


def _worker() -> EngineeringWorkerExecution:
    return EngineeringWorkerExecution(
        id="55555555-5555-4555-8555-555555555555",
        run_id=RUN,
        state="READY_FOR_INTEGRATION",
        lease_owner_id=None,
        lease_generation=2,
        lease_expires_at=None,
        checkpoint_revision=4,
        checkpoint_json="{}",
        current_step="verify",
        retry_count=2,
        no_progress_count=0,
        oscillation_count=0,
        revision=8,
        created_at=NOW,
        updated_at=NOW,
    )


def _metrics(projection):
    return {item.metric: item for item in projection.metrics}


def test_query_time_metrics_preserve_observed_estimated_and_unknown_truth() -> None:
    projection = build_agentic_run_observability(
        run=_run(),
        acceptance_ids=("AC-01",),
        worker=_worker(),
        event_plane_available=False,
    )
    metrics = _metrics(projection)

    assert metrics[RuntimeMetricId.RUN_ELAPSED_SECONDS].state is ProjectionKnownState.OBSERVED
    assert metrics[RuntimeMetricId.RUN_ELAPSED_SECONDS].value == 125.0
    assert metrics[RuntimeMetricId.ATTEMPT_RETRY_COUNT].value == 1.0
    assert metrics[RuntimeMetricId.WORKER_RETRY_COUNT].value == 2.0
    assert metrics[RuntimeMetricId.HUMAN_INTERVENTION_COUNT].state is ProjectionKnownState.ESTIMATED
    assert metrics[RuntimeMetricId.PROVIDER_USAGE_UNITS].state is ProjectionKnownState.UNKNOWN
    assert metrics[RuntimeMetricId.PROVIDER_USAGE_UNITS].value is None
    assert metrics[RuntimeMetricId.PROVIDER_COST_USD].state is ProjectionKnownState.UNKNOWN
    assert metrics[RuntimeMetricId.PROVIDER_COST_USD].value is None


def test_event_backed_interventions_are_observed_and_replay_duplicates_do_not_double_count() -> None:
    pause_attempt = "00000000-0000-4000-8000-000000000005"
    control = _event(1, event_key="pause-control", attempt_id=pause_attempt)
    duplicate = _event(99, event_key="pause-control", attempt_id=pause_attempt)
    review = _event(
        2,
        event_key="review-required",
        event_type=RunEventType.REVIEW_REQUIRED,
        outcome=RunEventOutcome.HUMAN_REQUIRED,
    )
    projection = build_agentic_run_observability(
        run=_run(),
        acceptance_ids=("AC-01",),
        events=(control, duplicate, review),
        event_plane_available=True,
    )
    metric = _metrics(projection)[RuntimeMetricId.HUMAN_INTERVENTION_COUNT]

    assert metric.state is ProjectionKnownState.OBSERVED
    assert metric.value == 2.0
    assert projection.coverage.unique_event_count == 2


def test_conflicting_replay_or_cross_project_evidence_fails_closed() -> None:
    first = _event(1, event_key="same-event")
    conflict = _event(
        2,
        event_key="same-event",
        outcome=RunEventOutcome.HUMAN_REQUIRED,
    )
    with pytest.raises(AgenticObservabilityError, match="conflicting protected content"):
        build_agentic_run_observability(
            run=_run(),
            acceptance_ids=("AC-01",),
            events=(first, conflict),
            event_plane_available=True,
        )
    with pytest.raises(AgenticObservabilityScopeError, match="cross-Project"):
        build_agentic_run_observability(
            run=_run(),
            acceptance_ids=("AC-01",),
            events=(_event(1, project_id=OTHER_PROJECT),),
            event_plane_available=True,
        )
    with pytest.raises(AgenticObservabilityScopeError, match="cross-Project"):
        build_agentic_run_observability(
            run=_run(),
            acceptance_ids=("AC-01",),
            events=(_event(1, run_id=OTHER_RUN),),
            event_plane_available=True,
        )


def test_deterministic_failure_remains_effective_despite_positive_evaluation_and_preview() -> None:
    evaluation = _event(
        1,
        event_type=RunEventType.EVALUATION_RESULT,
        outcome=RunEventOutcome.SUCCEEDED,
        metadata={"evaluation_id": "eval-pass", "score_class": "PASS"},
    )
    delivery = RunEvent(
        id="10000000-0000-4000-8000-000000000002",
        sequence=2,
        created_at=NOW,
        append=RunEventAppend(
            project_id=PROJECT,
            run_id=RUN,
            event_key="preview-ready",
            event_type=RunEventType.SOURCE_DELIVERY,
            outcome=RunEventOutcome.SUCCEEDED,
            subsystem=RunEventSubsystem.VERCEL,
            occurred_at=NOW,
            stage="VERIFY",
            artifact_ref="preview:bounded",
            evidence_ref="evidence:preview",
            summary="bounded preview evidence",
            metadata={"preview_deployment_id": "dpl_preview", "preview_status": "READY"},
        ),
    )
    projection = build_agentic_run_observability(
        run=_run(state="FAILED", fail_test=True),
        acceptance_ids=("AC-01",),
        events=(evaluation, delivery),
        event_plane_available=True,
    )

    assert projection.quality.evaluation_outcome == "SUCCEEDED"
    assert projection.quality.preview_status == "READY"
    assert projection.quality.deterministic_disposition is DeterministicDisposition.FAILED
    assert projection.quality.effective_disposition is DeterministicDisposition.FAILED
    assert projection.quality.deterministic_failure_authoritative is True


def test_s2_compatibility_keeps_cost_unknown_and_maps_existing_metrics_exactly() -> None:
    projection = build_agentic_run_observability(
        run=_run(),
        acceptance_ids=("AC-01",),
        worker=_worker(),
        event_plane_available=False,
    )
    compatible = {item.metric: item for item in projection.s2_compatible_metrics}

    assert compatible[ProjectionMetric.ELAPSED_TIME].value == 125.0
    assert compatible[ProjectionMetric.HUMAN_INTERVENTIONS].state is ProjectionKnownState.ESTIMATED
    assert compatible[ProjectionMetric.COST_USAGE].state is ProjectionKnownState.UNKNOWN
    assert compatible[ProjectionMetric.COST_USAGE].value is None


def test_serialization_is_bounded_privacy_safe_and_contains_no_authority() -> None:
    projection = build_agentic_run_observability(
        run=_run(),
        acceptance_ids=("AC-01",),
        worker=_worker(),
        event_plane_available=False,
    )
    payload = safe_agentic_observability_json(projection)

    assert "must-not-leak" not in payload
    assert "Bearer" not in payload
    assert '"contains_credentials":false' in payload
    assert '"contains_provider_payload":false' in payload
    assert '"contains_prompts":false' in payload
    assert '"contains_hidden_reasoning":false' in payload
    assert '"contains_source_bytes":false' in payload
    assert '"performs_merge":false' in payload
    assert '"performs_production_deployment":false' in payload
    assert '"completes_review":false' in payload


def test_query_time_retention_is_deterministic_noop_with_no_delete_authority() -> None:
    first = query_time_retention_cleanup()
    second = query_time_retention_cleanup()

    assert first == second
    assert first.mode == "QUERY_TIME"
    assert first.persisted_derived_rows is False
    assert first.cleanup_required is False
    assert first.cleanup_mutation_available is False
    assert first.canonical_deletion_authority is False


def test_unbound_run_and_invalid_durable_time_fail_to_explicit_safe_state() -> None:
    with pytest.raises(AgenticObservabilityScopeError, match="historical unbound"):
        build_agentic_run_observability(run=_run(project_id=None), acceptance_ids=("AC-01",))

    run = _run()
    run.updated_at = run.created_at - timedelta(seconds=1)
    projection = build_agentic_run_observability(run=run, acceptance_ids=("AC-01",))
    elapsed = _metrics(projection)[RuntimeMetricId.RUN_ELAPSED_SECONDS]
    assert elapsed.state is ProjectionKnownState.UNKNOWN
    assert elapsed.value is None
