from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from parallax_api.code.agent_protocol import (
    AdmissionReason,
    AgentAdapter,
    AgentEvidenceReference,
    AgentIdentity,
    AgentLifecycleStatus,
    AgentProtocolError,
    AgentSourceContext,
    AgentTaskRequest,
    EvidenceKind,
    MetricAvailability,
    MetricName,
    MetricObservation,
    MetricProvenanceKind,
    ReferenceCheckpointAdapter,
    ReferenceTimeoutAdapter,
    safe_json,
    verify_checkpoint_admission,
    verify_result_admission,
)

PROJECT = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"
SPEC = "33333333-3333-4333-8333-333333333333"
SPEC_DIGEST = "a" * 64
LINEAGE = "b" * 64
NOW = datetime(2026, 8, 26, 20, 0, tzinfo=timezone.utc)


def task(agent: AgentIdentity, **changes) -> AgentTaskRequest:
    values = {
        "project_id": PROJECT,
        "run_id": RUN,
        "work_specification_id": SPEC,
        "work_specification_revision": 3,
        "work_specification_digest": SPEC_DIGEST,
        "acceptance_ids": ("AC-01", "AC-02", "AC-03"),
        "operation_id": "operation:w6-s1",
        "request_id": "request:w6-s1:1",
        "attempt_number": 1,
        "attempt_id": "attempt:w6-s1:1",
        "agent": agent,
        "work_kind": "implementation",
        "source_context": AgentSourceContext(LINEAGE, "revision:accepted-1"),
        "requested_capabilities": ("bounded-source-evidence",),
        "context_refs": (AgentEvidenceReference(EvidenceKind.SOURCE, "source:accepted-1", LINEAGE),),
        "created_at": NOW,
        "deadline_at": NOW + timedelta(minutes=10),
    }
    values.update(changes)
    return AgentTaskRequest.create(**values)


def result(adapter=None):
    adapter = adapter or ReferenceCheckpointAdapter()
    bound = task(adapter.describe())
    return bound, asyncio.run(adapter.invoke(bound))


def test_exact_task_identity_and_authority_boundary():
    adapter = ReferenceCheckpointAdapter()
    bound = task(adapter.describe())
    b = bound.binding
    assert (b.project_id, b.run_id, b.work_specification_id) == (PROJECT, RUN, SPEC)
    assert (b.work_specification_revision, b.work_specification_digest) == (3, SPEC_DIGEST)
    assert b.acceptance_ids == ("AC-01", "AC-02", "AC-03")
    assert b.source_context == AgentSourceContext(LINEAGE, "revision:accepted-1")
    assert b.agent_identity_digest == adapter.describe().digest
    assert bound.as_dict()["capabilities_are_authority"] is False


@pytest.mark.parametrize("change", [
    {"project_id": "bad"},
    {"attempt_number": 0},
    {"acceptance_ids": ("AC-01", "AC-01")},
    {"acceptance_ids": ("",)},
    {"work_specification_digest": "bad"},
    {"deadline_at": NOW},
])
def test_task_rejects_malformed_contract(change):
    with pytest.raises(AgentProtocolError):
        task(ReferenceCheckpointAdapter().describe(), **change)


def test_agent_declarations_are_bounded_evidence_only():
    agent = ReferenceCheckpointAdapter().describe()
    assert agent.as_dict()["grants_authority"] is False
    assert agent.as_dict()["contains_credentials"] is False
    with pytest.raises(AgentProtocolError):
        AgentIdentity("bad agent", "1", "adapter", "1", "reference", ("implementation",))
    with pytest.raises(AgentProtocolError):
        task(agent, requested_capabilities=("unregistered-shell",))


def test_reference_adapters_normalize_different_internal_shapes():
    outputs = []
    for adapter in (ReferenceCheckpointAdapter(), ReferenceTimeoutAdapter()):
        bound = task(adapter.describe())
        output = asyncio.run(adapter.invoke(bound))
        assert output.status is AgentLifecycleStatus.COMPLETED
        safe = json.loads(safe_json(output))
        assert safe["contains_provider_payload"] is False
        assert not {"raw_provider_payload", "provider_request", "provider_response"} & safe.keys()
        outputs.append(output)
    assert outputs[0].claimed_acceptance_ids == outputs[1].claimed_acceptance_ids
    assert outputs[0].changed_paths == outputs[1].changed_paths
    assert [m.metric for m in outputs[0].metrics] == [m.metric for m in outputs[1].metrics]


