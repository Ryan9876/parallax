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
    EngineeringAttemptDeliveryRecordStore,
    OwnerScopedProjectBindingResolver,
    ProjectRepositoryBindingError,
    RegisteredPreviewTargetResolver,
    RepositoryLineageBootstrap,
    ScopedProviderInvocationFactory,
    SourceBootstrapError,
    VerifiedDeliveryError,
    VerifiedLineageDelivery,
    publication_branch_name,
)
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import (
    ProjectRunIdentity,
    SourceLineageStore,
    SourcePackage,
    StaleLineageError,
)
from parallax_api.db import Base, make_engine
from parallax_api.models import EngineeringAttempt, EngineeringRun
from parallax_api.projects.repository import ProjectRepository
from parallax_api.projects.schemas import ProjectCreate
from parallax_api.projects.service import ProjectService
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.tools.contracts import (
    ToolAuditRecord,
    ToolConsequence,
    ToolOutcome,
)
from parallax_api.tools.providers import (
    GitHubBranchResult,
    GitHubCommitResult,
    GitHubFileResult,
    GitHubPullRequestResult,
    GitHubRepositoryState,
    GitHubTreeEntry,
    GitHubTreeResult,
    ProviderActionEvidence,
    ProviderActionFailed,
    ProviderActionState,
    ProviderProjectBinding,
    VercelPreviewResult,
    VercelPreviewStatus,
    VercelPreviewTarget,
)
from parallax_api.tools.providers.common import ProviderActionSuccess


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
    provider_evidence = ProviderActionEvidence(
        provider=provider,
        action=action,
        state=ProviderActionState.SUCCEEDED,
        project_ref=binding.project_ref,
        repository_identity_digest=binding.repository_identity_digest,
        **evidence,
    )
    request_id = f"request:{uuid4().hex}"
    result_code = provider_evidence.result_status or "TEST_SUCCEEDED"
    result_identity = provider_evidence.result_identity
    audit = ToolAuditRecord(
        request_id=request_id,
        capability_id=f"cap:test-{provider}",
        project_ref=binding.project_ref,
        tool=provider,
        action=action,
        actor_ref="actor:test-runtime",
        consequence=(
            ToolConsequence.READ
            if action in {
                "repository.resolve",
                "source.tree.read",
                "source.file.read",
                "pull_request.read",
                "preview.read",
            }
            else ToolConsequence.MUTATE
        ),
        authority_allowed=True,
        outcome=ToolOutcome.SUCCEEDED,
        deny_reason=None,
        approval_id=None,
        request_digest=sha256(f"{request_id}|{provider}|{action}".encode()).hexdigest(),
        result_digest=sha256(f"{result_code}|{result_identity or ''}".encode()).hexdigest(),
        result_code=result_code,
        result_identity=result_identity,
    )
    return ProviderActionSuccess(value=value, evidence=provider_evidence, audit=audit)


def _action_failure(
    binding: ProviderProjectBinding,
    *,
    provider: str,
    action: str,
    result_code: str,
    source_revision: str | None = None,
    result_identity: str | None = None,
) -> ProviderActionFailed:
    evidence = ProviderActionEvidence(
        provider=provider,
        action=action,
        state=ProviderActionState.FAILED,
        project_ref=binding.project_ref,
        repository_identity_digest=binding.repository_identity_digest,
        source_revision=source_revision,
        result_identity=result_identity,
        result_status=result_code,
    )
    request_id = f"request:{uuid4().hex}"
    audit = ToolAuditRecord(
        request_id=request_id,
        capability_id=f"cap:test-{provider}",
        project_ref=binding.project_ref,
        tool=provider,
        action=action,
        actor_ref="actor:test-runtime",
        consequence=ToolConsequence.MUTATE,
        authority_allowed=True,
        outcome=ToolOutcome.FAILED,
        deny_reason=None,
        approval_id=None,
        request_digest=sha256(f"{request_id}|{provider}|{action}".encode()).hexdigest(),
        result_digest=sha256(f"{result_code}|{result_identity or ''}".encode()).hexdigest(),
        result_code=result_code,
        result_identity=result_identity,
    )
    return ProviderActionFailed(evidence=evidence, audit=audit)


