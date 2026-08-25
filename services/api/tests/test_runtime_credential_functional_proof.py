from __future__ import annotations

import base64
from hashlib import sha256
import json

import httpx
from sqlalchemy.orm import sessionmaker

from parallax_api.code import production_delivery as production_delivery_module
from parallax_api.code.autonomy import AutonomyStopReason
from parallax_api.code.lineage_persistence import (
    InMemoryImmutableObjectStore,
    InMemoryLineageMetadataStore,
)
from parallax_api.code.production_delivery import production_source_delivery
from parallax_api.code.runtime_composition import EngineeringRuntimeComposition
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import ProjectRunIdentity, SourceLineageStore
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.tools.providers.github_client import GitHubRestProviderClient


OWNER = "owner:runtime-credential-functional-proof"
REPOSITORY_REF = "github:Ryan9876/parallax"
CONNECTOR = "github/parallax-runtime"
VERCEL_REF = "vercel:preview:parallax"
VERCEL_TOKEN_ENV = "PARALLAX_VERCEL_TOKEN_PARALLAX"
RUNTIME_OIDC = "runtime-oidc-functional-proof"
REVISION = "a" * 40
BLOB_REVISION = "b" * 40
SOURCE_PATH = "src/app.py"
SOURCE_BYTES = b"print('protected bootstrap proof')\n"


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


class _PlanBoundaryExecutor:
    def __init__(self) -> None:
        self.probes: list[str] = []

    def probe(self, *, operation_key: str) -> dict[str, object]:
        self.probes.append(operation_key)
        return {
            "tool_id": "python",
            "exit_code": 0,
            "duration_ms": 1,
            "stdout_excerpt": "PARALLAX_SANDBOX_READY",
            "stderr_excerpt": "",
            "protected_success": True,
            "executor": "protected-production-like-proof",
            "network_policy": "deny-all",
            "persistent": False,
        }

    def execute(self, spec: object) -> dict[str, object]:
        raise AssertionError("functional proof must not execute BUILD/TEST/VERIFY")