@pytest.mark.parametrize(("change", "reason"), [
    ({"project_id": "44444444-4444-4444-8444-444444444444"}, AdmissionReason.PROJECT_MISMATCH),
    ({"run_id": "55555555-5555-4555-8555-555555555555"}, AdmissionReason.RUN_MISMATCH),
    ({"work_specification_revision": 4}, AdmissionReason.WORK_SPECIFICATION_MISMATCH),
    ({"acceptance_ids": ("AC-03", "AC-02", "AC-01")}, AdmissionReason.ACCEPTANCE_CONTRACT_MISMATCH),
    ({"operation_id": "operation:other"}, AdmissionReason.OPERATION_MISMATCH),
    ({"request_id": "request:other"}, AdmissionReason.REQUEST_MISMATCH),
    ({"attempt_id": "attempt:other"}, AdmissionReason.ATTEMPT_MISMATCH),
    ({"source_context": AgentSourceContext("c" * 64, "revision:accepted-1")}, AdmissionReason.SOURCE_CONTEXT_MISMATCH),
])
def test_result_admission_fails_closed_on_binding_mismatch(change, reason):
    bound, output = result()
    forged = replace(output, binding=replace(bound.binding, **change))
    decision = verify_result_admission(expected_task=bound, result=forged)
    assert not decision.admitted and decision.reason is reason
    assert decision.as_dict()["transitions_engineering_run"] is False
    assert decision.as_dict()["accepts_source_lineage"] is False


def test_agent_claims_are_evidence_and_agent_identity_mismatch_rejected():
    bound, output = result()
    assert output.as_dict()["claimed_acceptance_is_authoritative"] is False
    other = ReferenceTimeoutAdapter().describe()
    forged = replace(output, binding=replace(bound.binding, agent_identity_digest=other.digest), agent=other)
    decision = verify_result_admission(expected_task=bound, result=forged)
    assert not decision.admitted and decision.reason is AdmissionReason.AGENT_IDENTITY_MISMATCH


def test_duplicate_stale_competing_and_revoked_results_are_non_authoritative():
    bound, output = result()
    duplicate = verify_result_admission(
        expected_task=bound, result=output, accepted_terminal_digest=output.digest
    )
    assert not duplicate.admitted and duplicate.duplicate and duplicate.reason is AdmissionReason.DUPLICATE
    competing = replace(output, summary="different bounded terminal result")
    assert verify_result_admission(
        expected_task=bound, result=competing, accepted_terminal_digest=output.digest
    ).reason is AdmissionReason.COMPETING_TERMINAL_RESULT
    assert verify_result_admission(
        expected_task=bound, result=output, current_attempt_number=2
    ).reason is AdmissionReason.STALE_ATTEMPT
    assert verify_result_admission(
        expected_task=bound, result=output, revoked=True
    ).reason is AdmissionReason.REVOKED


def test_checkpoint_recovery_and_revocation_preserve_worker_authority():
    adapter = ReferenceCheckpointAdapter(recover_once=True)
    bound = task(adapter.describe())
    output = asyncio.run(adapter.invoke(bound))
    assert output.status is AgentLifecycleStatus.RECOVERABLE_FAILURE and output.checkpoint
    checkpoint = output.checkpoint
    assert verify_checkpoint_admission(expected_task=bound, checkpoint=checkpoint).admitted
    assert asyncio.run(adapter.resume(bound, checkpoint)).status is AgentLifecycleStatus.COMPLETED
    assert verify_checkpoint_admission(
        expected_task=bound, checkpoint=checkpoint, current_attempt_number=2
    ).reason is AdmissionReason.STALE_ATTEMPT
    assert verify_checkpoint_admission(
        expected_task=bound, checkpoint=checkpoint, revoked=True
    ).reason is AdmissionReason.REVOKED


