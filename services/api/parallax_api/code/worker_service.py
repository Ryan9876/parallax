from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from .run_events import (
    RunEventAppend,
    RunEventOutcome,
    RunEventSink,
    RunEventSubsystem,
    RunEventType,
)
from .domain import WorkflowStage
from .worker_recovery import (
    DEFAULT_LEASE_SECONDS,
    DEFAULT_MAX_NO_PROGRESS,
    DEFAULT_MAX_OSCILLATIONS,
    DEFAULT_MAX_RETRIES,
    MAX_CHECKPOINT_JSON,
    MAX_LEASE_SECONDS,
    MIN_LEASE_SECONDS,
    RecoveryAction,
    StallClassification,
    TERMINAL_STATES,
    WorkerCheckpoint,
    WorkerCheckpointError,
    WorkerHealthSnapshot,
    WorkerLease,
    WorkerLifecycleState,
    WorkerProgressResult,
    WorkerRecoveryError,
    WorkerStallDecision,
    WorkerStallEvidence,
    classify_stall,
    progress_fingerprint,
    validate_checkpoint,
    validate_lineage_ref,
)
from ..repositories.engineering_runs import EngineeringRunRepository
from ..repositories.worker_executions import EngineeringWorkerExecution, WorkerExecutionRepository


_BLOCKER_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_:-]{0,119}$")


class WorkerExecutionNotFound(WorkerRecoveryError):
    pass


