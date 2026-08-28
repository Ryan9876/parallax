from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
import math
import re
from typing import Iterable, Mapping, Protocol, Sequence
from uuid import UUID

from parallax_api.models import EngineeringAttempt, EngineeringRun
from parallax_api.repositories.worker_executions import EngineeringWorkerExecution

from .domain import ACTIVE_STAGES, TERMINAL_STAGES, AttemptStatus, WorkflowStage
from .run_events import RunEvent, RunEventOutcome, RunEventType
from .service import EngineeringRunService, RunOperationResult


_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_AC_RE = re.compile(r"^AC-[0-9]{2,3}$")
_ACTION_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$")
_MAX_EVENTS = 512
_MAX_ATTEMPTS = 256
_MAX_ACCEPTANCE_IDS = 128


class AgentRunProjectionError(ValueError):
    """Fail-closed error for malformed or cross-boundary projection evidence."""


class AgentRunControlRejected(AgentRunProjectionError):
    """Typed control request did not satisfy the current server-owned run contract."""


class ProjectionKnownState(StrEnum):
    OBSERVED = "OBSERVED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class ProjectionMetric(StrEnum):
    ELAPSED_TIME = "elapsed_time"
    COST_USAGE = "cost_usage"
    HUMAN_INTERVENTIONS = "human_interventions"


class ProjectionControlKind(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"


class ProjectionControlDenyReason(StrEnum):
    PROJECT_MISMATCH = "PROJECT_MISMATCH"
    RUN_MISMATCH = "RUN_MISMATCH"
    REVISION_MISMATCH = "REVISION_MISMATCH"
    STATE_MISMATCH = "STATE_MISMATCH"
    UNSUPPORTED_CONTROL = "UNSUPPORTED_CONTROL"


class DeterministicDisposition(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PENDING = "PENDING"


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
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id, "work_specification_id"))
        if not isinstance(self.work_specification_revision, int) or isinstance(self.work_specification_revision, bool) or self.work_specification_revision < 1:
            raise AgentRunProjectionError("work_specification_revision must be >= 1")
        object.__setattr__(self, "work_specification_digest", _sha(self.work_specification_digest, "work_specification_digest"))
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
class ProjectedTask:
    task_id: str
    stage: str
    attempt_number: int
    status: str
    producer_ref: str | None
    failure_code: str | None
    started_at: str | None
    completed_at: str | None

    @classmethod
    def from_attempt(cls, attempt: EngineeringAttempt) -> "ProjectedTask":
        producer_ref: str | None = None
        if attempt.tool_id:
            producer_ref = _optional_bounded(f"tool:{attempt.tool_id}", "producer_ref", 160)
        elif attempt.program_id:
            producer_ref = _optional_bounded(f"program:{attempt.program_id}", "producer_ref", 160)
        elif attempt.model_id:
            producer_ref = _optional_bounded(f"model:{attempt.model_id}", "producer_ref", 160)
        return cls(
            task_id=f"attempt:{_uuid(attempt.id, 'attempt_id')}",
            stage=_bounded(attempt.stage, "stage", 32),
            attempt_number=_positive_int(attempt.attempt_number, "attempt_number"),
            status=_bounded(attempt.status, "status", 32),
            producer_ref=producer_ref,
            failure_code=_optional_bounded(attempt.failure_code, "failure_code", 120),
            started_at=_utc_iso(attempt.started_at),
            completed_at=_utc_iso(attempt.completed_at),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "stage": self.stage,
            "attempt_number": self.attempt_number,
            "status": self.status,
            "producer_ref": self.producer_ref,
            "failure_code": self.failure_code,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass(frozen=True, slots=True)
class RecoveryProjection:
    execution_id: str | None
    state: str | None
    lease_generation: int | None
    checkpoint_revision: int | None
    current_step: str | None
    source_lineage_ref: str | None
    last_known_good_lineage_ref: str | None
    retry_count: int | None
    no_progress_count: int | None
    oscillation_count: int | None
    blocker_code: str | None
    next_recovery_action: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "execution_id": self.execution_id,
            "state": self.state,
            "lease_generation": self.lease_generation,
            "checkpoint_revision": self.checkpoint_revision,
            "current_step": self.current_step,
            "source_lineage_ref": self.source_lineage_ref,
            "last_known_good_lineage_ref": self.last_known_good_lineage_ref,
            "retry_count": self.retry_count,
            "no_progress_count": self.no_progress_count,
            "oscillation_count": self.oscillation_count,
            "blocker_code": self.blocker_code,
            "next_recovery_action": self.next_recovery_action,
        }