def test_runtime_oidc_bootstraps_canonical_repository_then_advances_beyond_plan(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'functional-proof.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()

    connect_calls: list[httpx.Request] = []
    scope_calls: list[httpx.Request] = []
    repository_calls: list[httpx.Request] = []

    def connect_handler(request: httpx.Request) -> httpx.Response:
        connect_calls.append(request)
        assert request.url.raw_path == b"/v1/connect/token/github%2Fparallax-runtime"
        assert request.headers["Authorization"] == f"Bearer {RUNTIME_OIDC}"
        return httpx.Response(
            200,
            json={
                "token": "github-installation-functional-proof",
                "expiresAt": "2099-01-01T00:00:00+00:00",
            },
        )

    def scope_handler(request: httpx.Request) -> httpx.Response:
        scope_calls.append(request)
        assert request.url.path == "/installation/repositories"
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "repositories": [{"full_name": "Ryan9876/parallax"}],
            },
        )

    def repository_handler(request: httpx.Request) -> httpx.Response:
        repository_calls.append(request)
        assert request.headers["Authorization"] == "Bearer github-installation-functional-proof"
        path = request.url.path
        if path == "/repos/Ryan9876/parallax":
            return httpx.Response(
                200,
                json={"full_name": "Ryan9876/parallax", "default_branch": "main"},
            )
        if path == "/repos/Ryan9876/parallax/git/ref/heads/main":
            return httpx.Response(200, json={"object": {"sha": REVISION}})
        if path == f"/repos/Ryan9876/parallax/git/trees/{REVISION}":
            assert request.url.params["recursive"] == "1"
            return httpx.Response(
                200,
                json={
                    "truncated": False,
                    "tree": [
                        {
                            "path": SOURCE_PATH,
                            "sha": BLOB_REVISION,
                            "type": "blob",
                            "mode": "100644",
                            "size": len(SOURCE_BYTES),
                        }
                    ],
                },
            )
        if path == f"/repos/Ryan9876/parallax/contents/{SOURCE_PATH}":
            assert request.url.params["ref"] == REVISION
            return httpx.Response(
                200,
                json={
                    "type": "file",
                    "encoding": "base64",
                    "path": SOURCE_PATH,
                    "size": len(SOURCE_BYTES),
                    "content": base64.b64encode(SOURCE_BYTES).decode("ascii"),
                },
            )
        raise AssertionError(f"unexpected GitHub request: {request.method} {request.url}")

    repository_transport = httpx.MockTransport(repository_handler)
    real_client = GitHubRestProviderClient

    def github_client(credentials):
        return real_client(credentials, transport=repository_transport)

    monkeypatch.setattr(production_delivery_module, "GitHubRestProviderClient", github_client)

    try:
        projects = ProjectRepository(session)
        conversations = ConversationRepository(session)
        runs = EngineeringRunRepository(session)
        work_specs = WorkSpecificationRepository(session)
        project = projects.create(
            owner_subject=OWNER,
            slug="runtime-credential-functional-proof",
            name="Runtime credential functional proof",
            description="Protected production-like repository bootstrap proof",
            repository_ref=REPOSITORY_REF,
        )
        conversation = conversations.create(
            "code",
            spec_id="P2-V0.13.0",
            project_id=project.id,
        )
        draft = WorkSpecificationDraft(
            title="Runtime credential functional proof",
            objective="Bootstrap the canonical repository and advance protected autonomy beyond PLAN.",
            constraints=["Advance into IMPLEMENT without provider publication or BUILD/TEST/VERIFY execution."],
            acceptance_criteria=[
                "Canonical repository source is bootstrapped through the scoped runtime credential path.",
                "Autonomous execution advances beyond PLAN without provider writes.",
            ],
            risks=["Credential authority could broaden if the registered repository scope is bypassed."],
            open_questions=[],
            confidence=0.99,
            program_version="runtime-credential-functional-proof",
        )
        specification = work_specs.create_draft(
            conversation_id=conversation.id,
            draft=draft,
            model_id="protected-test-model",
        )
        specification = work_specs.approve(specification)
        service = EngineeringRunService(
            runs,
            conversations,
            work_specs,
            projects,
            owner_subject=OWNER,
            require_project_binding=True,
        )
        run = service.activate_run(
            conversation_id=conversation.id,
            work_specification_id=specification.id,
        )
        assert run.state == "PLAN"

        lineage_store = SourceLineageStore(
            InMemoryImmutableObjectStore(),
            InMemoryLineageMetadataStore(),
        )
        allocator = ProjectWorkspaceAllocator(tmp_path / "materialized", lineage_store=lineage_store)
        source_delivery = production_source_delivery(
            session,
            owner_subject=OWNER,
            allocator=allocator,
            project_id=project.id,
            preview_targets_json=_targets_json(),
            environment={VERCEL_TOKEN_ENV: "vercel-preview-scoped-proof-token"},
            oidc_token=RUNTIME_OIDC,
            github_transport=httpx.MockTransport(connect_handler),
            github_scope_transport=httpx.MockTransport(scope_handler),
        )
        executor = _PlanBoundaryExecutor()
        runtime = EngineeringRuntimeComposition(
            service,
            allocator,
            executor,
            source_delivery=source_delivery,
        )

        result = runtime.run(
            run_id=run.id,
            operation_key="runtime-credential-functional-proof",
            expected_revision=run.revision,
        )

        # The real production composition installs the protected implementation
        # runtime. This proof intentionally supplies no implementation proposal,
        # so the bounded run must cross PLAN into IMPLEMENT and then fail closed
        # before mutation rather than stopping at the legacy implementation seam.
        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED
        assert result.run.state == "IMPLEMENT"
        assert [step.stage for step in result.steps] == ["EXECUTOR", "PLAN", "IMPLEMENT"]
        assert result.steps[-1].outcome == "FAILED"
        assert executor.probes == ["runtime-credential-functional-proof:executor-probe:1"]
        lineage = allocator.current_lineage(ProjectRunIdentity(project.id, run.id))
        assert lineage.project_id == project.id
        assert lineage.run_id == run.id
        assert lineage.source_kind == "repository"
        assert lineage.parent_lineage_id is None
        assert lineage.file_count == 1
        assert lineage.total_bytes == len(SOURCE_BYTES)
        assert lineage.files[0].path == SOURCE_PATH
        assert lineage.files[0].sha256 == sha256(SOURCE_BYTES).hexdigest()
        assert len(connect_calls) == 1
        assert len(scope_calls) == 1
        assert [request.method for request in repository_calls] == ["GET", "GET", "GET", "GET"]
        assert all(request.method == "GET" for request in repository_calls)
        assert runtime.last_delivery_result is None
    finally:
        session.close()
        engine.dispose()
