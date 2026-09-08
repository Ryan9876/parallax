from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter, sleep
from uuid import uuid4

from sqlalchemy import event, func, select
from sqlalchemy.orm import selectinload, sessionmaker

from parallax_api.db import Base, make_engine
from parallax_api.models import EngineeringAttempt, EngineeringRun
from parallax_api.repositories.engineering_runs import EngineeringRunRepository


BASELINE_COMMIT = "7b503876d3e2d9d42261235ff466f89432f37d5f"
SPEC_ID = "P2-V0.24.0"


def _run() -> EngineeringRun:
    return EngineeringRun(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        spec_id=SPEC_ID,
        project_id=str(uuid4()),
        state="PLAN",
        revision=0,
    )


def _baseline_record(session, run: EngineeringRun, index: int) -> None:
    """Reproduce the exact P2-V0.23.50 EngineeringRunRepository.record hot path."""

    next_number = int(
        session.scalar(
            select(func.max(EngineeringAttempt.attempt_number)).where(
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


def _measure_once(*, candidate: bool, iterations: int, round_trip_delay_seconds: float) -> tuple[float, int]:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    statements = 0

    def latency_probe(_conn, _cursor, _statement, _parameters, _context, _many):
        nonlocal statements
        statements += 1
        if round_trip_delay_seconds:
            sleep(round_trip_delay_seconds)

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        run = _run()
        session.add(run)
        session.commit()
        if candidate:
            loaded = EngineeringRunRepository(session).get(run.id)
            if loaded is None:
                raise RuntimeError("candidate benchmark run could not be loaded")
            run = loaded

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=32)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--round-trip-ms", type=float, default=1.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.iterations < 8 or args.rounds < 3 or args.round_trip_ms < 0:
        raise SystemExit("benchmark bounds are invalid")

    baseline_times: list[float] = []
    candidate_times: list[float] = []
    baseline_counts: list[int] = []
    candidate_counts: list[int] = []
    delay = args.round_trip_ms / 1000.0

    for _ in range(args.rounds):
        elapsed, count = _measure_once(
            candidate=False,
            iterations=args.iterations,
            round_trip_delay_seconds=delay,
        )
        baseline_times.append(elapsed)
        baseline_counts.append(count)

        elapsed, count = _measure_once(
            candidate=True,
            iterations=args.iterations,
            round_trip_delay_seconds=delay,
        )
        candidate_times.append(elapsed)
        candidate_counts.append(count)

    baseline_median = median(baseline_times)
    candidate_median = median(candidate_times)
    baseline_statements = median(baseline_counts)
    candidate_statements = median(candidate_counts)
    latency_improvement = 1.0 - (candidate_median / baseline_median)
    statement_improvement = 1.0 - (candidate_statements / baseline_statements)

    result = {
        "spec_id": SPEC_ID,
        "baseline_commit": BASELINE_COMMIT,
        "candidate_commit": os.getenv("GITHUB_SHA") or "local",
        "iterations_per_round": args.iterations,
        "rounds": args.rounds,
        "controlled_round_trip_ms": args.round_trip_ms,
        "baseline_median_seconds": round(baseline_median, 6),
        "candidate_median_seconds": round(candidate_median, 6),
        "latency_improvement_percent": round(latency_improvement * 100, 2),
        "baseline_statement_count": int(baseline_statements),
        "candidate_statement_count": int(candidate_statements),
        "statement_reduction_percent": round(statement_improvement * 100, 2),
        "required_improvement_percent": 40.0,
        "passed": latency_improvement >= 0.40 and statement_improvement >= 0.40,
        "method": (
            "Exact P2-V0.23.50 record() read/write/read sequence versus P2-V0.24.0 record(); "
            "same SQLite ORM workload with a fixed per-statement round-trip penalty to model remote persistence latency."
        ),
    }

    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
