from __future__ import annotations

from .browser_evidence import (
    BrowserEvidenceRecord,
    BrowserEvidenceRequest,
    BrowserEvidenceSession,
    BrowserOutcome,
    BrowserPolicyDenied,
    BrowserSessionLimits,
    BrowserTargetCatalog,
    PlaywrightBrowserAdapter,
)
from .registry import ToolCapabilityRegistry


class ProtectedBrowserEvidenceSession(BrowserEvidenceSession):
    """Public S4 composition that preserves deterministic validation precedence."""

    def __init__(
        self,
        *,
        registry: ToolCapabilityRegistry,
        catalog: BrowserTargetCatalog,
        adapter: PlaywrightBrowserAdapter,
        project_id: str,
        run_id: str,
        protected_validation_passed: bool,
        limits: BrowserSessionLimits | None = None,
    ) -> None:
        if not isinstance(protected_validation_passed, bool):
            raise TypeError("protected_validation_passed must be bool")
        super().__init__(
            registry=registry,
            catalog=catalog,
            adapter=adapter,
            project_id=project_id,
            run_id=run_id,
            limits=limits,
        )
        self._protected_validation_passed = protected_validation_passed

    def execute(self, request: BrowserEvidenceRequest) -> BrowserEvidenceRecord:
        if not self._protected_validation_passed:
            return BrowserEvidenceRecord(
                request_id=request.request_id,
                project_id=request.project_id,
                run_id=request.run_id,
                target_id=request.target_id,
                target_digest="0" * 64,
                action=request.action,
                outcome=BrowserOutcome.POLICY_DENIED,
                final_url=None,
                observations=(),
                assertion_passed=None,
                screenshot_digest=None,
                screenshot_size=None,
                viewport_width=None,
                viewport_height=None,
                reason_code="PROTECTED_VALIDATION_FAILED",
            )
        try:
            return super().execute(request)
        except BrowserPolicyDenied:
            return BrowserEvidenceRecord(
                request_id=request.request_id,
                project_id=request.project_id,
                run_id=request.run_id,
                target_id=request.target_id,
                target_digest="0" * 64,
                action=request.action,
                outcome=BrowserOutcome.POLICY_DENIED,
                final_url=None,
                observations=(),
                assertion_passed=None,
                screenshot_digest=None,
                screenshot_size=None,
                viewport_width=None,
                viewport_height=None,
                reason_code="NETWORK_OR_REDIRECT_NOT_ADMITTED",
            )
