from __future__ import annotations

from pathlib import Path
import re


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"expected exactly one replacement in {path}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1))


def regex_replace_once(path: str, pattern: str, replacement: str) -> None:
    target = Path(path)
    text = target.read_text()
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL | re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"expected exactly one regex replacement in {path}: {pattern[:80]!r}")
    target.write_text(updated)


PATCHING = "services/api/parallax_api/code/patching.py"
replace_once(PATCHING, "from hashlib import sha256\nimport os\n", "from hashlib import sha256\nimport errno\nimport os\n")
replace_once(
    PATCHING,
    "DEFAULT_MAX_RESULT_BYTES = 768_000\nEMPTY_SHA256 = sha256(b\"\").hexdigest()\n",
    "DEFAULT_MAX_RESULT_BYTES = 768_000\nDEFAULT_MAX_MISSING_PARENT_DIRECTORIES = 16\nEMPTY_SHA256 = sha256(b\"\").hexdigest()\n",
)
replace_once(
    PATCHING,
    "    deletions: int\n\n    @property\n",
    "    deletions: int\n    missing_parent_directories: tuple[str, ...] = ()\n\n    @property\n",
)
replace_once(
    PATCHING,
    "        max_result_bytes: int = DEFAULT_MAX_RESULT_BYTES,\n    ) -> None:\n        if min(max_file_bytes, max_patch_bytes, max_result_bytes) <= 0:\n            raise ValueError(\"patch limits must be positive\")\n        self.max_file_bytes = max_file_bytes\n        self.max_patch_bytes = max_patch_bytes\n        self.max_result_bytes = max_result_bytes\n",
    "        max_result_bytes: int = DEFAULT_MAX_RESULT_BYTES,\n        max_missing_parent_directories: int = DEFAULT_MAX_MISSING_PARENT_DIRECTORIES,\n    ) -> None:\n        if min(\n            max_file_bytes,\n            max_patch_bytes,\n            max_result_bytes,\n            max_missing_parent_directories,\n        ) <= 0:\n            raise ValueError(\"patch limits must be positive\")\n        self.max_file_bytes = max_file_bytes\n        self.max_patch_bytes = max_patch_bytes\n        self.max_result_bytes = max_result_bytes\n        self.max_missing_parent_directories = max_missing_parent_directories\n",
)
replace_once(
    PATCHING,
    "        root, target = self._safe_target(workspace_root, normalized)\n        del root  # containment has been validated; target is the only required value below.\n",
    "        root, target, missing_parent_directories = self._safe_target(\n            workspace_root,\n            normalized,\n            allow_missing_parents=expected == EMPTY_SHA256,\n        )\n        del root  # containment has been validated; target is the only required value below.\n",
)
replace_once(
    PATCHING,
    "            additions=additions,\n            deletions=deletions,\n        )\n\n    def commit",
    "            additions=additions,\n            deletions=deletions,\n            missing_parent_directories=missing_parent_directories,\n        )\n\n    def commit",
)
regex_replace_once(
    PATCHING,
    r"    def commit\(self, workspace_root: str \| Path, prepared: PreparedPatch\) -> None:\n.*?^    @staticmethod\n    def _validate_target_name",
    '''    def commit(self, workspace_root: str | Path, prepared: PreparedPatch) -> None:
        normalized = self.normalize_path(prepared.path)
        created_parent_directories: tuple[str, ...] = ()

        if prepared.existed:
            _, target, missing = self._safe_target(workspace_root, normalized)
            if missing:
                raise StaleBaseError("prepared existing target parent structure changed before commit")
            if target != prepared.target:
                raise UnsafeTargetError("prepared target no longer resolves to the same workspace path")
            if not target.exists() or not target.is_file() or target.is_symlink():
                raise StaleBaseError("prepared existing target changed type before commit")
            current = target.read_bytes()
            if current != prepared.before:
                raise StaleBaseError("prepared existing target changed before commit")
            self._atomic_replace(target, prepared.after, preserve_mode=True)
            return

        root, target, current_missing = self._safe_target(
            workspace_root,
            normalized,
            allow_missing_parents=True,
        )
        if target != prepared.target:
            raise UnsafeTargetError("prepared target no longer resolves to the same workspace path")
        recorded_missing = set(prepared.missing_parent_directories)
        if any(relative not in recorded_missing for relative in current_missing):
            raise StaleBaseError("prepared new target parent structure changed before commit")
        if target.exists() or target.is_symlink():
            raise StaleBaseError("prepared new target appeared before commit")

        try:
            created_parent_directories = self._create_missing_parent_directories(
                root,
                prepared.missing_parent_directories,
            )
            _, target, missing_after_creation = self._safe_target(workspace_root, normalized)
            if missing_after_creation:
                raise StaleBaseError("prepared new target parent creation is incomplete")
            if target != prepared.target:
                raise UnsafeTargetError("prepared target changed while creating parent directories")
            if target.exists() or target.is_symlink():
                raise StaleBaseError("prepared new target appeared before commit")
            self._atomic_replace(target, prepared.after, preserve_mode=False)
        except Exception:
            self._cleanup_parent_directories(
                root,
                created_parent_directories,
                fail_on_unsafe=False,
            )
            raise

    def restore(self, workspace_root: str | Path, prepared: PreparedPatch) -> None:
        normalized = self.normalize_path(prepared.path)
        root, target, missing = self._safe_target(workspace_root, normalized)
        if missing:
            raise StaleBaseError("committed target parent structure changed before rollback")
        if target != prepared.target:
            raise UnsafeTargetError("prepared rollback target no longer resolves to the same workspace path")

        if not target.exists() or not target.is_file() or target.is_symlink():
            raise StaleBaseError("committed target is unavailable for safe rollback")
        current = target.read_bytes()
        if current != prepared.after:
            raise StaleBaseError("committed target changed after implementation; refusing destructive rollback")

        if prepared.existed:
            self._atomic_replace(target, prepared.before, preserve_mode=True)
        else:
            target.unlink()
            self._cleanup_parent_directories(
                root,
                prepared.missing_parent_directories,
                fail_on_unsafe=True,
            )

    def _safe_target(
        self,
        workspace_root: str | Path,
        normalized: str,
        *,
        allow_missing_parents: bool = False,
    ) -> tuple[Path, Path, tuple[str, ...]]:
        root_input = Path(workspace_root)
        if not root_input.exists() or not root_input.is_dir():
            raise UnsafeTargetError("workspace root must be an existing directory")
        root = root_input.resolve(strict=True)

        current = root
        parts = PurePosixPath(normalized).parts
        missing_parent_directories: list[str] = []
        for index, part in enumerate(parts[:-1], start=1):
            current = current / part
            if current.is_symlink():
                raise UnsafeTargetError("symlink path components are forbidden")
            if current.exists():
                if not current.is_dir():
                    raise UnsafeTargetError("patch target parent component must be a directory")
            else:
                if not allow_missing_parents:
                    raise UnsafeTargetError("patch target parent directory must already exist")
                missing_parent_directories.append(PurePosixPath(*parts[:index]).as_posix())
                if len(missing_parent_directories) > self.max_missing_parent_directories:
                    raise PatchLimitError("patch target exceeds the missing-parent directory limit")

        target = current / parts[-1]
        if target.is_symlink():
            raise UnsafeTargetError("symlink patch targets are forbidden")
        resolved = target.resolve(strict=False)
        if resolved != root and root not in resolved.parents:
            raise UnsafeTargetError("patch target resolves outside the workspace")
        return root, resolved, tuple(missing_parent_directories)

    def _create_missing_parent_directories(
        self,
        root: Path,
        missing_parent_directories: tuple[str, ...],
    ) -> tuple[str, ...]:
        created: list[str] = []
        try:
            for relative in missing_parent_directories:
                pure = PurePosixPath(relative)
                directory = root.joinpath(*pure.parts)
                parent = directory.parent
                if parent.is_symlink() or not parent.exists() or not parent.is_dir():
                    raise UnsafeTargetError("patch parent hierarchy changed before directory creation")
                resolved_parent = parent.resolve(strict=True)
                if resolved_parent != root and root not in resolved_parent.parents:
                    raise UnsafeTargetError("patch parent hierarchy resolves outside the workspace")
                if directory.is_symlink():
                    raise UnsafeTargetError("symlink path components are forbidden")
                if directory.exists():
                    if not directory.is_dir():
                        raise UnsafeTargetError("patch target parent component must be a directory")
                    resolved_directory = directory.resolve(strict=True)
                    if resolved_directory != root and root not in resolved_directory.parents:
                        raise UnsafeTargetError("patch parent hierarchy resolves outside the workspace")
                    continue
                try:
                    directory.mkdir()
                except FileExistsError:
                    if directory.is_symlink() or not directory.is_dir():
                        raise UnsafeTargetError("patch parent hierarchy changed during directory creation")
                    resolved_directory = directory.resolve(strict=True)
                    if resolved_directory != root and root not in resolved_directory.parents:
                        raise UnsafeTargetError("patch parent hierarchy resolves outside the workspace")
                    continue
                created.append(relative)
            return tuple(created)
        except Exception:
            self._cleanup_parent_directories(root, tuple(created), fail_on_unsafe=False)
            raise

    def _cleanup_parent_directories(
        self,
        root: Path,
        parent_directories: tuple[str, ...],
        *,
        fail_on_unsafe: bool,
    ) -> None:
        for relative in reversed(parent_directories):
            directory = root.joinpath(*PurePosixPath(relative).parts)
            if directory.is_symlink():
                if fail_on_unsafe:
                    raise UnsafeTargetError("rollback parent became a symlink")
                continue
            if not directory.exists():
                continue
            if not directory.is_dir():
                if fail_on_unsafe:
                    raise UnsafeTargetError("rollback parent changed type")
                continue
            resolved = directory.resolve(strict=True)
            if resolved != root and root not in resolved.parents:
                if fail_on_unsafe:
                    raise UnsafeTargetError("rollback parent resolves outside the workspace")
                continue
            try:
                directory.rmdir()
            except OSError as exc:
                if exc.errno in {errno.ENOTEMPTY, errno.EEXIST}:
                    continue
                if fail_on_unsafe:
                    raise

    @staticmethod
    def _validate_target_name''',
)

