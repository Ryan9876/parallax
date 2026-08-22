from __future__ import annotations

from collections.abc import Iterable

from .contracts import (
    AuthorityDecision,
    AuthorityDenyReason,
    HumanApproval,
    ToolAuthorityRequest,
    ToolCapability,
)


class ToolCapabilityRegistry:
    """Immutable server-owned capability and approval authorization policy."""

    def __init__(
        self,
        capabilities: Iterable[ToolCapability],
        *,
        approvals: Iterable[HumanApproval] = (),
    ):
        ordered = tuple(capabilities)
        by_id: dict[str, ToolCapability] = {}
        for capability in ordered:
            if not isinstance(capability, ToolCapability):
                raise TypeError("registry entries must be ToolCapability values")
            if capability.capability_id in by_id:
                raise ValueError(f"duplicate capability_id: {capability.capability_id}")
            by_id[capability.capability_id] = capability

        ordered_approvals = tuple(approvals)
        approvals_by_id: dict[str, HumanApproval] = {}
        for approval in ordered_approvals:
            if not isinstance(approval, HumanApproval):
                raise TypeError("approval registry entries must be HumanApproval values")
            if approval.approval_id in approvals_by_id:
                raise ValueError(f"duplicate approval_id: {approval.approval_id}")
            approvals_by_id[approval.approval_id] = approval

        self._capabilities = ordered
        self._by_id = by_id
        self._approvals = ordered_approvals
        self._approvals_by_id = approvals_by_id

    @property
    def capabilities(self) -> tuple[ToolCapability, ...]:
        return self._capabilities

    @property
    def approvals(self) -> tuple[HumanApproval, ...]:
        return self._approvals

    @staticmethod
    def _deny(
        request: ToolAuthorityRequest,
        reason: AuthorityDenyReason,
        *,
        capability_id: str | None = None,
    ) -> AuthorityDecision:
        return AuthorityDecision(
            allowed=False,
            request_id=request.request_id,
            capability_id=capability_id,
            project_ref=request.project_ref,
            tool=request.tool,
            action=request.action,
            consequence=None,
            approval_id=None,
            deny_reason=reason,
        )

    def authorize(
        self,
        request: ToolAuthorityRequest,
        *,
        approval_id: str | None = None,
    ) -> AuthorityDecision:
        capability = self._by_id.get(request.capability_id)
        if capability is None:
            return self._deny(request, AuthorityDenyReason.UNKNOWN_CAPABILITY)

        if not capability.enabled:
            return self._deny(
                request,
                AuthorityDenyReason.CAPABILITY_DISABLED,
                capability_id=capability.capability_id,
            )

        if request.project_ref != capability.project_ref:
            return self._deny(
                request,
                AuthorityDenyReason.PROJECT_MISMATCH,
                capability_id=capability.capability_id,
            )

        if request.tool != capability.tool:
            return self._deny(
                request,
                AuthorityDenyReason.TOOL_MISMATCH,
                capability_id=capability.capability_id,
            )

        policy = capability.policy_for(request.action)
        if policy is None:
            return self._deny(
                request,
                AuthorityDenyReason.ACTION_NOT_ALLOWED,
                capability_id=capability.capability_id,
            )

        matched_approval_id: str | None = None
        if policy.requires_human_approval:
            if approval_id is None:
                return self._deny(
                    request,
                    AuthorityDenyReason.APPROVAL_REQUIRED,
                    capability_id=capability.capability_id,
                )
            approval = self._approvals_by_id.get(approval_id)
            if approval is None or not approval.matches(request):
                return self._deny(
                    request,
                    AuthorityDenyReason.APPROVAL_MISMATCH,
                    capability_id=capability.capability_id,
                )
            matched_approval_id = approval.approval_id

        return AuthorityDecision(
            allowed=True,
            request_id=request.request_id,
            capability_id=capability.capability_id,
            project_ref=request.project_ref,
            tool=request.tool,
            action=request.action,
            consequence=policy.consequence,
            approval_id=matched_approval_id,
            deny_reason=None,
        )
