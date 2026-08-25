from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath
import re
import tomllib
from typing import Iterable, Mapping
from uuid import UUID


PROFILE_VERSION = 1
_MAX_REPOSITORY_REF_BYTES = 256
_MAX_REVISION_BYTES = 128
_DEFAULT_MAX_ENTRIES = 512
_DEFAULT_MAX_EVIDENCE_BYTES = 2_000_000
_DEFAULT_MAX_ENTRY_BYTES = 512_000
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY_REF_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REQUIREMENTS_RE = re.compile(r"^requirements(?:[-_.][A-Za-z0-9_.-]+)?\.txt$")

_PACKAGE_SCRIPT_CANDIDATES = frozenset({"build", "test", "lint", "typecheck", "check"})
_KNOWN_JS_FRAMEWORKS: Mapping[str, str] = {
    "next": "nextjs",
    "react": "react",
    "vite": "vite",
    "express": "express",
    "@vitejs/plugin-react": "vite-react",
}
_KNOWN_PYTHON_FRAMEWORKS: Mapping[str, str] = {
    "fastapi": "fastapi",
    "flask": "flask",
    "django": "django",
    "pytest": "pytest",
}
_UNSUPPORTED_ROOT_MARKERS = frozenset({"Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts"})
_WORKSPACE_MARKERS = frozenset({"pnpm-workspace.yaml", "turbo.json", "nx.json"})
_EVIDENCE_BASENAMES = frozenset(
    {
        "package.json",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "pytest.ini",
        "tox.ini",
        "index.html",
        "tsconfig.json",
        "vite.config.js",
        "vite.config.mjs",
        "vite.config.ts",
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
        "pnpm-workspace.yaml",
        "turbo.json",
        "nx.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    }
)


class RepositoryShape(StrEnum):
    SINGLE_PACKAGE = "single-package"
    STATIC_WEB = "static-web"
    PYTHON_SERVICE = "python-service"
    WORKSPACE_MONOREPO = "workspace-monorepo"
    MIXED = "mixed"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"


class CompatibilityState(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    AMBIGUOUS = "AMBIGUOUS"


class BlockerCode(StrEnum):
    UNSUPPORTED_ECOSYSTEM = "UNSUPPORTED_ECOSYSTEM"
    AMBIGUOUS_APPLICATION_ROOT = "AMBIGUOUS_APPLICATION_ROOT"
    CONFLICTING_WORKSPACE_DECLARATION = "CONFLICTING_WORKSPACE_DECLARATION"
    MALFORMED_MANIFEST = "MALFORMED_MANIFEST"
    UNSAFE_SOURCE_PATH = "UNSAFE_SOURCE_PATH"
    EVIDENCE_LIMIT_EXCEEDED = "EVIDENCE_LIMIT_EXCEEDED"
    SOURCE_IDENTITY_MISMATCH = "SOURCE_IDENTITY_MISMATCH"


class RepositoryEvidenceError(ValueError):
    def __init__(self, code: BlockerCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class RepositorySourceIdentity:
    project_id: str
    repository_ref: str
    revision: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _canonical_uuid(self.project_id))
        object.__setattr__(self, "repository_ref", _canonical_repository_ref(self.repository_ref))
        object.__setattr__(self, "revision", _canonical_revision(self.revision))

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.as_dict())).hexdigest()

    def as_dict(self) -> dict[str, str]:
        return {
            "project_id": self.project_id,
            "repository_ref": self.repository_ref,
            "revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class RepositoryEvidenceEntry:
    path: str
    sha256: str
    size: int
    content: bytes | None = None
    is_symlink: bool = False


@dataclass(frozen=True, slots=True)
class RepositoryEvidenceSnapshot:
    identity: RepositorySourceIdentity
    entries: tuple[RepositoryEvidenceEntry, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    kind: str
    path: str
    sha256: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "path": self.path, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class RepositorySignal:
    kind: str
    value: str
    evidence_path: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value, "evidence_path": self.evidence_path}


@dataclass(frozen=True, slots=True)
class CommandCandidate:
    category: str
    name: str
    source_kind: str
    evidence_path: str
    evidence_sha256: str
    authoritative: bool = False

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "category": self.category,
            "name": self.name,
            "source_kind": self.source_kind,
            "evidence_path": self.evidence_path,
            "evidence_sha256": self.evidence_sha256,
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True, slots=True)
class CompatibilityBlocker:
    code: BlockerCode
    evidence_paths: tuple[str, ...]

    def as_dict(self) -> dict[str, str | list[str]]:
        return {"code": self.code.value, "evidence_paths": list(self.evidence_paths)}


