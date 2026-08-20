from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import get_session
from ..intelligence.coordinator import ResponseCoordinator
from ..repositories.conversations import ConversationRepository
from ..schemas import ConversationCreate, ConversationRead, MessageCreate, MessageRead, ResponseRequest
from ..services.conversations import ConversationService

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


def service(session: Session = Depends(get_session)) -> ConversationService:
    return ConversationService(ConversationRepository(session))


@router.post("", response_model=ConversationRead)
def create_conversation(payload: ConversationCreate, svc: ConversationService = Depends(service)):
    return svc.create(payload.mode)


@router.get("", response_model=list[ConversationRead])
def list_conversations(svc: ConversationService = Depends(service)):
    return svc.list()


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: str, svc: ConversationService = Depends(service)):
    return svc.get(conversation_id)


@router.post("/{conversation_id}/messages", response_model=MessageRead)
def append_message(conversation_id: str, payload: MessageCreate, svc: ConversationService = Depends(service)):
    return svc.append_message(conversation_id, payload.role, payload.content)


@router.post("/{conversation_id}/follow-ups", response_model=MessageRead)
def append_follow_up(conversation_id: str, payload: ResponseRequest, svc: ConversationService = Depends(service)):
    return svc.append_follow_up(
        conversation_id,
        payload.content,
        material_scope_change=payload.material_scope_change,
    )


@router.post("/{conversation_id}/responses")
async def stream_response(
    conversation_id: str,
    payload: ResponseRequest,
    svc: ConversationService = Depends(service),
):
    conversation = svc.get(conversation_id)
    svc.append_follow_up(
        conversation_id,
        payload.content,
        material_scope_change=payload.material_scope_change,
    )

    async def events():
        def event(name: str, data: dict) -> str:
            return f"event: {name}\ndata: {json.dumps(data)}\n\n"

        yield event("state", {"phase": "THINKING"})
        if payload.material_scope_change:
            yield event("state", {"phase": "SPEC_AMENDMENT"})
            return

        context = "\n".join(
            f"{message.role}: {message.content}"
            for message in conversation.messages[-12:]
        )
        try:
            result = await ResponseCoordinator().respond(
                conversation_id=conversation.id,
                spec_id=conversation.spec_id,
                mode=conversation.mode,
                objective=payload.content,
                context=context,
            )
        except Exception as exc:
            yield event("error", {"phase": "ERROR", "error": type(exc).__name__})
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
                "trace": result.trace.as_public_dict(),
            },
        )

    return StreamingResponse(events(), media_type="text/event-stream")
