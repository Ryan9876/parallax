from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.orm import sessionmaker

from parallax_api.code.autonomy import AutonomyCoordinator
from parallax_api.code.implementation_runtime import ProtectedImplementationRuntime, RunProjectBinding
from parallax_api.code.lineage_persistence import InMemoryImmutableObjectStore, InMemoryLineageMetadataStore
from parallax_api.code.runtime_composition import AllocatorWorkspaceLineageGateway
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.worker_service import WorkerRecoveryService
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import ProjectRunIdentity, SourceLineageStore, SourcePackage
from parallax_api.db import Base, make_engine
from parallax_api.evaluation.app_builder import load_app_builder_suite
from parallax_api.evaluation.runtime_evidence import (
    PersistedProviderActionFact,
    PersistedVerifiedDelivery,
    RuntimeAppBuilderEvidenceAdapter,
)
from parallax_api.evaluation.wave3_reference import (
    ProtectedWave3ReferenceAppHarness,
    Wave3ReferenceRuntimeContext,
)
from parallax_api.intelligence.implementation_generation import GeneratedSourcePatch, ImplementationProposal
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.worker_executions import WorkerExecutionRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.tools import ToolActionPolicy, ToolCapability, ToolCapabilityRegistry, ToolConsequence
from parallax_api.tools.providers.common import AcceptedSourceLineage, ProviderInvocation, ProviderProjectBinding
from parallax_api.tools.providers.github import (
    ACTION_BRANCH_CREATE,
    ACTION_COMMIT_WRITE,
    ACTION_PULL_REQUEST_CREATE,
    GitHubBranchResult,
    GitHubCommitFile,
    GitHubCommitResult,
    GitHubProviderActions,
    GitHubPullRequestResult,
)
from parallax_api.tools.providers.vercel import (
    ACTION_PREVIEW_CREATE,
    VercelPreviewActions,
    VercelPreviewResult,
    VercelPreviewStatus,
    VercelPreviewTarget,
)

OWNER = "owner:wave3-reference"
REPOSITORY_REF = "github:acme/wave3-reference-app"
BASE_REVISION = "1" * 40
VERCEL_PROJECT = "vercel:project:wave3-reference-app"
INITIAL_SOURCE = "value = 1\n"
UPDATED_SOURCE = "value = 2\n"


class StaticSourceProvider:
    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        return SourcePackage(
            source_kind="repository",
            source_ref=f"{REPOSITORY_REF}@{BASE_REVISION}",
            files={"app.py": INITIAL_SOURCE.encode("utf-8")},
        )


class FixedGenerator:
    def generate_sync(self, request):
        return SimpleNamespace(
            proposal=ImplementationProposal(
                acceptance_ids_covered=list(request.required_acceptance_ids),
                patches=[
                    GeneratedSourcePatch(
                        path="app.py",
                        expected_base_sha256=sha256(INITIAL_SOURCE.encode("utf-8")).hexdigest(),
                        unified_diff=(
                            "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n"
                            f"-{INITIAL_SOURCE.rstrip()}\n+{UPDATED_SOURCE.rstrip()}\n"
                        ),
                    )
                ],
            ),
            model="wave3-reference-model",
            program_version="wave3-reference-generator-v1",
        )


class NeverLegacyExecutor:
    def probe(self, *, operation_key: str):
        raise AssertionError("legacy executor probe must not run after protected PLAN")

    def execute(self, spec):
        raise AssertionError("legacy executor must not run after accepted IMPLEMENT lineage")


class ReconstructingLineageExecutor:
    def __init__(self, allocator: ProjectWorkspaceAllocator):
        self.allocator = allocator

    def execute_on_lineage(self, spec, *, project_ref: str, run_id: str, source_lineage_ref: str):
        workspace = self.allocator.reconstruct(ProjectRunIdentity(project_ref, run_id), source_lineage_ref)
        try:
            lineage = workspace.lineage
            assert (workspace.path / "app.py").read_text(encoding="utf-8") == UPDATED_SOURCE
            return {
                "tool_id": spec.tool_id,
                "invocation_digest": "a" * 64,
                "exit_code": 0,
                "duration_ms": 1,
                "stdout_digest": "b" * 64,
                "stdout_excerpt": "wave3-reference-ok",
                "stderr_digest": "c" * 64,
                "stderr_excerpt": "",
                "timed_out": False,
                "redacted": True,
                "artifacts": [],
                "protected_success": True,
                "executor": "wave3-reference-lineage-test",
                "network_policy": "deny-all",
                "persistent": False,
                "lineage_source_transfer": True,
                "source_content_digest": lineage.content_digest,
                "source_file_count": lineage.file_count,
                "source_total_bytes": lineage.total_bytes,
                "fresh_repository_checkout": False,
                "git_source": False,
            }
        finally:
            self.allocator.cleanup(workspace)


