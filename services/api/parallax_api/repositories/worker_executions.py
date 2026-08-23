from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..code.worker_recovery import (
    WorkerLeaseConflict,
    WorkerLeaseExpired,
    WorkerLifecycleState,
    WorkerStaleLease,
)
from ..db import Base
from ..models import utcnow


class EngineeringWorkerExecution(Base):
    __tablename__ = "engineering_worker_executions"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_engineering_worker_execution_run"),
        CheckConstraint("lease_generation >= 0", name="ck_worker_lease_generation_nonnegative"),
        CheckConstraint("checkpoint_revision >= 0", name="ck_worker_checkpoint_revision_nonnegative"),
        CheckConstraint("retry_count >= 0", name="ck_worker_retry_count_nonnegative"),
        CheckConstraint("no_progress_count >= 0", name="ck_worker_no_progress_count_nonnegative"),
        CheckConstraint("oscillation_count >= 0", name="ck_worker_oscillation_count_nonnegative"),
        CheckConstraint("revision >= 0", name="ck_worker_revision_nonnegative"),
        CheckConstraint(
            "(lease_owner_id IS NULL AND lease_expires_at IS NULL) OR "
            "(lease_owner_id IS NOT NULL AND lease_expires_at IS NOT NULL)",
            name="ck_worker_lease_pair",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        ForeignKey("engineering_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(32), default=WorkerLifecycleState.RUNNING.value, index=True)
    lease_owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_generation: Mapped[int] = mapped_column(BigInteger, default=0)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_meaningful_progress_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checkpoint_revision: Mapped[int] = mapped_column(BigInteger, default=0)
    checkpoint_json: Mapped[str] = mapped_column(Text, default="{}")
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_lineage_ref: Mapped[str | None] = mapped_column(String(68), nullable=True)
    last_known_good_lineage_ref: Mapped[str | None] = mapped_column(String(68), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    no_progress_count: Mapped[int] = mapped_column(Integer, default=0)
    oscillation_count: Mapped[int] = mapped_column(Integer, default=0)
    progress_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_progress_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stall_classification: Mapped[str | None] = mapped_column(String(64), nullable=True)
    blocker_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    next_recovery_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revision: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


class WorkerExecutionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_for_run(self, run_id: str) -> EngineeringWorkerExecution | None:
        return self.session.scalar(
            select(EngineeringWorkerExecution)
            .where(EngineeringWorkerExecution.run_id == run_id)
            .execution_options(populate_existing=True)
        )

    def get(self, execution_id: str) -> EngineeringWorkerExecution | None:
        return self.session.scalar(
            select(EngineeringWorkerExecution)
            .where(EngineeringWorkerExecution.id == execution_id)
            .execution_options(populate_existing=True)
        )

    def acquire(self, *, run_id: str, now: datetime, lease_seconds: int) -> EngineeringWorkerExecution:
        owner_id = f"worker:{uuid4()}"
        expires_at = now + timedelta(seconds=lease_seconds)
        existing = self.get_for_run(run_id)
        if existing is None:
            created = EngineeringWorkerExecution(
                run_id=run_id,
                state=WorkerLifecycleState.RUNNING.value,
                lease_owner_id=owner_id,
                lease_generation=1,
                lease_expires_at=expires_at,
                last_meaningful_progress_at=now,
                revision=1,
            )
            self.session.add(created)
            try:
                self.session.commit()
                self.session.refresh(created)
                return created
            except IntegrityError:
                self.session.rollback()
                existing = self.get_for_run(run_id)
                if existing is None:
                    raise

        lease_expiry = _aware(existing.lease_expires_at)
        if existing.lease_owner_id is not None:
            if lease_expiry is not None and lease_expiry <= now:
                raise WorkerLeaseExpired("worker lease expired; protected recovery/reassignment is required")
            raise WorkerLeaseConflict("Engineering Run already has an active worker lease")

        result = self.session.execute(
            update(EngineeringWorkerExecution)
            .where(
                EngineeringWorkerExecution.id == existing.id,
                EngineeringWorkerExecution.revision == existing.revision,
                EngineeringWorkerExecution.lease_owner_id.is_(None),
                EngineeringWorkerExecution.lease_expires_at.is_(None),
            )
            .values(
                state=WorkerLifecycleState.RUNNING.value,
                lease_owner_id=owner_id,
                lease_generation=existing.lease_generation + 1,
                lease_expires_at=expires_at,
                revision=existing.revision + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            raise WorkerLeaseConflict("worker lease was concurrently acquired")
        self.session.commit()
        refreshed = self.get(existing.id)
        if refreshed is None:
            raise RuntimeError("worker execution disappeared after lease acquisition")
        return refreshed

    def renew(
        self,
        *,
        execution_id: str,
        owner_id: str,
        generation: int,
        now: datetime,
        lease_seconds: int,
    ) -> EngineeringWorkerExecution:
        current = self.get(execution_id)
        if current is None:
            raise WorkerStaleLease("worker execution is unavailable")
        result = self.session.execute(
            update(EngineeringWorkerExecution)
            .where(
                EngineeringWorkerExecution.id == execution_id,
                EngineeringWorkerExecution.revision == current.revision,
                EngineeringWorkerExecution.lease_owner_id == owner_id,
                EngineeringWorkerExecution.lease_generation == generation,
                EngineeringWorkerExecution.lease_expires_at.is_not(None),
                EngineeringWorkerExecution.lease_expires_at > now,
            )
            .values(
                lease_expires_at=now + timedelta(seconds=lease_seconds),
                revision=current.revision + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            raise WorkerStaleLease("worker lease is expired, stale or no longer owned by this execution")
        self.session.commit()
        refreshed = self.get(execution_id)
        if refreshed is None:
            raise RuntimeError("worker execution disappeared after lease renewal")
        return refreshed

    def record_progress(
        self,
        *,
        execution_id: str,
        owner_id: str,
        generation: int,
        expected_revision: int,
        now: datetime,
        lease_seconds: int,
        state: WorkerLifecycleState,
        checkpoint_json: str,
        checkpoint_revision: int,
        current_step: str,
        source_lineage_ref: str | None,
        last_known_good_lineage_ref: str | None,
        retry_count: int,
        no_progress_count: int,
        oscillation_count: int,
        progress_fingerprint: str,
        previous_progress_fingerprint: str | None,
        meaningful_progress: bool,
        blocker_code: str | None,
        next_recovery_action: str | None,
        release_lease: bool,
    ) -> EngineeringWorkerExecution:
        values: dict[str, object] = {
            "state": state.value,
            "checkpoint_json": checkpoint_json,
            "checkpoint_revision": checkpoint_revision,
            "current_step": current_step,
            "source_lineage_ref": source_lineage_ref,
            "last_known_good_lineage_ref": last_known_good_lineage_ref,
            "retry_count": retry_count,
            "no_progress_count": no_progress_count,
            "oscillation_count": oscillation_count,
            "progress_fingerprint": progress_fingerprint,
            "previous_progress_fingerprint": previous_progress_fingerprint,
            "blocker_code": blocker_code,
            "next_recovery_action": next_recovery_action,
            "revision": expected_revision + 1,
            "updated_at": now,
        }
        if meaningful_progress:
            values["last_meaningful_progress_at"] = now
        if release_lease:
            values["lease_owner_id"] = None
            values["lease_expires_at"] = None
        else:
            values["lease_expires_at"] = now + timedelta(seconds=lease_seconds)

        result = self.session.execute(
            update(EngineeringWorkerExecution)
            .where(
                EngineeringWorkerExecution.id == execution_id,
                EngineeringWorkerExecution.revision == expected_revision,
                EngineeringWorkerExecution.lease_owner_id == owner_id,
                EngineeringWorkerExecution.lease_generation == generation,
                EngineeringWorkerExecution.lease_expires_at.is_not(None),
                EngineeringWorkerExecution.lease_expires_at > now,
            )
            .values(**values)
        )
        if result.rowcount != 1:
            self.session.rollback()
            raise WorkerStaleLease("worker progress rejected because lease ownership or revision is stale")
        self.session.commit()
        refreshed = self.get(execution_id)
        if refreshed is None:
            raise RuntimeError("worker execution disappeared after progress commit")
        return refreshed

    def mark_stalled(
        self,
        *,
        run_id: str,
        now: datetime,
        state: WorkerLifecycleState,
        stall_classification: str,
        blocker_code: str | None,
        next_recovery_action: str,
    ) -> EngineeringWorkerExecution:
        current = self.get_for_run(run_id)
        if current is None:
            raise WorkerStaleLease("worker execution is unavailable")
        if current.state in {WorkerLifecycleState.SUCCEEDED.value, WorkerLifecycleState.FAILED.value}:
            return current
        result = self.session.execute(
            update(EngineeringWorkerExecution)
            .where(
                EngineeringWorkerExecution.id == current.id,
                EngineeringWorkerExecution.revision == current.revision,
            )
            .values(
                state=state.value,
                lease_owner_id=None,
                lease_expires_at=None,
                stall_classification=stall_classification,
                blocker_code=blocker_code,
                next_recovery_action=next_recovery_action,
                revision=current.revision + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            raise WorkerStaleLease("worker stall transition lost a concurrent compare-and-swap race")
        self.session.commit()
        refreshed = self.get(current.id)
        if refreshed is None:
            raise RuntimeError("worker execution disappeared after stall transition")
        return refreshed

    def reassign(self, *, run_id: str, now: datetime, lease_seconds: int) -> EngineeringWorkerExecution:
        current = self.get_for_run(run_id)
        if current is None:
            raise WorkerStaleLease("worker execution is unavailable")
        if current.state == WorkerLifecycleState.HUMAN_REQUIRED.value:
            raise WorkerLeaseConflict("HUMAN_REQUIRED worker execution cannot be automatically reassigned")
        if current.state in {WorkerLifecycleState.SUCCEEDED.value, WorkerLifecycleState.FAILED.value}:
            raise WorkerLeaseConflict("terminal worker execution cannot be reassigned")

        expiry = _aware(current.lease_expires_at)
        lease_recoverable = current.lease_owner_id is None or (expiry is not None and expiry <= now)
        if not lease_recoverable:
            raise WorkerLeaseConflict("active worker lease cannot be reassigned")

        owner_id = f"worker:{uuid4()}"
        result = self.session.execute(
            update(EngineeringWorkerExecution)
            .where(
                EngineeringWorkerExecution.id == current.id,
                EngineeringWorkerExecution.revision == current.revision,
                or_(
                    EngineeringWorkerExecution.lease_owner_id.is_(None),
                    EngineeringWorkerExecution.lease_expires_at <= now,
                ),
            )
            .values(
                state=WorkerLifecycleState.REASSIGNED.value,
                lease_owner_id=owner_id,
                lease_generation=current.lease_generation + 1,
                lease_expires_at=now + timedelta(seconds=lease_seconds),
                stall_classification=None,
                blocker_code=None,
                next_recovery_action=None,
                revision=current.revision + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            raise WorkerLeaseConflict("worker reassignment lost a concurrent lease race")
        self.session.commit()
        refreshed = self.get(current.id)
        if refreshed is None:
            raise RuntimeError("worker execution disappeared after reassignment")
        return refreshed
