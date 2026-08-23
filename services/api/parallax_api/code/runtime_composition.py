from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .autonomy import AutonomyCoordinator, AutonomyResult, AutonomousExecutor, LineageAwareAutonomousExecutor
from .implementation_runtime import (
    ImplementationLineageReceipt,
    ImplementationWorkspaceHandle,
    ProtectedImplementationRuntime,
    RunProjectBinding,
    WorkspaceLineageError,
)
from .service import EngineeringRunService
from .workspace_allocator import MaterializedWorkspace
from .workspace_lineage import ProjectRunIdentity, SourceLineage


class DurableLineageAllocator(Protocol):
    """Narrow #60/#68 allocator contract consumed by runtime composition."""

    def resolve(
        self,
        identity: ProjectRunIdentity,
        lineage_id: str | None = None,
    ) -> MaterializedWorkspace: ...

    def accept_implementation(
        self,
        workspace: MaterializedWorkspace,
        *,
        expected_parent_lineage_id: str,
    ) -> SourceLineage: ...

    def reconstruct(
        self,
        identity: ProjectRunIdentity,
        lineage_id: str,
    ) -> MaterializedWorkspace: ...

    def cleanup(self, workspace: MaterializedWorkspace) -> None: ...


class RuntimeCompositionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _LeaseKey:
    project_ref: str
    run_id: str
    source_lineage_ref: str
    workspace_root: Path


class AllocatorWorkspaceLineageGateway:
    """Adapt the durable allocator contract to #61's implementation gateway.

    The in-memory lease map is intentionally disposable request coordination,
    not durable lineage authority. Durable identity lives behind the allocator.
    """

    def __init__(self, allocator: DurableLineageAllocator) -> None:
        self.allocator = allocator
        self._leases: dict[_LeaseKey, MaterializedWorkspace] = {}

    @staticmethod
    def _identity(project_ref: str, run_id: str) -> ProjectRunIdentity:
        try:
            return ProjectRunIdentity(project_id=project_ref, run_id=run_id)
        except (TypeError, ValueError, RuntimeError) as exc:
            raise WorkspaceLineageError("canonical Project/run identity is invalid") from exc

    @staticmethod
    def _validate_workspace(
        workspace: MaterializedWorkspace,
        *,
        identity: ProjectRunIdentity,
        lineage_id: str | None = None,
    ) -> None:
        if workspace.identity != identity:
            raise WorkspaceLineageError("materialized workspace Project/run identity mismatch")
        lineage = workspace.lineage
        if lineage.project_id != identity.project_id or lineage.run_id != identity.run_id:
            raise WorkspaceLineageError("materialized lineage Project/run identity mismatch")
        if lineage_id is not None and lineage.lineage_id != lineage_id:
            raise WorkspaceLineageError("materialized workspace lineage mismatch")
        if not workspace.path.is_absolute():
            raise WorkspaceLineageError("materialized workspace root must be server-owned absolute path")

    @staticmethod
    def _key(handle: ImplementationWorkspaceHandle) -> _LeaseKey:
        return _LeaseKey(
            project_ref=handle.project_ref,
            run_id=handle.run_id,
            source_lineage_ref=handle.source_lineage_ref,
            workspace_root=handle.workspace_root,
        )

    def resolve_for_implementation(
        self,
        *,
        project_ref: str,
        run_id: str,
    ) -> ImplementationWorkspaceHandle:
        identity = self._identity(project_ref, run_id)
        try:
            workspace = self.allocator.resolve(identity)
            self._validate_workspace(workspace, identity=identity)
        except WorkspaceLineageError:
            raise
        except Exception as exc:
            raise WorkspaceLineageError("durable source lineage could not be materialized") from exc

        handle = ImplementationWorkspaceHandle(
            project_ref=identity.project_id,
            run_id=identity.run_id,
            source_lineage_ref=workspace.lineage.lineage_id,
            base_revision=workspace.lineage.content_digest,
            workspace_root=workspace.path,
        )
        key = self._key(handle)
        if key in self._leases:
            try:
                self.allocator.cleanup(workspace)
            except Exception:
                pass
            raise WorkspaceLineageError("duplicate implementation workspace lease")
        self._leases[key] = workspace
        return handle

    @staticmethod
    def _verify_artifacts(lineage: SourceLineage, artifacts: list[dict[str, object]]) -> None:
        manifest = {item.path: item for item in lineage.files}
        if not artifacts:
            raise WorkspaceLineageError("safe implementation artifacts are required for lineage acceptance")
        seen: set[str] = set()
        for artifact in artifacts:
            path = artifact.get("path")
            digest = artifact.get("sha256")
            size = artifact.get("size")
            if not isinstance(path, str) or not path or path in seen:
                raise WorkspaceLineageError("safe implementation artifact paths must be unique")
            seen.add(path)
            entry = manifest.get(path)
            if entry is None or entry.sha256 != digest or entry.size != size:
                raise WorkspaceLineageError("accepted lineage does not contain the exact safe mutation artifact")

    def accept_implementation(
        self,
        *,
        handle: ImplementationWorkspaceHandle,
        workspace_digest: str,
        artifacts: list[dict[str, object]],
    ) -> ImplementationLineageReceipt:
        key = self._key(handle)
        workspace = self._leases.pop(key, None)
        if workspace is None:
            raise WorkspaceLineageError("implementation workspace lease is unknown or already consumed")

        identity = self._identity(handle.project_ref, handle.run_id)
        try:
            self._validate_workspace(
                workspace,
                identity=identity,
                lineage_id=handle.source_lineage_ref,
            )
            accepted = self.allocator.accept_implementation(
                workspace,
                expected_parent_lineage_id=handle.source_lineage_ref,
            )
            if accepted.project_id != identity.project_id or accepted.run_id != identity.run_id:
                raise WorkspaceLineageError("accepted lineage Project/run identity mismatch")
            if accepted.parent_lineage_id != handle.source_lineage_ref:
                raise WorkspaceLineageError("accepted lineage parent does not match implementation base")
            if accepted.lineage_id == handle.source_lineage_ref:
                raise WorkspaceLineageError("implementation did not advance source lineage")
            self._verify_artifacts(accepted, artifacts)
            return ImplementationLineageReceipt(
                project_ref=identity.project_id,
                run_id=identity.run_id,
                base_source_lineage_ref=handle.source_lineage_ref,
                source_lineage_ref=accepted.lineage_id,
                workspace_digest=workspace_digest,
            )
        except WorkspaceLineageError:
            raise
        except Exception as exc:
            raise WorkspaceLineageError("durable source lineage acceptance failed") from exc
        finally:
            try:
                self.allocator.cleanup(workspace)
            except Exception as exc:
                raise WorkspaceLineageError(
                    "failed to clean disposable implementation workspace after lineage acceptance"
                ) from exc

    def cleanup_pending(self) -> None:
        pending = list(self._leases.values())
        self._leases.clear()
        failures: list[str] = []
        for workspace in pending:
            try:
                self.allocator.cleanup(workspace)
            except Exception as exc:
                failures.append(type(exc).__name__)
        if failures:
            raise RuntimeCompositionError(
                "failed to clean one or more disposable implementation leases: " + ",".join(failures)
            )


