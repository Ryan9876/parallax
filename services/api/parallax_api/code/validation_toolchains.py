from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re

from .domain import WorkflowStage
from .execution import ExecutionPolicyError, ExecutionSpec
from .sandbox_execution import ProtectedCommandRegistry, RegisteredCommand


class ValidationProfileReason(StrEnum):
    UNSUPPORTED_VALIDATION_ECOSYSTEM = "UNSUPPORTED_VALIDATION_ECOSYSTEM"
    AMBIGUOUS_VALIDATION_ECOSYSTEM = "AMBIGUOUS_VALIDATION_ECOSYSTEM"
    AMBIGUOUS_DOTNET_TARGET = "AMBIGUOUS_DOTNET_TARGET"
    PYTHON_FIXED_VALIDATION_UNAVAILABLE = "PYTHON_FIXED_VALIDATION_UNAVAILABLE"
    NODE_FIXED_VALIDATION_UNAVAILABLE = "NODE_FIXED_VALIDATION_UNAVAILABLE"
    EXECUTION_CONTRACT_DRIFT = "EXECUTION_CONTRACT_DRIFT"
    EXECUTION_CONTRACT_UNAVAILABLE = "EXECUTION_CONTRACT_UNAVAILABLE"
    EXECUTION_SNAPSHOT_UNAVAILABLE = "EXECUTION_SNAPSHOT_UNAVAILABLE"
    INVALID_VALIDATION_PROFILE = "INVALID_VALIDATION_PROFILE"
    INVALID_VALIDATION_TARGET = "INVALID_VALIDATION_TARGET"


class ValidationProfileError(ExecutionPolicyError):
    def __init__(
        self,
        code: ValidationProfileReason | str,
        message: str | None = None,
    ) -> None:
        raw = code.value if isinstance(code, ValidationProfileReason) else str(code)
        try:
            self.code = ValidationProfileReason(raw)
        except ValueError:
            self.code = ValidationProfileReason.INVALID_VALIDATION_PROFILE
        super().__init__(message or raw)


class ValidationProfileCode(StrEnum):
    PYTHON = "python-v1"
    DOTNET = "dotnet-v1"
    NODE = "node-v1"


class ExecutionContractCode(StrEnum):
    PARALLAX_PYTHON = "parallax-python-v1"
    DOTNET = "dotnet-v1"
    STATIC_WEB = "static-web-v1"


class ExecutionBindingReason(StrEnum):
    EXISTING_PARALLAX_PYTHON = "EXISTING_PARALLAX_PYTHON"
    EXISTING_DOTNET = "EXISTING_DOTNET"
    GREENFIELD_STATIC_WEB = "GREENFIELD_STATIC_WEB"


@dataclass(frozen=True, slots=True)
class PreparationCommand:
    tool_id: str
    probe_command: str
    probe_args: tuple[str, ...]
    probe_timeout_seconds: int
    command: str
    args: tuple[str, ...]
    working_directory: str
    timeout_seconds: int
    package_domains: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ValidationProfile:
    profile_id: ValidationProfileCode
    ecosystem: str
    root: str
    target: str | None
    commands: tuple[RegisteredCommand, ...]
    preparation: PreparationCommand | None = None

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
        if self.preparation is not None:
            payload["preparation"] = {
                "tool_id": self.preparation.tool_id,
                "probe_command": self.preparation.probe_command,
                "probe_args": list(self.preparation.probe_args),
                "probe_timeout_seconds": self.preparation.probe_timeout_seconds,
                "command": self.preparation.command,
                "args": list(self.preparation.args),
                "working_directory": self.preparation.working_directory,
                "timeout_seconds": self.preparation.timeout_seconds,
                "package_domains": list(self.preparation.package_domains),
            }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def command_for(self, stage: WorkflowStage) -> RegisteredCommand:
        for command in self.commands:
            if command.stage is stage:
                return command
        raise ValidationProfileError(
            ValidationProfileReason.INVALID_VALIDATION_PROFILE,
            f"validation profile has no command for {stage.value}",
        )

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


