from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..code.worker_recovery import WorkerLifecycleState
from ..db import Base
from .common import utcnow


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
