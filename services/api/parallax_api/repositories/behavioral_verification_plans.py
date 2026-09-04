from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BehavioralVerificationPlan, utcnow


class BehavioralVerificationPlanRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, plan_id: str) -> BehavioralVerificationPlan | None:
        return self.session.get(BehavioralVerificationPlan, plan_id)

    def latest(self, work_specification_id: str) -> BehavioralVerificationPlan | None:
        statement = (
            select(BehavioralVerificationPlan)
            .where(BehavioralVerificationPlan.work_specification_id == work_specification_id)
            .order_by(BehavioralVerificationPlan.revision.desc())
        )
        return self.session.scalar(statement)

    def latest_approved(self, work_specification_id: str) -> BehavioralVerificationPlan | None:
        statement = (
            select(BehavioralVerificationPlan)
            .where(
                BehavioralVerificationPlan.work_specification_id == work_specification_id,
                BehavioralVerificationPlan.status == "APPROVED",
            )
            .order_by(BehavioralVerificationPlan.revision.desc())
        )
        return self.session.scalar(statement)

    def next_revision(self, work_specification_id: str) -> int:
        latest = self.latest(work_specification_id)
        return (latest.revision + 1) if latest is not None else 1

    def create_draft(
        self,
        *,
        work_specification_id: str,
        work_specification_revision: int,
        work_specification_digest: str,
        revision: int,
        plan_json: str,
        plan_digest: str,
        program_version: str,
        model_id: str | None,
    ) -> BehavioralVerificationPlan:
        for item in self.list_for_specification(work_specification_id):
            if item.status == "DRAFT":
                item.status = "SUPERSEDED"
                item.updated_at = utcnow()
                self.session.add(item)

        plan = BehavioralVerificationPlan(
            work_specification_id=work_specification_id,
            work_specification_revision=work_specification_revision,
            work_specification_digest=work_specification_digest,
            revision=revision,
            status="DRAFT",
            plan_json=plan_json,
            plan_digest=plan_digest,
            program_version=program_version,
            model_id=model_id,
        )
        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return plan

    def list_for_specification(self, work_specification_id: str) -> list[BehavioralVerificationPlan]:
        statement = (
            select(BehavioralVerificationPlan)
            .where(BehavioralVerificationPlan.work_specification_id == work_specification_id)
            .order_by(BehavioralVerificationPlan.revision.desc())
        )
        return list(self.session.scalars(statement).all())

    def approve(self, plan: BehavioralVerificationPlan) -> BehavioralVerificationPlan:
        if plan.status == "APPROVED":
            return plan
        if plan.status != "DRAFT":
            raise ValueError("only a draft behavioral verification plan can be approved")

        statement = select(BehavioralVerificationPlan).where(
            BehavioralVerificationPlan.work_specification_id == plan.work_specification_id,
            BehavioralVerificationPlan.status == "APPROVED",
            BehavioralVerificationPlan.id != plan.id,
        )
        for item in self.session.scalars(statement).all():
            item.status = "SUPERSEDED"
            item.updated_at = utcnow()
            self.session.add(item)

        plan.status = "APPROVED"
        plan.approved_at = utcnow()
        plan.updated_at = utcnow()
        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return plan
