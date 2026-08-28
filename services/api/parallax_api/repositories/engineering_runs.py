from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models import EngineeringAttempt, EngineeringRun, utcnow


_MAX_PROJECT_HISTORY = 25


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
        project_id: str | None,
        work_specification_id: str,
        work_specification_revision: int,
        work_specification_digest: str,
        workspace_ref: str | None = None,
    ) -> EngineeringRun:
        run = EngineeringRun(
            conversation_id=conversation_id,
            spec_id=spec_id,
            project_id=project_id,
            work_specification_id=work_specification_id,
            work_specification_revision=work_specification_revision,
            work_specification_digest=work_specification_digest,
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
            .execution_options(populate_existing=True)
        )
        return self.session.scalar(statement)

    def list_for_project(self, *, project_id: str, limit: int = 10) -> tuple[EngineeringRun, ...]:
        """Return a small deterministic Project-scoped history with attempts eagerly loaded."""

        if not isinstance(project_id, str) or not project_id:
            raise ValueError("project_id is required")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= _MAX_PROJECT_HISTORY:
            raise ValueError(f"engineering run project history limit must be between 1 and {_MAX_PROJECT_HISTORY}")
        rows = self.session.scalars(
            select(EngineeringRun)
            .where(EngineeringRun.project_id == project_id)
            .options(selectinload(EngineeringRun.attempts))
            .order_by(
                EngineeringRun.updated_at.desc(),
                EngineeringRun.created_at.desc(),
                EngineeringRun.id.asc(),
            )
            .limit(limit)
            .execution_options(populate_existing=True)
        ).all()
        return tuple(rows)

    def latest_for_conversation(self, conversation_id: str) -> EngineeringRun | None:
        run_id = self.session.scalar(
            select(EngineeringRun.id)
            .where(EngineeringRun.conversation_id == conversation_id)
            .order_by(EngineeringRun.updated_at.desc(), EngineeringRun.created_at.desc())
        )
        return self.get(run_id) if run_id else None

    def latest_for_binding(self, conversation_id: str, work_specification_id: str) -> EngineeringRun | None:
        run_id = self.session.scalar(
            select(EngineeringRun.id)
            .where(
                EngineeringRun.conversation_id == conversation_id,
                EngineeringRun.work_specification_id == work_specification_id,
            )
            .order_by(EngineeringRun.updated_at.desc(), EngineeringRun.created_at.desc())
        )
        return self.get(run_id) if run_id else None

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
