from __future__ import annotations

import difflib
from hashlib import sha256

import pytest

from parallax_api.code.patching import (
    EMPTY_SHA256,
    PatchConflictError,
    PatchFormatError,
    PatchLimitError,
    SourcePatch,
    StaleBaseError,
    TextPatchEngine,
    UnsafeTargetError,
)


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def unified(path: str, before: str, after: str, *, creating: bool = False) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="/dev/null" if creating else f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def test_existing_text_patch_is_bounded_and_emits_deterministic_evidence(tmp_path):
    target = tmp_path / "src" / "app.py"
    target.parent.mkdir()
    before = "value = 1\nprint(value)\n"
    after = "value = 2\nprint(value)\n"
    target.write_text(before, encoding="utf-8")
    patch_text = unified("src/app.py", before, after)
    engine = TextPatchEngine()

    prepared = engine.prepare(
        tmp_path,
        SourcePatch("src/app.py", digest(before.encode()), patch_text),
    )
    evidence_before_commit = prepared.evidence
    assert target.read_text(encoding="utf-8") == before
    assert evidence_before_commit["before_sha256"] == digest(before.encode())
    assert evidence_before_commit["after_sha256"] == digest(after.encode())
    assert evidence_before_commit["unified_diff"] == patch_text
    assert evidence_before_commit["additions"] == 1
    assert evidence_before_commit["deletions"] == 1

    engine.commit(tmp_path, prepared)
    assert target.read_text(encoding="utf-8") == after
    assert prepared.evidence == evidence_before_commit


def test_new_text_file_can_create_bounded_missing_safe_parent_at_commit(tmp_path):
    # Preparation remains mutation-free; a missing safe parent is created only at commit.
    (tmp_path / "src").mkdir()
    after = "def ready():\n    return True\n"
    patch_text = unified("src/ready.py", "", after, creating=True)
    engine = TextPatchEngine()

    prepared = engine.prepare(
        tmp_path,
        SourcePatch("src/ready.py", EMPTY_SHA256, patch_text),
    )
    assert prepared.existed is False
    assert not (tmp_path / "src" / "ready.py").exists()
    engine.commit(tmp_path, prepared)
    assert (tmp_path / "src" / "ready.py").read_text(encoding="utf-8") == after

    missing_parent_patch = unified("missing/new.py", "", "x = 1\n", creating=True)
    missing = engine.prepare(tmp_path, SourcePatch("missing/new.py", EMPTY_SHA256, missing_parent_patch))
    assert missing.existed is False
    assert not (tmp_path / "missing").exists()
    engine.commit(tmp_path, missing)
    assert (tmp_path / "missing" / "new.py").read_text(encoding="utf-8") == "x = 1\n"


@pytest.mark.parametrize(
    "path",
    [
        "../outside.py",
        "/tmp/outside.py",
        "src/../outside.py",
        "src\\outside.py",
        ".git/config",
        ".env",
        "config/.env.production",
        "credentials.json",
        "private.pem",
        "asset.png",
    ],
)
def test_unsafe_traversal_repository_secret_and_binary_prone_targets_fail_closed(tmp_path, path):
    (tmp_path / "src").mkdir()
    (tmp_path / "config").mkdir()
    engine = TextPatchEngine()
    with pytest.raises(UnsafeTargetError):
        engine.prepare(tmp_path, SourcePatch(path, EMPTY_SHA256, "--- /dev/null\n+++ b/x.py\n@@ -0,0 +1 @@\n+x = 1\n"))


