from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Protocol
from urllib.parse import urlsplit

from ..code.source_delivery_composition import DeliveryRecordStore, VerifiedDeliveryError, VerifiedDeliveryResult
from ..models import EngineeringRun
from ..tools.providers import VercelPreviewStatus


MAX_ACTIONS = 64
MAX_VIEWPORTS = 8
MAX_SCREENSHOTS = 8
MAX_EVIDENCE_ITEMS = 64
MAX_TEXT = 500
MAX_REF = 240
MAX_TIMEOUT_MS = 60_000
NETWORK_POLICY_EXACT_PREVIEW = "DENY_ALL_EXCEPT_EXACT_PREVIEW_HOST"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_SECRET_RE = re.compile(
    r"(?i)(bearer\s+\S+|(?:api[_ -]?key|secret|token|authorization|cookie|password)\s*[:=]\s*\S+)"
)
_HIDDEN_REASONING = (
    "chain_of_thought",
    "chain-of-thought",
    "scratchpad",
    "hidden_reasoning",
    "hidden-reasoning",
    "internal_reasoning",
    "internal-reasoning",
)


class BrowserValidationError(RuntimeError):
    pass


def _bounded(value: str, *, field: str, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        raise BrowserValidationError(f"{field} must be text")
    candidate = value.strip()
    if not candidate or len(candidate) > limit:
        raise BrowserValidationError(f"{field} exceeds protected bound")
    lowered = candidate.casefold()
    if _SECRET_RE.search(candidate):
        raise BrowserValidationError(f"{field} contains secret-bearing material")
    if any(marker in lowered for marker in _HIDDEN_REASONING):
        raise BrowserValidationError(f"{field} contains hidden-reasoning material")
    return candidate


def _identifier(value: str, *, field: str) -> str:
    candidate = _bounded(value, field=field, limit=120)
    if not _ID_RE.fullmatch(candidate):
        raise BrowserValidationError(f"{field} is not a bounded identifier")
    return candidate


def _digest(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise BrowserValidationError(f"{field} is not a canonical sha256 digest")
    return value


def _lineage(value: str) -> str:
    if not isinstance(value, str) or not _LINEAGE_RE.fullmatch(value):
        raise BrowserValidationError("source lineage is not canonical")
    return value


def _relative_path(value: str, *, field: str) -> str:
    candidate = _bounded(value, field=field, limit=240)
    parsed = urlsplit(candidate)
    if (
        not candidate.startswith("/")
        or candidate.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or any(part == ".." for part in parsed.path.split("/"))
    ):
        raise BrowserValidationError(f"{field} must be a bounded relative path without query or fragment")
    return parsed.path or "/"


def _preview_origin(value: str) -> tuple[str, str]:
    candidate = _bounded(value, field="preview_url", limit=500)
    parsed = urlsplit(candidate)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or not host.endswith(".vercel.app")
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise BrowserValidationError("persisted Preview URL is outside the protected HTTPS Vercel origin contract")
    return f"https://{host}", host


@dataclass(frozen=True, slots=True)
class BrowserValidationTarget:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    lineage_id: str
    content_digest: str
    preview_deployment_id: str
    preview_status: str
    preview_origin: str
    preview_host: str


class BrowserTargetResolver:
    """Reconstruct browser authority only from canonical Run + durable SOURCE_DELIVERY facts."""

    def __init__(self, records: DeliveryRecordStore) -> None:
        self.records = records

    def resolve(self, run: EngineeringRun, *, lineage_id: str) -> BrowserValidationTarget:
        if not isinstance(run, EngineeringRun):
            raise TypeError("run must be EngineeringRun")
        canonical_lineage = _lineage(lineage_id)
        if not run.project_id:
            raise BrowserValidationError("browser validation requires a Project-bound Engineering Run")
        if not run.work_specification_id or run.work_specification_revision is None or not run.work_specification_digest:
            raise BrowserValidationError("browser validation requires an approved Work Specification binding")
        work_spec_digest = _digest(run.work_specification_digest, field="work_specification_digest")
        if run.work_specification_revision < 1:
            raise BrowserValidationError("Work Specification revision is invalid")

        payload = self.records.load(run_id=run.id, lineage_id=canonical_lineage)
        if payload is None:
            raise BrowserValidationError("durable SOURCE_DELIVERY evidence is unavailable")
        try:
            delivery = VerifiedDeliveryResult.from_record(payload, replayed=True)
        except VerifiedDeliveryError as exc:
            raise BrowserValidationError("durable SOURCE_DELIVERY evidence failed protected validation") from exc
        if delivery.project_id != run.project_id or delivery.run_id != run.id or delivery.lineage_id != canonical_lineage:
            raise BrowserValidationError("durable Preview provenance does not match canonical Project/run/lineage")
        if delivery.preview_status != VercelPreviewStatus.READY.value or delivery.preview_url is None:
            raise BrowserValidationError("durable Preview is not READY with a safe URL")
        origin, host = _preview_origin(delivery.preview_url)
        _digest(delivery.content_digest, field="content_digest")
        _identifier(delivery.preview_deployment_id, field="preview_deployment_id")
        return BrowserValidationTarget(
            project_id=run.project_id,
            run_id=run.id,
            work_specification_id=run.work_specification_id,
            work_specification_revision=run.work_specification_revision,
            work_specification_digest=work_spec_digest,
            lineage_id=canonical_lineage,
            content_digest=delivery.content_digest,
            preview_deployment_id=delivery.preview_deployment_id,
            preview_status=delivery.preview_status,
            preview_origin=origin,
            preview_host=host,
        )


class SemanticTargetKind(StrEnum):
    ROLE = "ROLE"
    LABEL = "LABEL"
    TEST_ID = "TEST_ID"
    TEXT = "TEXT"


@dataclass(frozen=True, slots=True)
class SemanticTarget:
    kind: SemanticTargetKind
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SemanticTargetKind):
            raise TypeError("semantic target kind is invalid")
        object.__setattr__(self, "value", _bounded(self.value, field="semantic_target", limit=200))

    @property
    def ref(self) -> str:
        return f"{self.kind.value.lower()}:{self.value}"


class BrowserActionKind(StrEnum):
    NAVIGATE = "NAVIGATE"
    WAIT_FOR = "WAIT_FOR"
    ASSERT_VISIBLE = "ASSERT_VISIBLE"
    ASSERT_ABSENT = "ASSERT_ABSENT"
    CLICK = "CLICK"
    FILL = "FILL"
    SELECT = "SELECT"
    ASSERT_PATH = "ASSERT_PATH"
    ASSERT_LAYOUT = "ASSERT_LAYOUT"
    SCREENSHOT = "SCREENSHOT"


@dataclass(frozen=True, slots=True)
class BrowserAction:
    kind: BrowserActionKind
    path: str | None = None
    target: SemanticTarget | None = None
    value: str | None = None
    checkpoint: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, BrowserActionKind):
            raise TypeError("browser action kind is invalid")
        path_kinds = {BrowserActionKind.NAVIGATE, BrowserActionKind.ASSERT_PATH}
        target_kinds = {
            BrowserActionKind.WAIT_FOR,
            BrowserActionKind.ASSERT_VISIBLE,
            BrowserActionKind.ASSERT_ABSENT,
            BrowserActionKind.CLICK,
            BrowserActionKind.FILL,
            BrowserActionKind.SELECT,
            BrowserActionKind.ASSERT_LAYOUT,
        }
        value_kinds = {BrowserActionKind.FILL, BrowserActionKind.SELECT}
        if self.kind in path_kinds:
            if self.path is None:
                raise BrowserValidationError("path action requires a relative path")
            object.__setattr__(self, "path", _relative_path(self.path, field="action.path"))
        elif self.path is not None:
            raise BrowserValidationError("path is not allowed for this browser action")
        if self.kind in target_kinds:
            if not isinstance(self.target, SemanticTarget):
                raise BrowserValidationError("semantic browser action requires a registered target")
        elif self.target is not None:
            raise BrowserValidationError("semantic target is not allowed for this browser action")
        if self.kind in value_kinds:
            if self.value is None:
                raise BrowserValidationError("browser interaction requires a bounded fixture value")
            object.__setattr__(self, "value", _bounded(self.value, field="action.value", limit=200))
        elif self.value is not None:
            raise BrowserValidationError("fixture value is not allowed for this browser action")
        if self.kind is BrowserActionKind.SCREENSHOT:
            if self.checkpoint is None:
                raise BrowserValidationError("screenshot action requires a checkpoint")
            object.__setattr__(self, "checkpoint", _identifier(self.checkpoint, field="checkpoint"))
        elif self.checkpoint is not None:
            raise BrowserValidationError("checkpoint is not allowed for this browser action")


