from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath
from urllib.parse import quote

from ..models import EngineeringRun
from ..tools.providers import (
    ACTION_REPOSITORY_RESOLVE,
    ACTION_SOURCE_FILE_READ,
    ACTION_SOURCE_TREE_READ,
    GitHubProviderActions,
    ProviderClientError,
)
from ..tools.providers.common import require_repository_ref, require_source_revision
from ..tools.providers.github import MAX_FILE_BYTES
from ..tools.providers.github_client import GitHubRestProviderClient
from .source_delivery_composition import (
    BootstrapResult,
    ProjectRepositoryBindingError,
    RepositoryBoundSourceProvider,
    RepositoryLineageBootstrap,
    SourceBootstrapError,
)
from .workspace_allocator import MaterializedWorkspace
from .workspace_lineage import (
    LineageIdentityError,
    LineageNotFoundError,
    ProjectRunIdentity,
    SourcePackage,
)


_PROJECTION_VERSION = "lineage-safe-v2"
_SECRET_FILENAMES = frozenset(
    {
        "credentials",
        "credentials.json",
        "secrets",
        "secrets.json",
        "id_rsa",
        "id_ed25519",
    }
)
_SECRET_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx"})


def is_lineage_secret_sensitive_path(path: str) -> bool:
    """Match the durable lineage secret-path exclusions before provider reads.

    GitHub tree enumeration exposes names but not file bytes. This projection
    uses only those bounded names to omit content that durable lineage would
    reject anyway, preventing secret-sensitive files from ever entering a
    provider file-read, model/source package, durable object, sandbox transfer,
    mutation, or publication boundary.
    """

    candidate = PurePosixPath(path)
    parts = tuple(part.casefold() for part in candidate.parts)
    if not parts:
        return True
    filename = parts[-1]
    return (
        ".git" in parts
        or ".ssh" in parts
        or filename.startswith(".env")
        or filename in _SECRET_FILENAMES
        or any(filename.endswith(suffix) for suffix in _SECRET_SUFFIXES)
    )


@dataclass(frozen=True, slots=True)
class ProjectedGitHubFileResult:
    """Bounded canonical repository source read after secret-path projection.

    Source code may legitimately contain credential-related syntax and test
    fixtures, so the publication-time secret-literal heuristic is intentionally
    not applied to canonical repository reads. The strict heuristic remains on
    GitHubCommitFile, so Parallax cannot publish the same suspicious literal.
    """

    repository_ref: str
    source_revision: str
    path: str
    content: str
    content_sha256: str

    def __post_init__(self) -> None:
        require_repository_ref(self.repository_ref)
        require_source_revision(self.source_revision)
        if is_lineage_secret_sensitive_path(self.path):
            raise ValueError("secret-sensitive repository path is excluded from source projection")
        candidate = PurePosixPath(self.path)
        if candidate.is_absolute() or not candidate.parts or any(part in {"", ".", ".."} for part in candidate.parts):
            raise ValueError("projected source path must be a bounded relative path")
        encoded = self.content.encode("utf-8")
        if len(encoded) > MAX_FILE_BYTES or "\x00" in self.content:
            raise ValueError("projected source content exceeds the bounded UTF-8 contract")
        if sha256(encoded).hexdigest() != self.content_sha256:
            raise ValueError("projected source content digest does not match content")


