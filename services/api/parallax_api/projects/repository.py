from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import EngineeringRun, utcnow
from .model import Project


def terminal_run_states() -> frozenset[str]:
    # Import lazily because parallax_api.code exports EngineeringRunService,
    # which itself composes ProjectRepository during package initialization.
    from ..code.domain import TERMINAL_STAGES

    return frozenset(stage.value for stage in TERMINAL_STAGES)


class ProjectConflictError(RuntimeError):
    pass


class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        owner_subject: str,
        slug: str,
        name: str,
        description: str | None,
        repository_ref: str | None,
        delivery_mode: str,
    ) -> Project:
        project_id = str(uuid4())
        project = Project(
            id=project_id,
            owner_subject=owner_subject,
            slug=slug,
            name=name,
            description=description,
            repository_ref=repository_ref,
            workspace_ref=f"project:{project_id}",
            delivery_mode=delivery_mode,
            status="active",
        )
        self.session.add(project)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ProjectConflictError("project slug or repository reference already exists for this owner") from exc
        self.session.refresh(project)
        return project

    def list_for_owner(self, owner_subject: str) -> list[Project]:
        statement = (
            select(Project)
            .where(
                Project.owner_subject == owner_subject,
                Project.deleted_at.is_(None),
            )
            .order_by(Project.created_at.asc(), Project.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def get_for_owner(self, project_id: str, owner_subject: str) -> Project | None:
        statement = select(Project).where(
            Project.id == project_id,
            Project.owner_subject == owner_subject,
            Project.deleted_at.is_(None),
        )
        return self.session.scalar(statement)

    def has_nonterminal_run(self, project_id: str) -> bool:
        statement = (
            select(EngineeringRun.id)
            .where(
                EngineeringRun.project_id == project_id,
                EngineeringRun.state.notin_(terminal_run_states()),
            )
            .limit(1)
        )
        return self.session.scalar(statement) is not None

    def soft_delete(self, project: Project) -> None:
        project.status = "deleted"
        project.deleted_at = utcnow()
        project.updated_at = project.deleted_at
        self.session.add(project)
        self.session.commit()
