from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from .patching import PatchError, TextPatchEngine


DEFAULT_MAX_SELECTED_FILES = 24
DEFAULT_MAX_FILE_BYTES = 48_000
DEFAULT_MAX_TOTAL_BYTES = 192_000
DEFAULT_MAX_SCANNED_FILES = 2_000

_SKIP_DIRECTORIES = frozenset({".git", ".hg", ".svn", ".aws", ".gnupg", ".ssh", "node_modules", "__pycache__"})
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|client[_-]?secret|access[_-]?token|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+=]{16,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]{3,}")


class SourceContextError(RuntimeError):
    """Base class for protected source-context failures."""


class SourceContextLimitError(SourceContextError):
    pass


@dataclass(frozen=True, slots=True)
class SourceContextFile:
    path: str
    sha256: str
    size: int
    content: str

    def prompt_payload(self) -> dict[str, object]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size": self.size,
            "content": self.content,
        }


@dataclass(frozen=True, slots=True)
class SourceContextSnapshot:
    files: tuple[SourceContextFile, ...]
    digest: str
    total_bytes: int
    excluded_secret_files: int
    omitted_bounded_files: int

    def prompt_payload(self) -> dict[str, object]:
        # The protected local workspace root is deliberately absent.
        return {
            "digest": self.digest,
            "files": [item.prompt_payload() for item in self.files],
            "total_bytes": self.total_bytes,
            "file_count": len(self.files),
        }


class BoundedSourceContextSelector:
    """Select deterministic, bounded, secret-safe source context for generation.

    The workspace root is trusted server-side input from the workspace-lineage
    adapter. It is used only to read source and is never returned in model-visible
    payloads or protected evidence.
    """

    def __init__(
        self,
        *,
        max_selected_files: int = DEFAULT_MAX_SELECTED_FILES,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
        max_scanned_files: int = DEFAULT_MAX_SCANNED_FILES,
        patch_engine: TextPatchEngine | None = None,
    ) -> None:
        if min(max_selected_files, max_file_bytes, max_total_bytes, max_scanned_files) <= 0:
            raise ValueError("source-context limits must be positive")
        self.max_selected_files = max_selected_files
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.max_scanned_files = max_scanned_files
        self.patch_engine = patch_engine or TextPatchEngine()

    def select(
        self,
        workspace_root: str | Path,
        *,
        objective: str,
        acceptance_texts: tuple[str, ...],
    ) -> SourceContextSnapshot:
        root_input = Path(workspace_root)
        if not root_input.exists() or not root_input.is_dir() or root_input.is_symlink():
            raise SourceContextError("protected workspace root is unavailable")
        root = root_input.resolve(strict=True)
        terms = self._terms(objective, acceptance_texts)

        candidates: list[tuple[int, str, Path, int]] = []
        scanned = 0
        for current, dirs, files in os.walk(root, followlinks=False):
            current_path = Path(current)
            dirs[:] = sorted(
                name
                for name in dirs
                if name.casefold() not in _SKIP_DIRECTORIES and not (current_path / name).is_symlink()
            )
            for name in sorted(files):
                candidate = current_path / name
                if candidate.is_symlink() or not candidate.is_file():
                    continue
                scanned += 1
                if scanned > self.max_scanned_files:
                    raise SourceContextLimitError("workspace exceeds the configured source scan limit")
                try:
                    relative = candidate.relative_to(root).as_posix()
                    normalized = self.patch_engine.normalize_path(relative)
                except (ValueError, PatchError):
                    continue
                try:
                    size = candidate.stat().st_size
                except OSError as exc:
                    raise SourceContextError("source metadata could not be read") from exc
                score = self._path_score(normalized, terms)
                candidates.append((-score, normalized, candidate, size))

        candidates.sort(key=lambda item: (item[0], item[1]))
        selected: list[SourceContextFile] = []
        total = 0
        excluded_secret = 0
        omitted_bounded = 0
        for _, normalized, candidate, size in candidates:
            if len(selected) >= self.max_selected_files:
                omitted_bounded += 1
                continue
            if size > self.max_file_bytes:
                # Preserve the per-file ceiling without truncating a ranked file
                # into misleading partial context. An oversized file is omitted
                # whole and counted so smaller eligible context can still be used.
                omitted_bounded += 1
                continue
            if total + size > self.max_total_bytes:
                omitted_bounded += 1
                continue
            try:
                raw = candidate.read_bytes()
            except OSError as exc:
                raise SourceContextError("source content could not be read") from exc
            if len(raw) != size:
                raise SourceContextError("source changed while bounded context was being selected")
            if b"\x00" in raw:
                continue
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if self._contains_secret(content):
                excluded_secret += 1
                continue
            digest = sha256(raw).hexdigest()
            selected.append(SourceContextFile(normalized, digest, size, content))
            total += size

        projection = [
            {"path": item.path, "sha256": item.sha256, "size": item.size}
            for item in selected
        ]
        digest = sha256(
            json.dumps(projection, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return SourceContextSnapshot(
            files=tuple(selected),
            digest=digest,
            total_bytes=total,
            excluded_secret_files=excluded_secret,
            omitted_bounded_files=omitted_bounded,
        )

    @staticmethod
    def _terms(objective: str, acceptance_texts: tuple[str, ...]) -> frozenset[str]:
        values = [objective, *acceptance_texts]
        return frozenset(
            token.casefold()
            for value in values
            for token in _TOKEN_RE.findall(value)
            if len(token) >= 3
        )

    @staticmethod
    def _path_score(path: str, terms: frozenset[str]) -> int:
        lowered = path.casefold()
        score = sum(4 for term in terms if term in lowered)
        name = Path(path).name.casefold()
        if name in {"readme.md", "package.json", "pyproject.toml", "requirements.txt"}:
            score += 2
        if "/test" in f"/{lowered}" or name.startswith("test_") or name.endswith(".test.ts") or name.endswith(".test.tsx"):
            score += 1
        return score

    @staticmethod
    def _contains_secret(content: str) -> bool:
        return any(pattern.search(content) for pattern in _SECRET_PATTERNS)
