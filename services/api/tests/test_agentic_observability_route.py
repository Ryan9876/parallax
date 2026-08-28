from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from parallax_api.code.agentic_observability import (
    AgenticObservabilityScopeError,
    ProjectObservabilityHistory,
    build_agentic_run_observability,
)
from parallax_api.models import EngineeringRun
from parallax_api.routes import agentic_observability as observability_routes
from parallax_api.routes.agentic_observability import (
    AgenticRunObservabilityRead,
    ProjectObservabilityHistoryRead,
    get_agentic_run_observability,
    get_project_agentic_observability,
)


PROJECT = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"
SPEC = "33333333-3333-4333-8333-333333333333"
NOW = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)


def _run(*, project_id: str | None = PROJECT) -> EngineeringRun:
    run = EngineeringRun(
        id=RUN,
        conversation_id="77777777-7777-4777-8777-777777777777",
        spec_id="P2-V0.20.5",
        project_id=project_id,
        work_specification_id=SPEC,
        work_specification_revision=1,
        work_specification_digest="a" * 64,
        state="REVIEW",
        resume_stage=None,
        revision=5,
        workspace_ref=None,
        last_failure_code=None,
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=30),
        completed_at=None,
    )
    run.attempts = []
    return run


class FakeRunService:
    def __init__(self, run: EngineeringRun):
        self.run = run
        self.runs = SimpleNamespace(session=None)

    def get(self, run_id: str) -> EngineeringRun:
        assert run_id == self.run.id
        return self.run


class FakeFacade:
    def __init__(self, run: EngineeringRun):
        self.run = run
        self.project_calls: list[tuple[str, int]] = []

    def project_run(self, *, project_id: str, run_id: str):
        if self.run.project_id != project_id or self.run.id != run_id:
            raise AgenticObservabilityScopeError("agentic observability scope is unavailable")
        return build_agentic_run_observability(
            run=self.run,
            acceptance_ids=("AC-01",),
            event_plane_available=False,
        )

    def project_history(self, *, project_id: str, limit: int = 10):
        self.project_calls.append((project_id, limit))
        if self.run.project_id != project_id:
            raise AgenticObservabilityScopeError("agentic observability scope is unavailable")
        projection = self.project_run(project_id=project_id, run_id=self.run.id)
        return ProjectObservabilityHistory(project_id=project_id, limit=limit, runs=(projection,))


def test_run_route_exposes_fixed_privacy_safe_query_time_contract(monkeypatch) -> None:
    run = _run()
    svc = FakeRunService(run)
    facade = FakeFacade(run)
    monkeypatch.setattr(observability_routes, "_facade", lambda value: facade)

    payload = get_agentic_run_observability(RUN, svc=svc)
    response = AgenticRunObservabilityRead.model_validate(payload)

    assert response.observability_version == 1
    assert response.project_id == PROJECT
    assert response.run_id == RUN
    assert response.retention.mode == "QUERY_TIME"
    assert response.retention.persisted_derived_rows is False
    assert response.retention.cleanup_mutation_available is False
    assert response.retention.canonical_deletion_authority is False
    assert response.performs_production_deployment is False
    assert response.completes_review is False
    by_metric = {item.metric: item for item in response.metrics}
    assert by_metric["provider.cost_usd"].state == "UNKNOWN"
    assert by_metric["provider.cost_usd"].value is None


def test_project_history_route_enforces_server_bound_and_project_scope(monkeypatch) -> None:
    run = _run()
    svc = FakeRunService(run)
    facade = FakeFacade(run)
    monkeypatch.setattr(observability_routes, "_facade", lambda value: facade)

    payload = get_project_agentic_observability(PROJECT, limit=5, svc=svc)
    response = ProjectObservabilityHistoryRead.model_validate(payload)

    assert response.project_id == PROJECT
    assert response.limit == 5
    assert response.run_count == 1
    assert response.cross_project_aggregate is False
    assert response.contains_private_project_payload is False
    assert facade.project_calls == [(PROJECT, 5)]


def test_route_hides_unbound_or_cross_project_scope(monkeypatch) -> None:
    svc = FakeRunService(_run(project_id=None))
    with pytest.raises(HTTPException) as exc_info:
        get_agentic_run_observability(RUN, svc=svc)
    assert exc_info.value.status_code == 404

    run = _run()
    svc = FakeRunService(run)
    facade = FakeFacade(run)
    monkeypatch.setattr(observability_routes, "_facade", lambda value: facade)
    with pytest.raises(HTTPException) as cross_scope:
        get_project_agentic_observability(
            "99999999-9999-4999-8999-999999999999",
            limit=5,
            svc=svc,
        )
    assert cross_scope.value.status_code == 404
    assert cross_scope.value.detail == "agentic observability scope is unavailable"
