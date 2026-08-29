from __future__ import annotations

import pytest

from parallax_api.services import github_actions_identity as identity


TOKEN = "x" * 64


def _claims(**overrides):
    claims = {
        "iss": identity.GITHUB_ACTIONS_ISSUER,
        "aud": identity.QA_AUTOMATION_AUDIENCE,
        "exp": 2_000_000_000,
        "iat": 1_900_000_000,
        "nbf": 1_900_000_000,
        "repository": identity.QA_AUTOMATION_REPOSITORY,
        "ref": identity.QA_AUTOMATION_REF,
        "workflow_ref": identity.QA_AUTOMATION_WORKFLOW_REF,
        "event_name": "workflow_dispatch",
        "runner_environment": "github-hosted",
        "run_id": "12345",
        "actor": "Ryan9876",
    }
    claims.update(overrides)
    return claims


class _SigningKey:
    key = object()


class _JwkClient:
    def get_signing_key_from_jwt(self, token):
        assert token == TOKEN
        return _SigningKey()


def test_accepts_exact_trusted_workflow(monkeypatch):
    monkeypatch.setattr(identity, "_jwk_client", _JwkClient())
    monkeypatch.setattr(identity.jwt, "decode", lambda *args, **kwargs: _claims())

    result = identity.verify_github_actions_identity(TOKEN)

    assert result.repository == "Ryan9876/parallax"
    assert result.run_id == "12345"


@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("repository", "attacker/repo"),
        ("ref", "refs/heads/feature"),
        ("workflow_ref", "Ryan9876/parallax/.github/workflows/other.yml@refs/heads/main"),
        ("event_name", "pull_request"),
        ("runner_environment", "self-hosted"),
    ],
)
def test_rejects_wrong_trust_claim(monkeypatch, claim, value):
    monkeypatch.setattr(identity, "_jwk_client", _JwkClient())
    monkeypatch.setattr(
        identity.jwt,
        "decode",
        lambda *args, **kwargs: _claims(**{claim: value}),
    )

    with pytest.raises(identity.GitHubActionsIdentityError):
        identity.verify_github_actions_identity(TOKEN)


def test_rejects_signature_or_standard_claim_failure(monkeypatch):
    monkeypatch.setattr(identity, "_jwk_client", _JwkClient())

    def fail(*args, **kwargs):
        raise ValueError("invalid token")

    monkeypatch.setattr(identity.jwt, "decode", fail)

    with pytest.raises(identity.GitHubActionsIdentityError):
        identity.verify_github_actions_identity(TOKEN)


def test_rejects_missing_run_id(monkeypatch):
    monkeypatch.setattr(identity, "_jwk_client", _JwkClient())
    monkeypatch.setattr(identity.jwt, "decode", lambda *args, **kwargs: _claims(run_id=""))

    with pytest.raises(identity.GitHubActionsIdentityError):
        identity.verify_github_actions_identity(TOKEN)
