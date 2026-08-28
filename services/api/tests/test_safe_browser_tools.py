from __future__ import annotations

import hashlib
import json

import pytest

from parallax_api.tools import (
    BrowserAction,
    BrowserAdapterError,
    BrowserAdapterResult,
    BrowserAdapterTimeout,
    BrowserAssertion,
    BrowserAssertionKind,
    BrowserEvidenceError,
    BrowserEvidenceRequest,
    BrowserOutcome,
    BrowserSessionLimits,
    BrowserTarget,
    BrowserTargetCatalog,
    ProtectedBrowserEvidenceSession,
    ToolCapabilityRegistry,
    ToolConsequence,
    build_browser_evidence_capability,
    safe_browser_evidence_json,
)


PROJECT = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT = "99999999-9999-4999-8999-999999999999"
RUN = "22222222-2222-4222-8222-222222222222"
OTHER_RUN = "88888888-8888-4888-8888-888888888888"
TARGET_URL = "https://preview.example.test/app"


class FakeAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.closed = False
        self.final_url = TARGET_URL
        self.observations: tuple[str, ...] = ("heading: Parallax",)
        self.assertion_passed = True
        self.screenshot_bytes = b"png-evidence"
        self.raise_timeout = False
        self.raise_error = False

    def _maybe_fail(self) -> None:
        if self.raise_timeout:
            raise BrowserAdapterTimeout("timeout detail must not serialize")
        if self.raise_error:
            raise BrowserAdapterError("provider/browser detail must not serialize")

    def navigate(self, url: str, *, timeout_ms: int) -> BrowserAdapterResult:
        self.calls.append(("navigate", url))
        self._maybe_fail()
        return BrowserAdapterResult(final_url=self.final_url)

    def inspect(self, *, timeout_ms: int, max_items: int) -> BrowserAdapterResult:
        self.calls.append(("inspect", max_items))
        self._maybe_fail()
        return BrowserAdapterResult(final_url=self.final_url, observations=self.observations)

    def assert_condition(self, assertion: BrowserAssertion, *, timeout_ms: int) -> BrowserAdapterResult:
        self.calls.append(("assert", assertion.kind.value))
        self._maybe_fail()
        return BrowserAdapterResult(
            final_url=self.final_url,
            assertion_passed=self.assertion_passed,
        )

    def screenshot(self, *, timeout_ms: int) -> BrowserAdapterResult:
        self.calls.append(("screenshot", timeout_ms))
        self._maybe_fail()
        return BrowserAdapterResult(
            final_url=self.final_url,
            screenshot_bytes=self.screenshot_bytes,
            viewport_width=1440,
            viewport_height=900,
        )

    def close(self) -> None:
        self.closed = True


def _target(*, project_id: str = PROJECT, run_id: str = RUN) -> BrowserTarget:
    return BrowserTarget(
        target_id="preview-primary",
        project_id=project_id,
        run_id=run_id,
        url=TARGET_URL,
        source_lineage_ref="src:" + "a" * 64,
        preview_deployment_id="dpl_preview_123",
    )


def _registry(project_id: str = PROJECT) -> ToolCapabilityRegistry:
    return ToolCapabilityRegistry((build_browser_evidence_capability(project_id=project_id),))


def _request(
    action: BrowserAction = BrowserAction.INSPECT,
    *,
    project_id: str = PROJECT,
    run_id: str = RUN,
    target_id: str = "preview-primary",
    capability_id: str = "browser-evidence-v1",
) -> BrowserEvidenceRequest:
    return BrowserEvidenceRequest(
        request_id=f"request-{action.value}",
        capability_id=capability_id,
        project_id=project_id,
        run_id=run_id,
        actor_ref="agent:safe-browser",
        target_id=target_id,
        action=action,
        assertion=(
            BrowserAssertion(kind=BrowserAssertionKind.TEXT_PRESENT, expected="Parallax")
            if action is BrowserAction.ASSERT
            else None
        ),
    )


def _session(
    adapter: FakeAdapter,
    *,
    protected_validation_passed: bool = True,
    limits: BrowserSessionLimits | None = None,
) -> ProtectedBrowserEvidenceSession:
    return ProtectedBrowserEvidenceSession(
        registry=_registry(),
        catalog=BrowserTargetCatalog((_target(),)),
        adapter=adapter,
        project_id=PROJECT,
        run_id=RUN,
        protected_validation_passed=protected_validation_passed,
        limits=limits,
    )


