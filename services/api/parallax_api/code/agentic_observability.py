from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
import math
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence
from uuid import UUID

from parallax_api.models import EngineeringRun
from parallax_api.repositories.worker_executions import EngineeringWorkerExecution

from .agent_run_projection import (
    DeterministicDisposition,
    ProjectionKnownState,
    ProjectionMetric,
    ProjectionMetricEvidence,
    build_agent_run_projection,
)
from .domain import AttemptStatus, WorkflowStage
from .run_events import RunEvent, RunEventOutcome, RunEventType
from .service import EngineeringRunService


_MAX_HISTORY = 25
_MAX_EVENTS = 200
_MAX_METRICS = 16


class AgenticObservabilityError(ValueError):
    """Fail-closed error for malformed or unsupported S5 evidence."""


class AgenticObservabilityScopeError(AgenticObservabilityError):
    """Requested Project/run evidence is outside the authorized canonical scope."""


class RuntimeMetricId(StrEnum):
    RUN_ELAPSED_SECONDS = "run.elapsed_seconds"
    ATTEMPT_RETRY_COUNT = "attempt.retry_count"
    WORKER_RETRY_COUNT = "worker.retry_count"
    HUMAN_INTERVENTION_COUNT = "human.intervention_count"
    PROVIDER_USAGE_UNITS = "provider.usage_units"
    PROVIDER_COST_USD = "provider.cost_usd"


class RetentionClass(StrEnum):
    CANONICAL_REFERENCE = "CANONICAL_REFERENCE"
    PROTECTED_RELEASE_EVIDENCE = "PROTECTED_RELEASE_EVIDENCE"
    OPERATIONAL_SUMMARY = "OPERATIONAL_SUMMARY"
    EPHEMERAL_DIAGNOSTIC = "EPHEMERAL_DIAGNOSTIC"


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric: RuntimeMetricId
    unit: str
    source_kind: str
    retention_class: RetentionClass

    def as_dict(self) -> dict[str, str]:
        return {
            "metric": self.metric.value,
            "unit": self.unit,
            "source_kind": self.source_kind,
            "retention_class": self.retention_class.value,
        }


METRIC_CATALOG: Mapping[RuntimeMetricId, MetricDefinition] = MappingProxyType(
    {
        RuntimeMetricId.RUN_ELAPSED_SECONDS: MetricDefinition(
            RuntimeMetricId.RUN_ELAPSED_SECONDS,
            "seconds",
            "engineering_run.timestamps",
            RetentionClass.OPERATIONAL_SUMMARY,
        ),
        RuntimeMetricId.ATTEMPT_RETRY_COUNT: MetricDefinition(
            RuntimeMetricId.ATTEMPT_RETRY_COUNT,
            "count",
            "engineering_run.attempts",
            RetentionClass.OPERATIONAL_SUMMARY,
        ),
        RuntimeMetricId.WORKER_RETRY_COUNT: MetricDefinition(
            RuntimeMetricId.WORKER_RETRY_COUNT,
            "count",
            "engineering_worker_execution.retry_count",
            RetentionClass.OPERATIONAL_SUMMARY,
        ),
        RuntimeMetricId.HUMAN_INTERVENTION_COUNT: MetricDefinition(
            RuntimeMetricId.HUMAN_INTERVENTION_COUNT,
            "count",
            "engineering_run.attempts+run_events",
            RetentionClass.OPERATIONAL_SUMMARY,
        ),
        RuntimeMetricId.PROVIDER_USAGE_UNITS: MetricDefinition(
            RuntimeMetricId.PROVIDER_USAGE_UNITS,
            "usage_units",
            "provider_evidence",
            RetentionClass.OPERATIONAL_SUMMARY,
        ),
        RuntimeMetricId.PROVIDER_COST_USD: MetricDefinition(
            RuntimeMetricId.PROVIDER_COST_USD,
            "usd",
            "provider_evidence+server_price_table",
            RetentionClass.OPERATIONAL_SUMMARY,
        ),
    }
)


