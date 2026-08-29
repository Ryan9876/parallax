from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import logging
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Protocol

from ..tools.providers import ProviderActionDenied, ProviderActionFailed
from .autonomy import (
    AutonomyCoordinator,
    AutonomyResult,
    AutonomyStopReason,
    AutonomousExecutor,
    LineageAwareAutonomousExecutor,
)
from .implementation_runtime import (
    ImplementationLineageReceipt,
    ImplementationWorkspaceHandle,
    ProtectedImplementationRuntime,
    RunProjectBinding,
    WorkspaceLineageError,
)
from .run_events import (
    RunEventAppend,
    RunEventOutcome,
    RunEventSubsystem,
    RunEventType,
)
from .service import EngineeringRunService
from .source_delivery_composition import (
    SourceDeliveryComposition,
    VerifiedDeliveryResult,
)
from .source_only_delivery import SourceOnlyDeliveryResult, SourceOnlyLineageDelivery
from .workspace_allocator import MaterializedWorkspace
from .workspace_lineage import ProjectRunIdentity, SourceLineage, SourceProvider


logger = logging.getLogger(__name__)


class DurableLineageAllocator(Protocol):
    """Narrow #60/#68 allocator contract consumed by runtime composition."""

    def initialize(
        self,
        identity: ProjectRunIdentity,
        provider: SourceProvider,
    ) -> MaterializedWorkspace: ...

    def current_lineage(self, identity: ProjectRunIdentity) -> SourceLineage: ...

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


def _source_delivery_failure_evidence(error: object) -> dict[str, str]:
    """Extract only normalized provider failure facts from a bounded cause chain."""

    if not isinstance(error, BaseException):
        return {"error_class": "UnknownDeliveryFailure"}

    current: BaseException | None = error
    seen: set[int] = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))

        if isinstance(current, ProviderActionFailed):
            result = {
                "error_class": "ProviderActionFailed",
                "provider": current.evidence.provider,
                "action": current.evidence.action,
            }
            result_code = current.audit.result_code or current.evidence.result_status
            if isinstance(result_code, str) and result_code:
                result["result_code"] = result_code
            return result

        if isinstance(current, ProviderActionDenied):
            result = {
                "error_class": "ProviderActionDenied",
                "provider": current.evidence.provider,
                "action": current.evidence.action,
            }
            deny_reason = current.audit.deny_reason
            result_code = deny_reason.value if deny_reason is not None else current.evidence.result_status
            if isinstance(result_code, str) and result_code:
                result["result_code"] = result_code
            return result

        next_error = current.__cause__ or current.__context__
        current = next_error if isinstance(next_error, BaseException) else None

    error_class = type(error).__name__
    if len(error_class) > 80 or not error_class.isidentifier():
        error_class = "DeliveryFailure"
    return {"error_class": error_class}


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
    def _verify_workspace_artifacts(
        workspace: MaterializedWorkspace, artifacts: tuple[dict[str, object], ...]
    ) -> None:
        root = workspace.path.resolve(strict=True)
        seen: set[str] = set()
        for artifact in artifacts:
            path = artifact.get("path")
            digest = artifact.get("sha256")
            size = artifact.get("size")
            if not isinstance(path, str) or not path or path in seen:
                raise WorkspaceLineageError("safe implementation artifact paths must be unique")
            seen.add(path)
            pure = PurePosixPath(path)
            if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
                raise WorkspaceLineageError("safe implementation artifact path is invalid")
            target = workspace.path.joinpath(*pure.parts)
            if target.is_symlink() or not target.is_file():
                raise WorkspaceLineageError("safe implementation artifact is unavailable")
            resolved = target.resolve(strict=True)
            if not resolved.is_relative_to(root):
                raise WorkspaceLineageError("safe implementation artifact escaped the workspace")
            content = target.read_bytes()
            if sha256(content).hexdigest() != digest or len(content) != size:
                raise WorkspaceLineageError("safe implementation artifact evidence does not match workspace bytes")

    @staticmethod
    def _verify_artifacts(lineage: SourceLineage, artifacts: tuple[dict[str, object], ...]) -> None:
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
        artifacts: tuple[dict[str, object], ...],
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
            self._verify_workspace_artifacts(workspace, artifacts)
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


