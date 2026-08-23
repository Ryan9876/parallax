from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from threading import RLock
from typing import Mapping, Protocol
from uuid import UUID


LINEAGE_VERSION = 1
LINEAGE_PATTERN = re.compile(r"^src:[0-9a-f]{64}$")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_SOURCE_KINDS = frozenset({"repository", "template", "starter", "implementation"})
SECRET_FILENAMES = frozenset(
    {
        "credentials",
        "credentials.json",
        "secrets",
        "secrets.json",
        "id_rsa",
        "id_ed25519",
    }
)
SECRET_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx"})


class WorkspaceLineageError(RuntimeError):
    pass


class LineageIdentityError(WorkspaceLineageError, ValueError):
    pass


class SourcePolicyError(WorkspaceLineageError, ValueError):
    pass


class SourceProviderError(WorkspaceLineageError):
    pass


class LineageNotFoundError(WorkspaceLineageError, LookupError):
    pass


class LineageIntegrityError(WorkspaceLineageError):
    pass


class StaleLineageError(WorkspaceLineageError):
    pass


class NoSourceChangeError(WorkspaceLineageError):
    pass


def _canonical_uuid(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise LineageIdentityError(f"{label} must be a canonical UUID")
    if value.startswith("project:") or "/" in value or "\\" in value or "://" in value:
        raise LineageIdentityError(f"{label} is opaque identity, not filesystem or URL authority")
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise LineageIdentityError(f"{label} must be a canonical UUID") from exc
    canonical = str(parsed)
    if canonical != value:
        raise LineageIdentityError(f"{label} must use canonical lowercase UUID form")
    return canonical


@dataclass(frozen=True, slots=True)
class ProjectRunIdentity:
    project_id: str
    run_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _canonical_uuid(self.project_id, label="project_id"))
        object.__setattr__(self, "run_id", _canonical_uuid(self.run_id, label="run_id"))

    @property
    def storage_key(self) -> str:
        payload = f"{self.project_id}\0{self.run_id}".encode("utf-8")
        return sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class SourcePackage:
    source_kind: str
    source_ref: str
    files: Mapping[str, bytes]


class SourceProvider(Protocol):
    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        """Return trusted source resolved from protected canonical identity only."""


@dataclass(frozen=True, slots=True)
class LineageFile:
    path: str
    sha256: str
    size: int

    def as_dict(self) -> dict[str, str | int]:
        return {"path": self.path, "sha256": self.sha256, "size": self.size}


@dataclass(frozen=True, slots=True)
class SourceLineage:
    project_id: str
    run_id: str
    lineage_id: str
    parent_lineage_id: str | None
    content_digest: str
    source_kind: str
    source_ref_digest: str | None
    file_count: int
    total_bytes: int
    files: tuple[LineageFile, ...]

    def evidence(self) -> dict[str, str | int | None]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "lineage_id": self.lineage_id,
            "parent_lineage_id": self.parent_lineage_id,
            "content_digest": self.content_digest,
            "source_kind": self.source_kind,
            "source_ref_digest": self.source_ref_digest,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
        }


@dataclass(frozen=True, slots=True)
class _PreparedTree:
    files: tuple[LineageFile, ...]
    contents: dict[str, bytes]
    content_digest: str
    total_bytes: int


