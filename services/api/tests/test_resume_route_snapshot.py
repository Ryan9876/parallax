from __future__ import annotations

from types import SimpleNamespace

from parallax_api.routes import engineering_runs as routes


class _Payload:
    def model_dump(self) -> dict[str, object]:
        return {"operation_key": "resume-route-snapshot", "expected_revision": 7}


class _AliasedService:
    """Model the same-session ORM identity behavior that escaped P2-V0.23.11."""

    def __init__(self) -> None:
        self.run = SimpleNamespace(state="FAILED")

    def get(self, run_id: str):
        assert run_id == "run-1"
        return self.run

    def resume(self, *, run_id: str, operation_key: str, expected_revision: int):
        assert run_id == "run-1"
        assert operation_key == "resume-route-snapshot"
        assert expected_revision == 7
        # SQLAlchemy may refresh/mutate the exact same identity-mapped object
        # previously returned by get(). The route must therefore have captured
        # the scalar pre-mutation state already.
        self.run.state = "IMPLEMENT"
        return SimpleNamespace(run=self.run, attempt_id="attempt-1", replayed=False)


class _Recovery:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def prepare_human_resume(self, *, run_id: str):
        self.calls.append(run_id)
        return SimpleNamespace(state="RECOVERING")


def test_resume_snapshots_failed_state_before_identity_mapped_run_mutates(monkeypatch):
    service = _AliasedService()
    recovery = _Recovery()

    monkeypatch.setattr(routes, "worker_recovery_service", lambda svc: recovery)
    monkeypatch.setattr(
        routes,
        "result_payload",
        lambda result, svc: {"state": result.run.state, "attempt_id": result.attempt_id},
    )

    response = routes.resume("run-1", _Payload(), service)

    assert response == {"state": "IMPLEMENT", "attempt_id": "attempt-1"}
    assert recovery.calls == ["run-1"]
