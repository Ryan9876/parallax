from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
import time
from typing import Protocol

from .domain import WorkflowStage
from .execution import ExecutionPolicyError, ExecutionSpec, ProtectedCommandPolicy


class BoundedExecutor(Protocol):
    def execute(self, spec: ExecutionSpec) -> dict[str, object]: ...

    def probe(self, *, operation_key: str) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class RegisteredCommand:
    stage: WorkflowStage
    tool_id: str
    command: str
    args: tuple[str, ...]
    working_directory: str = "."
    timeout_seconds: int = 180


class ProtectedCommandRegistry:
    """Server-owned repository command registry.

    API callers and model output never supply executable command text. Expanding
    this registry is therefore a code/release decision, not a runtime decision.
    """

    _commands = {
        WorkflowStage.BUILD: RegisteredCommand(
            stage=WorkflowStage.BUILD,
            tool_id="build",
            command="python",
            args=("-m", "compileall", "-q", "services/api/parallax_api", "scripts"),
            timeout_seconds=120,
        ),
        WorkflowStage.TEST: RegisteredCommand(
            stage=WorkflowStage.TEST,
            tool_id="test",
            command="python",
            args=(
                "-m",
                "pytest",
                "-q",
                "services/api/tests/test_code_execution_kernel.py",
                "services/api/tests/test_code_autonomy.py",
            ),
            timeout_seconds=240,
        ),
        WorkflowStage.VERIFY: RegisteredCommand(
            stage=WorkflowStage.VERIFY,
            tool_id="verify",
            command="python",
            args=(
                "-m",
                "pytest",
                "-q",
                "services/api/tests/test_code_execution_kernel.py",
                "-k",
                "protected or execution or approved",
            ),
            timeout_seconds=240,
        ),
    }

    def spec_for(self, stage: WorkflowStage, *, operation_key: str) -> ExecutionSpec:
        try:
            command = self._commands[stage]
        except KeyError as exc:
            raise ExecutionPolicyError(f"no autonomous command is registered for {stage.value}") from exc
        return ExecutionSpec(
            tool_id=command.tool_id,
            args=command.args,
            working_directory=command.working_directory,
            timeout_seconds=command.timeout_seconds,
            environment_names=(),
            stage=stage,
            operation_key=operation_key,
        )

    def invocation_for(self, stage: WorkflowStage) -> tuple[str, tuple[str, ...]]:
        try:
            command = self._commands[stage]
        except KeyError as exc:
            raise ExecutionPolicyError(f"no autonomous command is registered for {stage.value}") from exc
        return command.command, command.args


class VercelSandboxUnavailable(RuntimeError):
    pass


def _bounded_evidence(spec: ExecutionSpec, *, exit_code: int | None, duration_ms: int,
                      stdout: str, stderr: str, timed_out: bool = False) -> dict[str, object]:
    stdout_excerpt = stdout[:2_000]
    stderr_excerpt = stderr[:2_000]
    invocation = json.dumps(
        {"tool": spec.tool_id, "args": spec.args, "cwd": spec.working_directory},
        sort_keys=True,
    )
    return {
        "tool_id": spec.tool_id,
        "invocation_digest": sha256(invocation.encode()).hexdigest(),
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "stdout_digest": sha256(stdout.encode()).hexdigest(),
        "stdout_excerpt": stdout_excerpt,
        "stderr_digest": sha256(stderr.encode()).hexdigest(),
        "stderr_excerpt": stderr_excerpt,
        "timed_out": timed_out,
        "redacted": len(stdout_excerpt) != len(stdout) or len(stderr_excerpt) != len(stderr),
        "artifacts": [],
        "protected_success": exit_code == 0 and not timed_out,
        "executor": "vercel-sandbox",
        "network_policy": "deny-all",
        "persistent": False,
    }


