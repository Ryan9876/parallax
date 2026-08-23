from __future__ import annotations

from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.lineage_persistence import (
    InMemoryImmutableObjectStore,
    InMemoryLineageMetadataStore,
)
from parallax_api.code.source_delivery_composition import (
    OwnerScopedProjectBindingResolver,
    ProjectRepositoryBindingError,
    RegisteredPreviewTargetResolver,
    RepositoryLineageBootstrap,
    ScopedProviderInvocationFactory,
    SourceBootstrapError,
    VerifiedDeliveryError,
    VerifiedLineageDelivery,
)
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import (
    ProjectRunIdentity,
    SourceLineageStore,
    SourcePackage,
    StaleLineageError,
)
from parallax_api.db import Base, make_engine
from parallax_api.projects.repository import ProjectRepository
from parallax_api.projects.schemas import ProjectCreate
from parallax_api.projects.service import ProjectService
from parallax_api.tools.providers import (
    GitHubBranchResult,
    GitHubCommitResult,
    GitHubFileResult,
    GitHubPullRequestResult,
    GitHubRepositoryState,
    GitHubTreeEntry,
    GitHubTreeResult,
    ProviderActionEvidence,
    ProviderActionState,
    ProviderProjectBinding,
    VercelPreviewResult,
    VercelPreviewStatus,
    VercelPreviewTarget,
)


REPOSITORY_REF = "github:Ryan9876/parallax"
ROOT_REVISION = "rootabc123"
COMMIT_REVISION = "commitdef456"


def _run(project_id: str, run_id: str | None = None, *, state: str = "PLAN", attempts=()):
    return SimpleNamespace(
        id=run_id or str(uuid4()),
        project_id=project_id,
        state=state,
        attempts=list(attempts),
    )


def _attempt(stage: str, evidence: dict[str, object]):
    return SimpleNamespace(stage=stage, status="PASSED", evidence_json=json.dumps(evidence))


def _action_success(binding: ProviderProjectBinding, *, provider: str, action: str, value, **evidence):
    return SimpleNamespace(
        value=value,
        evidence=ProviderActionEvidence(
            provider=provider,
            action=action,
            state=ProviderActionState.SUCCEEDED,
            project_ref=binding.project_ref,
            repository_identity_digest=binding.repository_identity_digest,
            **evidence,
        ),
    )


class BindingResolver:
    def __init__(self, binding: ProviderProjectBinding):
        self.binding = binding

    def resolve(self, project_id: str) -> ProviderProjectBinding:
        if project_id != self.binding.project_ref:
            raise ProjectRepositoryBindingError("canonical Project mismatch")
        return self.binding