@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: ExecutionContractCode
    binding_reason: ExecutionBindingReason
    validation_profile: ValidationProfile

    @property
    def target(self) -> str | None:
        return self.validation_profile.target

    @property
    def digest(self) -> str:
        payload = {
            "contract_id": self.contract_id.value,
            "binding_reason": self.binding_reason.value,
            "validation_profile_id": self.validation_profile.profile_id.value,
            "validation_profile_digest": self.validation_profile.digest,
            "target": self.target,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


_SHA256_RE = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class ExecutionContractIdentity:
    """Persisted PLAN identity for one closed-catalog execution contract."""

    contract_id: str
    binding_reason: str
    target: str | None
    contract_digest: str
    validation_profile_id: str
    validation_profile_digest: str

    @classmethod
    def from_evidence(cls, evidence: dict[str, object]) -> "ExecutionContractIdentity":
        contract_id = evidence.get("execution_contract_id")
        binding_reason = evidence.get("execution_contract_binding_reason")
        target = evidence.get("execution_contract_target")
        contract_digest = evidence.get("execution_contract_digest")
        validation_profile_id = evidence.get("validation_profile_id")
        validation_profile_digest = evidence.get("validation_profile_digest")
        if (
            not isinstance(contract_id, str)
            or not contract_id
            or not isinstance(binding_reason, str)
            or not binding_reason
            or (target is not None and not isinstance(target, str))
            or not isinstance(contract_digest, str)
            or _SHA256_RE.fullmatch(contract_digest) is None
            or not isinstance(validation_profile_id, str)
            or not validation_profile_id
            or not isinstance(validation_profile_digest, str)
            or _SHA256_RE.fullmatch(validation_profile_digest) is None
        ):
            raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
        return cls(
            contract_id=contract_id,
            binding_reason=binding_reason,
            target=target,
            contract_digest=contract_digest,
            validation_profile_id=validation_profile_id,
            validation_profile_digest=validation_profile_digest,
        )

    @classmethod
    def from_contract(cls, contract: ExecutionContract) -> "ExecutionContractIdentity":
        if not isinstance(contract, ExecutionContract):
            raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
        return cls(
            contract_id=contract.contract_id.value,
            binding_reason=contract.binding_reason.value,
            target=contract.target,
            contract_digest=contract.digest,
            validation_profile_id=contract.validation_profile.profile_id.value,
            validation_profile_digest=contract.validation_profile.digest,
        )

    def resolve(self) -> ExecutionContract:
        contract = resolve_execution_contract(
            self.contract_id,
            binding_reason=self.binding_reason,
            target=self.target,
        )
        expected = self.from_contract(contract)
        if self != expected:
            raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
        return contract


def _safe_relative(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    return _validate_bound_target(relative)


def _validate_bound_target(target: str) -> str:
    pure = PurePosixPath(target)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.suffix.casefold() not in {".sln", ".csproj"}
    ):
        raise ValidationProfileError(ValidationProfileReason.INVALID_VALIDATION_TARGET)
    return pure.as_posix()


def _root_files(root: Path, pattern: str) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.glob(pattern) if path.is_file() and not path.is_symlink()))


def _is_regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _is_regular_dir(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()


def _validate_root(root: Path) -> Path:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValidationProfileError(ValidationProfileReason.INVALID_VALIDATION_PROFILE)
    return root.resolve(strict=True)


def _is_established_parallax_python_root(root: Path) -> bool:
    """Recognize only the source shape covered by the legacy protected commands."""

    return (
        _is_regular_file(root / "services/api/pyproject.toml")
        and _is_regular_dir(root / "services/api/parallax_api")
        and _is_regular_file(root / "services/api/tests/test_code_execution_kernel.py")
        and _is_regular_file(root / "services/api/tests/test_code_autonomy.py")
        and _is_regular_dir(root / "scripts")
    )


def _legacy_parallax_commands() -> tuple[RegisteredCommand, ...]:
    registry = ProtectedCommandRegistry()
    commands: list[RegisteredCommand] = []
    for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY):
        spec = registry.spec_for(stage, operation_key="validation-profile")
        executable, args = registry.invocation_for(stage)
        commands.append(
            RegisteredCommand(
                stage=stage,
                tool_id=spec.tool_id,
                command=executable,
                args=args,
                working_directory=spec.working_directory,
                timeout_seconds=spec.timeout_seconds,
            )
        )
    return tuple(commands)


