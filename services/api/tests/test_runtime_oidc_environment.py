from __future__ import annotations

import pytest

from parallax_api.code.production_delivery import ProductionDeliveryConfigurationError
from parallax_api.code.runtime_credentials import runtime_vercel_oidc_token


VALID_HEADER = "header-runtime-oidc"
VALID_ENV = "environment-runtime-oidc"


def test_production_uses_server_environment_oidc_when_request_token_absent(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", VALID_ENV)

    assert runtime_vercel_oidc_token({}, environment="production") == VALID_ENV


def test_valid_request_oidc_takes_precedence_over_environment(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", VALID_ENV)

    assert (
        runtime_vercel_oidc_token(
            {"x-vercel-oidc-token": VALID_HEADER},
            environment="production",
        )
        == VALID_HEADER
    )


def test_production_without_valid_server_oidc_fails_closed(monkeypatch) -> None:
    monkeypatch.delenv("VERCEL_OIDC_TOKEN", raising=False)

    with pytest.raises(ProductionDeliveryConfigurationError, match="credential is unavailable"):
        runtime_vercel_oidc_token({}, environment="production")


@pytest.mark.parametrize(
    "invalid",
    [
        "short",
        " padded-runtime-oidc",
        "padded-runtime-oidc ",
        "runtime\noidc",
        "x" * 8_193,
    ],
)
def test_production_rejects_malformed_environment_oidc(monkeypatch, invalid: str) -> None:
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", invalid)

    with pytest.raises(ProductionDeliveryConfigurationError, match="credential is unavailable"):
        runtime_vercel_oidc_token({}, environment="production")


def test_non_production_does_not_gain_environment_provider_authority(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", VALID_ENV)

    assert runtime_vercel_oidc_token({}, environment="preview") is None


def test_non_production_preserves_valid_request_token_behavior(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", VALID_ENV)

    assert (
        runtime_vercel_oidc_token(
            {"x-vercel-oidc-token": VALID_HEADER},
            environment="preview",
        )
        == VALID_HEADER
    )
