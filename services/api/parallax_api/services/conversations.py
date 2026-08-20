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
        """Persist the user turn without treating a client hint as scope authority.

        The legacy Boolean remains in the transitional method signature for
        compatibility, but v0.3.0 scope mutation is performed only after the
        protected server-side scope policy resolves the turn.
        """

        del material_scope_change
        conversation = self.get(conversation_id)
        return self.repository.add_message(conversation, "user", content)

    def set_status(self, conversation_id: str, status: str):
        conversation = self.get(conversation_id)
        return self.repository.set_status(conversation, status)
