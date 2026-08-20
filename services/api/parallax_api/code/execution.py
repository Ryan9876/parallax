from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import re

from .domain import WorkflowStage


class ExecutionPolicyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExecutionSpec:
    tool_id: str
    args: tuple[str, ...] = ()
    working_directory: str = "."
    timeout_seconds: int = 120
    environment_names: tuple[str, ...] = ()
    stage: WorkflowStage = WorkflowStage.BUILD
    operation_key: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    exit_code: int | None
    duration_ms: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    redacted: bool = False
    artifacts: tuple[dict[str, object], ...] = field(default_factory=tuple)


class ProtectedCommandPolicy:
    allowed_tools = frozenset({"python", "pytest", "npm-typecheck", "npm-test", "build", "test", "verify"})
    forbidden_tokens = re.compile(r"[;&|`$<>\n\r]")

    def validate(self, spec: ExecutionSpec) -> None:
        if spec.stage not in {WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY}:
            raise ExecutionPolicyError("execution is limited to BUILD, TEST, or VERIFY")
        if spec.tool_id not in self.allowed_tools:
            raise ExecutionPolicyError("tool is not in the protected registry")
        if not spec.operation_key or not 1 <= spec.timeout_seconds <= 600:
            raise ExecutionPolicyError("invalid operation key or timeout")
        if spec.working_directory.startswith(("/", "~")) or ".." in spec.working_directory.split("/"):
            raise ExecutionPolicyError("working directory escapes the workspace")
        for value in (*spec.args, spec.working_directory):
            if self.forbidden_tokens.search(value):
                raise ExecutionPolicyError("shell metacharacters are not permitted")
        if spec.environment_names:
            raise ExecutionPolicyError("undeclared environment access is disabled")


class RecordedExecutor:
    def __init__(self, results: dict[str, ExecutionResult], *, policy: ProtectedCommandPolicy | None = None):
        self.results = results
        self.policy = policy or ProtectedCommandPolicy()

    def execute(self, spec: ExecutionSpec) -> dict[str, object]:
        self.policy.validate(spec)
        result = self.results.get(spec.operation_key)
        if result is None:
            raise ExecutionPolicyError("no deterministic result exists for this operation")
        stdout = result.stdout[:2_000]
        stderr = result.stderr[:2_000]
        payload = json.dumps({"tool": spec.tool_id, "args": spec.args, "cwd": spec.working_directory}, sort_keys=True)
        return {
            "tool_id": spec.tool_id,
            "invocation_digest": sha256(payload.encode()).hexdigest(),
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
            "stdout_digest": sha256(result.stdout.encode()).hexdigest(),
            "stdout_excerpt": stdout,
            "stderr_digest": sha256(result.stderr.encode()).hexdigest(),
            "stderr_excerpt": stderr,
            "timed_out": result.timed_out,
            "redacted": result.redacted or len(stdout) != len(result.stdout) or len(stderr) != len(result.stderr),
            "artifacts": list(result.artifacts),
            "protected_success": result.exit_code == 0 and not result.timed_out,
        }
