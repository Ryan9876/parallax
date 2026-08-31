from __future__ import annotations

from hashlib import sha256

import pytest

from parallax_api.code.implementation import (
    ImplementationCommitError,
    ImplementationRequest,
    SafeImplementationEngine,
    TargetHierarchyConflictError,
)
from parallax_api.code.model_patch_canonicalization import CanonicalizingTextPatchEngine
from parallax_api.code.patching import (
    EMPTY_SHA256,
    PatchError,
    SourcePatch,
    TextPatchEngine,
    UnsafeTargetError,
)


def _new_file(path: str, content: str = "ready\n") -> SourcePatch:
    lines = content.splitlines(keepends=True)
    diff = f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n" + "".join(
        f"+{line}" for line in lines
    )
    return SourcePatch(path=path, expected_base_sha256=EMPTY_SHA256, unified_diff=diff)


def test_nested_new_file_validation_is_side_effect_free(tmp_path):
    request = ImplementationRequest((_new_file("prototypes/fml-data-readiness/index.html", "<main>ready</main>\n"),))
    SafeImplementationEngine().validate(tmp_path, request)
    assert not (tmp_path / "prototypes").exists()


def test_nested_new_file_commit_creates_only_required_parents(tmp_path):
    request = ImplementationRequest((_new_file("prototypes/fml-data-readiness/index.html", "<main>ready</main>\n"),))
    result = SafeImplementationEngine().apply(tmp_path, request)
    assert result["applied"] is True
    assert (tmp_path / "prototypes" / "fml-data-readiness" / "index.html").read_text() == "<main>ready</main>\n"
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")) == [
        "prototypes",
        "prototypes/fml-data-readiness",
        "prototypes/fml-data-readiness/index.html",
    ]


def test_sibling_new_files_share_new_parent_safely(tmp_path):
    request = ImplementationRequest((
        _new_file("prototypes/fml-data-readiness/index.html", "index\n"),
        _new_file("prototypes/fml-data-readiness/app.js", "console.log('ready');\n"),
    ))
    SafeImplementationEngine().apply(tmp_path, request)
    assert (tmp_path / "prototypes/fml-data-readiness/index.html").read_text() == "index\n"
    assert (tmp_path / "prototypes/fml-data-readiness/app.js").read_text() == "console.log('ready');\n"


def test_restore_removes_only_recorded_empty_parents(tmp_path):
    (tmp_path / "prototypes").mkdir()
    engine = TextPatchEngine()
    prepared = engine.prepare(tmp_path, _new_file("prototypes/fml-data-readiness/index.html"))
    assert prepared.missing_parent_directories == ("prototypes/fml-data-readiness",)
    engine.commit(tmp_path, prepared)
    engine.restore(tmp_path, prepared)
    assert (tmp_path / "prototypes").is_dir()
    assert not (tmp_path / "prototypes/fml-data-readiness").exists()


class _FailSecondCommit(TextPatchEngine):
    def __init__(self):
        super().__init__()
        self.commit_count = 0

    def commit(self, workspace_root, prepared):
        self.commit_count += 1
        if self.commit_count == 2:
            raise PatchError("synthetic bounded commit failure")
        return super().commit(workspace_root, prepared)


def test_multi_patch_failure_rolls_back_nested_file_and_empty_parents(tmp_path):
    request = ImplementationRequest((
        _new_file("prototypes/fml-data-readiness/index.html", "index\n"),
        _new_file("other.txt", "other\n"),
    ))
    engine = SafeImplementationEngine(_FailSecondCommit())
    with pytest.raises(ImplementationCommitError):
        engine.apply(tmp_path, request)
    assert not (tmp_path / "prototypes").exists()
    assert not (tmp_path / "other.txt").exists()


def test_missing_parent_safety_stays_fail_closed(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "prototypes").symlink_to(outside, target_is_directory=True)
    with pytest.raises(UnsafeTargetError):
        TextPatchEngine().prepare(tmp_path, _new_file("prototypes/fml-data-readiness/index.html"))

    (tmp_path / "prototypes").unlink()
    (tmp_path / "prototypes").write_text("not a directory")
    with pytest.raises(UnsafeTargetError):
        TextPatchEngine().prepare(tmp_path, _new_file("prototypes/fml-data-readiness/index.html"))


def test_nonempty_base_cannot_authorize_missing_parent_creation(tmp_path):
    patch = _new_file("new/module.py", "print('ready')\n")
    patch = SourcePatch(
        path=patch.path,
        expected_base_sha256=sha256(b"existing").hexdigest(),
        unified_diff=patch.unified_diff,
    )
    with pytest.raises(UnsafeTargetError):
        TextPatchEngine().prepare(tmp_path, patch)
    assert not (tmp_path / "new").exists()


def test_secret_and_unsupported_nested_targets_remain_rejected(tmp_path):
    with pytest.raises(UnsafeTargetError):
        TextPatchEngine().prepare(tmp_path, _new_file("prototypes/.env"))
    with pytest.raises(UnsafeTargetError):
        TextPatchEngine().prepare(tmp_path, _new_file("prototypes/image.png"))
    assert not (tmp_path / "prototypes").exists()


def test_target_hierarchy_conflict_is_rejected_before_mutation(tmp_path):
    request = ImplementationRequest((
        _new_file("module.py", "root\n"),
        _new_file("module.py/test.py", "child\n"),
    ))
    with pytest.raises(TargetHierarchyConflictError):
        SafeImplementationEngine().validate(tmp_path, request)
    assert list(tmp_path.iterdir()) == []


def test_sibling_targets_do_not_trigger_hierarchy_conflict(tmp_path):
    request = ImplementationRequest((
        _new_file("pkg/a.py", "a\n"),
        _new_file("pkg/b.py", "b\n"),
    ))
    SafeImplementationEngine().validate(tmp_path, request)
    assert not (tmp_path / "pkg").exists()


def test_canonicalizer_recovers_nested_new_file_without_validation_mutation(tmp_path):
    path = "prototypes/fml-data-readiness/index.html"
    malformed = SourcePatch(
        path=path,
        expected_base_sha256=EMPTY_SHA256,
        unified_diff=f"--- /dev/null\n+++ {path}\n@@ -0,9 +1,1 @@\n+ready\n",
    )
    prepared = CanonicalizingTextPatchEngine().prepare(tmp_path, malformed)
    assert prepared.after == b"ready\n"
    assert prepared.missing_parent_directories == (
        "prototypes",
        "prototypes/fml-data-readiness",
    )
    assert not (tmp_path / "prototypes").exists()
