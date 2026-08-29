from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import AccessPrincipal, access_principal
from ..db import get_session
from .repository import ProjectConflictError, ProjectRepository
from .schemas import ProjectCreate, ProjectDeliveryModeUpdate, ProjectRead
from .service import (
    ProjectDeleteConflictError,
    ProjectDeliveryModeConflictError,
    ProjectNotFoundError,
    ProjectService,
    ProjectValidationError,
)


router = APIRouter(prefix="/v1/projects", tags=["projects"])


def service(session: Session = Depends(get_session)) -> ProjectService:
    return ProjectService(ProjectRepository(session))


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    request: ProjectCreate,
    principal: AccessPrincipal = Depends(access_principal),
    svc: ProjectService = Depends(service),
):
    try:
        return svc.create(owner_subject=principal.subject, request=request)
    except ProjectConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProjectValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[ProjectRead])
def list_projects(
    principal: AccessPrincipal = Depends(access_principal),
    svc: ProjectService = Depends(service),
):
    return svc.list(owner_subject=principal.subject)


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: str,
    principal: AccessPrincipal = Depends(access_principal),
    svc: ProjectService = Depends(service),
):
    try:
        return svc.get(project_id=project_id, owner_subject=principal.subject)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.patch("/{project_id}/delivery", response_model=ProjectRead)
def update_project_delivery(
    project_id: str,
    request: ProjectDeliveryModeUpdate,
    principal: AccessPrincipal = Depends(access_principal),
    svc: ProjectService = Depends(service),
):
    try:
        return svc.update_delivery_mode(
            project_id=project_id,
            owner_subject=principal.subject,
            request=request,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectDeliveryModeConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    principal: AccessPrincipal = Depends(access_principal),
    svc: ProjectService = Depends(service),
):
    try:
        svc.delete(project_id=project_id, owner_subject=principal.subject)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectDeleteConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return None
