from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import AccessPrincipal, access_principal
from ..db import get_session
from ..intelligence.behavioral_verification_plan import (
    BehavioralVerificationPlanCoordinator,
    BehavioralVerificationPlanGenerationFailure,
)
from ..intelligence.router import RoutingFailureKind
from ..intelligence.work_specification import (
    WorkSpecificationCoordinator,
    WorkSpecificationGenerationFailure,
)
from ..models import WorkSpecification
from ..intelligence.project_context import compose_project_capability_context
from ..projects.repository import ProjectRepository
from ..repositories.behavioral_verification_plans import BehavioralVerificationPlanRepository
from ..repositories.conversations import ConversationRepository
from ..repositories.work_specifications import WorkSpecificationRepository
from ..schemas import BehavioralVerificationPlanRead, ConversationRead, WorkSpecificationRead
from ..services.behavioral_verification_plans import BehavioralVerificationPlanService
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


def behavioral_plan_service(
    session: Session = Depends(get_session),
    principal: AccessPrincipal = Depends(access_principal),
) -> BehavioralVerificationPlanService:
    return BehavioralVerificationPlanService(
        BehavioralVerificationPlanRepository(session),
        WorkSpecificationRepository(session),
        ConversationRepository(session),
        owner_subject=principal.subject,
    )


def behavioral_plan_coordinator() -> BehavioralVerificationPlanCoordinator:
    return BehavioralVerificationPlanCoordinator()


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


def present_behavioral_plan(plan, svc: BehavioralVerificationPlanService) -> dict:
    payload = svc.validated_payload(plan)
    return {
        "id": plan.id,
        "work_specification_id": plan.work_specification_id,
        "work_specification_revision": plan.work_specification_revision,
        "work_specification_digest": plan.work_specification_digest,
        "revision": plan.revision,
        "status": plan.status,
        "plan_digest": plan.plan_digest,
        "criteria": payload["criteria"],
        "program_version": plan.program_version,
        "model_id": plan.model_id,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
        "approved_at": plan.approved_at,
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
        if exc.kind is RoutingFailureKind.RATE_LIMITED:
            raise HTTPException(
                status_code=429,
                detail="Model capacity is temporarily unavailable. Retry Capture Spec later; your objective is preserved.",
            ) from exc
        if exc.kind is RoutingFailureKind.VALIDATION_EXHAUSTED:
            raise HTTPException(
                status_code=503,
                detail="Parallax could not validate a Work Specification draft. The conversation is preserved; retry Capture Spec.",
            ) from exc
        raise HTTPException(
            status_code=503,
            detail="The Work Specification model provider is temporarily unavailable. The conversation is preserved; retry Capture Spec later.",
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

@router.get(
    "/work-specifications/{specification_id}/behavioral-verification-plan",
    response_model=BehavioralVerificationPlanRead | None,
)
def latest_behavioral_verification_plan(
    specification_id: str,
    svc: BehavioralVerificationPlanService = Depends(behavioral_plan_service),
):
    plan = svc.latest(specification_id)
    return present_behavioral_plan(plan, svc) if plan is not None else None


@router.post(
    "/work-specifications/{specification_id}/behavioral-verification-plan/draft",
    response_model=BehavioralVerificationPlanRead,
)
async def draft_behavioral_verification_plan(
    specification_id: str,
    svc: BehavioralVerificationPlanService = Depends(behavioral_plan_service),
    plan_coordinator: BehavioralVerificationPlanCoordinator = Depends(behavioral_plan_coordinator),
):
    specification = svc.approved_specification(specification_id)
    try:
        generation = await plan_coordinator.draft(specification)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except BehavioralVerificationPlanGenerationFailure as exc:
        if exc.kind is RoutingFailureKind.RATE_LIMITED:
            raise HTTPException(
                status_code=429,
                detail="Model capacity is temporarily unavailable. Retry verification-plan creation later.",
            ) from exc
        if exc.kind is RoutingFailureKind.VALIDATION_EXHAUSTED:
            raise HTTPException(
                status_code=503,
                detail="Parallax could not validate a bounded behavioral verification plan.",
            ) from exc
        raise HTTPException(
            status_code=503,
            detail="The behavioral verification plan provider is temporarily unavailable.",
        ) from exc
    plan = svc.create_draft(specification_id, generation)
    return present_behavioral_plan(plan, svc)


@router.post(
    "/behavioral-verification-plans/{plan_id}/approve",
    response_model=BehavioralVerificationPlanRead,
)
def approve_behavioral_verification_plan(
    plan_id: str,
    svc: BehavioralVerificationPlanService = Depends(behavioral_plan_service),
):
    plan = svc.approve(plan_id)
    return present_behavioral_plan(plan, svc)

