from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import httpx

from parallax_api.code.production_delivery import VercelConnectGitHubCredentialProvider


REPOSITORY_REF = "github:Ryan9876/parallax"
CONNECTOR = "github/parallax-runtime"


def test_vercel_connect_connector_is_one_percent_encoded_path_parameter_and_delivery_scope_is_exact() -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    connect_requests: list[httpx.Request] = []

    def connect_handler(request: httpx.Request) -> httpx.Response:
        connect_requests.append(request)
        # `URL.path` is decoded and would hide the production regression. The
        # raw wire path must encode the slash inside the connector identifier.
        assert request.url.raw_path == b"/v1/connect/token/github%2Fparallax-runtime"
        payload = json.loads(request.content)
        assert payload == {
            "subject": {"type": "app"},
            "authorizationDetails": [
                {
                    "type": "github_app_installation",
                    "repositories": ["Ryan9876/parallax"],
                    "permissions": [
                        "contents:write",
                        "metadata:read",
                        "pull_requests:write",
                    ],
                }
            ],
        }
        return httpx.Response(
            200,
            json={
                "token": "github-installation-test-token",
                "expiresAt": expires_at.isoformat(),
            },
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
        CONNECTOR,
        oidc_token="oidc-test-value",
        transport=httpx.MockTransport(connect_handler),
        github_transport=httpx.MockTransport(scope_handler),
    )

    credential = provider.credential_for_repository(REPOSITORY_REF)

    assert credential.resource_ref == REPOSITORY_REF
    assert len(connect_requests) == 1
