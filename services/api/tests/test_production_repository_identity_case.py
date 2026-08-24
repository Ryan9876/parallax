from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest

from parallax_api.code.production_delivery import (
    ProductionDeliveryConfigurationError,
    RepositoryPreviewTargetResolver,
    VercelConnectGitHubCredentialProvider,
)
from parallax_api.tools.providers.common import ProviderProjectBinding


PROJECT_ID = "11111111-1111-1111-1111-111111111111"
REGISTERED_REPOSITORY = "github:Ryan9876/parallax"
PROJECT_REPOSITORY = "github:ryan9876/parallax"
VERCEL_REF = "vercel:preview:parallax"


def _target(repository_ref: str = REGISTERED_REPOSITORY, *, suffix: str = "") -> dict[str, object]:
    return {
        "vercel_project_ref": f"{VERCEL_REF}{suffix}",
        "project_id": f"prj_casefold{suffix or '_primary'}",
        "project_name": f"parallax{suffix}",
        "team_id": "team_JgE8AWWz36uzRbeR6V6EWg9k",
        "repository_ref": repository_ref,
        "github_repo_id": 1340272514 if not suffix else 1340272515,
        "production_branch": "main",
        "github_connector": f"github/parallax-runtime{suffix}",
        "vercel_token_env": "PARALLAX_VERCEL_TOKEN_PARALLAX" if not suffix else "PARALLAX_VERCEL_TOKEN_OTHER",
    }


def test_preview_target_resolver_matches_github_repository_case_insensitively():
    resolver = RepositoryPreviewTargetResolver.from_environment(json.dumps([_target()]))
    binding = ProviderProjectBinding(PROJECT_ID, PROJECT_REPOSITORY)

    registration = resolver.registration(binding)
    target = resolver.resolve(binding)

    assert registration.api_target.repository_ref == REGISTERED_REPOSITORY
    assert target.project_ref == PROJECT_ID
    assert target.repository_ref == PROJECT_REPOSITORY
    assert target.vercel_project_ref == VERCEL_REF


def test_preview_target_resolver_rejects_case_only_github_duplicates():
    payload = [
        _target(),
        _target(PROJECT_REPOSITORY, suffix="-duplicate"),
    ]

    with pytest.raises(ProductionDeliveryConfigurationError, match="duplicate repository"):
        RepositoryPreviewTargetResolver.from_environment(json.dumps(payload))


def test_github_connect_scope_verification_accepts_provider_canonical_casing():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    def connect_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/connect/token/github/parallax-runtime"
        return httpx.Response(
            200,
            json={"token": "github-case-test-token", "expiresAt": expires_at.isoformat()},
        )

    def scope_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/installation/repositories"
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "repositories": [{"full_name": "Ryan9876/parallax"}],
            },
        )

    provider = VercelConnectGitHubCredentialProvider(
        "github/parallax-runtime",
        oidc_token="oidc-case-test",
        transport=httpx.MockTransport(connect_handler),
        github_transport=httpx.MockTransport(scope_handler),
    )

    credential = provider.credential_for_repository(PROJECT_REPOSITORY)

    assert credential.resource_ref == PROJECT_REPOSITORY