@dataclass(frozen=True, slots=True)
class BrowserViewport:
    viewport_id: str
    width: int
    height: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "viewport_id", _identifier(self.viewport_id, field="viewport_id"))
        if not 240 <= self.width <= 3840 or not 240 <= self.height <= 3840:
            raise BrowserValidationError("viewport dimensions exceed protected bounds")


DEFAULT_VIEWPORTS = (
    BrowserViewport("mobile-390", 390, 844),
    BrowserViewport("tablet-768", 768, 1024),
    BrowserViewport("desktop-1440", 1440, 1000),
)


@dataclass(frozen=True, slots=True)
class BrowserWorkflow:
    workflow_id: str
    version: int
    viewport_ids: tuple[str, ...]
    actions: tuple[BrowserAction, ...]
    timeout_ms: int = 30_000

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_id", _identifier(self.workflow_id, field="workflow_id"))
        if self.version < 1:
            raise BrowserValidationError("workflow version must be positive")
        if not self.viewport_ids or len(self.viewport_ids) > MAX_VIEWPORTS:
            raise BrowserValidationError("workflow viewport set exceeds protected bound")
        if len(set(self.viewport_ids)) != len(self.viewport_ids):
            raise BrowserValidationError("workflow viewport identities must be unique")
        for viewport_id in self.viewport_ids:
            _identifier(viewport_id, field="workflow.viewport_id")
        if not self.actions or len(self.actions) > MAX_ACTIONS:
            raise BrowserValidationError("workflow action set exceeds protected bound")
        if not all(isinstance(action, BrowserAction) for action in self.actions):
            raise BrowserValidationError("workflow actions must be protected typed actions")
        screenshot_count = sum(action.kind is BrowserActionKind.SCREENSHOT for action in self.actions)
        if screenshot_count < 1 or screenshot_count > MAX_SCREENSHOTS:
            raise BrowserValidationError("workflow requires a bounded screenshot set")
        if not 1_000 <= self.timeout_ms <= MAX_TIMEOUT_MS:
            raise BrowserValidationError("workflow timeout exceeds protected bound")

    @property
    def screenshot_checkpoints(self) -> tuple[str, ...]:
        return tuple(action.checkpoint for action in self.actions if action.kind is BrowserActionKind.SCREENSHOT and action.checkpoint)


