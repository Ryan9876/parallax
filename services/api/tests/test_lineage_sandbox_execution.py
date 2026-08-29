from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import SimpleNamespace

from parallax_api.code.domain import WorkflowStage
from parallax_api.code.execution import ExecutionSpec
from parallax_api.code.lineage_sandbox_execution import SameLineageVercelSandboxExecutor
from parallax_api.code.sandbox_execution import ProtectedCommandRegistry
from parallax_api.code.workspace_allocator import MaterializedWorkspace
from parallax_api.code.workspace_lineage import LineageFile, ProjectRunIdentity, SourceLineage


PROJECT_ID = "11111111-1111-1111-1111-111111111111"
RUN_ID = "22222222-2222-2222-2222-222222222222"
LINEAGE_ID = "src:" + "a" * 64
SNAPSHOT_ID = "snap_test-offline-runtime"


class FakeAllocator:
    def __init__(self, workspace: MaterializedWorkspace, *, cleanup_error: bool = False):
        self.workspace = workspace
        self.cleanup_error = cleanup_error
        self.reconstruct_calls = []
        self.cleanup_calls = []

    def reconstruct(self, identity, lineage_id):
        self.reconstruct_calls.append((identity, lineage_id))
        return self.workspace

    def cleanup(self, workspace):
        self.cleanup_calls.append(workspace)
        if self.cleanup_error:
            raise RuntimeError("cleanup failed")


class FakeFilesystemBatch:
    def __init__(self, filesystem, *, cwd):
        self.filesystem = filesystem
        self.cwd = cwd
        self.staged = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            return False
        if self.filesystem.fail_write:
            raise RuntimeError("transfer failed")
        self.filesystem.batch_flushes.append(tuple(self.staged))
        return False

    def write_bytes(self, path, data, *, mode=None):
        self.staged.append((path, data, mode))


class FakeFilesystem:
    def __init__(self, *, fail_write: bool = False):
        self.fail_write = fail_write
        self.mkdirs = []
        self.batch_cwds = []
        self.batch_flushes = []
        self.direct_writes = []

    def mkdir(self, path, *, cwd=None, recursive=True):
        self.mkdirs.append((path, cwd, recursive))

    def batch(self, *, cwd=None):
        self.batch_cwds.append(cwd)
        return FakeFilesystemBatch(self, cwd=cwd)

    def write_bytes(self, path, data, *, cwd=None):
        self.direct_writes.append((path, data, cwd))
        raise AssertionError("same-lineage transfer must use the public batch API")


class FakeSandboxInstance:
    def __init__(self, filesystem: FakeFilesystem, *, current_snapshot_id: str = SNAPSHOT_ID):
        self.fs = filesystem
        self.current_snapshot_id = current_snapshot_id
        self.process_calls = []

    def run_process(self, command, args, **kwargs):
        self.process_calls.append((command, args, kwargs))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")


class Context:
    def __init__(self, value=None):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeNetworkPolicy:
    @staticmethod
    def deny_all():
        return "DENY_ALL"


@dataclass(frozen=True)
class FakeSnapshotSource:
    snapshot_id: str


class FakeSandboxModule:
    def __init__(self, instance: FakeSandboxInstance):
        self.instance = instance
        self.create_calls = []

    def create_sandbox(self, **kwargs):
        self.create_calls.append(kwargs)
        return Context(self.instance)


def workspace_fixture(tmp_path, *, files=None):
    root = tmp_path / "lease"
    root.mkdir(parents=True)
    files = files or {
        "README.md": b"hello\n",
        "src/app.py": b"value = 2\n",
    }
    entries = []
    for path, content in sorted(files.items()):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        entries.append(LineageFile(path=path, sha256=sha256(content).hexdigest(), size=len(content)))
    identity = ProjectRunIdentity(project_id=PROJECT_ID, run_id=RUN_ID)
    lineage = SourceLineage(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        lineage_id=LINEAGE_ID,
        parent_lineage_id="src:" + "b" * 64,
        content_digest="c" * 64,
        source_kind="implementation",
        source_ref_digest=None,
        file_count=len(entries),
        total_bytes=sum(item.size for item in entries),
        files=tuple(entries),
    )
    return MaterializedWorkspace(identity=identity, lineage=lineage, lease_id="d" * 32, path=root), files