def test_timeout_cancellation_unknown_failure_and_unsupported_cancel_are_explicit():
    timeout_adapter = ReferenceTimeoutAdapter(timeout=True)
    bound = task(timeout_adapter.describe())
    assert asyncio.run(timeout_adapter.invoke(bound)).status is AgentLifecycleStatus.TIMEOUT
    cancelled = asyncio.run(timeout_adapter.cancel(bound))
    assert cancelled.status is AgentLifecycleStatus.CANCELLED
    assert verify_result_admission(expected_task=bound, result=cancelled, revoked=True).admitted

    unknown = ReferenceTimeoutAdapter(unknown_failure=True)
    failed = asyncio.run(unknown.invoke(task(unknown.describe())))
    assert (failed.status, failed.reason_code) == (
        AgentLifecycleStatus.TERMINAL_FAILURE, "UNKNOWN_PROVIDER_FAILURE"
    )
    unsupported = ReferenceCheckpointAdapter()
    rejected = asyncio.run(unsupported.cancel(task(unsupported.describe())))
    assert (rejected.status, rejected.reason_code) == (
        AgentLifecycleStatus.REJECTED, "CANCELLATION_UNSUPPORTED"
    )


def test_usage_metrics_preserve_provenance_missingness_and_finite_values():
    observed = MetricObservation(
        MetricName.COST, MetricAvailability.OBSERVED, "reference-adapter",
        value=0.25, unit="currency", currency="USD",
        provenance_kind=MetricProvenanceKind.ESTIMATE, provenance_ref="estimate:price-table-v1",
    )
    assert observed.as_dict()["provenance_kind"] == "ESTIMATE"
    missing = MetricObservation(
        MetricName.INPUT_TOKENS, MetricAvailability.UNAVAILABLE, "reference-adapter"
    )
    assert missing.value is None
    with pytest.raises(AgentProtocolError):
        MetricObservation(
            MetricName.COST, MetricAvailability.UNAVAILABLE, "reference-adapter",
            value=0, unit="currency", currency="USD",
        )
    with pytest.raises(AgentProtocolError):
        MetricObservation(
            MetricName.DURATION, MetricAvailability.OBSERVED, "reference-adapter",
            value=float("nan"), unit="seconds",
            provenance_kind=MetricProvenanceKind.PARALLAX, provenance_ref="observation:bad",
        )


def test_safe_serialization_is_deterministic_private_and_non_authoritative():
    _, output = result()
    first = safe_json(output)
    assert first == safe_json(output)
    parsed = json.loads(first)
    for key in (
        "grants_authority", "contains_credentials", "contains_hidden_reasoning",
        "contains_provider_payload", "accepts_source_lineage", "performs_validation",
        "transitions_engineering_run",
    ):
        assert parsed[key] is False
    assert not {
        "raw_provider_payload", "provider_request", "provider_response", "prompt",
        "hidden_reasoning_payload",
    } & parsed.keys()
    lowered = first.lower()
    for token in ("sk-", "bearer ", "authorization:", "password=", "token=", "http://", "https://"):
        assert token not in lowered


@pytest.mark.parametrize("unsafe", [
    "Authorization: Bearer secret-value",
    "provider said https://example.com/raw",
])
def test_summary_rejects_secret_or_url_content(unsafe):
    _, output = result()
    with pytest.raises(AgentProtocolError):
        replace(output, summary=unsafe)


@pytest.mark.parametrize("unsafe", [
    "../secret.txt", "/etc/passwd", ".env", ".env.local",
    "config/secrets", "config/secrets.toml", "config/credentials.json",
])
def test_changed_paths_reject_traversal_and_sensitive_targets(unsafe):
    _, output = result()
    with pytest.raises(AgentProtocolError):
        replace(output, changed_paths=(unsafe,))


def test_adapter_protocol_has_no_generic_authority_operations():
    public = {name for name in AgentAdapter.__dict__ if not name.startswith("_")}
    assert public == {"describe", "invoke", "cancel", "resume"}


def test_safe_json_and_references_fail_closed_on_untrusted_shapes():
    class FakeEvidence:
        def as_dict(self):
            return {"access_token": "secret"}

    with pytest.raises(AgentProtocolError):
        safe_json(FakeEvidence())  # type: ignore[arg-type]
    for unsafe in (
        "https:example.com", "credential:provider-key", "secret:runtime", "access_token:opaque"
    ):
        with pytest.raises(AgentProtocolError):
            AgentEvidenceReference(EvidenceKind.ARTIFACT, unsafe)
