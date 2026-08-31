from __future__ import annotations

import pytest

from parallax_api.services import github_actions_identity as identity


TOKEN = "x" * 64
LEGACY_REPOSITORY = "Ryan9876/parallax"
LEGACY_REPOSITORY_ID = "1340272514"
LEGACY_QA_WORKFLOW_REF = (
    "Ryan9876/parallax/.github/workflows/qa-production-replay.yml@refs/heads/main"
)
LEGACY_W8_S2_WORKFLOW_REF = (
    "Ryan9876/parallax/.github/workflows/w8-s2-qa-replay.yml@refs/heads/main"
)


def _claims(**overrides):
    claims = {
        "iss": identity.GITHUB_ACTIONS_ISSUER,
        "aud": identity.QA_AUTOMATION_AUDIENCE,
        "exp": 2_000_000_000,
        "iat": 1_900_000_000,
        "nbf": 1_900_000_000,
        "repository": identity.QA_AUTOMATION_REPOSITORY,
        "repository_id": identity.QA_AUTOMATION_REPOSITORY_ID,
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
    assert result.repository_id == "1351817336"
    assert result.workflow_ref == identity.QA_AUTOMATION_WORKFLOW_REF
    assert result.run_id == "12345"


def test_accepts_exact_dedicated_qa_main_push_workflow(monkeypatch):
    _install_valid_decode(monkeypatch, event_name="push")

    result = identity.verify_github_actions_identity(TOKEN)

    assert result.repository == identity.QA_AUTOMATION_REPOSITORY
    assert result.repository_id == identity.QA_AUTOMATION_REPOSITORY_ID
    assert result.workflow_ref == identity.QA_AUTOMATION_WORKFLOW_REF


def test_standing_trust_contains_only_dedicated_repository_tuple():
    assert identity.QA_AUTOMATION_TRUSTED_WORKFLOW_IDENTITIES == frozenset(
        {
            (
                identity.QA_AUTOMATION_REPOSITORY,
                identity.QA_AUTOMATION_REPOSITORY_ID,
                identity.QA_AUTOMATION_WORKFLOW_REF,
            )
        }
    )


@pytest.mark.parametrize(
    "workflow_ref",
    [LEGACY_QA_WORKFLOW_REF, LEGACY_W8_S2_WORKFLOW_REF],
)
def test_rejects_retired_application_qa_workflows(monkeypatch, workflow_ref):
    _install_valid_decode(
        monkeypatch,
        repository=LEGACY_REPOSITORY,
        repository_id=LEGACY_REPOSITORY_ID,
        workflow_ref=workflow_ref,
        event_name="push",
    )

    with pytest.raises(identity.GitHubActionsIdentityError):
        identity.verify_github_actions_identity(TOKEN)


@pytest.mark.parametrize(
    ("repository", "repository_id", "workflow_ref"),
    [
        (
            identity.QA_AUTOMATION_REPOSITORY,
            identity.QA_AUTOMATION_REPOSITORY_ID,
            LEGACY_QA_WORKFLOW_REF,
        ),
        (
            LEGACY_REPOSITORY,
            LEGACY_REPOSITORY_ID,
            identity.QA_AUTOMATION_WORKFLOW_REF,
        ),
        (
            "attacker/repo",
            identity.QA_AUTOMATION_REPOSITORY_ID,
            identity.QA_AUTOMATION_WORKFLOW_REF,
        ),
        (
            identity.QA_AUTOMATION_REPOSITORY,
            "9999999999",
            identity.QA_AUTOMATION_WORKFLOW_REF,
        ),
        (
            "attacker/recreated-parallax-qa",
            identity.QA_AUTOMATION_REPOSITORY_ID,
            identity.QA_AUTOMATION_WORKFLOW_REF,
        ),
    ],
)
def test_rejects_repository_identity_cross_pair(
    monkeypatch,
    repository,
    repository_id,
    workflow_ref,
):
    _install_valid_decode(
        monkeypatch,
        repository=repository,
        repository_id=repository_id,
        workflow_ref=workflow_ref,
    )

    with pytest.raises(identity.GitHubActionsIdentityError):
        identity.verify_github_actions_identity(TOKEN)


@pytest.mark.parametrize("repository_id", ["", " ", None])
def test_rejects_missing_repository_id(monkeypatch, repository_id):
    _install_valid_decode(monkeypatch, repository_id=repository_id)

    with pytest.raises(identity.GitHubActionsIdentityError):
        identity.verify_github_actions_identity(TOKEN)


def test_rejects_retired_p2314_production_retry_workflow(monkeypatch):
    _install_valid_decode(
        monkeypatch,
        repository=LEGACY_REPOSITORY,
        repository_id=LEGACY_REPOSITORY_ID,
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
