from __future__ import annotations

from dataclasses import fields, replace

import pytest

from parallax_api.tools import (
    AuthorityDenyReason,
    HumanApproval,
    ToolActionPolicy,
    ToolAuthorityRequest,
    ToolAuditRecord,
    ToolCapability,
    ToolCapabilityRegistry,
    ToolConsequence,
    ToolExecutionResult,
    ToolOutcome,
    audit_denied,
    audit_tool_result,
)


def capability(*, enabled: bool = True) -> ToolCapability:
    return ToolCapability(
        capability_id="cap-github-project-a",
        project_ref="project-a",
        tool="github",
        actions=(
            ToolActionPolicy(action="repository.read", consequence=ToolConsequence.READ),
            ToolActionPolicy(
                action="repository.write",
                consequence=ToolConsequence.MUTATE,
                requires_human_approval=True,
            ),
            ToolActionPolicy(
                action="deployment.promote",
                consequence=ToolConsequence.DESTRUCTIVE,
                requires_human_approval=True,
            ),
        ),
        enabled=enabled,
    )


def request(*, action: str = "repository.read", **changes: str) -> ToolAuthorityRequest:
    values = {
        "request_id": "req-1",
        "capability_id": "cap-github-project-a",
        "project_ref": "project-a",
        "tool": "github",
        "action": action,
        "actor_ref": "user-1",
    }
    values.update(changes)
    return ToolAuthorityRequest(**values)


def approval(value: ToolAuthorityRequest, **changes: str) -> HumanApproval:
    values = {
        "approval_id": "approval-1",
        "request_id": value.request_id,
        "capability_id": value.capability_id,
        "project_ref": value.project_ref,
        "tool": value.tool,
        "action": value.action,
        "approved_by": "owner-1",
    }
    values.update(changes)
    return HumanApproval(**values)


def test_registered_exact_read_capability_is_allowed_without_approval():
    decision = ToolCapabilityRegistry((capability(),)).authorize(request())

    assert decision.allowed is True
    assert decision.deny_reason is None
    assert decision.consequence is ToolConsequence.READ
    assert decision.approval_id is None


@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        (request(capability_id="unknown-cap"), AuthorityDenyReason.UNKNOWN_CAPABILITY),
        (request(project_ref="project-b"), AuthorityDenyReason.PROJECT_MISMATCH),
        (request(tool="vercel"), AuthorityDenyReason.TOOL_MISMATCH),
        (request(action="repository.delete"), AuthorityDenyReason.ACTION_NOT_ALLOWED),
    ],
)
def test_registry_fails_closed_for_unknown_or_mismatched_authority(
    candidate: ToolAuthorityRequest,
    reason: AuthorityDenyReason,
):
    decision = ToolCapabilityRegistry((capability(),)).authorize(candidate)

    assert decision.allowed is False
    assert decision.deny_reason is reason


def test_disabled_capability_is_denied():
    decision = ToolCapabilityRegistry((capability(enabled=False),)).authorize(request())

    assert decision.allowed is False
    assert decision.deny_reason is AuthorityDenyReason.CAPABILITY_DISABLED


def test_request_data_cannot_self_grant_an_unregistered_capability():
    unregistered = ToolCapability(
        capability_id="cap-model-claimed",
        project_ref="project-a",
        tool="github",
        actions=(ToolActionPolicy(action="repository.read", consequence=ToolConsequence.READ),),
    )
    candidate = request(capability_id=unregistered.capability_id)

    decision = ToolCapabilityRegistry((capability(),)).authorize(candidate)

    assert decision.allowed is False
    assert decision.deny_reason is AuthorityDenyReason.UNKNOWN_CAPABILITY


