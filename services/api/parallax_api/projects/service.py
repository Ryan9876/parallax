from __future__ import annotations

from .model import Project
from .repository import ProjectConflictError, ProjectRepository
from .schemas import ProjectCreate, slug_from_name


class ProjectNotFoundError(LookupError):
    pass


class ProjectValidationError(ValueError):
    pass


class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository

    def create(self, *, owner_subject: str, request: ProjectCreate) -> Project:
        owner = owner_subject.strip()
        if not owner:
            raise ProjectValidationError("owner subject is required")
        try:
            slug = request.slug or slug_from_name(request.name)
        except ValueError as exc:
            raise ProjectValidationError(str(exc)) from exc
        return self.repository.create(
            owner_subject=owner,
            slug=slug,
            name=request.name,
            description=request.description,
            repository_ref=request.repository_ref,
        )

    def list(self, *, owner_subject: str) -> list[Project]:
        return self.repository.list_for_owner(owner_subject.strip())

    def get(self, *, project_id: str, owner_subject: str) -> Project:
        project = self.repository.get_for_owner(project_id, owner_subject.strip())
        if project is None:
            raise ProjectNotFoundError("Project not found")
        return project


__all__ = [
    "ProjectConflictError",
    "ProjectNotFoundError",
    "ProjectService",
    "ProjectValidationError",
]
