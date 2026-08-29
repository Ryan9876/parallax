from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"anchor not found in {path}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


validation = "services/api/parallax_api/code/validation_toolchains.py"
replace_once(
    validation,
    "@dataclass(frozen=True, slots=True)\nclass ValidationProfile:\n",
    """@dataclass(frozen=True, slots=True)
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
""",
)
replace_once(
    validation,
    "    commands: tuple[RegisteredCommand, ...]\n\n    @property\n",
    "    commands: tuple[RegisteredCommand, ...]\n    preparation: PreparationCommand | None = None\n\n    @property\n",
)
replace_once(
    validation,
    '        }\n        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()\n',
    '''        }
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
''',
)
replace_once(
    validation,
    "            target=target,\n            commands=(\n",
    '''            target=target,
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
''',
)
text = Path(validation).read_text(encoding="utf-8")
text = text.replace(
    '("test", target, "--no-build", "--no-restore", "--nologo")',
    '("test", target, "--no-restore", "--nologo")',
)
text = text.replace(
    '    "ValidationProfile",\n',
    '    "PreparationCommand",\n    "ValidationProfile",\n',
    1,
)
Path(validation).write_text(text, encoding="utf-8")

agentic = "services/api/parallax_api/code/agentic_runtime.py"
replace_once(
    agentic,
    "from .domain import WorkflowStage\n",
    "from .dependency_preparation import DependencyPreparationError, preparation_network_policy, run_dependency_preparation\nfrom .domain import WorkflowStage\n",
)
replace_once(
    agentic,
    "                network_policy=NetworkPolicy.deny_all(),\n",
    "                network_policy=preparation_network_policy(NetworkPolicy, profile),\n",
)
replace_once(
    agentic,
    "                self._transfer_source(instance, files)\n                for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY):\n",
    '''                self._transfer_source(instance, files)
                try:
                    preparation_evidence = run_dependency_preparation(
                        instance,
                        NetworkPolicy,
                        profile,
                        sandbox_cwd=self._sandbox_cwd,
                    )
                except DependencyPreparationError as exc:
                    failure_spec = profile.spec_for(
                        WorkflowStage.BUILD,
                        operation_key=f"{operation_key[:120]}:candidate:prepare",
                    )
                    evidence = _bounded_evidence(
                        failure_spec,
                        exit_code=None,
                        duration_ms=int(exc.evidence.get("dependency_preparation_duration_ms") or 0),
                        stdout="",
                        stderr=exc.code,
                    )
                    evidence.update(
                        {
                            **exc.evidence,
                            "candidate_content_digest": content_digest,
                            "candidate_file_count": len(files),
                            "candidate_total_bytes": total_bytes,
                            "validation_profile_id": profile.profile_id.value,
                            "validation_profile_digest": profile.digest,
                            "execution_snapshot_id": self.snapshot_id,
                            "execution_snapshot_verified": True,
                            "network_policy": "deny-all" if exc.evidence.get("validation_network_locked") is True else "prepare-bounded",
                            "candidate_is_canonical_lineage": False,
                            "accepts_source_lineage": False,
                        }
                    )
                    stage_evidence.append((WorkflowStage.BUILD.value, evidence))
                    return CandidateValidationResult(
                        content_digest=content_digest,
                        file_count=len(files),
                        total_bytes=total_bytes,
                        validation_profile_id=profile.profile_id.value,
                        validation_profile_digest=profile.digest,
                        stage_evidence=tuple(stage_evidence),
                    )
                if preparation_evidence.get("validation_network_locked") is not True:
                    raise AgenticRuntimeError("validation network lock was not proven")
                for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY):
''',
)
replace_once(
    agentic,
    '                            "accepts_source_lineage": False,\n                        }\n                    )\n',
    '                            "accepts_source_lineage": False,\n                            **preparation_evidence,\n                        }\n                    )\n',
)

lineage = "services/api/parallax_api/code/lineage_sandbox_execution.py"
replace_once(
    lineage,
    "from .execution import ExecutionPolicyError, ExecutionSpec, ProtectedCommandPolicy\n",
    "from .dependency_preparation import preparation_network_policy, run_dependency_preparation\nfrom .execution import ExecutionPolicyError, ExecutionSpec, ProtectedCommandPolicy\n",
)
replace_once(
    lineage,
    "        cleanup_error: Exception | None = None\n",
    '''        cleanup_error: Exception | None = None
        preparation_evidence: dict[str, object] = {
            "dependency_preparation_required": False,
            "dependency_preparation_succeeded": False,
            "validation_network_locked": False,
        }
''',
)
replace_once(
    lineage,
    "                    network_policy=NetworkPolicy.deny_all(),\n",
    "                    network_policy=preparation_network_policy(NetworkPolicy, profile),\n",
)
replace_once(
    lineage,
    "                    self._transfer_source(instance, files)\n                    result = instance.run_process(\n",
    '''                    self._transfer_source(instance, files)
                    preparation_evidence = run_dependency_preparation(
                        instance,
                        NetworkPolicy,
                        profile,
                        sandbox_cwd=self._sandbox_cwd,
                    )
                    if preparation_evidence.get("validation_network_locked") is not True:
                        raise SameLineageExecutionError("validation network lock was not proven")
                    result = instance.run_process(
''',
)
replace_once(
    lineage,
    '                    "execution_working_directory": self._sandbox_cwd(execution_spec.working_directory),\n                }\n            )\n',
    '                    "execution_working_directory": self._sandbox_cwd(execution_spec.working_directory),\n                    **preparation_evidence,\n                }\n            )\n',
)
replace_once(
    lineage,
    '                    "validation_profile_digest": validation_profile_digest,\n                }\n            )\n',
    '                    "validation_profile_digest": validation_profile_digest,\n                    **preparation_evidence,\n                }\n            )\n',
)

validation_test = Path("services/api/tests/test_validation_toolchains.py")
text = validation_test.read_text(encoding="utf-8").replace(
    '("test", "OtTime.sln", "--no-build", "--no-restore", "--nologo")',
    '("test", "OtTime.sln", "--no-restore", "--nologo")',
)
validation_test.write_text(text, encoding="utf-8")

lineage_test = Path("services/api/tests/test_lineage_sandbox_execution.py")
text = lineage_test.read_text(encoding="utf-8").replace(
    'assert tuple(args) == ("-m", "compileall", "-q", ".")',
    'assert tuple(args) == ProtectedCommandRegistry().invocation_for(WorkflowStage.BUILD)[1]',
)
lineage_test.write_text(text, encoding="utf-8")
