from __future__ import annotations

from types import SimpleNamespace

from parallax_api.code.agent_run_projection import build_agent_run_projection
from parallax_api.models import EngineeringRun
from parallax_api.routes import agent_run_projection as projection_routes
from parallax_api.routes.agent_run_projection import (
    AgentRunProjectionControl,
    AgentRunProjectionRead,
    control_agent_run_projection,
    get_agent_run_projection,
)


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


class FakeFacade:
    def __init__(self, svc: FakeProjectionService):
        self.svc = svc
        self.control_requests = []

    def project(self, *, project_id: str, run_id: str):
        run = self.svc.get(run_id)
        assert project_id == run.project_id
        return build_agent_run_projection(
            run=run,
            acceptance_ids=("AC-01", "AC-02"),
        )

    def control(self, projection, request):
        self.control_requests.append((projection, request))
        return SimpleNamespace(run=self.svc.run, attempt_id="00000000-0000-4000-8000-000000000001", replayed=False)


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


def test_projection_route_exposes_typed_v2_read_contract(monkeypatch) -> None:
    svc = FakeProjectionService(_run())
    facade = FakeFacade(svc)
    monkeypatch.setattr(projection_routes, "_projection_service", lambda value: facade)

    payload = get_agent_run_projection(RUN, svc=svc)
    response = AgentRunProjectionRead.model_validate(payload)

    assert response.projection_version == 2
    assert response.identity.project_id == PROJECT
    assert response.identity.run_id == RUN
    assert response.identity.acceptance_ids == ["AC-01", "AC-02"]
    assert response.current_state == "REVIEW"
    assert response.run_revision == 6
    assert [item.kind for item in response.advertised_controls] == ["pause", "cancel"]
    assert response.deterministic_disposition == "PENDING"
    assert response.creates_lifecycle_authority is False
    assert response.accepts_source_lineage is False
    assert response.performs_production_deployment is False


def test_projection_control_route_binds_path_run_project_revision_state_and_request_identity(monkeypatch) -> None:
    svc = FakeProjectionService(_run())
    facade = FakeFacade(svc)
    monkeypatch.setattr(projection_routes, "_projection_service", lambda value: facade)

    response = control_agent_run_projection(
        RUN,
        AgentRunProjectionControl(
            request_id="operator-pause-1",
            project_id=PROJECT,
            expected_revision=6,
            expected_state="REVIEW",
            action="pause",
        ),
        svc=svc,
    )

    assert response["run"]["id"] == RUN
    assert response["run"]["project_id"] == PROJECT
    assert response["attempt_id"] == "00000000-0000-4000-8000-000000000001"
    assert response["replayed"] is False
    _, request = facade.control_requests[-1]
    assert request.request_id == "operator-pause-1"
    assert request.project_id == PROJECT
    assert request.run_id == RUN
    assert request.expected_revision == 6
    assert request.expected_state == "REVIEW"
    assert request.action == "pause"
    assert request.operation_key == "agent-projection:pause:operator-pause-1"


def test_projection_control_body_forbids_caller_invented_fields() -> None:
    try:
        AgentRunProjectionControl.model_validate(
            {
                "request_id": "operator-pause-1",
                "project_id": PROJECT,
                "expected_revision": 6,
                "expected_state": "REVIEW",
                "action": "pause",
                "source_lineage_ref": "src:" + "b" * 64,
            }
        )
    except Exception as exc:
        assert "extra" in str(exc).lower()
    else:  # pragma: no cover
        raise AssertionError("control schema accepted caller-supplied source authority")
