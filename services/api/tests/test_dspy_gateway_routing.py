from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest

import parallax_api.intelligence.dspy_programs as dspy_programs
from parallax_api.intelligence.router import MODEL_ORDER


_ENV_NAMES = (
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
_UNSET = object()


class FakeDspy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def LM(self, model: str, **kwargs: object):  # noqa: N802 - mirrors DSPy API
        self.calls.append((model, kwargs))
        return SimpleNamespace(model=model, kwargs=kwargs)


def _prepare_env(monkeypatch: pytest.MonkeyPatch, env: dict[str, str] | None = None) -> None:
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (env or {}).items():
        monkeypatch.setenv(name, value)


def _build(
    monkeypatch: pytest.MonkeyPatch,
    *,
    model: str = "openai/gpt-5.6-terra",
    env: dict[str, str] | None = None,
    request_credential: object = _UNSET,
) -> tuple[str, dict[str, object]]:
    _prepare_env(monkeypatch, env)
    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)

    if request_credential is _UNSET:
        dspy_programs.build_lm(model)
    else:
        with dspy_programs.request_model_gateway_credential(request_credential):
            dspy_programs.build_lm(model)

    assert len(fake.calls) == 1
    return fake.calls[0]


def test_request_scoped_oidc_uses_explicit_gateway_endpoint_without_model_rewrite(
    monkeypatch: pytest.MonkeyPatch,
):
    transport_model, kwargs = _build(
        monkeypatch,
        env={"VERCEL_ENV": "production"},
        request_credential="request-oidc-secret",
    )

    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs == {
        "api_base": "https://ai-gateway.vercel.sh/v1",
        "api_key": "request-oidc-secret",
    }


def test_process_environment_oidc_is_not_automatic_model_authority(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(
        monkeypatch,
        env={"VERCEL_OIDC_TOKEN": "build-time-secret"},
    )

    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs == {}


def test_production_fails_closed_without_request_oidc_even_if_gateway_env_keys_exist(
    monkeypatch: pytest.MonkeyPatch,
):
    _prepare_env(
        monkeypatch,
        {
            "VERCEL_ENV": "production",
            "AI_GATEWAY_API_KEY": "gateway-secret",
            "VERCEL_AI_GATEWAY_API_KEY": "gateway-alias-secret",
            "VERCEL_OIDC_TOKEN": "build-time-secret",
        },
    )
    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)

    with pytest.raises(
        dspy_programs.ModelTransportConfigurationError,
        match="production model gateway credential is unavailable",
    ):
        dspy_programs.build_lm("openai/gpt-5.6-terra")

    assert fake.calls == []


def test_nonproduction_gateway_key_precedence_is_deterministic(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(
        monkeypatch,
        env={
            "AI_GATEWAY_API_KEY": "primary-secret",
            "VERCEL_AI_GATEWAY_API_KEY": "alias-secret",
        },
    )
    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs == {
        "api_base": "https://ai-gateway.vercel.sh/v1",
        "api_key": "primary-secret",
    }

    _, alias_kwargs = _build(
        monkeypatch,
        env={"VERCEL_AI_GATEWAY_API_KEY": "alias-secret"},
    )
    assert alias_kwargs == {
        "api_base": "https://ai-gateway.vercel.sh/v1",
        "api_key": "alias-secret",
    }


def test_request_credential_wins_over_automatic_gateway_keys(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(
        monkeypatch,
        env={
            "VERCEL_ENV": "production",
            "AI_GATEWAY_API_KEY": "environment-secret",
        },
        request_credential="request-secret",
    )

    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs["api_key"] == "request-secret"
    assert kwargs["api_base"] == "https://ai-gateway.vercel.sh/v1"


def test_explicit_dspy_endpoint_override_prevents_gateway_substitution(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(
        monkeypatch,
        env={
            "VERCEL_ENV": "production",
            "DSPY_API_BASE": "http://127.0.0.1:11434",
            "DSPY_API_KEY": "",
            "AI_GATEWAY_API_KEY": "gateway-secret",
        },
        request_credential="request-secret",
    )

    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs == {"api_base": "http://127.0.0.1:11434", "api_key": ""}


def test_explicit_dspy_key_alone_remains_authoritative(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(
        monkeypatch,
        env={
            "DSPY_API_KEY": "explicit-secret",
            "AI_GATEWAY_API_KEY": "gateway-secret",
        },
        request_credential="request-secret",
    )

    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs == {"api_key": "explicit-secret"}


def test_nonproduction_no_gateway_credential_preserves_existing_provider_behavior(
    monkeypatch: pytest.MonkeyPatch,
):
    transport_model, kwargs = _build(monkeypatch)

    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs == {}


def test_namespace_rewritten_model_is_rejected(monkeypatch: pytest.MonkeyPatch):
    _prepare_env(monkeypatch)
    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)

    with pytest.raises(
        dspy_programs.ModelTransportConfigurationError,
        match="canonical Parallax model identity is required",
    ):
        with dspy_programs.request_model_gateway_credential("request-secret"):
            dspy_programs.build_lm("vercel_ai_gateway/openai/gpt-5.6-sol")

    assert fake.calls == []


def test_non_openai_local_model_is_not_forced_to_gateway(monkeypatch: pytest.MonkeyPatch):
    local_model, local_kwargs = _build(
        monkeypatch,
        model="ollama_chat/llama3.2:1b",
        env={"AI_GATEWAY_API_KEY": "gateway-secret"},
    )
    assert local_model == "ollama_chat/llama3.2:1b"
    assert local_kwargs == {}


def test_request_credential_is_reset_after_context(monkeypatch: pytest.MonkeyPatch):
    _prepare_env(monkeypatch, {"VERCEL_ENV": "production"})
    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)

    with dspy_programs.request_model_gateway_credential("request-secret"):
        dspy_programs.build_lm("openai/gpt-5.6-terra")

    with pytest.raises(dspy_programs.ModelTransportConfigurationError):
        dspy_programs.build_lm("openai/gpt-5.6-terra")

    assert len(fake.calls) == 1


def test_request_credential_propagates_through_asyncio_to_thread(monkeypatch: pytest.MonkeyPatch):
    _prepare_env(monkeypatch, {"VERCEL_ENV": "production"})
    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)

    async def construct_in_worker():
        with dspy_programs.request_model_gateway_credential("thread-request-secret"):
            return await asyncio.to_thread(dspy_programs.build_lm, "openai/gpt-5.6-terra")

    lm = asyncio.run(construct_in_worker())
    assert lm.model == "openai/gpt-5.6-terra"
    assert lm.kwargs == {
        "api_base": "https://ai-gateway.vercel.sh/v1",
        "api_key": "thread-request-secret",
    }


def test_gateway_secret_is_not_logged(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger=dspy_programs.__name__)
    _build(
        monkeypatch,
        env={"VERCEL_ENV": "production"},
        request_credential="never-log-this-secret",
    )

    assert "never-log-this-secret" not in caplog.text
    assert "transport=vercel_ai_gateway" in caplog.text
    assert "model=openai/gpt-5.6-terra" in caplog.text


def test_canonical_model_order_and_identity_remain_unchanged():
    assert MODEL_ORDER == (
        "openai/gpt-5.6-luna",
        "openai/gpt-5.6-terra",
        "openai/gpt-5.6-sol",
    )
    assert all(not model.startswith("vercel_ai_gateway/") for model in MODEL_ORDER)
