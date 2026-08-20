from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models import EngineeringAttempt, EngineeringRun, utcnow


@dataclass(frozen=True, slots=True)
class RecordedMutation:
    run: EngineeringRun
    attempt: EngineeringAttempt
    replayed: bool = False


class EngineeringRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        conversation_id: str,
        spec_id: str,
        workspace_ref: str | None = None,
    ) -> EngineeringRun:
        run = EngineeringRun(
            conversation_id=conversation_id,
            spec_id=spec_id,
            state="SPECIFY",
            revision=0,
            workspace_ref=workspace_ref,
        )
        self.session.add(run)
        self.session.commit()
        return self.get(run.id) or run

    def get(self, run_id: str) -> EngineeringRun | None:
        statement = (
            select(EngineeringRun)
            .where(EngineeringRun.id == run_id)
            .options(selectinload(EngineeringRun.attempts))
        )
        return self.session.scalar(statement)

    def find_operation(self, run_id: str, operation_key: str) -> EngineeringAttempt | None:
        return self.session.scalar(
            select(EngineeringAttempt).where(
                EngineeringAttempt.run_id == run_id,
                EngineeringAttempt.operation_key == operation_key,
            )
        )

    def passing_stage_names(self, run_id: str) -> set[str]:
        rows = self.session.scalars(
            select(EngineeringAttempt.stage).where(
                EngineeringAttempt.run_id == run_id,
                EngineeringAttempt.status == "PASSED",
            )
        ).all()
        return set(rows)

    def _next_attempt_number(self, run_id: str, stage: str) -> int:
        current = self.session.scalar(
            select(func.max(EngineeringAttempt.attempt_number)).where(
                EngineeringAttempt.run_id == run_id,
                EngineeringAttempt.stage == stage,
            )
        )
        return int(current or 0) + 1

    def record(
        self,
        run: EngineeringRun,
        *,
        stage: str,
        operation_key: str,
        status: str,
        next_state: str,
        evidence: dict | None = None,
        failure_code: str | None = None,
        resume_stage: str | None = None,
        program_id: str | None = None,
        model_id: str | None = None,
        tool_id: str | None = None,
    ) -> RecordedMutation:
        payload = json.dumps(evidence or {}, sort_keys=True, separators=(",", ":"))
        if len(payload) > 24_000:
            raise ValueError("engineering attempt evidence exceeds protected bound")

        attempt = EngineeringAttempt(
            run_id=run.id,
            stage=stage,
            attempt_number=self._next_attempt_number(run.id, stage),
            operation_key=operation_key,
            status=status,
            evidence_json=payload,
            failure_code=failure_code,
            program_id=program_id,
            model_id=model_id,
            tool_id=tool_id,
            completed_at=utcnow(),
        )
        run.state = next_state
        run.resume_stage = resume_stage
        run.last_failure_code = failure_code
        run.revision += 1
        run.updated_at = utcnow()
        if next_state == "COMPLETE":
            run.completed_at = utcnow()

        self.session.add(attempt)
        self.session.add(run)
        self.session.commit()
        self.session.refresh(attempt)
        refreshed = self.get(run.id) or run
        return RecordedMutation(run=refreshed, attempt=attempt)
