from __future__ import annotations

from .contracts import (
    AuthorityDecision,
    ToolAuditRecord,
    ToolAuthorityRequest,
    ToolExecutionResult,
    ToolOutcome,
)


def audit_denied(
    request: ToolAuthorityRequest,
    decision: AuthorityDecision,
) -> ToolAuditRecord:
    if decision.allowed:
        raise ValueError("allowed authority decision cannot be recorded as denied")
    if decision.request_id != request.request_id:
        raise ValueError("decision does not belong to request")

    return ToolAuditRecord(
        request_id=request.request_id,
        capability_id=decision.capability_id,
        project_ref=request.project_ref,
        tool=request.tool,
        action=request.action,
        actor_ref=request.actor_ref,
        consequence=decision.consequence,
        authority_allowed=False,
        outcome=ToolOutcome.DENIED,
        deny_reason=decision.deny_reason,
        approval_id=decision.approval_id,
        request_digest=request.digest,
        result_digest=None,
        result_code=None,
        result_identity=None,
    )


def audit_tool_result(
    request: ToolAuthorityRequest,
    decision: AuthorityDecision,
    result: ToolExecutionResult,
) -> ToolAuditRecord:
    if not decision.allowed:
        raise ValueError("denied authority cannot produce execution result audit")
    if decision.request_id != request.request_id:
        raise ValueError("decision does not belong to request")
    if decision.capability_id != request.capability_id:
        raise ValueError("decision capability does not match request")

    return ToolAuditRecord(
        request_id=request.request_id,
        capability_id=decision.capability_id,
        project_ref=request.project_ref,
        tool=request.tool,
        action=request.action,
        actor_ref=request.actor_ref,
        consequence=decision.consequence,
        authority_allowed=True,
        outcome=ToolOutcome.SUCCEEDED if result.succeeded else ToolOutcome.FAILED,
        deny_reason=None,
        approval_id=decision.approval_id,
        request_digest=request.digest,
        result_digest=result.digest,
        result_code=result.result_code,
        result_identity=result.result_identity,
    )
