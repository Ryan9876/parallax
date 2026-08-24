from __future__ import annotations

from hashlib import sha256
from pathlib import PurePosixPath

from ..models import EngineeringRun
from ..tools.providers import (
    ACTION_REPOSITORY_RESOLVE,
    ACTION_SOURCE_FILE_READ,
    ACTION_SOURCE_TREE_READ,
)
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


_PROJECTION_VERSION = "lineage-safe-v1"
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


class ProjectedRepositoryBoundSourceProvider(RepositoryBoundSourceProvider):
    """Read the immutable repository revision after lineage-safe path projection."""

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
            source = self.github.read_file(
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
    "ProjectedRepositoryBoundSourceProvider",
    "ProjectedRepositoryLineageBootstrap",
    "is_lineage_secret_sensitive_path",
]
