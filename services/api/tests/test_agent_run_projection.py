from __future__ import annotations

from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest

from parallax_api.code.agent_run_projection import (
    AgentRunControlRejected,
    AgentRunProjectionError,
    AgentRunProjectionService,
    DeterministicDisposition,
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
from parallax_api.repositories.worker_executions import EngineeringWorkerExecution


PROJECT = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT = "99999999-9999-4999-8999-999999999999"
RUN = "22222222-2222-4222-8222-222222222222"
OTHER_RUN = "88888888-8888-4888-8888-888888888888"
SPEC = "33333333-3333-4333-8333-333333333333"
SPEC_DIGEST = "a" * 64
ACCEPTANCE = ("AC-01", "AC-02")
NOW = datetime(2026, 8, 28, 3, 0, tzinfo=timezone.utc)


def _attempt(number: int, *, stage: str, status: str = "PASSED", failure_code: str | None = None) -> EngineeringAttempt:
    return EngineeringAttempt(
        id=f"00000000-0000-4000-8000-{number:012d}",
        run_id=RUN,
        stage=stage,
        attempt_number=number,
        operation_key=f"operation-{number}",
        status=status,
        program_id="protected-program",
        model_id="server-model",
        tool_id="sandbox-build" if stage in {"BUILD", "TEST", "VERIFY"} else None,
        evidence_json='{"prompt":"DO_NOT_PROJECT","authorization":"Bearer secret"}',
        failure_code=failure_code,
        started_at=NOW,
        completed_at=NOW,
    )


def _run(
    *,
    project_id: str | None = PROJECT,
    run_id: str = RUN,
    state: str = "REVIEW",
    revision: int = 6,
    resume_stage: str | None = None,
    fail_test: bool = False,
) -> EngineeringRun:
    run = EngineeringRun(
        id=run_id,
        conversation_id="77777777-7777-4777-8777-777777777777",
        spec_id="P2-V0.20.2",
        project_id=project_id,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        state=state,
        resume_stage=resume_stage,
        revision=revision,
        workspace_ref=None,
        last_failure_code="TEST_FAILED" if fail_test else None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
    )
    run.attempts = [
        _attempt(1, stage="BUILD"),
        _attempt(2, stage="TEST", status="FAILED" if fail_test else "PASSED", failure_code="TEST_FAILED" if fail_test else None),
        _attempt(3, stage="VERIFY"),
    ]
    return run


def _event(
    sequence: int,
    *,
    event_type: RunEventType,
    outcome: RunEventOutcome = RunEventOutcome.SUCCEEDED,
    project_id: str = PROJECT,
    run_id: str = RUN,
    source_lineage_ref: str | None = None,
    parent_source_lineage_ref: str | None = None,
    worker_execution_id: str | None = None,
    metadata: dict[str, object] | None = None,
    artifact_ref: str | None = None,
) -> RunEvent:
    subsystem = {
        RunEventType.WORKER_STATE: RunEventSubsystem.WORKER,
        RunEventType.EVALUATION_RESULT: RunEventSubsystem.EVALUATION,
        RunEventType.PROVIDER_RESULT: RunEventSubsystem.VERCEL,
        RunEventType.SOURCE_DELIVERY: RunEventSubsystem.GITHUB,
        RunEventType.SOURCE_LINEAGE_ACCEPTED: RunEventSubsystem.SOURCE_LINEAGE,
    }.get(event_type, RunEventSubsystem.RUN)
    return RunEvent(
        id=f"10000000-0000-4000-8000-{sequence:012d}",
        sequence=sequence,
        created_at=NOW,
        append=RunEventAppend(
            project_id=project_id,
            run_id=run_id,
            event_key=f"event:{sequence}",
            event_type=event_type,
            outcome=outcome,
            subsystem=subsystem,
            occurred_at=NOW,
            stage="VERIFY",
            worker_execution_id=worker_execution_id,
            source_lineage_ref=source_lineage_ref,
            parent_source_lineage_ref=parent_source_lineage_ref,
            artifact_ref=artifact_ref,
            evidence_ref=f"evidence:{sequence}",
            summary="bounded runtime evidence",
            metadata=metadata or {},
        ),
    )


def _worker(*, run_id: str = RUN) -> EngineeringWorkerExecution:
    return EngineeringWorkerExecution(
        id="55555555-5555-4555-8555-555555555555",
        run_id=run_id,
        state="READY_FOR_INTEGRATION",
        lease_owner_id=None,
        lease_generation=2,
        lease_expires_at=None,
        last_meaningful_progress_at=NOW,
        checkpoint_revision=4,
        checkpoint_json="{}",
        current_step="verify",
        source_lineage_ref="src:" + "b" * 64,
        last_known_good_lineage_ref="src:" + "a" * 64,
        retry_count=1,
        no_progress_count=0,
        oscillation_count=0,
        progress_fingerprint="c" * 64,
        previous_progress_fingerprint=None,
        stall_classification=None,
        blocker_code=None,
        next_recovery_action=None,
        revision=7,
        created_at=NOW,
        updated_at=NOW,
    )


def _events(*, evaluation_success: bool = True) -> tuple[RunEvent, ...]:
    lineage = "src:" + "b" * 64
    return (
        _event(
            1,
            event_type=RunEventType.WORKER_STATE,
            worker_execution_id="55555555-5555-4555-8555-555555555555",
            source_lineage_ref=lineage,
            metadata={"worker_state": "READY_FOR_INTEGRATION", "lease_generation": 2, "checkpoint_revision": 4},
        ),
        _event(
            2,
            event_type=RunEventType.EVALUATION_RESULT,
            outcome=RunEventOutcome.SUCCEEDED if evaluation_success else RunEventOutcome.FAILED,
            source_lineage_ref=lineage,
            metadata={"evaluation_id": "eval-primary", "score_class": "PASS" if evaluation_success else "FAIL"},
        ),
        _event(
            3,
            event_type=RunEventType.PROVIDER_RESULT,
            source_lineage_ref=lineage,
            metadata={"provider": "vercel", "result_code": "PREVIEW_READY"},
        ),
        _event(
            4,
            event_type=RunEventType.SOURCE_DELIVERY,
            source_lineage_ref=lineage,
            parent_source_lineage_ref="src:" + "a" * 64,
            artifact_ref="delivery:primary",
            metadata={"pull_request_number": 400, "preview_deployment_id": "dpl_preview_123", "preview_status": "READY"},
        ),
    )


def test_projection_binds_canonical_identity_recovery_evaluation_routing_and_delivery() -> None:
    projection = build_agent_run_projection(
        run=_run(),
        acceptance_ids=ACCEPTANCE,
        events=reversed(_events()),
        worker=_worker(),
    )

    assert projection.identity.project_id == PROJECT
    assert projection.identity.run_id == RUN
    assert projection.identity.acceptance_ids == ACCEPTANCE
    assert projection.latest_source_lineage_ref == "src:" + "b" * 64
    assert projection.recovery.execution_id == "55555555-5555-4555-8555-555555555555"
    assert projection.recovery.lease_generation == 2
    assert projection.evaluation.evaluation_id == "eval-primary"
    assert projection.routing.provider == "vercel"
    assert projection.delivery.pull_request_number == 400
    assert projection.delivery.preview_deployment_id == "dpl_preview_123"
    assert projection.delivery.preview_status == "READY"
    assert projection.latest_event_sequence == 4
    assert projection.final_handoff == "HUMAN_REQUIRED"


def test_cross_project_run_or_worker_evidence_fails_closed() -> None:
    with pytest.raises(AgentRunProjectionError, match="cross-Project or cross-run"):
        build_agent_run_projection(
            run=_run(),
            acceptance_ids=ACCEPTANCE,
            events=(_event(1, event_type=RunEventType.WORKER_STATE, project_id=OTHER_PROJECT),),
        )
    with pytest.raises(AgentRunProjectionError, match="cross-Project or cross-run"):
        build_agent_run_projection(
            run=_run(),
            acceptance_ids=ACCEPTANCE,
            events=(_event(1, event_type=RunEventType.WORKER_STATE, run_id=OTHER_RUN),),
        )
    with pytest.raises(AgentRunProjectionError, match="worker evidence crosses"):
        build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE, worker=_worker(run_id=OTHER_RUN))


