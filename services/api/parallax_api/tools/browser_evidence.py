from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from .contracts import ToolActionPolicy, ToolAuthorityRequest, ToolCapability, ToolConsequence
from .registry import ToolCapabilityRegistry


_MAX_OBSERVATIONS = 64
_MAX_OBSERVATION_TEXT = 240
_MAX_ASSERTION_TEXT = 160
_MAX_SCREENSHOT_BYTES = 12_000_000
_MAX_ACTIONS = 20
_MAX_TIMEOUT_MS = 30_000
_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SECRET_RE = re.compile(
    r"(?i)(authorization|cookie|set-cookie|api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|credential)\s*[:=]\s*[^\s,;]{4,}"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{4,}")
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


class BrowserEvidenceError(ValueError):
    """Fail-closed safe-browser contract error."""


class BrowserPolicyDenied(BrowserEvidenceError):
    pass


class BrowserAdapterError(RuntimeError):
    pass


class BrowserAdapterTimeout(BrowserAdapterError):
    pass


class BrowserAction(StrEnum):
    NAVIGATE = "navigate"
    INSPECT = "inspect"
    ASSERT = "assert"
    SCREENSHOT = "screenshot"


class BrowserAssertionKind(StrEnum):
    TEXT_PRESENT = "text_present"
    ROLE_PRESENT = "role_present"
    URL_EQUALS = "url_equals"


class BrowserOutcome(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    POLICY_DENIED = "POLICY_DENIED"
    BROWSER_ERROR = "BROWSER_ERROR"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True, slots=True)
class BrowserSessionLimits:
    max_actions: int = 12
    timeout_ms: int = 15_000
    max_observations: int = 32
    max_observation_text: int = 200
    max_screenshot_bytes: int = 8_000_000

    def __post_init__(self) -> None:
        if not 1 <= self.max_actions <= _MAX_ACTIONS:
            raise BrowserEvidenceError("max_actions is outside the protected bound")
        if not 1 <= self.timeout_ms <= _MAX_TIMEOUT_MS:
            raise BrowserEvidenceError("timeout_ms is outside the protected bound")
        if not 1 <= self.max_observations <= _MAX_OBSERVATIONS:
            raise BrowserEvidenceError("max_observations is outside the protected bound")
        if not 1 <= self.max_observation_text <= _MAX_OBSERVATION_TEXT:
            raise BrowserEvidenceError("max_observation_text is outside the protected bound")
        if not 1 <= self.max_screenshot_bytes <= _MAX_SCREENSHOT_BYTES:
            raise BrowserEvidenceError("max_screenshot_bytes is outside the protected bound")


@dataclass(frozen=True, slots=True)
class BrowserTarget:
    target_id: str
    project_id: str
    run_id: str
    url: str
    source_lineage_ref: str | None = None
    preview_deployment_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_id", _reference(self.target_id, "target_id"))
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        object.__setattr__(self, "url", _https_url(self.url, "url"))
        if self.source_lineage_ref is not None and _LINEAGE_RE.fullmatch(self.source_lineage_ref) is None:
            raise BrowserEvidenceError("source_lineage_ref must be an exact protected lineage identity")
        if self.preview_deployment_id is not None:
            object.__setattr__(
                self,
                "preview_deployment_id",
                _reference(self.preview_deployment_id, "preview_deployment_id"),
            )

    @property
    def origin(self) -> str:
        return _origin(self.url)

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "url": self.url,
            "source_lineage_ref": self.source_lineage_ref,
            "preview_deployment_id": self.preview_deployment_id,
        }


class BrowserTargetCatalog:
    """Immutable server-owned admitted target catalog."""

    def __init__(self, targets: tuple[BrowserTarget, ...]):
        if not targets:
            raise BrowserEvidenceError("browser target catalog cannot be empty")
        by_id: dict[str, BrowserTarget] = {}
        for target in targets:
            if not isinstance(target, BrowserTarget):
                raise BrowserEvidenceError("target catalog requires BrowserTarget values")
            if target.target_id in by_id:
                raise BrowserEvidenceError("browser target_id values must be unique")
            by_id[target.target_id] = target
        self._targets = tuple(targets)
        self._by_id = by_id

    @property
    def targets(self) -> tuple[BrowserTarget, ...]:
        return self._targets

    def resolve(self, target_id: str, *, project_id: str, run_id: str) -> BrowserTarget:
        target = self._by_id.get(target_id)
        if target is None:
            raise BrowserPolicyDenied("browser target is not server-admitted")
        if target.project_id != project_id or target.run_id != run_id:
            raise BrowserPolicyDenied("browser target belongs to a different Project or run")
        return target


