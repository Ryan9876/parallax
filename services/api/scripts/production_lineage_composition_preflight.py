from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from time import monotonic
from uuid import NAMESPACE_URL, uuid5

_SCRIPT_ROOT = Path(__file__).resolve().parent
_API_ROOT = _SCRIPT_ROOT.parent
for _path in (_SCRIPT_ROOT, _API_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from production_blob_sdk_preflight import main as blob_sdk_preflight
from sqlalchemy.orm import sessionmaker

from parallax_api.code.lineage_persistence import (
    PostgresLineageMetadataStore,
    VercelPrivateBlobObjectStore,
)
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import ProjectRunIdentity, SourceLineageStore, SourcePackage
from parallax_api.db import make_engine


_ENV_TARGETS = "PARALLAX_VERCEL_PREVIEW_TARGETS_JSON"
_MAX_TREE_ENTRIES = 1024
_MAX_FILE_BYTES = 256_000
_MAX_LINEAGE_FILES = 2_000
_MAX_LINEAGE_BYTES = 64_000_000
_REPOSITORY = re.compile(r"^github:([^/\s]+)/([^/\s]+)$")
_SOURCE_PATH = re.compile(r"^[A-Za-z0-9._-](?:[A-Za-z0-9._/ -]{0,238}[A-Za-z0-9._-])?$")
_ALLOWED_BLOB_MODES = frozenset({"100644", "100755"})
_PROVIDER_SECRET_PARTS = frozenset({".env", ".env.local", ".env.production", "secrets", "credentials"})
_LINEAGE_SECRET_FILENAMES = frozenset(
    {"credentials", "credentials.json", "secrets", "secrets.json", "id_rsa", "id_ed25519"}
)
_LINEAGE_SECRET_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx"})


@dataclass(frozen=True, slots=True)
class _Target:
    repository_ref: str
    production_branch: str


class _FixedSourceProvider:
    def __init__(self, identity: ProjectRunIdentity, package: SourcePackage) -> None:
        self.identity = identity
        self.package = package

    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        if identity != self.identity:
            raise RuntimeError("lineage composition canary identity mismatch")
        return self.package


def _targets() -> tuple[_Target, ...]:
    raw = os.getenv(_ENV_TARGETS)
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("registered production target is unavailable")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("registered production target is invalid JSON") from exc
    if not isinstance(payload, list) or len(payload) != 1:
        raise RuntimeError("lineage composition canary requires exactly one registered self-hosting target")
    target = payload[0]
    if not isinstance(target, dict):
        raise RuntimeError("registered production target is invalid")
    repository_ref = target.get("repository_ref")
    production_branch = target.get("production_branch")
    if not isinstance(repository_ref, str) or _REPOSITORY.fullmatch(repository_ref) is None:
        raise RuntimeError("registered production repository identity is invalid")
    if not isinstance(production_branch, str) or not production_branch or len(production_branch) > 255:
        raise RuntimeError("registered production branch identity is invalid")
    return (_Target(repository_ref=repository_ref, production_branch=production_branch),)


def _lineage_secret_sensitive(path: str) -> bool:
    parts = tuple(part.casefold() for part in path.split("/"))
    filename = parts[-1] if parts else ""
    return (
        not parts
        or ".git" in parts
        or ".ssh" in parts
        or filename.startswith(".env")
        or filename in _LINEAGE_SECRET_FILENAMES
        or any(filename.endswith(suffix) for suffix in _LINEAGE_SECRET_SUFFIXES)
    )


def _provider_path_valid(path: str) -> bool:
    if not _SOURCE_PATH.fullmatch(path) or path.startswith("/"):
        return False
    parts = path.split("/")
    if ".." in parts:
        return False
    return not ({part.casefold() for part in parts} & _PROVIDER_SECRET_PARTS)


def _git(repo_root: Path, *args: str, text: bool = True):
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=text,
    ).stdout


def _repository_root() -> Path:
    output = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    root = Path(output).resolve(strict=True)
    if not root.is_dir():
        raise RuntimeError("production checkout root is invalid")
    return root


def _local_source_package(target: _Target) -> tuple[SourcePackage, int, int]:
    root = _repository_root()
    head = _git(root, "rev-parse", "HEAD").strip().lower()
    expected_head = (os.getenv("VERCEL_GIT_COMMIT_SHA") or "").strip().lower()
    if expected_head and head != expected_head:
        raise RuntimeError("production checkout revision does not match Vercel deployment revision")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise RuntimeError("production checkout revision is invalid")

    raw = _git(root, "ls-files", "-s", "-z", text=False)
    entries = raw.decode("utf-8", errors="strict").split("\x00")
    files: dict[str, bytes] = {}
    total = 0
    tracked_entries = 0
    for entry in entries:
        if not entry:
            continue
        try:
            metadata, path = entry.split("\t", 1)
            mode, _object_id, stage = metadata.split(" ")
        except ValueError as exc:
            raise RuntimeError("production tracked-file record is invalid") from exc
        tracked_entries += 1
        if tracked_entries > _MAX_TREE_ENTRIES:
            raise RuntimeError("production tracked source tree exceeds protected entry bound")
        if stage != "0" or mode not in _ALLOWED_BLOB_MODES:
            continue
        if _lineage_secret_sensitive(path):
            continue
        if not _provider_path_valid(path):
            raise RuntimeError("production tracked source violates provider path policy")
        candidate = root.joinpath(*path.split("/"))
        if candidate.is_symlink() or not candidate.is_file():
            raise RuntimeError("production tracked source is not a regular file")
        content = candidate.read_bytes()
        size = len(content)
        if size > _MAX_FILE_BYTES:
            raise RuntimeError("production tracked source exceeds projected file byte bound")
        try:
            text = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise RuntimeError("production tracked source is not strict UTF-8") from exc
        if "\x00" in text:
            raise RuntimeError("production tracked source contains NUL content")
        files[path] = content
        total += size
        if len(files) > _MAX_LINEAGE_FILES:
            raise RuntimeError("production tracked source exceeds durable lineage file-count bound")
        if total > _MAX_LINEAGE_BYTES:
            raise RuntimeError("production tracked source exceeds durable lineage aggregate byte bound")

    if not files:
        raise RuntimeError("production tracked source contains no lineage-eligible files")
    package = SourcePackage(
        source_kind="repository",
        source_ref=f"{target.repository_ref}@{head}",
        files=files,
    )
    return package, len(files), total


