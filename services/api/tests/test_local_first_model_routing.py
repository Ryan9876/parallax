from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest

import parallax_api.intelligence.dspy_programs as dspy_programs
from parallax_api.intelligence.model_routes import (
    HOSTED_MODEL_ORDER,
    ModelRouteConfigurationError,
    effective_model_order,
)
from parallax_api.intelligence.router import MODEL_ORDER, ModelRouter


_LOCAL_ENV_NAMES = (
    "PARALLAX_LOCAL_MODEL_ENABLED",
    "PARALLAX_LOCAL_MODEL",
    "PARALLAX_LOCAL_MODEL_PROVIDER",
    "PARALLAX_LOCAL_MODEL_API_BASE",
    "PARALLAX_LOCAL_MODEL_API_KEY_ENV",
    "LOCAL_MODEL_SECRET",
)
_TRANSPORT_ENV_NAMES = (
    "DSPY_API_BASE",
    "DSPY_API_KEY",
    "DSPY_MODEL_TYPE",
    "DSPY_LOCAL_DEVELOPMENT",
    "AI_GATEWAY_API_KEY",
    "VERCEL_AI_GATEWAY_API_KEY",
    "VERCEL_OIDC_TOKEN",
    "OPENAI_API_KEY",
    "VERCEL_ENV",
)


class FakeDspy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def LM(self, model: str, **kwargs: object):  # noqa: N802 - mirrors DSPy API
        self.calls.append((model, kwargs))
        return SimpleNamespace(model=model, kwargs=kwargs)


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (*_LOCAL_ENV_NAMES, *_TRANSPORT_ENV_NAMES):
        monkeypatch.delenv(name, raising=False)


def _enable_local(
    monkeypatch: pytest.MonkeyPatch,
    *,
    model: str = "ollama_chat/qwen3-coder:30b",
    provider: str = "ollama",
    api_base: str = "http://127.0.0.1:11434",
    api_key_env: str | None = None,
) -> None:
    _clean_env(monkeypatch)
    monkeypatch.setenv("PARALLAX_LOCAL_MODEL_ENABLED", "true")
    monkeypatch.setenv("PARALLAX_LOCAL_MODEL", model)
    monkeypatch.setenv("PARALLAX_LOCAL_MODEL_PROVIDER", provider)
    monkeypatch.setenv("PARALLAX_LOCAL_MODEL_API_BASE", api_base)
    if api_key_env is not None:
        monkeypatch.setenv("PARALLAX_LOCAL_MODEL_API_KEY_ENV", api_key_env)


def test_default_effective_order_is_exact_hosted_chain(monkeypatch: pytest.MonkeyPatch):
    _clean_env(monkeypatch)
    assert HOSTED_MODEL_ORDER == MODEL_ORDER
    assert effective_model_order() == MODEL_ORDER
    assert ModelRouter[str]().models == MODEL_ORDER


def test_local_configuration_prepends_one_admitted_model(monkeypatch: pytest.MonkeyPatch):
    _enable_local(monkeypatch)
    assert effective_model_order() == ("ollama_chat/qwen3-coder:30b", *MODEL_ORDER)


def test_explicit_dspy_override_owns_whole_route_and_disables_local_first(
    monkeypatch: pytest.MonkeyPatch,
):
    _enable_local(monkeypatch)
    monkeypatch.setenv("DSPY_API_BASE", "http://127.0.0.1:9999")
    monkeypatch.setenv("DSPY_API_KEY", "")
    assert effective_model_order() == MODEL_ORDER


def test_local_success_stops_before_hosted_models(monkeypatch: pytest.MonkeyPatch):
    _enable_local(monkeypatch)
    seen: list[str] = []

    async def attempt(model: str) -> str:
        seen.append(model)
        return "valid local result"

    result = asyncio.run(ModelRouter[str]().route(attempt, lambda value: value.startswith("valid")))
    assert seen == ["ollama_chat/qwen3-coder:30b"]
    assert result.model == "ollama_chat/qwen3-coder:30b"
    assert result.attempts[0].provider_kind == "ollama"
    assert result.attempts[0].status == "ok"