def test_unbound_or_incomplete_run_cannot_be_projected_as_authoritative() -> None:
    with pytest.raises(AgentRunProjectionError, match="Project-bound approved Work Specification"):
        build_agent_run_projection(run=_run(project_id=None), acceptance_ids=ACCEPTANCE)
    run = _run()
    run.work_specification_digest = None
    with pytest.raises(AgentRunProjectionError, match="Project-bound approved Work Specification"):
        build_agent_run_projection(run=run, acceptance_ids=ACCEPTANCE)


def test_deterministic_validation_failure_remains_authoritative_over_positive_evaluation() -> None:
    projection = build_agent_run_projection(
        run=_run(fail_test=True, state="FAILED", resume_stage="TEST"),
        acceptance_ids=ACCEPTANCE,
        events=_events(evaluation_success=True),
        worker=_worker(),
    )
    assert projection.evaluation.outcome == "SUCCEEDED"
    assert projection.deterministic_disposition is DeterministicDisposition.FAILED
    test_gate = next(item for item in projection.validation if item.stage == "TEST")
    assert test_gate.disposition is DeterministicDisposition.FAILED
    assert test_gate.failure_code == "TEST_FAILED"


def test_metrics_preserve_observed_estimated_and_unknown_states() -> None:
    metrics = (
        ProjectionMetricEvidence(
            metric=ProjectionMetric.ELAPSED_TIME,
            state=ProjectionKnownState.OBSERVED,
            value=1234.0,
            provenance_ref="attempts:duration",
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
    with pytest.raises(AgentRunProjectionError, match="unknown metric cannot carry"):
        ProjectionMetricEvidence(
            metric=ProjectionMetric.COST_USAGE,
            state=ProjectionKnownState.UNKNOWN,
            value=0.0,
            provenance_ref=None,
        )


def test_projection_replay_is_deterministic_and_revision_drift_changes_fingerprint() -> None:
    first = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE, events=_events(), worker=_worker())
    replay = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE, events=_events(), worker=_worker())
    changed = build_agent_run_projection(run=_run(revision=7), acceptance_ids=ACCEPTANCE, events=_events(), worker=_worker())
    assert first.fingerprint == replay.fingerprint
    assert safe_agent_run_projection_json(first) == safe_agent_run_projection_json(replay)
    assert changed.fingerprint != first.fingerprint


