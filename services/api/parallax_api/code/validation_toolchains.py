from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath

from .domain import WorkflowStage
from .execution import ExecutionPolicyError, ExecutionSpec
from .sandbox_execution import RegisteredCommand


class ValidationProfileError(ExecutionPolicyError):
    pass


class ValidationProfileCode(StrEnum):
    PYTHON = "python-v1"
    DOTNET = "dotnet-v1"
    NODE = "node-v1"


@dataclass(frozen=True, slots=True)
class ValidationProfile:
    profile_id: ValidationProfileCode
    ecosystem: str
    root: str
    target: str | None
    commands: tuple[RegisteredCommand, ...]

    @property
    def digest(self) -> str:
        payload = {
            "profile_id": self.profile_id.value,
            "ecosystem": self.ecosystem,
            "root": self.root,
            "target": self.target,
            "commands": [
                {
                    "stage": command.stage.value,
                    "tool_id": command.tool_id,
                    "command": command.command,
                    "args": list(command.args),
                    "working_directory": command.working_directory,
                    "timeout_seconds": command.timeout_seconds,
                }
                for command in self.commands
            ],
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def command_for(self, stage: WorkflowStage) -> RegisteredCommand:
        for command in self.commands:
            if command.stage is stage:
                return command
        raise ValidationProfileError(f"validation profile has no command for {stage.value}")

    def spec_for(self, stage: WorkflowStage, *, operation_key: str) -> ExecutionSpec:
        command = self.command_for(stage)
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
        command = self.command_for(stage)
        return command.command, command.args


def _safe_relative(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValidationProfileError("validation target path is unsafe")
    return relative


def _root_files(root: Path, pattern: str) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.glob(pattern) if path.is_file() and not path.is_symlink()))


def _has_bounded_python_source(root: Path) -> bool:
    """Recognize source-only Python lineages without trusting project scripts.

    Historical accepted-lineage fixtures (and valid small Python projects) may
    contain Python source without a packaging manifest. File suffix is bounded
    ecosystem evidence only; it never becomes executable command authority.
    """

    for path in root.rglob("*.py"):
        if path.is_symlink() or not path.is_file():
            continue
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise ValidationProfileError("validation source escaped workspace root")
        return True
    return False


def select_validation_profile(root: Path) -> ValidationProfile:
    """Select one immutable server-owned validation profile from source shape.

    File names and bounded paths are evidence only. Repository file contents,
    scripts, model output, and user text never become executable command text.
    """

    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValidationProfileError("validation workspace root is invalid")
    resolved = root.resolve(strict=True)

    root_solutions = _root_files(resolved, "*.sln")
    root_projects = _root_files(resolved, "*.csproj")
    python_markers = tuple(
        path
        for name in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
        if (path := resolved / name).is_file() and not path.is_symlink()
    )
    has_python = bool(python_markers) or _has_bounded_python_source(resolved)
    node_marker = resolved / "package.json"
    has_node = node_marker.is_file() and not node_marker.is_symlink()

    ecosystems = int(bool(root_solutions or root_projects)) + int(has_python) + int(has_node)
    if ecosystems == 0:
        raise ValidationProfileError("UNSUPPORTED_VALIDATION_ECOSYSTEM")
    if ecosystems > 1:
        raise ValidationProfileError("AMBIGUOUS_VALIDATION_ECOSYSTEM")

    if root_solutions or root_projects:
        if len(root_solutions) > 1:
            raise ValidationProfileError("AMBIGUOUS_DOTNET_TARGET")
        if root_solutions:
            target = _safe_relative(root_solutions[0], resolved)
        elif len(root_projects) == 1:
            target = _safe_relative(root_projects[0], resolved)
        else:
            raise ValidationProfileError("AMBIGUOUS_DOTNET_TARGET")
        common = (target, "--no-restore", "--nologo")
        return ValidationProfile(
            profile_id=ValidationProfileCode.DOTNET,
            ecosystem="dotnet",
            root=".",
            target=target,
            commands=(
                RegisteredCommand(WorkflowStage.BUILD, "build", "dotnet", ("build", *common), timeout_seconds=300),
                RegisteredCommand(
                    WorkflowStage.TEST,
                    "test",
                    "dotnet",
                    ("test", target, "--no-build", "--no-restore", "--nologo"),
                    timeout_seconds=300,
                ),
                RegisteredCommand(
                    WorkflowStage.VERIFY,
                    "verify",
                    "dotnet",
                    ("test", target, "--no-build", "--no-restore", "--nologo"),
                    timeout_seconds=300,
                ),
            ),
        )

    if has_python:
        return ValidationProfile(
            profile_id=ValidationProfileCode.PYTHON,
            ecosystem="python",
            root=".",
            target=None,
            commands=(
                RegisteredCommand(
                    WorkflowStage.BUILD,
                    "build",
                    "python",
                    ("-m", "compileall", "-q", "."),
                    timeout_seconds=180,
                ),
                RegisteredCommand(
                    WorkflowStage.TEST,
                    "test",
                    "python",
                    ("-m", "pytest", "-q"),
                    timeout_seconds=300,
                ),
                RegisteredCommand(
                    WorkflowStage.VERIFY,
                    "verify",
                    "python",
                    ("-m", "pytest", "-q"),
                    timeout_seconds=300,
                ),
            ),
        )

    # package.json is deterministic Node evidence, but executing repository-defined
    # package scripts would cross the authority boundary. Until a fixed offline
    # Node validation route is admitted, fail closed with a typed result.
    raise ValidationProfileError("NODE_FIXED_VALIDATION_UNAVAILABLE")


__all__ = [
    "ValidationProfile",
    "ValidationProfileCode",
    "ValidationProfileError",
    "select_validation_profile",
]