@dataclass(frozen=True, slots=True)
class RuntimeMetricEvidence:
    metric: RuntimeMetricId
    state: ProjectionKnownState
    value: float | None
    provenance_ref: str | None

    def __post_init__(self) -> None:
        try:
            metric = self.metric if isinstance(self.metric, RuntimeMetricId) else RuntimeMetricId(self.metric)
            state = self.state if isinstance(self.state, ProjectionKnownState) else ProjectionKnownState(self.state)
        except (TypeError, ValueError) as exc:
            raise AgenticObservabilityError("invalid runtime metric identity/state") from exc
        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "state", state)
        if state is ProjectionKnownState.UNKNOWN:
            if self.value is not None or self.provenance_ref is not None:
                raise AgenticObservabilityError("UNKNOWN metric cannot carry value or provenance")
            return
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise AgenticObservabilityError("known runtime metric requires a numeric value")
        value = float(self.value)
        if not math.isfinite(value) or value < 0:
            raise AgenticObservabilityError("runtime metric value must be finite and non-negative")
        object.__setattr__(self, "value", value)
        if not isinstance(self.provenance_ref, str) or not self.provenance_ref or len(self.provenance_ref) > 200:
            raise AgenticObservabilityError("known runtime metric requires bounded provenance")

    @property
    def definition(self) -> MetricDefinition:
        return METRIC_CATALOG[self.metric]

    def as_dict(self) -> dict[str, object]:
        return {
            **self.definition.as_dict(),
            "state": self.state.value,
            "value": self.value,
            "provenance_ref": self.provenance_ref,
        }


@dataclass(frozen=True, slots=True)
class QualityProjection:
    deterministic_disposition: DeterministicDisposition
    effective_disposition: DeterministicDisposition
    evaluation_outcome: str | None
    preview_status: str | None
    deterministic_failure_authoritative: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "deterministic_disposition": self.deterministic_disposition.value,
            "effective_disposition": self.effective_disposition.value,
            "evaluation_outcome": self.evaluation_outcome,
            "preview_status": self.preview_status,
            "deterministic_failure_authoritative": self.deterministic_failure_authoritative,
        }


@dataclass(frozen=True, slots=True)
class RetentionProjection:
    mode: str = "QUERY_TIME"
    persisted_derived_rows: bool = False
    cleanup_required: bool = False
    cleanup_mutation_available: bool = False
    canonical_deletion_authority: bool = False
    audit_ref: str = "s5-retention:query-time:v1"

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "persisted_derived_rows": self.persisted_derived_rows,
            "cleanup_required": self.cleanup_required,
            "cleanup_mutation_available": self.cleanup_mutation_available,
            "canonical_deletion_authority": self.canonical_deletion_authority,
            "audit_ref": self.audit_ref,
        }


QUERY_TIME_RETENTION = RetentionProjection()


@dataclass(frozen=True, slots=True)
class RuntimeEvidenceCoverage:
    attempt_count: int
    unique_event_count: int
    event_plane_available: bool
    event_plane_complete: bool
    worker_evidence_available: bool
    known_metric_count: int
    estimated_metric_count: int
    unknown_metric_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "attempt_count": self.attempt_count,
            "unique_event_count": self.unique_event_count,
            "event_plane_available": self.event_plane_available,
            "event_plane_complete": self.event_plane_complete,
            "worker_evidence_available": self.worker_evidence_available,
            "known_metric_count": self.known_metric_count,
            "estimated_metric_count": self.estimated_metric_count,
            "unknown_metric_count": self.unknown_metric_count,
        }