def executor_fixture(
    tmp_path,
    *,
    fail_write=False,
    cleanup_error=False,
    current_snapshot_id=SNAPSHOT_ID,
    files=None,
):
    workspace, files = workspace_fixture(tmp_path, files=files)
    allocator = FakeAllocator(workspace, cleanup_error=cleanup_error)
    filesystem = FakeFilesystem(fail_write=fail_write)
    instance = FakeSandboxInstance(filesystem, current_snapshot_id=current_snapshot_id)
    sandbox = FakeSandboxModule(instance)
    executor = SameLineageVercelSandboxExecutor(
        allocator,
        project_id="vercel-project",
        snapshot_id=SNAPSHOT_ID,
    )
    executor._sdk = lambda: (lambda: Context(), FakeNetworkPolicy, FakeSnapshotSource, sandbox)
    return executor, allocator, filesystem, instance, sandbox, files


def test_same_lineage_executor_transfers_exact_source_to_pinned_deny_all_snapshot(tmp_path):
    executor, allocator, filesystem, instance, sandbox, files = executor_fixture(tmp_path)
    spec = ProtectedCommandRegistry().spec_for(WorkflowStage.BUILD, operation_key="build:1")

    evidence = executor.execute_on_lineage(
        spec,
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        source_lineage_ref=LINEAGE_ID,
    )

    assert evidence["protected_success"] is True
    assert evidence["network_policy"] == "deny-all"
    assert evidence["persistent"] is False
    assert evidence["lineage_source_transfer"] is True
    assert evidence["fresh_repository_checkout"] is False
    assert evidence["git_source"] is False
    assert evidence["execution_snapshot_id"] == SNAPSHOT_ID
    assert evidence["execution_snapshot_verified"] is True
    assert evidence["execution_working_directory"] == "/vercel/sandbox"
    assert allocator.reconstruct_calls[0][0] == ProjectRunIdentity(PROJECT_ID, RUN_ID)
    assert allocator.reconstruct_calls[0][1] == LINEAGE_ID
    assert len(allocator.cleanup_calls) == 1

    create = sandbox.create_calls[0]
    assert create["source"] == FakeSnapshotSource(snapshot_id=SNAPSHOT_ID)
    assert create["network_policy"] == "DENY_ALL"
    assert create["persistent"] is False
    assert create["env"] == {}
    assert create["destroy"] is True
    assert filesystem.mkdirs == [("sandbox", "/vercel", True)]
    assert filesystem.batch_cwds == ["/vercel/sandbox"]
    assert len(filesystem.batch_flushes) == 1
    assert {path: data for path, data, mode in filesystem.batch_flushes[0]} == files
    assert all(mode is None for _, _, mode in filesystem.batch_flushes[0])
    assert filesystem.direct_writes == []

    command, args, kwargs = instance.process_calls[0]
    assert command == "python"
    assert tuple(args) == ("-m", "compileall", "-q", ".")
    assert evidence["validation_profile_id"] == "python-v1"
    assert isinstance(evidence["validation_profile_digest"], str)
    assert len(evidence["validation_profile_digest"]) == 64
    assert kwargs["env"] == {}
    assert kwargs["cwd"] == "/vercel/sandbox"


def test_large_lineage_uses_one_bounded_batch_upload(tmp_path):
    files = {
        f"src/package/file_{index:03d}.py": f"VALUE = {index}\n".encode("utf-8")
        for index in range(96)
    }
    executor, _, filesystem, instance, _, expected = executor_fixture(tmp_path, files=files)
    spec = ProtectedCommandRegistry().spec_for(WorkflowStage.BUILD, operation_key="build:large-lineage")

    evidence = executor.execute_on_lineage(
        spec,
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        source_lineage_ref=LINEAGE_ID,
    )

    assert evidence["protected_success"] is True
    assert evidence["source_file_count"] == 96
    assert filesystem.mkdirs == [("sandbox", "/vercel", True)]
    assert filesystem.batch_cwds == ["/vercel/sandbox"]
    assert len(filesystem.batch_flushes) == 1
    assert len(filesystem.batch_flushes[0]) == 96
    assert {path: data for path, data, _ in filesystem.batch_flushes[0]} == expected
    assert filesystem.direct_writes == []
    assert len(instance.process_calls) == 1