class FakeGitHubActions:
    def __init__(self, binding: ProviderProjectBinding):
        self.binding = binding
        self.head_revision = ROOT_REVISION
        self.default_branch = "main"
        self.files = {"app.py": "value = 1\n", "README.md": "Parallax\n"}
        self.mutations: list[str] = []
        self.committed_files = ()

    def resolve_repository(self, binding, invocation):
        assert binding == self.binding
        value = GitHubRepositoryState(REPOSITORY_REF, self.default_branch, self.head_revision)
        return _action_success(
            binding,
            provider="github",
            action="repository.resolve",
            value=value,
            source_revision=self.head_revision,
            result_identity=self.head_revision,
        )

    def read_tree(self, binding, invocation, *, source_revision):
        assert binding == self.binding
        assert source_revision == self.head_revision
        entries = tuple(
            GitHubTreeEntry(path, "file", len(content.encode()), f"obj{index}")
            for index, (path, content) in enumerate(sorted(self.files.items()), start=1)
        )
        value = GitHubTreeResult(REPOSITORY_REF, source_revision, entries)
        return _action_success(
            binding,
            provider="github",
            action="source.tree.read",
            value=value,
            source_revision=source_revision,
            result_identity=source_revision,
        )

    def read_file(self, binding, invocation, *, source_revision, path):
        assert binding == self.binding
        content = self.files[path]
        digest = sha256(content.encode()).hexdigest()
        value = GitHubFileResult(REPOSITORY_REF, source_revision, path, content, digest)
        return _action_success(
            binding,
            provider="github",
            action="source.file.read",
            value=value,
            source_revision=source_revision,
            result_identity=digest,
        )

    def create_branch(self, binding, invocation, *, branch_name, base_revision):
        self.mutations.append("branch.create")
        assert base_revision == ROOT_REVISION
        value = GitHubBranchResult(REPOSITORY_REF, branch_name, base_revision, base_revision)
        return _action_success(
            binding,
            provider="github",
            action="branch.create",
            value=value,
            source_revision=base_revision,
            result_identity=branch_name,
        )

    def commit_accepted_lineage(
        self,
        binding,
        invocation,
        *,
        branch_name,
        expected_parent_revision,
        lineage,
        files,
    ):
        self.mutations.append("commit.write")
        assert expected_parent_revision == ROOT_REVISION
        self.committed_files = files
        value = GitHubCommitResult(
            REPOSITORY_REF,
            branch_name,
            expected_parent_revision,
            COMMIT_REVISION,
            lineage.lineage_id,
            lineage.content_digest,
        )
        return _action_success(
            binding,
            provider="github",
            action="commit.write",
            value=value,
            source_revision=COMMIT_REVISION,
            lineage_id=lineage.lineage_id,
            lineage_digest=lineage.content_digest,
            result_identity=COMMIT_REVISION,
        )

    def create_pull_request(
        self,
        binding,
        invocation,
        *,
        head_branch,
        expected_head_revision,
        base_branch,
        lineage,
        title,
        body="",
    ):
        self.mutations.append("pull_request.create")
        assert expected_head_revision == COMMIT_REVISION
        value = GitHubPullRequestResult(
            REPOSITORY_REF,
            7,
            head_branch,
            expected_head_revision,
            base_branch,
            "OPEN",
            "https://github.com/Ryan9876/parallax/pull/7",
        )
        return _action_success(
            binding,
            provider="github",
            action="pull_request.create",
            value=value,
            source_revision=expected_head_revision,
            lineage_id=lineage.lineage_id,
            lineage_digest=lineage.content_digest,
            result_identity="7",
            safe_url=value.url,
        )

    def read_pull_request(self, binding, invocation, *, number):
        self.mutations.append("pull_request.read")
        branch = f"parallax/{binding.project_ref[:8]}-{self.run_id[:8]}"
        value = GitHubPullRequestResult(
            REPOSITORY_REF,
            number,
            branch,
            COMMIT_REVISION,
            self.default_branch,
            "OPEN",
            "https://github.com/Ryan9876/parallax/pull/7",
        )
        return _action_success(
            binding,
            provider="github",
            action="pull_request.read",
            value=value,
            source_revision=COMMIT_REVISION,
            result_identity="7",
            safe_url=value.url,
        )


class FakeVercelActions:
    def __init__(self):
        self.calls: list[str] = []

    def create_preview(self, target, invocation, *, source_revision, branch_name, lineage):
        self.calls.append("preview.create")
        value = VercelPreviewResult(
            target.vercel_project_ref,
            target.repository_ref,
            "dpl_preview_1",
            source_revision,
            VercelPreviewStatus.READY,
            "https://parallax-preview.vercel.app",
        )
        binding = ProviderProjectBinding(target.project_ref, target.repository_ref)
        return _action_success(
            binding,
            provider="vercel",
            action="preview.create",
            value=value,
            source_revision=source_revision,
            lineage_id=lineage.lineage_id,
            lineage_digest=lineage.content_digest,
            result_identity=value.deployment_id,
            result_status="PREVIEW_READY",
            safe_url=value.url,
        )

    def read_preview(self, target, invocation, *, deployment_id, expected_source_revision):
        self.calls.append("preview.read")
        value = VercelPreviewResult(
            target.vercel_project_ref,
            target.repository_ref,
            deployment_id,
            expected_source_revision,
            VercelPreviewStatus.READY,
            "https://parallax-preview.vercel.app",
        )
        binding = ProviderProjectBinding(target.project_ref, target.repository_ref)
        return _action_success(
            binding,
            provider="vercel",
            action="preview.read",
            value=value,
            source_revision=expected_source_revision,
            result_identity=deployment_id,
            result_status="PREVIEW_STATUS_READY",
            safe_url=value.url,
        )


def _allocator(tmp_path, objects=None, metadata=None):
    objects = objects or InMemoryImmutableObjectStore()
    metadata = metadata or InMemoryLineageMetadataStore()
    store = SourceLineageStore(objects, metadata)
    return ProjectWorkspaceAllocator(tmp_path, lineage_store=store), store, objects, metadata


def _factory():
    return ScopedProviderInvocationFactory(
        github_capability_id="cap:github-source-delivery",
        vercel_capability_id="cap:vercel-preview",
        actor_ref="actor:parallax-runtime",
    )


