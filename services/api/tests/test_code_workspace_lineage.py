from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from parallax_api.code.workspace_lineage import (
    LineageIdentityError,
    LineageIntegrityError,
    NoSourceChangeError,
    ProjectRunIdentity,
    SourceLineageStore,
    SourcePackage,
    SourcePolicyError,
    StaleLineageError,
)


class StaticProvider:
    def __init__(self, files: dict[str, bytes], *, source_kind: str = "repository", source_ref: str = "github:owner/repo@abc123"):
        self.files = files
        self.source_kind = source_kind
        self.source_ref = source_ref
        self.identities: list[ProjectRunIdentity] = []

    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        self.identities.append(identity)
        return SourcePackage(self.source_kind, self.source_ref, self.files)


def identity() -> ProjectRunIdentity:
    return ProjectRunIdentity(str(uuid4()), str(uuid4()))


def test_project_run_identity_is_canonical_and_never_workspace_ref_or_path():
    project_id = str(uuid4())
    run_id = str(uuid4())
    accepted = ProjectRunIdentity(project_id, run_id)

    assert accepted.project_id == project_id
    assert accepted.run_id == run_id
    assert project_id not in accepted.storage_key
    assert run_id not in accepted.storage_key
    assert len(accepted.storage_key) == 64

    with pytest.raises(LineageIdentityError):
        ProjectRunIdentity(f"project:{project_id}", run_id)
    with pytest.raises(LineageIdentityError):
        ProjectRunIdentity("../project", run_id)
    with pytest.raises(LineageIdentityError):
        ProjectRunIdentity(project_id.upper(), run_id)


def test_trusted_source_initialization_is_bounded_idempotent_and_hides_raw_provenance(tmp_path):
    store = SourceLineageStore(tmp_path / "state")
    run_identity = identity()
    provider = StaticProvider({"src/app.py": b"print('hello')\n", "assets/logo.bin": b"\x00\x01"})

    first = store.initialize(run_identity, provider)
    again = store.initialize(run_identity, provider)

    assert again == first
    assert provider.identities == [run_identity, run_identity]
    assert first.parent_lineage_id is None
    assert first.source_kind == "repository"
    assert first.file_count == 2
    assert first.total_bytes == len(b"print('hello')\n") + 2
    assert first.source_ref_digest is not None
    assert provider.source_ref not in json.dumps(first.evidence())
    assert set(first.evidence()) == {
        "project_id",
        "run_id",
        "lineage_id",
        "parent_lineage_id",
        "content_digest",
        "source_kind",
        "source_ref_digest",
        "file_count",
        "total_bytes",
    }

    changed = StaticProvider({"src/app.py": b"print('different')\n"})
    with pytest.raises(StaleLineageError):
        store.initialize(run_identity, changed)
    assert store.current(run_identity) == first


def test_source_provider_output_rejects_paths_secrets_urls_and_resource_overflow(tmp_path):
    run_identity = identity()
    store = SourceLineageStore(tmp_path / "state", max_files=2, max_file_bytes=8, max_total_bytes=12)

    for files in (
        {"../escape.py": b"x"},
        {"/absolute.py": b"x"},
        {"src\\windows.py": b"x"},
        {".git/config": b"x"},
        {".env": b"TOKEN=value"},
        {"keys/private.pem": b"x"},
    ):
        with pytest.raises(SourcePolicyError):
            store.initialize(run_identity, StaticProvider(files))

    with pytest.raises(SourcePolicyError):
        store.initialize(run_identity, StaticProvider({"a.py": b"123456789"}))
    with pytest.raises(SourcePolicyError):
        store.initialize(run_identity, StaticProvider({"a.py": b"1", "b.py": b"2", "c.py": b"3"}))
    with pytest.raises(SourcePolicyError):
        store.initialize(run_identity, StaticProvider({"a.py": b"12345678", "b.py": b"12345678"}))
    with pytest.raises(SourcePolicyError):
        store.initialize(
            run_identity,
            StaticProvider({"a.py": b"1"}, source_ref="https://github.com/owner/repo"),
        )


def test_implementation_lineage_advances_once_retry_is_idempotent_and_stale_tree_is_denied(tmp_path):
    store = SourceLineageStore(tmp_path / "state")
    run_identity = identity()
    initial = store.initialize(run_identity, StaticProvider({"src/app.py": b"value = 1\n"}))
    workspace = tmp_path / "workspace"
    store.materialize(run_identity, initial.lineage_id, workspace)

    (workspace / "src/app.py").write_bytes(b"value = 2\n")
    accepted = store.capture_implementation(
        run_identity,
        workspace,
        expected_parent_lineage_id=initial.lineage_id,
    )
    retry = store.capture_implementation(
        run_identity,
        workspace,
        expected_parent_lineage_id=initial.lineage_id,
    )

    assert retry == accepted
    assert accepted.parent_lineage_id == initial.lineage_id
    assert accepted.content_digest != initial.content_digest
    assert store.current(run_identity) == accepted

    (workspace / "src/app.py").write_bytes(b"value = 3\n")
    with pytest.raises(StaleLineageError):
        store.capture_implementation(
            run_identity,
            workspace,
            expected_parent_lineage_id=initial.lineage_id,
        )
    assert store.current(run_identity) == accepted