def test_local_provider_failure_falls_back_to_luna(monkeypatch: pytest.MonkeyPatch):
    _enable_local(monkeypatch)
    seen: list[str] = []

    async def attempt(model: str) -> str:
        seen.append(model)
        if model.startswith("ollama_chat/"):
            raise RuntimeError("raw endpoint detail must not cross the router boundary")
        return "valid hosted result"

    result = asyncio.run(ModelRouter[str]().route(attempt, lambda value: value.startswith("valid")))
    assert seen == ["ollama_chat/qwen3-coder:30b", MODEL_ORDER[0]]
    assert result.model == MODEL_ORDER[0]
    assert result.attempts[0].status == "provider_failed"
    assert result.attempts[0].error == "RuntimeError"
    assert result.attempts[0].provider_kind == "ollama"


def test_local_validation_failure_falls_back_without_weakening_validator(
    monkeypatch: pytest.MonkeyPatch,
):
    _enable_local(monkeypatch)
    seen: list[str] = []

    async def attempt(model: str) -> str:
        seen.append(model)
        return "invalid local result" if model.startswith("ollama_chat/") else "valid hosted result"

    result = asyncio.run(ModelRouter[str]().route(attempt, lambda value: value.startswith("valid")))
    assert seen == ["ollama_chat/qwen3-coder:30b", MODEL_ORDER[0]]
    assert [record.status for record in result.attempts] == ["validation_failed", "ok"]


def test_remote_plain_http_endpoint_fails_closed(monkeypatch: pytest.MonkeyPatch):
    _enable_local(monkeypatch, api_base="http://model.internal.example/v1")
    with pytest.raises(ModelRouteConfigurationError, match="must use HTTPS"):
        effective_model_order()


def test_vercel_production_rejects_loopback_endpoint(monkeypatch: pytest.MonkeyPatch):
    _enable_local(monkeypatch)
    monkeypatch.setenv("VERCEL_ENV", "production")
    with pytest.raises(ModelRouteConfigurationError, match="cannot use a loopback"):
        effective_model_order()


def test_canonical_hosted_identity_cannot_be_rebound_as_local(monkeypatch: pytest.MonkeyPatch):
    _enable_local(monkeypatch, model=MODEL_ORDER[0])
    with pytest.raises(ModelRouteConfigurationError, match="collides"):
        effective_model_order()


def test_reserved_hosted_credential_slot_cannot_be_reused(monkeypatch: pytest.MonkeyPatch):
    _enable_local(monkeypatch, api_key_env="AI_GATEWAY_API_KEY")
    with pytest.raises(ModelRouteConfigurationError, match="reserved credential"):
        effective_model_order()


def test_local_transport_is_isolated_from_hosted_gateway(monkeypatch: pytest.MonkeyPatch):
    _enable_local(
        monkeypatch,
        model="openai/local-coder",
        provider="openai_compatible",
        api_base="https://local-model.internal.example/v1",
    )
    monkeypatch.setenv("VERCEL_ENV", "production")
    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)

    with dspy_programs.request_model_gateway_credential("request-oidc-secret"):
        local_lm = dspy_programs.build_lm("openai/local-coder")
        hosted_lm = dspy_programs.build_lm(MODEL_ORDER[0])

    assert local_lm.kwargs == {"api_base": "https://local-model.internal.example/v1"}
    assert hosted_lm.kwargs == {
        "api_base": "https://ai-gateway.vercel.sh/v1",
        "api_key": "request-oidc-secret",
    }


def test_local_secret_slot_is_resolved_but_never_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    _enable_local(
        monkeypatch,
        api_base="https://local-model.internal.example/v1",
        api_key_env="LOCAL_MODEL_SECRET",
    )
    monkeypatch.setenv("LOCAL_MODEL_SECRET", "never-log-this-local-secret")
    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)
    caplog.set_level(logging.INFO, logger=dspy_programs.__name__)

    lm = dspy_programs.build_lm("ollama_chat/qwen3-coder:30b")

    assert lm.kwargs == {
        "api_base": "https://local-model.internal.example/v1",
        "api_key": "never-log-this-local-secret",
    }
    assert "never-log-this-local-secret" not in caplog.text
    assert "transport=ollama" in caplog.text
    assert "model=ollama_chat/qwen3-coder:30b" in caplog.text


def test_missing_configured_local_secret_fails_sanitized(monkeypatch: pytest.MonkeyPatch):
    _enable_local(
        monkeypatch,
        api_base="https://local-model.internal.example/v1",
        api_key_env="LOCAL_MODEL_SECRET",
    )
    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)

    with pytest.raises(
        dspy_programs.ModelTransportConfigurationError,
        match="local model credential is unavailable",
    ):
        dspy_programs.build_lm("ollama_chat/qwen3-coder:30b")
    assert fake.calls == []