def _bootstrap(tmp_path, project_id: str, run_id: str, github=None, objects=None, metadata=None):
    binding = ProviderProjectBinding(project_id, REPOSITORY_REF)
    github = github or FakeGitHubActions(binding)
    github.run_id = run_id
    allocator, store, objects, metadata = _allocator(tmp_path, objects, metadata)
    bootstrap = RepositoryLineageBootstrap(
        allocator=allocator,
        projects=BindingResolver(binding),
        github=github,
        invocations=_factory(),
    )
    run = _run(project_id, run_id)
    return bootstrap, allocator, store, github, run, objects, metadata, binding


def _accept_implementation(allocator, identity: ProjectRunIdentity):
    workspace = allocator.resolve(identity)
    try:
        (workspace.path / "app.py").write_text("value = 2\n", encoding="utf-8")
        return allocator.accept_implementation(
            workspace,
            expected_parent_lineage_id=workspace.lineage.lineage_id,
        )
    finally:
        allocator.cleanup(workspace)


def _review_run(project_id: str, run_id: str, accepted):
    return _run(
        project_id,
        run_id,
        state="REVIEW",
        attempts=(
            _attempt(
                "IMPLEMENT",
                {
                    "project_ref": project_id,
                    "run_id": run_id,
                    "source_lineage_ref": accepted.lineage_id,
                },
            ),
            _attempt(
                "VERIFY",
                {
                    "project_ref": project_id,
                    "run_id": run_id,
                    "source_lineage_ref": accepted.lineage_id,
                    "lineage_bound_execution": True,
                    "protected_success": True,
                },
            ),
        ),
    )


