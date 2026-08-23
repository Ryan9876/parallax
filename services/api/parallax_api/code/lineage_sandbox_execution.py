from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import time

from .execution import ExecutionPolicyError, ExecutionSpec, ProtectedCommandPolicy
from .runtime_composition import DurableLineageAllocator
from .sandbox_execution import (
    ProtectedCommandRegistry,
    VercelSandboxUnavailable,
    _bounded_evidence,
    _sanitized_provider_error,
)
from .workspace_allocator import MaterializedWorkspace
from .workspace_lineage import ProjectRunIdentity, SourceLineage


class SameLineageExecutionError(RuntimeError):
    pass


class SameLineageVercelSandboxExecutor:
    """Execute protected stages only against one reconstructed accepted lineage."""

    def __init__(
        self,
        allocator: DurableLineageAllocator,
        *,
        registry: ProtectedCommandRegistry | None = None,
        policy: ProtectedCommandPolicy | None = None,
        project_id: str | None = None,
    ) -> None:
        self.allocator = allocator
        self.registry = registry or ProtectedCommandRegistry()
        self.policy = policy or ProtectedCommandPolicy()
        self.project_id = project_id or os.getenv("VERCEL_PROJECT_ID")

    @staticmethod
    def _sdk():
        try:
            from vercel.api import session
            from vercel.sandbox import NetworkPolicy
            from vercel.sandbox import sync as sandbox
        except ImportError as exc:
            raise VercelSandboxUnavailable("Vercel Sandbox SDK is not installed") from exc
        return session, NetworkPolicy, sandbox

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
        directories = sorted(
            {
                PurePosixPath(path).parent.as_posix()
                for path, _ in files
                if PurePosixPath(path).parent.as_posix() not in {"", "."}
            },
            key=lambda value: (value.count("/"), value),
        )
        for directory in directories:
            filesystem.mkdir(directory, cwd="/vercel/sandbox", recursive=True)
        for path, content in files:
            filesystem.write_bytes(path, content, cwd="/vercel/sandbox")

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
        cleanup_error: Exception | None = None
        try:
            self.policy.validate(spec)
            registered = self.registry.spec_for(spec.stage, operation_key=spec.operation_key)
            if spec != registered:
                raise ExecutionPolicyError("execution spec does not match the protected command registry")
            command, args = self.registry.invocation_for(spec.stage)
            identity = self._identity(project_ref, run_id)
            if not isinstance(source_lineage_ref, str) or not source_lineage_ref:
                raise SameLineageExecutionError("accepted source lineage identity is required")

            workspace = self.allocator.reconstruct(identity, source_lineage_ref)
            lineage, files = self._validate_workspace(
                workspace,
                identity=identity,
                lineage_id=source_lineage_ref,
            )

            self._require_provider_identity()
            session, NetworkPolicy, sandbox = self._sdk()
            with session():
                with sandbox.create_sandbox(
                    project_id=self.project_id,
                    execution_time_limit=spec.timeout_seconds + 30,
                    persistent=False,
                    network_policy=NetworkPolicy.deny_all(),
                    env={},
                    destroy=True,
                    tags={"parallax": "same-lineage", "stage": spec.stage.value.lower()},
                ) as instance:
                    self._transfer_source(instance, files)
                    result = instance.run_process(
                        command,
                        list(args),
                        cwd=spec.working_directory,
                        env={},
                        kill_after=spec.timeout_seconds,
                        capture_output=True,
                    )

            evidence = _bounded_evidence(
                spec,
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
                }
            )
        except Exception as exc:
            evidence = _bounded_evidence(
                spec,
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
