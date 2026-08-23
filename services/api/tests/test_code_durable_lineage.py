from __future__ import annotations

from hashlib import sha256
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from parallax_api.code.lineage_persistence import (
    InMemoryImmutableObjectStore,
    InMemoryLineageMetadataStore,
    MetadataCASConflict,
    ObjectWriteError,
    PostgresLineageMetadataStore,
    VercelPrivateBlobObjectStore,
    create_lineage_metadata_schema,
)
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import (
    LineageIntegrityError,
    ProjectRunIdentity,
    SourceLineageStore,
    SourcePackage,
    StaleLineageError,
)
from parallax_api.intelligence.protected_metrics import evaluate_compiled_plan, evaluate_spec_contract


class StaticProvider:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        return SourcePackage("repository", "github:owner/repo@durable", self.files)


class FailingObjectStore(InMemoryImmutableObjectStore):
    def __init__(self, *, fail_after: int) -> None:
        super().__init__()
        self.fail_after = fail_after
        self.writes = 0

    def put_if_absent(self, digest: str, content: bytes) -> None:
        if digest not in self.objects:
            self.writes += 1
            if self.writes > self.fail_after:
                raise ObjectWriteError("injected durable object failure")
        super().put_if_absent(digest, content)


def identity() -> ProjectRunIdentity:
    return ProjectRunIdentity(str(uuid4()), str(uuid4()))


def make_store(objects=None, metadata=None) -> SourceLineageStore:
    return SourceLineageStore(
        objects or InMemoryImmutableObjectStore(),
        metadata or InMemoryLineageMetadataStore(),
    )


def test_p2_v0155_spec_and_compiled_plan_require_protected_dspy_metadata():
    repository_root = Path(__file__).resolve().parents[3]
    spec_path = repository_root / "specs" / "P2-V0.15.5.md"
    plan_path = repository_root / "specs" / "compiled" / "P2-V0.15.5.plan.json"
    spec_text = spec_path.read_text(encoding="utf-8")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    assert evaluate_spec_contract(spec_text).passed is True
    assert evaluate_compiled_plan(spec_text, plan, require_metadata=True).passed is True
    assert plan["dspy_run"]["executed"] is True


def test_source_lineage_store_has_no_filesystem_durability_parameter():
    parameters = inspect.signature(SourceLineageStore).parameters
    assert tuple(parameters)[:2] == ("object_store", "metadata_store")
    assert "state_root" not in parameters
    assert "workspace_ref" not in parameters


def test_allocator_requires_explicit_lineage_store_and_has_no_local_durable_fallback(tmp_path):
    with pytest.raises(TypeError):
        ProjectWorkspaceAllocator(tmp_path / "instance")  # type: ignore[call-arg]


def test_partial_object_write_never_advances_durable_metadata():
    objects = FailingObjectStore(fail_after=1)
    metadata = InMemoryLineageMetadataStore()
    store = SourceLineageStore(objects, metadata)
    run_identity = identity()

    with pytest.raises(LineageIntegrityError):
        store.initialize(
            run_identity,
            StaticProvider({"a.py": b"first\n", "b.py": b"second\n"}),
        )

    assert metadata.get_current(run_identity.project_id, run_identity.run_id) is None
    assert metadata.manifests == {}
    assert len(objects.objects) == 1


def test_missing_or_corrupt_durable_object_fails_resolution_and_reconstruction(tmp_path):
    objects = InMemoryImmutableObjectStore()
    metadata = InMemoryLineageMetadataStore()
    store = SourceLineageStore(objects, metadata)
    run_identity = identity()
    accepted = store.initialize(run_identity, StaticProvider({"app.py": b"accepted\n"}))
    digest = accepted.files[0].sha256

    del objects.objects[digest]
    with pytest.raises(LineageIntegrityError):
        store.resolve(run_identity, accepted.lineage_id)

    objects.objects[digest] = b"corrupt\n"
    with pytest.raises(LineageIntegrityError):
        store.materialize(run_identity, accepted.lineage_id, tmp_path / "reconstructed")


def test_retry_after_store_recreation_is_exactly_idempotent(tmp_path):
    objects = InMemoryImmutableObjectStore()
    metadata = InMemoryLineageMetadataStore()
    run_identity = identity()

    first = SourceLineageStore(objects, metadata)
    initial = first.initialize(run_identity, StaticProvider({"app.py": b"before\n"}))
    workspace = tmp_path / "mutation"
    first.materialize(run_identity, initial.lineage_id, workspace)
    (workspace / "app.py").write_bytes(b"after\n")
    accepted = first.capture_implementation(
        run_identity,
        workspace,
        expected_parent_lineage_id=initial.lineage_id,
    )

    recreated = SourceLineageStore(objects, metadata)
    retry = recreated.capture_implementation(
        run_identity,
        workspace,
        expected_parent_lineage_id=initial.lineage_id,
    )

    assert retry == accepted
    assert recreated.current(run_identity) == accepted


def test_two_store_instances_cannot_advance_same_parent_to_different_children(tmp_path):
    objects = InMemoryImmutableObjectStore()
    metadata = InMemoryLineageMetadataStore()
    run_identity = identity()
    first = SourceLineageStore(objects, metadata)
    second = SourceLineageStore(objects, metadata)
    initial = first.initialize(run_identity, StaticProvider({"app.py": b"base\n"}))

    first_workspace = tmp_path / "first"
    second_workspace = tmp_path / "second"
    first.materialize(run_identity, initial.lineage_id, first_workspace)
    second.materialize(run_identity, initial.lineage_id, second_workspace)
    (first_workspace / "app.py").write_bytes(b"winner\n")
    (second_workspace / "app.py").write_bytes(b"loser\n")

    accepted = first.capture_implementation(
        run_identity,
        first_workspace,
        expected_parent_lineage_id=initial.lineage_id,
    )
    with pytest.raises(StaleLineageError):
        second.capture_implementation(
            run_identity,
            second_workspace,
            expected_parent_lineage_id=initial.lineage_id,
        )

    assert second.current(run_identity) == accepted


