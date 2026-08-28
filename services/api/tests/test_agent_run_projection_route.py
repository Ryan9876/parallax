from __future__ import annotations

from types import SimpleNamespace

from parallax_api.routes.agent_run_projection import AgentRunProjectionRead, get_agent_run_projection
from parallax_api.models import EngineeringRun


PROJECT = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"
SPEC = "33333333-3333-4333-8333-333333333333"


class FakeProjectionService:
    def __init__(self, run: EngineeringRun):
        self.run = run
        self.runs = SimpleNamespace(session=None)

    def get(self, run_id: str) -> EngineeringRun:
        assert run_id == self.run.id
        return self.run

    def acceptance_map_for_run(self, run: EngineeringRun) -> list[dict[str, str]]:
        assert run is self.run
        return [
            {"id": "AC-01", "text": "first"},
            {"id": "AC-02", "text": "second"},
        ]


def _run() -> EngineeringRun:
    run = EngineeringRun(
        id=RUN,
        conversation_id="77777777-7777-4777-8777-777777777777",
        spec_id="P2-V0.20.2",
        project_id=PROJECT,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest="a" * 64,
        state="REVIEW",
        resume_stage=None,
        revision=6,
        workspace_ref=None,
        last_failure_code=None,
    )
    run.attempts = []
    return run


def test_projection_route_exposes_typed_read_only_contract_without_event_plane(monkeypatch) -> None:
    monkeypatch.delenv("PARALLAX_RUN_EVENTS_ENABLED", raising=False)
    payload = get_agent_run_projection(RUN, svc=FakeProjectionService(_run()))
    response = AgentRunProjectionRead.model_validate(payload)

    assert response.identity.project_id == PROJECT
    assert response.identity.run_id == RUN
    assert response.identity.acceptance_ids == ["AC-01", "AC-02"]
    assert response.current_state == "REVIEW"
    assert response.run_revision == 6
    assert response.advertised_controls == []
    assert response.transitions_engineering_run is False
    assert response.accepts_source_lineage is False
    assert response.performs_production_deployment is False
