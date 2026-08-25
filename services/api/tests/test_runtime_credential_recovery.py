from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy.orm import sessionmaker

from parallax_api.code import production_delivery as production_delivery_module
from parallax_api.code.production_delivery import (
    ProductionDeliveryConfigurationError,
    VercelConnectGitHubCredentialProvider,
    production_source_delivery,
)
from parallax_api.code.runtime_credentials import (
    runtime_vercel_oidc_token,
    verify_registered_runtime_github_credentials,
)
from parallax_api.db import Base, make_engine
from parallax_api.projects.repository import ProjectRepository
from parallax_api.routes import health as health_routes
from parallax_api.tools.providers.common import ProviderClientError
from parallax_api.tools.providers.credentials import ProviderCredentialKind


OWNER = "owner:runtime-credential-recovery"
REPOSITORY_REF = "github:Ryan9876/parallax"
CONNECTOR = "github/parallax-runtime"
VERCEL_REF = "vercel:preview:parallax"
VERCEL_TOKEN_ENV = "PARALLAX_VERCEL_TOKEN_PARALLAX"
RUNTIME_OIDC = "runtime-oidc-test-value"


def _targets_json() -> str:
    return json.dumps(
        [
            {
                "vercel_project_ref": VERCEL_REF,
                "project_id": "prj_wLXC5JjjetJf0H97kncRlqczD3OC",
                "project_name": "parallax",
                "team_id": "team_JgE8AWWz36uzRbeR6V6EWg9k",
                "repository_ref": REPOSITORY_REF,
                "github_repo_id": 1340272514,
                "production_branch": "main",
                "github_connector": CONNECTOR,
                "vercel_token_env": VERCEL_TOKEN_ENV,
            }
        ]
    )


def _future_expiration() -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()


def _exact_scope_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "total_count": 1,
            "repositories": [{"full_name": "Ryan9876/parallax"}],
        },
    )


def test_production_runtime_oidc_requires_request_header_not_build_environment(monkeypatch):
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", "build-only-oidc-value")

    with pytest.raises(ProductionDeliveryConfigurationError, match="runtime Vercel OIDC"):
        runtime_vercel_oidc_token({}, environment="production")

    assert runtime_vercel_oidc_token(
        {"x-vercel-oidc-token": RUNTIME_OIDC},
        environment="production",
    ) == RUNTIME_OIDC


def test_runtime_credential_missing_oidc_fails_closed(monkeypatch):
    monkeypatch.delenv("VERCEL_OIDC_TOKEN", raising=False)
    provider = VercelConnectGitHubCredentialProvider(
        CONNECTOR,
        transport=httpx.MockTransport(lambda request: pytest.fail("Connect must not be called")),
        github_transport=httpx.MockTransport(lambda request: pytest.fail("GitHub must not be called")),
    )

    with pytest.raises(ProviderClientError, match="CREDENTIAL_UNAVAILABLE"):
        provider.credential_for_repository(REPOSITORY_REF)


def test_runtime_credential_connector_unavailable_fails_closed():
    connect_calls: list[httpx.Request] = []

    def connect_handler(request: httpx.Request) -> httpx.Response:
        connect_calls.append(request)
        assert request.url.raw_path == b"/v1/connect/token/github%2Fparallax-runtime"
        assert request.headers["Authorization"] == f"Bearer {RUNTIME_OIDC}"
        return httpx.Response(404, json={"error": {"code": "connector_not_found"}})

    provider = VercelConnectGitHubCredentialProvider(
        CONNECTOR,
        oidc_token=RUNTIME_OIDC,
        transport=httpx.MockTransport(connect_handler),
        github_transport=httpx.MockTransport(lambda request: pytest.fail("GitHub must not be called")),
    )

    with pytest.raises(ProviderClientError, match="CREDENTIAL_UNAVAILABLE"):
        provider.credential_for_repository(REPOSITORY_REF)
    assert len(connect_calls) == 1


def test_runtime_credential_scope_mismatch_is_rejected():
    def connect_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"token": "github-installation-test-token", "expiresAt": _future_expiration()},
        )

    def scope_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "total_count": 2,
                "repositories": [
                    {"full_name": "Ryan9876/parallax"},
                    {"full_name": "Ryan9876/other"},
                ],
            },
        )

    provider = VercelConnectGitHubCredentialProvider(
        CONNECTOR,
        oidc_token=RUNTIME_OIDC,
        transport=httpx.MockTransport(connect_handler),
        github_transport=httpx.MockTransport(scope_handler),
    )

    with pytest.raises(ProviderClientError, match="CREDENTIAL_SCOPE_MISMATCH"):
        provider.credential_for_repository(REPOSITORY_REF)


