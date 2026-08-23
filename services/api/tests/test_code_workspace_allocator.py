from __future__ import annotations

import inspect
from pathlib import Path
from uuid import uuid4

import pytest

from parallax_api.code.workspace_allocator import (
    MaterializedWorkspace,
    ProjectWorkspaceAllocator,
    WorkspaceLeaseError,
)
from parallax_api.code.workspace_lineage import (
    ProjectRunIdentity,
    SourcePackage,
    SourceProvider,
    StaleLineageError,
)


class RepositoryProvider:
    def __init__(self, files: dict[str, bytes]):
        self.files = files
        self.calls: list[ProjectRunIdentity] = []

    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        self.calls.append(identity)
        return SourcePackage(
            source_kind="repository",
            source_ref="github:owner/repo@0123456789abcdef",
            files=self.files,
        )


def identity() -> ProjectRunIdentity:
    return ProjectRunIdentity(str(uuid4()), str(uuid4()))


def test_allocator_public_operations_accept_no_caller_filesystem_root():
    assert tuple(inspect.signature(ProjectWorkspaceAllocator.initialize).parameters) == ("self", "identity", "provider")
    assert tuple(inspect.signature(ProjectWorkspaceAllocator.resolve).parameters) == ("self", "identity", "lineage_id")
    assert tuple(inspect.signature(ProjectWorkspaceAllocator.reconstruct).parameters) == ("self", "identity", "lineage_id")
    assert tuple(inspect.signature(ProjectWorkspaceAllocator.accept_implementation).parameters) == (
        "self",
        "workspace",
        "expected_parent_lineage_id",
    )
    assert tuple(inspect.signature(SourceProvider.load).parameters) == ("self", "identity")


def test_allocator_generates_server_owned_workspace_path_from_hashed_identity(tmp_path):
    allocator = ProjectWorkspaceAllocator(tmp_path / "protected")
    run_identity = identity()
    provider = RepositoryProvider({"src/app.py": b"print('hello')\n"})

    workspace = allocator.initialize(run_identity, provider)

    assert provider.calls == [run_identity]
    assert workspace.path.is_dir()
    assert workspace.path.is_relative_to(allocator.live_root)
    assert workspace.path.parent.name == run_identity.storage_key
    assert workspace.path.name == workspace.lease_id
    assert run_identity.project_id not in str(workspace.path)
    assert run_identity.run_id not in str(workspace.path)
    assert (workspace.path / "src/app.py").read_bytes() == b"print('hello')\n"


def test_forged_or_out_of_root_workspace_lease_is_rejected(tmp_path):
    allocator = ProjectWorkspaceAllocator(tmp_path / "protected")
    run_identity = identity()
    workspace = allocator.initialize(run_identity, RepositoryProvider({"app.py": b"x = 1\n"}))
    outside = tmp_path / "caller-selected"
    outside.mkdir()
    (outside / "app.py").write_bytes(b"x = 2\n")
    forged = MaterializedWorkspace(
        identity=workspace.identity,
        lineage=workspace.lineage,
        lease_id=workspace.lease_id,
        path=outside,
    )

    with pytest.raises(WorkspaceLeaseError):
        allocator.accept_implementation(
            forged,
            expected_parent_lineage_id=workspace.lineage.lineage_id,
        )
    assert allocator.current_lineage(run_identity) == workspace.lineage


def test_implementation_advances_lineage_and_retry_is_idempotent_through_lease(tmp_path):
    allocator = ProjectWorkspaceAllocator(tmp_path / "protected")
    run_identity = identity()
    workspace = allocator.initialize(run_identity, RepositoryProvider({"app.py": b"x = 1\n"}))
    parent = workspace.lineage
    (workspace.path / "app.py").write_bytes(b"x = 2\n")

    accepted = allocator.accept_implementation(
        workspace,
        expected_parent_lineage_id=parent.lineage_id,
    )
    retry = allocator.accept_implementation(
        workspace,
        expected_parent_lineage_id=parent.lineage_id,
    )

    assert retry == accepted
    assert accepted.parent_lineage_id == parent.lineage_id
    assert allocator.current_lineage(run_identity) == accepted

    (workspace.path / "app.py").write_bytes(b"x = 3\n")
    with pytest.raises(StaleLineageError):
        allocator.accept_implementation(
            workspace,
            expected_parent_lineage_id=parent.lineage_id,
        )
    assert allocator.current_lineage(run_identity) == accepted


