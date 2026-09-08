from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import inspect, text

from parallax_api.db import Base, make_engine
from parallax_api.models import (
    AuthorizedUser,
    BehavioralVerificationPlan,
    Conversation,
    EngineeringAttempt,
    EngineeringRun,
    EngineeringRunEvent,
    EngineeringWorkerExecution,
    Message,
    WorkSpecification,
)
from parallax_api.projects.model import Project


EXPECTED_TABLES = {
    AuthorizedUser.__tablename__,
    BehavioralVerificationPlan.__tablename__,
    Conversation.__tablename__,
    EngineeringAttempt.__tablename__,
    EngineeringRun.__tablename__,
    EngineeringRunEvent.__tablename__,
    EngineeringWorkerExecution.__tablename__,
    Message.__tablename__,
    WorkSpecification.__tablename__,
    Project.__tablename__,
}
EXPECTED_INDEXES = {
    "ix_engineering_runs_conversation_updated",
    "ix_engineering_runs_binding_updated",
    "ix_engineering_runs_project_updated",
    "ix_engineering_attempts_run_status_stage",
    "ix_engineering_run_events_run_sequence",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database_url")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    engine = make_engine(args.database_url, environment="test")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing_tables = sorted(EXPECTED_TABLES - tables)
    if missing_tables:
        raise SystemExit(f"missing expected tables: {missing_tables}")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS p0240_schema_sentinel (value INTEGER NOT NULL)"))
        connection.execute(text("DELETE FROM p0240_schema_sentinel"))
        connection.execute(text("INSERT INTO p0240_schema_sentinel(value) VALUES (41)"))

    # A second clean-initialization pass must be additive and preserve existing data.
    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        sentinel = connection.scalar(text("SELECT value FROM p0240_schema_sentinel"))
    if sentinel != 41:
        raise SystemExit("schema initialization altered existing sentinel data")

    inspector = inspect(engine)
    indexes: set[str] = set()
    for table_name in EXPECTED_TABLES:
        for item in inspector.get_indexes(table_name):
            name = item.get("name")
            if isinstance(name, str):
                indexes.add(name)
    missing_indexes = sorted(EXPECTED_INDEXES - indexes)
    if missing_indexes:
        raise SystemExit(f"missing expected indexes: {missing_indexes}")

    result = {
        "dialect": engine.dialect.name,
        "expected_tables": sorted(EXPECTED_TABLES),
        "expected_indexes": sorted(EXPECTED_INDEXES),
        "sentinel_preserved": True,
        "passed": True,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