def test_controls_are_server_derived_from_existing_run_authority_and_stale_requests_fail_closed() -> None:
    review = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE)
    assert [item.kind.value for item in review.advertised_controls] == ["pause", "cancel"]
    pause = ProjectionControlRequest(
        request_id="pause-once",
        project_id=PROJECT,
        run_id=RUN,
        expected_revision=6,
        expected_state="REVIEW",
        action="pause",
    )
    assert decide_projection_control(review, pause).allowed is True

    unsupported = ProjectionControlRequest(
        request_id="resume-invalid",
        project_id=PROJECT,
        run_id=RUN,
        expected_revision=6,
        expected_state="REVIEW",
        action="resume",
    )
    assert decide_projection_control(review, unsupported).deny_reason is ProjectionControlDenyReason.UNSUPPORTED_CONTROL

    stale = ProjectionControlRequest(
        request_id="pause-stale",
        project_id=PROJECT,
        run_id=RUN,
        expected_revision=5,
        expected_state="REVIEW",
        action="pause",
    )
    assert decide_projection_control(review, stale).deny_reason is ProjectionControlDenyReason.REVISION_MISMATCH

    paused = build_agent_run_projection(
        run=_run(state="PAUSED", revision=7, resume_stage="TEST"),
        acceptance_ids=ACCEPTANCE,
    )
    assert [item.kind.value for item in paused.advertised_controls] == ["resume", "cancel"]

    complete = build_agent_run_projection(run=_run(state="COMPLETE", revision=8), acceptance_ids=ACCEPTANCE)
    assert complete.advertised_controls == ()


class _FakeRuns:
    def __init__(self) -> None:
        self.existing: set[str] = set()

    def find_operation(self, run_id: str, operation_key: str):
        return SimpleNamespace(id="existing") if operation_key in self.existing else None


