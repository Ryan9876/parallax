from __future__ import annotations

from fastapi import HTTPException

from ..intelligence.work_specification import WorkSpecificationDraft
from ..repositories.conversations import ConversationRepository
from ..repositories.work_specifications import WorkSpecificationRepository


class WorkSpecificationService:
    def __init__(
        self,
        repository: WorkSpecificationRepository,
        conversations: ConversationRepository,
    ):
        self.repository = repository
        self.conversations = conversations

    def conversation(self, conversation_id: str):
        conversation = self.conversations.get(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    def latest(self, conversation_id: str):
        self.conversation(conversation_id)
        return self.repository.latest(conversation_id)

    def create_draft(
        self,
        *,
        conversation_id: str,
        draft: WorkSpecificationDraft,
        model_id: str | None,
    ):
        self.conversation(conversation_id)
        return self.repository.create_draft(
            conversation_id=conversation_id,
            draft=draft,
            model_id=model_id,
        )

    def approve(self, specification_id: str):
        specification = self.repository.get(specification_id)
        if specification is None:
            raise HTTPException(status_code=404, detail="Work specification not found")
        try:
            return self.repository.approve(specification)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
