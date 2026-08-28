from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import math
import re
from typing import Iterable, Mapping
from uuid import UUID

from parallax_api.models import EngineeringAttempt, EngineeringRun

from .run_events import RunEvent


_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_AC_RE = re.compile(r"^AC-[0-9]{2,3}$")
_ACTION_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_MAX_EVENTS = 512
_MAX_ATTEMPTS = 256
_MAX_ACCEPTANCE_IDS = 128


class AgentRunProjectionError(ValueError):
    """Fail-closed error for malformed or cross-boundary projection evidence."""


class ProjectionKnownState(StrEnum):
    OBSERVED = "OBSERVED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class ProjectionMetric(StrEnum):
    ELAPSED_TIME = "elapsed_time"
    COST_USAGE = "cost_usage"
    HUMAN_INTERVENTIONS = "human_interventions"


class ProjectionControlDenyReason(StrEnum):
    PROJECT_MISMATCH = "PROJECT_MISMATCH"
    RUN_MISMATCH = "RUN_MISMATCH"
    REVISION_MISMATCH = "REVISION_MISMATCH"
    STATE_MISMATCH = "STATE_MISMATCH"
    UNSUPPORTED_CONTROL = "UNSUPPORTED_CONTROL"


@dataclass(frozen=True, slots=True)
class ProjectionIdentity:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "work_specification_id",
            _uuid(self.work_specification_id, "work_specification_id"),
        )
        if (
            not isinstance(self.work_specification_revision, int)
            or isinstance(self.work_specification_revision, bool)
            or self.work_specification_revision < 1
        ):
            raise AgentRunProjectionError("work_specification_revision must be >= 1")
        object.__setattr__(
            self,
            "work_specification_digest",
            _sha(self.work_specification_digest, "work_specification_digest"),
        )
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
        }


@dataclass(frozen=True, slots=True)
class ProjectedAttempt:
    attempt_id: str
    stage: str
    attempt_number: int
    status: str
    failure_code: str | None
    program_id: str | None
    tool_id: str | None

    @classmethod
    def from_attempt(cls, attempt: EngineeringAttempt) -> "ProjectedAttempt":
        return cls(
            attempt_id=_uuid(attempt.id, "attempt_id"),
            stage=_bounded(attempt.stage, "stage", 32),
            attempt_number=_positive_int(attempt.attempt_number, "attempt_number"),
            status=_bounded(attempt.status, "status", 32),
            failure_code=_optional_bounded(attempt.failure_code, "failure_code", 120),
            program_id=_optional_bounded(attempt.program_id, "program_id", 160),
            tool_id=_optional_bounded(attempt.tool_id, "tool_id", 160),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "stage": self.stage,
            "attempt_number": self.attempt_number,
            "status": self.status,
            "failure_code": self.failure_code,
            "program_id": self.program_id,
            "tool_id": self.tool_id,
        }