class MemoryDeliveryRecordStore:
    def __init__(self):
        self.records: dict[tuple[str, str], dict[str, object]] = {}

    @staticmethod
    def _copy(payload: dict[str, object]) -> dict[str, object]:
        return json.loads(json.dumps(payload, sort_keys=True))

    def load(self, *, run_id: str, lineage_id: str):
        payload = self.records.get((run_id, lineage_id))
        return None if payload is None else self._copy(payload)

    def persist(self, *, run, lineage_id: str, payload: dict[str, object]):
        key = (run.id, lineage_id)
        current = self.records.get(key)
        if current is not None:
            if current != payload:
                raise VerifiedDeliveryError("conflicting in-memory delivery record")
            return self._copy(current), True
        self.records[key] = self._copy(payload)
        return self._copy(payload), False


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
        self.calls: list[str] = []
        self.mutations: list[str] = []
        self.committed_files = ()
        self.last_branch: str | None = None

    def resolve_repository(self, binding, invocation):
        self.calls.append("repository.resolve")
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
        self.calls.append("source.tree.read")
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
        self.calls.append("source.file.read")
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
        self.calls.append("branch.create")
        self.mutations.append("branch.create")
        assert base_revision == ROOT_REVISION
        self.last_branch = branch_name
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
        self.calls.append("commit.write")
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
        self.calls.append("pull_request.create")
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
        self.calls.append("pull_request.read")
        self.mutations.append("pull_request.read")
        branch = self.last_branch
        assert branch is not None
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


def _delete_implementation_file(allocator, identity: ProjectRunIdentity, path: str):
    workspace = allocator.resolve(identity)
    try:
        (workspace.path / path).unlink()
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