class BrowserWorkflowRegistry:
    def __init__(
        self,
        workflows: tuple[BrowserWorkflow, ...],
        viewports: tuple[BrowserViewport, ...] = DEFAULT_VIEWPORTS,
    ) -> None:
        if not workflows:
            raise ValueError("at least one protected browser workflow is required")
        self._workflows = {(item.workflow_id, item.version): item for item in workflows}
        if len(self._workflows) != len(workflows):
            raise ValueError("browser workflow identities must be unique")
        self._viewports = {item.viewport_id: item for item in viewports}
        if len(self._viewports) != len(viewports):
            raise ValueError("browser viewport identities must be unique")
        for workflow in workflows:
            if any(viewport_id not in self._viewports for viewport_id in workflow.viewport_ids):
                raise BrowserValidationError("workflow references an unregistered viewport")

    def resolve(self, workflow_id: str, version: int) -> BrowserWorkflow:
        key = (_identifier(workflow_id, field="workflow_id"), version)
        try:
            return self._workflows[key]
        except KeyError as exc:
            raise BrowserValidationError("requested browser workflow is not server-registered") from exc

    def viewport(self, viewport_id: str) -> BrowserViewport:
        try:
            return self._viewports[viewport_id]
        except KeyError as exc:
            raise BrowserValidationError("requested viewport is not server-registered") from exc


