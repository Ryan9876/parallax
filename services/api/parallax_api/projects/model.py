from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..models import utcnow


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index(
            "uq_projects_owner_slug_active",
            "owner_subject",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_projects_owner_repository_active",
            "owner_subject",
            "repository_ref",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND repository_ref IS NOT NULL"),
            sqlite_where=text("deleted_at IS NULL AND repository_ref IS NOT NULL"),
        ),
        UniqueConstraint("workspace_ref", name="uq_projects_workspace_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_subject: Mapped[str] = mapped_column(String(160), index=True)
    slug: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository_ref: Mapped[str | None] = mapped_column(String(240), nullable=True)
    workspace_ref: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
