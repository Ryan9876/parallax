from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest

from parallax_api.code.production_bootstrap import (
    VercelConnectGitHubBootstrapCredentialProvider,
)
from parallax_api.code.repository_authority import (
    RepositoryAuthorizationAwareGitHubCredentialProvider,
)
from parallax_api.tools.providers import ProviderClientError


REPOSITORY_REF = "github:Ryan9876/sickbeard"
CONNECTOR = "github/parallax-runtime"
OIDC = "vercel-runtime-oidc-test-token"


def _error_code(exc: ProviderClientError) -> str:
    return exc.result.result_code


def test_exact_repository_422_requires_explicit_provider_authorization() -> None:
    requests: list[httpx.Request] = []

    def connect(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "POST"
        assert request.url.path == "/v1/connect/token/github%2Fparallax-runtime"
        assert request.headers["authorization"] == f"Bearer {OIDC}"
        payload = json.loads(request.content)
        assert payload == {
            "subject": {"type": "app"},
            "authorizationDetails": [
                {
                    "type": "github_app_installation",
                    "repositories": ["Ryan9876/sickbeard"],
                    "permissions": ["contents:read", "metadata:read"],
                }
            ],
        }
        return httpx.Response(422, json={"error": {"code": "repository_not_authorized"}})

    provider = VercelConnectGitHubBootstrapCredentialProvider(
        CONNECTOR,
        oidc_token=OIDC,
        request_delivery_permissions=True,
        transport=httpx.MockTransport(connect),
    )

    with pytest.raises(ProviderClientError) as raised:
        provider.credential_for_repository(REPOSITORY_REF)

    assert _error_code(raised.value) == "REPOSITORY_AUTHORIZATION_REQUIRED"
    assert len(requests) == 1


def test_provider_outage_is_not_mislabeled_as_repository_consent() -> None:
    provider = RepositoryAuthorizationAwareGitHubCredentialProvider(
        CONNECTOR,
        oidc_token=OIDC,
        request_delivery_permissions=True,
        transport=httpx.MockTransport(lambda request: httpx.Response(503)),
    )

    with pytest.raises(ProviderClientError) as raised:
        provider.credential_for_repository(REPOSITORY_REF)

    assert _error_code(raised.value) == "CREDENTIAL_UNAVAILABLE"


def test_authorized_repository_still_requires_exact_derived_token_scope() -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    def connect(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "token": "github-exact-repository-token",
                "expiresAt": expires_at.isoformat(),
            },
        )

    def github(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/installation/repositories"
        assert request.headers["authorization"] == "Bearer github-exact-repository-token"
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "repositories": [{"full_name": "Ryan9876/sickbeard"}],
            },
        )

    provider = VercelConnectGitHubBootstrapCredentialProvider(
        CONNECTOR,
        oidc_token=OIDC,
        request_delivery_permissions=True,
        transport=httpx.MockTransport(connect),
        github_transport=httpx.MockTransport(github),
    )

    credential = provider.credential_for_repository(REPOSITORY_REF)

    assert credential.resource_ref == REPOSITORY_REF
    assert credential.authorization_value() == "Bearer github-exact-repository-token"


def test_multi_repository_derived_token_fails_exact_scope_verification() -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    provider = VercelConnectGitHubBootstrapCredentialProvider(
        CONNECTOR,
        oidc_token=OIDC,
        request_delivery_permissions=True,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "token": "github-too-broad-token",
                    "expiresAt": expires_at.isoformat(),
                },
            )
        ),
        github_transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "total_count": 2,
                    "repositories": [
                        {"full_name": "Ryan9876/sickbeard"},
                        {"full_name": "Ryan9876/parallax"},
                    ],
                },
            )
        ),
    )

    with pytest.raises(ProviderClientError) as raised:
        provider.credential_for_repository(REPOSITORY_REF)

    assert _error_code(raised.value) == "CREDENTIAL_SCOPE_MISMATCH"
