from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .common import utcnow
from .conversations import Conversation


class WorkSpecification(Base):
    __tablename__ = "work_specifications"
    __table_args__ = (
        UniqueConstraint("conversation_id", "revision", name="uq_work_spec_conversation_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", index=True)
    title: Mapped[str] = mapped_column(String(120))
    objective: Mapped[str] = mapped_column(Text)
    constraints_json: Mapped[str] = mapped_column(Text, default="[]")
    acceptance_criteria_json: Mapped[str] = mapped_column(Text, default="[]")
    risks_json: Mapped[str] = mapped_column(Text, default="[]")
    open_questions_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    program_version: Mapped[str] = mapped_column(String(100))
    model_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="work_specifications")


class BehavioralVerificationPlan(Base):
    __tablename__ = "behavioral_verification_plans"
    __table_args__ = (
        UniqueConstraint(
            "work_specification_id",
            "revision",
            name="uq_behavioral_plan_spec_revision",
        ),
        CheckConstraint("revision > 0", name="ck_behavioral_plan_revision_positive"),
        CheckConstraint(
            "work_specification_revision > 0",
            name="ck_behavioral_plan_spec_revision_positive",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'APPROVED', 'SUPERSEDED')",
            name="ck_behavioral_plan_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    work_specification_id: Mapped[str] = mapped_column(
        ForeignKey("work_specifications.id", ondelete="CASCADE"),
        index=True,
    )
    work_specification_revision: Mapped[int] = mapped_column(Integer)
    work_specification_digest: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", index=True)
    plan_json: Mapped[str] = mapped_column(Text)
    plan_digest: Mapped[str] = mapped_column(String(64))
    program_version: Mapped[str] = mapped_column(String(100))
    model_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
