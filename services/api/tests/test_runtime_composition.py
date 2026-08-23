from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.autonomy import AutonomyStopReason
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.execution import ExecutionSpec
from parallax_api.code.implementation_runtime import WorkspaceLineageError
from parallax_api.code.runtime_composition import (
    AllocatorWorkspaceLineageGateway,
    EngineeringRuntimeComposition,
    production_durable_lineage_allocator,
)
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import ProjectRunIdentity, SourceLineageStore, SourcePackage
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.implementation_generation import GeneratedSourcePatch, ImplementationProposal
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


class StaticSourceProvider:
    def __init__(self, files: dict[str, bytes]):
        self.files = files

    def load(self, identity: ProjectRunIdentity):
        return SourcePackage(source_kind="starter", source_ref="ws69-fixture", files=self.files)


class FixedGenerator:
    def __init__(self, proposal: ImplementationProposal):
        self.proposal = proposal
        self.calls = 0

    def generate_sync(self, request):
        self.calls += 1
        return SimpleNamespace(
            proposal=self.proposal,
            model="test-model",
            program_version="ws69-test-generation",
        )


class LegacyExecutor:
    def __init__(self):
        self.execute_calls: list[ExecutionSpec] = []
        self.probe_calls: list[str] = []

    def probe(self, *, operation_key: str):
        self.probe_calls.append(operation_key)
        return {
            "tool_id": "python",
            "exit_code": 0,
            "duration_ms": 1,
            "stdout_excerpt": "PARALLAX_SANDBOX_READY",
            "stderr_excerpt": "",
            "protected_success": True,
            "executor": "test",
            "network_policy": "deny-all",
            "persistent": False,
        }

    def execute(self, spec: ExecutionSpec):
        self.execute_calls.append(spec)
        raise AssertionError("legacy fresh-repository executor must not run after accepted IMPLEMENT lineage")


class LineageExecutor:
    def __init__(self):
        self.calls: list[tuple[WorkflowStage, str, str, str]] = []

    def execute_on_lineage(self, spec, *, project_ref: str, run_id: str, source_lineage_ref: str):
        self.calls.append((spec.stage, project_ref, run_id, source_lineage_ref))
        return {
            "tool_id": spec.tool_id,
            "exit_code": 0,
            "duration_ms": 1,
            "stdout_excerpt": "ok",
            "stderr_excerpt": "",
            "protected_success": True,
            "executor": "test-lineage",
            "network_policy": "deny-all",
            "persistent": False,
            "project_ref": "spoofed-project",
            "source_lineage_ref": "spoofed-lineage",
        }


def make_test_allocator(root):
    """Use #68 durable fakes when serialized, else the accepted #60 store."""

    try:
        from parallax_api.code.lineage_persistence import (
            InMemoryImmutableObjectStore,
            InMemoryLineageMetadataStore,
        )
    except ImportError:
        return ProjectWorkspaceAllocator(root)

    lineage_store = SourceLineageStore(
        InMemoryImmutableObjectStore(),
        InMemoryLineageMetadataStore(),
    )
    return ProjectWorkspaceAllocator(root, lineage_store=lineage_store)


def allocator_with_source(tmp_path, identity: ProjectRunIdentity, files=None):
    allocator = make_test_allocator(tmp_path / "allocator")
    lease = allocator.initialize(identity, StaticSourceProvider(files or {"app.py": b"value = 1\n"}))
    base = lease.lineage
    allocator.cleanup(lease)
    return allocator, base


def test_pre68_production_builder_fails_closed_instead_of_creating_filesystem_durability(tmp_path):
    try:
        import parallax_api.code.lineage_persistence  # noqa: F401
    except ImportError:
        assert production_durable_lineage_allocator(object(), materialization_root=tmp_path / "live") is None
    else:
        pytest.skip("#68 durable persistence is already serialized on this base")


