from __future__ import annotations

from datetime import datetime, timezone
import json

from .worker_recovery import (
    DEFAULT_LEASE_SECONDS,
    DEFAULT_MAX_NO_PROGRESS,
    DEFAULT_MAX_OSCILLATIONS,
    DEFAULT_MAX_RETRIES,
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
)
from ..repositories.engineering_runs import EngineeringRunRepository
from ..repositories.worker_executions import EngineeringWorkerExecution, WorkerExecutionRepository


class WorkerExecutionNotFound(WorkerRecoveryError):
    pass


def _utc(value: datetime | None = None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None:
        return result.replace(tzinfo=timezone.utc)
    return result


def _lease_seconds(value: int) -> int:
    if not MIN_LEASE_SECONDS <= value <= MAX_LEASE_SECONDS:
        raise ValueError(f"worker lease duration must be between {MIN_LEASE_SECONDS} and {MAX_LEASE_SECONDS} seconds")
    return value


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
    ):
        self.executions = executions
        self.runs = runs
        self.max_retries = max_retries
        self.max_no_progress = max_no_progress
        self.max_oscillations = max_oscillations

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
        return _lease_from(execution)

    def checkpoint(
        self,
        lease: WorkerLease,
        checkpoint: WorkerCheckpoint,
        *,
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
        except json.JSONDecodeError as exc:
            raise WorkerCheckpointError("stored worker checkpoint is corrupt") from exc

        existing_plan_ref = existing_payload.get("plan_ref")
        payload = validate_checkpoint(
            run,
            checkpoint,
            existing_plan_ref=existing_plan_ref if isinstance(existing_plan_ref, str) else None,
        )
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
        blocker_code = payload.get("blocker_code") if isinstance(payload.get("blocker_code"), str) else None
        target_state = state
        release_lease = state in TERMINAL_STATES
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

        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
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
        return WorkerProgressResult(execution=execution, meaningful_progress=meaningful, bounded_stop=bounded_stop)

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
        self.executions.mark_stalled(
            run_id=run_id,
            now=_utc(now),
            state=state,
            stall_classification=decision.classification.value,
            blocker_code=blocker_code,
            next_recovery_action=decision.action.value,
        )
        return decision

    def begin_recovery(self, *, run_id: str, now: datetime | None = None) -> EngineeringWorkerExecution:
        execution = self._execution(run_id)
        if execution.state == WorkerLifecycleState.HUMAN_REQUIRED.value:
            raise WorkerRecoveryError("HUMAN_REQUIRED execution cannot enter automatic recovery")
        if execution.state in {item.value for item in TERMINAL_STATES}:
            raise WorkerRecoveryError("terminal worker execution cannot enter recovery")
        classification = execution.stall_classification or StallClassification.PROCESS_LOSS.value
        action = execution.next_recovery_action or RecoveryAction.REASSIGN.value
        return self.executions.mark_stalled(
            run_id=run_id,
            now=_utc(now),
            state=WorkerLifecycleState.RECOVERING,
            stall_classification=classification,
            blocker_code=execution.blocker_code,
            next_recovery_action=action,
        )

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
        return _lease_from(execution)

    def health(self, *, run_id: str, now: datetime | None = None) -> WorkerHealthSnapshot:
        self._run(run_id)
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

        dependencies: tuple[str, ...] = ()
        try:
            checkpoint = json.loads(execution.checkpoint_json or "{}")
            if isinstance(checkpoint, dict) and isinstance(checkpoint.get("dependencies"), list):
                dependencies = tuple(str(item) for item in checkpoint["dependencies"])
        except json.JSONDecodeError:
            dependencies = ()

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
