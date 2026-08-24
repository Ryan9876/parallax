from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.run_events import (
    RunEventAppend,
    RunEventConflict,
    RunEventOutcome,
    RunEventScopeError,
    RunEventSubsystem,
    RunEventType,
    RunEventValidationError,
)
from parallax_api.db import Base, make_engine
from parallax_api.models import EngineeringRun
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.run_events import RunEventRepository


NOW = datetime(2026, 8, 24, 4, 0, tzinfo=timezone.utc)


def session_factory(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'run-events.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def bound_run(session):
    project = ProjectRepository(session).create(
        owner_subject="owner-a",
        slug=f"events-{uuid4().hex[:8]}",
        name="Run Events",
        description=None,
        repository_ref="github:acme/run-events",
    )
    conversation = ConversationRepository(session).create(
        "code",
        spec_id="P2-V0.17.1",
        project_id=project.id,
    )
    run = EngineeringRun(
        conversation_id=conversation.id,
        spec_id="P2-V0.17.1",
        project_id=project.id,
        state="PLAN",
        revision=1,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return project, run


def event_for(project_id: str, run_id: str, key: str, *, summary: str = "Protected PLAN completed."):
    return RunEventAppend(
        project_id=project_id,
        run_id=run_id,
        event_key=key,
        event_type=RunEventType.STAGE_RESULT,
        stage="PLAN",
        outcome=RunEventOutcome.SUCCEEDED,
        subsystem=RunEventSubsystem.RUN,
        evidence_ref="attempt:00000000-0000-4000-8000-000000000001",
        summary=summary,
        metadata={"attempt_number": 1, "program_id": "protected-plan-v1"},
        occurred_at=NOW,
    )


def test_append_read_replay_conflict_and_after_sequence_are_durable(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        project, run = bound_run(session)
        repository = RunEventRepository(session)
        first = repository.append(event_for(project.id, run.id, "plan:one"))
        second = repository.append(
            RunEventAppend(
                project_id=project.id,
                run_id=run.id,
                event_key="plan:two",
                event_type=RunEventType.REVIEW_REQUIRED,
                stage="REVIEW",
                outcome=RunEventOutcome.HUMAN_REQUIRED,
                subsystem=RunEventSubsystem.REVIEW,
                summary="Operator REVIEW is required.",
                metadata={"current_state": "REVIEW", "run_revision": 2},
                occurred_at=NOW,
            )
        )

        assert first.event.sequence == 1 and first.replayed is False
        assert second.event.sequence == 2 and second.replayed is False
        replay = repository.append(event_for(project.id, run.id, "plan:one"))
        assert replay.replayed is True
        assert replay.event.id == first.event.id
        assert repository.latest_sequence(project_id=project.id, run_id=run.id) == 2
        assert [item.event_key for item in repository.list_for_run(
            project_id=project.id,
            run_id=run.id,
            after_sequence=1,
            limit=20,
        )] == ["plan:two"]

        with pytest.raises(RunEventConflict):
            repository.append(event_for(project.id, run.id, "plan:one", summary="Conflicting content."))


def test_process_recreation_continues_after_durable_maximum_without_duplicate_identity(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        project, run = bound_run(session)
        project_id, run_id = project.id, run.id
        first = RunEventRepository(session).append(event_for(project_id, run_id, "event:first"))
        assert first.event.sequence == 1

    with Session() as recreated:
        repository = RunEventRepository(recreated)
        assert repository.latest_sequence(project_id=project_id, run_id=run_id) == 1
        second = repository.append(
            RunEventAppend(
                project_id=project_id,
                run_id=run_id,
                event_key="event:second",
                event_type=RunEventType.WORKER_STATE,
                outcome=RunEventOutcome.RECOVERING,
                subsystem=RunEventSubsystem.WORKER,
                summary="Worker recovery resumed from durable state.",
                metadata={"worker_state": "RECOVERING", "lease_generation": 2},
                occurred_at=NOW,
            )
        )
        assert second.event.sequence == 2
        assert [item.sequence for item in repository.list_for_run(
            project_id=project_id,
            run_id=run_id,
        )] == [1, 2]


def test_wrong_project_historical_unbound_and_invalid_read_scope_fail_closed(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        project, run = bound_run(session)
        repository = RunEventRepository(session)
        wrong_project = str(uuid4())
        with pytest.raises(RunEventScopeError):
            repository.append(event_for(wrong_project, run.id, "wrong:project"))
        with pytest.raises(RunEventScopeError):
            repository.list_for_run(project_id=wrong_project, run_id=run.id)

        historical_conversation = ConversationRepository(session).create(
            "code",
            spec_id="P2-V0.8.0",
        )
        historical = EngineeringRun(
            conversation_id=historical_conversation.id,
            spec_id="P2-V0.8.0",
            project_id=None,
            state="PLAN",
            revision=1,
        )
        session.add(historical)
        session.commit()
        with pytest.raises(RunEventScopeError):
            repository.append(event_for(project.id, historical.id, "historical:denied"))


def test_event_contract_rejects_secrets_raw_fields_nested_payloads_and_invalid_lineage():
    project_id, run_id = str(uuid4()), str(uuid4())

    with pytest.raises(RunEventValidationError, match="credential"):
        RunEventAppend(
            project_id=project_id,
            run_id=run_id,
            event_key="secret:summary",
            event_type=RunEventType.STAGE_RESULT,
            outcome=RunEventOutcome.FAILED,
            subsystem=RunEventSubsystem.EXECUTION,
            summary="api_key=abcdefghijklmno",
            occurred_at=NOW,
        )

    with pytest.raises(RunEventValidationError, match="not allowlisted"):
        RunEventAppend(
            project_id=project_id,
            run_id=run_id,
            event_key="raw:stdout",
            event_type=RunEventType.STAGE_RESULT,
            outcome=RunEventOutcome.INFO,
            subsystem=RunEventSubsystem.EXECUTION,
            metadata={"raw_stdout": "private output"},
            occurred_at=NOW,
        )

    with pytest.raises(RunEventValidationError, match="unsupported value type"):
        RunEventAppend(
            project_id=project_id,
            run_id=run_id,
            event_key="nested:provider",
            event_type=RunEventType.PROVIDER_RESULT,
            outcome=RunEventOutcome.INFO,
            subsystem=RunEventSubsystem.GITHUB,
            metadata={"branch_name": {"provider": "raw"}},
            occurred_at=NOW,
        )

    with pytest.raises(RunEventValidationError, match="source-lineage"):
        RunEventAppend(
            project_id=project_id,
            run_id=run_id,
            event_key="bad:lineage",
            event_type=RunEventType.SOURCE_LINEAGE_ACCEPTED,
            outcome=RunEventOutcome.SUCCEEDED,
            subsystem=RunEventSubsystem.SOURCE_LINEAGE,
            source_lineage_ref="src:not-a-digest",
            occurred_at=NOW,
        )


def test_run_event_migration_is_additive_bounded_rls_protected_and_reversible():
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "20260824_0010_run_events.sql"
    ).read_text()
    normalized = migration.lower()
    assert "create table if not exists engineering_run_events" in normalized
    assert "references projects(id) on delete restrict" in normalized
    assert "references engineering_runs(id) on delete cascade" in normalized
    assert "unique (run_id, sequence)" in normalized
    assert "unique (run_id, event_key)" in normalized
    assert "sequence > 0" in normalized
    assert "char_length(metadata_json) <= 4000" in normalized
    assert "enable row level security" in normalized
    assert "revoke all on table engineering_run_events from anon, authenticated" in normalized
    assert "alter table engineering_runs" not in normalized
    assert "alter table engineering_attempts" not in normalized
    # The table is an isolated additive projection and can be rolled back by
    # dropping it without rewriting any authoritative Wave 3 record.
    assert "update engineering_runs" not in normalized