class FakeGitHubPublishClient:
    def __init__(self, counters: dict[str, int]):
        self.counters = counters

    def create_branch(self, repository_ref: str, branch_name: str, base_revision: str):
        self.counters["branch"] += 1
        return GitHubBranchResult(repository_ref, branch_name, base_revision, base_revision)

    def commit_files(self, repository_ref, branch_name, expected_parent_revision, lineage, files):
        self.counters["commit"] += 1
        assert files and files[0].path == "app.py"
        revision = sha256(f"{lineage.lineage_id}:{lineage.content_digest}".encode()).hexdigest()[:40]
        return GitHubCommitResult(
            repository_ref,
            branch_name,
            expected_parent_revision,
            revision,
            lineage.lineage_id,
            lineage.content_digest,
        )

    def create_pull_request(self, repository_ref, head_branch, expected_head_revision, base_branch, title, body):
        self.counters["pr"] += 1
        return GitHubPullRequestResult(
            repository_ref,
            99,
            head_branch,
            expected_head_revision,
            base_branch,
            "OPEN",
            "https://github.com/acme/wave3-reference-app/pull/99",
        )


class FakeVercelPublishClient:
    def __init__(self, counters: dict[str, int]):
        self.counters = counters

    def create_preview(self, vercel_project_ref, repository_ref, source_revision, branch_name, lineage):
        self.counters["preview"] += 1
        return VercelPreviewResult(
            vercel_project_ref,
            repository_ref,
            "dpl_wave3_reference_99",
            source_revision,
            VercelPreviewStatus.READY,
            "https://wave3-reference-parallax.vercel.app",
        )


class DeterministicDeliveryDriver:
    def __init__(self, object_store, metadata_store):
        self.object_store = object_store
        self.metadata_store = metadata_store
        self.records: dict[tuple[str, str, str], PersistedVerifiedDelivery] = {}
        self.counters = {"branch": 0, "commit": 0, "pr": 0, "preview": 0}

    def _lineage_store(self):
        return SourceLineageStore(self.object_store, self.metadata_store)

    def ensure_bootstrap(self, *, project_id: str, run_id: str, repository_ref: str) -> str:
        assert repository_ref == REPOSITORY_REF
        return self._lineage_store().initialize(
            ProjectRunIdentity(project_id, run_id), StaticSourceProvider()
        ).lineage_id

    @staticmethod
    def _registry(project_id: str) -> ToolCapabilityRegistry:
        return ToolCapabilityRegistry(
            (
                ToolCapability(
                    capability_id="cap:github:wave3-reference",
                    project_ref=project_id,
                    tool="github",
                    actions=(
                        ToolActionPolicy(ACTION_BRANCH_CREATE, ToolConsequence.MUTATE),
                        ToolActionPolicy(ACTION_COMMIT_WRITE, ToolConsequence.MUTATE),
                        ToolActionPolicy(ACTION_PULL_REQUEST_CREATE, ToolConsequence.MUTATE),
                    ),
                ),
                ToolCapability(
                    capability_id="cap:vercel:wave3-reference",
                    project_ref=project_id,
                    tool="vercel",
                    actions=(ToolActionPolicy(ACTION_PREVIEW_CREATE, ToolConsequence.MUTATE),),
                ),
            )
        )

    @staticmethod
    def _invoke(capability: str, request: str) -> ProviderInvocation:
        return ProviderInvocation(request_id=request, capability_id=capability, actor_ref="actor:wave3-reference")

    def deliver_verified_source(self, *, project_id: str, run_id: str, lineage_id: str):
        key = (project_id, run_id, lineage_id)
        existing = self.records.get(key)
        if existing is not None:
            replayed = replace(existing, publication_replayed=True)
            self.records[key] = replayed
            return replayed

        store = self._lineage_store()
        lineage = store.resolve(ProjectRunIdentity(project_id, run_id), lineage_id)
        accepted = AcceptedSourceLineage(project_id, run_id, lineage.lineage_id, lineage.content_digest)
        registry = self._registry(project_id)
        github = GitHubProviderActions(registry, FakeGitHubPublishClient(self.counters))
        vercel = VercelPreviewActions(registry, FakeVercelPublishClient(self.counters))
        binding = ProviderProjectBinding(project_id, REPOSITORY_REF)
        branch_name = f"parallax/wave3-reference-{run_id[:8]}"

        branch = github.create_branch(
            binding,
            self._invoke("cap:github:wave3-reference", f"req:branch:{run_id}"),
            branch_name=branch_name,
            base_revision=BASE_REVISION,
        )
        source = store.object_store.get(lineage.files[0].sha256)
        commit = github.commit_accepted_lineage(
            binding,
            self._invoke("cap:github:wave3-reference", f"req:commit:{run_id}"),
            branch_name=branch_name,
            expected_parent_revision=BASE_REVISION,
            lineage=accepted,
            files=(GitHubCommitFile("app.py", source.decode("utf-8"), lineage.files[0].sha256),),
        )
        pr = github.create_pull_request(
            binding,
            self._invoke("cap:github:wave3-reference", f"req:pr:{run_id}"),
            head_branch=branch_name,
            expected_head_revision=commit.value.commit_revision,
            base_branch="main",
            lineage=accepted,
            title="Parallax Wave 3 protected reference app",
            body="Verified source lineage Wave 3 reference proof.",
        )
        preview = vercel.create_preview(
            VercelPreviewTarget(project_id, REPOSITORY_REF, VERCEL_PROJECT),
            self._invoke("cap:vercel:wave3-reference", f"req:preview:{run_id}"),
            source_revision=commit.value.commit_revision,
            branch_name=branch_name,
            lineage=accepted,
        )
        record = PersistedVerifiedDelivery(
            project_id=project_id,
            run_id=run_id,
            repository_ref=REPOSITORY_REF,
            lineage_id=lineage.lineage_id,
            content_digest=lineage.content_digest,
            expected_parent_revision=BASE_REVISION,
            published_revision=commit.value.commit_revision,
            pull_request_identity=pr.evidence.result_identity or "",
            preview_deployment_id=preview.value.deployment_id,
            preview_status=preview.value.status.value,
            actions=tuple(
                PersistedProviderActionFact(result.evidence, result.audit)
                for result in (branch, commit, pr, preview)
            ),
            publication_replayed=False,
        )
        self.records[key] = record
        return record

    def get_verified_delivery(self, *, project_id: str, run_id: str, lineage_id: str):
        return self.records.get((project_id, run_id, lineage_id))