@dataclass(frozen=True, slots=True)
class RepositoryCompatibilityProfile:
    project_id: str
    repository_ref: str
    repository_ref_digest: str
    source_revision: str
    source_identity_digest: str
    profile_version: int
    profile_digest: str
    repository_shape: RepositoryShape
    compatibility_state: CompatibilityState
    package_roots: tuple[str, ...]
    application_roots: tuple[str, ...]
    signals: tuple[RepositorySignal, ...]
    evidence: tuple[EvidenceSummary, ...]
    command_candidates: tuple[CommandCandidate, ...]
    blockers: tuple[CompatibilityBlocker, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "repository_ref": self.repository_ref,
            "repository_ref_digest": self.repository_ref_digest,
            "source_revision": self.source_revision,
            "source_identity_digest": self.source_identity_digest,
            "profile_version": self.profile_version,
            "profile_digest": self.profile_digest,
            "repository_shape": self.repository_shape.value,
            "compatibility_state": self.compatibility_state.value,
            "package_roots": list(self.package_roots),
            "application_roots": list(self.application_roots),
            "signals": [item.as_dict() for item in self.signals],
            "evidence": [item.as_dict() for item in self.evidence],
            "command_candidates": [item.as_dict() for item in self.command_candidates],
            "blockers": [item.as_dict() for item in self.blockers],
        }


@dataclass(frozen=True, slots=True)
class _ValidatedEntry:
    path: str
    sha256: str
    size: int
    content: bytes | None