def _parallax_python_profile() -> ValidationProfile:
    return ValidationProfile(
        profile_id=ValidationProfileCode.PYTHON,
        ecosystem="python",
        root=".",
        target=None,
        commands=_legacy_parallax_commands(),
    )


def _dotnet_profile(target: str) -> ValidationProfile:
    target = _validate_bound_target(target)
    common = (target, "--no-restore", "--nologo")
    return ValidationProfile(
        profile_id=ValidationProfileCode.DOTNET,
        ecosystem="dotnet",
        root=".",
        target=target,
        preparation=PreparationCommand(
            tool_id="dotnet-restore",
            probe_command="dotnet",
            probe_args=("--info",),
            probe_timeout_seconds=30,
            command="dotnet",
            args=("restore", target, "--nologo"),
            working_directory=".",
            timeout_seconds=300,
            package_domains=("api.nuget.org", "globalcdn.nuget.org"),
        ),
        commands=(
            RegisteredCommand(WorkflowStage.BUILD, "build", "dotnet", ("build", *common), timeout_seconds=300),
            RegisteredCommand(
                WorkflowStage.TEST,
                "test",
                "dotnet",
                ("test", target, "--no-restore", "--nologo"),
                timeout_seconds=300,
            ),
            RegisteredCommand(
                WorkflowStage.VERIFY,
                "verify",
                "dotnet",
                ("test", target, "--no-restore", "--nologo"),
                timeout_seconds=300,
            ),
        ),
    )


def _static_web_profile() -> ValidationProfile:
    validator = "/vercel/parallax-validator/static_web_validator.py"
    source_root = "/vercel/sandbox"
    commands = tuple(
        RegisteredCommand(
            stage=stage,
            tool_id={
                WorkflowStage.BUILD: "build",
                WorkflowStage.TEST: "test",
                WorkflowStage.VERIFY: "verify",
            }[stage],
            command="python",
            args=(validator, stage.value, source_root),
            working_directory=".",
            timeout_seconds=60,
        )
        for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY)
    )
    return ValidationProfile(
        profile_id=ValidationProfileCode.NODE,
        ecosystem="static-web",
        root=".",
        target=None,
        commands=commands,
    )


def _source_shape(root: Path) -> tuple[tuple[Path, ...], tuple[Path, ...], tuple[Path, ...], bool]:
    root_solutions = _root_files(root, "*.sln")
    root_projects = _root_files(root, "*.csproj")
    python_markers = tuple(
        path
        for name in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
        if _is_regular_file(path := root / name)
    )
    return root_solutions, root_projects, python_markers, _is_regular_file(root / "package.json")


def _dotnet_target(root: Path, root_solutions: tuple[Path, ...], root_projects: tuple[Path, ...]) -> str:
    if len(root_solutions) > 1:
        raise ValidationProfileError(ValidationProfileReason.AMBIGUOUS_DOTNET_TARGET)
    if root_solutions:
        return _safe_relative(root_solutions[0], root)
    if len(root_projects) == 1:
        return _safe_relative(root_projects[0], root)
    raise ValidationProfileError(ValidationProfileReason.AMBIGUOUS_DOTNET_TARGET)