@dataclass(frozen=True, slots=True)
class ValidationProjection:
    stage: str
    disposition: DeterministicDisposition
    attempt_id: str | None
    failure_code: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "disposition": self.disposition.value,
            "attempt_id": self.attempt_id,
            "failure_code": self.failure_code,
        }


@dataclass(frozen=True, slots=True)
class EvaluationProjection:
    evaluation_id: str | None
    outcome: str | None
    score_class: str | None
    source_lineage_ref: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "evaluation_id": self.evaluation_id,
            "outcome": self.outcome,
            "score_class": self.score_class,
            "source_lineage_ref": self.source_lineage_ref,
        }


@dataclass(frozen=True, slots=True)
class RoutingProjection:
    provider: str | None
    result_code: str | None
    outcome: str | None
    source_lineage_ref: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "result_code": self.result_code,
            "outcome": self.outcome,
            "source_lineage_ref": self.source_lineage_ref,
        }


@dataclass(frozen=True, slots=True)
class DeliveryProjection:
    source_lineage_ref: str | None
    parent_source_lineage_ref: str | None
    pull_request_number: int | None
    preview_deployment_id: str | None
    preview_status: str | None
    artifact_ref: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "source_lineage_ref": self.source_lineage_ref,
            "parent_source_lineage_ref": self.parent_source_lineage_ref,
            "pull_request_number": self.pull_request_number,
            "preview_deployment_id": self.preview_deployment_id,
            "preview_status": self.preview_status,
            "artifact_ref": self.artifact_ref,
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
class AdvertisedProjectionControl:
    kind: ProjectionControlKind
    expected_revision: int
    expected_state: str

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "expected_revision": self.expected_revision,
            "expected_state": self.expected_state,
        }


@dataclass(frozen=True, slots=True)
class ProjectionControlRequest:
    request_id: str
    project_id: str
    run_id: str
    expected_revision: int
    expected_state: str
    action: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _reference(self.request_id, "request_id"))
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        if not isinstance(self.expected_revision, int) or isinstance(self.expected_revision, bool) or self.expected_revision < 0:
            raise AgentRunProjectionError("expected_revision must be >= 0")
        object.__setattr__(self, "expected_state", _bounded(self.expected_state, "expected_state", 32))
        if not isinstance(self.action, str) or _ACTION_RE.fullmatch(self.action) is None:
            raise AgentRunProjectionError("action is invalid or unbounded")

    @property
    def operation_key(self) -> str:
        key = f"agent-projection:{self.action}:{self.request_id}"
        if len(key) > 160:
            raise AgentRunProjectionError("control operation identity is unbounded")
        return key


@dataclass(frozen=True, slots=True)
class ProjectionControlDecision:
    allowed: bool
    deny_reason: ProjectionControlDenyReason | None = None

    def __post_init__(self) -> None:
        if self.allowed and self.deny_reason is not None:
            raise AgentRunProjectionError("allowed control decision cannot include a deny reason")
        if not self.allowed and self.deny_reason is None:
            raise AgentRunProjectionError("denied control decision requires a deny reason")
        if self.deny_reason is not None:
            object.__setattr__(self, "deny_reason", ProjectionControlDenyReason(self.deny_reason))


