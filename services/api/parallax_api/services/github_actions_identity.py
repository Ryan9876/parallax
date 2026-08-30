from __future__ import annotations

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient


GITHUB_ACTIONS_ISSUER = "https://token.actions.githubusercontent.com"
QA_AUTOMATION_AUDIENCE = "parallax://qa-production"
QA_AUTOMATION_REPOSITORY = "Ryan9876/parallax"
QA_AUTOMATION_REF = "refs/heads/main"
QA_AUTOMATION_WORKFLOW_REF = (
    "Ryan9876/parallax/.github/workflows/qa-production-replay.yml@refs/heads/main"
)
W8_S2_QA_AUTOMATION_WORKFLOW_REF = (
    "Ryan9876/parallax/.github/workflows/w8-s2-qa-replay.yml@refs/heads/main"
)
P2313_QA_AUTOMATION_WORKFLOW_REF = (
    "Ryan9876/parallax/.github/workflows/qa-p2313-production-retry.yml@refs/heads/main"
)
QA_AUTOMATION_WORKFLOW_REFS = frozenset(
    {
        QA_AUTOMATION_WORKFLOW_REF,
        W8_S2_QA_AUTOMATION_WORKFLOW_REF,
        P2313_QA_AUTOMATION_WORKFLOW_REF,
    }
)
QA_AUTOMATION_EMAIL = "parallax.qa.ai@gmail.com"
QA_AUTOMATION_EVENTS = frozenset({"workflow_dispatch", "push"})
_GITHUB_JWKS_URL = "https://token.actions.githubusercontent.com/.well-known/jwks"


class GitHubActionsIdentityError(ValueError):
    pass


@dataclass(frozen=True)
class GitHubActionsIdentity:
    repository: str
    workflow_ref: str
    run_id: str
    actor: str | None


_jwk_client = PyJWKClient(_GITHUB_JWKS_URL, cache_keys=True)


def verify_github_actions_identity(token: str) -> GitHubActionsIdentity:
    if not isinstance(token, str):
        raise GitHubActionsIdentityError("GitHub Actions authentication could not be verified")
    candidate = token.strip()
    if candidate != token or not 32 <= len(candidate) <= 16_384:
        raise GitHubActionsIdentityError("GitHub Actions authentication could not be verified")

    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(candidate)
        claims = jwt.decode(
            candidate,
            signing_key.key,
            algorithms=["RS256"],
            audience=QA_AUTOMATION_AUDIENCE,
            issuer=GITHUB_ACTIONS_ISSUER,
            options={"require": ["exp", "iat", "nbf", "iss", "aud"]},
        )
    except Exception as exc:
        raise GitHubActionsIdentityError(
            "GitHub Actions authentication could not be verified"
        ) from exc

    required = {
        "repository": QA_AUTOMATION_REPOSITORY,
        "ref": QA_AUTOMATION_REF,
        "runner_environment": "github-hosted",
    }
    for key, expected in required.items():
        if claims.get(key) != expected:
            raise GitHubActionsIdentityError(
                "GitHub Actions authentication could not be verified"
            )

    workflow_ref = str(claims.get("workflow_ref") or "")
    if workflow_ref not in QA_AUTOMATION_WORKFLOW_REFS:
        raise GitHubActionsIdentityError("GitHub Actions authentication could not be verified")

    if claims.get("event_name") not in QA_AUTOMATION_EVENTS:
        raise GitHubActionsIdentityError("GitHub Actions authentication could not be verified")

    run_id = str(claims.get("run_id") or "").strip()
    if not run_id or len(run_id) > 64:
        raise GitHubActionsIdentityError("GitHub Actions authentication could not be verified")

    actor = str(claims.get("actor") or "").strip() or None
    return GitHubActionsIdentity(
        repository=QA_AUTOMATION_REPOSITORY,
        workflow_ref=workflow_ref,
        run_id=run_id,
        actor=actor,
    )