def test_sqlalchemy_metadata_adapter_uses_persistent_cas_across_adapter_instances(tmp_path):
    database = tmp_path / "lineage.sqlite"
    engine = create_engine(
        f"sqlite+pysqlite:///{database}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    create_lineage_metadata_schema(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    first = PostgresLineageMetadataStore(sessions)
    second = PostgresLineageMetadataStore(sessions)
    project_id = str(uuid4())
    run_id = str(uuid4())

    initial = "src:" + "1" * 64
    first_child = "src:" + "2" * 64
    losing_child = "src:" + "3" * 64
    initial_manifest = b'{"lineage_id":"initial"}\n'
    first_manifest = b'{"lineage_id":"first"}\n'
    losing_manifest = b'{"lineage_id":"loser"}\n'

    first.commit_manifest_and_advance(
        project_id=project_id,
        run_id=run_id,
        lineage_id=initial,
        manifest=initial_manifest,
        expected_current_lineage_id=None,
    )
    first.commit_manifest_and_advance(
        project_id=project_id,
        run_id=run_id,
        lineage_id=first_child,
        manifest=first_manifest,
        expected_current_lineage_id=initial,
    )

    with pytest.raises(MetadataCASConflict) as conflict:
        second.commit_manifest_and_advance(
            project_id=project_id,
            run_id=run_id,
            lineage_id=losing_child,
            manifest=losing_manifest,
            expected_current_lineage_id=initial,
        )

    assert conflict.value.current_lineage_id == first_child
    assert second.get_current(project_id, run_id) == first_child
    assert second.get_manifest(first_child) == first_manifest
    assert second.get_manifest(losing_child) is None


def test_cleanup_destroys_only_local_lease_and_new_instance_reconstructs(tmp_path):
    objects = InMemoryImmutableObjectStore()
    metadata = InMemoryLineageMetadataStore()
    run_identity = identity()
    first_store = SourceLineageStore(objects, metadata)
    first_allocator = ProjectWorkspaceAllocator(tmp_path / "instance-a", lineage_store=first_store)
    workspace = first_allocator.initialize(run_identity, StaticProvider({"app.py": b"durable\n"}))
    accepted = workspace.lineage

    first_allocator.cleanup(workspace)
    assert not workspace.path.exists()

    second_store = SourceLineageStore(objects, metadata)
    second_allocator = ProjectWorkspaceAllocator(tmp_path / "instance-b", lineage_store=second_store)
    reconstructed = second_allocator.reconstruct(run_identity, accepted.lineage_id)
    assert reconstructed.path.is_relative_to(tmp_path / "instance-b")
    assert (reconstructed.path / "app.py").read_bytes() == b"durable\n"


def test_vercel_blob_adapter_uses_private_deterministic_paths_and_verifies_content(monkeypatch):
    import vercel.blob

    remote: dict[str, bytes] = {}
    calls: list[tuple[str, str, dict[str, object]]] = []

    def fake_get(path: str, **kwargs):
        calls.append(("get", path, dict(kwargs)))
        if path not in remote:
            raise vercel.blob.BlobNotFoundError()
        return SimpleNamespace(content=remote[path])

    def fake_put(path: str, body: bytes, **kwargs):
        calls.append(("put", path, dict(kwargs)))
        if path in remote and kwargs.get("overwrite") is False:
            raise vercel.blob.BlobError("already exists")
        remote[path] = bytes(body)
        return SimpleNamespace(url="private")

    monkeypatch.setattr(vercel.blob, "get", fake_get)
    monkeypatch.setattr(vercel.blob, "put", fake_put)

    content = b"private accepted source\n"
    digest = sha256(content).hexdigest()
    store = VercelPrivateBlobObjectStore(token="test-token")
    store.put_if_absent(digest, content)
    store.put_if_absent(digest, content)

    assert store.get(digest) == content
    expected_path = f"parallax/source-lineage/v1/sha256/{digest[:2]}/{digest}"
    assert set(remote) == {expected_path}
    put_call = next(call for call in calls if call[0] == "put")
    assert put_call[1] == expected_path
    assert put_call[2]["access"] == "private"
    assert put_call[2]["add_random_suffix"] is False
    assert put_call[2]["overwrite"] is False
    assert all(call[2].get("access") == "private" for call in calls if call[0] == "get")
    assert all(call[2].get("use_cache") is False for call in calls if call[0] == "get")


def test_migration_persists_only_bounded_metadata_not_source_bytes():
    repository_root = Path(__file__).resolve().parents[3]
    migration = (repository_root / "services/api/migrations/20260823_0008_durable_source_lineage.sql").read_text(
        encoding="utf-8"
    )
    lowered = migration.lower()

    assert "source_lineage_manifests" in lowered
    assert "source_lineage_heads" in lowered
    assert "manifest_sha256" in lowered
    assert "revision bigint" in lowered
    assert "bytea" not in lowered
    assert "source_content" not in lowered
    assert "workspace_ref" not in lowered