def test_symlink_path_component_and_symlink_target_are_denied(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    try:
        (workspace / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")

    patch_text = unified("link/escape.py", "", "x = 1\n", creating=True)
    with pytest.raises(UnsafeTargetError):
        TextPatchEngine().prepare(
            workspace,
            SourcePatch("link/escape.py", EMPTY_SHA256, patch_text),
        )
    assert not (outside / "escape.py").exists()

    real = workspace / "real.py"
    real.write_text("x = 1\n", encoding="utf-8")
    alias = workspace / "alias.py"
    alias.symlink_to(real)
    patch_text = unified("alias.py", "x = 1\n", "x = 2\n")
    with pytest.raises(UnsafeTargetError):
        TextPatchEngine().prepare(
            workspace,
            SourcePatch("alias.py", digest(b"x = 1\n"), patch_text),
        )


def test_stale_base_rejected_before_any_mutation(tmp_path):
    target = tmp_path / "app.py"
    before = "x = 1\n"
    target.write_text(before, encoding="utf-8")
    patch_text = unified("app.py", before, "x = 2\n")

    with pytest.raises(StaleBaseError):
        TextPatchEngine().prepare(tmp_path, SourcePatch("app.py", "0" * 64, patch_text))
    assert target.read_text(encoding="utf-8") == before


def test_malformed_header_mismatch_and_multi_file_diff_are_rejected(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")
    engine = TextPatchEngine()

    malformed = "--- a/app.py\n+++ b/app.py\nnot-a-hunk\n"
    with pytest.raises(PatchFormatError):
        engine.prepare(tmp_path, SourcePatch("app.py", digest(b"x = 1\n"), malformed))

    mismatch = "--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
    with pytest.raises(PatchFormatError):
        engine.prepare(tmp_path, SourcePatch("app.py", digest(b"x = 1\n"), mismatch))

    multi = (
        "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
        "--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-y = 1\n+y = 2\n"
    )
    with pytest.raises(PatchFormatError):
        engine.prepare(tmp_path, SourcePatch("app.py", digest(b"x = 1\n"), multi))
    assert target.read_text(encoding="utf-8") == "x = 1\n"


def test_hunk_context_mismatch_is_rejected_without_mutation(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("x = 1\ny = 2\n", encoding="utf-8")
    bad = "--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n-x = 999\n+x = 3\n y = 2\n"

    with pytest.raises(PatchConflictError):
        TextPatchEngine().prepare(
            tmp_path,
            SourcePatch("app.py", digest(target.read_bytes()), bad),
        )
    assert target.read_text(encoding="utf-8") == "x = 1\ny = 2\n"


def test_patch_source_and_result_size_limits_fail_closed(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")
    patch_text = unified("app.py", "x = 1\n", "x = 2\n")

    with pytest.raises(PatchLimitError):
        TextPatchEngine(max_patch_bytes=10).prepare(
            tmp_path,
            SourcePatch("app.py", digest(target.read_bytes()), patch_text),
        )

    target.write_text("a" * 50, encoding="utf-8")
    large_patch = unified("app.py", "a" * 50, "b\n")
    with pytest.raises(PatchLimitError):
        TextPatchEngine(max_file_bytes=20).prepare(
            tmp_path,
            SourcePatch("app.py", digest(target.read_bytes()), large_patch),
        )

    target.write_text("x\n", encoding="utf-8")
    result_patch = unified("app.py", "x\n", "y" * 40 + "\n")
    with pytest.raises(PatchLimitError):
        TextPatchEngine(max_result_bytes=20).prepare(
            tmp_path,
            SourcePatch("app.py", digest(target.read_bytes()), result_patch),
        )


def test_binary_source_and_secret_bearing_patch_content_fail_closed(tmp_path):
    binary = tmp_path / "blob.txt"
    binary.write_bytes(b"prefix\x00suffix")
    with pytest.raises(UnsafeTargetError):
        TextPatchEngine().prepare(
            tmp_path,
            SourcePatch("blob.txt", digest(binary.read_bytes()), "--- a/blob.txt\n+++ b/blob.txt\n@@ -1 +1 @@\n-x\n+y\n"),
        )

    target = tmp_path / "config.py"
    target.write_text("value = 'safe'\n", encoding="utf-8")
    secret_after = "api_key = ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\n"
    patch_text = unified("config.py", "value = 'safe'\n", secret_after)
    with pytest.raises(UnsafeTargetError):
        TextPatchEngine().prepare(
            tmp_path,
            SourcePatch("config.py", digest(target.read_bytes()), patch_text),
        )
    assert target.read_text(encoding="utf-8") == "value = 'safe'\n"


def test_commit_rechecks_preimage_and_refuses_racy_overwrite(tmp_path):
    target = tmp_path / "app.py"
    before = "x = 1\n"
    after = "x = 2\n"
    target.write_text(before, encoding="utf-8")
    engine = TextPatchEngine()
    prepared = engine.prepare(
        tmp_path,
        SourcePatch("app.py", digest(before.encode()), unified("app.py", before, after)),
    )

    target.write_text("external = True\n", encoding="utf-8")
    with pytest.raises(StaleBaseError):
        engine.commit(tmp_path, prepared)
    assert target.read_text(encoding="utf-8") == "external = True\n"


def test_noop_or_effectively_unchanged_patch_is_rejected(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")
    engine = TextPatchEngine()

    empty_hunk = "--- a/app.py\n+++ b/app.py\n@@ -1,0 +1,0 @@\n"
    with pytest.raises(PatchConflictError):
        engine.prepare(tmp_path, SourcePatch("app.py", digest(target.read_bytes()), empty_hunk))

    same_content = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-x = 1\n+x = 1\n"
    with pytest.raises(PatchConflictError):
        engine.prepare(tmp_path, SourcePatch("app.py", digest(target.read_bytes()), same_content))
    assert target.read_text(encoding="utf-8") == "x = 1\n"
