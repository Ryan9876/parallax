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


def _install_valid_decode(monkeypatch, **overrides):
    monkeypatch.setattr(identity, "_jwk_client", _JwkClient())
    monkeypatch.setattr(identity.jwt, "decode", lambda *args, **kwargs: _claims(**overrides))


def test_accepts_exact_dedicated_qa_manual_workflow(monkeypatch):
    _install_valid_decode(monkeypatch)

    result = identity.verify_github_actions_identity(TOKEN)

    assert result.repository == "Ryan9876/parallax-qa"
    assert result.workflow_ref == identity.QA_AUTOMATION_WORKFLOW_REF
    assert result.run_id == "12345"


def test_accepts_exact_dedicated_qa_main_push_workflow(monkeypatch):
    _install_valid_decode(monkeypatch, event_name="push")

    result = identity.verify_github_actions_identity(TOKEN)

    assert result.repository == identity.QA_AUTOMATION_REPOSITORY
    assert result.workflow_ref == identity.QA_AUTOMATION_WORKFLOW_REF


def test_temporarily_accepts_legacy_application_qa_workflow(monkeypatch):
    _install_valid_decode(
        monkeypatch,
        repository=identity.LEGACY_QA_AUTOMATION_REPOSITORY,
        workflow_ref=identity.LEGACY_QA_AUTOMATION_WORKFLOW_REF,
        event_name="push",
    )

    result = identity.verify_github_actions_identity(TOKEN)

    assert result.repository == identity.LEGACY_QA_AUTOMATION_REPOSITORY
    assert result.workflow_ref == identity.LEGACY_QA_AUTOMATION_WORKFLOW_REF


def test_temporarily_accepts_legacy_w8_s2_workflow(monkeypatch):
    _install_valid_decode(
        monkeypatch,
        repository=identity.LEGACY_QA_AUTOMATION_REPOSITORY,
        workflow_ref=identity.W8_S2_QA_AUTOMATION_WORKFLOW_REF,
        event_name="push",
    )

    result = identity.verify_github_actions_identity(TOKEN)

    assert result.repository == identity.LEGACY_QA_AUTOMATION_REPOSITORY
    assert result.workflow_ref == identity.W8_S2_QA_AUTOMATION_WORKFLOW_REF


@pytest.mark.parametrize(
    ("repository", "workflow_ref"),
    [
        (
            "Ryan9876/parallax-qa",
            "Ryan9876/parallax/.github/workflows/qa-production-replay.yml@refs/heads/main",
        ),
        (
            "Ryan9876/parallax",
            "Ryan9876/parallax-qa/.github/workflows/production-replay.yml@refs/heads/main",
        ),
        (
            "attacker/repo",
            "Ryan9876/parallax-qa/.github/workflows/production-replay.yml@refs/heads/main",
        ),
    ],
)
def test_rejects_repository_workflow_cross_pair(monkeypatch, repository, workflow_ref):
    _install_valid_decode(
        monkeypatch,
        repository=repository,
        workflow_ref=workflow_ref,
    )

    with pytest.raises(identity.GitHubActionsIdentityError):
        identity.verify_github_actions_identity(TOKEN)


def test_rejects_retired_p2314_production_retry_workflow(monkeypatch):
    _install_valid_decode(
        monkeypatch,
        repository=identity.LEGACY_QA_AUTOMATION_REPOSITORY,
        workflow_ref=(
            "Ryan9876/parallax/.github/workflows/"
            "qa-p2313-production-retry.yml@refs/heads/main"
        ),
        event_name="push",
    )

    with pytest.raises(identity.GitHubActionsIdentityError):
        identity.verify_github_actions_identity(TOKEN)


@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("ref", "refs/heads/feature"),
        ("workflow_ref", "Ryan9876/parallax-qa/.github/workflows/other.yml@refs/heads/main"),
        ("event_name", "pull_request"),
        ("runner_environment", "self-hosted"),
    ],
)
def test_rejects_wrong_trust_claim(monkeypatch, claim, value):
    _install_valid_decode(monkeypatch, **{claim: value})

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
    _install_valid_decode(monkeypatch, run_id="")

    with pytest.raises(identity.GitHubActionsIdentityError):
        identity.verify_github_actions_identity(TOKEN)
