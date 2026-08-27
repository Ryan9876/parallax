from __future__ import annotations

import json

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import AccessPrincipal, access_principal
from ..config import settings
from ..db import get_session
from ..intelligence.context import ContextLimitError, compose_reason_context
from ..intelligence.project_context import compose_project_capability_context
from ..intelligence.coordinator import ResponseCoordinationFailure, ResponseCoordinator
from ..intelligence.scope import ScopeDecision
from ..projects.repository import ProjectRepository
from ..repositories.conversations import ConversationRepository
from ..schemas import ConversationCreate, ConversationRead, MessageCreate, MessageRead, ResponseRequest
from ..services.conversations import ConversationService

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])

AMENDMENT_MESSAGE = (
    "This request materially changes the approved objective. "
    "An approved specification amendment is required before I continue against the new objective."
)

CODE_OBJECTIVE_CAPTURED_MESSAGE = (
    "Objective captured. Capture the Work Specification to continue with governed Code execution."
)

MODEL_CAPACITY_RECOVERY_MESSAGE = (
    "Model capacity is temporarily unavailable. Your message is saved; "
    "when capacity returns, continue from here instead of sending it again."
)

MODEL_PROVIDER_RECOVERY_MESSAGE = (
    "Parallax model provider is temporarily unavailable. Your message is saved; "
    "when service returns, continue from here instead of sending it again."
)


def _coordination_failure_message(exc: ResponseCoordinationFailure) -> str:
    if exc.error_code == "MODEL_CAPACITY_RATE_LIMITED":
        return MODEL_CAPACITY_RECOVERY_MESSAGE
    if exc.error_code == "MODEL_PROVIDER_UNAVAILABLE":
        return MODEL_PROVIDER_RECOVERY_MESSAGE
    return f"{exc.public_message} Your conversation is preserved; retry or refine the request."


def service(
    session: Session = Depends(get_session),
    principal: AccessPrincipal = Depends(access_principal),
) -> ConversationService:
    return ConversationService(
        ConversationRepository(session),
        ProjectRepository(session),
        owner_subject=principal.subject,
        owner_role=principal.role,
        require_project_binding=True,
    )


@router.post("", response_model=ConversationRead)
def create_conversation(payload: ConversationCreate, svc: ConversationService = Depends(service)):
    return svc.create(payload.mode, payload.project_id)


@router.get("", response_model=list[ConversationRead])
def list_conversations(svc: ConversationService = Depends(service)):
    return svc.list()


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: str, svc: ConversationService = Depends(service)):
    return svc.get(conversation_id)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, svc: ConversationService = Depends(service)):
    svc.delete(conversation_id)
    return None


@router.post("/{conversation_id}/messages", response_model=MessageRead)
def append_message(conversation_id: str, payload: MessageCreate, svc: ConversationService = Depends(service)):
    return svc.append_message(conversation_id, payload.role, payload.content)


@router.post("/{conversation_id}/follow-ups", response_model=MessageRead)
def append_follow_up(conversation_id: str, payload: ResponseRequest, svc: ConversationService = Depends(service)):
    return svc.append_follow_up(conversation_id, payload.content)


