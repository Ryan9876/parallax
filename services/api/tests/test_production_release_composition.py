from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

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


def _targets_json(repository_ref: str = REPOSITORY_REF) -> str:
    return json.dumps(
        [
            {
                "vercel_project_ref": VERCEL_REF,
                "project_id": "prj_wLXC5JjjetJf0H97kncRlqczD3OC",
                "project_name": "parallax",
                "team_id": "team_JgE8AWWz36uzRbeR6V6EWg9k",
                "repository_ref": repository_ref,
                "github_repo_id": 1340272514,
                "production_branch": "main",
            }
        ]
    )


def test_preview_target_registry_binds_canonical_project_to_registered_repository():
    registry = RepositoryPreviewTargetResolver.from_environment(_targets_json())
    binding = ProviderProjectBinding(PROJECT_ID, REPOSITORY_REF)

    target = registry.resolve(binding)

    assert target.project_ref == PROJECT_ID
    assert target.repository_ref == REPOSITORY_REF
    assert target.vercel_project_ref == VERCEL_REF
    with pytest.raises(ProductionDeliveryConfigurationError, match="no registered"):
        registry.resolve(ProviderProjectBinding(PROJECT_ID, "github:Ryan9876/other"))


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
        provider.credential_for_project("vercel:preview:other")


def test_github_connect_provider_exchanges_oidc_for_short_lived_app_credential():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.path == "/v1/connect/token/github/parallax-runtime"
        assert request.headers["Authorization"] == "Bearer oidc-test-value"
        assert json.loads(request.content) == {"subject": {"type": "app"}}
        return httpx.Response(
            200,
            json={"token": "github-installation-test-token", "expiresAt": expires_at.isoformat()},
        )

    provider = VercelConnectGitHubCredentialProvider(
        "github/parallax-runtime",
        oidc_token="oidc-test-value",
        transport=httpx.MockTransport(handler),
    )
    first = provider.credential_for_repository(REPOSITORY_REF)
    second = provider.credential_for_repository(REPOSITORY_REF)

    assert first is second
    assert first.kind is ProviderCredentialKind.GITHUB_APP_INSTALLATION
    assert first.resource_ref == REPOSITORY_REF
    assert "github-installation-test-token" not in repr(first)
    assert len(calls) == 1


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
                github_connector="github/parallax-runtime",
                vercel_token="vercel-test-bearer-value",
                preview_targets_json=None,
            )

        with pytest.raises(ProductionDeliveryConfigurationError, match="GitHub Connect"):
            production_source_delivery(
                session,
                owner_subject=OWNER,
                allocator=allocator,
                project_id=project.id,
                github_connector="",
                vercel_token="vercel-test-bearer-value",
                preview_targets_json=_targets_json(),
            )

        delivery = production_source_delivery(
            session,
            owner_subject=OWNER,
            allocator=allocator,
            project_id=project.id,
            github_connector="github/parallax-runtime",
            vercel_token="vercel-test-bearer-value",
            preview_targets_json=_targets_json(),
        )
        assert delivery.bootstrap is not None
        assert delivery.delivery is not None
    finally:
        session.close()


def _route_run(project_id: str):
    return SimpleNamespace(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        spec_id="P2-V0.15.11",
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
