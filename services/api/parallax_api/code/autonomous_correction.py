from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath
import re
from typing import Callable, Protocol

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from ..models import EngineeringAttempt, EngineeringRun, utcnow
from ..repositories.engineering_runs import EngineeringRunRepository
from ..validation.browser import ProtectedBrowserValidationResult, VisualReviewOutcome
from .patching import SourcePatch
from .worker_recovery import WorkerCheckpoint, WorkerLease, WorkerLifecycleState
from .worker_service import WorkerRecoveryService


MAX_DEFECTS = 64
MAX_REFS = 16
MAX_REF_LENGTH = 240
MAX_CODE_LENGTH = 120
MAX_PATCHES = 16
MAX_PATCH_BYTES = 256_000
MAX_STATE_BYTES = 24_000
MAX_HISTORY = 24
MAX_REPEAT_KEYS = 24

_STATE_STAGE = "CORRECTION_STATE"
_STATE_STATUS = "RECORDED"
_STATE_PROGRAM = "autonomous-correction-v0.16.3"
_STATE_TOOL = "protected-correction-controller"
_STATE_KIND = "autonomous_correction_state"
_STATE_VERSION = 1

_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_.:-]{0,119}$")
_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,239}$")
_FORBIDDEN_REF_PREFIXES = (
    "http://",
    "https://",
    "data:",
    "file:",
    "command:",
    "shell:",
    "exec:",
    "subprocess:",
    "env:",
    "environment:",
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|authorization|cookie|password)\s*[:=]\s*\S{8,}"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?:vcp|vca|ghp|github_pat)_[A-Za-z0-9._-]{12,}", flags=re.I),
)
_PRIVATE_REASONING_TERMS = (
    "chain_of_thought",
    "chain-of-thought",
    "scratchpad",
    "hidden_reasoning",
    "hidden-reasoning",
    "internal_reasoning",
    "internal-reasoning",
    "rationale_trace",
    "rationale-trace",
)


class CorrectionError(RuntimeError):
    pass


class CorrectionIdentityError(CorrectionError):
    pass


class CorrectionPolicyError(CorrectionError):
    pass


class CorrectionStateConflict(CorrectionError):
    pass


class CorrectionReplayConflict(CorrectionError):
    pass


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def _lineage(value: str, *, field: str = "lineage_id") -> str:
    if not isinstance(value, str) or not _LINEAGE_RE.fullmatch(value):
        raise CorrectionIdentityError(f"{field} must use protected src:<sha256> identity")
    return value