@dataclass(frozen=True, slots=True)
class BrowserAssertion:
    kind: BrowserAssertionKind
    expected: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "kind", BrowserAssertionKind(self.kind))
        except ValueError as exc:
            raise BrowserEvidenceError("assertion kind is outside the allowlist") from exc
        object.__setattr__(self, "expected", _safe_text(self.expected, "expected", _MAX_ASSERTION_TEXT))


@dataclass(frozen=True, slots=True)
class BrowserEvidenceRequest:
    request_id: str
    capability_id: str
    project_id: str
    run_id: str
    actor_ref: str
    target_id: str
    action: BrowserAction
    assertion: BrowserAssertion | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _reference(self.request_id, "request_id"))
        object.__setattr__(self, "capability_id", _reference(self.capability_id, "capability_id"))
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        object.__setattr__(self, "actor_ref", _reference(self.actor_ref, "actor_ref"))
        object.__setattr__(self, "target_id", _reference(self.target_id, "target_id"))
        try:
            action = self.action if isinstance(self.action, BrowserAction) else BrowserAction(self.action)
        except ValueError as exc:
            raise BrowserEvidenceError("browser action is outside the registered v1 vocabulary") from exc
        object.__setattr__(self, "action", action)
        if action is BrowserAction.ASSERT:
            if not isinstance(self.assertion, BrowserAssertion):
                raise BrowserEvidenceError("assert action requires a declarative BrowserAssertion")
        elif self.assertion is not None:
            raise BrowserEvidenceError("assertion is only valid for the assert action")


@dataclass(frozen=True, slots=True)
class BrowserAdapterResult:
    final_url: str
    observations: tuple[str, ...] = ()
    assertion_passed: bool | None = None
    screenshot_bytes: bytes | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "final_url", _https_url(self.final_url, "final_url"))
        if not isinstance(self.observations, tuple):
            raise BrowserEvidenceError("observations must be a bounded tuple")
        if self.assertion_passed is not None and not isinstance(self.assertion_passed, bool):
            raise BrowserEvidenceError("assertion_passed must be bool or None")
        if self.screenshot_bytes is not None and not isinstance(self.screenshot_bytes, bytes):
            raise BrowserEvidenceError("screenshot_bytes must be bytes or None")
        for field_name, value in (("viewport_width", self.viewport_width), ("viewport_height", self.viewport_height)):
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 10_000):
                raise BrowserEvidenceError(f"{field_name} is outside the protected bound")


class PlaywrightBrowserAdapter(Protocol):
    """Typed adapter seam; deliberately exposes no evaluate/cookies/headers/raw-network API."""

    def navigate(self, url: str, *, timeout_ms: int) -> BrowserAdapterResult: ...

    def inspect(self, *, timeout_ms: int, max_items: int) -> BrowserAdapterResult: ...

    def assert_condition(self, assertion: BrowserAssertion, *, timeout_ms: int) -> BrowserAdapterResult: ...

    def screenshot(self, *, timeout_ms: int) -> BrowserAdapterResult: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class BrowserEvidenceRecord:
    request_id: str
    project_id: str
    run_id: str
    target_id: str
    target_digest: str
    action: BrowserAction
    outcome: BrowserOutcome
    final_url: str | None
    observations: tuple[str, ...]
    assertion_passed: bool | None
    screenshot_digest: str | None
    screenshot_size: int | None
    viewport_width: int | None
    viewport_height: int | None
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _reference(self.request_id, "request_id"))
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        object.__setattr__(self, "target_id", _reference(self.target_id, "target_id"))
        if not re.fullmatch(r"[0-9a-f]{64}", self.target_digest):
            raise BrowserEvidenceError("target_digest must be sha256")
        object.__setattr__(self, "action", BrowserAction(self.action))
        object.__setattr__(self, "outcome", BrowserOutcome(self.outcome))
        if self.final_url is not None:
            object.__setattr__(self, "final_url", _https_url(self.final_url, "final_url"))
        if self.screenshot_digest is not None and not re.fullmatch(r"[0-9a-f]{64}", self.screenshot_digest):
            raise BrowserEvidenceError("screenshot_digest must be sha256")
        object.__setattr__(self, "reason_code", _reference(self.reason_code, "reason_code"))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "browser_evidence_version": 1,
            "request_id": self.request_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "target_id": self.target_id,
            "target_digest": self.target_digest,
            "action": self.action.value,
            "outcome": self.outcome.value,
            "final_url": self.final_url,
            "observations": list(self.observations),
            "assertion_passed": self.assertion_passed,
            "screenshot_digest": self.screenshot_digest,
            "screenshot_size": self.screenshot_size,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "reason_code": self.reason_code,
            "contains_screenshot_bytes": False,
            "contains_full_dom": False,
            "contains_credentials": False,
            "contains_cookies": False,
            "contains_authorization_headers": False,
            "contains_server_environment": False,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
            "grants_arbitrary_network": False,
            "executes_arbitrary_javascript": False,
            "performs_destructive_action": False,
            "grants_provider_authority": False,
            "performs_merge": False,
            "performs_production_deployment": False,
            "completes_review": False,
        }