# The canonicalizer may recover malformed new-file diffs. It must be able to
# inspect a safe nested target without creating its missing parents.
replace_once(
    "services/api/parallax_api/code/model_patch_canonicalization.py",
    "        root, target = self._safe_target(workspace_root, normalized)\n        del root\n",
    "        root, target, _ = self._safe_target(\n            workspace_root,\n            normalized,\n            allow_missing_parents=True,\n        )\n        del root\n",
)

IMPLEMENTATION = "services/api/parallax_api/code/implementation.py"
replace_once(IMPLEMENTATION, "from pathlib import Path\n", "from pathlib import Path, PurePosixPath\n")
replace_once(
    IMPLEMENTATION,
    "class DuplicateTargetError(ImplementationError):\n    pass\n\n\nclass ImplementationCommitError",
    "class DuplicateTargetError(ImplementationError):\n    pass\n\n\nclass TargetHierarchyConflictError(ImplementationError):\n    pass\n\n\nclass ImplementationCommitError",
)
replace_once(
    IMPLEMENTATION,
    "        if len(set(normalized_paths)) != len(normalized_paths):\n            raise DuplicateTargetError(\"implementation request contains duplicate target paths\")\n\n        # Preparation is intentionally side-effect free",
    "        if len(set(normalized_paths)) != len(normalized_paths):\n            raise DuplicateTargetError(\"implementation request contains duplicate target paths\")\n        normalized_parts = [(path, PurePosixPath(path).parts) for path in normalized_paths]\n        for path, parts in normalized_parts:\n            for other_path, other_parts in normalized_parts:\n                if path == other_path or len(parts) >= len(other_parts):\n                    continue\n                if other_parts[: len(parts)] == parts:\n                    raise TargetHierarchyConflictError(\n                        \"implementation request contains conflicting target hierarchy\"\n                    )\n\n        # Preparation is intentionally side-effect free",
)