@dataclass(frozen=True, slots=True)
class ProjectedEvent:
    sequence: int
    event_type: str
    outcome: str
    subsystem: str
    stage: str | None
    attempt_id: str | None
    worker_execution_id: str | None
    source_lineage_ref: str | None
    evidence_ref: str | None
    failure_code: str | None
    summary: str | None
    metadata: tuple[tuple[str, object], ...]

    @classmethod
    def from_event(cls, event: RunEvent) -> "ProjectedEvent":
        append = event.append
        return cls(
            sequence=_positive_int(event.sequence, "event sequence"),
            event_type=append.event_type.value,
            outcome=append.outcome.value,
            subsystem=append.subsystem.value,
            stage=append.stage,
            attempt_id=append.attempt_id,
            worker_execution_id=append.worker_execution_id,
            source_lineage_ref=append.source_lineage_ref,
            evidence_ref=append.evidence_ref,
            failure_code=append.failure_code,
            summary=append.summary,
            metadata=tuple(sorted(dict(append.metadata).items())),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "outcome": self.outcome,
            "subsystem": self.subsystem,
            "stage": self.stage,
            "attempt_id": self.attempt_id,
            "worker_execution_id": self.worker_execution_id,
            "source_lineage_ref": self.source_lineage_ref,
            "evidence_ref": self.evidence_ref,
            "failure_code": self.failure_code,
            "summary": self.summary,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ProjectionMetricEvidence:
    metric: ProjectionMetric
    state: ProjectionKnownState
    value: float | None
    provenance_ref: str | None

    def __post_init__(self) -> None:
        try:
            metric = self.metric if isinstance(self.metric, ProjectionMetric) else ProjectionMetric(self.metric)
            state = self.state if isinstance(self.state, ProjectionKnownState) else ProjectionKnownState(self.state)
        except (TypeError, ValueError) as exc:
            raise AgentRunProjectionError("invalid projection metric/state") from exc
        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "state", state)
        if state is ProjectionKnownState.UNKNOWN:
            if self.value is not None or self.provenance_ref is not None:
                raise AgentRunProjectionError("unknown metric cannot carry value or provenance")
            return
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise AgentRunProjectionError("known metric requires numeric value")
        value = float(self.value)
        if not math.isfinite(value) or value < 0:
            raise AgentRunProjectionError("metric value must be finite and non-negative")
        object.__setattr__(self, "value", value)
        if self.provenance_ref is None:
            raise AgentRunProjectionError("known metric requires provenance_ref")
        object.__setattr__(self, "provenance_ref", _bounded(self.provenance_ref, "provenance_ref", 200))

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric.value,
            "state": self.state.value,
            "value": self.value,
            "provenance_ref": self.provenance_ref,
        }


@dataclass(frozen=True, slots=True)
class ProjectionControlRequest:
    project_id: str
    run_id: str
    expected_revision: int
    expected_state: str
    action: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        if not isinstance(self.expected_revision, int) or isinstance(self.expected_revision, bool) or self.expected_revision < 0:
            raise AgentRunProjectionError("expected_revision must be >= 0")
        object.__setattr__(self, "expected_state", _bounded(self.expected_state, "expected_state", 32))
        if not isinstance(self.action, str) or _ACTION_RE.fullmatch(self.action) is None:
            raise AgentRunProjectionError("action is invalid or unbounded")


@dataclass(frozen=True, slots=True)
class ProjectionControlDecision:
    allowed: bool
    deny_reason: ProjectionControlDenyReason

    def __post_init__(self) -> None:
        if self.allowed:
            raise AgentRunProjectionError("Wave 7 S2 v1 projection does not grant control authority")
        try:
            object.__setattr__(self, "deny_reason", ProjectionControlDenyReason(self.deny_reason))
        except ValueError as exc:
            raise AgentRunProjectionError("invalid projection control deny reason") from exc