class ProjectedGitHubReadClient:
    """Production-only read adapter over the accepted GitHub REST client.

    All provider authentication, repository scoping, timeouts and HTTP status
    normalization remain owned by the existing client. Only successful file
    payload construction differs so legitimate auth/security source code can be
    read after the stricter path projection above.
    """

    def __init__(self, delegate: GitHubRestProviderClient) -> None:
        if not isinstance(delegate, GitHubRestProviderClient):
            raise TypeError("projected GitHub reads require the protected REST client")
        self._delegate = delegate

    def __getattr__(self, name: str):
        return getattr(self._delegate, name)

    def read_file(
        self,
        repository_ref: str,
        source_revision: str,
        path: str,
        *,
        max_bytes: int,
    ) -> ProjectedGitHubFileResult:
        require_repository_ref(repository_ref)
        require_source_revision(source_revision)
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
            raise ValueError("max_bytes must be a positive integer")
        if max_bytes > MAX_FILE_BYTES:
            raise ValueError("projected read exceeds the protected file bound")
        if is_lineage_secret_sensitive_path(path):
            raise ProviderClientError("SOURCE_PATH_EXCLUDED")

        endpoint = f"{self._delegate._repo_path(repository_ref)}/contents/{quote(path, safe='/')}"
        response = self._delegate._send(
            "GET",
            repository_ref,
            endpoint,
            params={"ref": source_revision},
        )
        self._delegate._raise_status(response, not_found="SOURCE_NOT_FOUND")
        payload = self._delegate._json(response)
        if not isinstance(payload, dict):
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        if payload.get("type") != "file" or payload.get("encoding") != "base64":
            raise ProviderClientError("UNSUPPORTED_SOURCE_CONTENT")
        returned_path = payload.get("path")
        if returned_path != path:
            raise ProviderClientError("SOURCE_MISMATCH")
        size = payload.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or not 0 <= size <= max_bytes:
            raise ProviderClientError("SOURCE_FILE_TOO_LARGE")
        encoded = payload.get("content")
        if not isinstance(encoded, str):
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        try:
            content_bytes = base64.b64decode("".join(encoded.split()), validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from exc
        if len(content_bytes) != size or len(content_bytes) > max_bytes:
            raise ProviderClientError("SOURCE_FILE_TOO_LARGE")
        try:
            content = content_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ProviderClientError("UNSUPPORTED_SOURCE_CONTENT") from exc
        if "\x00" in content:
            raise ProviderClientError("UNSUPPORTED_SOURCE_CONTENT")
        try:
            return ProjectedGitHubFileResult(
                repository_ref=repository_ref,
                source_revision=source_revision,
                path=path,
                content=content,
                content_sha256=sha256(content_bytes).hexdigest(),
            )
        except (TypeError, ValueError) as exc:
            raise ProviderClientError("UNSUPPORTED_SOURCE_CONTENT") from exc


class ProjectedRepositoryBoundSourceProvider(RepositoryBoundSourceProvider):
    """Read the immutable repository revision after lineage-safe path projection."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._source_reads = self.github
        if isinstance(self.github, GitHubProviderActions) and isinstance(self.github.client, GitHubRestProviderClient):
            self._source_reads = GitHubProviderActions(
                self.github.executor.registry,
                ProjectedGitHubReadClient(self.github.client),
            )

    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        if identity != self.identity:
            raise SourceBootstrapError("repository source provider Project/run identity mismatch")
        repository = self.github.resolve_repository(
            self.binding,
            self._invocation(ACTION_REPOSITORY_RESOLVE),
        ).value
        revision = repository.head_revision
        tree = self.github.read_tree(
            self.binding,
            self._invocation(ACTION_SOURCE_TREE_READ),
            source_revision=revision,
        ).value
        files: dict[str, bytes] = {}
        read_index = 0
        for entry in sorted(tree.entries, key=lambda item: item.path):
            if entry.kind != "file" or is_lineage_secret_sensitive_path(entry.path):
                continue
            source = self._source_reads.read_file(
                self.binding,
                self._invocation(ACTION_SOURCE_FILE_READ, f":{read_index}"),
                source_revision=revision,
                path=entry.path,
            ).value
            read_index += 1
            raw = source.content.encode("utf-8")
            if sha256(raw).hexdigest() != source.content_sha256:
                raise SourceBootstrapError("repository file digest changed inside protected read boundary")
            files[source.path] = raw
        if not files:
            raise SourceBootstrapError("repository bootstrap returned no lineage-safe source files")
        return SourcePackage(
            source_kind="repository",
            source_ref=(
                f"{self.binding.repository_ref}@{revision}:projection:{_PROJECTION_VERSION}"
            ),
            files=files,
        )


class ProjectedRepositoryLineageBootstrap(RepositoryLineageBootstrap):
    """Initialize root lineage using the provider projection above.

    Existing durable heads remain authoritative and are never re-projected.
    The only behavioral change is for a missing root lineage, where files that
    durable lineage forbids are omitted before any source-file read occurs.
    """

    def ensure(self, run: EngineeringRun, *, operation_key: str) -> BootstrapResult:
        identity = self.identity_for_run(run)
        try:
            current = self.allocator.current_lineage(identity)
        except (LineageIdentityError, LineageNotFoundError):
            current = None
        except Exception as exc:
            raise SourceBootstrapError("durable source-lineage head could not be resolved") from exc
        if current is not None:
            if current.project_id != identity.project_id or current.run_id != identity.run_id:
                raise SourceBootstrapError("durable source lineage belongs to a different Project/run")
            return BootstrapResult(identity=identity, lineage=current, initialized=False)

        binding = self.projects.resolve(identity.project_id)
        if binding.project_ref != identity.project_id:
            raise ProjectRepositoryBindingError("repository binding belongs to a different Project")
        provider = ProjectedRepositoryBoundSourceProvider(
            identity=identity,
            binding=binding,
            github=self.github,
            invocations=self.invocations,
            operation_key=f"{operation_key}:bootstrap",
        )
        workspace: MaterializedWorkspace | None = None
        try:
            workspace = self.allocator.initialize(identity, provider)
            lineage = workspace.lineage
            if (
                lineage.project_id != identity.project_id
                or lineage.run_id != identity.run_id
                or lineage.parent_lineage_id is not None
                or lineage.source_kind != "repository"
                or lineage.source_ref_digest is None
            ):
                raise SourceBootstrapError("initialized repository lineage violates root-lineage contract")
            return BootstrapResult(identity=identity, lineage=lineage, initialized=True)
        except SourceBootstrapError:
            raise
        except Exception as exc:
            raise SourceBootstrapError("repository-backed durable lineage initialization failed") from exc
        finally:
            if workspace is not None:
                try:
                    self.allocator.cleanup(workspace)
                except Exception as exc:
                    raise SourceBootstrapError("failed to clean disposable bootstrap materialization") from exc


__all__ = [
    "ProjectedGitHubFileResult",
    "ProjectedGitHubReadClient",
    "ProjectedRepositoryBoundSourceProvider",
    "ProjectedRepositoryLineageBootstrap",
    "is_lineage_secret_sensitive_path",
]
