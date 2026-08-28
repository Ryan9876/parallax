from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.autonomy import AutonomyStopReason
from parallax_api.code.delivery_readiness import (
    VercelProjectReadinessRestClient,
    _provisioning_profile,
)
from parallax_api.code.runtime_composition import EngineeringRuntimeComposition
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import ProjectRunIdentity, SourcePackage
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.tools.providers.common import ProviderClientError
from parallax_api.code.production_delivery import (
    EnvironmentVercelCredentialProvider,
    ProductionDeliveryConfigurationError,
)


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
REPOSITORY_REF = "github:Ryan9876/ot-time"
TEAM_ID = "team_JgE8AWWz36uzRbeR6V6EWg9k"
READINESS_REF = f"readiness:{TEAM_ID}"
TOKEN = "vercel-readiness-test-token"
OWNER = "owner:w8-delivery-readiness"


def _credentials() -> EnvironmentVercelCredentialProvider:
    return EnvironmentVercelCredentialProvider(
        TOKEN,
        allowed_targets=frozenset({READINESS_REF}),
    )


def _project_payload(*, project_id: str = "prj_ot_time", account_id: str = TEAM_ID):
    return {
        "id": project_id,
        "name": "ot-time-px-11111111",
        "accountId": account_id,
        "link": {"type": "github", "repoId": 424242},
    }


