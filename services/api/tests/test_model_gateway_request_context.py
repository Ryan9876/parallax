from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import parallax_api.intelligence.dspy_programs as dspy_programs
from parallax_api.main import create_app


_ENV_NAMES = (
    "DSPY_API_BASE",
    "DSPY_API_KEY",
    "AI_GATEWAY_API_KEY",
    "VERCEL_AI_GATEWAY_API_KEY",
    "VERCEL_OIDC_TOKEN",
    "VERCEL_ENV",
)


class FakeDspy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def LM(self, model: str, **kwargs: object):  # noqa: N802 - mirrors DSPy API
        self.calls.append((model, kwargs))
        return SimpleNamespace(model=model, kwargs=kwargs)


def _production(monkeypatch: pytest.MonkeyPatch) -> FakeDspy:
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", "build-time-oidc-must-not-be-used")
    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)
    return fake


def test_app_binds_validated_request_oidc_to_model_construction_and_resets_between_requests(
    monkeypatch: pytest.MonkeyPatch,
):
    fake = _production(monkeypatch)
    app = create_app(create_schema=False)

    @app.get("/__model-transport-probe")
    def model_transport_probe():
        try:
            lm = dspy_programs.build_lm("openai/gpt-5.6-terra")
        except dspy_programs.ModelTransportConfigurationError:
            return {"status": "blocked"}
        return {
            "status": "ok",
            "model": lm.model,
            "api_base": lm.kwargs.get("api_base"),
        }

    client = TestClient(app)
    bound = client.get(
        "/__model-transport-probe",
        headers={"x-vercel-oidc-token": "request-scoped-oidc-secret"},
    )
    assert bound.status_code == 200
    assert bound.json() == {
        "status": "ok",
        "model": "openai/gpt-5.6-terra",
        "api_base": "https://ai-gateway.vercel.sh/v1",
    }
    assert fake.calls[-1][1]["api_key"] == "request-scoped-oidc-secret"

    # The request credential must not survive into a later request. The process-
    # environment VERCEL_OIDC_TOKEN is deliberately not accepted as fallback.
    unbound = client.get("/__model-transport-probe")
    assert unbound.status_code == 200
    assert unbound.json() == {"status": "blocked"}
    assert len(fake.calls) == 1


def test_malformed_request_oidc_fails_closed_only_when_model_transport_is_needed(
    monkeypatch: pytest.MonkeyPatch,
):
    fake = _production(monkeypatch)
    app = create_app(create_schema=False)

    @app.get("/__model-transport-probe")
    def model_transport_probe():
        try:
            dspy_programs.build_lm("openai/gpt-5.6-terra")
        except dspy_programs.ModelTransportConfigurationError:
            return {"status": "blocked"}
        return {"status": "ok"}

    client = TestClient(app)
    malformed = client.get(
        "/__model-transport-probe",
        headers={"x-vercel-oidc-token": "short"},
    )
    assert malformed.status_code == 200
    assert malformed.json() == {"status": "blocked"}
    assert fake.calls == []

    # Non-model paths are not made dependent on model-provider identity.
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["status"] == "online"