class _FakeService:
    def __init__(self, run: EngineeringRun) -> None:
        self.run = run
        self.runs = _FakeRuns()
        self.calls: list[tuple[str, str, int]] = []

    def get(self, run_id: str) -> EngineeringRun:
        assert run_id == self.run.id
        return self.run

    def acceptance_map_for_run(self, run: EngineeringRun) -> list[dict[str, str]]:
        return [{"id": item, "text": item} for item in ACCEPTANCE]

    def _record(self, method: str, *, operation_key: str, expected_revision: int):
        self.calls.append((method, operation_key, expected_revision))
        return SimpleNamespace(replayed=operation_key in self.runs.existing)

    def pause(self, *, run_id: str, operation_key: str, expected_revision: int):
        return self._record("pause", operation_key=operation_key, expected_revision=expected_revision)

    def resume(self, *, run_id: str, operation_key: str, expected_revision: int):
        return self._record("resume", operation_key=operation_key, expected_revision=expected_revision)

    def cancel(self, *, run_id: str, operation_key: str, expected_revision: int):
        return self._record("cancel", operation_key=operation_key, expected_revision=expected_revision)


class _FakeWorkers:
    def get_for_run(self, run_id: str):
        return _worker(run_id=run_id)


class _FakeEvents:
    def list_for_run(self, *, project_id: str, run_id: str, after_sequence: int = 0, limit: int = 100):
        return _events()


def test_projection_service_reuses_existing_control_methods_and_idempotency_key() -> None:
    run = _run()
    service = _FakeService(run)
    facade = AgentRunProjectionService(service, _FakeWorkers(), events=_FakeEvents())
    projection = facade.project(project_id=PROJECT, run_id=RUN)
    request = ProjectionControlRequest(
        request_id="pause-once",
        project_id=PROJECT,
        run_id=RUN,
        expected_revision=6,
        expected_state="REVIEW",
        action="pause",
    )
    result = facade.control(projection, request)
    assert result.replayed is False
    assert service.calls == [("pause", "agent-projection:pause:pause-once", 6)]

    service.runs.existing.add(request.operation_key)
    service.run.state = "PAUSED"
    service.run.revision = 7
    replay = facade.control(projection, request)
    assert replay.replayed is True
    assert service.calls[-1] == ("pause", "agent-projection:pause:pause-once", 6)


def test_projection_service_rejects_cross_project_and_stale_non_replay_controls() -> None:
    service = _FakeService(_run())
    facade = AgentRunProjectionService(service, _FakeWorkers())
    projection = facade.project(project_id=PROJECT, run_id=RUN)
    with pytest.raises(AgentRunControlRejected, match="REVISION_MISMATCH"):
        facade.control(
            projection,
            ProjectionControlRequest(
                request_id="stale",
                project_id=PROJECT,
                run_id=RUN,
                expected_revision=5,
                expected_state="REVIEW",
                action="pause",
            ),
        )
    with pytest.raises(AgentRunProjectionError, match="scope is unavailable"):
        facade.project(project_id=OTHER_PROJECT, run_id=RUN)


def test_safe_projection_serialization_exposes_no_private_payload_or_new_authority() -> None:
    projection = build_agent_run_projection(run=_run(), acceptance_ids=ACCEPTANCE, events=_events(), worker=_worker())
    payload = json.loads(safe_agent_run_projection_json(projection))
    assert [item["kind"] for item in payload["advertised_controls"]] == ["pause", "cancel"]
    for field in (
        "accepts_source_lineage",
        "creates_lifecycle_authority",
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
    assert "do_not_project" not in text
    assert "bearer secret" not in text
    assert "authorization" not in text


def test_duplicate_or_malformed_acceptance_identity_is_rejected() -> None:
    with pytest.raises(AgentRunProjectionError, match="unique stable AC identities"):
        build_agent_run_projection(run=_run(), acceptance_ids=("AC-01", "AC-01"))
    with pytest.raises(AgentRunProjectionError, match="unique stable AC identities"):
        build_agent_run_projection(run=_run(), acceptance_ids=("criterion-one",))
