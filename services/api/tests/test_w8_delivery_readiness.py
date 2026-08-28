from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

from parallax_api.code import delivery_readiness as readiness_module
from parallax_api.code import production_delivery_lazy as lazy_module
from parallax_api.code.delivery_readiness import (
    VercelProjectReadinessRestClient,
    _github_identity,
    production_source_delivery_ready,
)
from parallax_api.code.production_bootstrap import (
    VercelConnectGitHubBootstrapCredentialProvider,
)
from parallax_api.code.production_delivery import EnvironmentVercelCredentialProvider
from parallax_api.tools.providers.common import ProviderClientError
from parallax_api.tools.providers.credentials import (
    ProviderCredentialKind,
    ScopedBearerCredential,
)


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
REPOSITORY_REF = "github:Ryan9876/ot-time"
TEAM_ID = "team_JgE8AWWz36uzRbeR6V6EWg9k"
READINESS_REF = f"readiness:{TEAM_ID}"
TOKEN = "vercel-readiness-test-token"


def _vercel_credentials() -> EnvironmentVercelCredentialProvider:
    return EnvironmentVercelCredentialProvider(
        TOKEN,
        allowed_targets=frozenset({READINESS_REF}),
    )


def _project_payload(project_id: str = "prj_ot_time") -> dict[str, object]:
    return {
        "id": project_id,
        "name": "ot-time-px-11111111",
        "accountId": TEAM_ID,
        "link": {"type": "github", "repoId": 424242},
    }


def test_plan_composition_bootstraps_source_without_resolving_vercel(monkeypatch):
    calls: list[str] = []
    bootstrap = SimpleNamespace(ensure=lambda run, operation_key: calls.append(f"bootstrap:{operation_key}"))

    def fake_bootstrap(*args, **kwargs):
        calls.append("compose-bootstrap")
        return bootstrap

    def forbidden_readiness(*args, **kwargs):
        calls.append("resolve-vercel")
        raise AssertionError("Preview readiness must not be resolved during composition or source bootstrap")

    monkeypatch.setattr(lazy_module, "production_source_bootstrap", fake_bootstrap)
    monkeypatch.setattr(lazy_module, "production_source_delivery_ready", forbidden_readiness)

    composition = lazy_module.production_source_delivery_lazy(
        object(),
        owner_subject="owner:w8",
        allocator=object(),
        project_id=PROJECT_ID,
    )
    assert calls == ["compose-bootstrap"]

    composition.bootstrap.ensure(SimpleNamespace(), operation_key="w8-plan")
    assert calls == ["compose-bootstrap", "bootstrap:w8-plan"]


def test_deferred_delivery_resolves_readiness_only_at_review_delivery(monkeypatch):
    calls: list[str] = []
    bootstrap = SimpleNamespace(ensure=lambda run, operation_key: None)
    expected = object()

    class ReadyDelivery:
        def deliver(self, run, *, operation_key):
            calls.append(f"deliver:{operation_key}")
            return expected

        def resolve_record(self, run):
            return None

    def fake_bootstrap(*args, **kwargs):
        return bootstrap

    def fake_readiness(*args, **kwargs):
        calls.append("resolve-vercel")
        return SimpleNamespace(delivery=ReadyDelivery())

    monkeypatch.setattr(lazy_module, "production_source_bootstrap", fake_bootstrap)
    monkeypatch.setattr(lazy_module, "production_source_delivery_ready", fake_readiness)

    composition = lazy_module.production_source_delivery_lazy(
        object(),
        owner_subject="owner:w8",
        allocator=object(),
        project_id=PROJECT_ID,
    )
    assert calls == []
    assert composition.delivery.resolve_record(SimpleNamespace()) is None
    assert calls == []

    result = composition.delivery.deliver(SimpleNamespace(), operation_key="w8-review")
    assert result is expected
    assert calls == ["resolve-vercel", "deliver:w8-review"]


def test_plan_bootstrap_requests_exact_repository_read_only_scope():
    assert VercelConnectGitHubBootstrapCredentialProvider.delivery_authorization_details(
        "Ryan9876/ot-time"
    ) == [
        {
            "type": "github_app_installation",
            "repositories": ["Ryan9876/ot-time"],
            "permissions": ["contents:read", "metadata:read"],
        }
    ]


def test_existing_registered_target_preserves_existing_delivery_path(monkeypatch):
    sentinel = object()
    calls = []

    def existing(*args, **kwargs):
        calls.append(kwargs["project_id"])
        return sentinel

    monkeypatch.setattr(readiness_module, "production_source_delivery", existing)
    result = production_source_delivery_ready(
        object(),
        owner_subject="owner:w8",
        allocator=object(),
        project_id=PROJECT_ID,
    )

    assert result is sentinel
    assert calls == [PROJECT_ID]


def test_github_identity_requires_exact_canonical_repository_and_numeric_id():
    credential = ScopedBearerCredential(
        provider="github",
        resource_ref=REPOSITORY_REF,
        kind=ProviderCredentialKind.GITHUB_APP_INSTALLATION,
        secret="github-readiness-test-token",
        expires_at=None,
    )

    class Credentials:
        def credential_for_repository(self, repository_ref):
            assert repository_ref == REPOSITORY_REF
            return credential

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/repos/Ryan9876/ot-time"
        return httpx.Response(
            200,
            json={
                "full_name": "Ryan9876/ot-time",
                "id": 424242,
                "default_branch": "main",
            },
        )

    identity = _github_identity(
        Credentials(),
        REPOSITORY_REF,
        transport=httpx.MockTransport(handler),
    )
    assert identity.repository_ref == REPOSITORY_REF
    assert identity.repository_id == 424242
    assert identity.default_branch == "main"


