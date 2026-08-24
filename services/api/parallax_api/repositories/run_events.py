from __future__ import annotations

from datetime import datetime, timezone
import json

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..code.run_events import (
    RunEvent,
    RunEventAppend,
    RunEventAppendResult,
    RunEventConflict,
    RunEventPersistenceError,
    RunEventScopeError,
    RunEventSink,
)
from ..models import EngineeringRun, EngineeringRunEvent


_MAX_APPEND_RETRIES = 3
_MAX_READ_LIMIT = 200


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class RunEventRepository:
    """Append-only Project/run-scoped event projection.

    PostgreSQL appends serialize on the authoritative EngineeringRun row before
    allocating the next per-run sequence. Database uniqueness remains the final
    authority for both deterministic event identity and sequence allocation.
    """

    def __init__(self, session: Session):
        self.session = session

    def _run_for_append(self, event: RunEventAppend) -> EngineeringRun:
        run = self.session.scalar(
            select(EngineeringRun)
            .where(EngineeringRun.id == event.run_id)
            .with_for_update()
        )
        if run is None:
            raise RunEventScopeError("Engineering Run for event does not exist")
        if not run.project_id:
            raise RunEventScopeError("historical unbound Engineering Runs cannot produce Wave 4 telemetry")
        if run.project_id != event.project_id:
            raise RunEventScopeError("run-event Project identity does not match its Engineering Run")
        return run

    def _run_for_read(self, *, project_id: str, run_id: str) -> EngineeringRun:
        run = self.session.get(EngineeringRun, run_id)
        if run is None or run.project_id != project_id:
            raise RunEventScopeError("run-event scope is unavailable")
        return run

    def _existing(self, run_id: str, event_key: str) -> EngineeringRunEvent | None:
        return self.session.scalar(
            select(EngineeringRunEvent).where(
                EngineeringRunEvent.run_id == run_id,
                EngineeringRunEvent.event_key == event_key,
            )
        )

    @staticmethod
    def _decode(row: EngineeringRunEvent) -> RunEvent:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except json.JSONDecodeError as exc:
            raise RunEventPersistenceError("stored run-event metadata is invalid JSON") from exc
        if not isinstance(metadata, dict):
            raise RunEventPersistenceError("stored run-event metadata must be an object")
        append = RunEventAppend(
            project_id=row.project_id,
            run_id=row.run_id,
            event_key=row.event_key,
            event_type=row.event_type,
            stage=row.stage,
            outcome=row.outcome,
            subsystem=row.subsystem,
            attempt_id=row.attempt_id,
            worker_execution_id=row.worker_execution_id,
            source_lineage_ref=row.source_lineage_ref,
            parent_source_lineage_ref=row.parent_source_lineage_ref,
            operation_ref=row.operation_ref,
            artifact_ref=row.artifact_ref,
            evidence_ref=row.evidence_ref,
            failure_code=row.failure_code,
            summary=row.summary,
            metadata=metadata,
            occurred_at=_utc(row.occurred_at),
        )
        return RunEvent(
            id=row.id,
            sequence=int(row.sequence),
            created_at=_utc(row.created_at),
            append=append,
        )

    @classmethod
    def _resolve_existing(cls, row: EngineeringRunEvent, event: RunEventAppend) -> RunEventAppendResult:
        decoded = cls._decode(row)
        if decoded.append.canonical_payload() != event.canonical_payload():
            raise RunEventConflict("run-event key already exists with different protected content")
        return RunEventAppendResult(event=decoded, replayed=True)

    def append(self, event: RunEventAppend) -> RunEventAppendResult:
        if not isinstance(event, RunEventAppend):
            raise TypeError("event must be RunEventAppend")

        for attempt in range(_MAX_APPEND_RETRIES):
            try:
                self._run_for_append(event)
                existing = self._existing(event.run_id, event.event_key)
                if existing is not None:
                    return self._resolve_existing(existing, event)

                sequence = int(
                    self.session.scalar(
                        select(func.max(EngineeringRunEvent.sequence)).where(
                            EngineeringRunEvent.run_id == event.run_id
                        )
                    )
                    or 0
                ) + 1
                row = EngineeringRunEvent(
                    project_id=event.project_id,
                    run_id=event.run_id,
                    sequence=sequence,
                    event_key=event.event_key,
                    event_type=event.event_type.value,
                    stage=event.stage,
                    outcome=event.outcome.value,
                    subsystem=event.subsystem.value,
                    attempt_id=event.attempt_id,
                    worker_execution_id=event.worker_execution_id,
                    source_lineage_ref=event.source_lineage_ref,
                    parent_source_lineage_ref=event.parent_source_lineage_ref,
                    operation_ref=event.operation_ref,
                    artifact_ref=event.artifact_ref,
                    evidence_ref=event.evidence_ref,
                    failure_code=event.failure_code,
                    summary=event.summary,
                    metadata_json=json.dumps(
                        dict(event.metadata),
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                    ),
                    occurred_at=event.occurred_at,
                )
                self.session.add(row)
                self.session.commit()
                self.session.refresh(row)
                return RunEventAppendResult(event=self._decode(row), replayed=False)
            except RunEventConflict:
                self.session.rollback()
                raise
            except RunEventScopeError:
                self.session.rollback()
                raise
            except IntegrityError as exc:
                self.session.rollback()
                existing = self._existing(event.run_id, event.event_key)
                if existing is not None:
                    return self._resolve_existing(existing, event)
                if attempt + 1 >= _MAX_APPEND_RETRIES:
                    raise RunEventPersistenceError(
                        "run-event sequence allocation conflicted after bounded retries"
                    ) from exc
            except Exception as exc:
                self.session.rollback()
                if isinstance(exc, RunEventPersistenceError):
                    raise
                raise RunEventPersistenceError("durable run-event append failed") from exc

        raise RunEventPersistenceError("durable run-event append exhausted bounded retries")

    def list_for_run(
        self,
        *,
        project_id: str,
        run_id: str,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> tuple[RunEvent, ...]:
        if not isinstance(after_sequence, int) or after_sequence < 0:
            raise ValueError("after_sequence must be a nonnegative integer")
        if not isinstance(limit, int) or not 1 <= limit <= _MAX_READ_LIMIT:
            raise ValueError(f"run-event read limit must be between 1 and {_MAX_READ_LIMIT}")
        self._run_for_read(project_id=project_id, run_id=run_id)
        rows = self.session.scalars(
            select(EngineeringRunEvent)
            .where(
                EngineeringRunEvent.project_id == project_id,
                EngineeringRunEvent.run_id == run_id,
                EngineeringRunEvent.sequence > after_sequence,
            )
            .order_by(EngineeringRunEvent.sequence.asc(), EngineeringRunEvent.id.asc())
            .limit(limit)
        ).all()
        return tuple(self._decode(row) for row in rows)

    def latest_sequence(self, *, project_id: str, run_id: str) -> int:
        self._run_for_read(project_id=project_id, run_id=run_id)
        value = self.session.scalar(
            select(func.max(EngineeringRunEvent.sequence)).where(
                EngineeringRunEvent.project_id == project_id,
                EngineeringRunEvent.run_id == run_id,
            )
        )
        return int(value or 0)


class PersistentRunEventSink(RunEventSink):
    def __init__(self, repository: RunEventRepository):
        self.repository = repository

    def emit(self, event: RunEventAppend) -> RunEventAppendResult:
        return self.repository.append(event)


__all__ = ["PersistentRunEventSink", "RunEventRepository"]