def test_runtime_credential_expired_exchange_is_rejected_before_github_scope_call():
    expired_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()

    def connect_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"token": "github-installation-test-token", "expiresAt": expired_at},
        )

    provider = VercelConnectGitHubCredentialProvider(
        CONNECTOR,
        oidc_token=RUNTIME_OIDC,
        transport=httpx.MockTransport(connect_handler),
        github_transport=httpx.MockTransport(lambda request: pytest.fail("GitHub must not be called")),
    )

    with pytest.raises(ProviderClientError, match="CREDENTIAL_EXPIRED"):
        provider.credential_for_repository(REPOSITORY_REF)


def test_runtime_credential_success_is_exact_repository_scoped_and_redacted():
    def connect_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.raw_path == b"/v1/connect/token/github%2Fparallax-runtime"
        assert json.loads(request.content) == {"subject": {"type": "app"}}
        return httpx.Response(
            200,
            json={"token": "github-installation-test-token", "expiresAt": _future_expiration()},
        )

    provider = VercelConnectGitHubCredentialProvider(
        CONNECTOR,
        oidc_token=RUNTIME_OIDC,
        transport=httpx.MockTransport(connect_handler),
        github_transport=httpx.MockTransport(lambda request: _exact_scope_response()),
    )

    credential = provider.credential_for_repository(REPOSITORY_REF)

    assert credential.kind is ProviderCredentialKind.GITHUB_APP_INSTALLATION
    assert credential.resource_ref == REPOSITORY_REF
    assert "github-installation-test-token" not in repr(credential)


def test_runtime_readiness_preflight_reuses_real_exchange_and_exact_scope():
    connect_calls: list[httpx.Request] = []
    github_calls: list[httpx.Request] = []

    def connect_handler(request: httpx.Request) -> httpx.Response:
        connect_calls.append(request)
        return httpx.Response(
            200,
            json={"token": "github-installation-test-token", "expiresAt": _future_expiration()},
        )

    def github_handler(request: httpx.Request) -> httpx.Response:
        github_calls.append(request)
        return _exact_scope_response()

    verified = verify_registered_runtime_github_credentials(
        RUNTIME_OIDC,
        preview_targets_json=_targets_json(),
        connect_transport=httpx.MockTransport(connect_handler),
        github_transport=httpx.MockTransport(github_handler),
    )

    assert verified == 1
    assert len(connect_calls) == 1
    assert connect_calls[0].url.raw_path == b"/v1/connect/token/github%2Fparallax-runtime"
    assert len(github_calls) == 1
    assert github_calls[0].url.path == "/installation/repositories"


def test_production_source_delivery_injects_request_oidc_into_github_provider(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'runtime-oidc.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    captured: list[tuple[str, str | None]] = []

    class CapturingGitHubCredentials:
        def __init__(self, connector, *, oidc_token=None, **kwargs):
            captured.append((connector, oidc_token))

        def credential_for_repository(self, repository_ref):
            raise AssertionError("credential exchange is not expected during composition")

    monkeypatch.setattr(
        production_delivery_module,
        "VercelConnectGitHubCredentialProvider",
        CapturingGitHubCredentials,
    )

    try:
        project = ProjectRepository(session).create(
            owner_subject=OWNER,
            slug="runtime-credential-recovery",
            name="Runtime Credential Recovery",
            description="credential composition regression",
            repository_ref=REPOSITORY_REF,
        )
        delivery = production_source_delivery(
            session,
            owner_subject=OWNER,
            allocator=SimpleNamespace(),
            project_id=project.id,
            preview_targets_json=_targets_json(),
            environment={VERCEL_TOKEN_ENV: "vercel-preview-scoped-token"},
            oidc_token=RUNTIME_OIDC,
        )

        assert delivery.bootstrap is not None
        assert captured == [(CONNECTOR, RUNTIME_OIDC)]
    finally:
        session.close()
        engine.dispose()


class _ReadyResult:
    def scalar_one(self):
        return 1


class _ReadySession:
    def execute(self, statement):
        return _ReadyResult()


def _request(*, oidc: str | None = None) -> Request:
    headers = [] if oidc is None else [(b"x-vercel-oidc-token", oidc.encode())]
    return Request({"type": "http", "method": "GET", "path": "/ready", "headers": headers})


def test_production_ready_rejects_build_only_oidc(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", "build-only-oidc-value")

    with pytest.raises(HTTPException) as failure:
        health_routes.ready(_request(), _ReadySession())

    assert failure.value.status_code == 503
    assert failure.value.detail == "provider credential unavailable"


def test_production_ready_requires_successful_runtime_exchange(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "production")
    observed: list[str] = []

    def verify(oidc_token: str) -> int:
        observed.append(oidc_token)
        return 1

    monkeypatch.setattr(health_routes, "verify_registered_runtime_github_credentials", verify)

    result = health_routes.ready(_request(oidc=RUNTIME_OIDC), _ReadySession())

    assert observed == [RUNTIME_OIDC]
    assert result == {
        "status": "ready",
        "database": "ok",
        "service": "parallax-api",
        "providers": "ok",
        "provider_targets": 1,
    }