@dataclass(frozen=True, slots=True)
class AgenticRunObservability:
    project_id: str
    run_id: str
    run_state: str
    run_revision: int
    projection_fingerprint: str
    latest_event_sequence: int
    metrics: tuple[RuntimeMetricEvidence, ...]
    s2_compatible_metrics: tuple[ProjectionMetricEvidence, ...]
    quality: QualityProjection
    coverage: RuntimeEvidenceCoverage
    retention: RetentionProjection = QUERY_TIME_RETENTION

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _canonical_uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _canonical_uuid(self.run_id, "run_id"))
        if not isinstance(self.run_revision, int) or isinstance(self.run_revision, bool) or self.run_revision < 0:
            raise AgenticObservabilityError("run_revision must be non-negative")
        if not isinstance(self.latest_event_sequence, int) or self.latest_event_sequence < 0:
            raise AgenticObservabilityError("latest_event_sequence must be non-negative")
        if len(self.metrics) > _MAX_METRICS:
            raise AgenticObservabilityError("runtime metric cardinality exceeds server bound")

    @property
    def fingerprint(self) -> str:
        return _digest(self.as_dict(include_fingerprint=False))

    def as_dict(self, *, include_fingerprint: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "observability_version": 1,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "run_state": self.run_state,
            "run_revision": self.run_revision,
            "projection_fingerprint": self.projection_fingerprint,
            "latest_event_sequence": self.latest_event_sequence,
            "metrics": [item.as_dict() for item in self.metrics],
            "s2_compatible_metrics": [item.as_dict() for item in self.s2_compatible_metrics],
            "quality": self.quality.as_dict(),
            "coverage": self.coverage.as_dict(),
            "retention": self.retention.as_dict(),
            "creates_scheduler": False,
            "creates_billing_ledger": False,
            "creates_state_machine": False,
            "grants_lifecycle_authority": False,
            "grants_source_authority": False,
            "grants_provider_authority": False,
            "grants_tool_authority": False,
            "executes_arbitrary_command": False,
            "performs_arbitrary_network": False,
            "performs_merge": False,
            "performs_production_deployment": False,
            "completes_review": False,
            "contains_credentials": False,
            "contains_provider_payload": False,
            "contains_prompts": False,
            "contains_hidden_reasoning": False,
            "contains_source_bytes": False,
            "contains_unrestricted_logs": False,
        }
        if include_fingerprint:
            data["fingerprint"] = self.fingerprint
        return data


@dataclass(frozen=True, slots=True)
class ProjectObservabilityHistory:
    project_id: str
    limit: int
    runs: tuple[AgenticRunObservability, ...]
    retention: RetentionProjection = QUERY_TIME_RETENTION

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _canonical_uuid(self.project_id, "project_id"))
        if not isinstance(self.limit, int) or isinstance(self.limit, bool) or not 1 <= self.limit <= _MAX_HISTORY:
            raise AgenticObservabilityError(f"history limit must be between 1 and {_MAX_HISTORY}")
        if len(self.runs) > self.limit:
            raise AgenticObservabilityError("history result exceeds requested bound")
        if any(item.project_id != self.project_id for item in self.runs):
            raise AgenticObservabilityScopeError("history contains cross-Project evidence")

    @property
    def fingerprint(self) -> str:
        return _digest(self.as_dict(include_fingerprint=False))

    def as_dict(self, *, include_fingerprint: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "observability_version": 1,
            "project_id": self.project_id,
            "limit": self.limit,
            "run_count": len(self.runs),
            "runs": [item.as_dict() for item in self.runs],
            "retention": self.retention.as_dict(),
            "cross_project_aggregate": False,
            "contains_private_project_payload": False,
        }
        if include_fingerprint:
            data["fingerprint"] = self.fingerprint
        return data