class SourceLineageStore:
    def __init__(
        self,
        state_root: str | Path,
        *,
        max_files: int = 2_000,
        max_file_bytes: int = 4_000_000,
        max_total_bytes: int = 64_000_000,
        max_source_ref_bytes: int = 512,
    ) -> None:
        if max_files < 1 or max_file_bytes < 1 or max_total_bytes < 1 or max_source_ref_bytes < 1:
            raise ValueError("lineage resource bounds must be positive")
        root = Path(state_root)
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink():
            raise SourcePolicyError("lineage state root cannot be a symlink")
        self.state_root = root.resolve(strict=True)
        self.blobs_root = self.state_root / "blobs"
        self.lineages_root = self.state_root / "lineages"
        self.runs_root = self.state_root / "runs"
        for directory in (self.blobs_root, self.lineages_root, self.runs_root):
            directory.mkdir(exist_ok=True)
            if directory.is_symlink() or not directory.is_dir():
                raise SourcePolicyError("lineage state directories must be protected directories")
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.max_source_ref_bytes = max_source_ref_bytes
        self._lock = RLock()

    def initialize(self, identity: ProjectRunIdentity, provider: SourceProvider) -> SourceLineage:
        try:
            package = provider.load(identity)
        except WorkspaceLineageError:
            raise
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            raise SourceProviderError("trusted source provider failed") from exc
        if not isinstance(package, SourcePackage):
            raise SourceProviderError("trusted source provider returned an invalid package")
        source_kind = self._source_kind(package.source_kind, allow_implementation=False)
        source_ref_digest = self._source_ref_digest(package.source_ref)
        prepared = self._prepare_mapping(package.files)
        candidate = self._lineage(
            identity,
            prepared,
            parent_lineage_id=None,
            source_kind=source_kind,
            source_ref_digest=source_ref_digest,
        )

        with self._lock:
            current = self.current(identity, required=False)
            if current is not None:
                if current.parent_lineage_id is None and current.lineage_id == candidate.lineage_id:
                    return current
                raise StaleLineageError("source lineage is already initialized for this Project/run")
            self._persist_prepared(prepared)
            self._persist_manifest(candidate)
            self._write_current(identity, candidate.lineage_id)
        return candidate

    def capture_implementation(
        self,
        identity: ProjectRunIdentity,
        workspace_root: str | Path,
        *,
        expected_parent_lineage_id: str,
    ) -> SourceLineage:
        self._validate_lineage_id(expected_parent_lineage_id)
        prepared = self._prepare_workspace(workspace_root)

        with self._lock:
            current = self.current(identity)
            if current.lineage_id != expected_parent_lineage_id:
                if (
                    current.parent_lineage_id == expected_parent_lineage_id
                    and current.content_digest == prepared.content_digest
                ):
                    return current
                raise StaleLineageError("expected parent lineage is not current for this Project/run")
            if current.content_digest == prepared.content_digest:
                raise NoSourceChangeError("implementation result did not change the accepted source tree")

            candidate = self._lineage(
                identity,
                prepared,
                parent_lineage_id=current.lineage_id,
                source_kind="implementation",
                source_ref_digest=None,
            )
            self._persist_prepared(prepared)
            self._persist_manifest(candidate)
            self._write_current(identity, candidate.lineage_id)
            return candidate

    def current(self, identity: ProjectRunIdentity, *, required: bool = True) -> SourceLineage | None:
        pointer = self._pointer_path(identity)
        if not pointer.exists():
            if required:
                raise LineageNotFoundError("Project/run source lineage is not initialized")
            return None
        if pointer.is_symlink() or not pointer.is_file():
            raise LineageIntegrityError("current-lineage pointer is not a protected file")
        try:
            payload = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LineageIntegrityError("current-lineage pointer is invalid") from exc
        if payload.get("project_id") != identity.project_id or payload.get("run_id") != identity.run_id:
            raise LineageIntegrityError("current-lineage pointer identity mismatch")
        lineage_id = payload.get("lineage_id")
        if not isinstance(lineage_id, str):
            raise LineageIntegrityError("current-lineage pointer is missing lineage identity")
        return self.resolve(identity, lineage_id)

    def resolve(self, identity: ProjectRunIdentity, lineage_id: str) -> SourceLineage:
        digest = self._validate_lineage_id(lineage_id)
        manifest_path = self.lineages_root / f"{digest}.json"
        if not manifest_path.exists():
            raise LineageNotFoundError("source lineage does not exist")
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise LineageIntegrityError("source lineage manifest is not a protected file")
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LineageIntegrityError("source lineage manifest is invalid") from exc
        lineage = self._lineage_from_manifest(payload)
        if lineage.lineage_id != lineage_id:
            raise LineageIntegrityError("source lineage manifest identity mismatch")
        if lineage.project_id != identity.project_id or lineage.run_id != identity.run_id:
            raise LineageIntegrityError("source lineage belongs to a different Project/run")
        self._verify_lineage_identity(lineage)
        self._verify_blobs(lineage.files)
        return lineage

    def materialize(self, identity: ProjectRunIdentity, lineage_id: str, target_root: str | Path) -> SourceLineage:
        lineage = self.resolve(identity, lineage_id)
        target = Path(target_root)
        if target.exists() or target.is_symlink():
            raise SourcePolicyError("materialization target must not already exist")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.mkdir()
            for item in lineage.files:
                destination = target / item.path
                destination.parent.mkdir(parents=True, exist_ok=True)
                content = self._read_blob(item.sha256)
                if len(content) != item.size:
                    raise LineageIntegrityError("source blob size mismatch")
                destination.write_bytes(content)
            reconstructed = self._prepare_workspace(target)
            if reconstructed.content_digest != lineage.content_digest:
                raise LineageIntegrityError("reconstructed workspace does not match accepted lineage")
            return lineage
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise

    def _prepare_mapping(self, files: Mapping[str, bytes]) -> _PreparedTree:
        if not isinstance(files, Mapping) or not files:
            raise SourcePolicyError("trusted source package must contain at least one file")
        normalized: dict[str, bytes] = {}
        for raw_path, raw_content in files.items():
            path = self._normalize_source_path(raw_path)
            if path in normalized:
                raise SourcePolicyError("trusted source package contains duplicate normalized paths")
            if not isinstance(raw_content, (bytes, bytearray)):
                raise SourcePolicyError("trusted source content must be bytes")
            normalized[path] = bytes(raw_content)
        return self._prepare_contents(normalized)

    def _prepare_workspace(self, workspace_root: str | Path) -> _PreparedTree:
        root = Path(workspace_root)
        if root.is_symlink():
            raise SourcePolicyError("source workspace root cannot be a symlink")
        try:
            resolved_root = root.resolve(strict=True)
        except OSError as exc:
            raise SourcePolicyError("source workspace does not exist") from exc
        if not resolved_root.is_dir():
            raise SourcePolicyError("source workspace must be a directory")
        contents: dict[str, bytes] = {}
        for current, directories, filenames in os.walk(resolved_root, followlinks=False):
            current_path = Path(current)
            for directory in list(directories):
                candidate = current_path / directory
                if candidate.is_symlink():
                    raise SourcePolicyError("source workspace symlink directories are forbidden")
            for filename in filenames:
                candidate = current_path / filename
                if candidate.is_symlink() or not candidate.is_file():
                    raise SourcePolicyError("source workspace must contain regular files only")
                relative = candidate.relative_to(resolved_root).as_posix()
                normalized = self._normalize_source_path(relative)
                contents[normalized] = candidate.read_bytes()
        if not contents:
            raise SourcePolicyError("source workspace must contain at least one file")
        return self._prepare_contents(contents)

    def _prepare_contents(self, contents: Mapping[str, bytes]) -> _PreparedTree:
        if len(contents) > self.max_files:
            raise SourcePolicyError("source tree exceeds protected file-count bound")
        files: list[LineageFile] = []
        copied: dict[str, bytes] = {}
        total = 0
        for path in sorted(contents):
            content = bytes(contents[path])
            size = len(content)
            if size > self.max_file_bytes:
                raise SourcePolicyError("source file exceeds protected byte bound")
            total += size
            if total > self.max_total_bytes:
                raise SourcePolicyError("source tree exceeds protected aggregate byte bound")
            digest = sha256(content).hexdigest()
            files.append(LineageFile(path=path, sha256=digest, size=size))
            copied[path] = content
        file_tuple = tuple(files)
        return _PreparedTree(
            files=file_tuple,
            contents=copied,
            content_digest=self._content_digest(file_tuple),
            total_bytes=total,
        )

    def _lineage(
        self,
        identity: ProjectRunIdentity,
        prepared: _PreparedTree,
        *,
        parent_lineage_id: str | None,
        source_kind: str,
        source_ref_digest: str | None,
    ) -> SourceLineage:
        if parent_lineage_id is not None:
            self._validate_lineage_id(parent_lineage_id)
        core = {
            "version": LINEAGE_VERSION,
            "project_id": identity.project_id,
            "run_id": identity.run_id,
            "parent_lineage_id": parent_lineage_id,
            "content_digest": prepared.content_digest,
            "source_kind": source_kind,
            "source_ref_digest": source_ref_digest,
            "file_count": len(prepared.files),
            "total_bytes": prepared.total_bytes,
            "files": [item.as_dict() for item in prepared.files],
        }
        lineage_id = f"src:{sha256(self._canonical_json(core)).hexdigest()}"
        return SourceLineage(
            project_id=identity.project_id,
            run_id=identity.run_id,
            lineage_id=lineage_id,
            parent_lineage_id=parent_lineage_id,
            content_digest=prepared.content_digest,
            source_kind=source_kind,
            source_ref_digest=source_ref_digest,
            file_count=len(prepared.files),
            total_bytes=prepared.total_bytes,
            files=prepared.files,
        )

    def _persist_prepared(self, prepared: _PreparedTree) -> None:
        for item in prepared.files:
            self._persist_blob(item.sha256, prepared.contents[item.path])

    def _persist_blob(self, digest: str, content: bytes) -> None:
        path = self._blob_path(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise LineageIntegrityError("source blob directory is not protected")
        if path.exists():
            if path.is_symlink() or not path.is_file() or sha256(path.read_bytes()).hexdigest() != digest:
                raise LineageIntegrityError("existing source blob failed integrity verification")
            return
        self._atomic_write_bytes(path, content)

    def _persist_manifest(self, lineage: SourceLineage) -> None:
        digest = self._validate_lineage_id(lineage.lineage_id)
        path = self.lineages_root / f"{digest}.json"
        payload = self._manifest_payload(lineage)
        serialized = self._canonical_json(payload) + b"\n"
        if path.exists():
            if path.is_symlink() or path.read_bytes() != serialized:
                raise LineageIntegrityError("existing lineage manifest differs from immutable lineage")
            return
        self._atomic_write_bytes(path, serialized)

    def _write_current(self, identity: ProjectRunIdentity, lineage_id: str) -> None:
        run_dir = self.runs_root / identity.storage_key
        run_dir.mkdir(exist_ok=True)
        if run_dir.is_symlink() or not run_dir.is_dir():
            raise LineageIntegrityError("Project/run lineage directory is not protected")
        payload = {
            "project_id": identity.project_id,
            "run_id": identity.run_id,
            "lineage_id": lineage_id,
        }
        self._atomic_write_bytes(run_dir / "current.json", self._canonical_json(payload) + b"\n")

    def _lineage_from_manifest(self, payload: object) -> SourceLineage:
        if not isinstance(payload, dict) or payload.get("version") != LINEAGE_VERSION:
            raise LineageIntegrityError("source lineage manifest version is invalid")
        try:
            identity = ProjectRunIdentity(str(payload["project_id"]), str(payload["run_id"]))
            lineage_id = str(payload["lineage_id"])
            self._validate_lineage_id(lineage_id)
            parent = payload.get("parent_lineage_id")
            if parent is not None:
                if not isinstance(parent, str):
                    raise LineageIntegrityError("parent lineage identity is invalid")
                self._validate_lineage_id(parent)
            content_digest = str(payload["content_digest"])
            if not HEX_SHA256.fullmatch(content_digest):
                raise LineageIntegrityError("content digest is invalid")
            source_kind = self._source_kind(str(payload["source_kind"]), allow_implementation=True)
            source_ref_digest = payload.get("source_ref_digest")
            if source_ref_digest is not None:
                if not isinstance(source_ref_digest, str) or not HEX_SHA256.fullmatch(source_ref_digest):
                    raise LineageIntegrityError("source provenance digest is invalid")
            raw_files = payload["files"]
            if not isinstance(raw_files, list) or not raw_files:
                raise LineageIntegrityError("source lineage file evidence is invalid")
            files: list[LineageFile] = []
            seen: set[str] = set()
            for raw in raw_files:
                if not isinstance(raw, dict):
                    raise LineageIntegrityError("source lineage file evidence is invalid")
                path = self._normalize_source_path(raw.get("path"))
                digest = raw.get("sha256")
                size = raw.get("size")
                if path in seen or not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest):
                    raise LineageIntegrityError("source lineage file evidence is invalid")
                if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > self.max_file_bytes:
                    raise LineageIntegrityError("source lineage file size is invalid")
                seen.add(path)
                files.append(LineageFile(path=path, sha256=digest, size=size))
            file_tuple = tuple(files)
            if tuple(sorted(item.path for item in file_tuple)) != tuple(item.path for item in file_tuple):
                raise LineageIntegrityError("source lineage file evidence is not deterministic")
            file_count = payload.get("file_count")
            total_bytes = payload.get("total_bytes")
            if file_count != len(file_tuple) or file_count > self.max_files:
                raise LineageIntegrityError("source lineage file count mismatch")
            expected_total = sum(item.size for item in file_tuple)
            if total_bytes != expected_total or expected_total > self.max_total_bytes:
                raise LineageIntegrityError("source lineage byte count mismatch")
            if self._content_digest(file_tuple) != content_digest:
                raise LineageIntegrityError("source lineage content digest mismatch")
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, WorkspaceLineageError):
                raise
            raise LineageIntegrityError("source lineage manifest shape is invalid") from exc
        return SourceLineage(
            project_id=identity.project_id,
            run_id=identity.run_id,
            lineage_id=lineage_id,
            parent_lineage_id=parent,
            content_digest=content_digest,
            source_kind=source_kind,
            source_ref_digest=source_ref_digest,
            file_count=file_count,
            total_bytes=total_bytes,
            files=file_tuple,
        )

    def _verify_lineage_identity(self, lineage: SourceLineage) -> None:
        core = self._manifest_core(lineage)
        expected = f"src:{sha256(self._canonical_json(core)).hexdigest()}"
        if expected != lineage.lineage_id:
            raise LineageIntegrityError("source lineage manifest was modified")

    def _verify_blobs(self, files: tuple[LineageFile, ...]) -> None:
        for item in files:
            content = self._read_blob(item.sha256)
            if len(content) != item.size:
                raise LineageIntegrityError("source blob size mismatch")

    def _read_blob(self, digest: str) -> bytes:
        path = self._blob_path(digest)
        if not path.exists():
            raise LineageIntegrityError("source lineage blob is missing")
        if path.is_symlink() or not path.is_file():
            raise LineageIntegrityError("source lineage blob is not a protected file")
        content = path.read_bytes()
        if sha256(content).hexdigest() != digest:
            raise LineageIntegrityError("source lineage blob digest mismatch")
        return content

    def _pointer_path(self, identity: ProjectRunIdentity) -> Path:
        return self.runs_root / identity.storage_key / "current.json"

    def _blob_path(self, digest: str) -> Path:
        if not HEX_SHA256.fullmatch(digest):
            raise LineageIntegrityError("source blob digest is invalid")
        return self.blobs_root / digest[:2] / digest

    def _manifest_payload(self, lineage: SourceLineage) -> dict[str, object]:
        payload = self._manifest_core(lineage)
        payload["lineage_id"] = lineage.lineage_id
        return payload

    @staticmethod
    def _manifest_core(lineage: SourceLineage) -> dict[str, object]:
        return {
            "version": LINEAGE_VERSION,
            "project_id": lineage.project_id,
            "run_id": lineage.run_id,
            "parent_lineage_id": lineage.parent_lineage_id,
            "content_digest": lineage.content_digest,
            "source_kind": lineage.source_kind,
            "source_ref_digest": lineage.source_ref_digest,
            "file_count": lineage.file_count,
            "total_bytes": lineage.total_bytes,
            "files": [item.as_dict() for item in lineage.files],
        }

    @staticmethod
    def _content_digest(files: tuple[LineageFile, ...]) -> str:
        digest = sha256()
        for item in files:
            digest.update(f"{item.path}\0{item.sha256}\0{item.size}\n".encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _canonical_json(value: object) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    def _source_ref_digest(self, source_ref: str) -> str:
        if not isinstance(source_ref, str):
            raise SourcePolicyError("source provenance reference must be bounded text")
        encoded = source_ref.encode("utf-8")
        if not encoded or len(encoded) > self.max_source_ref_bytes:
            raise SourcePolicyError("source provenance reference exceeds protected bound")
        if "\x00" in source_ref or "\n" in source_ref or "\r" in source_ref or "://" in source_ref:
            raise SourcePolicyError("raw URLs or control characters are not accepted as source provenance")
        return sha256(encoded).hexdigest()

    @staticmethod
    def _source_kind(source_kind: str, *, allow_implementation: bool) -> str:
        allowed = ALLOWED_SOURCE_KINDS if allow_implementation else ALLOWED_SOURCE_KINDS - {"implementation"}
        if source_kind not in allowed:
            raise SourcePolicyError("source kind is not protected by this lineage contract")
        return source_kind

    @staticmethod
    def _normalize_source_path(raw_path: object) -> str:
        if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path or "\\" in raw_path:
            raise SourcePolicyError("source path must be a relative POSIX path")
        candidate = PurePosixPath(raw_path)
        if candidate.is_absolute():
            raise SourcePolicyError("absolute source paths are forbidden")
        parts = candidate.parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise SourcePolicyError("source traversal or ambiguous path components are forbidden")
        lowered = tuple(part.lower() for part in parts)
        if ".git" in lowered or ".ssh" in lowered:
            raise SourcePolicyError("Git internals and SSH material are not source lineage content")
        filename = lowered[-1]
        if filename.startswith(".env") or filename in SECRET_FILENAMES:
            raise SourcePolicyError("secret-sensitive source paths are forbidden")
        if any(filename.endswith(suffix) for suffix in SECRET_SUFFIXES):
            raise SourcePolicyError("private key or certificate source paths are forbidden")
        normalized = candidate.as_posix()
        if len(normalized.encode("utf-8")) > 512:
            raise SourcePolicyError("source path exceeds protected bound")
        return normalized

    @staticmethod
    def _validate_lineage_id(lineage_id: str) -> str:
        if not isinstance(lineage_id, str) or not LINEAGE_PATTERN.fullmatch(lineage_id):
            raise LineageIdentityError("source lineage identity is invalid")
        return lineage_id.removeprefix("src:")

    @staticmethod
    def _atomic_write_bytes(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(dir=path.parent, prefix=".tmp-", delete=False)
        temporary = Path(handle.name)
        try:
            with handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


__all__ = [
    "LineageIdentityError",
    "LineageIntegrityError",
    "LineageNotFoundError",
    "NoSourceChangeError",
    "ProjectRunIdentity",
    "SourceLineage",
    "SourceLineageStore",
    "SourcePackage",
    "SourcePolicyError",
    "SourceProvider",
    "SourceProviderError",
    "StaleLineageError",
    "WorkspaceLineageError",
]