@dataclass(frozen=True, slots=True)
class AgentRunProjection:
    identity: ProjectionIdentity
    current_state: str
    run_revision: int
    resume_stage: str | None
    last_failure_code: str | None
    latest_source_lineage_ref: str | None
    tasks: tuple[ProjectedTask, ...]
    recovery: RecoveryProjection
    validation: tuple[ValidationProjection, ...]
    deterministic_disposition: DeterministicDisposition
    evaluation: EvaluationProjection
    routing: RoutingProjection
    delivery: DeliveryProjection
    metrics: tuple[ProjectionMetricEvidence, ...]
    advertised_controls: tuple[AdvertisedProjectionControl, ...]
    final_handoff: str | None
    latest_event_sequence: int

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
        if len(self.tasks) > _MAX_ATTEMPTS:
            raise AgentRunProjectionError("projection tasks exceed bounded cardinality")
        if not isinstance(self.latest_event_sequence, int) or self.latest_event_sequence < 0:
            raise AgentRunProjectionError("latest_event_sequence must be nonnegative")

    @property
    def fingerprint(self) -> str:
        return _digest(self.as_dict(include_fingerprint=False))

    def as_dict(self, *, include_fingerprint: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "projection_version": 2,
            "identity": self.identity.as_dict(),
            "current_state": self.current_state,
            "run_revision": self.run_revision,
            "resume_stage": self.resume_stage,
            "last_failure_code": self.last_failure_code,
            "latest_source_lineage_ref": self.latest_source_lineage_ref,
            "tasks": [item.as_dict() for item in self.tasks],
            "recovery": self.recovery.as_dict(),
            "validation": [item.as_dict() for item in self.validation],
            "deterministic_disposition": self.deterministic_disposition.value,
            "evaluation": self.evaluation.as_dict(),
            "routing": self.routing.as_dict(),
            "delivery": self.delivery.as_dict(),
            "metrics": [item.as_dict() for item in self.metrics],
            "advertised_controls": [item.as_dict() for item in self.advertised_controls],
            "final_handoff": self.final_handoff,
            "latest_event_sequence": self.latest_event_sequence,
            "accepts_source_lineage": False,
            "creates_lifecycle_authority": False,
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


class AgentRunEventReader(Protocol):
    def list_for_run(self, *, project_id: str, run_id: str, after_sequence: int = 0, limit: int = 100) -> Sequence[RunEvent]: ...


class AgentRunWorkerReader(Protocol):
    def get_for_run(self, run_id: str) -> EngineeringWorkerExecution | None: ...


def build_agent_run_projection(
    *,
    run: EngineeringRun,
    acceptance_ids: Iterable[str],
    events: Iterable[RunEvent] = (),
    metrics: Iterable[ProjectionMetricEvidence] = (),
    worker: EngineeringWorkerExecution | None = None,
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

    ordered_events = tuple(sorted(tuple(events), key=lambda item: item.sequence))
    if len(ordered_events) > _MAX_EVENTS:
        raise AgentRunProjectionError("projection event evidence exceeds bounded cardinality")
    if any(not isinstance(event, RunEvent) for event in ordered_events):
        raise AgentRunProjectionError("events must contain canonical RunEvent values")
    if any(event.project_id != identity.project_id or event.run_id != identity.run_id for event in ordered_events):
        raise AgentRunProjectionError("cross-Project or cross-run event cannot satisfy projection")
    if worker is not None and worker.run_id != run.id:
        raise AgentRunProjectionError("worker evidence crosses the canonical run boundary")

    tasks = tuple(
        ProjectedTask.from_attempt(item)
        for item in sorted(tuple(run.attempts), key=lambda item: (item.started_at, item.attempt_number, item.id))
    )
    if len(tasks) > _MAX_ATTEMPTS:
        raise AgentRunProjectionError("projection attempt evidence exceeds bounded cardinality")

    supplied_metrics = tuple(metrics)
    if any(not isinstance(item, ProjectionMetricEvidence) for item in supplied_metrics):
        raise AgentRunProjectionError("metrics must contain canonical ProjectionMetricEvidence values")
    by_metric = {item.metric: item for item in supplied_metrics}
    if len(by_metric) != len(supplied_metrics):
        raise AgentRunProjectionError("metrics must be unique")
    complete_metrics = tuple(
        by_metric.get(metric, ProjectionMetricEvidence(metric=metric, state=ProjectionKnownState.UNKNOWN, value=None, provenance_ref=None))
        for metric in ProjectionMetric
    )

    latest_lineage = _latest_lineage(ordered_events, worker)
    validation, deterministic = _validation(tasks)
    evaluation = _evaluation(ordered_events)
    routing = _routing(ordered_events)
    delivery = _delivery(ordered_events, latest_lineage)
    recovery = _recovery(worker, ordered_events)
    controls = _advertised_controls(run)
    final_handoff = "HUMAN_REQUIRED" if run.state == WorkflowStage.REVIEW.value or any(
        event.append.outcome is RunEventOutcome.HUMAN_REQUIRED for event in ordered_events
    ) else None

    return AgentRunProjection(
        identity=identity,
        current_state=run.state,
        run_revision=int(run.revision),
        resume_stage=run.resume_stage,
        last_failure_code=run.last_failure_code,
        latest_source_lineage_ref=latest_lineage,
        tasks=tasks,
        recovery=recovery,
        validation=validation,
        deterministic_disposition=deterministic,
        evaluation=evaluation,
        routing=routing,
        delivery=delivery,
        metrics=complete_metrics,
        advertised_controls=controls,
        final_handoff=final_handoff,
        latest_event_sequence=max((item.sequence for item in ordered_events), default=0),
    )


def decide_projection_control(projection: AgentRunProjection, request: ProjectionControlRequest) -> ProjectionControlDecision:
    if request.project_id != projection.identity.project_id:
        return ProjectionControlDecision(False, ProjectionControlDenyReason.PROJECT_MISMATCH)
    if request.run_id != projection.identity.run_id:
        return ProjectionControlDecision(False, ProjectionControlDenyReason.RUN_MISMATCH)
    if request.expected_revision != projection.run_revision:
        return ProjectionControlDecision(False, ProjectionControlDenyReason.REVISION_MISMATCH)
    if request.expected_state != projection.current_state:
        return ProjectionControlDecision(False, ProjectionControlDenyReason.STATE_MISMATCH)
    allowed = {item.kind.value for item in projection.advertised_controls}
    if request.action not in allowed:
        return ProjectionControlDecision(False, ProjectionControlDenyReason.UNSUPPORTED_CONTROL)
    return ProjectionControlDecision(True, None)


class AgentRunProjectionService:
    """Projection facade that reuses existing Engineering Run mutation authority."""

    def __init__(self, service: EngineeringRunService, workers: AgentRunWorkerReader, *, events: AgentRunEventReader | None = None):
        self.service = service
        self.workers = workers
        self.events = events

    def project(self, *, project_id: str, run_id: str, metrics: Iterable[ProjectionMetricEvidence] = ()) -> AgentRunProjection:
        run = self.service.get(run_id)
        if run.project_id != project_id:
            raise AgentRunProjectionError("Agent Run projection scope is unavailable")
        acceptance_ids = tuple(item["id"] for item in self.service.acceptance_map_for_run(run))
        event_rows: Sequence[RunEvent] = ()
        if self.events is not None:
            event_rows = self.events.list_for_run(project_id=project_id, run_id=run_id, limit=200)
        return build_agent_run_projection(
            run=run,
            acceptance_ids=acceptance_ids,
            events=event_rows,
            metrics=metrics,
            worker=self.workers.get_for_run(run_id),
        )

    def control(self, projection: AgentRunProjection, request: ProjectionControlRequest) -> RunOperationResult:
        decision = decide_projection_control(projection, request)
        run = self.service.get(request.run_id)
        if run.project_id != request.project_id:
            raise AgentRunControlRejected("Agent Run control scope is unavailable")
        existing = self.service.runs.find_operation(run.id, request.operation_key)
        if existing is None:
            if not decision.allowed:
                assert decision.deny_reason is not None
                raise AgentRunControlRejected(decision.deny_reason.value)
            if run.revision != request.expected_revision:
                raise AgentRunControlRejected(ProjectionControlDenyReason.REVISION_MISMATCH.value)
            if run.state != request.expected_state:
                raise AgentRunControlRejected(ProjectionControlDenyReason.STATE_MISMATCH.value)
        try:
            kind = ProjectionControlKind(request.action)
        except ValueError as exc:
            raise AgentRunControlRejected(ProjectionControlDenyReason.UNSUPPORTED_CONTROL.value) from exc
        method = {
            ProjectionControlKind.PAUSE: self.service.pause,
            ProjectionControlKind.RESUME: self.service.resume,
            ProjectionControlKind.CANCEL: self.service.cancel,
        }[kind]
        return method(
            run_id=request.run_id,
            operation_key=request.operation_key,
            expected_revision=request.expected_revision,
        )


def safe_agent_run_projection_json(projection: AgentRunProjection) -> str:
    if not isinstance(projection, AgentRunProjection):
        raise AgentRunProjectionError("projection must be AgentRunProjection")
    return json.dumps(projection.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _advertised_controls(run: EngineeringRun) -> tuple[AdvertisedProjectionControl, ...]:
    try:
        state = WorkflowStage(run.state)
    except ValueError:
        return ()
    controls: list[AdvertisedProjectionControl] = []
    if state in ACTIVE_STAGES:
        controls.append(AdvertisedProjectionControl(ProjectionControlKind.PAUSE, int(run.revision), state.value))
    if state in {WorkflowStage.PAUSED, WorkflowStage.FAILED} and run.resume_stage:
        try:
            if WorkflowStage(run.resume_stage) in ACTIVE_STAGES:
                controls.append(AdvertisedProjectionControl(ProjectionControlKind.RESUME, int(run.revision), state.value))
        except ValueError:
            pass
    if state not in TERMINAL_STAGES:
        controls.append(AdvertisedProjectionControl(ProjectionControlKind.CANCEL, int(run.revision), state.value))
    return tuple(controls)


def _validation(tasks: tuple[ProjectedTask, ...]) -> tuple[tuple[ValidationProjection, ...], DeterministicDisposition]:
    rows: list[ValidationProjection] = []
    for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY):
        candidates = [item for item in tasks if item.stage == stage.value]
        latest = candidates[-1] if candidates else None
        if latest is None:
            disposition = DeterministicDisposition.PENDING
        elif latest.status == AttemptStatus.PASSED.value:
            disposition = DeterministicDisposition.PASSED
        else:
            disposition = DeterministicDisposition.FAILED
        rows.append(
            ValidationProjection(
                stage=stage.value,
                disposition=disposition,
                attempt_id=latest.task_id.removeprefix("attempt:") if latest else None,
                failure_code=latest.failure_code if latest else None,
            )
        )
    if any(item.disposition is DeterministicDisposition.FAILED for item in rows):
        overall = DeterministicDisposition.FAILED
    elif all(item.disposition is DeterministicDisposition.PASSED for item in rows):
        overall = DeterministicDisposition.PASSED
    else:
        overall = DeterministicDisposition.PENDING
    return tuple(rows), overall


def _latest_lineage(events: Sequence[RunEvent], worker: EngineeringWorkerExecution | None) -> str | None:
    for event in reversed(tuple(events)):
        if event.append.source_lineage_ref and event.append.event_type in {RunEventType.SOURCE_LINEAGE_ACCEPTED, RunEventType.SOURCE_DELIVERY}:
            return event.append.source_lineage_ref
    if worker is not None and worker.source_lineage_ref and _LINEAGE_RE.fullmatch(worker.source_lineage_ref):
        return worker.source_lineage_ref
    return None


def _evaluation(events: Sequence[RunEvent]) -> EvaluationProjection:
    for event in reversed(tuple(events)):
        if event.append.event_type is RunEventType.EVALUATION_RESULT:
            metadata = event.append.metadata
            return EvaluationProjection(
                evaluation_id=_safe_metadata_ref(metadata.get("evaluation_id")),
                outcome=event.append.outcome.value,
                score_class=_safe_metadata_ref(metadata.get("score_class")),
                source_lineage_ref=event.append.source_lineage_ref,
            )
    return EvaluationProjection(None, None, None, None)


def _routing(events: Sequence[RunEvent]) -> RoutingProjection:
    for event in reversed(tuple(events)):
        if event.append.event_type is RunEventType.PROVIDER_RESULT:
            metadata = event.append.metadata
            return RoutingProjection(
                provider=_safe_metadata_ref(metadata.get("provider")),
                result_code=_safe_metadata_ref(metadata.get("result_code")),
                outcome=event.append.outcome.value,
                source_lineage_ref=event.append.source_lineage_ref,
            )
    return RoutingProjection(None, None, None, None)


def _delivery(events: Sequence[RunEvent], fallback_lineage: str | None) -> DeliveryProjection:
    for event in reversed(tuple(events)):
        if event.append.event_type is RunEventType.SOURCE_DELIVERY:
            metadata = event.append.metadata
            pr = metadata.get("pull_request_number")
            return DeliveryProjection(
                source_lineage_ref=event.append.source_lineage_ref or fallback_lineage,
                parent_source_lineage_ref=event.append.parent_source_lineage_ref,
                pull_request_number=int(pr) if isinstance(pr, int) and pr > 0 else None,
                preview_deployment_id=_safe_metadata_ref(metadata.get("preview_deployment_id")),
                preview_status=_safe_metadata_ref(metadata.get("preview_status")),
                artifact_ref=event.append.artifact_ref,
            )
    return DeliveryProjection(fallback_lineage, None, None, None, None, None)


def _recovery(worker: EngineeringWorkerExecution | None, events: Sequence[RunEvent]) -> RecoveryProjection:
    if worker is not None:
        return RecoveryProjection(
            execution_id=worker.id,
            state=worker.state,
            lease_generation=int(worker.lease_generation),
            checkpoint_revision=int(worker.checkpoint_revision),
            current_step=_optional_bounded(worker.current_step, "current_step", 64),
            source_lineage_ref=worker.source_lineage_ref if worker.source_lineage_ref and _LINEAGE_RE.fullmatch(worker.source_lineage_ref) else None,
            last_known_good_lineage_ref=(worker.last_known_good_lineage_ref if worker.last_known_good_lineage_ref and _LINEAGE_RE.fullmatch(worker.last_known_good_lineage_ref) else None),
            retry_count=int(worker.retry_count),
            no_progress_count=int(worker.no_progress_count),
            oscillation_count=int(worker.oscillation_count),
            blocker_code=_optional_bounded(worker.blocker_code, "blocker_code", 120),
            next_recovery_action=_optional_bounded(worker.next_recovery_action, "next_recovery_action", 64),
        )
    for event in reversed(tuple(events)):
        if event.append.event_type is RunEventType.WORKER_STATE:
            metadata = event.append.metadata
            return RecoveryProjection(
                execution_id=event.append.worker_execution_id,
                state=_safe_metadata_ref(metadata.get("worker_state")),
                lease_generation=_safe_metadata_int(metadata.get("lease_generation")),
                checkpoint_revision=_safe_metadata_int(metadata.get("checkpoint_revision")),
                current_step=_safe_metadata_ref(metadata.get("current_step")),
                source_lineage_ref=event.append.source_lineage_ref,
                last_known_good_lineage_ref=None,
                retry_count=_safe_metadata_int(metadata.get("retry_count")),
                no_progress_count=_safe_metadata_int(metadata.get("no_progress_count")),
                oscillation_count=_safe_metadata_int(metadata.get("oscillation_count")),
                blocker_code=event.append.failure_code,
                next_recovery_action=_safe_metadata_ref(metadata.get("next_recovery_action")),
            )
    return RecoveryProjection(None, None, None, None, None, None, None, None, None, None, None, None)


def _safe_metadata_ref(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > 160:
        return None
    return candidate


def _safe_metadata_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


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


def _reference(value: str, field: str) -> str:
    if not isinstance(value, str) or _REF_RE.fullmatch(value) is None:
        raise AgentRunProjectionError(f"{field} must be a bounded opaque identifier")
    return value


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _digest(value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()


__all__ = [
    "AdvertisedProjectionControl",
    "AgentRunControlRejected",
    "AgentRunProjection",
    "AgentRunProjectionError",
    "AgentRunProjectionService",
    "DeterministicDisposition",
    "ProjectionControlDecision",
    "ProjectionControlDenyReason",
    "ProjectionControlKind",
    "ProjectionControlRequest",
    "ProjectionKnownState",
    "ProjectionMetric",
    "ProjectionMetricEvidence",
    "build_agent_run_projection",
    "decide_projection_control",
    "safe_agent_run_projection_json",
]
