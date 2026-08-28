from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from parallax_api.code.agent_run_projection import (
    AgentRunProjectionError,
    ProjectionControlDenyReason,
    ProjectionControlRequest,
    ProjectionKnownState,
    ProjectionMetric,
    ProjectionMetricEvidence,
    build_agent_run_projection,
    decide_projection_control,
    safe_agent_run_projection_json,
)
from parallax_api.code.run_events import (
    RunEvent,
    RunEventAppend,
    RunEventOutcome,
    RunEventSubsystem,
    RunEventType,
)
from parallax_api.models import EngineeringAttempt, EngineeringRun


PROJECT = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT = "99999999-9999-4999-8999-999999999999"
RUN = "22222222-2222-4222-8222-222222222222"
OTHER_RUN = "88888888-8888-4888-8888-888888888888"
SPEC = "33333333-3333-4333-8333-333333333333"
SPEC_DIGEST = "a" * 64
ACCEPTANCE = ("AC-01", "AC-02")
NOW = datetime(2026, 8, 28, 3, 0, tzinfo=timezone.utc)


def _attempt(*, number: int = 1, stage: str = "BUILD", status: str = "PASSED") -> EngineeringAttempt:
    return EngineeringAttempt(
        id=f"00000000-0000-4000-8000-{number:012d}",
        run_id=RUN,
        stage=stage,
        attempt_number=number,
        operation_key=f"operation-{number}",
        status=status,
        program_id="protected-build" if stage == "BUILD" else None,
        model_id=None,
        tool_id="sandbox-build" if stage == "BUILD" else None,
        evidence_json="{}",
        failure_code=None if status == "PASSED" else "PROTECTED_FAILURE",
        started_at=NOW,
        completed_at=NOW,
    )


def _run(*, project_id: str = PROJECT, run_id: str = RUN, state: str = "REVIEW", revision: int = 6) -> EngineeringRun:
    run = EngineeringRun(
        id=run_id,
        conversation_id="77777777-7777-4777-8777-777777777777",
        spec_id="P2-V0.20.2",
        project_id=project_id,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        state=state,
        resume_stage=None,
        revision=revision,
        workspace_ref=None,
        last_failure_code=None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
    )
    run.attempts = [_attempt()]
    return run


def _event(
    sequence: int,
    *,
    project_id: str = PROJECT,
    run_id: str = RUN,
    event_type: RunEventType = RunEventType.WORKER_STATE,
    source_lineage_ref: str | None = None,
    metadata: dict[str, object] | None = None,
) -> RunEvent:
    return RunEvent(
        id=f"10000000-0000-4000-8000-{sequence:012d}",
        sequence=sequence,
        created_at=NOW,
        append=RunEventAppend(
            project_id=project_id,
            run_id=run_id,
            event_key=f"event:{sequence}",
            event_type=event_type,
            outcome=RunEventOutcome.SUCCEEDED,
            subsystem=(
                RunEventSubsystem.SOURCE_LINEAGE
                if event_type is RunEventType.SOURCE_LINEAGE_ACCEPTED
                else RunEventSubsystem.WORKER
            ),
            occurred_at=NOW,
            stage="IMPLEMENT" if source_lineage_ref else "VERIFY",
            worker_execution_id="55555555-5555-4555-8555-555555555555",
            source_lineage_ref=source_lineage_ref,
            evidence_ref=f"evidence:{sequence}",
            summary="bounded authoritative runtime evidence",
            metadata=metadata or {"worker_state": "READY_FOR_INTEGRATION", "lease_generation": 1},
        ),
    )


def test_projection_derives_exact_authoritative_identity_and_orders_evidence() -> None:
    events = (
        _event(2, event_type=RunEventType.SOURCE_LINEAGE_ACCEPTED, source_lineage_ref="src:" + "b" * 64),
        _event(1),
        _event(
            3,
            event_type=RunEventType.PROVIDER_RESULT,
            metadata={"preview_deployment_id": "dpl_preview_123", "preview_status": "READY"},
        ),
    )
    projection = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE, events=events)

    assert projection.identity.project_id == PROJECT
    assert projection.identity.run_id == RUN
    assert projection.identity.acceptance_ids == ACCEPTANCE
    assert [item.sequence for item in projection.events] == [1, 2, 3]
    assert projection.latest_source_lineage_ref == "src:" + "b" * 64
    assert projection.preview_deployment_id == "dpl_preview_123"
    assert projection.preview_status == "READY"
    assert projection.attempts[0].stage == "BUILD"
    assert projection.attempts[0].status == "PASSED"
    assert projection.current_state == "REVIEW"
    assert projection.run_revision == 6


def test_cross_project_or_cross_run_events_fail_closed() -> None:
    with pytest.raises(AgentRunProjectionError, match="cross-Project or cross-run"):
        build_agent_run_projection(
            run=_run(),
            acceptance_ids=ACCEPTANCE,
            events=(_event(1, project_id=OTHER_PROJECT),),
        )
    with pytest.raises(AgentRunProjectionError, match="cross-Project or cross-run"):
        build_agent_run_projection(
            run=_run(),
            acceptance_ids=ACCEPTANCE,
            events=(_event(1, run_id=OTHER_RUN),),
        )