def test_no_change_cannot_manufacture_new_lineage(tmp_path):
    store = SourceLineageStore(tmp_path / "state")
    run_identity = identity()
    initial = store.initialize(run_identity, StaticProvider({"app.py": b"x = 1\n"}))
    workspace = tmp_path / "workspace"
    store.materialize(run_identity, initial.lineage_id, workspace)

    with pytest.raises(NoSourceChangeError):
        store.capture_implementation(
            run_identity,
            workspace,
            expected_parent_lineage_id=initial.lineage_id,
        )
    assert store.current(run_identity) == initial


def test_historical_lineage_reconstructs_exact_content_after_later_mutation(tmp_path):
    store = SourceLineageStore(tmp_path / "state")
    run_identity = identity()
    initial = store.initialize(
        run_identity,
        StaticProvider({"src/app.py": b"one\n", "assets/data.bin": b"\x00\xff\x10"}),
    )
    implementation_workspace = tmp_path / "implementation"
    store.materialize(run_identity, initial.lineage_id, implementation_workspace)
    (implementation_workspace / "src/app.py").write_bytes(b"two\n")
    accepted = store.capture_implementation(
        run_identity,
        implementation_workspace,
        expected_parent_lineage_id=initial.lineage_id,
    )

    old_workspace = tmp_path / "old"
    new_workspace = tmp_path / "new"
    store.materialize(run_identity, initial.lineage_id, old_workspace)
    store.materialize(run_identity, accepted.lineage_id, new_workspace)

    assert (old_workspace / "src/app.py").read_bytes() == b"one\n"
    assert (new_workspace / "src/app.py").read_bytes() == b"two\n"
    assert (old_workspace / "assets/data.bin").read_bytes() == b"\x00\xff\x10"
    assert (new_workspace / "assets/data.bin").read_bytes() == b"\x00\xff\x10"
    assert store.resolve(run_identity, initial.lineage_id) == initial
    assert store.resolve(run_identity, accepted.lineage_id) == accepted


def test_different_source_tree_or_identity_cannot_be_mislabeled_as_accepted_lineage(tmp_path):
    store = SourceLineageStore(tmp_path / "state")
    run_identity = identity()
    accepted = store.initialize(run_identity, StaticProvider({"app.py": b"accepted\n"}))
    other_identity = identity()

    with pytest.raises(LineageIntegrityError):
        store.resolve(other_identity, accepted.lineage_id)

    manifest = store.lineages_root / f"{accepted.lineage_id.removeprefix('src:')}.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["content_digest"] = "0" * 64
    manifest.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    with pytest.raises(LineageIntegrityError):
        store.resolve(run_identity, accepted.lineage_id)


def test_blob_tampering_is_detected_before_reconstruction(tmp_path):
    store = SourceLineageStore(tmp_path / "state")
    run_identity = identity()
    accepted = store.initialize(run_identity, StaticProvider({"app.py": b"safe\n"}))
    blob_digest = accepted.files[0].sha256
    blob = store.blobs_root / blob_digest[:2] / blob_digest
    blob.write_bytes(b"tampered\n")

    with pytest.raises(LineageIntegrityError):
        store.resolve(run_identity, accepted.lineage_id)
    with pytest.raises(LineageIntegrityError):
        store.materialize(run_identity, accepted.lineage_id, tmp_path / "reconstructed")


def test_workspace_capture_rejects_symlinks_and_secret_sensitive_files(tmp_path):
    store = SourceLineageStore(tmp_path / "state")
    run_identity = identity()
    initial = store.initialize(run_identity, StaticProvider({"app.py": b"x = 1\n"}))
    workspace = tmp_path / "workspace"
    store.materialize(run_identity, initial.lineage_id, workspace)
    (workspace / "link.py").symlink_to(workspace / "app.py")

    with pytest.raises(SourcePolicyError):
        store.capture_implementation(run_identity, workspace, expected_parent_lineage_id=initial.lineage_id)

    (workspace / "link.py").unlink()
    (workspace / ".env").write_text("TOKEN=value", encoding="utf-8")
    with pytest.raises(SourcePolicyError):
        store.capture_implementation(run_identity, workspace, expected_parent_lineage_id=initial.lineage_id)