def test_approval_required_action_denies_missing_approval_and_accepts_exact_approval():
    registry = ToolCapabilityRegistry((capability(),))
    candidate = request(action="repository.write")

    missing = registry.authorize(candidate)
    allowed = registry.authorize(candidate, approval=approval(candidate))

    assert missing.allowed is False
    assert missing.deny_reason is AuthorityDenyReason.APPROVAL_REQUIRED
    assert allowed.allowed is True
    assert allowed.approval_id == "approval-1"
    assert allowed.consequence is ToolConsequence.MUTATE


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("request_id", "req-other"),
        ("capability_id", "cap-other"),
        ("project_ref", "project-other"),
        ("tool", "vercel"),
        ("action", "repository.read"),
    ],
)
def test_approval_cannot_be_replayed_for_a_different_authority_tuple(field: str, value: str):
    registry = ToolCapabilityRegistry((capability(),))
    candidate = request(action="repository.write")
    mismatched = approval(candidate, **{field: value})

    decision = registry.authorize(candidate, approval=mismatched)

    assert decision.allowed is False
    assert decision.deny_reason is AuthorityDenyReason.APPROVAL_MISMATCH


def test_destructive_action_requires_and_records_exact_human_approval():
    registry = ToolCapabilityRegistry((capability(),))
    candidate = request(action="deployment.promote")

    denied = registry.authorize(candidate)
    approved = registry.authorize(candidate, approval=approval(candidate))

    assert denied.deny_reason is AuthorityDenyReason.APPROVAL_REQUIRED
    assert approved.allowed is True
    assert approved.consequence is ToolConsequence.DESTRUCTIVE
    assert approved.approval_id == "approval-1"


def test_denied_and_failed_tool_outcomes_remain_truthful():
    registry = ToolCapabilityRegistry((capability(),))
    denied_request = request(project_ref="project-b")
    denied_decision = registry.authorize(denied_request)
    denied_audit = audit_denied(denied_request, denied_decision)

    assert denied_audit.outcome is ToolOutcome.DENIED
    assert denied_audit.authority_allowed is False
    assert denied_audit.result_digest is None

    with pytest.raises(ValueError, match="denied authority"):
        audit_tool_result(
            denied_request,
            denied_decision,
            ToolExecutionResult(succeeded=True, result_code="OK"),
        )

    allowed_request = request()
    allowed_decision = registry.authorize(allowed_request)
    failed = audit_tool_result(
        allowed_request,
        allowed_decision,
        ToolExecutionResult(
            succeeded=False,
            result_code="PROVIDER_UNAVAILABLE",
            result_identity="attempt-7",
        ),
    )
    succeeded = audit_tool_result(
        allowed_request,
        allowed_decision,
        ToolExecutionResult(
            succeeded=True,
            result_code="OK",
            result_identity="attempt-8",
        ),
    )

    assert failed.outcome is ToolOutcome.FAILED
    assert succeeded.outcome is ToolOutcome.SUCCEEDED
    assert failed.result_digest != succeeded.result_digest


def test_audit_contract_has_no_arbitrary_provider_content_fields():
    prohibited = {"payload", "raw_payload", "raw_error", "error_body", "headers", "body", "environment", "metadata"}
    assert prohibited.isdisjoint({item.name for item in fields(ToolAuditRecord)})


def test_decision_and_digests_are_deterministic():
    registry_a = ToolCapabilityRegistry((capability(),))
    registry_b = ToolCapabilityRegistry((capability(),))
    candidate_a = request()
    candidate_b = request()

    assert registry_a.authorize(candidate_a) == registry_b.authorize(candidate_b)
    assert candidate_a.digest == candidate_b.digest

    result_a = ToolExecutionResult(
        succeeded=False,
        result_code="PROVIDER_UNAVAILABLE",
        result_identity="attempt-1",
    )
    result_b = ToolExecutionResult(
        succeeded=False,
        result_code="PROVIDER_UNAVAILABLE",
        result_identity="attempt-1",
    )
    assert result_a.digest == result_b.digest


def test_registry_rejects_duplicate_capability_ids():
    first = capability()
    second = replace(first, project_ref="project-b")

    with pytest.raises(ValueError, match="duplicate capability_id"):
        ToolCapabilityRegistry((first, second))
