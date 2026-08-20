from __future__ import annotations

from fastapi import HTTPException

from ..repositories.conversations import ConversationRepository


class ConversationService:
    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    def create(self, mode: str):
        return self.repository.create(mode)

    def list(self):
        return self.repository.list()

    def get(self, conversation_id: str):
        conversation = self.repository.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    def append_message(self, conversation_id: str, role: str, content: str):
        conversation = self.get(conversation_id)
        return self.repository.add_message(conversation, role, content)

    def append_follow_up(self, conversation_id: str, content: str, *, material_scope_change: bool = False):
        conversation = self.get(conversation_id)
        if material_scope_change:
            conversation.status = "SPEC_AMENDMENT"
        elif conversation.status == "ACTIVE":
            conversation.status = "ACTIVE"
        return self.repository.add_message(conversation, "user", content)
