from __future__ import annotations

from time import perf_counter, sleep
from uuid import uuid4

from sqlalchemy import event, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.orm import selectinload, sessionmaker

from parallax_api.db import Base, make_engine
from parallax_api.models import (
    EngineeringAttempt,
    EngineeringRun,
    EngineeringRunEvent,
    EngineeringWorkerExecution,
)
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.worker_executions import (
    EngineeringWorkerExecution as RepositoryWorkerExecution,
)


def _run() -> EngineeringRun:
    return EngineeringRun(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        spec_id="P2-V0.24.0",
        project_id=str(uuid4()),
        state="PLAN",
        revision=0,
    )


def test_model_package_preserves_compatibility_and_one_metadata_graph(tmp_path) -> None:
    assert RepositoryWorkerExecution is EngineeringWorkerExecution
    expected = {
        "authorized_users",
        "conversations",
        "messages",
        "work_specifications",
        "behavioral_verification_plans",
        "engineering_runs",
        "engineering_attempts",
        "engineering_run_events",
        "engineering_worker_executions",
    }
    assert expected <= set(Base.metadata.tables)

    engine = make_engine(f"sqlite:///{tmp_path / 'schema.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("create table sentinel_p0240 (value integer not null)"))
        connection.execute(text("insert into sentinel_p0240(value) values (41)"))
    # create_all is additive/idempotent and must not purge an existing database.
    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        assert connection.scalar(text("select value from sentinel_p0240")) == 41

    index_names = {
        index.name
        for table in Base.metadata.tables.values()
        for index in table.indexes
    }
    assert {
        "ix_engineering_runs_conversation_updated",
        "ix_engineering_runs_binding_updated",
        "ix_engineering_runs_project_updated",
        "ix_engineering_attempts_run_status_stage",
        "ix_engineering_run_events_run_sequence",
    } <= index_names


def test_supported_metadata_compiles_for_postgresql() -> None:
    dialect = postgresql.dialect()
    for table in Base.metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=dialect))
        for index in table.indexes:
            assert str(CreateIndex(index).compile(dialect=dialect))


def _baseline_record(session, run: EngineeringRun, index: int) -> None:
    next_number = int(
        session.scalar(
            select(__import__("sqlalchemy").func.max(EngineeringAttempt.attempt_number)).where(
                EngineeringAttempt.run_id == run.id,
                EngineeringAttempt.stage == "PLAN",
            )
        )
        or 0
    ) + 1
    attempt = EngineeringAttempt(
        run_id=run.id,
        stage="PLAN",
        attempt_number=next_number,
        operation_key=f"baseline:{index}",
        status="PASSED",
        evidence_json="{}",
    )
    run.state = "PLAN"
    run.revision += 1
    session.add(attempt)
    session.add(run)
    session.commit()
    session.refresh(attempt)
    session.scalar(
        select(EngineeringRun)
        .where(EngineeringRun.id == run.id)
        .options(selectinload(EngineeringRun.attempts))
        .execution_options(populate_existing=True)
    )


def _measure(*, candidate: bool, iterations: int = 24) -> tuple[float, int]:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    statements = 0

    def latency_probe(_conn, _cursor, _statement, _parameters, _context, _many):
        nonlocal statements
        statements += 1
        # Controlled 0.75 ms database round-trip cost approximates the remote
        # serverless persistence regime where the eliminated reads matter.
        sleep(0.00075)

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        run = _run()
        session.add(run)
        session.commit()
        if candidate:
            # Load attempts once, matching runtime repository behavior.
            run = EngineeringRunRepository(session).get(run.id)
            assert run is not None

        event.listen(engine, "before_cursor_execute", latency_probe)
        started = perf_counter()
        try:
            if candidate:
                repository = EngineeringRunRepository(session)
                for index in range(iterations):
                    repository.record(
                        run,
                        stage="PLAN",
                        operation_key=f"candidate:{index}",
                        status="PASSED",
                        next_state="PLAN",
                    )
            else:
                for index in range(iterations):
                    _baseline_record(session, run, index)
        finally:
            elapsed = perf_counter() - started
            event.remove(engine, "before_cursor_execute", latency_probe)
    return elapsed, statements


def test_transition_round_trip_latency_improves_at_least_40_percent() -> None:
    baseline_seconds, baseline_statements = _measure(candidate=False)
    candidate_seconds, candidate_statements = _measure(candidate=True)

    assert candidate_statements <= baseline_statements * 0.60
    assert candidate_seconds <= baseline_seconds * 0.60, (
        f"P2-V0.24.0 transition gate failed: baseline={baseline_seconds:.6f}s/"
        f"{baseline_statements} statements candidate={candidate_seconds:.6f}s/"
        f"{candidate_statements} statements"
    )


def test_run_event_index_matches_replay_cursor_access_path() -> None:
    names = {index.name for index in EngineeringRunEvent.__table__.indexes}
    assert "ix_engineering_run_events_run_sequence" in names