@router.post("/{conversation_id}/responses")
async def stream_response(
    conversation_id: str,
    payload: ResponseRequest,
    svc: ConversationService = Depends(service),
):
    conversation = svc.get(conversation_id)
    prior_messages = tuple(conversation.messages)
    first_code_objective = (
        conversation.mode == "code"
        and conversation.status == "ACTIVE"
        and not any(
            item.role == "user" and item.content.strip()
            for item in prior_messages
        )
    )
    svc.append_follow_up(conversation_id, payload.content)

    async def events():
        def event(name: str, data: dict) -> str:
            return f"event: {name}\ndata: {json.dumps(data)}\n\n"

        yield event("state", {"phase": "THINKING"})

        if first_code_objective:
            assistant = svc.append_message(
                conversation_id,
                "assistant",
                CODE_OBJECTIVE_CAPTURED_MESSAGE,
            )
            yield event("state", {"phase": "RESPONDING"})
            yield event("chunk", {"text": CODE_OBJECTIVE_CAPTURED_MESSAGE})
            yield event("state", {"phase": "VERIFYING"})
            yield event(
                "complete",
                {
                    "phase": "COMPLETE",
                    "message_id": assistant.id,
                    "confidence": 1.0,
                    "scope_decision": None,
                    "material_uncertainties": [],
                    "assumptions": [],
                },
            )
            return

        try:
            project_context = None
            if conversation.mode == "code" and conversation.project_id:
                project = svc.project_for_conversation(conversation)
                if project is not None:
                    project_context = compose_project_capability_context(
                        project_id=project.id,
                        repository_ref=project.repository_ref,
                    )
            context = compose_reason_context(
                conversation_id=conversation.id,
                spec_id=conversation.spec_id,
                status=conversation.status,
                mode=conversation.mode,
                current_user_turn=payload.content,
                prior_messages=prior_messages,
                project_context=project_context,
            )
            result = await ResponseCoordinator().respond(
                conversation_id=conversation.id,
                spec_id=conversation.spec_id,
                mode=conversation.mode,
                objective=payload.content,
                current_user_turn=payload.content,
                context=context,
                explicit_test_scope_override=(
                    settings.allow_scope_override and payload.material_scope_change
                ),
            )
        except ContextLimitError:
            yield event(
                "error",
                {
                    "phase": "ERROR",
                    "error": "CONTEXT_LIMIT",
                    "recoverable": True,
                    "message": "The active conversation context exceeded protected limits. Your conversation is preserved.",
                },
            )
            return
        except ResponseCoordinationFailure as exc:
            yield event(
                "error",
                {
                    "phase": "ERROR",
                    "error": exc.error_code,
                    "recoverable": True,
                    "message": _coordination_failure_message(exc),
                    "trace": exc.trace.as_public_dict(),
                },
            )
            return
        except Exception as exc:
            yield event(
                "error",
                {
                    "phase": "ERROR",
                    "error": type(exc).__name__,
                    "recoverable": True,
                    "message": "Parallax could not complete this response. Your conversation is preserved.",
                },
            )
            return

        if result.scope.decision is ScopeDecision.SPEC_AMENDMENT:
            svc.set_status(conversation_id, "SPEC_AMENDMENT")
            assistant = svc.append_message(conversation_id, "assistant", AMENDMENT_MESSAGE)
            yield event("state", {"phase": "SPEC_AMENDMENT"})
            yield event(
                "amendment",
                {
                    "phase": "SPEC_AMENDMENT",
                    "message_id": assistant.id,
                    "text": AMENDMENT_MESSAGE,
                    "confidence": result.confidence,
                    "scope_decision": result.scope.decision.value,
                    "trace": result.trace.as_public_dict(),
                },
            )
            return

        if result.answer is None:
            yield event(
                "error",
                {
                    "phase": "ERROR",
                    "error": "MISSING_REASON_ANSWER",
                    "recoverable": True,
                    "message": "Parallax could not complete this response. Your conversation is preserved.",
                },
            )
            return

        yield event("state", {"phase": "RESPONDING"})
        chunk_size = 48
        for start in range(0, len(result.answer), chunk_size):
            yield event("chunk", {"text": result.answer[start:start + chunk_size]})
        yield event("state", {"phase": "VERIFYING"})
        assistant = svc.append_message(conversation_id, "assistant", result.answer)
        yield event(
            "complete",
            {
                "phase": "COMPLETE",
                "message_id": assistant.id,
                "confidence": result.confidence,
                "scope_decision": result.scope.decision.value,
                "material_uncertainties": list(result.material_uncertainties),
                "assumptions": list(result.assumptions),
                "trace": result.trace.as_public_dict(),
            },
        )

    return StreamingResponse(events(), media_type="text/event-stream")