def build_agentic_run_observability(
    *,
    run: EngineeringRun,
    acceptance_ids: Iterable[str],
    events: Iterable[RunEvent] = (),
    worker: EngineeringWorkerExecution | None = None,
    event_plane_available: bool = False,
    event_plane_complete: bool | None = None,
    authoritative_latest_event_sequence: int | None = None,
) -> AgenticRunObservability:
    if not isinstance(run, EngineeringRun):
        raise AgenticObservabilityError("run must be an EngineeringRun")
    if run.project_id is None:
        raise AgenticObservabilityScopeError("historical unbound runs do not have Project-scoped observability")

    unique_events = _dedupe_events(run, events)
    loaded_latest_sequence = max((item.sequence for item in unique_events), default=0)
    latest_event_sequence = (
        loaded_latest_sequence
        if authoritative_latest_event_sequence is None
        else authoritative_latest_event_sequence
    )
    if not isinstance(latest_event_sequence, int) or latest_event_sequence < loaded_latest_sequence:
        raise AgenticObservabilityError("authoritative latest event sequence is inconsistent with loaded evidence")
    complete = event_plane_available if event_plane_complete is None else event_plane_complete
    if complete and not event_plane_available:
        raise AgenticObservabilityError("event plane cannot be complete when it is unavailable")

    projection = build_agent_run_projection(
        run=run,
        acceptance_ids=tuple(acceptance_ids),
        events=unique_events,
        worker=worker,
    )
    metrics = _runtime_metrics(
        run=run,
        events=unique_events,
        worker=worker,
        event_plane_available=event_plane_available,
        event_plane_complete=complete,
    )
    s2_metrics = _s2_compatible_metrics(metrics)
    quality = QualityProjection(
        deterministic_disposition=projection.deterministic_disposition,
        effective_disposition=projection.deterministic_disposition,
        evaluation_outcome=projection.evaluation.outcome if complete else None,
        preview_status=projection.delivery.preview_status if complete else None,
        deterministic_failure_authoritative=(
            projection.deterministic_disposition is DeterministicDisposition.FAILED
        ),
    )
    coverage = RuntimeEvidenceCoverage(
        attempt_count=len(tuple(run.attempts)),
        unique_event_count=len(unique_events),
        event_plane_available=event_plane_available,
        event_plane_complete=complete,
        worker_evidence_available=worker is not None,
        known_metric_count=sum(item.state is ProjectionKnownState.OBSERVED for item in metrics),
        estimated_metric_count=sum(item.state is ProjectionKnownState.ESTIMATED for item in metrics),
        unknown_metric_count=sum(item.state is ProjectionKnownState.UNKNOWN for item in metrics),
    )
    return AgenticRunObservability(
        project_id=run.project_id,
        run_id=run.id,
        run_state=run.state,
        run_revision=int(run.revision),
        projection_fingerprint=projection.fingerprint,
        latest_event_sequence=latest_event_sequence,
        metrics=metrics,
        s2_compatible_metrics=s2_metrics,
        quality=quality,
        coverage=coverage,
    )


class AgenticObservabilityService:
    """Read/derive facade over canonical S1/S2/Wave 4/Wave 6 evidence only."""

    def __init__(self, run_service: EngineeringRunService, workers, *, events=None):
        self.run_service = run_service
        self.workers = workers
        self.events = events

    def project_run(self, *, project_id: str, run_id: str) -> AgenticRunObservability:
        project_id = _canonical_uuid(project_id, "project_id")
        run = self.run_service.get(run_id)
        if run.project_id != project_id:
            raise AgenticObservabilityScopeError("agentic observability scope is unavailable")
        acceptance_ids = tuple(item["id"] for item in self.run_service.acceptance_map_for_run(run))
        event_rows: Sequence[RunEvent] = ()
        latest_event_sequence = 0
        event_plane_complete = False
        if self.events is not None:
            latest_event_sequence = self.events.latest_sequence(project_id=project_id, run_id=run_id)
            event_rows = self.events.list_for_run(
                project_id=project_id,
                run_id=run_id,
                limit=_MAX_EVENTS,
            )
            loaded_latest = max((item.sequence for item in event_rows), default=0)
            event_plane_complete = loaded_latest >= latest_event_sequence
        return build_agentic_run_observability(
            run=run,
            acceptance_ids=acceptance_ids,
            events=event_rows,
            worker=self.workers.get_for_run(run_id),
            event_plane_available=self.events is not None,
            event_plane_complete=event_plane_complete,
            authoritative_latest_event_sequence=latest_event_sequence,
        )

    def project_history(self, *, project_id: str, limit: int = 10) -> ProjectObservabilityHistory:
        project_id = _canonical_uuid(project_id, "project_id")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= _MAX_HISTORY:
            raise AgenticObservabilityError(f"history limit must be between 1 and {_MAX_HISTORY}")
        if self.run_service.owner_subject:
            if self.run_service.projects is None or self.run_service.projects.get_for_owner(
                project_id,
                self.run_service.owner_subject,
            ) is None:
                raise AgenticObservabilityScopeError("agentic observability scope is unavailable")
        runs = self.run_service.runs.list_for_project(project_id=project_id, limit=limit)
        projected = tuple(
            self.project_run(project_id=project_id, run_id=run.id)
            for run in runs
        )
        return ProjectObservabilityHistory(project_id=project_id, limit=limit, runs=projected)


