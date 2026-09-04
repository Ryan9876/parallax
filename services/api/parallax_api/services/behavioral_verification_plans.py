from __future__ import annotations

import json

from fastapi import HTTPException

from ..code.work_spec_binding import work_specification_digest
from ..intelligence.behavioral_verification_plan import (
    BehavioralVerificationPlanGeneration,
    behavioral_plan_digest,
    compile_behavioral_plan,
    validate_persisted_behavioral_plan,
)
from ..repositories.behavioral_verification_plans import BehavioralVerificationPlanRepository
from ..repositories.conversations import ConversationRepository
from ..repositories.work_specifications import WorkSpecificationRepository


class BehavioralVerificationPlanService:
    def __init__(
        self,
        plans: BehavioralVerificationPlanRepository,
        specifications: WorkSpecificationRepository,
        conversations: ConversationRepository,
        *,
        owner_subject: str,
    ) -> None:
        subject = owner_subject.strip()
        if not subject:
            raise ValueError("behavioral verification plan service requires an owner subject")
        self.plans = plans
        self.specifications = specifications
        self.conversations = conversations
        self.owner_subject = subject

    def specification_for_owner(self, specification_id: str):
        specification = self.specifications.get(specification_id)
        if specification is None:
            raise HTTPException(status_code=404, detail="Work specification not found")
        conversation = self.conversations.get_for_owner(
            specification.conversation_id,
            self.owner_subject,
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Work specification not found")
        return specification

    def approved_specification(self, specification_id: str):
        specification = self.specification_for_owner(specification_id)
        if specification.status != "APPROVED":
            raise HTTPException(
                status_code=422,
                detail="Behavioral verification plans require an approved Work Specification.",
            )
        return specification

    def latest(self, specification_id: str):
        specification = self.specification_for_owner(specification_id)
        plan = self.plans.latest(specification.id)
        if plan is not None:
            self.validated_payload(plan, specification=specification)
        return plan

    def validated_payload(self, plan, *, specification=None) -> dict[str, object]:
        specification = specification or self.specification_for_owner(plan.work_specification_id)
        if (
            plan.work_specification_id != specification.id
            or plan.work_specification_revision != specification.revision
            or plan.work_specification_digest != work_specification_digest(specification)
        ):
            raise HTTPException(
                status_code=409,
                detail="Behavioral verification plan Work Specification binding is no longer exact.",
            )
        try:
            return validate_persisted_behavioral_plan(
                specification,
                plan_revision=plan.revision,
                plan_json=plan.plan_json,
                plan_digest=plan.plan_digest,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail="Behavioral verification plan failed protected read-back validation.",
            ) from exc

    def create_draft(
        self,
        specification_id: str,
        generation: BehavioralVerificationPlanGeneration,
    ):
        specification = self.approved_specification(specification_id)
        revision = self.plans.next_revision(specification.id)
        try:
            payload = compile_behavioral_plan(
                specification,
                generation.proposal,
                plan_revision=revision,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        plan = self.plans.create_draft(
            work_specification_id=specification.id,
            work_specification_revision=specification.revision,
            work_specification_digest=work_specification_digest(specification),
            revision=revision,
            plan_json=canonical,
            plan_digest=behavioral_plan_digest(payload),
            program_version=generation.program_version,
            model_id=generation.model,
        )
        self.validated_payload(plan, specification=specification)
        return plan

    def approve(self, plan_id: str):
        plan = self.plans.get(plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Behavioral verification plan not found")
        specification = self.specification_for_owner(plan.work_specification_id)
        self.validated_payload(plan, specification=specification)
        if plan.status == "APPROVED":
            return plan
        if specification.status != "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="The bound Work Specification is no longer approved.",
            )
        try:
            return self.plans.approve(plan)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