class RuntimeContext(Wave3ReferenceRuntimeContext):
    def __init__(self, *args, session, gateway, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.gateway = gateway

    def close(self):
        self.gateway.cleanup_pending()
        self.session.close()


class RuntimeFactory:
    def __init__(self, Session, object_store, metadata_store, delivery, materialization_root: Path):
        self.Session = Session
        self.object_store = object_store
        self.metadata_store = metadata_store
        self.delivery = delivery
        self.materialization_root = materialization_root
        self.opens = 0

    def open(self):
        self.opens += 1
        session = self.Session()
        projects = ProjectRepository(session)
        runs = EngineeringRunRepository(session)
        service = EngineeringRunService(
            runs,
            ConversationRepository(session),
            WorkSpecificationRepository(session),
            projects,
            owner_subject=OWNER,
            require_project_binding=True,
        )
        lineage_store = SourceLineageStore(self.object_store, self.metadata_store)
        allocator = ProjectWorkspaceAllocator(
            self.materialization_root / f"instance-{self.opens}",
            lineage_store=lineage_store,
        )
        gateway = AllocatorWorkspaceLineageGateway(allocator)
        implementation = ProtectedImplementationRuntime(
            service, RunProjectBinding(), gateway, generator=FixedGenerator()
        )
        autonomy = AutonomyCoordinator(
            service,
            NeverLegacyExecutor(),
            implementation_runtime=implementation,
            lineage_executor=ReconstructingLineageExecutor(allocator),
        )
        adapter = RuntimeAppBuilderEvidenceAdapter(
            session,
            owner_subject=OWNER,
            lineage_store=lineage_store,
            delivery_reader=self.delivery,
        )
        return RuntimeContext(
            service=service,
            implementation_runtime=implementation,
            autonomy=autonomy,
            evidence_adapter=adapter,
            worker_recovery=WorkerRecoveryService(WorkerExecutionRepository(session), runs),
            session=session,
            gateway=gateway,
        )


def _environment(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 'wave3-reference.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    object_store = InMemoryImmutableObjectStore()
    metadata_store = InMemoryLineageMetadataStore()
    delivery = DeterministicDeliveryDriver(object_store, metadata_store)
    factory = RuntimeFactory(Session, object_store, metadata_store, delivery, tmp_path / "materialized")

    with Session() as session:
        projects = ProjectRepository(session)
        project = projects.create(
            owner_subject=OWNER,
            slug=f"wave3-reference-{uuid4().hex[:8]}",
            name="Wave 3 Reference App",
            description="Protected deterministic Wave 3 app-builder reference",
            repository_ref=REPOSITORY_REF,
        )
        conversations = ConversationRepository(session)
        conversation = conversations.create("code", spec_id="P2-V0.16.5", project_id=project.id)
        work_specs = WorkSpecificationRepository(session)
        spec = work_specs.create_draft(
            conversation_id=conversation.id,
            draft=WorkSpecificationDraft(
                title="Complete Wave 3 reference proof",
                objective="Prove durable recovery and replay-safe protected app-builder delivery.",
                constraints=["Preserve exact lineage, worker generation and operator REVIEW authority."],
                acceptance_criteria=[
                    "The reference source is implemented through protected mutation.",
                    "Process loss recovers without duplicate mutation or publication.",
                ],
                risks=["Stale worker or provider replay could otherwise duplicate side effects."],
                open_questions=[],
                confidence=0.99,
                program_version="wave3-reference-spec-v1",
            ),
            model_id="wave3-reference-spec-model",
        )
        spec = work_specs.approve(spec)
        service = EngineeringRunService(
            EngineeringRunRepository(session),
            conversations,
            work_specs,
            projects,
            owner_subject=OWNER,
            require_project_binding=True,
        )
        run = service.activate_run(
            conversation_id=conversation.id,
            work_specification_id=spec.id,
        )
        return Session, factory, delivery, project.id, run.id


def _suite():
    root = Path(__file__).resolve().parents[3]
    return load_app_builder_suite(
        root / "benchmarks/parallax-app-builder/reference-runtime-v0.1.json"
    )


def test_wave3_reference_recovers_process_loss_without_manual_resume_or_duplicate_publication(tmp_path):
    Session, factory, delivery, project_id, run_id = _environment(tmp_path)
    result = ProtectedWave3ReferenceAppHarness(factory, delivery, _suite()).run(
        run_id=run_id,
        operation_key="wave3-reference-loop",
        candidate_version="P2-V0.16.5-reference",
        operator_ref="operator:wave3-reference",
    )

    assert result.ready_for_production_promotion is True
    assert result.production_deployed is False
    assert result.evaluation.protected_pass is True
    assert result.evaluation.aggregate_score == 1.0
    assert result.recovery.original_generation == 1
    assert result.recovery.replacement_generation == 2
    assert result.recovery.stale_worker_rejected is True
    assert result.recovery.no_manual_run_resume is True
    assert result.recovery.checkpoint_lineage_ref == result.source_lineage_ref
    assert delivery.counters == {"branch": 1, "commit": 1, "pr": 1, "preview": 1}
    assert factory.opens >= 5

    with Session() as session:
        run = EngineeringRunRepository(session).get(run_id)
        assert run is not None and run.project_id == project_id and run.state == "COMPLETE"
        assert len([item for item in run.attempts if item.stage == "IMPLEMENT" and item.status == "PASSED"]) == 1
        assert len([item for item in run.attempts if item.stage == "BUILD" and item.status == "PASSED"]) == 1
        assert len([item for item in run.attempts if item.stage == "TEST" and item.status == "PASSED"]) == 1
        assert len([item for item in run.attempts if item.stage == "VERIFY" and item.status == "PASSED"]) == 1
        assert len([item for item in run.attempts if item.stage == "REVIEW" and item.status == "PASSED"]) == 1
        assert not any(item.status in {"PAUSED", "RESUMED"} for item in run.attempts)
        worker = WorkerExecutionRepository(session).get_for_run(run_id)
        assert worker is not None
        assert worker.state == "SUCCEEDED"
        assert worker.lease_generation == 2
        assert worker.source_lineage_ref == result.source_lineage_ref
        assert worker.last_known_good_lineage_ref == result.source_lineage_ref
        assert worker.lease_owner_id is None


def test_wave3_reference_result_never_claims_production_deployment(tmp_path):
    _Session, factory, delivery, _project_id, run_id = _environment(tmp_path)
    result = ProtectedWave3ReferenceAppHarness(factory, delivery, _suite()).run(
        run_id=run_id,
        operation_key="wave3-reference-production-boundary",
        candidate_version="P2-V0.16.5-boundary",
        operator_ref="operator:wave3-reference",
    )
    assert result.production_deployed is False
    assert "production" not in result.delivery.preview_status.casefold()