def test_github_identity_rejects_cross_repository_response():
    credential = ScopedBearerCredential(
        provider="github",
        resource_ref=REPOSITORY_REF,
        kind=ProviderCredentialKind.GITHUB_APP_INSTALLATION,
        secret="github-readiness-test-token",
        expires_at=None,
    )

    class Credentials:
        def credential_for_repository(self, repository_ref):
            return credential

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "full_name": "Ryan9876/not-ot-time",
                "id": 424242,
                "default_branch": "main",
            },
        )
    )
    with pytest.raises(ProviderClientError, match="REPOSITORY_MISMATCH"):
        _github_identity(Credentials(), REPOSITORY_REF, transport=transport)


def test_readiness_reuses_only_exact_numeric_github_repository_match():
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path == "/v9/projects":
            return httpx.Response(
                200,
                json={
                    "projects": [
                        {
                            "id": "prj_name_only",
                            "name": "ot-time-px-11111111",
                            "link": {"type": "github", "repoId": 9},
                        },
                        _project_payload(),
                    ],
                    "pagination": {"next": None},
                },
            )
        if request.url.path == "/v9/projects/prj_ot_time":
            return httpx.Response(200, json=_project_payload())
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = VercelProjectReadinessRestClient(
        _vercel_credentials(),
        credential_ref=READINESS_REF,
        team_id=TEAM_ID,
        transport=httpx.MockTransport(handler),
    )
    result = client.ensure(
        repository_ref=REPOSITORY_REF,
        github_repo_id=424242,
        production_branch="main",
        project_name="ot-time-px-11111111",
    )

    assert result.created is False
    assert result.target.project_id == "prj_ot_time"
    assert result.target.github_repo_id == 424242
    assert requests == [("GET", "/v9/projects"), ("GET", "/v9/projects/prj_ot_time")]


def test_missing_target_is_created_once_verified_and_reused_without_production_mutation():
    created = False
    mutations: list[tuple[str, str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal created
        if request.url.path == "/v9/projects":
            projects = [_project_payload()] if created else []
            return httpx.Response(200, json={"projects": projects, "pagination": {"next": None}})
        if request.url.path == "/v11/projects":
            assert request.method == "POST"
            body = json.loads(request.content)
            mutations.append((request.method, request.url.path, body))
            assert body == {
                "name": "ot-time-px-11111111",
                "gitRepository": {"type": "github", "repo": "Ryan9876/ot-time"},
            }
            assert "target" not in body
            created = True
            return httpx.Response(200, json={"id": "prj_ot_time"})
        if request.url.path == "/v9/projects/prj_ot_time":
            return httpx.Response(200, json=_project_payload())
        if request.url.path == "/v6/deployments":
            assert request.method == "GET"
            assert request.url.params["target"] == "production"
            assert request.url.params["projectId"] == "prj_ot_time"
            return httpx.Response(200, json={"deployments": []})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = VercelProjectReadinessRestClient(
        _vercel_credentials(),
        credential_ref=READINESS_REF,
        team_id=TEAM_ID,
        transport=httpx.MockTransport(handler),
    )

    first = client.ensure(
        repository_ref=REPOSITORY_REF,
        github_repo_id=424242,
        production_branch="main",
        project_name="ot-time-px-11111111",
    )
    second = client.ensure(
        repository_ref=REPOSITORY_REF,
        github_repo_id=424242,
        production_branch="main",
        project_name="ot-time-px-11111111",
    )

    assert first.created is True
    assert second.created is False
    assert first.target.project_id == second.target.project_id == "prj_ot_time"
    assert mutations == [
        (
            "POST",
            "/v11/projects",
            {
                "name": "ot-time-px-11111111",
                "gitRepository": {"type": "github", "repo": "Ryan9876/ot-time"},
            },
        )
    ]


def test_duplicate_exact_targets_fail_before_any_mutation():
    mutation_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal mutation_count
        if request.method != "GET":
            mutation_count += 1
        if request.url.path == "/v9/projects":
            first = _project_payload("prj_one")
            second = _project_payload("prj_two")
            return httpx.Response(
                200,
                json={"projects": [first, second], "pagination": {"next": None}},
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = VercelProjectReadinessRestClient(
        _vercel_credentials(),
        credential_ref=READINESS_REF,
        team_id=TEAM_ID,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderClientError, match="TARGET_AMBIGUOUS"):
        client.ensure(
            repository_ref=REPOSITORY_REF,
            github_repo_id=424242,
            production_branch="main",
            project_name="ot-time-px-11111111",
        )
    assert mutation_count == 0


def test_unbounded_project_discovery_fails_closed():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"projects": [], "pagination": {"next": 123}},
        )
    )
    client = VercelProjectReadinessRestClient(
        _vercel_credentials(),
        credential_ref=READINESS_REF,
        team_id=TEAM_ID,
        transport=transport,
    )
    with pytest.raises(ProviderClientError, match="TARGET_DISCOVERY_UNBOUNDED"):
        client.ensure(
            repository_ref=REPOSITORY_REF,
            github_repo_id=424242,
            production_branch="main",
            project_name="ot-time-px-11111111",
        )
