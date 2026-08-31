from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import errno
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile


DEFAULT_MAX_FILE_BYTES = 512_000
DEFAULT_MAX_PATCH_BYTES = 512_000
DEFAULT_MAX_RESULT_BYTES = 768_000
DEFAULT_MAX_MISSING_PARENT_DIRECTORIES = 16
EMPTY_SHA256 = sha256(b"").hexdigest()

_SUPPORTED_SUFFIXES = frozenset(
    {
        ".bash",
        ".c",
        ".cfg",
        ".conf",
        ".cpp",
        ".cs",
        ".css",
        ".gql",
        ".go",
        ".graphql",
        ".h",
        ".hpp",
        ".html",
        ".ini",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".kt",
        ".kts",
        ".less",
        ".md",
        ".mjs",
        ".php",
        ".ps1",
        ".py",
        ".pyi",
        ".rb",
        ".rs",
        ".sass",
        ".scss",
        ".sh",
        ".sql",
        ".svelte",
        ".swift",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".vue",
        ".xml",
        ".yaml",
        ".yml",
        ".zsh",
    }
)
_SUPPORTED_EXTENSIONLESS = frozenset({"dockerfile", "makefile", "procfile"})
_SECRET_FILENAMES = frozenset(
    {
        ".env",
        ".npmrc",
        ".pypirc",
        "credentials",
        "credentials.json",
        "id_dsa",
        "id_ed25519",
        "id_ecdsa",
        "id_rsa",
        "secrets.json",
    }
)
_SECRET_SUFFIXES = frozenset({".key", ".p12", ".pem", ".pfx"})
_SECRET_DIRECTORIES = frozenset({".aws", ".git", ".gnupg", ".ssh"})
_SECRET_CONTENT_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{16,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")


class PatchError(ValueError):
    """Base class for safe patch rejection."""


class UnsafeTargetError(PatchError):
    pass


class PatchFormatError(PatchError):
    pass


class StaleBaseError(PatchError):
    pass


class PatchConflictError(PatchError):
    pass


class PatchLimitError(PatchError):
    pass


@dataclass(frozen=True, slots=True)
class SourcePatch:
    path: str
    expected_base_sha256: str
    unified_diff: str


@dataclass(frozen=True, slots=True)
class PreparedPatch:
    path: str
    target: Path
    existed: bool
    before: bytes
    after: bytes
    patch_bytes: bytes
    additions: int
    deletions: int
    missing_parent_directories: tuple[str, ...] = ()

    @property
    def evidence(self) -> dict[str, object]:
        after_digest = sha256(self.after).hexdigest()
        return {
            "path": self.path,
            "created": not self.existed,
            "before_sha256": sha256(self.before).hexdigest(),
            "after_sha256": after_digest,
            "before_size": len(self.before),
            "after_size": len(self.after),
            "patch_sha256": sha256(self.patch_bytes).hexdigest(),
            "patch_size": len(self.patch_bytes),
            "unified_diff": self.patch_bytes.decode("utf-8"),
            "additions": self.additions,
            "deletions": self.deletions,
            "artifact": {"path": self.path, "sha256": after_digest, "size": len(self.after)},
        }


@dataclass(frozen=True, slots=True)
class _DiffRecord:
    prefix: str
    body: str
    no_newline: bool = False

    def content(self) -> str:
        if not self.no_newline:
            return self.body
        if self.body.endswith("\r\n"):
            return self.body[:-2]
        if self.body.endswith("\n"):
            return self.body[:-1]
        return self.body


class TextPatchEngine:
    """Prepare and atomically write bounded text patches inside one workspace.

    The engine deliberately implements a strict unified-diff subset in Python.
    It never invokes a shell, Git, an external patch process, or a network tool.
    """

    def __init__(
        self,
        *,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_patch_bytes: int = DEFAULT_MAX_PATCH_BYTES,
        max_result_bytes: int = DEFAULT_MAX_RESULT_BYTES,
        max_missing_parent_directories: int = DEFAULT_MAX_MISSING_PARENT_DIRECTORIES,
    ) -> None:
        if min(
            max_file_bytes,
            max_patch_bytes,
            max_result_bytes,
            max_missing_parent_directories,
        ) <= 0:
            raise ValueError("patch limits must be positive")
        self.max_file_bytes = max_file_bytes
        self.max_patch_bytes = max_patch_bytes
        self.max_result_bytes = max_result_bytes
        self.max_missing_parent_directories = max_missing_parent_directories

    def normalize_path(self, path: str) -> str:
        if not isinstance(path, str) or not path:
            raise UnsafeTargetError("patch target path is required")
        if "\x00" in path:
            raise UnsafeTargetError("patch target contains a NUL byte")
        if "\\" in path:
            raise UnsafeTargetError("patch target must use POSIX separators")
        if path.startswith("/"):
            raise UnsafeTargetError("absolute patch targets are forbidden")
        raw_parts = path.split("/")
        if any(part in {"", ".", ".."} for part in raw_parts):
            raise UnsafeTargetError("patch target contains an unsafe path segment")
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts:
            raise UnsafeTargetError("patch target escapes the workspace")
        normalized = pure.as_posix()
        self._validate_target_name(pure)
        return normalized

    def prepare(self, workspace_root: str | Path, patch: SourcePatch) -> PreparedPatch:
        normalized = self.normalize_path(patch.path)
        expected = patch.expected_base_sha256
        if not isinstance(expected, str) or _SHA256_RE.fullmatch(expected) is None:
            raise StaleBaseError("expected base SHA-256 must be 64 lowercase hexadecimal characters")

        try:
            patch_bytes = patch.unified_diff.encode("utf-8")
        except (AttributeError, UnicodeEncodeError) as exc:
            raise PatchFormatError("unified diff must be valid UTF-8 text") from exc
        if len(patch_bytes) > self.max_patch_bytes:
            raise PatchLimitError("unified diff exceeds the configured patch-size limit")
        if b"\x00" in patch_bytes:
            raise PatchFormatError("unified diff contains binary NUL content")
        self._reject_secret_content(patch.unified_diff)

        root, target, missing_parent_directories = self._safe_target(
            workspace_root,
            normalized,
            allow_missing_parents=expected == EMPTY_SHA256,
        )
        del root  # containment has been validated; target is the only required value below.

        existed = target.exists()
        if existed:
            if not target.is_file() or target.is_symlink():
                raise UnsafeTargetError("existing patch target must be a regular non-symlink file")
            before = target.read_bytes()
            if len(before) > self.max_file_bytes:
                raise PatchLimitError("source file exceeds the configured file-size limit")
            self._decode_source(before)
            actual = sha256(before).hexdigest()
            if actual != expected:
                raise StaleBaseError("source content does not match the expected base SHA-256")
        else:
            before = b""
            if expected != EMPTY_SHA256:
                raise StaleBaseError("new-file patches must bind to the SHA-256 of empty content")

        after_text, additions, deletions = self._apply_unified_diff(
            path=normalized,
            before=before.decode("utf-8"),
            diff=patch.unified_diff,
            creating=not existed,
        )
        after = after_text.encode("utf-8")
        if additions == 0 and deletions == 0 or after == before:
            raise PatchConflictError("unified diff does not produce a source-content change")
        if len(after) > self.max_result_bytes:
            raise PatchLimitError("patched file exceeds the configured result-size limit")
        self._reject_secret_content(after_text)

        return PreparedPatch(
            path=normalized,
            target=target,
            existed=existed,
            before=before,
            after=after,
            patch_bytes=patch_bytes,
            additions=additions,
            deletions=deletions,
            missing_parent_directories=missing_parent_directories,
        )

    def commit(self, workspace_root: str | Path, prepared: PreparedPatch) -> None:
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
    def _validate_target_name(path: PurePosixPath) -> None:
        lowered_parts = tuple(part.casefold() for part in path.parts)
        if any(part in _SECRET_DIRECTORIES for part in lowered_parts[:-1]):
            raise UnsafeTargetError("secret-sensitive or repository-internal directory is not patchable")
        name = lowered_parts[-1]
        if name in _SECRET_FILENAMES or name.startswith(".env."):
            raise UnsafeTargetError("secret-sensitive target is not patchable")
        suffix = PurePosixPath(name).suffix.casefold()
        if suffix in _SECRET_SUFFIXES:
            raise UnsafeTargetError("private-key or certificate target is not patchable")
        if suffix:
            if suffix not in _SUPPORTED_SUFFIXES:
                raise UnsafeTargetError("unsupported or binary-prone file extension")
        elif name not in _SUPPORTED_EXTENSIONLESS:
            raise UnsafeTargetError("extensionless target is not in the supported source-file allowlist")

    @staticmethod
    def _decode_source(value: bytes) -> str:
        if b"\x00" in value:
            raise UnsafeTargetError("binary source content is not patchable")
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnsafeTargetError("source file must be valid UTF-8 text") from exc

    @staticmethod
    def _reject_secret_content(value: str) -> None:
        if any(pattern.search(value) for pattern in _SECRET_CONTENT_PATTERNS):
            raise UnsafeTargetError("patch/source content appears to contain secret material")

    def _apply_unified_diff(
        self,
        *,
        path: str,
        before: str,
        diff: str,
        creating: bool,
    ) -> tuple[str, int, int]:
        lines = diff.splitlines(keepends=True)
        if len(lines) < 3:
            raise PatchFormatError("unified diff must contain file headers and at least one hunk")

        old_header = self._header_path(lines[0], prefix="--- ")
        new_header = self._header_path(lines[1], prefix="+++ ")
        expected_old = "/dev/null" if creating else f"a/{path}"
        expected_new = f"b/{path}"
        if old_header != expected_old or new_header != expected_new:
            raise PatchFormatError("unified diff file headers do not match the declared target")

        source = before.splitlines(keepends=True)
        output: list[str] = []
        source_index = 0
        index = 2
        additions = 0
        deletions = 0
        saw_hunk = False

        while index < len(lines):
            header = lines[index].rstrip("\r\n")
            match = _HUNK_RE.fullmatch(header)
            if match is None:
                raise PatchFormatError("unexpected content outside a unified diff hunk")
            saw_hunk = True
            old_start = int(match.group(1))
            old_count = int(match.group(2) or "1")
            new_start = int(match.group(3))
            new_count = int(match.group(4) or "1")
            if old_count < 0 or new_count < 0:
                raise PatchFormatError("negative hunk counts are forbidden")

            expected_source_index = old_start if old_count == 0 else old_start - 1
            if expected_source_index < source_index or expected_source_index > len(source):
                raise PatchConflictError("unified diff hunks overlap or address content outside the source")
            output.extend(source[source_index:expected_source_index])
            source_index = expected_source_index
            index += 1

            records: list[_DiffRecord] = []
            while index < len(lines):
                raw = lines[index]
                if _HUNK_RE.fullmatch(raw.rstrip("\r\n")):
                    break
                if raw.startswith("--- ") or raw.startswith("+++ "):
                    raise PatchFormatError("multi-file unified diffs are forbidden")
                if raw.rstrip("\r\n") == r"\ No newline at end of file":
                    if not records or records[-1].no_newline:
                        raise PatchFormatError("orphaned no-newline marker")
                    previous = records[-1]
                    records[-1] = _DiffRecord(previous.prefix, previous.body, True)
                    index += 1
                    continue
                if not raw or raw[0] not in {" ", "+", "-"}:
                    raise PatchFormatError("unsupported unified diff record")
                records.append(_DiffRecord(raw[0], raw[1:]))
                index += 1

            old_seen = 0
            new_seen = 0
            for record in records:
                content = record.content()
                if record.prefix == " ":
                    if source_index >= len(source) or source[source_index] != content:
                        raise PatchConflictError("unified diff context does not match the source")
                    output.append(content)
                    source_index += 1
                    old_seen += 1
                    new_seen += 1
                elif record.prefix == "-":
                    if source_index >= len(source) or source[source_index] != content:
                        raise PatchConflictError("unified diff removal does not match the source")
                    source_index += 1
                    old_seen += 1
                    deletions += 1
                else:
                    output.append(content)
                    new_seen += 1
                    additions += 1

            if old_seen != old_count or new_seen != new_count:
                raise PatchFormatError("unified diff hunk counts do not match its records")

            # new_start is validated against the output position implied by the
            # already-applied patch. A zero-count insertion uses the position
            # before the next output line, matching unified-diff conventions.
            expected_new_index = new_start if new_count == 0 else new_start - 1
            produced_before_hunk = len(output) - new_seen
            if expected_new_index != produced_before_hunk:
                raise PatchConflictError("unified diff new-file hunk position is inconsistent")

        if not saw_hunk:
            raise PatchFormatError("unified diff contains no hunks")
        output.extend(source[source_index:])
        return "".join(output), additions, deletions

    @staticmethod
    def _header_path(line: str, *, prefix: str) -> str:
        if not line.startswith(prefix):
            raise PatchFormatError("unified diff file header is malformed")
        value = line[len(prefix) :].rstrip("\r\n")
        if not value or "\t" in value or " " in value:
            raise PatchFormatError("unified diff file headers must contain only canonical paths")
        return value

    @staticmethod
    def _atomic_replace(target: Path, content: bytes, *, preserve_mode: bool) -> None:
        mode = stat.S_IMODE(target.stat().st_mode) if preserve_mode and target.exists() else 0o644
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.parallax-", dir=target.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, mode)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
