from __future__ import annotations

from types import SimpleNamespace

from parallax_api.routes import engineering_runs as routes


class _Payload:
    def model_dump(self) -> dict[str, object]:
        return {"operation_key": "resume-route-snapshot", "expected_revision": 7}


class _AliasedService:
    """Model same-session ORM identity mutation and capture server-only resume mode."""

    def __init__(self, *, resume_stage: str = "IMPLEMENT") -> None:
        self.run = SimpleNamespace(
            state="FAILED",
            resume_stage=resume_stage,
            project_id="project-1",
        )
        self.refresh_plan_values: list[bool] = []

    def get(self, run_id: str):
        assert run_id == "run-1"
        return self.run

    def resume(
        self,
        *,
        run_id: str,
        operation_key: str,
        expected_revision: int,
        refresh_plan: bool = False,
    ):
        assert run_id == "run-1"
        assert operation_key == "resume-route-snapshot"
        assert expected_revision == 7
        self.refresh_plan_values.append(refresh_plan)
        # SQLAlchemy may refresh/mutate this exact object after the pre-read.
        self.run.state = "PLAN" if refresh_plan else self.run.resume_stage
        self.run.resume_stage = None
        return SimpleNamespace(run=self.run, attempt_id="attempt-1", replayed=False)


class _Recovery:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def prepare_human_resume(self, *, run_id: str):
        self.calls.append(run_id)
        return SimpleNamespace(state="RECOVERING")


def _wire(monkeypatch, recovery: _Recovery) -> None:
    monkeypatch.setattr(routes, "worker_recovery_service", lambda svc: recovery)
    monkeypatch.setattr(
        routes,
        "result_payload",
        lambda result, svc: {"state": result.run.state, "attempt_id": result.attempt_id},
    )


def test_failed_agentic_implement_resume_snapshots_state_and_refreshes_plan(monkeypatch):
    service = _AliasedService()
    recovery = _Recovery()
    _wire(monkeypatch, recovery)
    monkeypatch.setenv("PARALLAX_AGENTIC_RUNTIME_ENABLED", "1")

    response = routes.resume("run-1", _Payload(), service)

    assert response == {"state": "PLAN", "attempt_id": "attempt-1"}
    assert service.refresh_plan_values == [True]
    assert recovery.calls == ["run-1"]


def test_failed_implement_resume_without_agentic_runtime_preserves_direct_resume(monkeypatch):
    service = _AliasedService()
    recovery = _Recovery()
    _wire(monkeypatch, recovery)
    monkeypatch.delenv("PARALLAX_AGENTIC_RUNTIME_ENABLED", raising=False)

    response = routes.resume("run-1", _Payload(), service)

    assert response == {"state": "IMPLEMENT", "attempt_id": "attempt-1"}
    assert service.refresh_plan_values == [False]
    assert recovery.calls == ["run-1"]


def test_failed_non_implement_resume_does_not_refresh_plan(monkeypatch):
    service = _AliasedService(resume_stage="TEST")
    recovery = _Recovery()
    _wire(monkeypatch, recovery)
    monkeypatch.setenv("PARALLAX_AGENTIC_RUNTIME_ENABLED", "1")

    response = routes.resume("run-1", _Payload(), service)

    assert response == {"state": "TEST", "attempt_id": "attempt-1"}
    assert service.refresh_plan_values == [False]
    assert recovery.calls == ["run-1"]