@dataclass(frozen=True, slots=True)
class AgentRunProjection:
    identity: ProjectionIdentity
    current_state: str
    run_revision: int
    resume_stage: str | None
    last_failure_code: str | None
    latest_source_lineage_ref: str | None
    preview_deployment_id: str | None
    preview_status: str | None
    attempts: tuple[ProjectedAttempt, ...]
    events: tuple[ProjectedEvent, ...]
    metrics: tuple[ProjectionMetricEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ProjectionIdentity):
            raise AgentRunProjectionError("projection requires canonical identity")
        object.__setattr__(self, "current_state", _bounded(self.current_state, "current_state", 32))
        if not isinstance(self.run_revision, int) or isinstance(self.run_revision, bool) or self.run_revision < 0:
            raise AgentRunProjectionError("run_revision must be >= 0")
        object.__setattr__(self, "resume_stage", _optional_bounded(self.resume_stage, "resume_stage", 32))
        object.__setattr__(self, "last_failure_code", _optional_bounded(self.last_failure_code, "last_failure_code", 120))
        if self.latest_source_lineage_ref is not None and _LINEAGE_RE.fullmatch(self.latest_source_lineage_ref) is None:
            raise AgentRunProjectionError("latest_source_lineage_ref is invalid")
        object.__setattr__(
            self,
            "preview_deployment_id",
            _optional_bounded(self.preview_deployment_id, "preview_deployment_id", 200),
        )
        object.__setattr__(self, "preview_status", _optional_bounded(self.preview_status, "preview_status", 80))
        attempts = tuple(self.attempts)
        events = tuple(self.events)
        metrics = tuple(self.metrics)
        if len(attempts) > _MAX_ATTEMPTS or len(events) > _MAX_EVENTS:
            raise AgentRunProjectionError("projection evidence exceeds bounded cardinality")
        if any(not isinstance(item, ProjectedAttempt) for item in attempts):
            raise AgentRunProjectionError("projection attempts must be canonical")
        if any(not isinstance(item, ProjectedEvent) for item in events):
            raise AgentRunProjectionError("projection events must be canonical")
        if any(not isinstance(item, ProjectionMetricEvidence) for item in metrics):
            raise AgentRunProjectionError("projection metrics must be canonical")
        if len({item.attempt_id for item in attempts}) != len(attempts):
            raise AgentRunProjectionError("projection attempt identities must be unique")
        if tuple(item.sequence for item in events) != tuple(sorted(item.sequence for item in events)):
            raise AgentRunProjectionError("projection events must be sequence ordered")
        if len({item.sequence for item in events}) != len(events):
            raise AgentRunProjectionError("projection event sequences must be unique")
        if {item.metric for item in metrics} != set(ProjectionMetric) or len(metrics) != len(ProjectionMetric):
            raise AgentRunProjectionError("projection must report each runtime metric exactly once")
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "metrics", tuple(sorted(metrics, key=lambda item: item.metric.value)))

    @property
    def fingerprint(self) -> str:
        return _digest(self.as_dict(include_fingerprint=False))

    def as_dict(self, *, include_fingerprint: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "projection_version": 1,
            "identity": self.identity.as_dict(),
            "current_state": self.current_state,
            "run_revision": self.run_revision,
            "resume_stage": self.resume_stage,
            "last_failure_code": self.last_failure_code,
            "latest_source_lineage_ref": self.latest_source_lineage_ref,
            "preview_deployment_id": self.preview_deployment_id,
            "preview_status": self.preview_status,
            "attempts": [item.as_dict() for item in self.attempts],
            "events": [item.as_dict() for item in self.events],
            "metrics": [item.as_dict() for item in self.metrics],
            "advertised_controls": [],
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
            "grants_provider_authority": False,
            "grants_tool_authority": False,
            "executes_arbitrary_command": False,
            "performs_merge": False,
            "performs_production_deployment": False,
            "completes_review": False,
            "contains_source_bytes": False,
            "contains_patch": False,
            "contains_credentials": False,
            "contains_provider_payload": False,
            "contains_prompts": False,
            "contains_hidden_reasoning": False,
            "contains_unrestricted_logs": False,
        }
        if include_fingerprint:
            data["fingerprint"] = self.fingerprint
        return data


