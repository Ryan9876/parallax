from __future__ import annotations

import pytest

from parallax_api.tools import (
    BrowserAction,
    BrowserAdapterError,
    BrowserAssertion,
    BrowserEvidenceRequest,
    BrowserOutcome,
    BrowserPolicyDenied,
    BrowserTarget,
    BrowserTargetCatalog,
    ProtectedBrowserEvidenceSession,
    SyncPlaywrightBrowserAdapter,
    ToolCapabilityRegistry,
    build_browser_evidence_capability,
)


PROJECT = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"
TARGET_URL = "https://preview.example.test/app"


def test_concrete_playwright_adapter_has_no_generic_mutation_or_secret_surface() -> None:
    adapter = SyncPlaywrightBrowserAdapter()
    public = {name for name in dir(adapter) if not name.startswith("_")}
    assert {"navigate", "inspect", "assert_condition", "screenshot", "close"}.issubset(public)
    for forbidden in (
        "evaluate",
        "eval",
        "cookies",
        "headers",
        "request",
        "fetch",
        "submit",
        "click",
        "fill",
        "upload",
        "download",
        "delete",
    ):
        assert forbidden not in public
    adapter.close()
    assert adapter.closed is True
    adapter.close()


def test_concrete_adapter_requires_server_admitted_navigation_before_inspection() -> None:
    adapter = SyncPlaywrightBrowserAdapter()
    with pytest.raises(BrowserAdapterError, match="navigation must occur"):
        adapter.inspect(timeout_ms=100, max_items=5)
    adapter.close()


class _PolicyDenyAdapter:
    def navigate(self, url: str, *, timeout_ms: int):
        raise BrowserPolicyDenied("off-origin request blocked")

    def inspect(self, *, timeout_ms: int, max_items: int):
        raise BrowserPolicyDenied("off-origin request blocked")

    def assert_condition(self, assertion: BrowserAssertion, *, timeout_ms: int):
        raise BrowserPolicyDenied("off-origin request blocked")

    def screenshot(self, *, timeout_ms: int):
        raise BrowserPolicyDenied("off-origin request blocked")

    def close(self) -> None:
        return None


def test_protected_session_normalizes_concrete_network_policy_denial() -> None:
    registry = ToolCapabilityRegistry((build_browser_evidence_capability(project_id=PROJECT),))
    catalog = BrowserTargetCatalog(
        (
            BrowserTarget(
                target_id="preview-primary",
                project_id=PROJECT,
                run_id=RUN,
                url=TARGET_URL,
                source_lineage_ref="src:" + "a" * 64,
                preview_deployment_id="dpl_preview_123",
            ),
        )
    )
    request = BrowserEvidenceRequest(
        request_id="request-navigation-policy",
        capability_id="browser-evidence-v1",
        project_id=PROJECT,
        run_id=RUN,
        actor_ref="agent:safe-browser",
        target_id="preview-primary",
        action=BrowserAction.NAVIGATE,
    )
    with ProtectedBrowserEvidenceSession(
        registry=registry,
        catalog=catalog,
        adapter=_PolicyDenyAdapter(),
        project_id=PROJECT,
        run_id=RUN,
        protected_validation_passed=True,
    ) as session:
        record = session.execute(request)
    assert record.outcome is BrowserOutcome.POLICY_DENIED
    assert record.reason_code == "NETWORK_OR_REDIRECT_NOT_ADMITTED"
    assert record.final_url is None
