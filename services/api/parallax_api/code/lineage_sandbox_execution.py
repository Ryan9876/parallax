from __future__ import annotations

from hashlib import sha256
import os
from pathlib import PurePosixPath
import time

from parallax_api.execution_environment import execution_snapshot_id

from .execution import ExecutionPolicyError, ExecutionSpec, ProtectedCommandPolicy
from .runtime_composition import DurableLineageAllocator
from .sandbox_execution import (
    ProtectedCommandRegistry,
    VercelSandboxUnavailable,
    _bounded_evidence,
    _sanitized_provider_error,
)
from .validation_toolchains import select_validation_profile
from .workspace_allocator import MaterializedWorkspace
from .workspace_lineage import ProjectRunIdentity, SourceLineage


_SANDBOX_SOURCE_ROOT = "/vercel/sandbox"


class SameLineageExecutionError(RuntimeError):
    pass


class SameLineageVercelSandboxExecutor:
    """Execute protected stages only against one reconstructed accepted lineage.

    Runtime dependencies come from one server-pinned, source-free Vercel Sandbox
    snapshot. The accepted lineage is transferred after the snapshot is restored,
    and execution remains deny-all network with no application environment.
    """

    def __init__(
        self,
        allocator: DurableLineageAllocator,
        *,
        registry: ProtectedCommandRegistry | None = None,
        policy: ProtectedCommandPolicy | None = None,
        project_id: str | None = None,
        snapshot_id: str | None = None,
    ) -> None:
        self.allocator = allocator
        self.registry = registry or ProtectedCommandRegistry()
        self.policy = policy or ProtectedCommandPolicy()
        self.project_id = project_id or os.getenv("VERCEL_PROJECT_ID")
        try:
            self.snapshot_id = execution_snapshot_id(snapshot_id)
        except ValueError as exc:
            raise SameLineageExecutionError("server-owned execution snapshot identity is invalid") from exc

    @staticmethod
    def _sdk():
        try:
            from vercel.api import session
            from vercel.sandbox import NetworkPolicy, SnapshotSource
            from vercel.sandbox import sync as sandbox
        except ImportError as exc:
            raise VercelSandboxUnavailable("Vercel Sandbox SDK is not installed") from exc
        return session, NetworkPolicy, SnapshotSource, sandbox

    def _require_provider_identity(self) -> None:
        if not self.project_id:
            raise VercelSandboxUnavailable("Vercel project identity is unavailable")

    @staticmethod
    def _identity(project_ref: str, run_id: str) -> ProjectRunIdentity:
        try:
            return ProjectRunIdentity(project_id=project_ref, run_id=run_id)
        except (TypeError, ValueError, RuntimeError) as exc:
            raise SameLineageExecutionError("canonical Project/run identity is invalid") from exc

    @staticmethod
    def _sandbox_cwd(working_directory: str) -> str:
        pure = PurePosixPath(working_directory)
        if pure.is_absolute() or any(part == ".." for part in pure.parts):
            raise SameLineageExecutionError("protected working directory escaped the sandbox source root")
        if working_directory in {"", "."}:
            return _SANDBOX_SOURCE_ROOT
        clean = pure.as_posix()
        if clean.startswith("./"):
            clean = clean[2:]
        if not clean or clean == ".":
            return _SANDBOX_SOURCE_ROOT
        return f"{_SANDBOX_SOURCE_ROOT}/{clean}"

    @staticmethod
    def _validate_workspace(
        workspace: MaterializedWorkspace,
        *,
        identity: ProjectRunIdentity,
        lineage_id: str,
    ) -> tuple[SourceLineage, tuple[tuple[str, bytes], ...]]:
        if workspace.identity != identity:
            raise SameLineageExecutionError("reconstructed workspace Project/run identity mismatch")
        lineage = workspace.lineage
        if lineage.project_id != identity.project_id or lineage.run_id != identity.run_id:
            raise SameLineageExecutionError("reconstructed lineage Project/run identity mismatch")
        if lineage.lineage_id != lineage_id:
            raise SameLineageExecutionError("reconstructed lineage identity mismatch")

        root = workspace.path
        if not root.is_absolute() or root.is_symlink() or not root.is_dir():
            raise SameLineageExecutionError("reconstructed workspace root is invalid")
        resolved_root = root.resolve(strict=True)

        actual_paths: set[str] = set()
        for candidate in root.rglob("*"):
            if candidate.is_symlink():
                raise SameLineageExecutionError("reconstructed source contains a symlink")
            if candidate.is_file():
                resolved = candidate.resolve(strict=True)
                if not resolved.is_relative_to(resolved_root):
                    raise SameLineageExecutionError("reconstructed source escaped its lease")
                actual_paths.add(candidate.relative_to(root).as_posix())
            elif candidate.exists() and not candidate.is_dir():
                raise SameLineageExecutionError("reconstructed source contains a special file")

        manifest_paths = {item.path for item in lineage.files}
        if actual_paths != manifest_paths:
            raise SameLineageExecutionError("reconstructed source file set does not match accepted lineage")

        files: list[tuple[str, bytes]] = []
        total = 0
        for entry in lineage.files:
            pure = PurePosixPath(entry.path)
            if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
                raise SameLineageExecutionError("accepted lineage contains an invalid source path")
            target = root.joinpath(*pure.parts)
            if target.is_symlink() or not target.is_file():
                raise SameLineageExecutionError("accepted lineage source file is unavailable")
            content = target.read_bytes()
            if len(content) != entry.size or sha256(content).hexdigest() != entry.sha256:
                raise SameLineageExecutionError("reconstructed source bytes do not match accepted lineage")
            files.append((entry.path, content))
            total += len(content)
        if total != lineage.total_bytes or len(files) != lineage.file_count:
            raise SameLineageExecutionError("reconstructed source aggregate evidence does not match lineage")
        return lineage, tuple(files)

    @staticmethod
    def _transfer_source(instance: object, files: tuple[tuple[str, bytes], ...]) -> None:
        filesystem = getattr(instance, "fs", None)
        if filesystem is None:
            raise SameLineageExecutionError("sandbox filesystem API is unavailable")
        filesystem.mkdir("sandbox", cwd="/vercel", recursive=True)
        with filesystem.batch(cwd=_SANDBOX_SOURCE_ROOT) as batch:
            for path, content in files:
                batch.write_bytes(path, content)

    def _validate_caller_stage_spec(self, spec: ExecutionSpec) -> None:
        """Reject caller-shaped command drift before any lineage materialization.

        The caller may identify only the protected stage/operation. Repository
        profile selection happens later from exact reconstructed source; it does
        not make arbitrary incoming command arguments authoritative.
        """

        self.policy.validate(spec)
        expected = self.registry.spec_for(spec.stage, operation_key=spec.operation_key)
        if spec != expected:
            raise ExecutionPolicyError("protected execution spec is not the registered stage authority")

    def execute_on_lineage(
        self,
        spec: ExecutionSpec,
        *,
        project_ref: str,
        run_id: str,
        source_lineage_ref: str,
    ) -> dict[str, object]:
        started = time.monotonic()
        workspace: MaterializedWorkspace | None = None
        evidence: dict[str, object] | None = None
        execution_spec = spec
        validation_profile_id: str | None = None
        validation_profile_digest: str | None = None
        cleanup_error: Exception | None = None
        try:
            self._validate_caller_stage_spec(spec)
            identity = self._identity(project_ref, run_id)
            if not isinstance(source_lineage_ref, str) or not source_lineage_ref:
                raise SameLineageExecutionError("accepted source lineage identity is required")

            workspace = self.allocator.reconstruct(identity, source_lineage_ref)
            lineage, files = self._validate_workspace(
                workspace,
                identity=identity,
                lineage_id=source_lineage_ref,
            )
            profile = select_validation_profile(workspace.path)
            validation_profile_id = profile.profile_id.value
            validation_profile_digest = profile.digest
            execution_spec = profile.spec_for(spec.stage, operation_key=spec.operation_key)
            self.policy.validate(execution_spec)
            command, args = profile.invocation_for(spec.stage)

            self._require_provider_identity()
            session, NetworkPolicy, SnapshotSource, sandbox = self._sdk()
            snapshot_source = SnapshotSource(snapshot_id=self.snapshot_id)
            with session():
                with sandbox.create_sandbox(
                    project_id=self.project_id,
                    source=snapshot_source,
                    execution_time_limit=execution_spec.timeout_seconds + 30,
                    persistent=False,
                    network_policy=NetworkPolicy.deny_all(),
                    env={},
                    destroy=True,
                    tags={"parallax": "same-lineage", "stage": spec.stage.value.lower()},
                ) as instance:
                    restored_snapshot_id = getattr(instance, "current_snapshot_id", None)
                    if restored_snapshot_id != self.snapshot_id:
                        raise SameLineageExecutionError("sandbox did not restore the server-pinned execution snapshot")
                    self._transfer_source(instance, files)
                    result = instance.run_process(
                        command,
                        list(args),
                        cwd=self._sandbox_cwd(execution_spec.working_directory),
                        env={},
                        kill_after=execution_spec.timeout_seconds,
                        capture_output=True,
                    )

            evidence = _bounded_evidence(
                execution_spec,
                exit_code=result.returncode,
                duration_ms=int((time.monotonic() - started) * 1_000),
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )
            evidence.update(
                {
                    "lineage_source_transfer": True,
                    "source_content_digest": lineage.content_digest,
                    "source_file_count": lineage.file_count,
                    "source_total_bytes": lineage.total_bytes,
                    "fresh_repository_checkout": False,
                    "git_source": False,
                    "execution_snapshot_id": self.snapshot_id,
                    "execution_snapshot_verified": True,
                    "validation_profile_id": validation_profile_id,
                    "validation_profile_digest": validation_profile_digest,
                    "execution_working_directory": self._sandbox_cwd(execution_spec.working_directory),
                }
            )
        except Exception as exc:
            evidence = _bounded_evidence(
                execution_spec,
                exit_code=None,
                duration_ms=int((time.monotonic() - started) * 1_000),
                stdout="",
                stderr=_sanitized_provider_error(exc),
                timed_out="timeout" in type(exc).__name__.lower(),
            )
            evidence.update(
                {
                    "lineage_source_transfer": False,
                    "fresh_repository_checkout": False,
                    "git_source": False,
                    "execution_snapshot_id": self.snapshot_id,
                    "execution_snapshot_verified": False,
                    "validation_profile_id": validation_profile_id,
                    "validation_profile_digest": validation_profile_digest,
                }
            )
        finally:
            if workspace is not None:
                try:
                    self.allocator.cleanup(workspace)
                except Exception as exc:
                    cleanup_error = exc

        assert evidence is not None
        if cleanup_error is not None:
            cleanup_message = _sanitized_provider_error(cleanup_error)
            existing = str(evidence.get("stderr_excerpt") or "")
            combined = (existing + ("; " if existing else "") + cleanup_message)[:2_000]
            evidence["stderr_excerpt"] = combined
            evidence["stderr_digest"] = sha256(combined.encode()).hexdigest()
            evidence["protected_success"] = False
            evidence["lineage_cleanup_failed"] = True
        else:
            evidence["lineage_cleanup_failed"] = False
        return evidence


__all__ = ["SameLineageExecutionError", "SameLineageVercelSandboxExecutor"]