def test_owner_scoped_project_repository_binding_is_canonical(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'projects.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        service = ProjectService(ProjectRepository(session))
        project = service.create(
            owner_subject="owner-a",
            request=ProjectCreate(name="Parallax", repository_ref=REPOSITORY_REF),
        )
        resolver = OwnerScopedProjectBindingResolver(ProjectRepository(session), owner_subject="owner-a")
        binding = resolver.resolve(project.id)
        assert binding.project_ref == project.id
        assert binding.repository_ref == REPOSITORY_REF

        denied = OwnerScopedProjectBindingResolver(ProjectRepository(session), owner_subject="owner-b")
        with pytest.raises(ProjectRepositoryBindingError):
            denied.resolve(project.id)


def test_repository_bootstrap_is_durable_idempotent_and_survives_allocator_recreation(tmp_path):
    project_id, run_id = str(uuid4()), str(uuid4())
    bootstrap, allocator, _, github, run, objects, metadata, _ = _bootstrap(
        tmp_path / "first", project_id, run_id
    )
    first = bootstrap.ensure(run, operation_key="run:first")
    again = bootstrap.ensure(run, operation_key="run:retry")

    assert first.initialized is True
    assert again.initialized is False
    assert again.lineage == first.lineage
    assert first.lineage.source_ref_digest == sha256(f"{REPOSITORY_REF}@{ROOT_REVISION}".encode()).hexdigest()
    assert not any((tmp_path / "first" / "live").rglob("*"))

    recreated, _, _, recreated_github, recreated_run, _, _, _ = _bootstrap(
        tmp_path / "second", project_id, run_id, github=github, objects=objects, metadata=metadata
    )
    replay = recreated.ensure(recreated_run, operation_key="run:recreated")
    assert replay.initialized is False
    assert replay.lineage == first.lineage
    assert recreated_github.mutations == []


def test_competing_initial_source_cannot_replace_durable_root(tmp_path):
    project_id, run_id = str(uuid4()), str(uuid4())
    bootstrap, allocator, store, github, run, _, _, _ = _bootstrap(tmp_path, project_id, run_id)
    first = bootstrap.ensure(run, operation_key="bootstrap:first").lineage

    class ChangedSource:
        def load(self, identity):
            return SourcePackage("repository", f"{REPOSITORY_REF}@otherrev", {"app.py": b"different\n"})

    with pytest.raises(StaleLineageError):
        store.initialize(ProjectRunIdentity(project_id, run_id), ChangedSource())
    assert allocator.current_lineage(ProjectRunIdentity(project_id, run_id)) == first


def test_verified_delivery_publishes_only_exact_current_lineage_and_preview(tmp_path):
    project_id, run_id = str(uuid4()), str(uuid4())
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(tmp_path, project_id, run_id)
    root = bootstrap.ensure(run, operation_key="bootstrap").lineage
    accepted = _accept_implementation(allocator, ProjectRunIdentity(project_id, run_id))
    assert accepted.parent_lineage_id == root.lineage_id
    github.run_id = run_id
    vercel = FakeVercelActions()
    target = VercelPreviewTarget(project_id, REPOSITORY_REF, "vercel-project-parallax")
    delivery = VerifiedLineageDelivery(
        allocator=allocator,
        projects=BindingResolver(binding),
        preview_targets=RegisteredPreviewTargetResolver((target,)),
        github=github,
        vercel=vercel,
        invocations=_factory(),
    )

    result = delivery.deliver(_review_run(project_id, run_id, accepted), operation_key="deliver")

    assert result.lineage_id == accepted.lineage_id
    assert result.content_digest == accepted.content_digest
    assert result.commit_revision == COMMIT_REVISION
    assert result.preview_status == "READY"
    assert github.mutations == ["branch.create", "commit.write", "pull_request.create", "pull_request.read"]
    assert vercel.calls == ["preview.create", "preview.read"]
    committed = {item.path: item.content for item in github.committed_files}
    assert committed == {"README.md": "Parallax\n", "app.py": "value = 2\n"}
    assert all(item.state is ProviderActionState.SUCCEEDED for item in result.evidence)
    assert not any((tmp_path / "live").rglob("*"))


def test_unverified_or_stale_provider_parent_fails_before_provider_mutation(tmp_path):
    project_id, run_id = str(uuid4()), str(uuid4())
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(tmp_path, project_id, run_id)
    bootstrap.ensure(run, operation_key="bootstrap")
    accepted = _accept_implementation(allocator, ProjectRunIdentity(project_id, run_id))
    github.run_id = run_id
    vercel = FakeVercelActions()
    delivery = VerifiedLineageDelivery(
        allocator=allocator,
        projects=BindingResolver(binding),
        preview_targets=RegisteredPreviewTargetResolver(
            (VercelPreviewTarget(project_id, REPOSITORY_REF, "vercel-project-parallax"),)
        ),
        github=github,
        vercel=vercel,
        invocations=_factory(),
    )

    unverified = _run(project_id, run_id, state="REVIEW", attempts=())
    with pytest.raises(VerifiedDeliveryError):
        delivery.deliver(unverified, operation_key="unverified")
    assert github.mutations == [] and vercel.calls == []

    github.head_revision = "movedrevision"
    with pytest.raises(VerifiedDeliveryError, match="repository parent moved"):
        delivery.deliver(_review_run(project_id, run_id, accepted), operation_key="stale")
    assert github.mutations == [] and vercel.calls == []


def test_cross_project_bootstrap_and_unregistered_preview_target_fail_closed(tmp_path):
    project_id, run_id, other_project = str(uuid4()), str(uuid4()), str(uuid4())
    binding = ProviderProjectBinding(other_project, REPOSITORY_REF)
    github = FakeGitHubActions(binding)
    github.run_id = run_id
    allocator, _, _, _ = _allocator(tmp_path)
    bootstrap = RepositoryLineageBootstrap(
        allocator=allocator,
        projects=BindingResolver(binding),
        github=github,
        invocations=_factory(),
    )
    with pytest.raises(ProjectRepositoryBindingError):
        bootstrap.ensure(_run(project_id, run_id), operation_key="cross-project")

    resolver = RegisteredPreviewTargetResolver(
        (VercelPreviewTarget(other_project, REPOSITORY_REF, "vercel-other"),)
    )
    with pytest.raises(VerifiedDeliveryError):
        resolver.resolve(ProviderProjectBinding(project_id, REPOSITORY_REF))


def test_invocation_factory_allows_only_fixed_github_and_preview_actions():
    factory = _factory()
    github = factory.for_action(tool="github", action="branch.create", operation_key="op")
    preview = factory.for_action(tool="vercel", action="preview.create", operation_key="op")
    assert github.capability_id == "cap:github-source-delivery"
    assert preview.capability_id == "cap:vercel-preview"
    assert "op" not in github.request_id

    with pytest.raises(ValueError):
        factory.for_action(tool="github", action="merge", operation_key="op")
    with pytest.raises(ValueError):
        factory.for_action(tool="vercel", action="production.promote", operation_key="op")
    with pytest.raises(ValueError):
        factory.for_action(tool="http", action="request", operation_key="op")