class BrowserEvidenceSession:
    """Ephemeral Project-bound executor for already-authorized read-only browser evidence."""

    def __init__(
        self,
        *,
        registry: ToolCapabilityRegistry,
        catalog: BrowserTargetCatalog,
        adapter: PlaywrightBrowserAdapter,
        project_id: str,
        run_id: str,
        limits: BrowserSessionLimits | None = None,
    ) -> None:
        if not isinstance(registry, ToolCapabilityRegistry):
            raise BrowserEvidenceError("registry must be ToolCapabilityRegistry")
        if not isinstance(catalog, BrowserTargetCatalog):
            raise BrowserEvidenceError("catalog must be BrowserTargetCatalog")
        self.registry = registry
        self.catalog = catalog
        self.adapter = adapter
        self.project_id = _uuid(project_id, "project_id")
        self.run_id = _uuid(run_id, "run_id")
        self.limits = limits or BrowserSessionLimits()
        self._actions = 0
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def __enter__(self) -> "BrowserEvidenceSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self.adapter.close()

    def execute(self, request: BrowserEvidenceRequest) -> BrowserEvidenceRecord:
        if self._closed:
            raise BrowserEvidenceError("browser evidence session is closed")
        if request.project_id != self.project_id or request.run_id != self.run_id:
            return self._denied(request, "SESSION_CONTEXT_MISMATCH")
        if self._actions >= self.limits.max_actions:
            return self._denied(request, "ACTION_LIMIT_EXCEEDED")
        self._actions += 1

        authority = self.registry.authorize(
            ToolAuthorityRequest(
                request_id=request.request_id,
                capability_id=request.capability_id,
                project_ref=request.project_id,
                tool="browser_evidence",
                action=request.action.value,
                actor_ref=request.actor_ref,
            )
        )
        if not authority.allowed:
            return self._denied(request, f"AUTHORITY_{authority.deny_reason.value}")
        if authority.consequence is not ToolConsequence.READ:
            return self._denied(request, "NON_READ_CAPABILITY_DENIED")

        try:
            target = self.catalog.resolve(
                request.target_id,
                project_id=request.project_id,
                run_id=request.run_id,
            )
        except BrowserPolicyDenied:
            return self._denied(request, "TARGET_NOT_ADMITTED")

        try:
            if request.action is BrowserAction.NAVIGATE:
                raw = self.adapter.navigate(target.url, timeout_ms=self.limits.timeout_ms)
            elif request.action is BrowserAction.INSPECT:
                raw = self.adapter.inspect(
                    timeout_ms=self.limits.timeout_ms,
                    max_items=self.limits.max_observations,
                )
            elif request.action is BrowserAction.ASSERT:
                assert request.assertion is not None
                raw = self.adapter.assert_condition(request.assertion, timeout_ms=self.limits.timeout_ms)
            elif request.action is BrowserAction.SCREENSHOT:
                raw = self.adapter.screenshot(timeout_ms=self.limits.timeout_ms)
            else:  # pragma: no cover - enum construction prevents this
                return self._denied(request, "ACTION_NOT_REGISTERED")
            return self._admit_result(request, target, raw)
        except BrowserAdapterTimeout:
            return self._failure(request, target, BrowserOutcome.TIMEOUT, "BROWSER_TIMEOUT")
        except BrowserAdapterError:
            return self._failure(request, target, BrowserOutcome.BROWSER_ERROR, "BROWSER_ERROR")

    def _admit_result(
        self,
        request: BrowserEvidenceRequest,
        target: BrowserTarget,
        raw: BrowserAdapterResult,
    ) -> BrowserEvidenceRecord:
        if not isinstance(raw, BrowserAdapterResult):
            raise BrowserEvidenceError("browser adapter returned an invalid result contract")
        if _origin(raw.final_url) != target.origin:
            return self._denied(request, "REDIRECT_ORIGIN_NOT_ADMITTED", target=target)
        observations = tuple(
            _safe_observation(item, self.limits.max_observation_text)
            for item in raw.observations[: self.limits.max_observations]
        )
        screenshot_digest: str | None = None
        screenshot_size: int | None = None
        if raw.screenshot_bytes is not None:
            screenshot_size = len(raw.screenshot_bytes)
            if screenshot_size > self.limits.max_screenshot_bytes:
                return self._failure(request, target, BrowserOutcome.BROWSER_ERROR, "SCREENSHOT_TOO_LARGE")
            screenshot_digest = sha256(raw.screenshot_bytes).hexdigest()
        return BrowserEvidenceRecord(
            request_id=request.request_id,
            project_id=request.project_id,
            run_id=request.run_id,
            target_id=target.target_id,
            target_digest=target.digest,
            action=request.action,
            outcome=BrowserOutcome.SUCCEEDED,
            final_url=raw.final_url,
            observations=observations,
            assertion_passed=raw.assertion_passed,
            screenshot_digest=screenshot_digest,
            screenshot_size=screenshot_size,
            viewport_width=raw.viewport_width,
            viewport_height=raw.viewport_height,
            reason_code="SUCCEEDED",
        )

    def _denied(
        self,
        request: BrowserEvidenceRequest,
        reason: str,
        *,
        target: BrowserTarget | None = None,
    ) -> BrowserEvidenceRecord:
        return BrowserEvidenceRecord(
            request_id=request.request_id,
            project_id=request.project_id,
            run_id=request.run_id,
            target_id=request.target_id,
            target_digest=target.digest if target else "0" * 64,
            action=request.action,
            outcome=BrowserOutcome.POLICY_DENIED,
            final_url=None,
            observations=(),
            assertion_passed=None,
            screenshot_digest=None,
            screenshot_size=None,
            viewport_width=None,
            viewport_height=None,
            reason_code=reason,
        )

    def _failure(
        self,
        request: BrowserEvidenceRequest,
        target: BrowserTarget,
        outcome: BrowserOutcome,
        reason: str,
    ) -> BrowserEvidenceRecord:
        return BrowserEvidenceRecord(
            request_id=request.request_id,
            project_id=request.project_id,
            run_id=request.run_id,
            target_id=target.target_id,
            target_digest=target.digest,
            action=request.action,
            outcome=outcome,
            final_url=None,
            observations=(),
            assertion_passed=None,
            screenshot_digest=None,
            screenshot_size=None,
            viewport_width=None,
            viewport_height=None,
            reason_code=reason,
        )