def production_durable_lineage_allocator(
    engine: object,
    *,
    materialization_root: str | Path | None = None,
) -> DurableLineageAllocator | None:
    """Build #68's production-safe allocator when its adapters are serialized.

    Immutable contents live in private Vercel Blob and lineage/head metadata
    lives transactionally in the existing database. The local root below is
    disposable materialization only and never authoritative source-lineage state.
    """

    try:
        from sqlalchemy.orm import sessionmaker

        from .lineage_persistence import PostgresLineageMetadataStore, VercelPrivateBlobObjectStore
        from .workspace_allocator import ProjectWorkspaceAllocator
        from .workspace_lineage import SourceLineageStore
    except ImportError:
        return None

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    lineage_store = SourceLineageStore(
        VercelPrivateBlobObjectStore(),
        PostgresLineageMetadataStore(session_factory),
    )
    root = Path(
        materialization_root
        or os.getenv("PARALLAX_LINEAGE_MATERIALIZATION_ROOT")
        or (Path(tempfile.gettempdir()) / "parallax-lineage-materialization")
    )
    return ProjectWorkspaceAllocator(root, lineage_store=lineage_store)


class EngineeringRuntimeComposition:
    """Concrete per-request production composition for protected autonomy."""

    def __init__(
        self,
        service: EngineeringRunService,
        allocator: DurableLineageAllocator,
        legacy_executor: AutonomousExecutor,
        *,
        lineage_executor: LineageAwareAutonomousExecutor | None = None,
        source_delivery: SourceDeliveryComposition | None = None,
    ) -> None:
        self.service = service
        self.allocator = allocator
        self.source_delivery = source_delivery
        self.last_delivery_result: VerifiedDeliveryResult | SourceOnlyDeliveryResult | None = None
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

    @staticmethod
    def _event_time(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _emit_delivery_success(
        self,
        result: VerifiedDeliveryResult | SourceOnlyDeliveryResult,
        run: object,
    ) -> None:
        if getattr(self.service, "event_sink", None) is None:
            return
        project_id = getattr(run, "project_id", None)
        run_id = getattr(run, "id", None)
        updated_at = getattr(run, "updated_at", None)
        if not isinstance(project_id, str) or not isinstance(run_id, str) or not isinstance(updated_at, datetime):
            raise RuntimeCompositionError("verified delivery cannot be projected without canonical run identity")

        if isinstance(result, SourceOnlyDeliveryResult):
            event = RunEventAppend(
                project_id=project_id,
                run_id=run_id,
                event_key=f"handoff:{result.lineage_id.removeprefix('src:')}",
                event_type=RunEventType.SOURCE_DELIVERY,
                stage="REVIEW",
                outcome=RunEventOutcome.SUCCEEDED,
                subsystem=RunEventSubsystem.SOURCE_LINEAGE,
                source_lineage_ref=result.lineage_id,
                evidence_ref=result.handoff_id,
                summary="Verified accepted source lineage is ready for authenticated download or external deployment.",
                metadata={
                    "content_digest": result.content_digest,
                    "delivery_action_count": 0,
                },
                occurred_at=self._event_time(updated_at),
            )
        else:
            event = RunEventAppend(
                project_id=project_id,
                run_id=run_id,
                event_key=f"delivery:{result.lineage_id}",
                event_type=RunEventType.SOURCE_DELIVERY,
                stage="REVIEW",
                outcome=RunEventOutcome.SUCCEEDED,
                subsystem=RunEventSubsystem.VERCEL,
                source_lineage_ref=result.lineage_id,
                evidence_ref=f"delivery:{result.preview_deployment_id}",
                summary="Verified accepted source lineage was published to GitHub and a bounded Vercel Preview.",
                metadata={
                    "content_digest": result.content_digest,
                    "branch_name": result.branch_name,
                    "commit_revision": result.commit_revision,
                    "pull_request_number": result.pull_request_number,
                    "preview_deployment_id": result.preview_deployment_id,
                    "preview_status": result.preview_status,
                    "delivery_action_count": len(result.actions),
                },
                occurred_at=self._event_time(updated_at),
            )
        self.service.emit_event(event)

    def _source_only_delivery(self) -> bool:
        return bool(
            self.source_delivery is not None
            and isinstance(self.source_delivery.delivery, SourceOnlyLineageDelivery)
        )

    def _emit_delivery_failure(self, run: object, error: object) -> None:
        if getattr(self.service, "event_sink", None) is None:
            return
        project_id = getattr(run, "project_id", None)
        run_id = getattr(run, "id", None)
        revision = getattr(run, "revision", None)
        updated_at = getattr(run, "updated_at", None)
        if (
            not isinstance(project_id, str)
            or not isinstance(run_id, str)
            or not isinstance(revision, int)
            or not isinstance(updated_at, datetime)
        ):
            return
        failure_evidence = _source_delivery_failure_evidence(error)
        metadata: dict[str, object] = {"run_revision": revision, "current_state": "REVIEW"}
        metadata.update(failure_evidence)
        source_only = self._source_only_delivery()
        self.service.emit_event(
            RunEventAppend(
                project_id=project_id,
                run_id=run_id,
                event_key=f"delivery-failure:{run_id}:{revision}",
                event_type=RunEventType.SOURCE_DELIVERY,
                stage="REVIEW",
                outcome=RunEventOutcome.FAILED,
                subsystem=(RunEventSubsystem.SOURCE_LINEAGE if source_only else RunEventSubsystem.VERCEL),
                failure_code="SOURCE_DELIVERY_FAILED",
                summary=(
                    "Verified source handoff failed before accepted lineage was made downloadable."
                    if source_only
                    else "Verified source delivery failed before operator review publication completed."
                ),
                metadata=metadata,
                occurred_at=self._event_time(updated_at),
            )
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
        self.last_delivery_result = None
        try:
            if self.source_delivery is not None:
                run = self.service.get(run_id)
                try:
                    self.source_delivery.bootstrap.ensure(run, operation_key=operation_key)
                except Exception as exc:
                    raise RuntimeCompositionError("repository-backed source bootstrap failed") from exc

            result = self.coordinator.run(
                run_id=run_id,
                operation_key=operation_key,
                expected_revision=expected_revision,
            )
            if self.source_delivery is not None and result.stop_reason is AutonomyStopReason.REVIEW_REQUIRED:
                try:
                    delivery_result = self.source_delivery.delivery.deliver(
                        result.run,
                        operation_key=operation_key,
                    )
                except Exception as exc:
                    self.last_delivery_result = None
                    logger.error(
                        "source_delivery_failed error_class=%s reason=%s",
                        type(exc).__name__,
                        str(exc)[:240],
                    )
                    try:
                        self._emit_delivery_failure(result.run, exc)
                    except Exception:
                        pass
                    raise RuntimeCompositionError("verified source delivery failed before operator review") from exc
                self.last_delivery_result = delivery_result
                try:
                    self._emit_delivery_success(delivery_result, result.run)
                except Exception as exc:
                    raise RuntimeCompositionError(
                        "durable run-event projection failed after verified source delivery"
                    ) from exc
                refreshed_run = self.service.get(run_id)
                if refreshed_run.state != result.run.state or refreshed_run.revision != result.run.revision:
                    raise RuntimeCompositionError("verified source delivery changed protected run state")
                result = AutonomyResult(
                    run=refreshed_run,
                    stop_reason=result.stop_reason,
                    steps=result.steps,
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
    "production_durable_lineage_allocator",
]
