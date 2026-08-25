from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from parallax_api.code import production_delivery as production_delivery_module
from parallax_api.code.autonomy import AutonomyResult, AutonomyStopReason
from parallax_api.code.production_delivery import (
    EnvironmentVercelCredentialProvider,
    ProductionDeliveryConfigurationError,
    RepositoryPreviewTargetResolver,
    VercelConnectGitHubCredentialProvider,
    production_source_delivery,
)
from parallax_api.db import Base, make_engine
from parallax_api.projects.repository import ProjectRepository
from parallax_api.routes import engineering_runs as engineering_routes
from parallax_api.schemas import EngineeringOperation
from parallax_api.tools.providers.common import ProviderClientError, ProviderProjectBinding
from parallax_api.tools.providers.credentials import ProviderCredentialKind


OWNER = "owner:release-composition"
PROJECT_ID = str(uuid4())
REPOSITORY_REF = "github:Ryan9876/parallax"
VERCEL_REF = "vercel:preview:parallax"
GITHUB_CONNECTOR = "github/parallax-runtime"
VERCEL_TOKEN_ENV = "PARALLAX_VERCEL_TOKEN_PARALLAX"

OTHER_REPOSITORY_REF = "github:Ryan9876/other"
OTHER_VERCEL_REF = "vercel:preview:other"
OTHER_GITHUB_CONNECTOR = "github/other-runtime"
OTHER_VERCEL_TOKEN_ENV = "PARALLAX_VERCEL_TOKEN_OTHER"


def _target(
    *,
    repository_ref: str = REPOSITORY_REF,
    vercel_project_ref: str = VERCEL_REF,
    project_id: str = "prj_wLXC5JjjetJf0H97kncRlqczD3OC",
    project_name: str = "parallax",
    github_repo_id: int = 1340272514,
    github_connector: str = GITHUB_CONNECTOR,
    vercel_token_env: str = VERCEL_TOKEN_ENV,
) -> dict[str, object]:
    return {
        "vercel_project_ref": vercel_project_ref,
        "project_id": project_id,
        "project_name": project_name,
        "team_id": "team_JgE8AWWz36uzRbeR6V6EWg9k",
        "repository_ref": repository_ref,
        "github_repo_id": github_repo_id,
        "production_branch": "main",
        "github_connector": github_connector,
        "vercel_token_env": vercel_token_env,
    }


def _targets_json(**overrides: object) -> str:
    return json.dumps([_target(**overrides)])


def _two_targets_json() -> str:
    return json.dumps(
        [
            _target(),
            _target(
                repository_ref=OTHER_REPOSITORY_REF,
                vercel_project_ref=OTHER_VERCEL_REF,
                project_id="prj_4lhve1AXZntfauaGHvkuaGWC6KJX",
                project_name="parallax-api",
                github_repo_id=1340272515,
                github_connector=OTHER_GITHUB_CONNECTOR,
                vercel_token_env=OTHER_VERCEL_TOKEN_ENV,
            ),
        ]
    )


def test_preview_target_registry_binds_canonical_project_to_registered_repository():
    registry = RepositoryPreviewTargetResolver.from_environment(_targets_json())
    binding = ProviderProjectBinding(PROJECT_ID, REPOSITORY_REF)

    target = registry.resolve(binding)
    registration = registry.registration(binding)

    assert target.project_ref == PROJECT_ID
    assert target.repository_ref == REPOSITORY_REF
    assert target.vercel_project_ref == VERCEL_REF
    assert registration.github_connector == GITHUB_CONNECTOR
    assert registration.vercel_token_env == VERCEL_TOKEN_ENV
    assert registration.api_target.vercel_project_ref == VERCEL_REF
    with pytest.raises(ProductionDeliveryConfigurationError, match="no registered"):
        registry.resolve(ProviderProjectBinding(PROJECT_ID, OTHER_REPOSITORY_REF))


def test_preview_target_registry_preserves_distinct_per_target_credential_references():
    registry = RepositoryPreviewTargetResolver.from_environment(_two_targets_json())

    first = registry.registration(ProviderProjectBinding(PROJECT_ID, REPOSITORY_REF))
    second = registry.registration(ProviderProjectBinding(PROJECT_ID, OTHER_REPOSITORY_REF))

    assert first.github_connector == GITHUB_CONNECTOR
    assert first.vercel_token_env == VERCEL_TOKEN_ENV
    assert second.github_connector == OTHER_GITHUB_CONNECTOR
    assert second.vercel_token_env == OTHER_VERCEL_TOKEN_ENV
    assert first.api_target.vercel_project_ref != second.api_target.vercel_project_ref


