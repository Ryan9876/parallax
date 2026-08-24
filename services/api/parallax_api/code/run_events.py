from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import math
from types import MappingProxyType
import re
from typing import Mapping, Protocol
from uuid import UUID


MAX_EVENT_KEY = 160
MAX_SUMMARY = 360
MAX_METADATA_BYTES = 4_000
MAX_METADATA_ITEMS = 20
MAX_METADATA_LIST_ITEMS = 32
MAX_METADATA_STRING = 240
MAX_REFERENCE = 200


_EVENT_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$")
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#@+-]{0,199}$")
_FAILURE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_:-]{0,119}$")
_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SECRET_LITERAL_RE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|authorization|cookie|credential)"
    r"\s*[:=]\s*['\"]?[^\s,'\"]{8,}"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


_METADATA_KEYS = frozenset(
    {
        "acceptance_count",
        "artifact_count",
        "attempt_number",
        "bounded_stop",
        "branch_name",
        "checkpoint_revision",
        "command_id",
        "commit_revision",
        "content_digest",
        "control_status",
        "current_state",
        "current_step",
        "delivery_action_count",
        "evaluation_id",
        "exit_code",
        "file_count",
        "lease_generation",
        "lineage_bound_execution",
        "meaningful_progress",
        "next_recovery_action",
        "no_progress_count",
        "oscillation_count",
        "preview_deployment_id",
        "preview_status",
        "program_id",
        "pull_request_number",
        "redacted",
        "retry_count",
        "run_revision",
        "score_class",
        "source_revision",
        "stall_classification",
        "stop_reason",
        "target_state",
        "timed_out",
        "tool_id",
        "worker_state",
        "workspace_digest",
    }
)


class RunEventType(str, Enum):
    RUN_CREATED = "RUN_CREATED"
    STAGE_RESULT = "STAGE_RESULT"
    OPERATION_REPLAY = "OPERATION_REPLAY"
    RUN_CONTROL = "RUN_CONTROL"
    SOURCE_LINEAGE_ACCEPTED = "SOURCE_LINEAGE_ACCEPTED"
    SOURCE_DELIVERY = "SOURCE_DELIVERY"
    PROVIDER_RESULT = "PROVIDER_RESULT"
    EVALUATION_RESULT = "EVALUATION_RESULT"
    WORKER_STATE = "WORKER_STATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class RunEventOutcome(str, Enum):
    STARTED = "STARTED"
    PROGRESSED = "PROGRESSED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DENIED = "DENIED"
    REPLAYED = "REPLAYED"
    RECOVERING = "RECOVERING"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    INFO = "INFO"


class RunEventSubsystem(str, Enum):
    RUN = "RUN"
    IMPLEMENTATION = "IMPLEMENTATION"
    EXECUTION = "EXECUTION"
    WORKER = "WORKER"
    SOURCE_LINEAGE = "SOURCE_LINEAGE"
    GITHUB = "GITHUB"
    VERCEL = "VERCEL"
    EVALUATION = "EVALUATION"
    REVIEW = "REVIEW"


class RunEventError(RuntimeError):
    pass


class RunEventValidationError(ValueError, RunEventError):
    pass


class RunEventScopeError(RunEventError):
    pass


class RunEventConflict(RunEventError):
    pass


class RunEventPersistenceError(RunEventError):
    pass


