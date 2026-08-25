from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
from typing import Mapping, Protocol
from uuid import UUID

from .lineage_persistence import (
    DurableLineagePersistenceError,
    ImmutableObjectStore,
    LineageMetadataStore,
    MetadataCASConflict,
    ObjectMissingError,
)


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
_OBJECT_PERSIST_WORKERS = 8


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
    """Canonical #60 lineage semantics over explicit durable persistence adapters.

    Accepted source bytes and lineage/head metadata never depend on a local
    filesystem path. Local paths enter only when an accepted lineage is scanned
    from or materialized into a disposable protected workspace lease.
    """

    def __init__(
        self,
        object_store: ImmutableObjectStore,
        metadata_store: LineageMetadataStore,
        *,
        max_files: int = 2_000,
        max_file_bytes: int = 4_000_000,
        max_total_bytes: int = 64_000_000,
        max_source_ref_bytes: int = 512,
    ) -> None:
        if max_files < 1 or max_file_bytes < 1 or max_total_bytes < 1 or max_source_ref_bytes < 1:
            raise ValueError("lineage resource bounds must be positive")
        self.object_store = object_store
        self.metadata_store = metadata_store
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.max_source_ref_bytes = max_source_ref_bytes

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

        self._persist_prepared(prepared)
        try:
            result = self.metadata_store.commit_manifest_and_advance(
                project_id=identity.project_id,
                run_id=identity.run_id,
                lineage_id=candidate.lineage_id,
                manifest=self._serialized_manifest(candidate),
                expected_current_lineage_id=None,
            )
        except MetadataCASConflict as exc:
            if exc.current_lineage_id == candidate.lineage_id:
                return self.resolve(identity, candidate.lineage_id)
            raise StaleLineageError("source lineage is already initialized for this Project/run") from exc
        except DurableLineagePersistenceError as exc:
            raise LineageIntegrityError("durable source-lineage metadata could not be committed") from exc

        if result.lineage_id != candidate.lineage_id:
            raise LineageIntegrityError("durable metadata returned a different lineage identity")
        return self.resolve(identity, candidate.lineage_id)

    def capture_implementation(
        self,
        identity: ProjectRunIdentity,
        workspace_root: str | Path,
        *,
        expected_parent_lineage_id: str,
    ) -> SourceLineage:
        self._validate_lineage_id(expected_parent_lineage_id)
        prepared = self._prepare_workspace(workspace_root)
        current = self.current(identity)
        if current is None:  # defensive for type narrowing
            raise LineageNotFoundError("Project/run source lineage is not initialized")

        if current.lineage_id != expected_parent_lineage_id:
            if current.parent_lineage_id == expected_parent_lineage_id and current.content_digest == prepared.content_digest:
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
        try:
            result = self.metadata_store.commit_manifest_and_advance(
                project_id=identity.project_id,
                run_id=identity.run_id,
                lineage_id=candidate.lineage_id,
                manifest=self._serialized_manifest(candidate),
                expected_current_lineage_id=current.lineage_id,
            )
        except MetadataCASConflict as exc:
            if exc.current_lineage_id is not None:
                durable_current = self.resolve(identity, exc.current_lineage_id)
                if (
                    durable_current.parent_lineage_id == expected_parent_lineage_id
                    and durable_current.content_digest == prepared.content_digest
                ):
                    return durable_current
            raise StaleLineageError("expected parent lineage lost the durable advancement race") from exc
        except DurableLineagePersistenceError as exc:
            raise LineageIntegrityError("durable source-lineage metadata could not be advanced") from exc

        if result.lineage_id != candidate.lineage_id:
            raise LineageIntegrityError("durable metadata returned a different implementation lineage")
        return self.resolve(identity, candidate.lineage_id)

    def current(self, identity: ProjectRunIdentity, *, required: bool = True) -> SourceLineage | None:
        try:
            lineage_id = self.metadata_store.get_current(identity.project_id, identity.run_id)
        except DurableLineagePersistenceError as exc:
            raise LineageIntegrityError("durable current-lineage metadata could not be read") from exc
        if lineage_id is None:
            if required:
                raise LineageNotFoundError("Project/run source lineage is not initialized")
            return None
        if not isinstance(lineage_id, str):
            raise LineageIntegrityError("durable current-lineage metadata is invalid")
        return self.resolve(identity, lineage_id)

    def resolve(self, identity: ProjectRunIdentity, lineage_id: str) -> SourceLineage:
        self._validate_lineage_id(lineage_id)
        try:
            serialized = self.metadata_store.get_manifest(lineage_id)
        except DurableLineagePersistenceError as exc:
            raise LineageIntegrityError("durable source-lineage manifest could not be read") from exc
        if serialized is None:
            raise LineageNotFoundError("source lineage does not exist")
        try:
            payload = json.loads(serialized.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LineageIntegrityError("source lineage manifest is invalid") from exc
        lineage = self._lineage_from_manifest(payload)
        if lineage.lineage_id != lineage_id:
            raise LineageIntegrityError("source lineage manifest identity mismatch")
        if lineage.project_id != identity.project_id or lineage.run_id != identity.run_id:
            raise LineageIntegrityError("source lineage belongs to a different Project/run")
        self._verify_lineage_identity(lineage)
        self._verify_objects(lineage.files)
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
                content = self._read_object(item.sha256)
                if len(content) != item.size:
                    raise LineageIntegrityError("source object size mismatch")
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
        def persist_one(item: LineageFile) -> None:
            self.object_store.put_if_absent(item.sha256, prepared.contents[item.path])

        try:
            worker_count = min(_OBJECT_PERSIST_WORKERS, len(prepared.files))
            if worker_count <= 1:
                for item in prepared.files:
                    persist_one(item)
            else:
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    tuple(executor.map(persist_one, prepared.files))
        except DurableLineagePersistenceError as exc:
            # Immutable objects written before a later failure may remain as
            # harmless unreferenced content, but accepted metadata/head state is
            # never advanced until every object write succeeds.
            raise LineageIntegrityError("durable source object persistence failed") from exc

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
            if not isinstance(file_count, int) or isinstance(file_count, bool) or file_count != len(file_tuple):
                raise LineageIntegrityError("source lineage file count mismatch")
            if file_count > self.max_files:
                raise LineageIntegrityError("source lineage file count exceeds protected bound")
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
        expected = f"src:{sha256(self._canonical_json(self._manifest_core(lineage))).hexdigest()}"
        if expected != lineage.lineage_id:
            raise LineageIntegrityError("source lineage manifest was modified")

    def _verify_objects(self, files: tuple[LineageFile, ...]) -> None:
        for item in files:
            content = self._read_object(item.sha256)
            if len(content) != item.size:
                raise LineageIntegrityError("source object size mismatch")

    def _read_object(self, digest: str) -> bytes:
        if not HEX_SHA256.fullmatch(digest):
            raise LineageIntegrityError("source object digest is invalid")
        try:
            content = self.object_store.get(digest)
        except ObjectMissingError as exc:
            raise LineageIntegrityError("source lineage object is missing") from exc
        except DurableLineagePersistenceError as exc:
            raise LineageIntegrityError("durable source object could not be read") from exc
        payload = bytes(content)
        if sha256(payload).hexdigest() != digest:
            raise LineageIntegrityError("source lineage object digest mismatch")
        return payload

    def _serialized_manifest(self, lineage: SourceLineage) -> bytes:
        return self._canonical_json(self._manifest_payload(lineage)) + b"\n"

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