@pytest.mark.parametrize(
    "value",
    [
        "DATABASE_URL",
        "VERCEL_TOKEN",
        "PARALLAX_VERCEL_TOKEN_",
        "parallax_vercel_token_other",
        "vercel-test-bearer-value",
    ],
)
def test_preview_target_registry_rejects_generic_or_embedded_secret_references(value):
    with pytest.raises(ProductionDeliveryConfigurationError, match="invalid target"):
        RepositoryPreviewTargetResolver.from_environment(_targets_json(vercel_token_env=value))


def test_preview_target_registry_rejects_malformed_connector_reference():
    with pytest.raises(ProductionDeliveryConfigurationError, match="invalid target"):
        RepositoryPreviewTargetResolver.from_environment(_targets_json(github_connector=" bad connector "))


def test_vercel_credential_provider_is_exact_target_scoped_and_redacted():
    provider = EnvironmentVercelCredentialProvider(
        "vercel-test-bearer-value",
        allowed_targets=frozenset({VERCEL_REF}),
    )
    credential = provider.credential_for_project(VERCEL_REF)

    assert credential.kind is ProviderCredentialKind.VERCEL_SCOPED
    assert credential.resource_ref == VERCEL_REF
    assert "vercel-test-bearer-value" not in repr(credential)
    with pytest.raises(ProviderClientError, match="CREDENTIAL_SCOPE_MISMATCH"):
        provider.credential_for_project(OTHER_VERCEL_REF)


def test_github_connect_provider_exchanges_and_verifies_exact_repository_scope():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    connect_calls = []
    scope_calls = []

    def connect_handler(request: httpx.Request) -> httpx.Response:
        connect_calls.append(request)
        assert request.url.path == "/v1/connect/token/github/parallax-runtime"
        assert request.headers["Authorization"] == "Bearer oidc-test-value"
        assert json.loads(request.content) == {
    "subject": {"type": "app"},
    "authorizationDetails": [
        {
            "type": "github_app_installation",
            "repositories": ["Ryan9876/parallax"],
            "permissions": ["contents:write", "metadata:read", "pull_requests:write"],
        }
    ],
}
        return httpx.Response(
            200,
            json={"token": "github-installation-test-token", "expiresAt": expires_at.isoformat()},
        )

    def scope_handler(request: httpx.Request) -> httpx.Response:
        scope_calls.append(request)
        assert request.url.path == "/installation/repositories"
        assert request.url.params["per_page"] == "2"
        assert request.headers["Authorization"] == "Bearer github-installation-test-token"
        assert request.headers["X-GitHub-Api-Version"] == "2026-03-10"
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "repositories": [{"full_name": "Ryan9876/parallax"}],
            },
        )

    provider = VercelConnectGitHubCredentialProvider(
        GITHUB_CONNECTOR,
        oidc_token="oidc-test-value",
        transport=httpx.MockTransport(connect_handler),
        github_transport=httpx.MockTransport(scope_handler),
    )
    first = provider.credential_for_repository(REPOSITORY_REF)
    second = provider.credential_for_repository(REPOSITORY_REF)

    assert first is second
    assert first.kind is ProviderCredentialKind.GITHUB_APP_INSTALLATION
    assert first.resource_ref == REPOSITORY_REF
    assert "github-installation-test-token" not in repr(first)
    assert len(connect_calls) == 1
    assert len(scope_calls) == 1


def test_github_connect_provider_rejects_broader_installation_scope():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    def connect_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"token": "github-broad-test-token", "expiresAt": expires_at.isoformat()},
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
        GITHUB_CONNECTOR,
        oidc_token="oidc-test-value",
        transport=httpx.MockTransport(connect_handler),
        github_transport=httpx.MockTransport(scope_handler),
    )

    with pytest.raises(ProviderClientError, match="CREDENTIAL_SCOPE_MISMATCH"):
        provider.credential_for_repository(REPOSITORY_REF)


def test_github_connect_provider_rejects_noncanonical_repository_ref_before_network():
    provider = VercelConnectGitHubCredentialProvider(
        GITHUB_CONNECTOR,
        oidc_token="oidc-test-value",
        transport=httpx.MockTransport(lambda request: pytest.fail("Connect must not be called")),
        github_transport=httpx.MockTransport(lambda request: pytest.fail("GitHub must not be called")),
    )

    with pytest.raises(ProviderClientError, match="CREDENTIAL_SCOPE_MISMATCH"):
        provider.credential_for_repository("github:Ryan9876/parallax/extra")