def select_validation_profile(root: Path) -> ValidationProfile:
    """Legacy source-shape selector retained for already governed profile consumers.

    Greenfield admission deliberately remains unsupported here. P2-V0.23.31
    binds greenfield execution through `bind_execution_contract` during PLAN so
    candidate validation never infers authority from candidate source.
    """

    resolved = _validate_root(root)
    if _is_established_parallax_python_root(resolved):
        return _parallax_python_profile()

    root_solutions, root_projects, python_markers, has_node = _source_shape(resolved)
    ecosystems = int(bool(root_solutions or root_projects)) + int(bool(python_markers)) + int(has_node)
    if ecosystems == 0:
        raise ValidationProfileError(ValidationProfileReason.UNSUPPORTED_VALIDATION_ECOSYSTEM)
    if ecosystems > 1:
        raise ValidationProfileError(ValidationProfileReason.AMBIGUOUS_VALIDATION_ECOSYSTEM)
    if root_solutions or root_projects:
        return _dotnet_profile(_dotnet_target(resolved, root_solutions, root_projects))
    if python_markers:
        raise ValidationProfileError(ValidationProfileReason.PYTHON_FIXED_VALIDATION_UNAVAILABLE)
    raise ValidationProfileError(ValidationProfileReason.NODE_FIXED_VALIDATION_UNAVAILABLE)


def bind_execution_contract(root: Path) -> ExecutionContract:
    """Bind execution authority once from accepted source before IMPLEMENT."""

    resolved = _validate_root(root)
    if _is_established_parallax_python_root(resolved):
        return ExecutionContract(
            contract_id=ExecutionContractCode.PARALLAX_PYTHON,
            binding_reason=ExecutionBindingReason.EXISTING_PARALLAX_PYTHON,
            validation_profile=_parallax_python_profile(),
        )

    root_solutions, root_projects, python_markers, has_node = _source_shape(resolved)
    ecosystems = int(bool(root_solutions or root_projects)) + int(bool(python_markers)) + int(has_node)
    if ecosystems == 0:
        return ExecutionContract(
            contract_id=ExecutionContractCode.STATIC_WEB,
            binding_reason=ExecutionBindingReason.GREENFIELD_STATIC_WEB,
            validation_profile=_static_web_profile(),
        )
    if ecosystems > 1:
        raise ValidationProfileError(ValidationProfileReason.AMBIGUOUS_VALIDATION_ECOSYSTEM)
    if root_solutions or root_projects:
        return ExecutionContract(
            contract_id=ExecutionContractCode.DOTNET,
            binding_reason=ExecutionBindingReason.EXISTING_DOTNET,
            validation_profile=_dotnet_profile(_dotnet_target(resolved, root_solutions, root_projects)),
        )
    if python_markers:
        raise ValidationProfileError(ValidationProfileReason.PYTHON_FIXED_VALIDATION_UNAVAILABLE)
    raise ValidationProfileError(ValidationProfileReason.NODE_FIXED_VALIDATION_UNAVAILABLE)


def resolve_execution_contract(
    contract_id: str,
    *,
    binding_reason: str,
    target: str | None,
) -> ExecutionContract:
    """Resolve only a previously bound closed-catalog contract; never inspect source."""

    try:
        code = ExecutionContractCode(contract_id)
        reason = ExecutionBindingReason(binding_reason)
    except ValueError as exc:
        raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_UNAVAILABLE) from exc

    if code is ExecutionContractCode.PARALLAX_PYTHON:
        if reason is not ExecutionBindingReason.EXISTING_PARALLAX_PYTHON or target is not None:
            raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
        profile = _parallax_python_profile()
    elif code is ExecutionContractCode.DOTNET:
        if reason is not ExecutionBindingReason.EXISTING_DOTNET or not isinstance(target, str):
            raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
        profile = _dotnet_profile(target)
    elif code is ExecutionContractCode.STATIC_WEB:
        if reason is not ExecutionBindingReason.GREENFIELD_STATIC_WEB or target is not None:
            raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
        profile = _static_web_profile()
    else:  # pragma: no cover - StrEnum exhaustiveness
        raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_UNAVAILABLE)

    return ExecutionContract(code, reason, profile)


__all__ = [
    "ExecutionBindingReason",
    "ExecutionContract",
    "ExecutionContractCode",
    "ExecutionContractIdentity",
    "PreparationCommand",
    "ValidationProfile",
    "ValidationProfileCode",
    "ValidationProfileError",
    "ValidationProfileReason",
    "bind_execution_contract",
    "resolve_execution_contract",
    "select_validation_profile",
]