CONTINUATION = "apps/client/src/state/engineeringRunContinuation.ts"
replace_once(
    CONTINUATION,
    "export function automaticAutonomyOperationKey(run: EngineeringRunContinuationIdentity): string {\n",
    "export function isAuthoritativeAutonomyAdvance(\n  requested: EngineeringRunContinuationIdentity,\n  latest: EngineeringRunContinuationIdentity | null | undefined,\n): boolean {\n  if (!latest || latest.id !== requested.id) return false;\n  if (!Number.isInteger(requested.revision) || requested.revision < 0) return false;\n  if (!Number.isInteger(latest.revision) || latest.revision < 0) return false;\n  return latest.revision > requested.revision;\n}\n\nexport function automaticAutonomyOperationKey(run: EngineeringRunContinuationIdentity): string {\n",
)

HOOK = "apps/client/src/hooks/useEngineeringRun.ts"
replace_once(
    HOOK,
    "  canContinueEngineeringRunAutonomously,\n  MAX_AUTONOMY_REQUESTS_PER_CONTINUATION,\n",
    "  canContinueEngineeringRunAutonomously,\n  isAuthoritativeAutonomyAdvance,\n  MAX_AUTONOMY_REQUESTS_PER_CONTINUATION,\n",
)
replace_once(
    HOOK,
    "      const result = await runEngineeringAutonomy(current, currentOperationKey);\n      const next: EngineeringRunView = { ...result.run, autonomy_stop_reason: result.stop_reason };\n",
    "      let result;\n      try {\n        result = await runEngineeringAutonomy(current, currentOperationKey);\n      } catch (caught) {\n        // An HTTP/API failure is authoritative server truth. Only a transport\n        // exception without a response is ambiguous enough for read-only\n        // reconciliation against the latest canonical Engineering Run.\n        if (caught instanceof EngineeringAutonomyError || !conversationId) throw caught;\n\n        let reconciled: EngineeringRunDto | null = null;\n        try {\n          reconciled = await api.latestEngineeringRun(conversationId);\n        } catch {\n          throw caught;\n        }\n        if (!isAuthoritativeAutonomyAdvance(current, reconciled)) throw caught;\n\n        const recovered: EngineeringRunView = { ...reconciled, autonomy_stop_reason: null };\n        setRun(recovered);\n        clearFailure();\n        if (!canContinueEngineeringRunAutonomously(reconciled)) return recovered;\n        if (completedRequests >= MAX_AUTONOMY_REQUESTS_PER_CONTINUATION) {\n          throw new EngineeringAutonomyError(\n            'Parallax recovered server progress but reached the protected continuation limit. Try again to continue.',\n            'AUTONOMY_CONTINUATION_LIMIT',\n          );\n        }\n        current = reconciled;\n        currentOperationKey = automaticAutonomyOperationKey(current);\n        continue;\n      }\n      const next: EngineeringRunView = { ...result.run, autonomy_stop_reason: result.stop_reason };\n",
)
replace_once(HOOK, "  }, [clearFailure]);\n", "  }, [clearFailure, conversationId]);\n")