class _TrackingEnvironment(dict):
    def __init__(self, values):
        super().__init__(values)
        self.reads = []

    def get(self, key, default=None):
        self.reads.append(key)
        return super().get(key, default)


def test_production_source_delivery_selects_only_canonical_target_credentials(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'multi-target.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    captured = {"github": [], "vercel": []}

    class GitHubCredentials:
        def __init__(self, connector, **kwargs):
            captured["github"].append(connector)

        def credential_for_repository(self, repository_ref):
            raise AssertionError("provider credential should not be used during composition")

    class VercelCredentials:
        def __init__(self, secret, *, allowed_targets):
            captured["vercel"].append((secret, allowed_targets))

        def credential_for_project(self, vercel_project_ref):
            raise AssertionError("provider credential should not be used during composition")

    monkeypatch.setattr(production_delivery_module, "VercelConnectGitHubCredentialProvider", GitHubCredentials)
    monkeypatch.setattr(production_delivery_module, "EnvironmentVercelCredentialProvider", VercelCredentials)

    try:
        project = ProjectRepository(session).create(
            owner_subject=OWNER,
            slug="release-app",
            name="Release App",
            description="release composition test",
            repository_ref=REPOSITORY_REF,
        )
        allocator = SimpleNamespace()
        env = _TrackingEnvironment(
            {
                VERCEL_TOKEN_ENV: "vercel-target-a-secret",
                OTHER_VERCEL_TOKEN_ENV: "vercel-target-b-secret",
            }
        )

        delivery = production_source_delivery(
            session,
            owner_subject=OWNER,
            allocator=allocator,
            project_id=project.id,
            preview_targets_json=_two_targets_json(),
            environment=env,
        )

        assert delivery.bootstrap is not None
        assert delivery.delivery is not None
        assert env.reads == [VERCEL_TOKEN_ENV]
        assert captured["github"] == [GITHUB_CONNECTOR]
        assert captured["vercel"] == [
            ("vercel-target-a-secret", frozenset({VERCEL_REF}))
        ]
        vercel_client = delivery.delivery.vercel.client
        assert set(vercel_client._targets) == {VERCEL_REF}
    finally:
        session.close()


def test_production_source_delivery_second_project_uses_distinct_credentials(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'second-target.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    captured = {"github": [], "vercel": []}

    class GitHubCredentials:
        def __init__(self, connector, **kwargs):
            captured["github"].append(connector)

        def credential_for_repository(self, repository_ref):
            raise AssertionError("provider credential should not be used during composition")

    class VercelCredentials:
        def __init__(self, secret, *, allowed_targets):
            captured["vercel"].append((secret, allowed_targets))

        def credential_for_project(self, vercel_project_ref):
            raise AssertionError("provider credential should not be used during composition")

    monkeypatch.setattr(production_delivery_module, "VercelConnectGitHubCredentialProvider", GitHubCredentials)
    monkeypatch.setattr(production_delivery_module, "EnvironmentVercelCredentialProvider", VercelCredentials)

    try:
        project = ProjectRepository(session).create(
            owner_subject=OWNER,
            slug="other-app",
            name="Other App",
            description="second release composition test",
            repository_ref=OTHER_REPOSITORY_REF,
        )
        env = _TrackingEnvironment(
            {
                VERCEL_TOKEN_ENV: "vercel-target-a-secret",
                OTHER_VERCEL_TOKEN_ENV: "vercel-target-b-secret",
            }
        )

        delivery = production_source_delivery(
            session,
            owner_subject=OWNER,
            allocator=SimpleNamespace(),
            project_id=project.id,
            preview_targets_json=_two_targets_json(),
            environment=env,
        )

        assert delivery.bootstrap is not None
        assert env.reads == [OTHER_VERCEL_TOKEN_ENV]
        assert captured["github"] == [OTHER_GITHUB_CONNECTOR]
        assert captured["vercel"] == [
            ("vercel-target-b-secret", frozenset({OTHER_VERCEL_REF}))
        ]
        assert set(delivery.delivery.vercel.client._targets) == {OTHER_VERCEL_REF}
    finally:
        session.close()


def test_production_source_delivery_requires_exact_server_configuration(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'release.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        project = ProjectRepository(session).create(
            owner_subject=OWNER,
            slug="release-app",
            name="Release App",
            description="release composition test",
            repository_ref=REPOSITORY_REF,
        )
        allocator = SimpleNamespace()

        with pytest.raises(ProductionDeliveryConfigurationError, match="target registry"):
            production_source_delivery(
                session,
                owner_subject=OWNER,
                allocator=allocator,
                project_id=project.id,
                preview_targets_json=None,
                environment={VERCEL_TOKEN_ENV: "vercel-test-bearer-value"},
            )

        with pytest.raises(ProductionDeliveryConfigurationError, match="invalid target"):
            production_source_delivery(
                session,
                owner_subject=OWNER,
                allocator=allocator,
                project_id=project.id,
                preview_targets_json=_targets_json(github_connector=""),
                environment={VERCEL_TOKEN_ENV: "vercel-test-bearer-value"},
            )

        with pytest.raises(ProductionDeliveryConfigurationError, match="unavailable for registered target"):
            production_source_delivery(
                session,
                owner_subject=OWNER,
                allocator=allocator,
                project_id=project.id,
                preview_targets_json=_targets_json(),
                environment={},
            )

        delivery = production_source_delivery(
            session,
            owner_subject=OWNER,
            allocator=allocator,
            project_id=project.id,
            preview_targets_json=_targets_json(),
            environment={VERCEL_TOKEN_ENV: "vercel-test-bearer-value"},
        )
        assert delivery.bootstrap is not None
        assert delivery.delivery is not None
    finally:
        session.close()


def _route_run(project_id: str):
    return SimpleNamespace(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        spec_id="P2-V0.15.12",
        project_id=project_id,
        work_specification_id=None,
        work_specification_revision=None,
        work_specification_digest=None,
        state="PLAN",
        resume_stage=None,
        revision=2,
        workspace_ref=f"project:{project_id}",
        last_failure_code=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        completed_at=None,
        attempts=[],
    )


class _RouteService:
    def __init__(self, run):
        self.run = run
        self.owner_subject = OWNER
        self.runs = SimpleNamespace(session=object())

    def get(self, run_id):
        assert run_id == self.run.id
        return self.run

    def acceptance_map_for_run(self, run):
        return []


def test_autonomous_route_injects_source_delivery_when_durable_runtime_is_active(monkeypatch):
    run = _route_run(PROJECT_ID)
    svc = _RouteService(run)
    allocator = object()
    delivery = SimpleNamespace(bootstrap=object(), delivery=object())
    captured = {}

    monkeypatch.setattr(engineering_routes, "VercelSandboxExecutor", lambda: object())

    def build_delivery(session, *, owner_subject, allocator, project_id):
        captured["factory"] = (session, owner_subject, allocator, project_id)
        return delivery

    class Runtime:
        def __init__(self, service, actual_allocator, legacy_executor, *, source_delivery=None, **kwargs):
            captured["runtime"] = (service, actual_allocator, source_delivery)

        def run(self, *, run_id, operation_key, expected_revision):
            assert run_id == run.id
            assert operation_key == "release-route"
            assert expected_revision == run.revision
            return AutonomyResult(run=run, stop_reason=AutonomyStopReason.REVIEW_REQUIRED, steps=())

    monkeypatch.setattr(engineering_routes, "production_source_delivery", build_delivery)
    monkeypatch.setattr(engineering_routes, "EngineeringRuntimeComposition", Runtime)

    result = engineering_routes.autonomous(
        run.id,
        EngineeringOperation(operation_key="release-route", expected_revision=run.revision),
        svc=svc,
        allocator=allocator,
    )

    assert result["stop_reason"] == AutonomyStopReason.REVIEW_REQUIRED.value
    assert captured["factory"] == (svc.runs.session, OWNER, allocator, PROJECT_ID)
    assert captured["runtime"] == (svc, allocator, delivery)


def test_autonomous_route_missing_delivery_configuration_returns_503_without_runtime(monkeypatch):
    run = _route_run(PROJECT_ID)
    svc = _RouteService(run)
    allocator = object()
    constructed = False

    monkeypatch.setattr(engineering_routes, "VercelSandboxExecutor", lambda: object())

    def unavailable(*args, **kwargs):
        raise ProductionDeliveryConfigurationError("provider configuration unavailable")

    class Runtime:
        def __init__(self, *args, **kwargs):
            nonlocal constructed
            constructed = True

    monkeypatch.setattr(engineering_routes, "production_source_delivery", unavailable)
    monkeypatch.setattr(engineering_routes, "EngineeringRuntimeComposition", Runtime)

    with pytest.raises(HTTPException) as failure:
        engineering_routes.autonomous(
            run.id,
            EngineeringOperation(operation_key="release-route", expected_revision=run.revision),
            svc=svc,
            allocator=allocator,
        )

    assert failure.value.status_code == 503
    assert constructed is False