@dataclass(frozen=True, slots=True)
class BrowserExecutionRequest:
    target: BrowserValidationTarget
    workflow: BrowserWorkflow
    viewport: BrowserViewport
    allowed_host: str
    network_policy: str = NETWORK_POLICY_EXACT_PREVIEW

    def __post_init__(self) -> None:
        if self.allowed_host != self.target.preview_host:
            raise BrowserValidationError("browser network authority must equal the exact Preview host")
        if self.network_policy != NETWORK_POLICY_EXACT_PREVIEW:
            raise BrowserValidationError("browser executor must use the protected exact-host network policy")
        if self.viewport.viewport_id not in self.workflow.viewport_ids:
            raise BrowserValidationError("viewport is outside the registered workflow")


@dataclass(frozen=True, slots=True)
class AssertionEvidence:
    code: str
    passed: bool
    target_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _identifier(self.code, field="assertion.code"))
        object.__setattr__(self, "target_ref", _bounded(self.target_ref, field="assertion.target_ref", limit=240))
        if not isinstance(self.passed, bool):
            raise TypeError("assertion passed must be bool")


class AccessibilityImpact(StrEnum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SERIOUS = "SERIOUS"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class AccessibilityFinding:
    rule_id: str
    impact: AccessibilityImpact
    locator: str
    count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _identifier(self.rule_id, field="a11y.rule_id"))
        object.__setattr__(self, "locator", _bounded(self.locator, field="a11y.locator", limit=240))
        if not isinstance(self.impact, AccessibilityImpact):
            raise TypeError("accessibility impact is invalid")
        if not 1 <= self.count <= 1000:
            raise BrowserValidationError("accessibility finding count exceeds protected bound")


@dataclass(frozen=True, slots=True)
class ConsoleFinding:
    kind: str
    excerpt: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _identifier(self.kind, field="console.kind"))
        object.__setattr__(self, "excerpt", _bounded(self.excerpt, field="console.excerpt", limit=MAX_TEXT))


@dataclass(frozen=True, slots=True)
class NetworkFinding:
    method: str
    host: str
    path: str
    status: int | None = None
    failure_class: str | None = None
    unexpected_external: bool = False
    required: bool = False

    def __post_init__(self) -> None:
        method = _identifier(self.method.upper(), field="network.method")
        host = _bounded(self.host.lower().rstrip("."), field="network.host", limit=253)
        path = _relative_path(self.path, field="network.path")
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "host", host)
        object.__setattr__(self, "path", path)
        if self.status is not None and not 100 <= self.status <= 599:
            raise BrowserValidationError("network status is invalid")
        if self.failure_class is not None:
            object.__setattr__(self, "failure_class", _identifier(self.failure_class, field="network.failure_class"))
        if not isinstance(self.unexpected_external, bool) or not isinstance(self.required, bool):
            raise TypeError("network flags must be bool")


@dataclass(frozen=True, slots=True)
class LayoutFinding:
    code: str
    locator: str
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _identifier(self.code, field="layout.code"))
        object.__setattr__(self, "locator", _bounded(self.locator, field="layout.locator", limit=240))
        for value in (self.x, self.y, self.width, self.height):
            if not isinstance(value, int) or abs(value) > 100_000:
                raise BrowserValidationError("layout geometry exceeds protected bound")