def test_registered_browser_v1_capability_is_read_only_and_bounded() -> None:
    capability = build_browser_evidence_capability(project_id=PROJECT)
    assert capability.project_ref == PROJECT
    assert capability.tool == "browser_evidence"
    assert {policy.action for policy in capability.actions} == {action.value for action in BrowserAction}
    assert all(policy.consequence is ToolConsequence.READ for policy in capability.actions)
    assert not any(policy.requires_human_approval for policy in capability.actions)
    assert "delete" not in {policy.action for policy in capability.actions}
    assert "submit" not in {policy.action for policy in capability.actions}
    assert "evaluate" not in {policy.action for policy in capability.actions}


def test_unknown_capability_or_action_is_denied_before_adapter_execution() -> None:
    adapter = FakeAdapter()
    with _session(adapter) as session:
        record = session.execute(_request(capability_id="browser-evidence-unknown"))
        assert record.outcome is BrowserOutcome.POLICY_DENIED
        assert record.reason_code == "AUTHORITY_UNKNOWN_CAPABILITY"
        assert adapter.calls == []

    with pytest.raises(BrowserEvidenceError, match="outside the registered v1 vocabulary"):
        BrowserEvidenceRequest(
            request_id="request-evaluate",
            capability_id="browser-evidence-v1",
            project_id=PROJECT,
            run_id=RUN,
            actor_ref="agent:safe-browser",
            target_id="preview-primary",
            action="evaluate",
        )


def test_target_contract_rejects_non_https_loopback_userinfo_and_fragments() -> None:
    for url in (
        "http://preview.example.test/app",
        "https://localhost/app",
        "https://127.0.0.1/app",
        "https://user:pass@preview.example.test/app",
        "https://preview.example.test/app#secret",
    ):
        with pytest.raises(BrowserEvidenceError):
            BrowserTarget(
                target_id="invalid-target",
                project_id=PROJECT,
                run_id=RUN,
                url=url,
            )


def test_cross_project_and_unadmitted_targets_fail_closed_without_browser_call() -> None:
    adapter = FakeAdapter()
    with _session(adapter) as session:
        foreign = session.execute(_request(project_id=OTHER_PROJECT))
        assert foreign.outcome is BrowserOutcome.POLICY_DENIED
        assert foreign.reason_code == "SESSION_CONTEXT_MISMATCH"
        missing = session.execute(_request(target_id="not-admitted"))
        assert missing.outcome is BrowserOutcome.POLICY_DENIED
        assert missing.reason_code == "TARGET_NOT_ADMITTED"
        assert adapter.calls == []


def test_off_origin_redirect_is_denied_and_not_admitted_as_success() -> None:
    adapter = FakeAdapter()
    adapter.final_url = "https://evil.example.test/redirected"
    with _session(adapter) as session:
        record = session.execute(_request(BrowserAction.NAVIGATE))
    assert record.outcome is BrowserOutcome.POLICY_DENIED
    assert record.reason_code == "REDIRECT_ORIGIN_NOT_ADMITTED"
    assert record.final_url is None


def test_protected_validation_failure_blocks_adapter_before_visual_evidence() -> None:
    adapter = FakeAdapter()
    with _session(adapter, protected_validation_passed=False) as session:
        record = session.execute(_request(BrowserAction.SCREENSHOT))
    assert record.outcome is BrowserOutcome.POLICY_DENIED
    assert record.reason_code == "PROTECTED_VALIDATION_FAILED"
    assert adapter.calls == []


def test_inspection_is_bounded_and_sensitive_observation_is_redacted() -> None:
    adapter = FakeAdapter()
    adapter.observations = (
        "heading: Dashboard",
        "Authorization: Bearer super-secret-token",
        "button: Continue",
        "ignored because max items",
    )
    limits = BrowserSessionLimits(max_observations=3)
    with _session(adapter, limits=limits) as session:
        record = session.execute(_request(BrowserAction.INSPECT))

    assert record.outcome is BrowserOutcome.SUCCEEDED
    assert record.observations == (
        "heading: Dashboard",
        "[REDACTED_SENSITIVE_OBSERVATION]",
        "button: Continue",
    )
    assert "super-secret-token" not in safe_browser_evidence_json(record)