def _canary_identity(repository_ref: str) -> ProjectRunIdentity:
    project_id = str(uuid5(NAMESPACE_URL, f"parallax:production-lineage-canary:project:{repository_ref}"))
    run_id = str(uuid5(NAMESPACE_URL, f"parallax:production-lineage-canary:run:{repository_ref}"))
    return ProjectRunIdentity(project_id=project_id, run_id=run_id)


def _run_lineage_composition(target: _Target, package: SourcePackage) -> tuple[str, int]:
    identity = _canary_identity(target.repository_ref)
    engine = make_engine(environment="production")
    lineage_id: str | None = None
    object_count = len({sha256(content).hexdigest() for content in package.files.values()})
    try:
        with engine.connect() as connection:
            outer_transaction = connection.begin()
            try:
                sessions = sessionmaker(
                    bind=connection,
                    autoflush=False,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )
                metadata = PostgresLineageMetadataStore(sessions)
                if metadata.get_current(identity.project_id, identity.run_id) is not None:
                    raise RuntimeError("synthetic lineage canary identity is contaminated")
                lineage_store = SourceLineageStore(
                    VercelPrivateBlobObjectStore(),
                    metadata,
                )
                with tempfile.TemporaryDirectory(prefix="parallax-lineage-preflight-") as root:
                    allocator = ProjectWorkspaceAllocator(root, lineage_store=lineage_store)
                    workspace = allocator.initialize(
                        identity,
                        _FixedSourceProvider(identity, package),
                    )
                    lineage = workspace.lineage
                    lineage_id = lineage.lineage_id
                    if lineage.project_id != identity.project_id or lineage.run_id != identity.run_id:
                        raise RuntimeError("lineage composition returned a different synthetic identity")
                    if lineage.parent_lineage_id is not None or lineage.source_kind != "repository":
                        raise RuntimeError("lineage composition violated root-lineage semantics")
                    if lineage.file_count != len(package.files):
                        raise RuntimeError("lineage composition file count does not match projected package")
                    if lineage.total_bytes != sum(len(content) for content in package.files.values()):
                        raise RuntimeError("lineage composition byte count does not match projected package")
                    durable_current = metadata.get_current(identity.project_id, identity.run_id)
                    if durable_current != lineage.lineage_id:
                        raise RuntimeError("lineage composition durable head mismatch")
                    if metadata.get_manifest(lineage.lineage_id) is None:
                        raise RuntimeError("lineage composition durable manifest is unavailable")
                    allocator.cleanup(workspace)
            finally:
                outer_transaction.rollback()

        verification_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        verification = PostgresLineageMetadataStore(verification_sessions)
        if verification.get_current(identity.project_id, identity.run_id) is not None:
            raise RuntimeError("lineage composition rollback left a synthetic durable head")
        if lineage_id is not None and verification.get_manifest(lineage_id) is not None:
            raise RuntimeError("lineage composition rollback left a synthetic durable manifest")
        if lineage_id is None:
            raise RuntimeError("lineage composition did not produce a lineage identity")
        return lineage_id, object_count
    finally:
        engine.dispose()


def main() -> None:
    environment = os.getenv("VERCEL_ENV") or "unknown"
    if environment != "production":
        print(
            "Production lineage composition preflight: SKIP "
            f"(VERCEL_ENV={environment}; durable authority remains production-only)"
        )
        return

    started = monotonic()
    stage = "blob-sdk"
    try:
        blob_sdk_preflight()
        stage = "local-source-package"
        target = _targets()[0]
        package, file_count, total_bytes = _local_source_package(target)
        stage = "lineage-initialize-materialize"
        _lineage_id, object_count = _run_lineage_composition(target, package)
    except Exception as exc:
        print(
            "Production lineage composition preflight: FAIL "
            f"(stage={stage}; error={type(exc).__name__})",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    elapsed_ms = int((monotonic() - started) * 1000)
    print(
        "Production lineage composition preflight: PASS "
        f"(files={file_count}; unique_objects={object_count}; bytes={total_bytes}; elapsed_ms={elapsed_ms}; "
        "metadata_rollback_verified)"
    )


if __name__ == "__main__":
    main()