@dataclass(frozen=True, slots=True)
class ScreenshotArtifact:
    project_id: str
    run_id: str
    work_specification_digest: str
    lineage_id: str
    preview_deployment_id: str
    workflow_id: str
    workflow_version: int
    viewport_id: str
    checkpoint: str
    artifact_ref: str
    sha256: str
    width: int
    height: int

    def __post_init__(self) -> None:
        _digest(self.work_specification_digest, field="screenshot.work_specification_digest")
        _lineage(self.lineage_id)
        _identifier(self.workflow_id, field="screenshot.workflow_id")
        _identifier(self.viewport_id, field="screenshot.viewport_id")
        _identifier(self.checkpoint, field="screenshot.checkpoint")
        _bounded(self.artifact_ref, field="screenshot.artifact_ref", limit=MAX_REF)
        _digest(self.sha256, field="screenshot.sha256")
        if not 1 <= self.width <= 10_000 or not 1 <= self.height <= 10_000:
            raise BrowserValidationError("screenshot dimensions are invalid")


@dataclass(frozen=True, slots=True)
class BrowserExecutionEvidence:
    project_id: str
    run_id: str
    lineage_id: str
    preview_deployment_id: str
    workflow_id: str
    workflow_version: int
    viewport_id: str
    network_policy: str
    assertions: tuple[AssertionEvidence, ...] = ()
    accessibility: tuple[AccessibilityFinding, ...] = ()
    console: tuple[ConsoleFinding, ...] = ()
    network: tuple[NetworkFinding, ...] = ()
    layout: tuple[LayoutFinding, ...] = ()
    screenshots: tuple[ScreenshotArtifact, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("assertions", "accessibility", "console", "network", "layout"):
            if len(getattr(self, field_name)) > MAX_EVIDENCE_ITEMS:
                raise BrowserValidationError(f"{field_name} evidence exceeds protected bound")
        if len(self.screenshots) > MAX_SCREENSHOTS:
            raise BrowserValidationError("screenshot evidence exceeds protected bound")


class BrowserExecutor(Protocol):
    def execute(self, request: BrowserExecutionRequest) -> BrowserExecutionEvidence: ...


def validate_execution_evidence(request: BrowserExecutionRequest, evidence: BrowserExecutionEvidence) -> None:
    target = request.target
    if (
        evidence.project_id != target.project_id
        or evidence.run_id != target.run_id
        or evidence.lineage_id != target.lineage_id
        or evidence.preview_deployment_id != target.preview_deployment_id
        or evidence.workflow_id != request.workflow.workflow_id
        or evidence.workflow_version != request.workflow.version
        or evidence.viewport_id != request.viewport.viewport_id
        or evidence.network_policy != NETWORK_POLICY_EXACT_PREVIEW
    ):
        raise BrowserValidationError("browser execution evidence provenance mismatch")
    if any(item.host != target.preview_host and not item.unexpected_external for item in evidence.network):
        raise BrowserValidationError("off-origin request evidence must be classified as unexpected external traffic")
    expected = set(request.workflow.screenshot_checkpoints)
    actual = {item.checkpoint for item in evidence.screenshots}
    if actual != expected or len(actual) != len(evidence.screenshots):
        raise BrowserValidationError("browser screenshot evidence does not cover the registered checkpoints exactly")
    for screenshot in evidence.screenshots:
        if (
            screenshot.project_id != target.project_id
            or screenshot.run_id != target.run_id
            or screenshot.work_specification_digest != target.work_specification_digest
            or screenshot.lineage_id != target.lineage_id
            or screenshot.preview_deployment_id != target.preview_deployment_id
            or screenshot.workflow_id != request.workflow.workflow_id
            or screenshot.workflow_version != request.workflow.version
            or screenshot.viewport_id != request.viewport.viewport_id
            or screenshot.width != request.viewport.width
            or screenshot.height != request.viewport.height
        ):
            raise BrowserValidationError("screenshot artifact provenance mismatch")


def deterministic_defects(evidence: BrowserExecutionEvidence) -> tuple[str, ...]:
    defects: list[str] = []
    defects.extend(f"ASSERTION:{item.code}" for item in evidence.assertions if not item.passed)
    defects.extend(
        f"ACCESSIBILITY:{item.rule_id}"
        for item in evidence.accessibility
        if item.impact in {AccessibilityImpact.SERIOUS, AccessibilityImpact.CRITICAL}
    )
    defects.extend(f"CONSOLE:{item.kind}" for item in evidence.console)
    defects.extend(
        f"NETWORK:{item.failure_class or ('EXTERNAL_HOST' if item.unexpected_external else 'REQUIRED_REQUEST_FAILED')}"
        for item in evidence.network
        if item.unexpected_external or item.failure_class is not None or (item.required and (item.status is None or item.status >= 400))
    )
    defects.extend(f"LAYOUT:{item.code}" for item in evidence.layout)
    return tuple(dict.fromkeys(defects))


@dataclass(frozen=True, slots=True)
class ScreenshotBaseline:
    project_id: str
    workflow_id: str
    workflow_version: int
    viewport_id: str
    checkpoint: str
    design_state_id: str
    artifact_ref: str
    sha256: str
    max_difference_ratio: float

    def __post_init__(self) -> None:
        _identifier(self.project_id, field="baseline.project_id")
        _identifier(self.workflow_id, field="baseline.workflow_id")
        _identifier(self.viewport_id, field="baseline.viewport_id")
        _identifier(self.checkpoint, field="baseline.checkpoint")
        _identifier(self.design_state_id, field="baseline.design_state_id")
        _bounded(self.artifact_ref, field="baseline.artifact_ref", limit=MAX_REF)
        _digest(self.sha256, field="baseline.sha256")
        if self.workflow_version < 1 or not 0.0 <= self.max_difference_ratio <= 1.0:
            raise BrowserValidationError("screenshot baseline policy is invalid")


class ScreenshotBaselineRegistry:
    def __init__(self, baselines: tuple[ScreenshotBaseline, ...]) -> None:
        self._items = {
            (item.project_id, item.workflow_id, item.workflow_version, item.viewport_id, item.checkpoint): item
            for item in baselines
        }
        if len(self._items) != len(baselines):
            raise ValueError("screenshot baseline identities must be unique")

    def resolve(self, screenshot: ScreenshotArtifact) -> ScreenshotBaseline:
        key = (
            screenshot.project_id,
            screenshot.workflow_id,
            screenshot.workflow_version,
            screenshot.viewport_id,
            screenshot.checkpoint,
        )
        try:
            return self._items[key]
        except KeyError as exc:
            raise BrowserValidationError("no provenance-compatible screenshot baseline is registered") from exc


@dataclass(frozen=True, slots=True)
class ScreenshotDifference:
    candidate_sha256: str
    baseline_sha256: str
    difference_ratio: float
    diff_artifact_ref: str | None = None

    def __post_init__(self) -> None:
        _digest(self.candidate_sha256, field="comparison.candidate_sha256")
        _digest(self.baseline_sha256, field="comparison.baseline_sha256")
        if not 0.0 <= self.difference_ratio <= 1.0:
            raise BrowserValidationError("screenshot difference ratio is invalid")
        if self.diff_artifact_ref is not None:
            _bounded(self.diff_artifact_ref, field="comparison.diff_artifact_ref", limit=MAX_REF)


class ScreenshotComparator(Protocol):
    def compare(self, candidate: ScreenshotArtifact, baseline: ScreenshotBaseline) -> ScreenshotDifference: ...


def validate_screenshot_difference(
    candidate: ScreenshotArtifact,
    baseline: ScreenshotBaseline,
    difference: ScreenshotDifference,
) -> bool:
    if candidate.project_id != baseline.project_id:
        raise BrowserValidationError("screenshot baseline belongs to a different Project")
    if (
        candidate.workflow_id != baseline.workflow_id
        or candidate.workflow_version != baseline.workflow_version
        or candidate.viewport_id != baseline.viewport_id
        or candidate.checkpoint != baseline.checkpoint
    ):
        raise BrowserValidationError("screenshot baseline provenance mismatch")
    if difference.candidate_sha256 != candidate.sha256 or difference.baseline_sha256 != baseline.sha256:
        raise BrowserValidationError("screenshot comparator returned mismatched artifact identity")
    return difference.difference_ratio <= baseline.max_difference_ratio


class VisualReviewOutcome(StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class VisualFinding:
    category: str
    region: str
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", _identifier(self.category, field="visual.category"))
        object.__setattr__(self, "region", _bounded(self.region, field="visual.region", limit=160))
        object.__setattr__(self, "summary", _bounded(self.summary, field="visual.summary", limit=MAX_TEXT))


@dataclass(frozen=True, slots=True)
class VisualReviewResult:
    outcome: VisualReviewOutcome
    findings: tuple[VisualFinding, ...]
    confidence: float

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, VisualReviewOutcome):
            raise TypeError("visual review outcome is invalid")
        if len(self.findings) > 24 or not all(isinstance(item, VisualFinding) for item in self.findings):
            raise BrowserValidationError("multimodal findings exceed protected bound")
        if not 0.0 <= self.confidence <= 1.0:
            raise BrowserValidationError("multimodal confidence is invalid")


class MultimodalReviewer(Protocol):
    def review(
        self,
        screenshot: ScreenshotArtifact,
        *,
        context: tuple[str, ...],
    ) -> VisualReviewResult: ...


class ProtectedValidationStatus(StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class ProtectedBrowserValidationResult:
    project_id: str
    run_id: str
    work_specification_digest: str
    lineage_id: str
    preview_deployment_id: str
    workflow_id: str
    workflow_version: int
    status: ProtectedValidationStatus
    deterministic_defects: tuple[str, ...]
    screenshot_differences: tuple[ScreenshotDifference, ...]
    visual_reviews: tuple[VisualReviewResult, ...]
    executions: tuple[BrowserExecutionEvidence, ...]

    def __post_init__(self) -> None:
        if len(self.deterministic_defects) > MAX_EVIDENCE_ITEMS:
            raise BrowserValidationError("normalized defect evidence exceeds protected bound")


class ProtectedBrowserValidator:
    """Compose deterministic browser evidence, screenshot regression and secondary visual review."""

    def __init__(
        self,
        *,
        targets: BrowserTargetResolver,
        workflows: BrowserWorkflowRegistry,
        executor: BrowserExecutor,
        baselines: ScreenshotBaselineRegistry,
        comparator: ScreenshotComparator,
        reviewer: MultimodalReviewer,
    ) -> None:
        self.targets = targets
        self.workflows = workflows
        self.executor = executor
        self.baselines = baselines
        self.comparator = comparator
        self.reviewer = reviewer

    def validate(
        self,
        run: EngineeringRun,
        *,
        lineage_id: str,
        workflow_id: str,
        workflow_version: int,
    ) -> ProtectedBrowserValidationResult:
        target = self.targets.resolve(run, lineage_id=lineage_id)
        workflow = self.workflows.resolve(workflow_id, workflow_version)
        executions: list[BrowserExecutionEvidence] = []
        defects: list[str] = []
        screenshots: list[ScreenshotArtifact] = []

        for viewport_id in workflow.viewport_ids:
            viewport = self.workflows.viewport(viewport_id)
            request = BrowserExecutionRequest(
                target=target,
                workflow=workflow,
                viewport=viewport,
                allowed_host=target.preview_host,
            )
            evidence = self.executor.execute(request)
            validate_execution_evidence(request, evidence)
            executions.append(evidence)
            defects.extend(deterministic_defects(evidence))
            screenshots.extend(evidence.screenshots)

        if defects:
            return ProtectedBrowserValidationResult(
                project_id=target.project_id,
                run_id=target.run_id,
                work_specification_digest=target.work_specification_digest,
                lineage_id=target.lineage_id,
                preview_deployment_id=target.preview_deployment_id,
                workflow_id=workflow.workflow_id,
                workflow_version=workflow.version,
                status=ProtectedValidationStatus.FAIL,
                deterministic_defects=tuple(dict.fromkeys(defects)),
                screenshot_differences=(),
                visual_reviews=(),
                executions=tuple(executions),
            )

        differences: list[ScreenshotDifference] = []
        regression_defects: list[str] = []
        for screenshot in screenshots:
            baseline = self.baselines.resolve(screenshot)
            difference = self.comparator.compare(screenshot, baseline)
            differences.append(difference)
            if not validate_screenshot_difference(screenshot, baseline, difference):
                regression_defects.append(f"SCREENSHOT_REGRESSION:{screenshot.viewport_id}:{screenshot.checkpoint}")

        if regression_defects:
            return ProtectedBrowserValidationResult(
                project_id=target.project_id,
                run_id=target.run_id,
                work_specification_digest=target.work_specification_digest,
                lineage_id=target.lineage_id,
                preview_deployment_id=target.preview_deployment_id,
                workflow_id=workflow.workflow_id,
                workflow_version=workflow.version,
                status=ProtectedValidationStatus.FAIL,
                deterministic_defects=tuple(regression_defects),
                screenshot_differences=tuple(differences),
                visual_reviews=(),
                executions=tuple(executions),
            )

        context = (
            f"workflow:{workflow.workflow_id}:v{workflow.version}",
            "deterministic:PASS",
            "screenshot-regression:PASS",
        )
        reviews = tuple(self.reviewer.review(screenshot, context=context) for screenshot in screenshots)
        if any(review.outcome is VisualReviewOutcome.FAIL for review in reviews):
            status = ProtectedValidationStatus.FAIL
        elif any(review.outcome is VisualReviewOutcome.REVIEW for review in reviews):
            status = ProtectedValidationStatus.REVIEW
        else:
            status = ProtectedValidationStatus.PASS
        return ProtectedBrowserValidationResult(
            project_id=target.project_id,
            run_id=target.run_id,
            work_specification_digest=target.work_specification_digest,
            lineage_id=target.lineage_id,
            preview_deployment_id=target.preview_deployment_id,
            workflow_id=workflow.workflow_id,
            workflow_version=workflow.version,
            status=status,
            deterministic_defects=(),
            screenshot_differences=tuple(differences),
            visual_reviews=reviews,
            executions=tuple(executions),
        )


def reference_app_workflow() -> BrowserWorkflow:
    """Permanent protected fixture used by Wave 3 reference-app proof."""

    heading = SemanticTarget(SemanticTargetKind.ROLE, "heading:Parallax")
    root = SemanticTarget(SemanticTargetKind.TEST_ID, "parallax-root")
    return BrowserWorkflow(
        workflow_id="reference-app-primary",
        version=1,
        viewport_ids=("mobile-390", "desktop-1440"),
        actions=(
            BrowserAction(BrowserActionKind.NAVIGATE, path="/"),
            BrowserAction(BrowserActionKind.WAIT_FOR, target=root),
            BrowserAction(BrowserActionKind.ASSERT_VISIBLE, target=heading),
            BrowserAction(BrowserActionKind.ASSERT_LAYOUT, target=root),
            BrowserAction(BrowserActionKind.SCREENSHOT, checkpoint="primary"),
        ),
        timeout_ms=30_000,
    )


__all__ = [
    "AccessibilityFinding",
    "AccessibilityImpact",
    "AssertionEvidence",
    "BrowserAction",
    "BrowserActionKind",
    "BrowserExecutionEvidence",
    "BrowserExecutionRequest",
    "BrowserExecutor",
    "BrowserTargetResolver",
    "BrowserValidationError",
    "BrowserValidationTarget",
    "BrowserViewport",
    "BrowserWorkflow",
    "BrowserWorkflowRegistry",
    "ConsoleFinding",
    "DEFAULT_VIEWPORTS",
    "LayoutFinding",
    "MultimodalReviewer",
    "NETWORK_POLICY_EXACT_PREVIEW",
    "NetworkFinding",
    "ProtectedBrowserValidationResult",
    "ProtectedBrowserValidator",
    "ProtectedValidationStatus",
    "ScreenshotArtifact",
    "ScreenshotBaseline",
    "ScreenshotBaselineRegistry",
    "ScreenshotComparator",
    "ScreenshotDifference",
    "SemanticTarget",
    "SemanticTargetKind",
    "VisualFinding",
    "VisualReviewOutcome",
    "VisualReviewResult",
    "deterministic_defects",
    "reference_app_workflow",
    "validate_execution_evidence",
    "validate_screenshot_difference",
]