def query_time_retention_cleanup() -> RetentionProjection:
    """Deterministic no-op: S5 v1 persists no derived telemetry and owns no delete target."""

    return QUERY_TIME_RETENTION


def safe_agentic_observability_json(value: AgenticRunObservability | ProjectObservabilityHistory) -> str:
    if not isinstance(value, (AgenticRunObservability, ProjectObservabilityHistory)):
        raise AgenticObservabilityError("unsupported observability payload")
    return json.dumps(value.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _runtime_metrics(
    *,
    run: EngineeringRun,
    events: Sequence[RunEvent],
    worker: EngineeringWorkerExecution | None,
    event_plane_available: bool,
    event_plane_complete: bool,
) -> tuple[RuntimeMetricEvidence, ...]:
    elapsed = _elapsed_metric(run)
    attempt_retries = sum(
        1 for attempt in run.attempts
        if isinstance(attempt.attempt_number, int) and attempt.attempt_number > 1
    )
    retry_attempt_metric = RuntimeMetricEvidence(
        RuntimeMetricId.ATTEMPT_RETRY_COUNT,
        ProjectionKnownState.OBSERVED,
        float(attempt_retries),
        f"obs:attempt-retries:v1:{run.id}:r{int(run.revision)}",
    )
    worker_retry_metric = (
        RuntimeMetricEvidence(
            RuntimeMetricId.WORKER_RETRY_COUNT,
            ProjectionKnownState.OBSERVED,
            float(worker.retry_count),
            f"obs:worker-retries:v1:{worker.id}:r{int(worker.revision)}",
        )
        if worker is not None
        else RuntimeMetricEvidence(
            RuntimeMetricId.WORKER_RETRY_COUNT,
            ProjectionKnownState.UNKNOWN,
            None,
            None,
        )
    )
    human_count = float(len(_intervention_identities(run, events)))
    event_truth_complete = event_plane_available and event_plane_complete
    human_metric = RuntimeMetricEvidence(
        RuntimeMetricId.HUMAN_INTERVENTION_COUNT,
        ProjectionKnownState.OBSERVED if event_truth_complete else ProjectionKnownState.ESTIMATED,
        human_count,
        (
            f"obs:interventions:v1:{run.id}:seq{max((item.sequence for item in events), default=0)}"
            if event_truth_complete
            else f"est:interventions-bounded:v1:{run.id}:r{int(run.revision)}"
        ),
    )
    unknown_usage = RuntimeMetricEvidence(
        RuntimeMetricId.PROVIDER_USAGE_UNITS,
        ProjectionKnownState.UNKNOWN,
        None,
        None,
    )
    unknown_cost = RuntimeMetricEvidence(
        RuntimeMetricId.PROVIDER_COST_USD,
        ProjectionKnownState.UNKNOWN,
        None,
        None,
    )
    return (
        elapsed,
        retry_attempt_metric,
        worker_retry_metric,
        human_metric,
        unknown_usage,
        unknown_cost,
    )


def _elapsed_metric(run: EngineeringRun) -> RuntimeMetricEvidence:
    start = _aware(run.created_at)
    end = _aware(run.completed_at or run.updated_at)
    if start is None or end is None or end < start:
        return RuntimeMetricEvidence(
            RuntimeMetricId.RUN_ELAPSED_SECONDS,
            ProjectionKnownState.UNKNOWN,
            None,
            None,
        )
    return RuntimeMetricEvidence(
        RuntimeMetricId.RUN_ELAPSED_SECONDS,
        ProjectionKnownState.OBSERVED,
        (end - start).total_seconds(),
        f"obs:run-timestamps:v1:{run.id}:r{int(run.revision)}",
    )


def _intervention_identities(run: EngineeringRun, events: Sequence[RunEvent]) -> frozenset[str]:
    identities: set[str] = set()
    control_statuses = {
        AttemptStatus.PAUSED.value,
        AttemptStatus.RESUMED.value,
        AttemptStatus.CANCELLED.value,
        AttemptStatus.SPEC_AMENDMENT.value,
    }
    for attempt in run.attempts:
        if attempt.status in control_statuses:
            identities.add(f"attempt:{attempt.id}")
    for event in events:
        append = event.append
        if append.event_type is RunEventType.RUN_CONTROL and append.attempt_id:
            identities.add(f"attempt:{append.attempt_id}")
        elif append.event_type is RunEventType.REVIEW_REQUIRED or append.outcome is RunEventOutcome.HUMAN_REQUIRED:
            identities.add(f"event:{append.event_key}")
    if not events and run.state == WorkflowStage.REVIEW.value:
        identities.add(f"run-review:{run.id}:r{int(run.revision)}")
    return frozenset(identities)


def _s2_compatible_metrics(metrics: Sequence[RuntimeMetricEvidence]) -> tuple[ProjectionMetricEvidence, ...]:
    by_metric = {item.metric: item for item in metrics}

    def convert(source: RuntimeMetricId, target: ProjectionMetric) -> ProjectionMetricEvidence:
        item = by_metric[source]
        return ProjectionMetricEvidence(
            metric=target,
            state=item.state,
            value=item.value,
            provenance_ref=item.provenance_ref,
        )

    return (
        convert(RuntimeMetricId.RUN_ELAPSED_SECONDS, ProjectionMetric.ELAPSED_TIME),
        ProjectionMetricEvidence(
            metric=ProjectionMetric.COST_USAGE,
            state=ProjectionKnownState.UNKNOWN,
            value=None,
            provenance_ref=None,
        ),
        convert(RuntimeMetricId.HUMAN_INTERVENTION_COUNT, ProjectionMetric.HUMAN_INTERVENTIONS),
    )


def _dedupe_events(run: EngineeringRun, events: Iterable[RunEvent]) -> tuple[RunEvent, ...]:
    if run.project_id is None:
        raise AgenticObservabilityScopeError("run is not Project-bound")
    by_key: dict[str, RunEvent] = {}
    for event in events:
        if not isinstance(event, RunEvent):
            raise AgenticObservabilityError("events must contain canonical RunEvent values")
        if event.project_id != run.project_id or event.run_id != run.id:
            raise AgenticObservabilityScopeError("cross-Project or cross-run telemetry evidence is denied")
        existing = by_key.get(event.event_key)
        if existing is not None:
            if existing.append.canonical_payload() != event.append.canonical_payload():
                raise AgenticObservabilityError("duplicate event identity has conflicting protected content")
            continue
        by_key[event.event_key] = event
    if len(by_key) > _MAX_EVENTS:
        raise AgenticObservabilityError("event evidence exceeds server-owned cardinality bound")
    return tuple(sorted(by_key.values(), key=lambda item: (item.sequence, item.event_key)))


def _canonical_uuid(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise AgenticObservabilityError(f"{field_name} must be a canonical UUID string")
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise AgenticObservabilityError(f"{field_name} must be a canonical UUID string") from exc
    canonical = str(parsed)
    if canonical != value:
        raise AgenticObservabilityError(f"{field_name} must use canonical lowercase UUID form")
    return canonical


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise AgenticObservabilityError("durable timestamp is invalid")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "AgenticObservabilityError",
    "AgenticObservabilityScopeError",
    "AgenticObservabilityService",
    "AgenticRunObservability",
    "METRIC_CATALOG",
    "MetricDefinition",
    "ProjectObservabilityHistory",
    "QUERY_TIME_RETENTION",
    "RetentionClass",
    "RetentionProjection",
    "RuntimeMetricEvidence",
    "RuntimeMetricId",
    "build_agentic_run_observability",
    "query_time_retention_cleanup",
    "safe_agentic_observability_json",
]