def test_cleanup_removes_only_live_lease_and_exact_lineage_reconstructs_for_later_stages(tmp_path):
    allocator = ProjectWorkspaceAllocator(tmp_path / "protected")
    run_identity = identity()
    implementation_workspace = allocator.initialize(
        run_identity,
        RepositoryProvider({"src/app.py": b"before\n", "assets/data.bin": b"\x00\x01"}),
    )
    initial = implementation_workspace.lineage
    (implementation_workspace.path / "src/app.py").write_bytes(b"after\n")
    accepted = allocator.accept_implementation(
        implementation_workspace,
        expected_parent_lineage_id=initial.lineage_id,
    )

    allocator.cleanup(implementation_workspace)
    assert not implementation_workspace.path.exists()
    assert allocator.current_lineage(run_identity) == accepted

    build_workspace = allocator.reconstruct(run_identity, accepted.lineage_id)
    test_workspace = allocator.reconstruct(run_identity, accepted.lineage_id)
    verify_workspace = allocator.resolve(run_identity)
    historical_workspace = allocator.reconstruct(run_identity, initial.lineage_id)

    for later in (build_workspace, test_workspace, verify_workspace):
        assert later.path != implementation_workspace.path
        assert later.lineage.lineage_id == accepted.lineage_id
        assert later.lineage.content_digest == accepted.content_digest
        assert (later.path / "src/app.py").read_bytes() == b"after\n"
        assert (later.path / "assets/data.bin").read_bytes() == b"\x00\x01"

    assert historical_workspace.lineage.lineage_id == initial.lineage_id
    assert (historical_workspace.path / "src/app.py").read_bytes() == b"before\n"


def test_cleanup_is_idempotent_and_does_not_delete_lineage_state(tmp_path):
    allocator = ProjectWorkspaceAllocator(tmp_path / "protected")
    run_identity = identity()
    workspace = allocator.initialize(run_identity, RepositoryProvider({"app.py": b"stable\n"}))
    lineage_id = workspace.lineage.lineage_id

    allocator.cleanup(workspace)
    allocator.cleanup(workspace)

    assert allocator.current_lineage(run_identity).lineage_id == lineage_id
    restored = allocator.reconstruct(run_identity, lineage_id)
    assert (restored.path / "app.py").read_bytes() == b"stable\n"


def test_lineage_state_survives_allocator_recreation_for_resume(tmp_path):
    protected_root = tmp_path / "protected"
    run_identity = identity()
    first_allocator = ProjectWorkspaceAllocator(protected_root)
    workspace = first_allocator.initialize(run_identity, RepositoryProvider({"app.py": b"before\n"}))
    initial = workspace.lineage
    (workspace.path / "app.py").write_bytes(b"accepted\n")
    accepted = first_allocator.accept_implementation(
        workspace,
        expected_parent_lineage_id=initial.lineage_id,
    )
    first_allocator.cleanup(workspace)

    resumed_allocator = ProjectWorkspaceAllocator(protected_root)
    assert resumed_allocator.current_lineage(run_identity) == accepted
    resumed = resumed_allocator.resolve(run_identity)
    historical = resumed_allocator.reconstruct(run_identity, initial.lineage_id)

    assert resumed.lineage.lineage_id == accepted.lineage_id
    assert (resumed.path / "app.py").read_bytes() == b"accepted\n"
    assert (historical.path / "app.py").read_bytes() == b"before\n"


def test_workspace_lease_cannot_claim_lineage_from_another_project_run(tmp_path):
    allocator = ProjectWorkspaceAllocator(tmp_path / "protected")
    first_identity = identity()
    second_identity = identity()
    first = allocator.initialize(first_identity, RepositoryProvider({"app.py": b"one\n"}))
    second = allocator.initialize(second_identity, RepositoryProvider({"app.py": b"two\n"}))
    forged = MaterializedWorkspace(
        identity=first_identity,
        lineage=second.lineage,
        lease_id=first.lease_id,
        path=first.path,
    )

    with pytest.raises(StaleLineageError):
        allocator.accept_implementation(
            forged,
            expected_parent_lineage_id=second.lineage.lineage_id,
        )
