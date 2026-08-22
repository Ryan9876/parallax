from __future__ import annotations

import difflib
from hashlib import sha256
import json
from pathlib import Path

import pytest

from parallax_api.code.implementation import (
    DuplicateTargetError,
    ImplementationCommitError,
    ImplementationLimitError,
    ImplementationRequest,
    SafeImplementationEngine,
)
from parallax_api.code.patching import EMPTY_SHA256, SourcePatch, TextPatchEngine
from parallax_api.intelligence.protected_metrics import evaluate_compiled_plan, evaluate_spec_contract


def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def unified(path: str, before: str, after: str, *, creating: bool = False) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="/dev/null" if creating else f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def source_patch(path: str, before: str, after: str, *, creating: bool = False) -> SourcePatch:
    return SourcePatch(
        path=path,
        expected_base_sha256=EMPTY_SHA256 if creating else digest(before),
        unified_diff=unified(path, before, after, creating=creating),
    )


def test_workstream_spec_and_compiled_plan_pass_protected_validator():
    repository_root = Path(__file__).resolve().parents[3]
    spec_path = repository_root / "specs" / "P2-WS-APP-SAFE-IMPLEMENTATION.md"
    plan_path = repository_root / "specs" / "compiled" / "P2-WS-APP-SAFE-IMPLEMENTATION.plan.json"
    spec_text = spec_path.read_text(encoding="utf-8")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    assert evaluate_spec_contract(spec_text).passed is True
    assert evaluate_compiled_plan(spec_text, plan, require_metadata=False).passed is True


def test_multi_file_implementation_is_successful_and_evidence_is_deterministic(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "src" / "b.py").write_text("b = 1\n", encoding="utf-8")
    request = ImplementationRequest(
        patches=(
            source_patch("src/a.py", "a = 1\n", "a = 2\n"),
            source_patch("src/b.py", "b = 1\n", "b = 2\n"),
        )
    )
    engine = SafeImplementationEngine()
    result = engine.apply(tmp_path, request)

    assert result["protected_success"] is True
    assert result["external_execution"] is False
    assert result["git_mutation"] is False
    assert result["deployment_mutation"] is False
    assert result["file_count"] == 2
    assert len(result["workspace_digest"]) == 64
    assert [item["path"] for item in result["artifacts"]] == ["src/a.py", "src/b.py"]
    assert (tmp_path / "src" / "a.py").read_text(encoding="utf-8") == "a = 2\n"
    assert (tmp_path / "src" / "b.py").read_text(encoding="utf-8") == "b = 2\n"

    # Equivalent inputs in another workspace produce the same observable
    # patch/artifact/workspace evidence; temporary file names are not exposed.
    second = tmp_path / "second"
    (second / "src").mkdir(parents=True)
    (second / "src" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (second / "src" / "b.py").write_text("b = 1\n", encoding="utf-8")
    again = engine.apply(second, request)
    assert again == result


def test_all_patches_prepare_before_first_mutation(tmp_path):
    (tmp_path / "src").mkdir()
    a = tmp_path / "src" / "a.py"
    b = tmp_path / "src" / "b.py"
    a.write_text("a = 1\n", encoding="utf-8")
    b.write_text("b = 1\n", encoding="utf-8")
    request = ImplementationRequest(
        patches=(
            source_patch("src/a.py", "a = 1\n", "a = 2\n"),
            SourcePatch("src/b.py", "0" * 64, unified("src/b.py", "b = 1\n", "b = 2\n")),
        )
    )

    with pytest.raises(Exception):
        SafeImplementationEngine().apply(tmp_path, request)
    assert a.read_text(encoding="utf-8") == "a = 1\n"
    assert b.read_text(encoding="utf-8") == "b = 1\n"


def test_duplicate_targets_are_rejected_before_mutation(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")
    patch = source_patch("app.py", "x = 1\n", "x = 2\n")
    request = ImplementationRequest(patches=(patch, patch))

    with pytest.raises(DuplicateTargetError):
        SafeImplementationEngine().apply(tmp_path, request)
    assert target.read_text(encoding="utf-8") == "x = 1\n"


def test_empty_patch_count_and_aggregate_result_limits_are_enforced(tmp_path):
    with pytest.raises(ImplementationLimitError):
        SafeImplementationEngine().apply(tmp_path, ImplementationRequest(patches=()))

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "src" / "b.py").write_text("b = 1\n", encoding="utf-8")
    request = ImplementationRequest(
        patches=(
            source_patch("src/a.py", "a = 1\n", "a = 'abcdefghij'\n"),
            source_patch("src/b.py", "b = 1\n", "b = 'abcdefghij'\n"),
        )
    )
    with pytest.raises(ImplementationLimitError):
        SafeImplementationEngine(max_total_result_bytes=20).apply(tmp_path, request)
    assert (tmp_path / "src" / "a.py").read_text(encoding="utf-8") == "a = 1\n"
    assert (tmp_path / "src" / "b.py").read_text(encoding="utf-8") == "b = 1\n"


class FailSecondCommitEngine(TextPatchEngine):
    def __init__(self):
        super().__init__()
        self.commits = 0

    def commit(self, workspace_root, prepared):
        self.commits += 1
        if self.commits == 2:
            raise OSError("simulated second commit failure")
        return super().commit(workspace_root, prepared)


def test_later_commit_failure_rolls_back_already_committed_files(tmp_path):
    (tmp_path / "src").mkdir()
    a = tmp_path / "src" / "a.py"
    b = tmp_path / "src" / "b.py"
    a.write_text("a = 1\n", encoding="utf-8")
    b.write_text("b = 1\n", encoding="utf-8")
    request = ImplementationRequest(
        patches=(
            source_patch("src/a.py", "a = 1\n", "a = 2\n"),
            source_patch("src/b.py", "b = 1\n", "b = 2\n"),
        )
    )

    with pytest.raises(ImplementationCommitError) as exc_info:
        SafeImplementationEngine(FailSecondCommitEngine()).apply(tmp_path, request)
    assert exc_info.value.rollback_errors == ()
    assert a.read_text(encoding="utf-8") == "a = 1\n"
    assert b.read_text(encoding="utf-8") == "b = 1\n"


def test_rollback_removes_new_file_created_before_later_failure(tmp_path):
    (tmp_path / "src").mkdir()
    existing = tmp_path / "src" / "existing.py"
    existing.write_text("x = 1\n", encoding="utf-8")
    request = ImplementationRequest(
        patches=(
            source_patch("src/new.py", "", "created = True\n", creating=True),
            source_patch("src/existing.py", "x = 1\n", "x = 2\n"),
        )
    )

    with pytest.raises(ImplementationCommitError):
        SafeImplementationEngine(FailSecondCommitEngine()).apply(tmp_path, request)
    assert not (tmp_path / "src" / "new.py").exists()
    assert existing.read_text(encoding="utf-8") == "x = 1\n"
