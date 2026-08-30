from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from uuid import uuid4

from .workspace_lineage import (
    LineageIdentityError,
    ProjectRunIdentity,
    SourceLineage,
    SourceLineageStore,
    SourceProvider,
    SourcePolicyError,
    StaleLineageError,
)


class WorkspaceLeaseError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MaterializedWorkspace:
    identity: ProjectRunIdentity
    lineage: SourceLineage
    lease_id: str
    path: Path

    def evidence(self) -> dict[str, str | int | None]:
        return {
            **self.lineage.evidence(),
            "lease_id": self.lease_id,
        }


class ProjectWorkspaceAllocator:
    """Server-owned allocator for disposable exact-lineage materialization.

    Durable source contents and current-lineage metadata are owned by the
    explicitly injected SourceLineageStore. `protected_root` is only a local
    materialization lease root and is never authoritative durable state.
    """

    def __init__(
        self,
        protected_root: str | Path,
        *,
        lineage_store: SourceLineageStore,
    ) -> None:
        if not isinstance(lineage_store, SourceLineageStore):
            raise TypeError("an explicit durable SourceLineageStore is required")
        root = Path(protected_root)
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink():
            raise SourcePolicyError("protected workspace allocator root cannot be a symlink")
        self.protected_root = root.resolve(strict=True)
        self.live_root = self.protected_root / "live"
        self.live_root.mkdir(exist_ok=True)
        if self.live_root.is_symlink() or not self.live_root.is_dir():
            raise SourcePolicyError("protected live-workspace root is invalid")
        self.lineage_store = lineage_store

    def initialize(self, identity: ProjectRunIdentity, provider: SourceProvider) -> MaterializedWorkspace:
        lineage = self.lineage_store.initialize(identity, provider)
        return self._materialize(identity, lineage)

    def initialize_greenfield(self, identity: ProjectRunIdentity, *, source_ref: str) -> MaterializedWorkspace:
        initializer = getattr(self.lineage_store, "initialize_greenfield", None)
        if not callable(initializer):
            raise SourcePolicyError("durable lineage store does not admit greenfield roots")
        lineage = initializer(identity, source_ref=source_ref)
        if not isinstance(lineage, SourceLineage) or lineage.source_kind != "greenfield":
            raise SourcePolicyError("greenfield lineage initialization returned an invalid root")
        return self._materialize(identity, lineage)

    def resolve(self, identity: ProjectRunIdentity, lineage_id: str | None = None) -> MaterializedWorkspace:
        lineage = (
            self.lineage_store.current(identity)
            if lineage_id is None
            else self.lineage_store.resolve(identity, lineage_id)
        )
        if lineage is None:  # defensive for type narrowing
            raise LineageIdentityError("Project/run source lineage is not initialized")
        return self._materialize(identity, lineage)

    def accept_implementation(
        self,
        workspace: MaterializedWorkspace,
        *,
        expected_parent_lineage_id: str,
    ) -> SourceLineage:
        self._validate_lease(workspace)
        if workspace.lineage.lineage_id != expected_parent_lineage_id:
            raise StaleLineageError("workspace lease does not represent the expected parent lineage")
        return self.lineage_store.capture_implementation(
            workspace.identity,
            workspace.path,
            expected_parent_lineage_id=expected_parent_lineage_id,
        )

    def reconstruct(self, identity: ProjectRunIdentity, lineage_id: str) -> MaterializedWorkspace:
        lineage = self.lineage_store.resolve(identity, lineage_id)
        return self._materialize(identity, lineage)

    def cleanup(self, workspace: MaterializedWorkspace) -> None:
        self._validate_lease(workspace, require_exists=False)
        if workspace.path.exists():
            shutil.rmtree(workspace.path)
        run_live_root = workspace.path.parent
        if run_live_root.exists() and run_live_root.is_dir() and not any(run_live_root.iterdir()):
            run_live_root.rmdir()

    def current_lineage(self, identity: ProjectRunIdentity) -> SourceLineage:
        lineage = self.lineage_store.current(identity)
        if lineage is None:  # defensive for type narrowing
            raise LineageIdentityError("Project/run source lineage is not initialized")
        return lineage

    def _materialize(self, identity: ProjectRunIdentity, lineage: SourceLineage) -> MaterializedWorkspace:
        if lineage.project_id != identity.project_id or lineage.run_id != identity.run_id:
            raise WorkspaceLeaseError("lineage identity does not match requested Project/run")
        run_root = self.live_root / identity.storage_key
        run_root.mkdir(exist_ok=True)
        if run_root.is_symlink() or not run_root.is_dir():
            raise WorkspaceLeaseError("Project/run live-workspace directory is invalid")
        lease_id = uuid4().hex
        target = run_root / lease_id
        self.lineage_store.materialize(identity, lineage.lineage_id, target)
        return MaterializedWorkspace(identity=identity, lineage=lineage, lease_id=lease_id, path=target)

    def _validate_lease(self, workspace: MaterializedWorkspace, *, require_exists: bool = True) -> Path:
        if not isinstance(workspace, MaterializedWorkspace):
            raise WorkspaceLeaseError("protected workspace lease is required")
        if len(workspace.lease_id) != 32 or any(character not in "0123456789abcdef" for character in workspace.lease_id):
            raise WorkspaceLeaseError("workspace lease identity is invalid")
        expected_parent = self.live_root / workspace.identity.storage_key
        expected_path = expected_parent / workspace.lease_id
        try:
            resolved_parent = expected_parent.resolve(strict=True)
        except OSError as exc:
            if not require_exists and not expected_parent.exists():
                return expected_path
            raise WorkspaceLeaseError("workspace lease parent does not exist") from exc
        if resolved_parent.is_symlink() or not resolved_parent.is_dir():
            raise WorkspaceLeaseError("workspace lease parent is invalid")
        if workspace.path != expected_path:
            raise WorkspaceLeaseError("workspace lease path is not server-owned")
        if require_exists:
            try:
                resolved = workspace.path.resolve(strict=True)
            except OSError as exc:
                raise WorkspaceLeaseError("workspace lease no longer exists") from exc
            if workspace.path.is_symlink() or not resolved.is_dir() or not resolved.is_relative_to(self.live_root):
                raise WorkspaceLeaseError("workspace lease escaped the protected allocator root")
        return expected_path


__all__ = [
    "MaterializedWorkspace",
    "ProjectWorkspaceAllocator",
    "WorkspaceLeaseError",
]