def _utc(value: datetime | None = None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None:
        return result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _lease_seconds(value: int) -> int:
    if not MIN_LEASE_SECONDS <= value <= MAX_LEASE_SECONDS:
        raise ValueError(f"worker lease duration must be between {MIN_LEASE_SECONDS} and {MAX_LEASE_SECONDS} seconds")
    return value


def _blocker_code(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not _BLOCKER_CODE_RE.fullmatch(candidate):
        raise WorkerCheckpointError("worker blocker code is invalid or unbounded")
    return candidate


def _lease_from(execution: EngineeringWorkerExecution) -> WorkerLease:
    if execution.lease_owner_id is None or execution.lease_expires_at is None:
        raise WorkerRecoveryError("worker execution does not currently own a lease")
    expires_at = execution.lease_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return WorkerLease(
        execution_id=execution.id,
        run_id=execution.run_id,
        owner_id=execution.lease_owner_id,
        generation=int(execution.lease_generation),
        expires_at=expires_at,
    )


class WorkerRecoveryService:
    def __init__(
        self,
        executions: WorkerExecutionRepository,
        runs: EngineeringRunRepository,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_no_progress: int = DEFAULT_MAX_NO_PROGRESS,
        max_oscillations: int = DEFAULT_MAX_OSCILLATIONS,
        event_sink: RunEventSink | None = None,
    ):
        if min(max_retries, max_no_progress, max_oscillations) < 0:
            raise ValueError("worker recovery bounds must be nonnegative")
        self.executions = executions
        self.runs = runs
        self.max_retries = max_retries
        self.max_no_progress = max_no_progress
        self.max_oscillations = max_oscillations
        self.event_sink = event_sink

    def _run(self, run_id: str):
        run = self.runs.get(run_id)
        if run is None:
            raise WorkerExecutionNotFound(f"Engineering Run {run_id} was not found")
        if not run.project_id or not run.work_specification_id or run.work_specification_revision is None or not run.work_specification_digest:
            raise WorkerRecoveryError("worker execution requires a canonical Project and approved Work Specification binding")
        return run

    def _execution(self, run_id: str) -> EngineeringWorkerExecution:
        execution = self.executions.get_for_run(run_id)
        if execution is None:
            raise WorkerExecutionNotFound(f"worker execution for Engineering Run {run_id} was not found")
        return execution

    def _emit_worker_event(
        self,
        execution: EngineeringWorkerExecution,
        *,
        event_key: str,
        outcome: RunEventOutcome,
        summary: str,
        failure_code: str | None = None,
        meaningful_progress: bool | None = None,
        bounded_stop: bool | None = None,
    ) -> None:
        if self.event_sink is None:
            return
        run = self._run(execution.run_id)
        metadata: dict[str, object] = {
            "worker_state": execution.state,
            "lease_generation": int(execution.lease_generation),
            "checkpoint_revision": int(execution.checkpoint_revision),
            "retry_count": int(execution.retry_count),
            "no_progress_count": int(execution.no_progress_count),
            "oscillation_count": int(execution.oscillation_count),
        }
        if execution.current_step:
            metadata["current_step"] = execution.current_step
        if execution.stall_classification:
            metadata["stall_classification"] = execution.stall_classification
        if execution.next_recovery_action:
            metadata["next_recovery_action"] = execution.next_recovery_action
        if meaningful_progress is not None:
            metadata["meaningful_progress"] = meaningful_progress
        if bounded_stop is not None:
            metadata["bounded_stop"] = bounded_stop
        self.event_sink.emit(
            RunEventAppend(
                project_id=run.project_id or "",
                run_id=run.id,
                event_key=event_key,
                event_type=RunEventType.WORKER_STATE,
                outcome=outcome,
                subsystem=RunEventSubsystem.WORKER,
                worker_execution_id=execution.id,
                source_lineage_ref=execution.source_lineage_ref,
                failure_code=failure_code,
                summary=summary,
                metadata=metadata,
                occurred_at=_utc(execution.updated_at),
            )
        )

    def acquire(
        self,
        *,
        run_id: str,
        now: datetime | None = None,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> WorkerLease:
        self._run(run_id)
        execution = self.executions.acquire(
            run_id=run_id,
            now=_utc(now),
            lease_seconds=_lease_seconds(lease_seconds),
        )
        self._emit_worker_event(
            execution,
            event_key=f"worker:{execution.id}:lease:{execution.lease_generation}:acquired",
            outcome=RunEventOutcome.STARTED,
            summary="Protected worker mutation lease acquired for the Project-bound Engineering Run.",
        )
        return _lease_from(execution)

    def renew(
        self,
        lease: WorkerLease,
        *,
        now: datetime | None = None,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> WorkerLease:
        execution = self.executions.renew(
            execution_id=lease.execution_id,
            owner_id=lease.owner_id,
            generation=lease.generation,
            now=_utc(now),
            lease_seconds=_lease_seconds(lease_seconds),
        )
        # Lease heartbeat chatter is deliberately not a product event.
        return _lease_from(execution)

    def checkpoint(
        self,
        lease: WorkerLease,
        checkpoint: WorkerCheckpoint,
        *,
        authoritative_source_lineage_ref: str | None,
        state: WorkerLifecycleState = WorkerLifecycleState.CHECKPOINTED,
        retry: bool = False,
        now: datetime | None = None,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> WorkerProgressResult:
        if state not in {
            WorkerLifecycleState.PROGRESSING,
            WorkerLifecycleState.CHECKPOINTED,
            WorkerLifecycleState.READY_FOR_INTEGRATION,
            WorkerLifecycleState.SUCCEEDED,
            WorkerLifecycleState.FAILED,
        }:
            raise WorkerCheckpointError(f"{state.value} is not a valid checkpoint progress state")

        run = self._run(lease.run_id)
        execution = self._execution(lease.run_id)
        if execution.id != lease.execution_id:
            raise WorkerCheckpointError("worker checkpoint execution identity mismatch")

        existing_payload: dict[str, object] = {}
        try:
            decoded = json.loads(execution.checkpoint_json or "{}")
            if isinstance(decoded, dict):
                existing_payload = decoded
            else:
                raise WorkerCheckpointError("stored worker checkpoint must be an object")
        except json.JSONDecodeError as exc:
            raise WorkerCheckpointError("stored worker checkpoint is corrupt") from exc

        existing_plan_ref = existing_payload.get("plan_ref")
        payload = validate_checkpoint(
            run,
            checkpoint,
            existing_plan_ref=existing_plan_ref if isinstance(existing_plan_ref, str) else None,
        )
        authoritative_lineage = validate_lineage_ref(
            authoritative_source_lineage_ref,
            field="authoritative_source_lineage_ref",
        )
        if payload.get("source_lineage_ref") != authoritative_lineage:
            raise WorkerCheckpointError("worker checkpoint source lineage does not match server-resolved accepted lineage")

        fingerprint = progress_fingerprint(payload)
        meaningful = fingerprint != execution.progress_fingerprint
        no_progress_count = 0 if meaningful else int(execution.no_progress_count) + 1
        oscillation_count = int(execution.oscillation_count)
        previous_fingerprint = execution.previous_progress_fingerprint
        if (
            meaningful
            and previous_fingerprint is not None
            and fingerprint == previous_fingerprint
            and fingerprint != execution.progress_fingerprint
        ):
            oscillation_count += 1
        retry_count = int(execution.retry_count) + (1 if retry else 0)

        bounded_stop = (
            retry_count > self.max_retries
            or no_progress_count > self.max_no_progress
            or oscillation_count > self.max_oscillations
        )
        next_action: str | None = None
        blocker_code = _blocker_code(
            payload.get("blocker_code") if isinstance(payload.get("blocker_code"), str) else None
        )
        target_state = state
        release_lease = state in TERMINAL_STATES or state is WorkerLifecycleState.READY_FOR_INTEGRATION
        if bounded_stop:
            target_state = WorkerLifecycleState.FAILED
            release_lease = True
            next_action = RecoveryAction.STOP_BOUNDED.value
            if retry_count > self.max_retries:
                blocker_code = "WORKER_RETRY_LIMIT"
            elif no_progress_count > self.max_no_progress:
                blocker_code = "WORKER_NO_PROGRESS_LIMIT"
            else:
                blocker_code = "WORKER_OSCILLATION_LIMIT"

        payload.update(
            {
                "engineering_run_revision": int(run.revision),
                "attempt_count": len(run.attempts),
                "retry_count": retry_count,
                "no_progress_count": no_progress_count,
                "oscillation_count": oscillation_count,
            }
        )
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        if len(serialized) > MAX_CHECKPOINT_JSON:
            raise WorkerCheckpointError("worker checkpoint exceeds protected JSON bound after server context")

        execution = self.executions.record_progress(
            execution_id=execution.id,
            owner_id=lease.owner_id,
            generation=lease.generation,
            expected_revision=int(execution.revision),
            now=_utc(now),
            lease_seconds=_lease_seconds(lease_seconds),
            state=target_state,
            checkpoint_json=serialized,
            checkpoint_revision=int(execution.checkpoint_revision) + 1,
            current_step=checkpoint.current_step,
            source_lineage_ref=checkpoint.source_lineage_ref,
            last_known_good_lineage_ref=checkpoint.last_known_good_lineage_ref,
            retry_count=retry_count,
            no_progress_count=no_progress_count,
            oscillation_count=oscillation_count,
            progress_fingerprint=fingerprint,
            previous_progress_fingerprint=(execution.progress_fingerprint if meaningful else previous_fingerprint),
            meaningful_progress=meaningful,
            blocker_code=blocker_code,
            next_recovery_action=next_action,
            release_lease=release_lease,
        )
        result = WorkerProgressResult(execution=execution, meaningful_progress=meaningful, bounded_stop=bounded_stop)
        if target_state is WorkerLifecycleState.FAILED:
            outcome = RunEventOutcome.FAILED
        elif target_state is WorkerLifecycleState.READY_FOR_INTEGRATION:
            outcome = RunEventOutcome.HUMAN_REQUIRED
        else:
            outcome = RunEventOutcome.PROGRESSED
        self._emit_worker_event(
            execution,
            event_key=f"worker:{execution.id}:checkpoint:{execution.checkpoint_revision}",
            outcome=outcome,
            summary=f"Protected worker checkpoint recorded in {execution.state} state.",
            failure_code=blocker_code if target_state is WorkerLifecycleState.FAILED else None,
            meaningful_progress=meaningful,
            bounded_stop=bounded_stop,
        )
        return result

    def classify_and_stall(
        self,
        *,
        run_id: str,
        evidence: WorkerStallEvidence,
        blocker_code: str | None = None,
        now: datetime | None = None,
    ) -> WorkerStallDecision:
        self._run(run_id)
        decision = classify_stall(evidence)
        if decision.action == RecoveryAction.STOP_BOUNDED:
            state = WorkerLifecycleState.FAILED
        elif decision.human_required:
            state = WorkerLifecycleState.HUMAN_REQUIRED
        else:
            state = WorkerLifecycleState.STALLED
        execution = self.executions.mark_stalled(
            run_id=run_id,
            now=_utc(now),
            state=state,
            stall_classification=decision.classification.value,
            blocker_code=_blocker_code(blocker_code),
            next_recovery_action=decision.action.value,
        )
        self._emit_worker_event(
            execution,
            event_key=f"worker:{execution.id}:state:{execution.revision}:{execution.state}",
            outcome=(
                RunEventOutcome.HUMAN_REQUIRED
                if state is WorkerLifecycleState.HUMAN_REQUIRED
                else RunEventOutcome.FAILED
                if state is WorkerLifecycleState.FAILED
                else RunEventOutcome.INFO
            ),
            summary=f"Protected worker stall classification produced {execution.state} state.",
            failure_code=execution.blocker_code if state in {WorkerLifecycleState.FAILED, WorkerLifecycleState.HUMAN_REQUIRED} else None,
        )
        return decision


    def prepare_review_rework(
        self,
        *,
        run_id: str,
        authoritative_source_lineage_ref: str,
        now: datetime | None = None,
    ) -> EngineeringWorkerExecution | None:
        run = self._run(run_id)
        lineage = validate_lineage_ref(
            authoritative_source_lineage_ref,
            field="authoritative_source_lineage_ref",
        )
        if run.state != WorkflowStage.PLAN.value:
            raise WorkerRecoveryError("REVIEW rework worker preparation requires the transitioned PLAN state")
        context = None
        for attempt in reversed(run.attempts):
            if attempt.stage != WorkflowStage.REVIEW.value or attempt.status != "RESUMED":
                continue
            try:
                payload = json.loads(attempt.evidence_json or "{}")
            except json.JSONDecodeError as exc:
                raise WorkerRecoveryError("durable REVIEW rework evidence is corrupt") from exc
            if isinstance(payload, dict) and payload.get("review_rework_version") == "review-rework-v1":
                context = payload
                break
        if context is None or context.get("base_source_lineage_ref") != lineage:
            raise WorkerRecoveryError("worker REVIEW rework source identity lacks matching durable human control")

        before = self.executions.get_for_run(run_id)
        if before is None:
            return None
        before_revision = int(before.revision)
        execution = self.executions.prepare_review_rework(
            run_id=run_id,
            authoritative_source_lineage_ref=lineage,
            now=_utc(now),
        )
        if execution is None:
            return None
        if int(execution.revision) != before_revision:
            self._emit_worker_event(
                execution,
                event_key=f"worker:{execution.id}:state:{execution.revision}:REVIEW_REWORK_RECOVERING",
                outcome=RunEventOutcome.RECOVERING,
                summary="Explicit human REVIEW rework invalidated the prior selected candidate and re-armed bounded generation.",
            )
        return execution

    def prepare_human_resume(
        self,
        *,
        run_id: str,
        now: datetime | None = None,
    ) -> EngineeringWorkerExecution | None:
        self._run(run_id)
        current = self.executions.get_for_run(run_id)
        if current is None or current.state != WorkerLifecycleState.FAILED.value:
            return current
        execution = self.executions.prepare_human_resume(run_id=run_id, now=_utc(now))
        if execution is None:
            return None
        self._emit_worker_event(
            execution,
            event_key=f"worker:{execution.id}:state:{execution.revision}:HUMAN_RESUME_RECOVERING",
            outcome=RunEventOutcome.RECOVERING,
            summary="Explicit Engineering Run resume re-armed the terminal worker for one new bounded generation.",
        )
        return execution

    def begin_recovery(self, *, run_id: str, now: datetime | None = None) -> EngineeringWorkerExecution:
        execution = self._execution(run_id)
        if execution.state != WorkerLifecycleState.STALLED.value:
            raise WorkerRecoveryError("automatic recovery requires a STALLED worker execution")
        classification = execution.stall_classification or StallClassification.PROCESS_LOSS.value
        action = execution.next_recovery_action or RecoveryAction.REASSIGN.value
        execution = self.executions.mark_stalled(
            run_id=run_id,
            now=_utc(now),
            state=WorkerLifecycleState.RECOVERING,
            stall_classification=classification,
            blocker_code=execution.blocker_code,
            next_recovery_action=action,
        )
        self._emit_worker_event(
            execution,
            event_key=f"worker:{execution.id}:state:{execution.revision}:RECOVERING",
            outcome=RunEventOutcome.RECOVERING,
            summary="Protected worker recovery began after accepted stall classification.",
        )
        return execution

    def reassign(
        self,
        *,
        run_id: str,
        now: datetime | None = None,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> WorkerLease:
        self._run(run_id)
        execution = self.executions.reassign(
            run_id=run_id,
            now=_utc(now),
            lease_seconds=_lease_seconds(lease_seconds),
        )
        self._emit_worker_event(
            execution,
            event_key=f"worker:{execution.id}:lease:{execution.lease_generation}:reassigned",
            outcome=RunEventOutcome.RECOVERING,
            summary="Protected worker recovery reassigned mutation authority with a fresh lease generation.",
        )
        return _lease_from(execution)

    def health(self, *, run_id: str, now: datetime | None = None) -> WorkerHealthSnapshot:
        run = self._run(run_id)
        execution = self._execution(run_id)
        current_time = _utc(now)
        expiry = execution.lease_expires_at
        if expiry is not None and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if execution.lease_owner_id is None:
            lease_status = "UNOWNED"
        elif expiry is not None and expiry <= current_time:
            lease_status = "EXPIRED"
        else:
            lease_status = "ACTIVE"

        try:
            checkpoint = json.loads(execution.checkpoint_json or "{}")
        except json.JSONDecodeError as exc:
            raise WorkerRecoveryError("stored worker checkpoint is corrupt") from exc
        if not isinstance(checkpoint, dict):
            raise WorkerRecoveryError("stored worker checkpoint must be an object")
        dependencies_value = checkpoint.get("dependencies")
        if dependencies_value is None:
            dependencies: tuple[str, ...] = ()
        elif isinstance(dependencies_value, list) and all(isinstance(item, str) for item in dependencies_value):
            dependencies = tuple(dependencies_value)
        else:
            raise WorkerRecoveryError("stored worker checkpoint dependencies are corrupt")

        classification = None
        if execution.stall_classification:
            try:
                classification = StallClassification(execution.stall_classification)
            except ValueError:
                classification = StallClassification.UNKNOWN
        next_action = None
        if execution.next_recovery_action:
            try:
                next_action = RecoveryAction(execution.next_recovery_action)
            except ValueError:
                next_action = RecoveryAction.STOP_BOUNDED

        return WorkerHealthSnapshot(
            execution_id=execution.id,
            project_id=run.project_id or "",
            run_id=execution.run_id,
            state=WorkerLifecycleState(execution.state),
            lease_status=lease_status,
            lease_generation=int(execution.lease_generation),
            current_step=execution.current_step,
            source_lineage_ref=execution.source_lineage_ref,
            last_known_good_lineage_ref=execution.last_known_good_lineage_ref,
            checkpoint_revision=int(execution.checkpoint_revision),
            last_meaningful_progress_at=execution.last_meaningful_progress_at,
            retry_count=int(execution.retry_count),
            no_progress_count=int(execution.no_progress_count),
            oscillation_count=int(execution.oscillation_count),
            stall_classification=classification,
            blocker_code=execution.blocker_code,
            dependencies=dependencies,
            next_recovery_action=next_action,
            human_required=execution.state == WorkerLifecycleState.HUMAN_REQUIRED.value,
        )
