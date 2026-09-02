from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.agentic_runtime_live import LiveAgenticControlPlane
from parallax_api.code.autonomy import AutonomyCoordinator
from parallax_api.code.implementation_runtime import ProtectedImplementationRuntime, RunProjectBinding
from parallax_api.code.runtime_composition import AllocatorWorkspaceLineageGateway
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import ProjectRunIdentity, SourceLineageStore, SourcePackage
from parallax_api.code.lineage_persistence import InMemoryImmutableObjectStore, InMemoryLineageMetadataStore
from parallax_api.db import Base, make_engine
from parallax_api.evaluation.app_builder import evaluate_app_builder, load_app_builder_suite
from parallax_api.evaluation.reference_app import (
    ProtectedReferenceAppHarness,
    ReferenceRuntimeContext,
)
from parallax_api.evaluation.runtime_evidence import (
    PersistedProviderActionFact,
    PersistedVerifiedDelivery,
    RuntimeAppBuilderEvidenceAdapter,
    RuntimeEvidenceError,
)
from parallax_api.intelligence.implementation_generation import GeneratedSourcePatch, ImplementationProposal
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.tools import ToolActionPolicy, ToolCapability, ToolCapabilityRegistry, ToolConsequence, ToolOutcome
from parallax_api.tools.providers.common import (
    AcceptedSourceLineage,
    ProviderActionState,
    ProviderInvocation,
    ProviderProjectBinding,
)
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


OWNER = "owner:reference-test"
REPOSITORY_REF = "github:acme/reference-app"
BASE_REVISION = "1" * 40
VERCEL_PROJECT = "vercel:project:reference-app"
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
        proposal = ImplementationProposal(
            acceptance_ids_covered=list(request.required_acceptance_ids),
            patches=[
                GeneratedSourcePatch(
                    path="app.py",
                    expected_base_sha256=sha256(INITIAL_SOURCE.encode("utf-8")).hexdigest(),
                    unified_diff=(
                        "--- a/app.py\n"
                        "+++ b/app.py\n"
                        "@@ -1 +1 @@\n"
                        f"-{INITIAL_SOURCE.rstrip()}\n"
                        f"+{UPDATED_SOURCE.rstrip()}\n"
                    ),
                )
            ],
        )
        return SimpleNamespace(
            proposal=proposal,
            model="reference-test-model",
            program_version="reference-generator-v1",
        )


class NeverLegacyExecutor:
    def probe(self, *, operation_key: str):
        raise AssertionError("legacy executor probe must not run after protected PLAN")

    def execute(self, spec):
        raise AssertionError("legacy executor must not run after accepted IMPLEMENT lineage")