def test_gateway_binds_canonical_identity_accepts_exact_artifacts_and_separates_digests(tmp_path):
    identity = ProjectRunIdentity(
        project_id="11111111-1111-1111-1111-111111111111",
        run_id="22222222-2222-2222-2222-222222222222",
    )
    allocator, base = allocator_with_source(tmp_path, identity)
    gateway = AllocatorWorkspaceLineageGateway(allocator)

    handle = gateway.resolve_for_implementation(project_ref=identity.project_id, run_id=identity.run_id)
    assert handle.source_lineage_ref == base.lineage_id
    handle.workspace_root.joinpath("app.py").write_text("value = 2\n", encoding="utf-8")
    content = b"value = 2\n"
    artifact = {"path": "app.py", "sha256": sha256(content).hexdigest(), "size": len(content)}
    mutation_digest = "d" * 64

    receipt = gateway.accept_implementation(
        handle=handle,
        workspace_digest=mutation_digest,
        artifacts=(artifact,),
    )
    accepted = allocator.current_lineage(identity)
    assert receipt.project_ref == identity.project_id
    assert receipt.run_id == identity.run_id
    assert receipt.base_source_lineage_ref == base.lineage_id
    assert receipt.source_lineage_ref == accepted.lineage_id
    assert receipt.workspace_digest == mutation_digest
    assert accepted.parent_lineage_id == base.lineage_id
    assert accepted.content_digest != mutation_digest
    assert {item.path: item.sha256 for item in accepted.files}["app.py"] == artifact["sha256"]
    assert not handle.workspace_root.exists()


def test_gateway_rejects_bad_artifact_before_advancing_durable_lineage_and_cleans_lease(tmp_path):
    identity = ProjectRunIdentity(
        project_id="11111111-1111-1111-1111-111111111111",
        run_id="33333333-3333-3333-3333-333333333333",
    )
    allocator, base = allocator_with_source(tmp_path, identity)
    gateway = AllocatorWorkspaceLineageGateway(allocator)
    handle = gateway.resolve_for_implementation(project_ref=identity.project_id, run_id=identity.run_id)
    handle.workspace_root.joinpath("app.py").write_text("value = 2\n", encoding="utf-8")

    with pytest.raises(WorkspaceLineageError):
        gateway.accept_implementation(
            handle=handle,
            workspace_digest="a" * 64,
            artifacts=({"path": "app.py", "sha256": "0" * 64, "size": 10},),
        )

    assert allocator.current_lineage(identity).lineage_id == base.lineage_id
    assert not handle.workspace_root.exists()


def test_gateway_rejects_noncanonical_project_identity_without_materialization(tmp_path):
    identity = ProjectRunIdentity(
        project_id="11111111-1111-1111-1111-111111111111",
        run_id="44444444-4444-4444-4444-444444444444",
    )
    allocator, _ = allocator_with_source(tmp_path, identity)
    gateway = AllocatorWorkspaceLineageGateway(allocator)
    with pytest.raises(WorkspaceLineageError):
        gateway.resolve_for_implementation(project_ref=f"project:{identity.project_id}", run_id=identity.run_id)


def test_cleanup_pending_releases_disposable_materialization_without_deleting_lineage(tmp_path):
    identity = ProjectRunIdentity(
        project_id="11111111-1111-1111-1111-111111111111",
        run_id="55555555-5555-5555-5555-555555555555",
    )
    allocator, base = allocator_with_source(tmp_path, identity)
    gateway = AllocatorWorkspaceLineageGateway(allocator)
    handle = gateway.resolve_for_implementation(project_ref=identity.project_id, run_id=identity.run_id)
    assert handle.workspace_root.exists()
    gateway.cleanup_pending()
    assert not handle.workspace_root.exists()
    assert allocator.current_lineage(identity).lineage_id == base.lineage_id


