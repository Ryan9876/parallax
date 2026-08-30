from __future__ import annotations

import json
from uuid import uuid4

import pytest

from parallax_api.code.greenfield_lineage import (
    EMPTY_CONTENT_DIGEST,
    GREENFIELD_SOURCE_KIND,
    GreenfieldSourceLineageStore,
    greenfield_source_ref,
)
from parallax_api.code.lineage_persistence import InMemoryImmutableObjectStore, InMemoryLineageMetadataStore
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import (
    LineageIntegrityError,
    ProjectRunIdentity,
    SourcePackage,
    SourcePolicyError,
)


class PackageProvider:
    def __init__(self, package: SourcePackage) -> None:
        self.package = package

    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        return self.package


def _identity() -> ProjectRunIdentity:
    return ProjectRunIdentity(str(uuid4()), str(uuid4()))


def _store():
    objects = InMemoryImmutableObjectStore()
    metadata = InMemoryLineageMetadataStore()
    return GreenfieldSourceLineageStore(objects, metadata), objects, metadata


def test_greenfield_root_is_explicit_zero_file_lineage_and_idempotent() -> None:
    store, objects, _ = _store()
    identity = _identity()
    source_ref = greenfield_source_ref("github:owner/empty", "main")

    first = store.initialize_greenfield(identity, source_ref=source_ref)
    replay = store.initialize_greenfield(identity, source_ref=source_ref)

    assert replay == first
    assert first.source_kind == GREENFIELD_SOURCE_KIND
    assert first.parent_lineage_id is None
    assert first.content_digest == EMPTY_CONTENT_DIGEST
    assert first.file_count == 0
    assert first.total_bytes == 0
    assert first.files == ()
    assert first.source_ref_digest is not None
    assert objects.objects == {}
    assert source_ref not in json.dumps(first.evidence())


def test_greenfield_root_materializes_empty_but_implementation_must_be_nonempty(tmp_path) -> None:
    store, _, _ = _store()
    allocator = ProjectWorkspaceAllocator(tmp_path / "protected", lineage_store=store)
    identity = _identity()
    workspace = allocator.initialize_greenfield(
        identity,
        source_ref=greenfield_source_ref("github:owner/empty", "main"),
    )

    assert workspace.path.is_dir()
    assert tuple(workspace.path.iterdir()) == ()

    with pytest.raises(SourcePolicyError, match="at least one file"):
        allocator.accept_implementation(
            workspace,
            expected_parent_lineage_id=workspace.lineage.lineage_id,
        )

    (workspace.path / "app.py").write_text("print('created')\n", encoding="utf-8")
    accepted = allocator.accept_implementation(
        workspace,
        expected_parent_lineage_id=workspace.lineage.lineage_id,
    )
    assert accepted.source_kind == "implementation"
    assert accepted.parent_lineage_id == workspace.lineage.lineage_id
    assert accepted.file_count == 1
    assert accepted.content_digest != EMPTY_CONTENT_DIGEST


def test_ordinary_source_package_cannot_claim_greenfield_or_be_empty() -> None:
    store, _, _ = _store()
    identity = _identity()

    with pytest.raises(SourcePolicyError, match="source kind"):
        store.initialize(
            identity,
            PackageProvider(
                SourcePackage(
                    source_kind=GREENFIELD_SOURCE_KIND,
                    source_ref="github:owner/empty@greenfield-empty:main:v1",
                    files={"app.py": b"not-greenfield\n"},
                )
            ),
        )

    with pytest.raises(SourcePolicyError, match="at least one file"):
        store.initialize(
            identity,
            PackageProvider(
                SourcePackage(
                    source_kind="repository",
                    source_ref="github:owner/repo@abc123",
                    files={},
                )
            ),
        )


def test_changed_greenfield_provenance_cannot_replace_existing_root() -> None:
    store, _, _ = _store()
    identity = _identity()
    store.initialize_greenfield(identity, source_ref=greenfield_source_ref("github:owner/empty", "main"))

    with pytest.raises(Exception, match="already initialized"):
        store.initialize_greenfield(identity, source_ref=greenfield_source_ref("github:owner/empty", "trunk"))


def test_forged_empty_manifest_is_rejected_unless_all_greenfield_root_invariants_match() -> None:
    store, _, metadata = _store()
    identity = _identity()
    lineage = store.initialize_greenfield(
        identity,
        source_ref=greenfield_source_ref("github:owner/empty", "main"),
    )
    original = metadata.manifests[lineage.lineage_id]

    payload = json.loads(original.decode("utf-8"))
    payload["source_kind"] = "implementation"
    metadata.manifests[lineage.lineage_id] = (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    with pytest.raises((LineageIntegrityError, SourcePolicyError)):
        store.resolve(identity, lineage.lineage_id)

    metadata.manifests[lineage.lineage_id] = original
    payload = json.loads(original.decode("utf-8"))
    payload["file_count"] = 1
    metadata.manifests[lineage.lineage_id] = (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    with pytest.raises(LineageIntegrityError, match="zero source files"):
        store.resolve(identity, lineage.lineage_id)


def test_greenfield_source_ref_is_bounded_and_deterministic() -> None:
    assert greenfield_source_ref("github:Owner/Repo", "main") == "github:Owner/Repo@greenfield-empty:main:v1"
    with pytest.raises(SourcePolicyError):
        greenfield_source_ref("https://github.com/owner/repo", "main")
    with pytest.raises(SourcePolicyError):
        greenfield_source_ref("github:owner/repo", "main\nmalicious")