class ReconstructingLineageExecutor:
    def __init__(self, allocator: ProjectWorkspaceAllocator):
        self.allocator = allocator
        self.calls: list[tuple[str, str, str]] = []

    def execute_on_lineage(
        self, spec, *, project_ref: str, run_id: str, source_lineage_ref: str, execution_contract
    ):
        self.calls.append((project_ref, run_id, source_lineage_ref))
        identity = ProjectRunIdentity(project_ref, run_id)
        workspace = self.allocator.reconstruct(identity, source_lineage_ref)
        try:
            lineage = workspace.lineage
            assert (workspace.path / "app.py").read_text(encoding="utf-8") == UPDATED_SOURCE
            return {
                "tool_id": spec.tool_id,
                "invocation_digest": "a" * 64,
                "exit_code": 0,
                "duration_ms": 1,
                "stdout_digest": "b" * 64,
                "stdout_excerpt": "reference-ok",
                "stderr_digest": "c" * 64,
                "stderr_excerpt": "",
                "timed_out": False,
                "redacted": True,
                "artifacts": [],
                "protected_success": True,
                "executor": "reference-lineage-test",
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

    def commit_files(
        self,
        repository_ref: str,
        branch_name: str,
        expected_parent_revision: str,
        lineage: AcceptedSourceLineage,
        files: tuple[GitHubCommitFile, ...],
    ):
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

    def create_pull_request(
        self,
        repository_ref: str,
        head_branch: str,
        expected_head_revision: str,
        base_branch: str,
        title: str,
        body: str,
    ):
        self.counters["pr"] += 1
        return GitHubPullRequestResult(
            repository_ref,
            80,
            head_branch,
            expected_head_revision,
            base_branch,
            "OPEN",
            "https://github.com/acme/reference-app/pull/80",
        )


class FakeVercelPublishClient:
    def __init__(self, counters: dict[str, int]):
        self.counters = counters

    def create_preview(self, vercel_project_ref, repository_ref, source_revision, branch_name, lineage):
        self.counters["preview"] += 1
        return VercelPreviewResult(
            vercel_project_ref,
            repository_ref,
            "dpl_reference_80",
            source_revision,
            VercelPreviewStatus.READY,
            "https://reference-app-parallax.vercel.app",
        )


class ProvisionalDeliveryDriver:
    """Deterministic #79-shaped fake with a durable journal and recreated actions."""

    def __init__(self, object_store, metadata_store):
        self.object_store = object_store
        self.metadata_store = metadata_store
        self.records: dict[tuple[str, str, str], PersistedVerifiedDelivery] = {}
        self.counters = {"branch": 0, "commit": 0, "pr": 0, "preview": 0}

    def _lineage_store(self):
        return SourceLineageStore(self.object_store, self.metadata_store)

    def ensure_bootstrap(self, *, project_id: str, run_id: str, repository_ref: str) -> str:
        assert repository_ref == REPOSITORY_REF
        lineage = self._lineage_store().initialize(ProjectRunIdentity(project_id, run_id), StaticSourceProvider())
        return lineage.lineage_id

    @staticmethod
    def _registry(project_id: str) -> ToolCapabilityRegistry:
        return ToolCapabilityRegistry(
            (
                ToolCapability(
                    capability_id="cap:github:reference",
                    project_ref=project_id,
                    tool="github",
                    actions=(
                        ToolActionPolicy(ACTION_BRANCH_CREATE, ToolConsequence.MUTATE),
                        ToolActionPolicy(ACTION_COMMIT_WRITE, ToolConsequence.MUTATE),
                        ToolActionPolicy(ACTION_PULL_REQUEST_CREATE, ToolConsequence.MUTATE),
                    ),
                ),
                ToolCapability(
                    capability_id="cap:vercel:reference",
                    project_ref=project_id,
                    tool="vercel",
                    actions=(ToolActionPolicy(ACTION_PREVIEW_CREATE, ToolConsequence.MUTATE),),
                ),
            )
        )

    @staticmethod
    def _invoke(capability: str, request: str) -> ProviderInvocation:
        return ProviderInvocation(request_id=request, capability_id=capability, actor_ref="actor:reference-harness")

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
        branch_name = f"parallax/reference-{run_id[:8]}"

        branch = github.create_branch(
            binding,
            self._invoke("cap:github:reference", f"req:branch:{run_id}"),
            branch_name=branch_name,
            base_revision=BASE_REVISION,
        )
        source = store.object_store.get(lineage.files[0].sha256)
        commit_file = GitHubCommitFile("app.py", source.decode("utf-8"), lineage.files[0].sha256)
        commit = github.commit_accepted_lineage(
            binding,
            self._invoke("cap:github:reference", f"req:commit:{run_id}"),
            branch_name=branch_name,
            expected_parent_revision=BASE_REVISION,
            lineage=accepted,
            files=(commit_file,),
        )
        pr = github.create_pull_request(
            binding,
            self._invoke("cap:github:reference", f"req:pr:{run_id}"),
            head_branch=branch_name,
            expected_head_revision=commit.value.commit_revision,
            base_branch="main",
            lineage=accepted,
            title="Parallax protected reference app",
            body="Verified source lineage reference proof.",
        )
        preview = vercel.create_preview(
            VercelPreviewTarget(project_id, REPOSITORY_REF, VERCEL_PROJECT),
            self._invoke("cap:vercel:reference", f"req:preview:{run_id}"),
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


class TestRuntimeContext(ReferenceRuntimeContext):
    def __init__(self, *args, session, gateway, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.gateway = gateway

    def close(self):
        self.gateway.cleanup_pending()
        self.session.close()


class TestRuntimeFactory:
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
        service = EngineeringRunService(
            EngineeringRunRepository(session),
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
            service,
            RunProjectBinding(),
            gateway,
            generator=FixedGenerator(),
        )
        autonomy = AutonomyCoordinator(
            service,
            NeverLegacyExecutor(),
            implementation_runtime=implementation,
            lineage_executor=ReconstructingLineageExecutor(allocator),
            plan_runtime=LiveAgenticControlPlane(service, allocator),
        )
        adapter = RuntimeAppBuilderEvidenceAdapter(
            session,
            owner_subject=OWNER,
            lineage_store=lineage_store,
            delivery_reader=self.delivery,
        )
        return TestRuntimeContext(
            service=service,
            implementation_runtime=implementation,
            autonomy=autonomy,
            evidence_adapter=adapter,
            session=session,
            gateway=gateway,
        )


def _environment(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 'reference.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    object_store = InMemoryImmutableObjectStore()
    metadata_store = InMemoryLineageMetadataStore()
    delivery = ProvisionalDeliveryDriver(object_store, metadata_store)
    factory = TestRuntimeFactory(Session, object_store, metadata_store, delivery, tmp_path / "materialized")

    session = Session()
    try:
        projects = ProjectRepository(session)
        project = projects.create(
            owner_subject=OWNER,
            slug="reference-app",
            name="Reference App",
            description="Protected deterministic app-builder reference",
            repository_ref=REPOSITORY_REF,
        )
        conversations = ConversationRepository(session)
        conversation = conversations.create("code", spec_id="P2-V0.15.10", project_id=project.id)
        work_specs = WorkSpecificationRepository(session)
        spec = work_specs.create_draft(
            conversation_id=conversation.id,
            draft=WorkSpecificationDraft(
                title="Update reference application value",
                objective="Update the reference application through the protected app-builder path.",
                constraints=["Preserve protected authority and exact source lineage."],
                acceptance_criteria=[
                    "The reference value is updated through safe mutation.",
                    "BUILD TEST VERIFY operate on the accepted implementation lineage.",
                ],
                risks=["Provider or source identity drift must fail closed."],
                open_questions=[],
                confidence=0.99,
                program_version="reference-spec-v1",
            ),
            model_id="reference-spec-model",
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
    finally:
        session.close()


def _suite():
    repository_root = Path(__file__).resolve().parents[3]
    return load_app_builder_suite(repository_root / "benchmarks/parallax-app-builder/reference-runtime-v0.1.json")


def _run_reference(tmp_path: Path):
    Session, factory, delivery, project_id, run_id = _environment(tmp_path)
    harness = ProtectedReferenceAppHarness(factory, delivery, _suite())
    result = harness.run(
        run_id=run_id,
        operation_key="reference-loop",
        candidate_version="P2-V0.15.10-reference",
        operator_ref="operator:reference-test",
    )
    return Session, factory, delivery, project_id, run_id, result


def test_reference_app_proves_restart_replay_provider_delivery_evaluation_and_operator_review(tmp_path):
    Session, factory, delivery, project_id, run_id, result = _run_reference(tmp_path)

    assert result.evaluation.protected_pass is True
    assert result.evaluation.aggregate_score == 1.0
    assert all(item.score == 1.0 and item.passed for item in result.evaluation.category_results)
    assert result.review.run.state == "COMPLETE"
    assert result.delivery.publication_replayed is True
    assert delivery.counters == {"branch": 1, "commit": 1, "pr": 1, "preview": 1}
    assert factory.opens >= 5

    session = Session()
    try:
        run = EngineeringRunRepository(session).get(run_id)
        assert run is not None and run.project_id == project_id
        implement = [item for item in run.attempts if item.stage == "IMPLEMENT" and item.status == "PASSED"]
        assert len(implement) == 1
        assert any(item.status == "PAUSED" for item in run.attempts)
        assert any(item.status == "RESUMED" for item in run.attempts)
        assert len([item for item in run.attempts if item.stage == "BUILD" and item.status == "PASSED"]) == 1
        assert len([item for item in run.attempts if item.stage == "TEST" and item.status == "PASSED"]) == 1
        assert len([item for item in run.attempts if item.stage == "VERIFY" and item.status == "PASSED"]) == 1
        assert len([item for item in run.attempts if item.stage == "REVIEW" and item.status == "PASSED"]) == 1
        for stage in ("TEST", "VERIFY"):
            attempt = next(item for item in run.attempts if item.stage == stage and item.status == "PASSED")
            evidence = json.loads(attempt.evidence_json)
            assert evidence["acceptance_verification_scope"] == "STRUCTURAL_ONLY"
            assert set(evidence["acceptance_ids_targeted"]) == {"AC-01", "AC-02"}
            assert evidence["acceptance_ids_verified"] == []
            assert set(evidence["acceptance_ids_unverified"]) == {"AC-01", "AC-02"}
    finally:
        session.close()


def test_reference_suite_dynamic_binding_does_not_weaken_scoring(tmp_path):
    Session, factory, delivery, _project_id, run_id, result = _run_reference(tmp_path)
    context = factory.open()
    try:
        snapshot = context.evidence_adapter.snapshot(run_id)
        suite = _suite()
        bound = context.evidence_adapter.bind_suite(suite, snapshot)
        assert suite.minimum_aggregate_score == bound.minimum_aggregate_score == 1.0
        assert suite.category_minimums == bound.category_minimums
        assert all(case.minimum_score == 1.0 for case in bound.cases)
        assert all(all(req.critical for req in case.requirements) for case in bound.cases)
        assert all(case.expected_project_ref == snapshot.project_id for case in bound.cases)
        assert all(case.expected_workspace_ref == snapshot.workspace_ref for case in bound.cases)
        assert all(case.expected_spec_ref == snapshot.work_specification_id for case in bound.cases)
        assert all(case.expected_spec_digest == snapshot.spec_digest for case in bound.cases)
    finally:
        context.close()


def test_deliberate_negative_runtime_facts_fail_closed(tmp_path):
    Session, factory, delivery, project_id, run_id, result = _run_reference(tmp_path)
    lineage_id = result.source_lineage_ref
    key = (project_id, run_id, lineage_id)
    original_delivery = delivery.records[key]

    # Wrong Project in persisted provider delivery.
    delivery.records[key] = replace(original_delivery, project_id=str(uuid4()))
    context = factory.open()
    try:
        with pytest.raises(RuntimeEvidenceError):
            context.evidence_adapter.snapshot(run_id)
    finally:
        context.close()
    delivery.records[key] = original_delivery

    # Missing READY preview.
    delivery.records[key] = replace(
        original_delivery,
        actions=tuple(item for item in original_delivery.actions if item.evidence.provider != "vercel"),
    )
    context = factory.open()
    try:
        with pytest.raises(RuntimeEvidenceError):
            context.evidence_adapter.snapshot(run_id)
    finally:
        context.close()
    delivery.records[key] = original_delivery

    # Provider failure remains a failure and cannot be normalized to success.
    commit_index = next(i for i, item in enumerate(original_delivery.actions) if item.evidence.action == "commit.write")
    success_fact = original_delivery.actions[commit_index]
    failed_evidence = replace(
        success_fact.evidence,
        state=ProviderActionState.FAILED,
        result_status="PROVIDER_ERROR",
    )
    failed_audit = replace(
        success_fact.audit,
        outcome=ToolOutcome.FAILED,
        result_code="PROVIDER_ERROR",
    )
    failed_actions = list(original_delivery.actions)
    failed_actions[commit_index] = PersistedProviderActionFact(failed_evidence, failed_audit)
    delivery.records[key] = replace(original_delivery, actions=tuple(failed_actions))
    context = factory.open()
    try:
        with pytest.raises(RuntimeEvidenceError):
            context.evidence_adapter.snapshot(run_id)
    finally:
        context.close()
    delivery.records[key] = original_delivery

    # Stale/unrelated delivery lineage.
    delivery.records[key] = replace(original_delivery, lineage_id="src:" + "f" * 64)
    context = factory.open()
    try:
        with pytest.raises(RuntimeEvidenceError):
            context.evidence_adapter.snapshot(run_id)
    finally:
        context.close()
    delivery.records[key] = original_delivery

    # False execution success and unrelated/fresh source evidence both fail.
    session = Session()
    try:
        run = EngineeringRunRepository(session).get(run_id)
        assert run is not None
        build = next(item for item in run.attempts if item.stage == "BUILD" and item.status == "PASSED")
        original_build = build.evidence_json
        payload = json.loads(original_build)
        payload["protected_success"] = False
        build.evidence_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        session.add(build)
        session.commit()
    finally:
        session.close()
    context = factory.open()
    try:
        with pytest.raises(RuntimeEvidenceError):
            context.evidence_adapter.snapshot(run_id)
    finally:
        context.close()

    session = Session()
    try:
        build = next(
            item
            for item in EngineeringRunRepository(session).get(run_id).attempts
            if item.stage == "BUILD" and item.status == "PASSED"
        )
        payload = json.loads(original_build)
        payload["fresh_repository_checkout"] = True
        build.evidence_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        session.add(build)
        session.commit()
    finally:
        session.close()
    context = factory.open()
    try:
        with pytest.raises(RuntimeEvidenceError):
            context.evidence_adapter.snapshot(run_id)
    finally:
        context.close()

    # Secret-bearing persisted stage evidence is rejected, not copied into #46 evidence.
    session = Session()
    try:
        build = next(
            item
            for item in EngineeringRunRepository(session).get(run_id).attempts
            if item.stage == "BUILD" and item.status == "PASSED"
        )
        payload = json.loads(original_build)
        payload["token"] = "test-secret-token-value-123456789"
        build.evidence_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        session.add(build)
        session.commit()
    finally:
        session.close()
    context = factory.open()
    try:
        with pytest.raises(RuntimeEvidenceError):
            context.evidence_adapter.snapshot(run_id)
    finally:
        context.close()

    # Wrong persisted Work Specification digest is not accepted as a binding.
    session = Session()
    try:
        run = EngineeringRunRepository(session).get(run_id)
        assert run is not None
        run.work_specification_digest = "0" * 64
        session.add(run)
        session.commit()
    finally:
        session.close()
    context = factory.open()
    try:
        with pytest.raises(RuntimeEvidenceError):
            context.evidence_adapter.snapshot(run_id)
    finally:
        context.close()


def test_reference_suite_forbidden_production_claim_remains_critical_failure(tmp_path):
    _Session, factory, _delivery, _project_id, run_id, _result = _run_reference(tmp_path)
    context = factory.open()
    try:
        snapshot = context.evidence_adapter.snapshot(run_id)
        suite = _suite()
        bound = context.evidence_adapter.bind_suite(suite, snapshot)
        evidence = context.evidence_adapter.recorded_evidence(
            suite,
            snapshot,
            candidate_version="negative-production-claim",
        )
        cases = list(evidence.cases)
        index = next(i for i, case in enumerate(cases) if case.case_id == "runtime-tool-authority-01")
        cases[index] = cases[index].model_copy(
            update={"observations": [*cases[index].observations, "production.authority=true"]}
        )
        negative = evidence.model_copy(update={"cases": cases})
        report = evaluate_app_builder(bound, negative)
        assert report.protected_pass is False
        tool_result = next(item for item in report.case_results if item.case_id == "runtime-tool-authority-01")
        assert tool_result.critical_failure is True
        assert "forbidden_present:production-authority" in tool_result.failures
    finally:
        context.close()


def test_runtime_evidence_rejects_forged_structural_acceptance_claim(tmp_path):
    Session, factory, _delivery, _project_id, run_id, _result = _run_reference(tmp_path)
    session = Session()
    try:
        run = EngineeringRunRepository(session).get(run_id)
        assert run is not None
        test_attempt = next(
            item for item in run.attempts if item.stage == "TEST" and item.status == "PASSED"
        )
        evidence = json.loads(test_attempt.evidence_json)
        evidence["acceptance_ids_verified"] = ["AC-01"]
        test_attempt.evidence_json = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
        session.add(test_attempt)
        session.commit()
    finally:
        session.close()

    context = factory.open()
    try:
        with pytest.raises(RuntimeEvidenceError, match="structural evidence claimed"):
            context.evidence_adapter.snapshot(run_id)
    finally:
        context.close()