def runtime_service(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'runtime-composition.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    projects = ProjectRepository(session)
    project = projects.create(
        owner_subject="owner-a",
        slug="runtime-composition",
        name="Runtime Composition",
        description=None,
        repository_ref=None,
    )
    conversations = ConversationRepository(session)
    work_specs = WorkSpecificationRepository(session)
    conversation = conversations.create("code", spec_id="P2-V0.15.6", project_id=project.id)
    draft = work_specs.create_draft(
        conversation_id=conversation.id,
        draft=WorkSpecificationDraft(
            title="Compose protected runtime",
            objective="Change app source and prove later stages use the accepted lineage.",
            constraints=["Never use a fresh repository checkout after IMPLEMENT."],
            acceptance_criteria=[
                "The application value is changed through protected IMPLEMENT.",
                "BUILD TEST and VERIFY use the exact accepted lineage.",
            ],
            risks=["Later execution could drift to unrelated source."],
            open_questions=[],
            confidence=0.99,
            program_version="ws69-test",
        ),
        model_id="test-model",
    )
    approved = work_specs.approve(draft)
    service = EngineeringRunService(
        EngineeringRunRepository(session),
        conversations,
        work_specs,
        projects,
        owner_subject="owner-a",
        require_project_binding=True,
    )
    run = service.activate_run(
        conversation_id=conversation.id,
        work_specification_id=approved.id,
    )
    return session, service, project, run


def proposal_for_value_change():
    return ImplementationProposal(
        acceptance_ids_covered=["AC-01", "AC-02"],
        patches=[
            GeneratedSourcePatch(
                path="app.py",
                expected_base_sha256=sha256(b"value = 1\n").hexdigest(),
                unified_diff=(
                    "--- a/app.py\n"
                    "+++ b/app.py\n"
                    "@@ -1 +1 @@\n"
                    "-value = 1\n"
                    "+value = 2\n"
                ),
            )
        ],
    )


def test_composed_runtime_uses_one_accepted_lineage_for_implement_build_test_verify(tmp_path):
    session, service, project, run = runtime_service(tmp_path)
    try:
        identity = ProjectRunIdentity(project_id=project.id, run_id=run.id)
        allocator, base = allocator_with_source(tmp_path, identity)
        legacy = LegacyExecutor()
        lineage_executor = LineageExecutor()
        runtime = EngineeringRuntimeComposition(
            service,
            allocator,
            legacy,
            lineage_executor=lineage_executor,
        )
        runtime.implementation_runtime.generator = FixedGenerator(proposal_for_value_change())

        result = runtime.run(
            run_id=run.id,
            operation_key="ws69:e2e",
            expected_revision=run.revision,
        )
        assert result.stop_reason is AutonomyStopReason.REVIEW_REQUIRED
        assert result.run.state == "REVIEW"
        assert legacy.execute_calls == []
        assert [item[0] for item in lineage_executor.calls] == [
            WorkflowStage.BUILD,
            WorkflowStage.TEST,
            WorkflowStage.VERIFY,
        ]
        accepted = allocator.current_lineage(identity)
        assert accepted.parent_lineage_id == base.lineage_id
        assert accepted.lineage_id != base.lineage_id
        assert all(item[1] == project.id for item in lineage_executor.calls)
        assert all(item[2] == run.id for item in lineage_executor.calls)
        assert all(item[3] == accepted.lineage_id for item in lineage_executor.calls)

        for attempt in result.run.attempts:
            if attempt.stage in {"BUILD", "TEST", "VERIFY"} and attempt.status == "PASSED":
                import json

                evidence = json.loads(attempt.evidence_json)
                assert evidence["project_ref"] == project.id
                assert evidence["source_lineage_ref"] == accepted.lineage_id
                assert evidence["lineage_bound_execution"] is True

        reconstructed = allocator.reconstruct(identity, accepted.lineage_id)
        try:
            assert reconstructed.path.joinpath("app.py").read_text(encoding="utf-8") == "value = 2\n"
        finally:
            allocator.cleanup(reconstructed)
    finally:
        session.close()
