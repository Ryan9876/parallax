from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    mode: Mapped[str] = mapped_column(String(20), default="reason")
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    spec_id: Mapped[str] = mapped_column(String(64), default="P2-V0.3.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class EngineeringRun(Base):
    __tablename__ = "engineering_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    spec_id: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[str] = mapped_column(String(32), default="SPECIFY", index=True)
    resume_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    workspace_ref: Mapped[str | None] = mapped_column(String(300), nullable=True)
    last_failure_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    attempts: Mapped[list["EngineeringAttempt"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="EngineeringAttempt.id",
    )


class EngineeringAttempt(Base):
    __tablename__ = "engineering_attempts"
    __table_args__ = (
        UniqueConstraint("run_id", "operation_key", name="uq_engineering_attempt_run_operation"),
        UniqueConstraint("run_id", "stage", "attempt_number", name="uq_engineering_attempt_stage_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("engineering_runs.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(32), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    operation_key: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(32))
    program_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tool_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    failure_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[EngineeringRun] = relationship(back_populates="attempts")
