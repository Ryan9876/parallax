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
        *,
        owner_subject: str | None = None,
    ):
        self.repository = repository
        self.conversations = conversations
        self.owner_subject = owner_subject.strip() if owner_subject else None

    def conversation(self, conversation_id: str):
        conversation = (
            self.conversations.get_for_owner(conversation_id, self.owner_subject)
            if self.owner_subject
            else self.conversations.get(conversation_id)
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    def latest(self, conversation_id: str):
        self.conversation(conversation_id)
        return self.repository.latest(conversation_id)

    def latest_approved(self, conversation_id: str):
        self.conversation(conversation_id)
        return self.repository.latest_approved(conversation_id)

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

        conversation = self.conversation(specification.conversation_id)
        latest = self.repository.latest(specification.conversation_id)
        releases_amendment = (
            conversation.status == "SPEC_AMENDMENT"
            and specification.status == "DRAFT"
            and latest is not None
            and latest.id == specification.id
        )

        try:
            approved = self.repository.approve(specification)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if releases_amendment:
            self.conversations.set_status(conversation, "ACTIVE")

        return approved

    def resume_approved_scope(self, conversation_id: str):
        conversation = self.conversation(conversation_id)
        if conversation.status != "SPEC_AMENDMENT":
            raise HTTPException(
                status_code=409,
                detail="conversation is not waiting for a specification amendment",
            )

        latest = self.repository.latest(conversation_id)
        if latest is None or latest.status != "APPROVED":
            raise HTTPException(
                status_code=422,
                detail="approve the current work specification before resuming its scope",
            )

        return self.conversations.set_status(conversation, "ACTIVE")