class RepositoryIntelligenceAnalyzer:
    """Deterministic repository compatibility analysis over server-owned evidence.

    The analyzer deliberately has no filesystem, network, credential, provider,
    shell, package-manager, Git, deployment, or execution dependency. Repository
    content is evidence only and can never become runtime authority here.
    """

    def __init__(
        self,
        expected_identity: RepositorySourceIdentity,
        *,
        max_entries: int = _DEFAULT_MAX_ENTRIES,
        max_evidence_bytes: int = _DEFAULT_MAX_EVIDENCE_BYTES,
        max_entry_bytes: int = _DEFAULT_MAX_ENTRY_BYTES,
    ) -> None:
        if max_entries < 1 or max_evidence_bytes < 1 or max_entry_bytes < 1:
            raise ValueError("repository evidence bounds must be positive")
        self.expected_identity = expected_identity
        self.max_entries = max_entries
        self.max_evidence_bytes = max_evidence_bytes
        self.max_entry_bytes = max_entry_bytes

    def analyze(self, snapshot: RepositoryEvidenceSnapshot) -> RepositoryCompatibilityProfile:
        if snapshot.identity != self.expected_identity:
            raise RepositoryEvidenceError(BlockerCode.SOURCE_IDENTITY_MISMATCH)
        entries = self._validated_entries(snapshot.entries)

        blockers: list[CompatibilityBlocker] = []
        evidence: list[EvidenceSummary] = []
        signals: set[tuple[str, str, str]] = set()
        candidates: set[tuple[str, str, str, str, str]] = set()
        package_roots: set[str] = set()
        python_roots: set[str] = set()
        static_roots: set[str] = set()
        workspace_roots: set[str] = set()
        unsupported_markers: list[str] = []
        malformed_paths: list[str] = []

        by_path = {entry.path: entry for entry in entries}
        for entry in entries:
            path = entry.path
            basename = PurePosixPath(path).name
            root = _root_for(path)

            if _is_evidence_file(basename):
                evidence.append(EvidenceSummary(kind=_evidence_kind(basename), path=path, sha256=entry.sha256))

            if basename == "package.json":
                package_roots.add(root)
                signals.add(("ecosystem", "javascript-node", path))
                package = self._parse_package_json(entry)
                if package is None:
                    malformed_paths.append(path)
                    continue
                if _declares_workspace(package):
                    workspace_roots.add(root)
                for dependency, framework in _KNOWN_JS_FRAMEWORKS.items():
                    if dependency in _package_dependencies(package):
                        signals.add(("framework", framework, path))
                scripts = package.get("scripts")
                if scripts is not None and not isinstance(scripts, dict):
                    malformed_paths.append(path)
                    continue
                if isinstance(scripts, dict):
                    for script_name in sorted(_PACKAGE_SCRIPT_CANDIDATES.intersection(scripts)):
                        candidates.add((script_name, script_name, "package-script", path, entry.sha256))

            elif basename == "pyproject.toml":
                python_roots.add(root)
                signals.add(("ecosystem", "python", path))
                pyproject = self._parse_pyproject(entry)
                if pyproject is None:
                    malformed_paths.append(path)
                    continue
                for dependency, framework in _KNOWN_PYTHON_FRAMEWORKS.items():
                    if dependency in _python_dependencies(pyproject):
                        signals.add(("framework", framework, path))
                if "pytest" in _python_dependencies(pyproject) or _has_pytest_config(pyproject):
                    candidates.add(("test", "pytest", "test-framework", path, entry.sha256))

            elif _REQUIREMENTS_RE.fullmatch(basename) or basename in {"setup.py", "setup.cfg"}:
                python_roots.add(root)
                signals.add(("ecosystem", "python", path))
            elif basename in {"pytest.ini", "tox.ini"}:
                signals.add(("test-framework", "pytest", path))
                candidates.add(("test", "pytest", "test-framework", path, entry.sha256))
            elif basename == "index.html":
                static_roots.add(root)
                signals.add(("application", "static-web", path))
                candidates.add(("visual", "static-web", "application-shape", path, entry.sha256))
            elif basename in _WORKSPACE_MARKERS:
                workspace_roots.add(root)
                signals.add(("workspace", _workspace_signal(basename), path))
            elif basename in _UNSUPPORTED_ROOT_MARKERS:
                unsupported_markers.append(path)

            suffix = PurePosixPath(path).suffix.casefold()
            if suffix in {".ts", ".tsx"} or basename == "tsconfig.json":
                signals.add(("language", "typescript", path))
            elif suffix in {".js", ".jsx", ".mjs", ".cjs"}:
                signals.add(("language", "javascript", path))
            elif suffix == ".py":
                signals.add(("language", "python", path))
            elif suffix == ".html":
                signals.add(("language", "html", path))
            elif suffix == ".css":
                signals.add(("language", "css", path))

        if malformed_paths:
            blockers.append(
                CompatibilityBlocker(BlockerCode.MALFORMED_MANIFEST, tuple(sorted(set(malformed_paths))))
            )

        shape, state, shape_blockers, application_roots = _classify_repository(
            package_roots=package_roots,
            python_roots=python_roots,
            static_roots=static_roots,
            workspace_roots=workspace_roots,
            unsupported_markers=unsupported_markers,
            malformed=bool(malformed_paths),
        )
        blockers.extend(shape_blockers)

        signal_items = tuple(
            RepositorySignal(kind=kind, value=value, evidence_path=path)
            for kind, value, path in sorted(signals)
        )
        evidence_items = tuple(sorted(evidence, key=lambda item: (item.kind, item.path, item.sha256)))
        candidate_items = tuple(
            CommandCandidate(
                category=category,
                name=name,
                source_kind=source_kind,
                evidence_path=path,
                evidence_sha256=digest,
                authoritative=False,
            )
            for category, name, source_kind, path, digest in sorted(candidates)
        )
        blocker_items = tuple(sorted(blockers, key=lambda item: (item.code.value, item.evidence_paths)))
        all_package_roots = tuple(sorted(package_roots.union(python_roots)))
        application_root_items = tuple(sorted(application_roots))

        identity = snapshot.identity
        core: dict[str, object] = {
            "project_id": identity.project_id,
            "repository_ref": identity.repository_ref,
            "repository_ref_digest": sha256(identity.repository_ref.encode("utf-8")).hexdigest(),
            "source_revision": identity.revision,
            "source_identity_digest": identity.digest,
            "profile_version": PROFILE_VERSION,
            "repository_shape": shape.value,
            "compatibility_state": state.value,
            "package_roots": list(all_package_roots),
            "application_roots": list(application_root_items),
            "signals": [item.as_dict() for item in signal_items],
            "evidence": [item.as_dict() for item in evidence_items],
            "command_candidates": [item.as_dict() for item in candidate_items],
            "blockers": [item.as_dict() for item in blocker_items],
        }
        profile_digest = sha256(_canonical_json(core)).hexdigest()
        return RepositoryCompatibilityProfile(
            project_id=identity.project_id,
            repository_ref=identity.repository_ref,
            repository_ref_digest=core["repository_ref_digest"],  # type: ignore[arg-type]
            source_revision=identity.revision,
            source_identity_digest=identity.digest,
            profile_version=PROFILE_VERSION,
            profile_digest=profile_digest,
            repository_shape=shape,
            compatibility_state=state,
            package_roots=all_package_roots,
            application_roots=application_root_items,
            signals=signal_items,
            evidence=evidence_items,
            command_candidates=candidate_items,
            blockers=blocker_items,
        )

    def _validated_entries(self, raw_entries: Iterable[RepositoryEvidenceEntry]) -> tuple[_ValidatedEntry, ...]:
        entries = tuple(raw_entries)
        if not entries or len(entries) > self.max_entries:
            raise RepositoryEvidenceError(BlockerCode.EVIDENCE_LIMIT_EXCEEDED)

        normalized: dict[str, _ValidatedEntry] = {}
        evidence_bytes = 0
        for entry in entries:
            if not isinstance(entry, RepositoryEvidenceEntry):
                raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)
            if entry.is_symlink:
                raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)
            path = _safe_source_path(entry.path)
            if path in normalized:
                raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)
            if not isinstance(entry.size, int) or isinstance(entry.size, bool) or entry.size < 0:
                raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)
            if not isinstance(entry.sha256, str) or not _SHA256_RE.fullmatch(entry.sha256):
                raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)

            content: bytes | None = None
            if entry.content is not None:
                if not isinstance(entry.content, (bytes, bytearray)):
                    raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)
                content = bytes(entry.content)
                if len(content) != entry.size or sha256(content).hexdigest() != entry.sha256:
                    raise RepositoryEvidenceError(BlockerCode.SOURCE_IDENTITY_MISMATCH)
                if len(content) > self.max_entry_bytes:
                    raise RepositoryEvidenceError(BlockerCode.EVIDENCE_LIMIT_EXCEEDED)
                evidence_bytes += len(content)
                if evidence_bytes > self.max_evidence_bytes:
                    raise RepositoryEvidenceError(BlockerCode.EVIDENCE_LIMIT_EXCEEDED)

            normalized[path] = _ValidatedEntry(path=path, sha256=entry.sha256, size=entry.size, content=content)
        return tuple(normalized[path] for path in sorted(normalized))

    @staticmethod
    def _parse_package_json(entry: _ValidatedEntry) -> dict[str, object] | None:
        if entry.content is None:
            return {}
        try:
            payload = json.loads(entry.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _parse_pyproject(entry: _ValidatedEntry) -> dict[str, object] | None:
        if entry.content is None:
            return {}
        try:
            payload = tomllib.loads(entry.content.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError):
            return None
        return payload if isinstance(payload, dict) else None


def _canonical_uuid(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise RepositoryEvidenceError(BlockerCode.SOURCE_IDENTITY_MISMATCH)
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise RepositoryEvidenceError(BlockerCode.SOURCE_IDENTITY_MISMATCH) from exc
    canonical = str(parsed)
    if canonical != value:
        raise RepositoryEvidenceError(BlockerCode.SOURCE_IDENTITY_MISMATCH)
    return canonical


def _canonical_repository_ref(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > _MAX_REPOSITORY_REF_BYTES
        or not _REPOSITORY_REF_RE.fullmatch(value)
        or value.startswith(".")
        or "/." in value
    ):
        raise RepositoryEvidenceError(BlockerCode.SOURCE_IDENTITY_MISMATCH)
    return value


def _canonical_revision(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value.encode("utf-8")) > _MAX_REVISION_BYTES
        or not _GIT_REVISION_RE.fullmatch(value)
    ):
        raise RepositoryEvidenceError(BlockerCode.SOURCE_IDENTITY_MISMATCH)
    return value


def _safe_source_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or value.startswith("./") or value.endswith("/"):
        raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)
    parts = candidate.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)
    normalized = candidate.as_posix()
    if normalized != value:
        raise RepositoryEvidenceError(BlockerCode.UNSAFE_SOURCE_PATH)
    return normalized


