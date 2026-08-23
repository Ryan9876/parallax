from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ..models import Conversation, Message, utcnow
from ..projects.model import Project


class ConversationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        mode: str = "reason",
        *,
        spec_id: str,
        project_id: str | None = None,
    ) -> Conversation:
        conversation = Conversation(mode=mode, spec_id=spec_id, project_id=project_id)
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return conversation

    def list(self) -> list[Conversation]:
        statement = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
        )
        return list(self.session.scalars(statement).unique().all())

    def list_for_owner(self, owner_subject: str) -> list[Conversation]:
        statement = (
            select(Conversation)
            .outerjoin(Project, Conversation.project_id == Project.id)
            .where(
                or_(
                    Conversation.project_id.is_(None),
                    Project.owner_subject == owner_subject,
                )
            )
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
        )
        return list(self.session.scalars(statement).unique().all())

    def get(self, conversation_id: str) -> Conversation | None:
        statement = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return self.session.scalar(statement)

    def get_for_owner(self, conversation_id: str, owner_subject: str) -> Conversation | None:
        statement = (
            select(Conversation)
            .outerjoin(Project, Conversation.project_id == Project.id)
            .where(
                Conversation.id == conversation_id,
                or_(
                    Conversation.project_id.is_(None),
                    Project.owner_subject == owner_subject,
                ),
            )
            .options(selectinload(Conversation.messages))
        )
        return self.session.scalar(statement)

    def add_message(self, conversation: Conversation, role: str, content: str) -> Message:
        message = Message(conversation_id=conversation.id, role=role, content=content)
        if conversation.title == "New conversation" and role == "user":
            conversation.title = content.strip().replace("\n", " ")[:72] or conversation.title
        conversation.updated_at = utcnow()
        self.session.add(message)
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(message)
        return message

    def set_status(self, conversation: Conversation, status: str) -> Conversation:
        conversation.status = status
        conversation.updated_at = utcnow()
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return conversation
