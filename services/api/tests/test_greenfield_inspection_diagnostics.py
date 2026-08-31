from __future__ import annotations

import logging

from parallax_api.code.greenfield_composition import (
    _log_greenfield_repository_inspection_failure,
    _provider_result_code,
)
from parallax_api.tools.contracts import (
    ToolAuditRecord,
    ToolConsequence,
    ToolExecutionResult,
    ToolOutcome,
)
from parallax_api.tools.providers import (
    ProviderActionEvidence,
    ProviderActionFailed,
    ProviderActionState,
)


PROJECT = "11111111-1111-4111-8111-111111111111"


def _provider_failure(code: str) -> ProviderActionFailed:
    execution = ToolExecutionResult(succeeded=False, result_code=code)
    audit = ToolAuditRecord(
        request_id="request:greenfield-diagnostic",
        capability_id="cap:greenfield-diagnostic",
        project_ref=PROJECT,
        tool="github",
        action="repository.inspect",
        actor_ref="actor:parallax-runtime",
        consequence=ToolConsequence.READ,
        authority_allowed=True,
        outcome=ToolOutcome.FAILED,
        deny_reason=None,
        approval_id=None,
        request_digest="a" * 64,
        result_digest=execution.digest,
        result_code=code,
        result_identity=None,
    )
    evidence = ProviderActionEvidence(
        provider="github",
        action="repository.inspect",
        state=ProviderActionState.FAILED,
        project_ref=PROJECT,
        repository_identity_digest="b" * 64,
        result_status=code,
    )
    return ProviderActionFailed(evidence=evidence, audit=audit)


def test_protected_provider_result_code_is_logged_without_raw_exception(caplog) -> None:
    failure = _provider_failure("CREDENTIAL_SCOPE_MISMATCH")
    failure.__cause__ = RuntimeError("raw-provider-secret-token")

    with caplog.at_level(logging.WARNING, logger="parallax_api.code.greenfield_composition"):
        result = _log_greenfield_repository_inspection_failure(failure)

    assert result == "CREDENTIAL_SCOPE_MISMATCH"
    assert _provider_result_code(failure) == "CREDENTIAL_SCOPE_MISMATCH"
    assert caplog.messages == [
        "greenfield_repository_inspection_failed result_code=CREDENTIAL_SCOPE_MISMATCH"
    ]
    assert "raw-provider-secret-token" not in caplog.text


def test_unclassified_failure_uses_fixed_server_owned_fallback(caplog) -> None:
    raw = RuntimeError("external-body-with-sensitive-material")

    with caplog.at_level(logging.WARNING, logger="parallax_api.code.greenfield_composition"):
        result = _log_greenfield_repository_inspection_failure(raw)

    assert result == "UNCLASSIFIED_PROVIDER_FAILURE"
    assert caplog.messages == [
        "greenfield_repository_inspection_failed result_code=UNCLASSIFIED_PROVIDER_FAILURE"
    ]
    assert "external-body-with-sensitive-material" not in caplog.text


def test_authorization_required_remains_a_normalized_protected_code(caplog) -> None:
    failure = _provider_failure("REPOSITORY_AUTHORIZATION_REQUIRED")

    with caplog.at_level(logging.WARNING, logger="parallax_api.code.greenfield_composition"):
        result = _log_greenfield_repository_inspection_failure(failure)

    assert result == "REPOSITORY_AUTHORIZATION_REQUIRED"
    assert caplog.messages == [
        "greenfield_repository_inspection_failed result_code=REPOSITORY_AUTHORIZATION_REQUIRED"
    ]
