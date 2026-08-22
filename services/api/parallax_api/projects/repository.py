from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .model import Project


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
            .where(Project.owner_subject == owner_subject)
            .order_by(Project.created_at.asc(), Project.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def get_for_owner(self, project_id: str, owner_subject: str) -> Project | None:
        statement = select(Project).where(
            Project.id == project_id,
            Project.owner_subject == owner_subject,
        )
        return self.session.scalar(statement)