def _canonical_uuid(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise RunEventValidationError(f"{field_name} must be a canonical UUID string")
    try:
        parsed = UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise RunEventValidationError(f"{field_name} must be a canonical UUID string") from exc
    canonical = str(parsed)
    if value != canonical:
        raise RunEventValidationError(f"{field_name} must use canonical lowercase UUID form")
    return canonical


def _bounded_ref(value: str | None, *, field_name: str, uuid: bool = False) -> str | None:
    if value is None:
        return None
    if uuid:
        return _canonical_uuid(value, field_name=field_name)
    if not isinstance(value, str) or len(value) > MAX_REFERENCE or _REFERENCE_RE.fullmatch(value) is None:
        raise RunEventValidationError(f"{field_name} is invalid or unbounded")
    return value


def _lineage(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _LINEAGE_RE.fullmatch(value) is None:
        raise RunEventValidationError(f"{field_name} must be a protected source-lineage identity")
    return value


def _failure_code(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _FAILURE_CODE_RE.fullmatch(value) is None:
        raise RunEventValidationError("failure_code is invalid or unbounded")
    return value


def _safe_text(value: str, *, field_name: str, limit: int) -> str:
    if not isinstance(value, str):
        raise RunEventValidationError(f"{field_name} must be text")
    candidate = value.strip()
    if not candidate or len(candidate) > limit:
        raise RunEventValidationError(f"{field_name} is empty or unbounded")
    if "\x00" in candidate:
        raise RunEventValidationError(f"{field_name} contains a forbidden NUL byte")
    if _SECRET_LITERAL_RE.search(candidate) or _BEARER_RE.search(candidate) or _PRIVATE_KEY_RE.search(candidate):
        raise RunEventValidationError(f"{field_name} appears to contain credential material")
    return candidate


def _safe_metadata_value(value: object, *, key: str) -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RunEventValidationError(f"metadata {key} contains a non-finite number")
        return value
    if isinstance(value, str):
        candidate = _safe_text(value, field_name=f"metadata {key}", limit=MAX_METADATA_STRING)
        if key in {"content_digest", "workspace_digest"} and _HEX64_RE.fullmatch(candidate) is None:
            raise RunEventValidationError(f"metadata {key} must be a lowercase sha256 digest")
        return candidate
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_METADATA_LIST_ITEMS:
            raise RunEventValidationError(f"metadata {key} list is unbounded")
        normalized = []
        for item in value:
            if isinstance(item, (dict, list, tuple, set)):
                raise RunEventValidationError(f"metadata {key} cannot contain nested structures")
            normalized.append(_safe_metadata_value(item, key=key))
        return normalized
    raise RunEventValidationError(f"metadata {key} contains an unsupported value type")


def normalize_metadata(metadata: Mapping[str, object] | None) -> Mapping[str, object]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping) or len(metadata) > MAX_METADATA_ITEMS:
        raise RunEventValidationError("event metadata is invalid or unbounded")
    normalized: dict[str, object] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or key not in _METADATA_KEYS:
            raise RunEventValidationError(f"event metadata key {key!r} is not allowlisted")
        normalized[key] = _safe_metadata_value(value, key=key)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
        raise RunEventValidationError("event metadata exceeds the protected byte bound")
    return MappingProxyType(normalized)


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise RunEventValidationError("occurred_at must be a datetime")
    if value.tzinfo is None:
        raise RunEventValidationError("occurred_at must be timezone aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class RunEventAppend:
    project_id: str
    run_id: str
    event_key: str
    event_type: RunEventType
    outcome: RunEventOutcome
    subsystem: RunEventSubsystem
    occurred_at: datetime
    stage: str | None = None
    attempt_id: str | None = None
    worker_execution_id: str | None = None
    source_lineage_ref: str | None = None
    parent_source_lineage_ref: str | None = None
    operation_ref: str | None = None
    artifact_ref: str | None = None
    evidence_ref: str | None = None
    failure_code: str | None = None
    summary: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _canonical_uuid(self.project_id, field_name="project_id"))
        object.__setattr__(self, "run_id", _canonical_uuid(self.run_id, field_name="run_id"))
        if not isinstance(self.event_key, str) or _EVENT_KEY_RE.fullmatch(self.event_key) is None:
            raise RunEventValidationError("event_key is invalid or unbounded")
        try:
            object.__setattr__(self, "event_type", RunEventType(self.event_type))
            object.__setattr__(self, "outcome", RunEventOutcome(self.outcome))
            object.__setattr__(self, "subsystem", RunEventSubsystem(self.subsystem))
        except ValueError as exc:
            raise RunEventValidationError("event type/outcome/subsystem is outside the protected vocabulary") from exc
        if self.stage is not None:
            from .domain import WorkflowStage

            try:
                stage = WorkflowStage(self.stage).value
            except ValueError as exc:
                raise RunEventValidationError("stage is outside the protected Engineering Run vocabulary") from exc
            object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "attempt_id", _bounded_ref(self.attempt_id, field_name="attempt_id", uuid=True))
        object.__setattr__(
            self,
            "worker_execution_id",
            _bounded_ref(self.worker_execution_id, field_name="worker_execution_id", uuid=True),
        )
        object.__setattr__(
            self,
            "source_lineage_ref",
            _lineage(self.source_lineage_ref, field_name="source_lineage_ref"),
        )
        object.__setattr__(
            self,
            "parent_source_lineage_ref",
            _lineage(self.parent_source_lineage_ref, field_name="parent_source_lineage_ref"),
        )
        object.__setattr__(self, "operation_ref", _bounded_ref(self.operation_ref, field_name="operation_ref"))
        object.__setattr__(self, "artifact_ref", _bounded_ref(self.artifact_ref, field_name="artifact_ref"))
        object.__setattr__(self, "evidence_ref", _bounded_ref(self.evidence_ref, field_name="evidence_ref"))
        object.__setattr__(self, "failure_code", _failure_code(self.failure_code))
        if self.summary is not None:
            object.__setattr__(self, "summary", _safe_text(self.summary, field_name="summary", limit=MAX_SUMMARY))
        object.__setattr__(self, "metadata", normalize_metadata(self.metadata))
        object.__setattr__(self, "occurred_at", _aware_utc(self.occurred_at))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "event_key": self.event_key,
            "event_type": self.event_type.value,
            "outcome": self.outcome.value,
            "subsystem": self.subsystem.value,
            "stage": self.stage,
            "attempt_id": self.attempt_id,
            "worker_execution_id": self.worker_execution_id,
            "source_lineage_ref": self.source_lineage_ref,
            "parent_source_lineage_ref": self.parent_source_lineage_ref,
            "operation_ref": self.operation_ref,
            "artifact_ref": self.artifact_ref,
            "evidence_ref": self.evidence_ref,
            "failure_code": self.failure_code,
            "summary": self.summary,
            "metadata": dict(self.metadata),
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class RunEvent:
    id: str
    sequence: int
    created_at: datetime
    append: RunEventAppend

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _canonical_uuid(self.id, field_name="event id"))
        if not isinstance(self.sequence, int) or self.sequence < 1:
            raise RunEventValidationError("event sequence must be a positive integer")
        object.__setattr__(self, "created_at", _aware_utc(self.created_at))

    @property
    def project_id(self) -> str:
        return self.append.project_id

    @property
    def run_id(self) -> str:
        return self.append.run_id

    @property
    def event_key(self) -> str:
        return self.append.event_key


@dataclass(frozen=True, slots=True)
class RunEventAppendResult:
    event: RunEvent
    replayed: bool


class RunEventSink(Protocol):
    def emit(self, event: RunEventAppend) -> RunEventAppendResult: ...


class RecordingRunEventSink:
    """Deterministic test sink; never used as production persistence authority."""

    def __init__(self) -> None:
        self.events: list[RunEventAppend] = []

    def emit(self, event: RunEventAppend) -> RunEventAppendResult:
        self.events.append(event)
        synthetic = RunEvent(
            id="00000000-0000-4000-8000-000000000001",
            sequence=len(self.events),
            created_at=event.occurred_at,
            append=event,
        )
        return RunEventAppendResult(event=synthetic, replayed=False)


__all__ = [
    "MAX_METADATA_BYTES",
    "RecordingRunEventSink",
    "RunEvent",
    "RunEventAppend",
    "RunEventAppendResult",
    "RunEventConflict",
    "RunEventError",
    "RunEventOutcome",
    "RunEventPersistenceError",
    "RunEventScopeError",
    "RunEventSink",
    "RunEventSubsystem",
    "RunEventType",
    "RunEventValidationError",
    "normalize_metadata",
]