def _root_for(path: str) -> str:
    parent = PurePosixPath(path).parent.as_posix()
    return "." if parent == "." else parent


def _is_evidence_file(basename: str) -> bool:
    return basename in _EVIDENCE_BASENAMES or bool(_REQUIREMENTS_RE.fullmatch(basename))


def _evidence_kind(basename: str) -> str:
    if basename == "package.json":
        return "package-manifest"
    if basename == "pyproject.toml":
        return "python-manifest"
    if _REQUIREMENTS_RE.fullmatch(basename):
        return "python-requirements"
    if basename in _WORKSPACE_MARKERS:
        return "workspace-config"
    if basename == "index.html":
        return "static-entry"
    if basename in _UNSUPPORTED_ROOT_MARKERS:
        return "unsupported-ecosystem-marker"
    return "repository-config"


def _workspace_signal(basename: str) -> str:
    return {
        "pnpm-workspace.yaml": "pnpm-workspace",
        "turbo.json": "turborepo",
        "nx.json": "nx-workspace",
    }[basename]


def _declares_workspace(package: Mapping[str, object]) -> bool:
    workspaces = package.get("workspaces")
    if workspaces is None:
        return False
    if isinstance(workspaces, list):
        return all(isinstance(item, str) for item in workspaces)
    if isinstance(workspaces, dict):
        packages = workspaces.get("packages")
        return isinstance(packages, list) and all(isinstance(item, str) for item in packages)
    return False