TEST_SCRIPT = "apps/client/scripts/test-engineering-run-continuation.cjs"
replace_once(
    TEST_SCRIPT,
    "  canContinueEngineeringRunAutonomously,\n  MAX_AUTONOMY_REQUESTS_PER_CONTINUATION,\n",
    "  canContinueEngineeringRunAutonomously,\n  isAuthoritativeAutonomyAdvance,\n  MAX_AUTONOMY_REQUESTS_PER_CONTINUATION,\n",
)
replace_once(
    TEST_SCRIPT,
    "assert.equal(MAX_AUTONOMY_REQUESTS_PER_CONTINUATION, 8);\n",
    "assert.equal(MAX_AUTONOMY_REQUESTS_PER_CONTINUATION, 8);\nassert.equal(\n  isAuthoritativeAutonomyAdvance(\n    { ...base, state: 'IMPLEMENT' },\n    { ...base, revision: 8, state: 'BUILD' },\n  ),\n  true,\n  'same-run newer revision is authoritative recovered progress',\n);\nassert.equal(\n  isAuthoritativeAutonomyAdvance(\n    { ...base, state: 'IMPLEMENT' },\n    { ...base, revision: 7, state: 'IMPLEMENT' },\n  ),\n  false,\n  'unchanged revision is not proof that an ambiguous request completed',\n);\nassert.equal(\n  isAuthoritativeAutonomyAdvance(\n    { ...base, state: 'IMPLEMENT' },\n    { ...base, revision: 6, state: 'PLAN' },\n  ),\n  false,\n  'older revision is never recovered progress',\n);\nassert.equal(\n  isAuthoritativeAutonomyAdvance(\n    { ...base, state: 'IMPLEMENT' },\n    { ...base, id: '55555555-5555-4555-8555-555555555555', revision: 8, state: 'BUILD' },\n  ),\n  false,\n  'a different run cannot reconcile an ambiguous request',\n);\nassert.equal(\n  isAuthoritativeAutonomyAdvance({ ...base, state: 'IMPLEMENT' }, null),\n  false,\n  'missing canonical state is not proof of progress',\n);\n",
)

nested_tests = r'''from __future__ import annotations

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
'''
Path("services/api/tests/test_nested_new_file_creation_v02325.py").write_text(nested_tests)

print("P2-V0.23.25 implementation patch applied")