def test_unbound_or_incomplete_run_cannot_be_projected_as_authoritative() -> None:
    with pytest.raises(AgentRunProjectionError, match="Project-bound approved Work Specification"):
        build_agent_run_projection(run=_run(project_id=None), acceptance_ids=ACCEPTANCE)

    run = _run()
    run.work_specification_digest = None
    with pytest.raises(AgentRunProjectionError, match="Project-bound approved Work Specification"):
        build_agent_run_projection(run=run, acceptance_ids=ACCEPTANCE)


def test_metrics_preserve_observed_estimated_and_unknown_states() -> None:
    metrics = (
        ProjectionMetricEvidence(
            metric=ProjectionMetric.ELAPSED_TIME,
            state=ProjectionKnownState.OBSERVED,
            value=1234.0,
            provenance_ref="event:elapsed-time",
        ),
        ProjectionMetricEvidence(
            metric=ProjectionMetric.COST_USAGE,
            state=ProjectionKnownState.ESTIMATED,
            value=1.25,
            provenance_ref="estimate:cost-v1",
        ),
    )
    projection = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE, metrics=metrics)
    by_metric = {item.metric: item for item in projection.metrics}

    assert by_metric[ProjectionMetric.ELAPSED_TIME].state is ProjectionKnownState.OBSERVED
    assert by_metric[ProjectionMetric.COST_USAGE].state is ProjectionKnownState.ESTIMATED
    assert by_metric[ProjectionMetric.HUMAN_INTERVENTIONS].state is ProjectionKnownState.UNKNOWN
    assert by_metric[ProjectionMetric.HUMAN_INTERVENTIONS].value is None

    with pytest.raises(AgentRunProjectionError, match="unknown metric cannot carry value"):
        ProjectionMetricEvidence(
            metric=ProjectionMetric.COST_USAGE,
            state=ProjectionKnownState.UNKNOWN,
            value=0.0,
            provenance_ref=None,
        )


def test_projection_replay_is_deterministic_and_revision_drift_changes_identity() -> None:
    events = (_event(1),)
    first = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE, events=events)
    replay = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE, events=events)
    changed = build_agent_run_projection(run=_run(revision=7), acceptance_ids=ACCEPTANCE, events=events)

    assert first.fingerprint == replay.fingerprint
    assert safe_agent_run_projection_json(first) == safe_agent_run_projection_json(replay)
    assert changed.fingerprint != first.fingerprint


def test_s2_v1_advertises_no_invented_controls_and_stale_requests_fail_closed() -> None:
    projection = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE)
    exact = ProjectionControlRequest(
        project_id=PROJECT,
        run_id=RUN,
        expected_revision=6,
        expected_state="REVIEW",
        action="resume",
    )
    assert decide_projection_control(projection, exact).deny_reason is ProjectionControlDenyReason.UNSUPPORTED_CONTROL

    stale = ProjectionControlRequest(
        project_id=PROJECT,
        run_id=RUN,
        expected_revision=5,
        expected_state="REVIEW",
        action="resume",
    )
    assert decide_projection_control(projection, stale).deny_reason is ProjectionControlDenyReason.REVISION_MISMATCH

    foreign = ProjectionControlRequest(
        project_id=OTHER_PROJECT,
        run_id=RUN,
        expected_revision=6,
        expected_state="REVIEW",
        action="resume",
    )
    assert decide_projection_control(projection, foreign).deny_reason is ProjectionControlDenyReason.PROJECT_MISMATCH


def test_safe_projection_serialization_exposes_no_mutation_or_private_payload_authority() -> None:
    projection = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE, events=(_event(1),))
    payload = json.loads(safe_agent_run_projection_json(projection))

    assert payload["advertised_controls"] == []
    for field in (
        "accepts_source_lineage",
        "transitions_engineering_run",
        "grants_provider_authority",
        "grants_tool_authority",
        "executes_arbitrary_command",
        "performs_merge",
        "performs_production_deployment",
        "completes_review",
        "contains_source_bytes",
        "contains_patch",
        "contains_credentials",
        "contains_provider_payload",
        "contains_prompts",
        "contains_hidden_reasoning",
        "contains_unrestricted_logs",
    ):
        assert payload[field] is False

    text = safe_agent_run_projection_json(projection).lower()
    assert "bearer " not in text
    assert "authorization:" not in text
    assert "chain-of-thought" not in text


def test_duplicate_or_malformed_acceptance_identity_is_rejected() -> None:
    with pytest.raises(AgentRunProjectionError, match="unique stable AC identities"):
        build_agent_run_projection(run=_run(), acceptance_ids=("AC-01", "AC-01"))
    with pytest.raises(AgentRunProjectionError, match="unique stable AC identities"):
        build_agent_run_projection(run=_run(), acceptance_ids=("criterion-one",))
