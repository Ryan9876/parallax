from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..intelligence.work_specification import WorkSpecificationDraft
from ..models import WorkSpecification, utcnow


class WorkSpecificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, specification_id: str) -> WorkSpecification | None:
        return self.session.get(WorkSpecification, specification_id)

    def latest(self, conversation_id: str) -> WorkSpecification | None:
        statement = (
            select(WorkSpecification)
            .where(WorkSpecification.conversation_id == conversation_id)
            .order_by(WorkSpecification.revision.desc())
        )
        return self.session.scalar(statement)

    def latest_approved(self, conversation_id: str) -> WorkSpecification | None:
        statement = (
            select(WorkSpecification)
            .where(
                WorkSpecification.conversation_id == conversation_id,
                WorkSpecification.status == "APPROVED",
            )
            .order_by(WorkSpecification.revision.desc())
        )
        return self.session.scalar(statement)

    def list_for_conversation(self, conversation_id: str) -> list[WorkSpecification]:
        statement = (
            select(WorkSpecification)
            .where(WorkSpecification.conversation_id == conversation_id)
            .order_by(WorkSpecification.revision.desc())
        )
        return list(self.session.scalars(statement).all())

    def create_draft(
        self,
        *,
        conversation_id: str,
        draft: WorkSpecificationDraft,
        model_id: str | None,
    ) -> WorkSpecification:
        latest = self.latest(conversation_id)
        revision = (latest.revision + 1) if latest else 1

        for item in self.list_for_conversation(conversation_id):
            if item.status == "DRAFT":
                item.status = "SUPERSEDED"
                item.updated_at = utcnow()
                self.session.add(item)

        specification = WorkSpecification(
            conversation_id=conversation_id,
            revision=revision,
            status="DRAFT",
            title=draft.title,
            objective=draft.objective,
            constraints_json=json.dumps(draft.constraints, ensure_ascii=False),
            acceptance_criteria_json=json.dumps(draft.acceptance_criteria, ensure_ascii=False),
            risks_json=json.dumps(draft.risks, ensure_ascii=False),
            open_questions_json=json.dumps(draft.open_questions, ensure_ascii=False),
            confidence=draft.confidence,
            program_version=draft.program_version,
            model_id=model_id,
        )
        self.session.add(specification)
        self.session.commit()
        self.session.refresh(specification)
        return specification

    def approve(self, specification: WorkSpecification) -> WorkSpecification:
        if specification.status == "APPROVED":
            return specification
        if specification.status != "DRAFT":
            raise ValueError("only a draft work specification can be approved")

        statement = select(WorkSpecification).where(
            WorkSpecification.conversation_id == specification.conversation_id,
            WorkSpecification.status == "APPROVED",
            WorkSpecification.id != specification.id,
        )
        for item in self.session.scalars(statement).all():
            item.status = "SUPERSEDED"
            item.updated_at = utcnow()
            self.session.add(item)

        specification.status = "APPROVED"
        specification.approved_at = utcnow()
        specification.updated_at = utcnow()
        self.session.add(specification)
        self.session.commit()
        self.session.refresh(specification)
        return specification
