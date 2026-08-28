from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from parallax_api.code.agentic_observability import (
    AgenticObservabilityError,
    AgenticObservabilityScopeError,
    AgenticObservabilityService,
)
from parallax_api.models import EngineeringRun


PROJECT = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT = "99999999-9999-4999-8999-999999999999"
RUN = "22222222-2222-4222-8222-222222222222"
SPEC = "33333333-3333-4333-8333-333333333333"
NOW = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)


def _run() -> EngineeringRun:
    run = EngineeringRun(
        id=RUN,
        conversation_id="77777777-7777-4777-8777-777777777777",
        spec_id="P2-V0.20.5",
        project_id=PROJECT,
        work_specification_id=SPEC,
        work_specification_revision=1,
        work_specification_digest="a" * 64,
        state="PLAN",
        resume_stage=None,
        revision=1,
        workspace_ref=None,
        last_failure_code=None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
    )
    run.attempts = []
    return run


class FakeRuns:
    def __init__(self, run: EngineeringRun):
        self.run = run
        self.history_calls: list[tuple[str, int]] = []

    def list_for_project(self, *, project_id: str, limit: int):
        self.history_calls.append((project_id, limit))
        return (self.run,) if project_id == self.run.project_id else ()


class FakeRunService:
    def __init__(self, run: EngineeringRun):
        self.run = run
        self.runs = FakeRuns(run)
        self.owner_subject = None
        self.projects = None

    def get(self, run_id: str) -> EngineeringRun:
        assert run_id == self.run.id
        return self.run

    def acceptance_map_for_run(self, run: EngineeringRun):
        assert run is self.run
        return [{"id": "AC-01", "text": "bounded"}]


class FakeWorkers:
    def get_for_run(self, run_id: str):
        assert run_id == RUN
        return None


def test_service_projects_bounded_project_history_from_same_run_contract() -> None:
    run = _run()
    svc = FakeRunService(run)
    facade = AgenticObservabilityService(svc, FakeWorkers())

    history = facade.project_history(project_id=PROJECT, limit=3)

    assert history.project_id == PROJECT
    assert history.limit == 3
    assert len(history.runs) == 1
    assert history.runs[0].run_id == RUN
    assert svc.runs.history_calls == [(PROJECT, 3)]


def test_service_rejects_cross_project_and_unbounded_history_requests() -> None:
    run = _run()
    facade = AgenticObservabilityService(FakeRunService(run), FakeWorkers())

    with pytest.raises(AgenticObservabilityScopeError, match="scope is unavailable"):
        facade.project_run(project_id=OTHER_PROJECT, run_id=RUN)
    with pytest.raises(AgenticObservabilityError, match="history limit"):
        facade.project_history(project_id=PROJECT, limit=26)