def build_agent_run_projection(
    *,
    run: EngineeringRun,
    acceptance_ids: Iterable[str],
    events: Iterable[RunEvent] = (),
    metrics: Iterable[ProjectionMetricEvidence] = (),
) -> AgentRunProjection:
    """Project existing authoritative facts without creating a second state machine."""

    if not isinstance(run, EngineeringRun):
        raise AgentRunProjectionError("run must be an EngineeringRun")
    if run.project_id is None or run.work_specification_id is None or run.work_specification_revision is None or run.work_specification_digest is None:
        raise AgentRunProjectionError("projection requires a Project-bound approved Work Specification run")
    identity = ProjectionIdentity(
        project_id=run.project_id,
        run_id=run.id,
        work_specification_id=run.work_specification_id,
        work_specification_revision=run.work_specification_revision,
        work_specification_digest=run.work_specification_digest,
        acceptance_ids=tuple(acceptance_ids),
    )

    canonical_events: list[ProjectedEvent] = []
    latest_lineage: str | None = None
    preview_deployment_id: str | None = None
    preview_status: str | None = None
    for event in sorted(tuple(events), key=lambda item: item.sequence):
        if not isinstance(event, RunEvent):
            raise AgentRunProjectionError("events must contain canonical RunEvent values")
        if event.project_id != identity.project_id or event.run_id != identity.run_id:
            raise AgentRunProjectionError("cross-Project or cross-run event cannot satisfy projection")
        projected = ProjectedEvent.from_event(event)
        canonical_events.append(projected)
        if projected.source_lineage_ref is not None:
            latest_lineage = projected.source_lineage_ref
        metadata = dict(projected.metadata)
        deployment = metadata.get("preview_deployment_id")
        status = metadata.get("preview_status")
        if isinstance(deployment, str):
            preview_deployment_id = deployment
        if isinstance(status, str):
            preview_status = status

    projected_attempts = tuple(
        ProjectedAttempt.from_attempt(item)
        for item in sorted(
            tuple(run.attempts),
            key=lambda item: (item.started_at, item.attempt_number, item.id),
        )
    )
    supplied_metrics = tuple(metrics)
    by_metric = {item.metric: item for item in supplied_metrics if isinstance(item, ProjectionMetricEvidence)}
    if len(by_metric) != len(supplied_metrics):
        raise AgentRunProjectionError("metrics must be unique canonical ProjectionMetricEvidence values")
    complete_metrics = tuple(
        by_metric.get(
            metric,
            ProjectionMetricEvidence(metric=metric, state=ProjectionKnownState.UNKNOWN, value=None, provenance_ref=None),
        )
        for metric in ProjectionMetric
    )
    return AgentRunProjection(
        identity=identity,
        current_state=run.state,
        run_revision=run.revision,
        resume_stage=run.resume_stage,
        last_failure_code=run.last_failure_code,
        latest_source_lineage_ref=latest_lineage,
        preview_deployment_id=preview_deployment_id,
        preview_status=preview_status,
        attempts=projected_attempts,
        events=tuple(canonical_events),
        metrics=complete_metrics,
    )


def decide_projection_control(
    projection: AgentRunProjection,
    request: ProjectionControlRequest,
) -> ProjectionControlDecision:
    """Fail closed until a separately accepted server authority is wired to S2."""

    if request.project_id != projection.identity.project_id:
        reason = ProjectionControlDenyReason.PROJECT_MISMATCH
    elif request.run_id != projection.identity.run_id:
        reason = ProjectionControlDenyReason.RUN_MISMATCH
    elif request.expected_revision != projection.run_revision:
        reason = ProjectionControlDenyReason.REVISION_MISMATCH
    elif request.expected_state != projection.current_state:
        reason = ProjectionControlDenyReason.STATE_MISMATCH
    else:
        reason = ProjectionControlDenyReason.UNSUPPORTED_CONTROL
    return ProjectionControlDecision(allowed=False, deny_reason=reason)


def safe_agent_run_projection_json(projection: AgentRunProjection) -> str:
    if not isinstance(projection, AgentRunProjection):
        raise AgentRunProjectionError("projection must be AgentRunProjection")
    return json.dumps(projection.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _uuid(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise AgentRunProjectionError(f"{field} must be a canonical UUID")
    try:
        parsed = str(UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise AgentRunProjectionError(f"{field} must be a canonical UUID") from exc
    if parsed != value:
        raise AgentRunProjectionError(f"{field} must use canonical lowercase UUID form")
    return parsed


def _sha(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise AgentRunProjectionError(f"{field} must be a lowercase sha256 digest")
    return value


def _bounded(value: str, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise AgentRunProjectionError(f"{field} must be text")
    candidate = value.strip()
    if not candidate or len(candidate) > limit or "\x00" in candidate:
        raise AgentRunProjectionError(f"{field} is empty or unbounded")
    return candidate


def _optional_bounded(value: str | None, field: str, limit: int) -> str | None:
    return None if value is None else _bounded(value, field, limit)


def _positive_int(value: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise AgentRunProjectionError(f"{field} must be a positive integer")
    return value


def _acceptance_ids(values: Iterable[str]) -> tuple[str, ...]:
    ids = tuple(values)
    if not ids or len(ids) > _MAX_ACCEPTANCE_IDS:
        raise AgentRunProjectionError("acceptance_ids are empty or unbounded")
    if len(set(ids)) != len(ids) or any(not isinstance(item, str) or _AC_RE.fullmatch(item) is None for item in ids):
        raise AgentRunProjectionError("acceptance_ids must be unique stable AC identities")
    return tuple(sorted(ids))


def _digest(value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()