def _digest(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise CorrectionIdentityError(f"{field} must be lowercase sha256 hex")
    return value


def _code(value: str, *, field: str = "failure_code") -> str:
    if not isinstance(value, str):
        raise CorrectionPolicyError(f"{field} must be text")
    candidate = value.strip().upper().replace(" ", "_")
    if not _CODE_RE.fullmatch(candidate):
        raise CorrectionPolicyError(f"{field} must be a bounded normalized code")
    return candidate


def _safe_ref(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise CorrectionPolicyError(f"{field} must be text")
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_REF_LENGTH or not _SAFE_REF_RE.fullmatch(candidate):
        raise CorrectionPolicyError(f"{field} is invalid or unbounded")
    lowered = candidate.casefold()
    if lowered.startswith(_FORBIDDEN_REF_PREFIXES):
        raise CorrectionPolicyError(f"{field} contains forbidden URL, command, file or environment authority")
    if any(term in lowered for term in _PRIVATE_REASONING_TERMS):
        raise CorrectionPolicyError(f"{field} contains private-reasoning material")
    if any(pattern.search(candidate) for pattern in _SECRET_PATTERNS):
        raise CorrectionPolicyError(f"{field} contains secret-bearing material")
    return candidate


def _refs(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if len(values) > MAX_REFS:
        raise CorrectionPolicyError(f"{field} exceeds protected item bound")
    normalized = tuple(_safe_ref(value, field=field) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CorrectionPolicyError(f"{field} contains duplicate references")
    return normalized


def _safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 240 or "\\" in value:
        raise CorrectionPolicyError("correction patch path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CorrectionPolicyError("correction patch path must be a safe relative path")
    return path.as_posix()


def _iso(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat()


def _parse_iso(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise CorrectionStateConflict(f"{field} is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CorrectionStateConflict(f"{field} is invalid") from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


class DefectSource(StrEnum):
    IMPLEMENT = "IMPLEMENT"
    BUILD = "BUILD"
    TEST = "TEST"
    VERIFY = "VERIFY"
    BROWSER_DETERMINISTIC = "BROWSER_DETERMINISTIC"
    SCREENSHOT_REGRESSION = "SCREENSHOT_REGRESSION"
    VISUAL = "VISUAL"
    PROVIDER = "PROVIDER"


class DefectPrecedence(IntEnum):
    DETERMINISTIC = 0
    PROTECTED_ACCEPTANCE = 1
    SCREENSHOT_REGRESSION = 2
    MULTIMODAL = 3


class DefectSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class VisualDisposition(StrEnum):
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class CorrectionBoundary(StrEnum):
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    PRIVILEGED_ACTION = "PRIVILEGED_ACTION"
    SPEC_AMBIGUITY = "SPEC_AMBIGUITY"
    CREDENTIAL_AUTHORIZATION = "CREDENTIAL_AUTHORIZATION"
    PROTECTED_POLICY_CHANGE = "PROTECTED_POLICY_CHANGE"
    UNSUPPORTED_REPAIR = "UNSUPPORTED_REPAIR"


class CorrectionStopReason(StrEnum):
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    PRIVILEGED_BOUNDARY = "PRIVILEGED_BOUNDARY"
    MATERIAL_SPEC_AMBIGUITY = "MATERIAL_SPEC_AMBIGUITY"
    MISSING_CREDENTIAL_AUTHORIZATION = "MISSING_CREDENTIAL_AUTHORIZATION"
    PROTECTED_POLICY_BOUNDARY = "PROTECTED_POLICY_BOUNDARY"
    UNRECOVERABLE_FAILURE = "UNRECOVERABLE_FAILURE"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    REPEATED_DEFECT = "REPEATED_DEFECT"
    NO_PROGRESS = "NO_PROGRESS"
    OSCILLATION = "OSCILLATION"


_BOUNDARY_TO_STOP = {
    CorrectionBoundary.HUMAN_APPROVAL: CorrectionStopReason.HUMAN_APPROVAL_REQUIRED,
    CorrectionBoundary.PRIVILEGED_ACTION: CorrectionStopReason.PRIVILEGED_BOUNDARY,
    CorrectionBoundary.SPEC_AMBIGUITY: CorrectionStopReason.MATERIAL_SPEC_AMBIGUITY,
    CorrectionBoundary.CREDENTIAL_AUTHORIZATION: CorrectionStopReason.MISSING_CREDENTIAL_AUTHORIZATION,
    CorrectionBoundary.PROTECTED_POLICY_CHANGE: CorrectionStopReason.PROTECTED_POLICY_BOUNDARY,
    CorrectionBoundary.UNSUPPORTED_REPAIR: CorrectionStopReason.UNRECOVERABLE_FAILURE,
}


class CorrectionSessionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PASSED = "PASSED"
    STOPPED = "STOPPED"


@dataclass(frozen=True, slots=True)
class NormalizedDefect:
    source: DefectSource
    precedence: DefectPrecedence
    failure_code: str
    severity: DefectSeverity
    reproducible: bool
    project_id: str
    run_id: str
    work_specification_digest: str
    lineage_id: str
    preview_deployment_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    source_path: str | None = None
    locator: str | None = None
    boundary: CorrectionBoundary | None = None
    visual_disposition: VisualDisposition | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, DefectSource):
            raise TypeError("defect source is invalid")
        if not isinstance(self.precedence, DefectPrecedence):
            raise TypeError("defect precedence is invalid")
        object.__setattr__(self, "failure_code", _code(self.failure_code))
        if not isinstance(self.severity, DefectSeverity):
            raise TypeError("defect severity is invalid")
        if not isinstance(self.reproducible, bool):
            raise TypeError("defect reproducible must be bool")
        _digest(self.work_specification_digest, field="work_specification_digest")
        _lineage(self.lineage_id)
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, field="defect.evidence_refs"))
        if self.preview_deployment_id is not None:
            object.__setattr__(self, "preview_deployment_id", _safe_ref(self.preview_deployment_id, field="preview_deployment_id"))
        if self.source_path is not None:
            object.__setattr__(self, "source_path", _safe_path(self.source_path))
        if self.locator is not None:
            object.__setattr__(self, "locator", _safe_ref(self.locator, field="defect.locator"))
        if self.boundary is not None and not isinstance(self.boundary, CorrectionBoundary):
            raise TypeError("defect boundary is invalid")
        if self.visual_disposition is not None and not isinstance(self.visual_disposition, VisualDisposition):
            raise TypeError("visual disposition is invalid")
        if self.precedence is DefectPrecedence.MULTIMODAL and self.visual_disposition is None:
            raise CorrectionPolicyError("multimodal defect requires FAIL or REVIEW disposition")
        if self.precedence is not DefectPrecedence.MULTIMODAL and self.visual_disposition is not None:
            raise CorrectionPolicyError("visual disposition is only valid for multimodal defects")

    @property
    def defect_id(self) -> str:
        digest = _canonical_digest(
            {
                "source": self.source.value,
                "precedence": int(self.precedence),
                "failure_code": self.failure_code,
                "project_id": self.project_id,
                "run_id": self.run_id,
                "work_specification_digest": self.work_specification_digest,
                "lineage_id": self.lineage_id,
                "preview_deployment_id": self.preview_deployment_id,
                "source_path": self.source_path,
                "locator": self.locator,
                "boundary": self.boundary.value if self.boundary else None,
                "visual_disposition": self.visual_disposition.value if self.visual_disposition else None,
            }
        )
        return f"defect:{digest[:40]}"

    @property
    def equivalence_fingerprint(self) -> str:
        return _canonical_digest(
            {
                "source": self.source.value,
                "precedence": int(self.precedence),
                "failure_code": self.failure_code,
                "source_path": self.source_path,
                "locator": self.locator,
                "boundary": self.boundary.value if self.boundary else None,
                "visual_disposition": self.visual_disposition.value if self.visual_disposition else None,
            }
        )

    def to_record(self) -> dict[str, object]:
        return {
            "source": self.source.value,
            "precedence": int(self.precedence),
            "failure_code": self.failure_code,
            "severity": self.severity.value,
            "reproducible": self.reproducible,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_digest": self.work_specification_digest,
            "lineage_id": self.lineage_id,
            "preview_deployment_id": self.preview_deployment_id,
            "evidence_refs": list(self.evidence_refs),
            "source_path": self.source_path,
            "locator": self.locator,
            "boundary": self.boundary.value if self.boundary else None,
            "visual_disposition": self.visual_disposition.value if self.visual_disposition else None,
        }

    @classmethod
    def from_record(cls, value: object) -> "NormalizedDefect":
        if not isinstance(value, dict):
            raise CorrectionStateConflict("stored defect is invalid")
        try:
            boundary_raw = value.get("boundary")
            visual_raw = value.get("visual_disposition")
            refs_raw = value.get("evidence_refs", [])
            if not isinstance(refs_raw, list) or not all(isinstance(item, str) for item in refs_raw):
                raise TypeError("invalid evidence refs")
            return cls(
                source=DefectSource(value["source"]),
                precedence=DefectPrecedence(value["precedence"]),
                failure_code=value["failure_code"],
                severity=DefectSeverity(value["severity"]),
                reproducible=value["reproducible"],
                project_id=value["project_id"],
                run_id=value["run_id"],
                work_specification_digest=value["work_specification_digest"],
                lineage_id=value["lineage_id"],
                preview_deployment_id=value.get("preview_deployment_id"),
                evidence_refs=tuple(refs_raw),
                source_path=value.get("source_path"),
                locator=value.get("locator"),
                boundary=CorrectionBoundary(boundary_raw) if boundary_raw is not None else None,
                visual_disposition=VisualDisposition(visual_raw) if visual_raw is not None else None,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CorrectionStateConflict("stored defect failed protected validation") from exc


@dataclass(frozen=True, slots=True, order=True)
class ProtectedQualityVector:
    deterministic_failures: int
    acceptance_failures: int
    screenshot_failures: int
    visual_failures: int
    visual_reviews: int

    def __post_init__(self) -> None:
        values = (
            self.deterministic_failures,
            self.acceptance_failures,
            self.screenshot_failures,
            self.visual_failures,
            self.visual_reviews,
        )
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
            raise CorrectionPolicyError("protected quality counts must be nonnegative integers")

    @property
    def passed(self) -> bool:
        return self == ProtectedQualityVector(0, 0, 0, 0, 0)

    def to_record(self) -> list[int]:
        return [
            self.deterministic_failures,
            self.acceptance_failures,
            self.screenshot_failures,
            self.visual_failures,
            self.visual_reviews,
        ]

    @classmethod
    def from_record(cls, value: object) -> "ProtectedQualityVector":
        if not isinstance(value, list) or len(value) != 5:
            raise CorrectionStateConflict("stored protected quality vector is invalid")
        return cls(*value)

    @classmethod
    def from_defects(cls, defects: tuple[NormalizedDefect, ...]) -> "ProtectedQualityVector":
        deterministic = sum(item.precedence is DefectPrecedence.DETERMINISTIC for item in defects)
        acceptance = sum(item.precedence is DefectPrecedence.PROTECTED_ACCEPTANCE for item in defects)
        screenshot = sum(item.precedence is DefectPrecedence.SCREENSHOT_REGRESSION for item in defects)
        visual_failures = sum(
            item.precedence is DefectPrecedence.MULTIMODAL and item.visual_disposition is VisualDisposition.FAIL
            for item in defects
        )
        visual_reviews = sum(
            item.precedence is DefectPrecedence.MULTIMODAL and item.visual_disposition is VisualDisposition.REVIEW
            for item in defects
        )
        return cls(deterministic, acceptance, screenshot, visual_failures, visual_reviews)


@dataclass(frozen=True, slots=True)
class CandidateValidation:
    project_id: str
    run_id: str
    work_specification_digest: str
    lineage_id: str
    quality: ProtectedQualityVector
    defects: tuple[NormalizedDefect, ...]
    evidence_refs: tuple[str, ...] = ()
    preview_deployment_id: str | None = None

    def __post_init__(self) -> None:
        _digest(self.work_specification_digest, field="work_specification_digest")
        _lineage(self.lineage_id)
        if len(self.defects) > MAX_DEFECTS or not all(isinstance(item, NormalizedDefect) for item in self.defects):
            raise CorrectionPolicyError("candidate defect set exceeds protected bound")
        for defect in self.defects:
            if (
                defect.project_id != self.project_id
                or defect.run_id != self.run_id
                or defect.work_specification_digest != self.work_specification_digest
                or defect.lineage_id != self.lineage_id
            ):
                raise CorrectionIdentityError("candidate defect provenance mismatch")
            if self.preview_deployment_id is not None and defect.preview_deployment_id not in {None, self.preview_deployment_id}:
                raise CorrectionIdentityError("candidate defect Preview provenance mismatch")
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, field="candidate.evidence_refs"))
        if self.preview_deployment_id is not None:
            object.__setattr__(self, "preview_deployment_id", _safe_ref(self.preview_deployment_id, field="preview_deployment_id"))
        if self.quality != ProtectedQualityVector.from_defects(self.defects):
            raise CorrectionPolicyError("candidate quality vector must be derived exactly from normalized defects")

    @property
    def state_fingerprint(self) -> str:
        return _canonical_digest(
            {
                "quality": self.quality.to_record(),
                "defects": sorted(item.equivalence_fingerprint for item in self.defects),
            }
        )


@dataclass(frozen=True, slots=True)
class CorrectionContext:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    plan_ref: str
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.work_specification_revision < 1:
            raise CorrectionIdentityError("Work Specification revision must be positive")
        _digest(self.work_specification_digest, field="work_specification_digest")
        object.__setattr__(self, "plan_ref", _safe_ref(self.plan_ref, field="plan_ref"))
        object.__setattr__(self, "dependencies", _refs(self.dependencies, field="dependencies"))

    @classmethod
    def from_run(
        cls,
        run: EngineeringRun,
        *,
        plan_ref: str,
        dependencies: tuple[str, ...] = (),
    ) -> "CorrectionContext":
        if not run.project_id or not run.work_specification_id or run.work_specification_revision is None or not run.work_specification_digest:
            raise CorrectionIdentityError("correction requires canonical Project and approved Work Specification binding")
        return cls(
            project_id=run.project_id,
            run_id=run.id,
            work_specification_id=run.work_specification_id,
            work_specification_revision=run.work_specification_revision,
            work_specification_digest=run.work_specification_digest,
            plan_ref=plan_ref,
            dependencies=dependencies,
        )

    @property
    def session_id(self) -> str:
        digest = _canonical_digest(
            {
                "project_id": self.project_id,
                "run_id": self.run_id,
                "work_specification_id": self.work_specification_id,
                "work_specification_revision": self.work_specification_revision,
                "work_specification_digest": self.work_specification_digest,
                "plan_ref": self.plan_ref,
            }
        )
        return f"corr:{digest[:40]}"


@dataclass(frozen=True, slots=True)
class CorrectionBudgetPolicy:
    max_attempts: int = 6
    max_changed_bytes: int = 256_000
    max_compute_units: int = 24
    max_elapsed_seconds: int = 900
    max_no_progress: int = 2
    max_defect_repeats: int = 3
    max_oscillations: int = 2

    def __post_init__(self) -> None:
        values = (
            self.max_attempts,
            self.max_changed_bytes,
            self.max_compute_units,
            self.max_elapsed_seconds,
            self.max_no_progress,
            self.max_defect_repeats,
            self.max_oscillations,
        )
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
            raise CorrectionPolicyError("correction budgets must be finite nonnegative integers")
        if self.max_attempts < 1 or self.max_changed_bytes < 1 or self.max_compute_units < 1 or self.max_elapsed_seconds < 1:
            raise CorrectionPolicyError("primary correction budgets must be positive")


@dataclass(frozen=True, slots=True)
class CorrectionPathPolicy:
    forbidden_prefixes: tuple[str, ...] = (
        ".github/workflows/",
        "specs/",
        "PROJECT-CONSTITUTION.md",
        "ARCHITECTURE.md",
        "CURRENT-STATE.md",
        "services/api/parallax_api/intelligence/protected_metrics.py",
        "services/api/parallax_api/tools/registry.py",
        "services/api/parallax_api/validation/browser.py",
    )

    def validate(self, patch: SourcePatch) -> SourcePatch:
        path = _safe_path(patch.path)
        _digest(patch.expected_base_sha256, field="expected_base_sha256")
        if not isinstance(patch.unified_diff, str) or not patch.unified_diff:
            raise CorrectionPolicyError("correction patch requires a non-empty unified diff")
        if len(patch.unified_diff.encode("utf-8")) > MAX_PATCH_BYTES:
            raise CorrectionPolicyError("correction patch exceeds protected size bound")
        lowered = path.casefold()
        for prefix in self.forbidden_prefixes:
            protected = prefix.casefold()
            if lowered == protected.rstrip("/") or lowered.startswith(protected):
                raise CorrectionPolicyError("correction plan attempts to mutate protected policy or authority")
        return SourcePatch(path=path, expected_base_sha256=patch.expected_base_sha256, unified_diff=patch.unified_diff)


@dataclass(frozen=True, slots=True)
class CorrectionPlan:
    target_defect_ids: tuple[str, ...]
    patches: tuple[SourcePatch, ...]
    estimated_changed_bytes: int
    compute_units: int
    boundary: CorrectionBoundary | None = None

    def __post_init__(self) -> None:
        if not self.target_defect_ids or len(self.target_defect_ids) > MAX_DEFECTS:
            raise CorrectionPolicyError("correction plan requires a bounded target defect set")
        normalized_targets = tuple(_safe_ref(value, field="target_defect_id") for value in self.target_defect_ids)
        if len(set(normalized_targets)) != len(normalized_targets):
            raise CorrectionPolicyError("correction plan target defects must be unique")
        object.__setattr__(self, "target_defect_ids", normalized_targets)
        if len(self.patches) > MAX_PATCHES or not all(isinstance(item, SourcePatch) for item in self.patches):
            raise CorrectionPolicyError("correction plan patch set exceeds protected bound")
        if self.boundary is None and not self.patches:
            raise CorrectionPolicyError("ordinary correction plan requires at least one source patch")
        if self.boundary is not None and self.patches:
            raise CorrectionPolicyError("boundary correction plan cannot also request source mutation")
        if not isinstance(self.estimated_changed_bytes, int) or not 0 <= self.estimated_changed_bytes <= 10_000_000:
            raise CorrectionPolicyError("estimated changed bytes are invalid")
        if not isinstance(self.compute_units, int) or not 0 <= self.compute_units <= 10_000:
            raise CorrectionPolicyError("estimated compute units are invalid")

    def digest(self, path_policy: CorrectionPathPolicy) -> str:
        patches = tuple(path_policy.validate(item) for item in self.patches)
        return _canonical_digest(
            {
                "target_defect_ids": self.target_defect_ids,
                "patches": [
                    {
                        "path": patch.path,
                        "expected_base_sha256": patch.expected_base_sha256,
                        "diff_sha256": sha256(patch.unified_diff.encode("utf-8")).hexdigest(),
                        "diff_size": len(patch.unified_diff.encode("utf-8")),
                    }
                    for patch in patches
                ],
                "estimated_changed_bytes": self.estimated_changed_bytes,
                "compute_units": self.compute_units,
                "boundary": self.boundary.value if self.boundary else None,
            }
        )


@dataclass(frozen=True, slots=True)
class CorrectionMutationResult:
    lineage_id: str
    changed_bytes: int
    replayed: bool
    evidence_ref: str

    def __post_init__(self) -> None:
        _lineage(self.lineage_id)
        if not isinstance(self.changed_bytes, int) or self.changed_bytes < 0:
            raise CorrectionPolicyError("mutation changed bytes must be nonnegative")
        if not isinstance(self.replayed, bool):
            raise TypeError("mutation replayed must be bool")
        object.__setattr__(self, "evidence_ref", _safe_ref(self.evidence_ref, field="mutation.evidence_ref"))


class CorrectionPlanner(Protocol):
    def plan(
        self,
        context: CorrectionContext,
        *,
        lineage_id: str,
        defects: tuple[NormalizedDefect, ...],
    ) -> CorrectionPlan: ...


class CorrectionMutationRuntime(Protocol):
    def apply(
        self,
        context: CorrectionContext,
        *,
        operation_key: str,
        base_lineage_id: str,
        plan: CorrectionPlan,
    ) -> CorrectionMutationResult: ...


class CorrectionValidator(Protocol):
    def validate(self, context: CorrectionContext, *, lineage_id: str) -> CandidateValidation: ...


@dataclass(frozen=True, slots=True)
class CorrectionSessionState:
    session_id: str
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    plan_ref: str
    status: CorrectionSessionStatus
    current_lineage_id: str
    current_quality: ProtectedQualityVector
    current_defects: tuple[NormalizedDefect, ...]
    lkg_lineage_id: str
    lkg_quality: ProtectedQualityVector
    lkg_defects: tuple[NormalizedDefect, ...]
    attempt_count: int
    cumulative_changed_bytes: int
    cumulative_compute_units: int
    no_progress_count: int
    oscillation_count: int
    defect_repeat_counts: tuple[tuple[str, int], ...]
    state_history: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    started_at: datetime
    updated_at: datetime
    pending_operation_key: str | None = None
    pending_plan_digest: str | None = None
    stop_reason: CorrectionStopReason | None = None
    revision: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _safe_ref(self.session_id, field="session_id"))
        _digest(self.work_specification_digest, field="work_specification_digest")
        object.__setattr__(self, "plan_ref", _safe_ref(self.plan_ref, field="plan_ref"))
        _lineage(self.current_lineage_id, field="current_lineage_id")
        _lineage(self.lkg_lineage_id, field="lkg_lineage_id")
        if len(self.current_defects) > MAX_DEFECTS or len(self.lkg_defects) > MAX_DEFECTS:
            raise CorrectionStateConflict("stored defect set exceeds protected bound")
        if any(not isinstance(item, NormalizedDefect) for item in self.current_defects + self.lkg_defects):
            raise CorrectionStateConflict("stored defect set is invalid")
        for field_name in (
            "attempt_count",
            "cumulative_changed_bytes",
            "cumulative_compute_units",
            "no_progress_count",
            "oscillation_count",
            "revision",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CorrectionStateConflict(f"{field_name} is invalid")
        if len(self.defect_repeat_counts) > MAX_REPEAT_KEYS:
            raise CorrectionStateConflict("defect repeat history exceeds protected bound")
        for fingerprint, count in self.defect_repeat_counts:
            _digest(fingerprint, field="defect_repeat_fingerprint")
            if not isinstance(count, int) or count < 1:
                raise CorrectionStateConflict("defect repeat count is invalid")
        if len(self.state_history) > MAX_HISTORY:
            raise CorrectionStateConflict("state history exceeds protected bound")
        for fingerprint in self.state_history:
            _digest(fingerprint, field="state_history_fingerprint")
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, field="state.evidence_refs"))
        if (self.pending_operation_key is None) != (self.pending_plan_digest is None):
            raise CorrectionStateConflict("pending correction identity is incomplete")
        if self.pending_operation_key is not None:
            object.__setattr__(self, "pending_operation_key", _safe_ref(self.pending_operation_key, field="pending_operation_key"))
            _digest(self.pending_plan_digest or "", field="pending_plan_digest")
        if self.status is CorrectionSessionStatus.PASSED and not self.current_quality.passed:
            raise CorrectionStateConflict("passed correction state must retain protected PASS quality")
        if self.status is CorrectionSessionStatus.STOPPED and self.stop_reason is None:
            raise CorrectionStateConflict("stopped correction state requires a stop reason")
        if self.status is not CorrectionSessionStatus.STOPPED and self.stop_reason is not None:
            raise CorrectionStateConflict("active/passed correction state cannot retain a stop reason")

    def to_record(self) -> dict[str, object]:
        return {
            "record_kind": _STATE_KIND,
            "record_version": _STATE_VERSION,
            "session_id": self.session_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "plan_ref": self.plan_ref,
            "status": self.status.value,
            "current_lineage_id": self.current_lineage_id,
            "current_quality": self.current_quality.to_record(),
            "current_defects": [item.to_record() for item in self.current_defects],
            "lkg_lineage_id": self.lkg_lineage_id,
            "lkg_quality": self.lkg_quality.to_record(),
            "lkg_defects": [item.to_record() for item in self.lkg_defects],
            "attempt_count": self.attempt_count,
            "cumulative_changed_bytes": self.cumulative_changed_bytes,
            "cumulative_compute_units": self.cumulative_compute_units,
            "no_progress_count": self.no_progress_count,
            "oscillation_count": self.oscillation_count,
            "defect_repeat_counts": [[key, count] for key, count in self.defect_repeat_counts],
            "state_history": list(self.state_history),
            "evidence_refs": list(self.evidence_refs),
            "started_at": _iso(self.started_at),
            "updated_at": _iso(self.updated_at),
            "pending_operation_key": self.pending_operation_key,
            "pending_plan_digest": self.pending_plan_digest,
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "revision": self.revision,
        }

    @classmethod
    def from_record(cls, value: object) -> "CorrectionSessionState":
        if not isinstance(value, dict) or value.get("record_kind") != _STATE_KIND or value.get("record_version") != _STATE_VERSION:
            raise CorrectionStateConflict("stored correction state version is invalid")
        try:
            current_raw = value["current_defects"]
            lkg_raw = value["lkg_defects"]
            repeats_raw = value["defect_repeat_counts"]
            history_raw = value["state_history"]
            refs_raw = value["evidence_refs"]
            if not isinstance(current_raw, list) or not isinstance(lkg_raw, list):
                raise TypeError("invalid defect records")
            if not isinstance(repeats_raw, list) or not isinstance(history_raw, list) or not isinstance(refs_raw, list):
                raise TypeError("invalid bounded histories")
            stop_raw = value.get("stop_reason")
            return cls(
                session_id=value["session_id"],
                project_id=value["project_id"],
                run_id=value["run_id"],
                work_specification_id=value["work_specification_id"],
                work_specification_revision=value["work_specification_revision"],
                work_specification_digest=value["work_specification_digest"],
                plan_ref=value["plan_ref"],
                status=CorrectionSessionStatus(value["status"]),
                current_lineage_id=value["current_lineage_id"],
                current_quality=ProtectedQualityVector.from_record(value["current_quality"]),
                current_defects=tuple(NormalizedDefect.from_record(item) for item in current_raw),
                lkg_lineage_id=value["lkg_lineage_id"],
                lkg_quality=ProtectedQualityVector.from_record(value["lkg_quality"]),
                lkg_defects=tuple(NormalizedDefect.from_record(item) for item in lkg_raw),
                attempt_count=value["attempt_count"],
                cumulative_changed_bytes=value["cumulative_changed_bytes"],
                cumulative_compute_units=value["cumulative_compute_units"],
                no_progress_count=value["no_progress_count"],
                oscillation_count=value["oscillation_count"],
                defect_repeat_counts=tuple((item[0], item[1]) for item in repeats_raw),
                state_history=tuple(history_raw),
                evidence_refs=tuple(refs_raw),
                started_at=_parse_iso(value["started_at"], field="started_at"),
                updated_at=_parse_iso(value["updated_at"], field="updated_at"),
                pending_operation_key=value.get("pending_operation_key"),
                pending_plan_digest=value.get("pending_plan_digest"),
                stop_reason=CorrectionStopReason(stop_raw) if stop_raw is not None else None,
                revision=value["revision"],
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise CorrectionStateConflict("stored correction state failed protected validation") from exc


class CorrectionStateStore(Protocol):
    def load(self, *, run_id: str, session_id: str) -> CorrectionSessionState | None: ...

    def save(
        self,
        *,
        run: EngineeringRun,
        state: CorrectionSessionState,
        expected_revision: int,
    ) -> CorrectionSessionState: ...


class EngineeringAttemptCorrectionStateStore:
    """Durable bounded correction ledger without advancing Engineering Run lifecycle state."""

    def __init__(self, repository: EngineeringRunRepository) -> None:
        if not isinstance(repository, EngineeringRunRepository):
            raise TypeError("repository must be EngineeringRunRepository")
        self.repository = repository

    @staticmethod
    def operation_key(session_id: str) -> str:
        return f"correction-state:{_safe_ref(session_id, field='session_id')}"

    @staticmethod
    def _encode(state: CorrectionSessionState) -> str:
        encoded = json.dumps(state.to_record(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if len(encoded.encode("utf-8")) > MAX_STATE_BYTES:
            raise CorrectionStateConflict("durable correction state exceeds protected 24KB bound")
        return encoded

    def load(self, *, run_id: str, session_id: str) -> CorrectionSessionState | None:
        attempt = self.repository.find_operation(run_id, self.operation_key(session_id))
        if attempt is None:
            return None
        if attempt.stage != _STATE_STAGE or attempt.status != _STATE_STATUS:
            raise CorrectionStateConflict("durable correction attempt has invalid record type")
        try:
            payload = json.loads(attempt.evidence_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise CorrectionStateConflict("durable correction evidence is invalid") from exc
        state = CorrectionSessionState.from_record(payload)
        if state.run_id != run_id or state.session_id != session_id:
            raise CorrectionStateConflict("durable correction identity mismatch")
        self._encode(state)
        return state

    def save(
        self,
        *,
        run: EngineeringRun,
        state: CorrectionSessionState,
        expected_revision: int,
    ) -> CorrectionSessionState:
        if state.project_id != run.project_id or state.run_id != run.id:
            raise CorrectionStateConflict("correction state does not match canonical Engineering Run")
        if (
            state.work_specification_id != run.work_specification_id
            or state.work_specification_revision != run.work_specification_revision
            or state.work_specification_digest != run.work_specification_digest
        ):
            raise CorrectionStateConflict("correction state Work Specification binding mismatch")
        current = self.load(run_id=run.id, session_id=state.session_id)
        if current is None:
            if expected_revision != 0 or state.revision != 0:
                raise CorrectionStateConflict("new correction state revision mismatch")
            saved = replace(state, revision=1)
            encoded = self._encode(saved)
            attempt = EngineeringAttempt(
                run_id=run.id,
                stage=_STATE_STAGE,
                attempt_number=1,
                operation_key=self.operation_key(state.session_id),
                status=_STATE_STATUS,
                program_id=_STATE_PROGRAM,
                tool_id=_STATE_TOOL,
                evidence_json=encoded,
                completed_at=utcnow(),
            )
            try:
                self.repository.session.add(attempt)
                self.repository.session.commit()
            except IntegrityError as exc:
                self.repository.session.rollback()
                replay = self.load(run_id=run.id, session_id=state.session_id)
                if replay is None:
                    raise CorrectionStateConflict("concurrent correction-state creation conflicted") from exc
                return replay
            return saved

        if current.revision != expected_revision or state.revision != expected_revision:
            raise CorrectionStateConflict("correction state compare-and-swap revision mismatch")
        saved = replace(state, revision=expected_revision + 1)
        encoded = self._encode(saved)
        attempt = self.repository.find_operation(run.id, self.operation_key(state.session_id))
        if attempt is None:
            raise CorrectionStateConflict("durable correction state disappeared during update")
        old_encoded = attempt.evidence_json
        result = self.repository.session.execute(
            update(EngineeringAttempt)
            .where(EngineeringAttempt.id == attempt.id, EngineeringAttempt.evidence_json == old_encoded)
            .values(evidence_json=encoded, completed_at=utcnow())
        )
        if result.rowcount != 1:
            self.repository.session.rollback()
            raise CorrectionStateConflict("concurrent correction-state update conflicted")
        self.repository.session.commit()
        return saved


class CorrectionCheckpointSink(Protocol):
    def record(self, state: CorrectionSessionState) -> None: ...


class WorkerCorrectionCheckpointSink:
    """Record correction progress through the existing P2-V0.16.1 worker identity."""

    def __init__(
        self,
        service: WorkerRecoveryService,
        *,
        lease: WorkerLease,
        run: EngineeringRun,
        context: CorrectionContext,
    ) -> None:
        self.service = service
        self.lease = lease
        self.run = run
        self.context = context

    def record(self, state: CorrectionSessionState) -> None:
        blocker = f"CORRECTION_{state.stop_reason.value}" if state.stop_reason is not None else None
        evidence = tuple(dict.fromkeys(state.evidence_refs))[-MAX_REFS:]
        checkpoint = WorkerCheckpoint(
            project_id=self.context.project_id,
            run_id=self.context.run_id,
            work_specification_id=self.context.work_specification_id,
            work_specification_revision=self.context.work_specification_revision,
            work_specification_digest=self.context.work_specification_digest,
            plan_ref=self.context.plan_ref,
            current_step=("CORRECTION_PASSED" if state.status is CorrectionSessionStatus.PASSED else "CORRECTION_ACTIVE"),
            source_lineage_ref=state.current_lineage_id,
            last_known_good_lineage_ref=state.lkg_lineage_id,
            evidence_refs=evidence,
            dependencies=self.context.dependencies,
            blocker_code=blocker,
        )
        lifecycle = WorkerLifecycleState.SUCCEEDED if state.status is CorrectionSessionStatus.PASSED else WorkerLifecycleState.CHECKPOINTED
        self.service.checkpoint(
            self.lease,
            checkpoint,
            authoritative_source_lineage_ref=state.current_lineage_id,
            state=lifecycle,
            retry=False,
        )


@dataclass(frozen=True, slots=True)
class FailureDispatch:
    project_id: str
    run_id: str
    work_specification_digest: str
    source_lineage_id: str
    lkg_lineage_id: str
    defect_fingerprint: str
    evidence_refs: tuple[str, ...]
    dependency_refs: tuple[str, ...]
    receiving_class: str
    stop_reason: CorrectionStopReason
    reproducible: bool

    def __post_init__(self) -> None:
        _digest(self.work_specification_digest, field="work_specification_digest")
        _lineage(self.source_lineage_id, field="source_lineage_id")
        _lineage(self.lkg_lineage_id, field="lkg_lineage_id")
        _digest(self.defect_fingerprint, field="defect_fingerprint")
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, field="dispatch.evidence_refs"))
        object.__setattr__(self, "dependency_refs", _refs(self.dependency_refs, field="dispatch.dependencies"))
        object.__setattr__(self, "receiving_class", _safe_ref(self.receiving_class, field="receiving_class"))


def normalize_failure(
    *,
    source: DefectSource,
    precedence: DefectPrecedence,
    failure_code: str,
    severity: DefectSeverity,
    reproducible: bool,
    project_id: str,
    run_id: str,
    work_specification_digest: str,
    lineage_id: str,
    preview_deployment_id: str | None = None,
    evidence_refs: tuple[str, ...] = (),
    source_path: str | None = None,
    locator: str | None = None,
    boundary: CorrectionBoundary | None = None,
    visual_disposition: VisualDisposition | None = None,
) -> NormalizedDefect:
    return NormalizedDefect(
        source=source,
        precedence=precedence,
        failure_code=failure_code,
        severity=severity,
        reproducible=reproducible,
        project_id=project_id,
        run_id=run_id,
        work_specification_digest=work_specification_digest,
        lineage_id=lineage_id,
        preview_deployment_id=preview_deployment_id,
        evidence_refs=evidence_refs,
        source_path=source_path,
        locator=locator,
        boundary=boundary,
        visual_disposition=visual_disposition,
    )


def candidate_from_browser(result: ProtectedBrowserValidationResult) -> CandidateValidation:
    defects: list[NormalizedDefect] = []
    for index, code in enumerate(result.deterministic_defects):
        screenshot = code.startswith("SCREENSHOT_REGRESSION:")
        defects.append(
            normalize_failure(
                source=DefectSource.SCREENSHOT_REGRESSION if screenshot else DefectSource.BROWSER_DETERMINISTIC,
                precedence=DefectPrecedence.SCREENSHOT_REGRESSION if screenshot else DefectPrecedence.DETERMINISTIC,
                failure_code=("SCREENSHOT_REGRESSION" if screenshot else code.split(":", 1)[0]),
                severity=DefectSeverity.ERROR,
                reproducible=True,
                project_id=result.project_id,
                run_id=result.run_id,
                work_specification_digest=result.work_specification_digest,
                lineage_id=result.lineage_id,
                preview_deployment_id=result.preview_deployment_id,
                evidence_refs=(f"browser:{result.workflow_id}:{index}",),
                locator=(code.split(":", 1)[1] if ":" in code else None),
            )
        )
    for index, review in enumerate(result.visual_reviews):
        if review.outcome is VisualReviewOutcome.PASS:
            continue
        disposition = VisualDisposition.FAIL if review.outcome is VisualReviewOutcome.FAIL else VisualDisposition.REVIEW
        defects.append(
            normalize_failure(
                source=DefectSource.VISUAL,
                precedence=DefectPrecedence.MULTIMODAL,
                failure_code=f"MULTIMODAL_{disposition.value}",
                severity=DefectSeverity.ERROR if disposition is VisualDisposition.FAIL else DefectSeverity.WARNING,
                reproducible=True,
                project_id=result.project_id,
                run_id=result.run_id,
                work_specification_digest=result.work_specification_digest,
                lineage_id=result.lineage_id,
                preview_deployment_id=result.preview_deployment_id,
                evidence_refs=(f"visual:{result.workflow_id}:{index}",),
                visual_disposition=disposition,
            )
        )
    normalized = tuple(defects)
    return CandidateValidation(
        project_id=result.project_id,
        run_id=result.run_id,
        work_specification_digest=result.work_specification_digest,
        lineage_id=result.lineage_id,
        quality=ProtectedQualityVector.from_defects(normalized),
        defects=normalized,
        evidence_refs=(f"browser-result:{result.workflow_id}:v{result.workflow_version}",),
        preview_deployment_id=result.preview_deployment_id,
    )


def _defect_set_fingerprint(defects: tuple[NormalizedDefect, ...]) -> str:
    return _canonical_digest(sorted(item.equivalence_fingerprint for item in defects))


def _merge_refs(*groups: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = []
    for group in groups:
        for value in group:
            safe = _safe_ref(value, field="evidence_ref")
            if safe not in values:
                values.append(safe)
    return tuple(values[-MAX_REFS:])


class AutonomousCorrectionController:
    def __init__(
        self,
        *,
        run: EngineeringRun,
        context: CorrectionContext,
        planner: CorrectionPlanner,
        mutation: CorrectionMutationRuntime,
        validator: CorrectionValidator,
        state_store: CorrectionStateStore,
        budget: CorrectionBudgetPolicy | None = None,
        path_policy: CorrectionPathPolicy | None = None,
        checkpoint_sink: CorrectionCheckpointSink | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.run = run
        self.context = context
        self.planner = planner
        self.mutation = mutation
        self.validator = validator
        self.state_store = state_store
        self.budget = budget or CorrectionBudgetPolicy()
        self.path_policy = path_policy or CorrectionPathPolicy()
        self.checkpoint_sink = checkpoint_sink
        self.now = now or (lambda: datetime.now(timezone.utc))
        expected = CorrectionContext.from_run(run, plan_ref=context.plan_ref, dependencies=context.dependencies)
        if expected != context:
            raise CorrectionIdentityError("correction context does not match canonical Engineering Run")

    def _validate_candidate(self, candidate: CandidateValidation, lineage_id: str) -> CandidateValidation:
        if (
            candidate.project_id != self.context.project_id
            or candidate.run_id != self.context.run_id
            or candidate.work_specification_digest != self.context.work_specification_digest
            or candidate.lineage_id != lineage_id
        ):
            raise CorrectionIdentityError("fresh validation result does not match correction session identity")
        return candidate

    def _save(self, state: CorrectionSessionState) -> CorrectionSessionState:
        saved = self.state_store.save(run=self.run, state=state, expected_revision=state.revision)
        if self.checkpoint_sink is not None:
            self.checkpoint_sink.record(saved)
        return saved

    def _initialize(self, initial_lineage_id: str) -> CorrectionSessionState:
        lineage = _lineage(initial_lineage_id, field="initial_lineage_id")
        existing = self.state_store.load(run_id=self.context.run_id, session_id=self.context.session_id)
        if existing is not None:
            if (
                existing.project_id != self.context.project_id
                or existing.work_specification_id != self.context.work_specification_id
                or existing.work_specification_revision != self.context.work_specification_revision
                or existing.work_specification_digest != self.context.work_specification_digest
                or existing.plan_ref != self.context.plan_ref
            ):
                raise CorrectionStateConflict("durable correction state belongs to a different protected session")
            return existing

        candidate = self._validate_candidate(
            self.validator.validate(self.context, lineage_id=lineage),
            lineage,
        )
        now = self.now()
        fingerprint = _defect_set_fingerprint(candidate.defects)
        status = CorrectionSessionStatus.PASSED if candidate.quality.passed else CorrectionSessionStatus.ACTIVE
        state = CorrectionSessionState(
            session_id=self.context.session_id,
            project_id=self.context.project_id,
            run_id=self.context.run_id,
            work_specification_id=self.context.work_specification_id,
            work_specification_revision=self.context.work_specification_revision,
            work_specification_digest=self.context.work_specification_digest,
            plan_ref=self.context.plan_ref,
            status=status,
            current_lineage_id=lineage,
            current_quality=candidate.quality,
            current_defects=candidate.defects,
            lkg_lineage_id=lineage,
            lkg_quality=candidate.quality,
            lkg_defects=candidate.defects,
            attempt_count=0,
            cumulative_changed_bytes=0,
            cumulative_compute_units=0,
            no_progress_count=0,
            oscillation_count=0,
            defect_repeat_counts=((fingerprint, 1),) if candidate.defects else (),
            state_history=(candidate.state_fingerprint,),
            evidence_refs=candidate.evidence_refs,
            started_at=now,
            updated_at=now,
            revision=0,
        )
        return self._save(state)

    def _stop(self, state: CorrectionSessionState, reason: CorrectionStopReason) -> CorrectionSessionState:
        return self._save(
            replace(
                state,
                status=CorrectionSessionStatus.STOPPED,
                stop_reason=reason,
                pending_operation_key=None,
                pending_plan_digest=None,
                updated_at=self.now(),
            )
        )

    def _boundary_reason(self, defects: tuple[NormalizedDefect, ...]) -> CorrectionStopReason | None:
        boundaries = [item.boundary for item in defects if item.boundary is not None]
        if not boundaries:
            return None
        priority = (
            CorrectionBoundary.HUMAN_APPROVAL,
            CorrectionBoundary.PRIVILEGED_ACTION,
            CorrectionBoundary.SPEC_AMBIGUITY,
            CorrectionBoundary.CREDENTIAL_AUTHORIZATION,
            CorrectionBoundary.PROTECTED_POLICY_CHANGE,
            CorrectionBoundary.UNSUPPORTED_REPAIR,
        )
        selected = next(item for item in priority if item in boundaries)
        return _BOUNDARY_TO_STOP[selected]

    def _elapsed(self, state: CorrectionSessionState) -> float:
        return max(0.0, (self.now() - state.started_at).total_seconds())

    def _validate_plan(self, state: CorrectionSessionState, plan: CorrectionPlan) -> str:
        known = {item.defect_id for item in state.current_defects}
        if not set(plan.target_defect_ids).issubset(known):
            raise CorrectionPolicyError("correction plan targets defects outside the current protected evidence set")
        for patch in plan.patches:
            self.path_policy.validate(patch)
        return plan.digest(self.path_policy)

    def _operation_key(self, state: CorrectionSessionState, plan_digest: str) -> str:
        digest = _canonical_digest(
            {
                "session_id": state.session_id,
                "attempt": state.attempt_count + 1,
                "base_lineage_id": state.current_lineage_id,
                "plan_digest": plan_digest,
            }
        )
        return f"correction:{digest[:48]}"

    def advance(self, *, initial_lineage_id: str) -> CorrectionSessionState:
        state = self._initialize(initial_lineage_id)
        if state.status is not CorrectionSessionStatus.ACTIVE:
            return state
        if state.current_quality.passed:
            return self._save(replace(state, status=CorrectionSessionStatus.PASSED, updated_at=self.now()))

        boundary = self._boundary_reason(state.current_defects)
        if boundary is not None:
            return self._stop(state, boundary)
        if self._elapsed(state) >= self.budget.max_elapsed_seconds or state.attempt_count >= self.budget.max_attempts:
            return self._stop(state, CorrectionStopReason.RESOURCE_EXHAUSTION)

        plan = self.planner.plan(
            self.context,
            lineage_id=state.current_lineage_id,
            defects=state.current_defects,
        )
        plan_digest = self._validate_plan(state, plan)
        if plan.boundary is not None:
            return self._stop(state, _BOUNDARY_TO_STOP[plan.boundary])

        if state.pending_operation_key is not None:
            if state.pending_plan_digest != plan_digest:
                raise CorrectionReplayConflict("reconstructed correction plan does not match durable pending plan digest")
            operation_key = state.pending_operation_key
        else:
            if (
                state.cumulative_changed_bytes + plan.estimated_changed_bytes > self.budget.max_changed_bytes
                or state.cumulative_compute_units + plan.compute_units > self.budget.max_compute_units
            ):
                return self._stop(state, CorrectionStopReason.RESOURCE_EXHAUSTION)
            operation_key = self._operation_key(state, plan_digest)
            state = self._save(
                replace(
                    state,
                    pending_operation_key=operation_key,
                    pending_plan_digest=plan_digest,
                    updated_at=self.now(),
                )
            )

        mutation = self.mutation.apply(
            self.context,
            operation_key=operation_key,
            base_lineage_id=state.current_lineage_id,
            plan=plan,
        )
        if mutation.lineage_id == state.current_lineage_id:
            raise CorrectionPolicyError("correction mutation must return a new immutable lineage")
        candidate = self._validate_candidate(
            self.validator.validate(self.context, lineage_id=mutation.lineage_id),
            mutation.lineage_id,
        )

        previous_current_quality = state.current_quality
        better_than_current = candidate.quality < previous_current_quality
        better_than_lkg = candidate.quality < state.lkg_quality
        lkg_lineage = mutation.lineage_id if better_than_lkg else state.lkg_lineage_id
        lkg_quality = candidate.quality if better_than_lkg else state.lkg_quality
        lkg_defects = candidate.defects if better_than_lkg else state.lkg_defects
        if better_than_current:
            current_lineage = mutation.lineage_id
            current_quality = candidate.quality
            current_defects = candidate.defects
            no_progress = 0
        else:
            current_lineage = lkg_lineage
            current_quality = lkg_quality
            current_defects = lkg_defects
            no_progress = state.no_progress_count + 1

        candidate_fingerprint = candidate.state_fingerprint
        history = tuple((state.state_history + (candidate_fingerprint,))[-MAX_HISTORY:])
        oscillation = state.oscillation_count
        if len(state.state_history) >= 2 and candidate_fingerprint == state.state_history[-2] and candidate_fingerprint != state.state_history[-1]:
            oscillation += 1

        repeat_map = dict(state.defect_repeat_counts)
        defect_fingerprint = _defect_set_fingerprint(candidate.defects)
        repeat_map[defect_fingerprint] = repeat_map.get(defect_fingerprint, 0) + 1
        if len(repeat_map) > MAX_REPEAT_KEYS:
            repeat_map = dict(list(repeat_map.items())[-MAX_REPEAT_KEYS:])

        changed = state.cumulative_changed_bytes + mutation.changed_bytes
        compute = state.cumulative_compute_units + plan.compute_units
        attempts = state.attempt_count + 1
        evidence_refs = _merge_refs(state.evidence_refs, candidate.evidence_refs, (mutation.evidence_ref,))

        next_state = replace(
            state,
            current_lineage_id=current_lineage,
            current_quality=current_quality,
            current_defects=current_defects,
            lkg_lineage_id=lkg_lineage,
            lkg_quality=lkg_quality,
            lkg_defects=lkg_defects,
            attempt_count=attempts,
            cumulative_changed_bytes=changed,
            cumulative_compute_units=compute,
            no_progress_count=no_progress,
            oscillation_count=oscillation,
            defect_repeat_counts=tuple(repeat_map.items()),
            state_history=history,
            evidence_refs=evidence_refs,
            pending_operation_key=None,
            pending_plan_digest=None,
            updated_at=self.now(),
        )

        if candidate.quality.passed:
            next_state = replace(
                next_state,
                status=CorrectionSessionStatus.PASSED,
                current_lineage_id=mutation.lineage_id,
                current_quality=candidate.quality,
                current_defects=candidate.defects,
                lkg_lineage_id=mutation.lineage_id,
                lkg_quality=candidate.quality,
                lkg_defects=candidate.defects,
            )
        elif changed > self.budget.max_changed_bytes or compute > self.budget.max_compute_units or attempts >= self.budget.max_attempts:
            next_state = replace(next_state, status=CorrectionSessionStatus.STOPPED, stop_reason=CorrectionStopReason.RESOURCE_EXHAUSTION)
        elif repeat_map[defect_fingerprint] > self.budget.max_defect_repeats:
            next_state = replace(next_state, status=CorrectionSessionStatus.STOPPED, stop_reason=CorrectionStopReason.REPEATED_DEFECT)
        elif oscillation > self.budget.max_oscillations:
            next_state = replace(next_state, status=CorrectionSessionStatus.STOPPED, stop_reason=CorrectionStopReason.OSCILLATION)
        elif no_progress > self.budget.max_no_progress:
            next_state = replace(next_state, status=CorrectionSessionStatus.STOPPED, stop_reason=CorrectionStopReason.NO_PROGRESS)
        else:
            boundary = self._boundary_reason(candidate.defects)
            if boundary is not None:
                next_state = replace(next_state, status=CorrectionSessionStatus.STOPPED, stop_reason=boundary)

        return self._save(next_state)

    def run(self, *, initial_lineage_id: str) -> CorrectionSessionState:
        state = self._initialize(initial_lineage_id)
        while state.status is CorrectionSessionStatus.ACTIVE:
            state = self.advance(initial_lineage_id=initial_lineage_id)
        return state

    def dispatch(self, state: CorrectionSessionState, *, receiving_class: str) -> FailureDispatch:
        if state.status is not CorrectionSessionStatus.STOPPED or state.stop_reason is None:
            raise CorrectionPolicyError("failure dispatch requires a stopped bounded correction session")
        fingerprint = _defect_set_fingerprint(state.current_defects)
        reproducible = bool(state.current_defects) and all(item.reproducible for item in state.current_defects)
        return FailureDispatch(
            project_id=state.project_id,
            run_id=state.run_id,
            work_specification_digest=state.work_specification_digest,
            source_lineage_id=state.current_lineage_id,
            lkg_lineage_id=state.lkg_lineage_id,
            defect_fingerprint=fingerprint,
            evidence_refs=state.evidence_refs,
            dependency_refs=self.context.dependencies,
            receiving_class=receiving_class,
            stop_reason=state.stop_reason,
            reproducible=reproducible,
        )


__all__ = [
    "AutonomousCorrectionController",
    "CandidateValidation",
    "CorrectionBoundary",
    "CorrectionBudgetPolicy",
    "CorrectionCheckpointSink",
    "CorrectionContext",
    "CorrectionError",
    "CorrectionIdentityError",
    "CorrectionMutationResult",
    "CorrectionMutationRuntime",
    "CorrectionPathPolicy",
    "CorrectionPlan",
    "CorrectionPlanner",
    "CorrectionPolicyError",
    "CorrectionReplayConflict",
    "CorrectionSessionState",
    "CorrectionSessionStatus",
    "CorrectionStateConflict",
    "CorrectionStateStore",
    "CorrectionStopReason",
    "CorrectionValidator",
    "DefectPrecedence",
    "DefectSeverity",
    "DefectSource",
    "EngineeringAttemptCorrectionStateStore",
    "FailureDispatch",
    "NormalizedDefect",
    "ProtectedQualityVector",
    "VisualDisposition",
    "WorkerCorrectionCheckpointSink",
    "candidate_from_browser",
    "normalize_failure",
]
