from __future__ import annotations

from fastapi import HTTPException

from ..config import settings
from ..projects.repository import ProjectRepository
from ..repositories.conversations import ConversationRepository


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepository,
        project_repository: ProjectRepository | None = None,
        *,
        owner_subject: str | None = None,
        active_spec_id: str | None = None,
        require_project_binding: bool = False,
    ):
        self.repository = repository
        self.projects = project_repository
        self.owner_subject = owner_subject.strip() if owner_subject else None
        self.require_project_binding = require_project_binding
        self.active_spec_id = active_spec_id or settings.active_spec_id

    def _resolve_project(self, project_id: str | None):
        if project_id is None:
            return None
        if not self.owner_subject or self.projects is None:
            if self.require_project_binding:
                raise HTTPException(status_code=500, detail="Project binding service unavailable")
            return None
        project = self.projects.get_for_owner(project_id, self.owner_subject)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def project_for_conversation(self, conversation):
        if conversation.project_id is None:
            return None
        return self._resolve_project(conversation.project_id)

    def create(self, mode: str, project_id: str | None = None):
        if self.require_project_binding and mode == "code" and project_id is None:
            raise HTTPException(status_code=422, detail="Code conversations require a canonical Project")
        if project_id is not None:
            self._resolve_project(project_id)
        return self.repository.create(mode, spec_id=self.active_spec_id, project_id=project_id)

    def list(self):
        if self.owner_subject:
            return self.repository.list_for_owner(self.owner_subject)
        return self.repository.list()

    def get(self, conversation_id: str):
        conversation = (
            self.repository.get_for_owner(conversation_id, self.owner_subject)
            if self.owner_subject
            else self.repository.get(conversation_id)
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    def delete(self, conversation_id: str) -> None:
        conversation = self.get(conversation_id)
        if self.repository.has_nonterminal_run(conversation.id):
            raise HTTPException(
                status_code=409,
                detail="Conversation has active engineering work. Cancel or complete it before deleting the conversation.",
            )
        self.repository.soft_delete(conversation)

    def append_message(self, conversation_id: str, role: str, content: str):
        conversation = self.get(conversation_id)
        return self.repository.add_message(conversation, role, content)

    def append_follow_up(self, conversation_id: str, content: str, *, material_scope_change: bool = False):
        """Persist the user turn without treating a client hint as scope authority."""
        del material_scope_change
        conversation = self.get(conversation_id)
        return self.repository.add_message(conversation, "user", content)

    def set_status(self, conversation_id: str, status: str):
        conversation = self.get(conversation_id)
        return self.repository.set_status(conversation, status)
