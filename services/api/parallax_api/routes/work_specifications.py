from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import AccessPrincipal, access_principal
from ..db import get_session
from ..intelligence.work_specification import (
    WorkSpecificationCoordinator,
    WorkSpecificationGenerationFailure,
)
from ..models import WorkSpecification
from ..intelligence.project_context import compose_project_capability_context
from ..projects.repository import ProjectRepository
from ..repositories.conversations import ConversationRepository
from ..repositories.work_specifications import WorkSpecificationRepository
from ..schemas import ConversationRead, WorkSpecificationRead
from ..services.work_specifications import WorkSpecificationService

router = APIRouter(prefix="/v1", tags=["work-specifications"])


def service(
    session: Session = Depends(get_session),
    principal: AccessPrincipal = Depends(access_principal),
) -> WorkSpecificationService:
    return WorkSpecificationService(
        WorkSpecificationRepository(session),
        ConversationRepository(session),
        ProjectRepository(session),
        owner_subject=principal.subject,
    )


def coordinator() -> WorkSpecificationCoordinator:
    return WorkSpecificationCoordinator()


def present(specification: WorkSpecification) -> dict:
    return {
        "id": specification.id,
        "conversation_id": specification.conversation_id,
        "revision": specification.revision,
        "status": specification.status,
        "title": specification.title,
        "objective": specification.objective,
        "constraints": json.loads(specification.constraints_json),
        "acceptance_criteria": json.loads(specification.acceptance_criteria_json),
        "risks": json.loads(specification.risks_json),
        "open_questions": json.loads(specification.open_questions_json),
        "confidence": specification.confidence,
        "program_version": specification.program_version,
        "model_id": specification.model_id,
        "created_at": specification.created_at,
        "updated_at": specification.updated_at,
        "approved_at": specification.approved_at,
    }


@router.get(
    "/conversations/{conversation_id}/work-specifications/latest",
    response_model=WorkSpecificationRead | None,
)
def latest_work_specification(
    conversation_id: str,
    svc: WorkSpecificationService = Depends(service),
):
    specification = svc.latest(conversation_id)
    return present(specification) if specification else None


@router.get(
    "/conversations/{conversation_id}/work-specifications/approved",
    response_model=WorkSpecificationRead | None,
)
def latest_approved_work_specification(
    conversation_id: str,
    svc: WorkSpecificationService = Depends(service),
):
    specification = svc.latest_approved(conversation_id)
    return present(specification) if specification else None


@router.post(
    "/conversations/{conversation_id}/work-specifications/draft",
    response_model=WorkSpecificationRead,
)
async def draft_work_specification(
    conversation_id: str,
    svc: WorkSpecificationService = Depends(service),
    spec_coordinator: WorkSpecificationCoordinator = Depends(coordinator),
):
    conversation = svc.conversation(conversation_id)
    project_context = None
    if getattr(conversation, "mode", None) == "code" and getattr(conversation, "project_id", None):
        project = svc.project_for_conversation(conversation)
        if project is not None:
            project_context = compose_project_capability_context(
                project_id=project.id,
                repository_ref=project.repository_ref,
            )
    try:
        generated = await spec_coordinator.draft(
            conversation.messages,
            project_context=project_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WorkSpecificationGenerationFailure as exc:
        raise HTTPException(
            status_code=503,
            detail="Parallax could not produce a valid work specification draft. The conversation is preserved.",
        ) from exc
    specification = svc.create_draft(
        conversation_id=conversation_id,
        draft=generated.draft,
        model_id=generated.model,
    )
    return present(specification)


@router.post(
    "/work-specifications/{specification_id}/approve",
    response_model=WorkSpecificationRead,
)
def approve_work_specification(
    specification_id: str,
    svc: WorkSpecificationService = Depends(service),
):
    return present(svc.approve(specification_id))


@router.post(
    "/conversations/{conversation_id}/work-specifications/resume-approved-scope",
    response_model=ConversationRead,
)
def resume_approved_scope(
    conversation_id: str,
    svc: WorkSpecificationService = Depends(service),
):
    return svc.resume_approved_scope(conversation_id)