def _package_dependencies(package: Mapping[str, object]) -> frozenset[str]:
    names: set[str] = set()
    for field in ("dependencies", "devDependencies", "peerDependencies"):
        section = package.get(field)
        if isinstance(section, dict):
            names.update(key for key in section if isinstance(key, str))
    return frozenset(names)


def _normalize_python_dependency(value: str) -> str:
    name = re.split(r"[ <>=!~\[;@]", value.strip(), maxsplit=1)[0]
    return name.casefold().replace("_", "-")


def _python_dependencies(pyproject: Mapping[str, object]) -> frozenset[str]:
    result: set[str] = set()
    project = pyproject.get("project")
    if isinstance(project, dict):
        dependencies = project.get("dependencies")
        if isinstance(dependencies, list):
            for item in dependencies:
                if isinstance(item, str):
                    normalized = _normalize_python_dependency(item)
                    if normalized:
                        result.add(normalized)
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for group in optional.values():
                if isinstance(group, list):
                    for item in group:
                        if isinstance(item, str):
                            normalized = _normalize_python_dependency(item)
                            if normalized:
                                result.add(normalized)
    return frozenset(result)


def _has_pytest_config(pyproject: Mapping[str, object]) -> bool:
    tool = pyproject.get("tool")
    return isinstance(tool, dict) and isinstance(tool.get("pytest"), dict)