class EngineeringRuntimeComposition:
    """Concrete per-request production composition for protected autonomy."""

    def __init__(
        self,
        service: EngineeringRunService,
        allocator: DurableLineageAllocator,
        legacy_executor: AutonomousExecutor,
        *,
        lineage_executor: LineageAwareAutonomousExecutor | None = None,
    ) -> None:
        self.service = service
        self.allocator = allocator
        self.gateway = AllocatorWorkspaceLineageGateway(allocator)
        self.implementation_runtime = ProtectedImplementationRuntime(
            service,
            RunProjectBinding(),
            self.gateway,
        )
        if lineage_executor is None:
            from .lineage_sandbox_execution import SameLineageVercelSandboxExecutor

            lineage_executor = SameLineageVercelSandboxExecutor(allocator)
        self.coordinator = AutonomyCoordinator(
            service,
            legacy_executor,
            implementation_runtime=self.implementation_runtime,
            lineage_executor=lineage_executor,
        )

    def run(
        self,
        *,
        run_id: str,
        operation_key: str,
        expected_revision: int,
    ) -> AutonomyResult:
        result: AutonomyResult | None = None
        primary_error: BaseException | None = None
        try:
            result = self.coordinator.run(
                run_id=run_id,
                operation_key=operation_key,
                expected_revision=expected_revision,
            )
            return result
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            try:
                self.gateway.cleanup_pending()
            except RuntimeCompositionError:
                if primary_error is None and result is not None:
                    raise


__all__ = [
    "AllocatorWorkspaceLineageGateway",
    "DurableLineageAllocator",
    "EngineeringRuntimeComposition",
    "RuntimeCompositionError",
]
