from __future__ import annotations

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
)


class FakeDspy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def LM(self, model: str, **kwargs: object):  # noqa: N802 - mirrors DSPy API
        self.calls.append((model, kwargs))
        return SimpleNamespace(model=model, kwargs=kwargs)


def _build(
    monkeypatch: pytest.MonkeyPatch,
    *,
    model: str = "openai/gpt-5.6-terra",
    env: dict[str, str] | None = None,
) -> tuple[str, dict[str, object]]:
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (env or {}).items():
        monkeypatch.setenv(name, value)

    fake = FakeDspy()
    monkeypatch.setattr(dspy_programs, "_dspy", lambda: fake)
    dspy_programs.build_lm(model)
    assert len(fake.calls) == 1
    return fake.calls[0]


def test_vercel_oidc_routes_openai_model_through_ai_gateway(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(
        monkeypatch,
        env={"VERCEL_OIDC_TOKEN": "oidc-secret"},
    )

    assert transport_model == "vercel_ai_gateway/openai/gpt-5.6-terra"
    assert kwargs == {"api_key": "oidc-secret"}


def test_gateway_credential_precedence_is_deterministic(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(
        monkeypatch,
        env={
            "AI_GATEWAY_API_KEY": "primary-secret",
            "VERCEL_AI_GATEWAY_API_KEY": "alias-secret",
            "VERCEL_OIDC_TOKEN": "oidc-secret",
        },
    )
    assert transport_model == "vercel_ai_gateway/openai/gpt-5.6-terra"
    assert kwargs["api_key"] == "primary-secret"

    _, alias_kwargs = _build(
        monkeypatch,
        env={
            "VERCEL_AI_GATEWAY_API_KEY": "alias-secret",
            "VERCEL_OIDC_TOKEN": "oidc-secret",
        },
    )
    assert alias_kwargs["api_key"] == "alias-secret"


def test_explicit_dspy_endpoint_override_prevents_gateway_remap(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(
        monkeypatch,
        env={
            "DSPY_API_BASE": "http://127.0.0.1:11434",
            "DSPY_API_KEY": "",
            "VERCEL_OIDC_TOKEN": "oidc-secret",
        },
    )

    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs == {"api_base": "http://127.0.0.1:11434", "api_key": ""}


def test_explicit_dspy_key_alone_prevents_gateway_remap(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(
        monkeypatch,
        env={
            "DSPY_API_KEY": "explicit-secret",
            "AI_GATEWAY_API_KEY": "gateway-secret",
        },
    )

    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs == {"api_key": "explicit-secret"}


def test_no_gateway_credential_preserves_existing_provider_behavior(monkeypatch: pytest.MonkeyPatch):
    transport_model, kwargs = _build(monkeypatch)

    assert transport_model == "openai/gpt-5.6-terra"
    assert kwargs == {}


def test_non_openai_and_already_gateway_models_are_not_misrouted(monkeypatch: pytest.MonkeyPatch):
    local_model, local_kwargs = _build(
        monkeypatch,
        model="ollama_chat/llama3.2:1b",
        env={"VERCEL_OIDC_TOKEN": "oidc-secret"},
    )
    assert local_model == "ollama_chat/llama3.2:1b"
    assert local_kwargs == {}

    gateway_model, gateway_kwargs = _build(
        monkeypatch,
        model="vercel_ai_gateway/openai/gpt-5.6-sol",
        env={"VERCEL_OIDC_TOKEN": "oidc-secret"},
    )
    assert gateway_model == "vercel_ai_gateway/openai/gpt-5.6-sol"
    assert gateway_kwargs == {"api_key": "oidc-secret"}


def test_canonical_model_order_and_identity_remain_unchanged():
    assert MODEL_ORDER == (
        "openai/gpt-5.6-luna",
        "openai/gpt-5.6-terra",
        "openai/gpt-5.6-sol",
    )
    assert all(not model.startswith("vercel_ai_gateway/") for model in MODEL_ORDER)