def test_creation_conflict_reconciles_to_one_exact_verified_target():
    list_calls = 0
    post_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal list_calls, post_calls
        assert request.url.params.get("teamId") == TEAM_ID
        if request.url.path == "/v9/projects":
            list_calls += 1
            projects = [] if list_calls == 1 else [_project_payload()]
            return httpx.Response(200, json={"projects": projects, "pagination": {"next": None}})
        if request.url.path == "/v11/projects":
            post_calls += 1
            return httpx.Response(409, json={"error": {"code": "project_already_exists"}})
        if request.url.path == "/v9/projects/prj_ot_time":
            return httpx.Response(200, json=_project_payload())
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = VercelProjectReadinessRestClient(
        _credentials(),
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
    assert list_calls == 2
    assert post_calls == 1


def test_exact_repository_match_with_wrong_team_readback_fails_closed():
    mutation_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal mutation_count
        if request.method != "GET":
            mutation_count += 1
        if request.url.path == "/v9/projects":
            return httpx.Response(
                200,
                json={"projects": [_project_payload()], "pagination": {"next": None}},
            )
        if request.url.path == "/v9/projects/prj_ot_time":
            return httpx.Response(
                200,
                json=_project_payload(account_id="team_wrong_scope"),
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = VercelProjectReadinessRestClient(
        _credentials(),
        credential_ref=READINESS_REF,
        team_id=TEAM_ID,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderClientError, match="TARGET_SCOPE_MISMATCH"):
        client.ensure(
            repository_ref=REPOSITORY_REF,
            github_repo_id=424242,
            production_branch="main",
            project_name="ot-time-px-11111111",
        )
    assert mutation_count == 0


def test_provider_auth_denial_fails_before_project_mutation():
    mutation_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal mutation_count
        if request.method != "GET":
            mutation_count += 1
        return httpx.Response(403, json={"error": {"code": "forbidden"}})

    client = VercelProjectReadinessRestClient(
        _credentials(),
        credential_ref=READINESS_REF,
        team_id=TEAM_ID,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderClientError, match="PROVIDER_AUTH_DENIED"):
        client.ensure(
            repository_ref=REPOSITORY_REF,
            github_repo_id=424242,
            production_branch="main",
            project_name="ot-time-px-11111111",
        )
    assert mutation_count == 0


def test_conflicting_server_owned_provisioning_profiles_fail_closed():
    encoded = json.dumps(
        [
            {
                "vercel_project_ref": "vercel:preview:one",
                "project_id": "prj_one",
                "project_name": "one",
                "team_id": TEAM_ID,
                "repository_ref": "github:Ryan9876/parallax",
                "github_repo_id": 1001,
                "production_branch": "main",
                "github_connector": "github/parallax-runtime",
                "vercel_token_env": "PARALLAX_VERCEL_TOKEN_PARALLAX",
            },
            {
                "vercel_project_ref": "vercel:preview:two",
                "project_id": "prj_two",
                "project_name": "two",
                "team_id": "team_conflicting",
                "repository_ref": "github:Ryan9876/other",
                "github_repo_id": 1002,
                "production_branch": "main",
                "github_connector": "github/other-runtime",
                "vercel_token_env": "PARALLAX_VERCEL_TOKEN_OTHER",
            },
        ]
    )
    with pytest.raises(ProductionDeliveryConfigurationError, match="profile is ambiguous"):
        _provisioning_profile(encoded)


class _StarterSource:
    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        return SourcePackage(
            source_kind="starter",
            source_ref="w8-plan-source",
            files={"app.py": b"value = 1\n"},
        )


class _ProbeExecutor:
    def probe(self, *, operation_key: str):
        return {
            "tool_id": "python",
            "protected_success": True,
            "exit_code": 0,
            "duration_ms": 1,
            "stdout_excerpt": "ready",
            "stderr_excerpt": "",
            "executor": "w8-test",
            "network_policy": "deny-all",
            "persistent": False,
        }

    def execute(self, spec):
        raise AssertionError("one-step PLAN proof must not reach execution stages")


class _ExistingBootstrap:
    def __init__(self):
        self.calls = 0

    def ensure(self, run, *, operation_key: str):
        self.calls += 1
        return SimpleNamespace(initialized=False)


class _ForbiddenPreviewDelivery:
    def __init__(self):
        self.calls = 0

    def deliver(self, run, *, operation_key: str):
        self.calls += 1
        raise AssertionError("PLAN must not require Vercel Preview delivery")

    def resolve_record(self, run):
        return None


def test_durable_plan_advances_to_implement_without_preview_target(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'w8-plan.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        projects = ProjectRepository(session)
        project = projects.create(
            owner_subject=OWNER,
            slug="w8-plan-no-preview",
            name="W8 Plan No Preview",
            description=None,
            repository_ref=REPOSITORY_REF,
        )
        conversations = ConversationRepository(session)
        specifications = WorkSpecificationRepository(session)
        conversation = conversations.create("code", spec_id="P2-V0.21.1", project_id=project.id)
        draft = specifications.create_draft(
            conversation_id=conversation.id,
            draft=WorkSpecificationDraft(
                title="Advance PLAN without hosting registration",
                objective="Prove protected PLAN is durable without a Vercel Preview target.",
                constraints=["Do not resolve or create a Preview target during PLAN."],
                acceptance_criteria=[
                    "PLAN advances durably to IMPLEMENT.",
                    "No Vercel Preview delivery is invoked while PLAN advances.",
                ],
                risks=["A hidden hosting prerequisite could block PLAN."],
                open_questions=[],
                confidence=0.99,
                program_version="w8-s2-test",
            ),
            model_id="test-model",
        )
        approved = specifications.approve(draft)
        service = EngineeringRunService(
            EngineeringRunRepository(session),
            conversations,
            specifications,
            projects,
            owner_subject=OWNER,
            require_project_binding=True,
        )
        run = service.activate_run(
            conversation_id=conversation.id,
            work_specification_id=approved.id,
        )
        assert run.state == "PLAN"

        allocator = ProjectWorkspaceAllocator(tmp_path / "lineage")
        identity = ProjectRunIdentity(project_id=project.id, run_id=run.id)
        materialized = allocator.initialize(identity, _StarterSource())
        allocator.cleanup(materialized)

        bootstrap = _ExistingBootstrap()
        delivery = _ForbiddenPreviewDelivery()
        runtime = EngineeringRuntimeComposition(
            service,
            allocator,
            _ProbeExecutor(),
            lineage_executor=SimpleNamespace(),
            source_delivery=SimpleNamespace(bootstrap=bootstrap, delivery=delivery),
        )
        # Isolate the PLAN transition. Production can continue in the same
        # request; this acceptance proof specifically asserts the durable PLAN
        # boundary before any later implementation or Preview work.
        runtime.coordinator.max_steps = 1
        result = runtime.run(
            run_id=run.id,
            operation_key="w8-s2:plan-no-preview",
            expected_revision=run.revision,
        )

        refreshed = service.get(run.id)
        assert result.stop_reason is AutonomyStopReason.MAX_STEPS_REACHED
        assert refreshed.state == "IMPLEMENT"
        assert refreshed.revision == run.revision + 1
        plan_attempts = [item for item in refreshed.attempts if item.stage == "PLAN"]
        assert len(plan_attempts) == 1
        assert plan_attempts[0].status == "PASSED"
        assert bootstrap.calls == 1
        assert delivery.calls == 0
    finally:
        session.close()