def build_browser_evidence_capability(*, project_id: str) -> ToolCapability:
    project = _uuid(project_id, "project_id")
    return ToolCapability(
        capability_id="browser-evidence-v1",
        project_ref=project,
        tool="browser_evidence",
        actions=tuple(
            ToolActionPolicy(action=action.value, consequence=ToolConsequence.READ)
            for action in BrowserAction
        ),
        enabled=True,
    )


def safe_browser_evidence_json(record: BrowserEvidenceRecord) -> str:
    if not isinstance(record, BrowserEvidenceRecord):
        raise BrowserEvidenceError("record must be BrowserEvidenceRecord")
    return json.dumps(record.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = f":{parsed.port}" if parsed.port is not None and parsed.port != 443 else ""
    return f"https://{host}{port}"


def _https_url(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) > 2_000:
        raise BrowserEvidenceError(f"{field} is invalid or unbounded")
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise BrowserEvidenceError(f"{field} must use an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise BrowserEvidenceError(f"{field} cannot contain userinfo")
    if parsed.fragment:
        raise BrowserEvidenceError(f"{field} cannot contain a fragment")
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        raise BrowserEvidenceError(f"{field} cannot target loopback in the protected browser layer")
    netloc = hostname
    if parsed.port is not None and parsed.port != 443:
        netloc += f":{parsed.port}"
    return urlunsplit(("https", netloc, parsed.path or "/", parsed.query, ""))


def _reference(value: str, field: str) -> str:
    if not isinstance(value, str) or _REF_RE.fullmatch(value) is None:
        raise BrowserEvidenceError(f"{field} must be a bounded opaque identifier")
    return value


def _uuid(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise BrowserEvidenceError(f"{field} must be a canonical UUID")
    try:
        parsed = str(UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise BrowserEvidenceError(f"{field} must be a canonical UUID") from exc
    if parsed != value:
        raise BrowserEvidenceError(f"{field} must use canonical lowercase UUID form")
    return parsed


def _safe_text(value: str, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise BrowserEvidenceError(f"{field} must be text")
    candidate = value.strip()
    if not candidate or len(candidate) > limit or "\x00" in candidate:
        raise BrowserEvidenceError(f"{field} is empty or unbounded")
    if _SECRET_RE.search(candidate) or _BEARER_RE.search(candidate) or _PRIVATE_KEY_RE.search(candidate):
        raise BrowserEvidenceError(f"{field} appears to contain credential material")
    return candidate


def _safe_observation(value: str, limit: int) -> str:
    try:
        return _safe_text(value, "browser observation", limit)
    except BrowserEvidenceError as exc:
        if "credential material" in str(exc):
            return "[REDACTED_SENSITIVE_OBSERVATION]"
        raise


def _digest(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()