class VercelSandboxExecutor:
    """Runs protected commands in an ephemeral deny-all Vercel Sandbox.

    The Git source is initialized by the Sandbox service before the runtime is
    exposed to the command. No application environment values are forwarded.
    """

    def __init__(
        self,
        *,
        registry: ProtectedCommandRegistry | None = None,
        policy: ProtectedCommandPolicy | None = None,
        repository_url: str | None = None,
        revision: str | None = None,
        project_id: str | None = None,
    ) -> None:
        self.registry = registry or ProtectedCommandRegistry()
        self.policy = policy or ProtectedCommandPolicy()
        self.repository_url = repository_url or os.getenv(
            "PARALLAX_AUTONOMY_REPOSITORY_URL", "https://github.com/Ryan9876/parallax.git"
        )
        self.revision = revision or os.getenv("VERCEL_GIT_COMMIT_SHA") or os.getenv(
            "PARALLAX_AUTONOMY_REVISION", "p2/v0.13.0-bounded-autonomy"
        )
        self.project_id = project_id or os.getenv("VERCEL_PROJECT_ID")

    @staticmethod
    def _sdk():
        try:
            from vercel.api import session
            from vercel.sandbox import GitSource, NetworkPolicy
            from vercel.sandbox import sync as sandbox
        except ImportError as exc:
            raise VercelSandboxUnavailable("Vercel Sandbox SDK is not installed") from exc
        return session, GitSource, NetworkPolicy, sandbox

    def _require_identity(self) -> None:
        if not self.project_id:
            raise VercelSandboxUnavailable("Vercel project identity is unavailable")
        # The SDK resolves project-scoped credentials from Vercel runtime identity.
        # Never copy VERCEL_OIDC_TOKEN or VERCEL_TOKEN into the sandbox environment.

    def execute(self, spec: ExecutionSpec) -> dict[str, object]:
        self.policy.validate(spec)
        command, registered_args = self.registry.invocation_for(spec.stage)
        registered_spec = self.registry.spec_for(spec.stage, operation_key=spec.operation_key)
        if spec != registered_spec:
            raise ExecutionPolicyError("execution spec does not match the protected command registry")
        return self._run(
            spec,
            command=command,
            args=registered_args,
            source_repository=True,
        )

    def probe(self, *, operation_key: str) -> dict[str, object]:
        if not operation_key:
            raise ExecutionPolicyError("probe operation key is required")
        spec = ExecutionSpec(
            tool_id="python",
            args=("-c", "print('PARALLAX_SANDBOX_READY')"),
            timeout_seconds=60,
            stage=WorkflowStage.BUILD,
            operation_key=operation_key,
        )
        self.policy.validate(spec)
        return self._run(
            spec,
            command="python",
            args=spec.args,
            source_repository=False,
        )

    def _run(
        self,
        spec: ExecutionSpec,
        *,
        command: str,
        args: tuple[str, ...],
        source_repository: bool,
    ) -> dict[str, object]:
        self._require_identity()
        session, GitSource, NetworkPolicy, sandbox = self._sdk()
        source = (
            GitSource(url=self.repository_url, revision=self.revision, depth=1)
            if source_repository
            else None
        )
        started = time.monotonic()
        try:
            with session():
                with sandbox.create_sandbox(
                    project_id=self.project_id,
                    source=source,
                    execution_time_limit=spec.timeout_seconds + 30,
                    persistent=False,
                    network_policy=NetworkPolicy.deny_all(),
                    env={},
                    destroy=True,
                    tags={"parallax": "bounded-autonomy", "stage": spec.stage.value.lower()},
                ) as instance:
                    result = instance.run_process(
                        command,
                        list(args),
                        cwd=spec.working_directory,
                        env={},
                        kill_after=spec.timeout_seconds,
                        capture_output=True,
                    )
            duration_ms = int((time.monotonic() - started) * 1_000)
            return _bounded_evidence(
                spec,
                exit_code=result.returncode,
                duration_ms=duration_ms,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )
        except Exception as exc:
            # Provider/API errors are observable failures, never passing evidence.
            duration_ms = int((time.monotonic() - started) * 1_000)
            name = type(exc).__name__
            message = str(exc)[:1_000]
            return _bounded_evidence(
                spec,
                exit_code=None,
                duration_ms=duration_ms,
                stdout="",
                stderr=f"{name}: {message}",
                timed_out="timeout" in name.lower(),
            )