def _delivery(allocator, binding, github, vercel, project_id, *, records=None):
    return VerifiedLineageDelivery(
        allocator=allocator,
        projects=BindingResolver(binding),
        preview_targets=RegisteredPreviewTargetResolver(
            (VercelPreviewTarget(project_id, REPOSITORY_REF, "vercel-project-parallax"),)
        ),
        github=github,
        vercel=vercel,
        invocations=_factory(),
        records=records or MemoryDeliveryRecordStore(),
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


def test_verified_delivery_publishes_only_exact_current_lineage_delta_and_preview(tmp_path):
    project_id, run_id = str(uuid4()), str(uuid4())
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(tmp_path, project_id, run_id)
    root = bootstrap.ensure(run, operation_key="bootstrap").lineage
    accepted = _accept_implementation(allocator, ProjectRunIdentity(project_id, run_id))
    assert accepted.parent_lineage_id == root.lineage_id
    github.run_id = run_id
    vercel = FakeVercelActions()
    delivery = _delivery(allocator, binding, github, vercel, project_id)

    result = delivery.deliver(_review_run(project_id, run_id, accepted), operation_key="deliver")

    assert result.lineage_id == accepted.lineage_id
    assert result.content_digest == accepted.content_digest
    assert result.branch_name == publication_branch_name(ProjectRunIdentity(project_id, run_id), accepted.lineage_id)
    assert result.commit_revision == COMMIT_REVISION
    assert result.preview_status == "READY"
    assert result.replayed is False
    assert github.mutations == ["branch.create", "commit.write", "pull_request.create", "pull_request.read"]
    assert vercel.calls == ["preview.create", "preview.read"]
    committed = {item.path: item.content for item in github.committed_files}
    assert committed == {"app.py": "value = 2\n"}
    assert len(result.actions) == 7
    assert result.evidence == tuple(item.evidence for item in result.actions)
    assert result.audits == tuple(item.audit for item in result.actions)
    assert all(item.state is ProviderActionState.SUCCEEDED for item in result.evidence)
    assert all(item.outcome is ToolOutcome.SUCCEEDED for item in result.audits)
    assert all(item.authority_allowed is True for item in result.audits)
    assert not any((tmp_path / "live").rglob("*"))


def test_large_accepted_lineage_submits_only_changed_file_delta(tmp_path):
    project_id, run_id = str(uuid4()), str(uuid4())
    binding = ProviderProjectBinding(project_id, REPOSITORY_REF)
    github = FakeGitHubActions(binding)
    github.files = {"app.py": "value = 1\n"}
    github.files.update({f"src/file-{index:02d}.txt": f"unchanged-{index}\n" for index in range(40)})
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(
        tmp_path,
        project_id,
        run_id,
        github=github,
    )
    root = bootstrap.ensure(run, operation_key="bootstrap:large").lineage
    assert root.file_count == 41
    accepted = _accept_implementation(allocator, ProjectRunIdentity(project_id, run_id))
    github.run_id = run_id
    vercel = FakeVercelActions()

    result = _delivery(allocator, binding, github, vercel, project_id).deliver(
        _review_run(project_id, run_id, accepted),
        operation_key="deliver:large",
    )

    assert result.preview_status == "READY"
    assert len(github.committed_files) == 1
    assert github.committed_files[0].path == "app.py"
    assert github.committed_files[0].content == "value = 2\n"


def test_accepted_deletion_fails_before_provider_mutation(tmp_path):
    project_id, run_id = str(uuid4()), str(uuid4())
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(tmp_path, project_id, run_id)
    bootstrap.ensure(run, operation_key="bootstrap:delete")
    accepted = _delete_implementation_file(
        allocator,
        ProjectRunIdentity(project_id, run_id),
        "README.md",
    )
    github.run_id = run_id
    vercel = FakeVercelActions()

    with pytest.raises(VerifiedDeliveryError, match="deletions outside bounded GitHub commit surface"):
        _delivery(allocator, binding, github, vercel, project_id).deliver(
            _review_run(project_id, run_id, accepted),
            operation_key="deliver:delete",
        )

    assert github.mutations == []
    assert vercel.calls == []


def test_durable_delivery_record_survives_session_recreation_and_retry_has_no_provider_calls(tmp_path):
    project_id, run_id = str(uuid4()), str(uuid4())
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(
        tmp_path / "lineage", project_id, run_id
    )
    bootstrap.ensure(run, operation_key="bootstrap")
    accepted = _accept_implementation(allocator, ProjectRunIdentity(project_id, run_id))
    github.run_id = run_id

    engine = make_engine(f"sqlite:///{tmp_path / 'delivery.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    implementation_evidence = {
        "project_ref": project_id,
        "run_id": run_id,
        "source_lineage_ref": accepted.lineage_id,
    }
    verify_evidence = {
        "project_ref": project_id,
        "run_id": run_id,
        "source_lineage_ref": accepted.lineage_id,
        "lineage_bound_execution": True,
        "protected_success": True,
    }

    with Session() as session:
        session.add(
            EngineeringRun(
                id=run_id,
                conversation_id=str(uuid4()),
                spec_id="P2-V0.15.9",
                project_id=project_id,
                state="REVIEW",
                revision=9,
            )
        )
        session.add_all(
            [
                EngineeringAttempt(
                    run_id=run_id,
                    stage="IMPLEMENT",
                    attempt_number=1,
                    operation_key="implement:accepted",
                    status="PASSED",
                    evidence_json=json.dumps(implementation_evidence),
                ),
                EngineeringAttempt(
                    run_id=run_id,
                    stage="VERIFY",
                    attempt_number=1,
                    operation_key="verify:accepted",
                    status="PASSED",
                    evidence_json=json.dumps(verify_evidence),
                ),
            ]
        )
        session.commit()
        repository = EngineeringRunRepository(session)
        records = EngineeringAttemptDeliveryRecordStore(repository)
        durable_run = repository.get(run_id)
        assert durable_run is not None
        vercel = FakeVercelActions()
        first = _delivery(
            allocator,
            binding,
            github,
            vercel,
            project_id,
            records=records,
        ).deliver(durable_run, operation_key="runtime:first")

        assert first.replayed is False
        assert repository.get(run_id).revision == 9
        attempt = repository.find_operation(
            run_id,
            EngineeringAttemptDeliveryRecordStore.operation_key(accepted.lineage_id),
        )
        assert attempt is not None
        assert attempt.stage == "SOURCE_DELIVERY"
        assert attempt.status == "RECORDED"
        assert len(attempt.evidence_json.encode("utf-8")) <= 24_000
        payload = json.loads(attempt.evidence_json)
        assert payload["project_id"] == project_id
        assert payload["run_id"] == run_id
        assert payload["lineage_id"] == accepted.lineage_id
        assert len(payload["actions"]) == 7
        assert all("evidence" in item and "audit" in item for item in payload["actions"])

    with Session() as recreated_session:
        repository = EngineeringRunRepository(recreated_session)
        records = EngineeringAttemptDeliveryRecordStore(repository)
        recreated_run = repository.get(run_id)
        assert recreated_run is not None
        recreated_github = FakeGitHubActions(binding)
        recreated_github.run_id = run_id
        recreated_vercel = FakeVercelActions()
        recreated_delivery = _delivery(
            allocator,
            binding,
            recreated_github,
            recreated_vercel,
            project_id,
            records=records,
        )

        resolved = recreated_delivery.resolve_record(recreated_run)
        assert resolved is not None and resolved.replayed is True
        assert resolved.commit_revision == first.commit_revision
        assert resolved.pull_request_number == first.pull_request_number
        assert resolved.preview_deployment_id == first.preview_deployment_id

        retry = recreated_delivery.deliver(recreated_run, operation_key="runtime:exact-retry")
        assert retry.replayed is True
        assert retry.commit_revision == first.commit_revision
        assert retry.pull_request_number == first.pull_request_number
        assert retry.preview_deployment_id == first.preview_deployment_id
        assert retry.actions == first.actions
        assert recreated_github.calls == []
        assert recreated_vercel.calls == []
        assert repository.get(run_id).revision == 9


def test_unverified_or_stale_provider_parent_fails_before_provider_mutation(tmp_path):
    project_id, run_id = str(uuid4()), str(uuid4())
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(tmp_path, project_id, run_id)
    bootstrap.ensure(run, operation_key="bootstrap")
    accepted = _accept_implementation(allocator, ProjectRunIdentity(project_id, run_id))
    github.run_id = run_id
    vercel = FakeVercelActions()
    delivery = _delivery(allocator, binding, github, vercel, project_id)

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


def test_publication_branch_name_uses_full_lineage_identity_and_fails_closed() -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    identity = ProjectRunIdentity(project_id, run_id)
    first = "src:" + "a" * 64
    second = "src:" + "b" * 64

    first_branch = publication_branch_name(identity, first)
    assert first_branch == f"parallax/{project_id[:8]}-{run_id[:8]}-{first[4:]}"
    assert publication_branch_name(identity, first) == first_branch
    assert publication_branch_name(identity, second) != first_branch
    assert publication_branch_name(identity, second).startswith(f"parallax/{project_id[:8]}-{run_id[:8]}-")

    malformed = (None, "", "src:" + "a" * 63, "src:" + "A" * 64, "src:" + "g" * 64, "sha:" + "a" * 64)
    for value in malformed:
        with pytest.raises(VerifiedDeliveryError, match="lineage identity"):
            publication_branch_name(identity, value)  # type: ignore[arg-type]
    with pytest.raises(VerifiedDeliveryError, match="Project/run identity"):
        publication_branch_name(SimpleNamespace(project_id=project_id, run_id=run_id), first)  # type: ignore[arg-type]


def test_same_run_replacement_lineages_publish_to_distinct_branches_and_preserve_prior_record(tmp_path) -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(tmp_path, project_id, run_id)
    bootstrap.ensure(run, operation_key="bootstrap")
    identity = ProjectRunIdentity(project_id, run_id)
    first_lineage = _accept_implementation(allocator, identity)
    records = MemoryDeliveryRecordStore()
    delivery = _delivery(allocator, binding, github, FakeVercelActions(), project_id, records=records)

    first = delivery.deliver(_review_run(project_id, run_id, first_lineage), operation_key="deliver:first")

    workspace = allocator.resolve(identity)
    try:
        (workspace.path / "app.py").write_text("value = 3\n", encoding="utf-8")
        second_lineage = allocator.accept_implementation(
            workspace, expected_parent_lineage_id=workspace.lineage.lineage_id
        )
    finally:
        allocator.cleanup(workspace)

    second = delivery.deliver(_review_run(project_id, run_id, second_lineage), operation_key="deliver:second")

    assert first.branch_name == publication_branch_name(identity, first_lineage.lineage_id)
    assert second.branch_name == publication_branch_name(identity, second_lineage.lineage_id)
    assert first.branch_name != second.branch_name
    assert records.records[(run_id, first_lineage.lineage_id)]["branch_name"] == first.branch_name
    assert records.records[(run_id, second_lineage.lineage_id)]["branch_name"] == second.branch_name
    assert github.mutations.count("branch.create") == 2
    assert github.mutations.count("commit.write") == 2
    assert github.mutations.count("pull_request.create") == 2


def test_durable_delivery_store_persists_multiple_same_run_lineages_without_run_transition(tmp_path) -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    first_lineage = "src:" + "1" * 64
    second_lineage = "src:" + "2" * 64
    engine = make_engine(f"sqlite:///{tmp_path / 'same-run-delivery.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        session.add(
            EngineeringRun(
                id=run_id,
                conversation_id=str(uuid4()),
                spec_id="P2-V0.23.43",
                project_id=project_id,
                state="REVIEW",
                revision=12,
            )
        )
        session.commit()
        repository = EngineeringRunRepository(session)
        records = EngineeringAttemptDeliveryRecordStore(repository)
        run = repository.get(run_id)
        assert run is not None
        first_payload = {"project_id": project_id, "run_id": run_id, "lineage_id": first_lineage, "branch_name": "legacy-branch"}
        second_payload = {"project_id": project_id, "run_id": run_id, "lineage_id": second_lineage, "branch_name": "replacement-branch"}

        stored_first, replayed_first = records.persist(run=run, lineage_id=first_lineage, payload=first_payload)
        stored_second, replayed_second = records.persist(run=run, lineage_id=second_lineage, payload=second_payload)
        exact_replay, replayed_exact = records.persist(run=run, lineage_id=first_lineage, payload=first_payload)

        assert stored_first == first_payload and replayed_first is False
        assert stored_second == second_payload and replayed_second is False
        assert exact_replay == first_payload and replayed_exact is True
        first_attempt = repository.find_operation(run_id, records.operation_key(first_lineage))
        second_attempt = repository.find_operation(run_id, records.operation_key(second_lineage))
        assert first_attempt is not None and first_attempt.attempt_number == 1
        assert second_attempt is not None and second_attempt.attempt_number == 2
        assert first_attempt.operation_key != second_attempt.operation_key
        assert records.load(run_id=run_id, lineage_id=first_lineage) == first_payload
        assert records.load(run_id=run_id, lineage_id=second_lineage) == second_payload
        refreshed = repository.get(run_id)
        assert refreshed is not None and refreshed.state == "REVIEW" and refreshed.revision == 12


def test_durable_delivery_store_retries_only_database_attempt_number_collision_once(tmp_path, monkeypatch) -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    existing_lineage = "src:" + "3" * 64
    target_lineage = "src:" + "4" * 64
    engine = make_engine(f"sqlite:///{tmp_path / 'delivery-race.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        session.add(
            EngineeringRun(
                id=run_id,
                conversation_id=str(uuid4()),
                spec_id="P2-V0.23.43",
                project_id=project_id,
                state="REVIEW",
                revision=12,
            )
        )
        session.add(
            EngineeringAttempt(
                run_id=run_id,
                stage="SOURCE_DELIVERY",
                attempt_number=1,
                operation_key=EngineeringAttemptDeliveryRecordStore.operation_key(existing_lineage),
                status="RECORDED",
                evidence_json=json.dumps({"project_id": project_id, "run_id": run_id, "lineage_id": existing_lineage}),
            )
        )
        session.commit()
        repository = EngineeringRunRepository(session)
        records = EngineeringAttemptDeliveryRecordStore(repository)
        run = repository.get(run_id)
        assert run is not None
        payload = {"project_id": project_id, "run_id": run_id, "lineage_id": target_lineage, "branch_name": "target"}

        original_scalar = session.scalar
        max_reads = 0

        def stale_once(statement, *args, **kwargs):
            nonlocal max_reads
            rendered = str(statement)
            if "max(engineering_attempts.attempt_number)" in rendered:
                max_reads += 1
                if max_reads == 1:
                    return 0
            return original_scalar(statement, *args, **kwargs)

        monkeypatch.setattr(session, "scalar", stale_once)
        stored, replayed = records.persist(run=run, lineage_id=target_lineage, payload=payload)

        assert stored == payload and replayed is False
        target_attempt = repository.find_operation(run_id, records.operation_key(target_lineage))
        assert target_attempt is not None and target_attempt.attempt_number == 2
        assert max_reads == 2
        refreshed = repository.get(run_id)
        assert refreshed is not None and refreshed.state == "REVIEW" and refreshed.revision == 12


def test_durable_delivery_store_fails_after_one_unresolved_attempt_number_retry(tmp_path, monkeypatch) -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    target_lineage = "src:" + "7" * 64
    engine = make_engine(f"sqlite:///{tmp_path / 'delivery-race-fail.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        session.add(
            EngineeringRun(
                id=run_id,
                conversation_id=str(uuid4()),
                spec_id="P2-V0.23.43",
                project_id=project_id,
                state="REVIEW",
                revision=12,
            )
        )
        for number, digit in ((1, "5"), (2, "6")):
            lineage = "src:" + digit * 64
            session.add(
                EngineeringAttempt(
                    run_id=run_id,
                    stage="SOURCE_DELIVERY",
                    attempt_number=number,
                    operation_key=EngineeringAttemptDeliveryRecordStore.operation_key(lineage),
                    status="RECORDED",
                    evidence_json=json.dumps({"project_id": project_id, "run_id": run_id, "lineage_id": lineage}),
                )
            )
        session.commit()
        repository = EngineeringRunRepository(session)
        records = EngineeringAttemptDeliveryRecordStore(repository)
        run = repository.get(run_id)
        assert run is not None
        payload = {"project_id": project_id, "run_id": run_id, "lineage_id": target_lineage, "branch_name": "target"}

        original_scalar = session.scalar
        forced = iter((0, 1))

        def two_stale_reads(statement, *args, **kwargs):
            rendered = str(statement)
            if "max(engineering_attempts.attempt_number)" in rendered:
                return next(forced)
            return original_scalar(statement, *args, **kwargs)

        monkeypatch.setattr(session, "scalar", two_stale_reads)
        with pytest.raises(VerifiedDeliveryError, match="concurrent durable delivery record conflicted"):
            records.persist(run=run, lineage_id=target_lineage, payload=payload)
        assert repository.find_operation(run_id, records.operation_key(target_lineage)) is None
        refreshed = repository.get(run_id)
        assert refreshed is not None and refreshed.state == "REVIEW" and refreshed.revision == 12


class BranchConflictReplayGitHubActions(FakeGitHubActions):
    def create_branch(self, binding, invocation, *, branch_name, base_revision):
        self.calls.append("branch.create")
        assert base_revision == ROOT_REVISION
        self.last_branch = branch_name
        raise _action_failure(
            binding,
            provider="github",
            action="branch.create",
            result_code="BRANCH_CONFLICT",
            source_revision=base_revision,
            result_identity=branch_name,
        )


class BranchConflictMismatchGitHubActions(BranchConflictReplayGitHubActions):
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
        self.calls.append("commit.write")
        raise _action_failure(
            binding,
            provider="github",
            action="commit.write",
            result_code="STALE_PARENT",
            source_revision=expected_parent_revision,
            result_identity=branch_name,
        )


def test_exact_partial_commit_recovers_after_branch_conflict_without_relabeling_failure(tmp_path) -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    binding = ProviderProjectBinding(project_id, REPOSITORY_REF)
    github = BranchConflictReplayGitHubActions(binding)
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(
        tmp_path,
        project_id,
        run_id,
        github=github,
    )
    bootstrap.ensure(run, operation_key="bootstrap")
    identity = ProjectRunIdentity(project_id, run_id)
    accepted = _accept_implementation(allocator, identity)
    records = MemoryDeliveryRecordStore()
    delivery = _delivery(
        allocator,
        binding,
        github,
        FakeVercelActions(),
        project_id,
        records=records,
    )

    result = delivery.deliver(
        _review_run(project_id, run_id, accepted),
        operation_key="deliver:partial-replay",
    )

    assert result.lineage_id == accepted.lineage_id
    assert result.branch_name == publication_branch_name(identity, accepted.lineage_id)
    successful_actions = tuple(pair.evidence.action for pair in result.actions)
    assert "branch.create" not in successful_actions
    assert "commit.write" in successful_actions
    assert "pull_request.create" in successful_actions
    assert "preview.create" in successful_actions
    assert records.load(run_id=run_id, lineage_id=accepted.lineage_id) is not None


def test_arbitrary_partial_branch_head_remains_fail_closed(tmp_path) -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    binding = ProviderProjectBinding(project_id, REPOSITORY_REF)
    github = BranchConflictMismatchGitHubActions(binding)
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(
        tmp_path,
        project_id,
        run_id,
        github=github,
    )
    bootstrap.ensure(run, operation_key="bootstrap")
    identity = ProjectRunIdentity(project_id, run_id)
    accepted = _accept_implementation(allocator, identity)
    vercel = FakeVercelActions()
    delivery = _delivery(allocator, binding, github, vercel, project_id)

    with pytest.raises(ProviderActionFailed) as failed:
        delivery.deliver(
            _review_run(project_id, run_id, accepted),
            operation_key="deliver:partial-mismatch",
        )
    assert failed.value.audit.result_code == "STALE_PARENT"
    assert vercel.calls == []