def test_same_lineage_executor_fails_closed_when_snapshot_identity_does_not_match(tmp_path):
    executor, allocator, filesystem, instance, sandbox, _ = executor_fixture(
        tmp_path,
        current_snapshot_id="snap_wrong-runtime",
    )
    spec = ProtectedCommandRegistry().spec_for(WorkflowStage.TEST, operation_key="test:snapshot")

    evidence = executor.execute_on_lineage(
        spec,
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        source_lineage_ref=LINEAGE_ID,
    )

    assert evidence["protected_success"] is False
    assert evidence["execution_snapshot_id"] == SNAPSHOT_ID
    assert evidence["execution_snapshot_verified"] is False
    assert evidence["lineage_source_transfer"] is False
    assert filesystem.mkdirs == []
    assert filesystem.batch_cwds == []
    assert filesystem.batch_flushes == []
    assert filesystem.direct_writes == []
    assert instance.process_calls == []
    assert sandbox.create_calls[0]["network_policy"] == "DENY_ALL"
    assert len(allocator.cleanup_calls) == 1


def test_same_lineage_executor_rejects_unregistered_spec_before_materialization(tmp_path):
    executor, allocator, _, instance, sandbox, _ = executor_fixture(tmp_path)
    registered = ProtectedCommandRegistry().spec_for(WorkflowStage.BUILD, operation_key="build:2")
    spoofed = ExecutionSpec(
        tool_id=registered.tool_id,
        args=("-c", "print('caller command')"),
        working_directory=registered.working_directory,
        timeout_seconds=registered.timeout_seconds,
        environment_names=(),
        stage=registered.stage,
        operation_key=registered.operation_key,
    )
    evidence = executor.execute_on_lineage(
        spoofed,
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        source_lineage_ref=LINEAGE_ID,
    )
    assert evidence["protected_success"] is False
    assert allocator.reconstruct_calls == []
    assert sandbox.create_calls == []
    assert instance.process_calls == []


def test_same_lineage_executor_fails_closed_on_corrupt_reconstructed_source(tmp_path):
    workspace, _ = workspace_fixture(tmp_path)
    workspace.path.joinpath("src/app.py").write_text("tampered\n", encoding="utf-8")
    allocator = FakeAllocator(workspace)
    executor = SameLineageVercelSandboxExecutor(
        allocator,
        project_id="vercel-project",
        snapshot_id=SNAPSHOT_ID,
    )
    executor._sdk = lambda: (_ for _ in ()).throw(AssertionError("sandbox must not be created"))
    spec = ProtectedCommandRegistry().spec_for(WorkflowStage.TEST, operation_key="test:1")

    evidence = executor.execute_on_lineage(
        spec,
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        source_lineage_ref=LINEAGE_ID,
    )
    assert evidence["protected_success"] is False
    assert evidence["lineage_source_transfer"] is False
    assert len(allocator.cleanup_calls) == 1


def test_source_transfer_failure_is_non_success_and_cleans_lease(tmp_path):
    executor, allocator, filesystem, instance, sandbox, _ = executor_fixture(tmp_path, fail_write=True)
    spec = ProtectedCommandRegistry().spec_for(WorkflowStage.VERIFY, operation_key="verify:1")
    evidence = executor.execute_on_lineage(
        spec,
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        source_lineage_ref=LINEAGE_ID,
    )
    assert evidence["protected_success"] is False
    assert evidence["lineage_source_transfer"] is False
    assert filesystem.batch_cwds == ["/vercel/sandbox"]
    assert filesystem.batch_flushes == []
    assert filesystem.direct_writes == []
    assert len(allocator.cleanup_calls) == 1
    assert instance.process_calls == []
    assert sandbox.create_calls[0]["network_policy"] == "DENY_ALL"


def test_cleanup_failure_cannot_leave_successful_execution_evidence(tmp_path):
    executor, allocator, _, instance, _, _ = executor_fixture(tmp_path, cleanup_error=True)
    spec = ProtectedCommandRegistry().spec_for(WorkflowStage.BUILD, operation_key="build:cleanup")
    evidence = executor.execute_on_lineage(
        spec,
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        source_lineage_ref=LINEAGE_ID,
    )
    assert instance.process_calls
    assert evidence["protected_success"] is False
    assert evidence["lineage_cleanup_failed"] is True
    assert len(allocator.cleanup_calls) == 1


def test_wrong_project_or_lineage_identity_cannot_be_substituted(tmp_path):
    executor, allocator, _, _, sandbox, _ = executor_fixture(tmp_path)
    spec = ProtectedCommandRegistry().spec_for(WorkflowStage.BUILD, operation_key="build:identity")
    evidence = executor.execute_on_lineage(
        spec,
        project_ref="project:" + PROJECT_ID,
        run_id=RUN_ID,
        source_lineage_ref=LINEAGE_ID,
    )
    assert evidence["protected_success"] is False
    assert allocator.reconstruct_calls == []
    assert sandbox.create_calls == []
