from __future__ import annotations

from types import SimpleNamespace

from parallax_api.code.runtime_composition import _source_delivery_failure_evidence
from parallax_api.code.source_delivery_composition import VerifiedDeliveryError
from parallax_api.tools.contracts import ToolAuditRecord, ToolConsequence, ToolOutcome
from parallax_api.tools.providers import ProviderActionEvidence, ProviderActionFailed, ProviderActionState


def _provider_failure() -> ProviderActionFailed:
    evidence = ProviderActionEvidence(
        provider="github",
        action="branch.create",
        state=ProviderActionState.FAILED,
        project_ref="b1f6984d-dc64-4220-bd51-51f6f215d175",
        repository_identity_digest="1" * 64,
        source_revision="abc123",
        result_status="PROVIDER_AUTH_DENIED",
    )
    audit = ToolAuditRecord(
        request_id="request:delivery-test",
        capability_id="cap:github-delivery:b1f6984d-dc64-4220-bd51-51f6f215d175",
        project_ref="b1f6984d-dc64-4220-bd51-51f6f215d175",
        tool="github",
        action="branch.create",
        actor_ref="actor:runtime",
        consequence=ToolConsequence.MUTATE,
        authority_allowed=True,
        outcome=ToolOutcome.FAILED,
        deny_reason=None,
        approval_id=None,
        request_digest="2" * 64,
        result_digest=None,
        result_code="PROVIDER_AUTH_DENIED",
        result_identity=None,
    )
    return ProviderActionFailed(evidence=evidence, audit=audit)


def test_source_delivery_failure_evidence_preserves_only_bounded_provider_classification():
    outer = VerifiedDeliveryError("bounded wrapper")
    outer.__cause__ = _provider_failure()

    result = _source_delivery_failure_evidence(outer)

    assert result == {
        "error_class": "ProviderActionFailed",
        "provider": "github",
        "action": "branch.create",
        "result_code": "PROVIDER_AUTH_DENIED",
    }


def test_source_delivery_failure_evidence_never_exposes_exception_text_or_secret_attributes():
    error = VerifiedDeliveryError("token=super-secret provider payload")
    error.secret = "must-not-leak"  # type: ignore[attr-defined]
    error.__cause__ = RuntimeError("Authorization: Bearer secret-value")

    result = _source_delivery_failure_evidence(error)

    assert result == {"error_class": "VerifiedDeliveryError"}
    encoded = repr(result)
    assert "super-secret" not in encoded
    assert "Bearer" not in encoded
    assert "must-not-leak" not in encoded


def test_source_delivery_failure_evidence_handles_non_exception_defensively():
    assert _source_delivery_failure_evidence(SimpleNamespace()) == {"error_class": "UnknownDeliveryFailure"}