def test_screenshot_serializes_digest_metadata_only_never_binary_payload() -> None:
    adapter = FakeAdapter()
    with _session(adapter) as session:
        record = session.execute(_request(BrowserAction.SCREENSHOT))
    payload = json.loads(safe_browser_evidence_json(record))

    assert record.outcome is BrowserOutcome.SUCCEEDED
    assert record.screenshot_digest == hashlib.sha256(b"png-evidence").hexdigest()
    assert record.screenshot_size == len(b"png-evidence")
    assert payload["contains_screenshot_bytes"] is False
    assert "png-evidence" not in safe_browser_evidence_json(record)


def test_oversized_screenshot_is_failure_not_success() -> None:
    adapter = FakeAdapter()
    adapter.screenshot_bytes = b"x" * 20
    limits = BrowserSessionLimits(max_screenshot_bytes=10)
    with _session(adapter, limits=limits) as session:
        record = session.execute(_request(BrowserAction.SCREENSHOT))
    assert record.outcome is BrowserOutcome.BROWSER_ERROR
    assert record.reason_code == "SCREENSHOT_TOO_LARGE"
    assert record.screenshot_digest is None


def test_browser_timeout_and_browser_error_are_distinct_bounded_outcomes() -> None:
    timeout_adapter = FakeAdapter()
    timeout_adapter.raise_timeout = True
    with _session(timeout_adapter) as session:
        timed_out = session.execute(_request(BrowserAction.INSPECT))
    assert timed_out.outcome is BrowserOutcome.TIMEOUT
    assert timed_out.reason_code == "BROWSER_TIMEOUT"

    error_adapter = FakeAdapter()
    error_adapter.raise_error = True
    with _session(error_adapter) as session:
        failed = session.execute(_request(BrowserAction.INSPECT))
    assert failed.outcome is BrowserOutcome.BROWSER_ERROR
    assert failed.reason_code == "BROWSER_ERROR"
    assert "provider/browser detail" not in safe_browser_evidence_json(failed)


def test_ephemeral_session_enforces_action_limit_and_always_closes_adapter() -> None:
    adapter = FakeAdapter()
    with _session(adapter, limits=BrowserSessionLimits(max_actions=1)) as session:
        first = session.execute(_request(BrowserAction.NAVIGATE))
        second = session.execute(_request(BrowserAction.INSPECT))
        assert first.outcome is BrowserOutcome.SUCCEEDED
        assert second.outcome is BrowserOutcome.POLICY_DENIED
        assert second.reason_code == "ACTION_LIMIT_EXCEEDED"
    assert adapter.closed is True
    with pytest.raises(BrowserEvidenceError, match="session is closed"):
        session.execute(_request(BrowserAction.INSPECT))


def test_safe_serialization_explicitly_grants_no_source_provider_network_or_review_authority() -> None:
    adapter = FakeAdapter()
    with _session(adapter) as session:
        record = session.execute(_request(BrowserAction.ASSERT))
    payload = json.loads(safe_browser_evidence_json(record))

    assert record.assertion_passed is True
    for field in (
        "contains_screenshot_bytes",
        "contains_full_dom",
        "contains_credentials",
        "contains_cookies",
        "contains_authorization_headers",
        "contains_server_environment",
        "accepts_source_lineage",
        "transitions_engineering_run",
        "grants_arbitrary_network",
        "executes_arbitrary_javascript",
        "performs_destructive_action",
        "grants_provider_authority",
        "performs_merge",
        "performs_production_deployment",
        "completes_review",
    ):
        assert payload[field] is False


def test_assertion_contract_is_declarative_and_bounded() -> None:
    assertion = BrowserAssertion(kind=BrowserAssertionKind.ROLE_PRESENT, expected="button")
    assert assertion.kind is BrowserAssertionKind.ROLE_PRESENT
    with pytest.raises(BrowserEvidenceError, match="assertion kind is outside the allowlist"):
        BrowserAssertion(kind="javascript", expected="document.cookie")
    with pytest.raises(BrowserEvidenceError, match="credential material"):
        BrowserAssertion(kind=BrowserAssertionKind.TEXT_PRESENT, expected="password=supersecret")