def _classify_repository(
    *,
    package_roots: set[str],
    python_roots: set[str],
    static_roots: set[str],
    workspace_roots: set[str],
    unsupported_markers: list[str],
    malformed: bool,
) -> tuple[RepositoryShape, CompatibilityState, list[CompatibilityBlocker], set[str]]:
    blockers: list[CompatibilityBlocker] = []
    supported_roots = package_roots.union(python_roots).union(static_roots)

    if malformed:
        return RepositoryShape.AMBIGUOUS, CompatibilityState.AMBIGUOUS, blockers, supported_roots

    root_workspace = "." in workspace_roots
    if workspace_roots and not root_workspace and len(package_roots) > 1:
        blockers.append(
            CompatibilityBlocker(
                BlockerCode.CONFLICTING_WORKSPACE_DECLARATION,
                tuple(sorted(workspace_roots)),
            )
        )
        return RepositoryShape.AMBIGUOUS, CompatibilityState.AMBIGUOUS, blockers, supported_roots

    if len(package_roots) > 1 and not root_workspace:
        blockers.append(
            CompatibilityBlocker(
                BlockerCode.AMBIGUOUS_APPLICATION_ROOT,
                tuple(sorted(package_roots)),
            )
        )
        return RepositoryShape.AMBIGUOUS, CompatibilityState.AMBIGUOUS, blockers, supported_roots

    if unsupported_markers and not supported_roots:
        blockers.append(
            CompatibilityBlocker(
                BlockerCode.UNSUPPORTED_ECOSYSTEM,
                tuple(sorted(unsupported_markers)),
            )
        )
        return RepositoryShape.UNSUPPORTED, CompatibilityState.UNSUPPORTED, blockers, set()

    if not supported_roots:
        blockers.append(CompatibilityBlocker(BlockerCode.UNSUPPORTED_ECOSYSTEM, ()))
        return RepositoryShape.UNSUPPORTED, CompatibilityState.UNSUPPORTED, blockers, set()

    if package_roots and python_roots:
        state = CompatibilityState.PARTIAL if unsupported_markers else CompatibilityState.SUPPORTED
        return RepositoryShape.MIXED, state, blockers, supported_roots

    if root_workspace and len(package_roots) >= 1:
        state = CompatibilityState.PARTIAL if unsupported_markers else CompatibilityState.SUPPORTED
        return RepositoryShape.WORKSPACE_MONOREPO, state, blockers, package_roots.union(static_roots)

    if package_roots:
        state = CompatibilityState.PARTIAL if unsupported_markers else CompatibilityState.SUPPORTED
        return RepositoryShape.SINGLE_PACKAGE, state, blockers, package_roots.union(static_roots)

    if python_roots:
        state = CompatibilityState.PARTIAL if unsupported_markers else CompatibilityState.SUPPORTED
        return RepositoryShape.PYTHON_SERVICE, state, blockers, python_roots

    state = CompatibilityState.PARTIAL if unsupported_markers else CompatibilityState.SUPPORTED
    return RepositoryShape.STATIC_WEB, state, blockers, static_roots


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


__all__ = [
    "BlockerCode",
    "CommandCandidate",
    "CompatibilityBlocker",
    "CompatibilityState",
    "EvidenceSummary",
    "PROFILE_VERSION",
    "RepositoryCompatibilityProfile",
    "RepositoryEvidenceEntry",
    "RepositoryEvidenceError",
    "RepositoryEvidenceSnapshot",
    "RepositoryIntelligenceAnalyzer",
    "RepositoryShape",
    "RepositorySignal",
    "RepositorySourceIdentity",
]
