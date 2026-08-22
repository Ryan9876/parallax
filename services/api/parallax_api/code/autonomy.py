from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from ..models import EngineeringRun
from .domain import WorkflowStage
from .execution import ExecutionSpec
from .sandbox_execution import ProtectedCommandRegistry
from .service import EngineeringRunService
from .state_machine import RevisionConflict


class AutonomousExecutor(Protocol):
    def execute(self, spec: ExecutionSpec) -> dict[str, object]: ...

    def probe(self, *, operation_key: str) -> dict[str, object]: ...


class AutonomyStopReason(str, Enum):
    IMPLEMENTATION_REQUIRED = "IMPLEMENTATION_REQUIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    SPEC_AMENDMENT = "SPEC_AMENDMENT"
    EXECUTOR_UNAVAILABLE = "EXECUTOR_UNAVAILABLE"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    MAX_STEPS_REACHED = "MAX_STEPS_REACHED"


@dataclass(frozen=True, slots=True)
class AutonomyStep:
    stage: str
    outcome: str
    attempt_id: str | None = None
    replayed: bool = False
    tool_id: str | None = None


@dataclass(frozen=True, slots=True)
class AutonomyResult:
    run: EngineeringRun
    stop_reason: AutonomyStopReason
    steps: tuple[AutonomyStep, ...] = field(default_factory=tuple)


class AutonomyCoordinator:
    """Advance only stages for which v0.13 grants explicit autonomous authority."""

    def __init__(
        self,
        service: EngineeringRunService,
        executor: AutonomousExecutor,
        *,
        registry: ProtectedCommandRegistry | None = None,
        max_steps: int = 8,
    ) -> None:
        self.service = service
        self.executor = executor
        self.registry = registry or ProtectedCommandRegistry()
        self.max_steps = max_steps

    def run(
        self,
        *,
        run_id: str,
        operation_key: str,
        expected_revision: int,
    ) -> AutonomyResult:
        if not operation_key:
            raise ValueError("autonomy operation key is required")
        run = self.service.get(run_id)
        if run.revision != expected_revision:
            raise RevisionConflict(
                f"stale engineering run revision: expected {expected_revision}, current {run.revision}"
            )

        steps: list[AutonomyStep] = []
        for _ in range(self.max_steps):
            run = self.service.get(run_id)
            stage = WorkflowStage(run.state)

            terminal_reason = self._stop_reason(stage)
            if terminal_reason is not None:
                return AutonomyResult(run=run, stop_reason=terminal_reason, steps=tuple(steps))

            if stage is WorkflowStage.PLAN:
                probe_key = f"{operation_key[:130]}:executor-probe:{run.revision}"
                probe = self.executor.probe(operation_key=probe_key)
                probe_passed = probe.get("protected_success") is True
                if not probe_passed:
                    result = self.service.complete_stage(
                        run_id=run.id,
                        stage=WorkflowStage.PLAN,
                        operation_key=self._stage_key(operation_key, stage, run.revision),
                        expected_revision=run.revision,
                        passed=False,
                        evidence={
                            "executor_preflight": "failed",
                            "executor": probe.get("executor"),
                            "network_policy": probe.get("network_policy"),
                            "exit_code": probe.get("exit_code"),
                            "duration_ms": probe.get("duration_ms"),
                            "stdout_excerpt": probe.get("stdout_excerpt"),
                            "stderr_excerpt": probe.get("stderr_excerpt"),
                            "timed_out": probe.get("timed_out"),
                            "redacted": probe.get("redacted"),
                        },
                        failure_code="AUTONOMOUS_EXECUTOR_UNAVAILABLE",
                        program_id="bounded-autonomy-v0.13.0",
                        tool_id=str(probe.get("tool_id") or "python"),
                    )
                    steps.append(
                        AutonomyStep(
                            stage="EXECUTOR",
                            outcome="FAILED",
                            attempt_id=result.attempt_id,
                            replayed=result.replayed,
                            tool_id=str(probe.get("tool_id") or "python"),
                        )
                    )
                    return AutonomyResult(
                        run=result.run,
                        stop_reason=AutonomyStopReason.EXECUTOR_UNAVAILABLE,
                        steps=tuple(steps),
                    )

                steps.append(
                    AutonomyStep(
                        stage="EXECUTOR",
                        outcome="PASSED",
                        tool_id=str(probe.get("tool_id") or "python"),
                    )
                )
                required = sorted(item["id"] for item in self.service.acceptance_map_for_run(run))
                evidence: dict[str, object] = {
                    "acceptance_ids_covered": required,
                    "work_items": [
                        {"acceptance_id": acceptance_id, "action": "satisfy protected acceptance criterion"}
                        for acceptance_id in required
                    ],
                    "validation_checks": [
                        {"acceptance_id": acceptance_id, "check": "verify against protected acceptance criterion"}
                        for acceptance_id in required
                    ],
                    "planner": "protected-deterministic-v0.13.0",
                    "executor_preflight": "passed",
                }
                result = self.service.complete_stage(
                    run_id=run.id,
                    stage=WorkflowStage.PLAN,
                    operation_key=self._stage_key(operation_key, stage, run.revision),
                    expected_revision=run.revision,
                    passed=True,
                    evidence=evidence,
                    program_id="protected-autonomy-plan-v0.13.0",
                )
                steps.append(
                    AutonomyStep(
                        stage=stage.value,
                        outcome="PASSED",
                        attempt_id=result.attempt_id,
                        replayed=result.replayed,
                    )
                )
                continue

            if stage in {WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY}:
                stage_key = self._stage_key(operation_key, stage, run.revision)
                spec = self.registry.spec_for(stage, operation_key=stage_key)
                evidence = self.executor.execute(spec)
                acceptance_ids = sorted(item["id"] for item in self.service.acceptance_map_for_run(run))
                if stage is WorkflowStage.BUILD:
                    evidence["acceptance_ids_targeted"] = acceptance_ids
                else:
                    evidence["acceptance_ids_verified"] = acceptance_ids

                passed = evidence.get("protected_success") is True
                result = self.service.complete_stage(
                    run_id=run.id,
                    stage=stage,
                    operation_key=stage_key,
                    expected_revision=run.revision,
                    passed=passed,
                    evidence=evidence,
                    failure_code=None if passed else f"AUTONOMOUS_{stage.value}_FAILED",
                    program_id="bounded-autonomy-v0.13.0",
                    tool_id=str(evidence.get("tool_id") or spec.tool_id),
                )
                steps.append(
                    AutonomyStep(
                        stage=stage.value,
                        outcome="PASSED" if passed else "FAILED",
                        attempt_id=result.attempt_id,
                        replayed=result.replayed,
                        tool_id=spec.tool_id,
                    )
                )
                if not passed:
                    return AutonomyResult(
                        run=result.run,
                        stop_reason=AutonomyStopReason.EXECUTION_FAILED,
                        steps=tuple(steps),
                    )
                continue

            return AutonomyResult(
                run=run,
                stop_reason=AutonomyStopReason.IMPLEMENTATION_REQUIRED,
                steps=tuple(steps),
            )

        return AutonomyResult(
            run=self.service.get(run_id),
            stop_reason=AutonomyStopReason.MAX_STEPS_REACHED,
            steps=tuple(steps),
        )

    @staticmethod
    def _stage_key(operation_key: str, stage: WorkflowStage, revision: int) -> str:
        suffix = f":{stage.value.lower()}:{revision}"
        return f"{operation_key[: max(1, 160 - len(suffix))]}{suffix}"

    @staticmethod
    def _stop_reason(stage: WorkflowStage) -> AutonomyStopReason | None:
        reasons = {
            WorkflowStage.IMPLEMENT: AutonomyStopReason.IMPLEMENTATION_REQUIRED,
            WorkflowStage.REVIEW: AutonomyStopReason.REVIEW_REQUIRED,
            WorkflowStage.PAUSED: AutonomyStopReason.PAUSED,
            WorkflowStage.FAILED: AutonomyStopReason.FAILED,
            WorkflowStage.COMPLETE: AutonomyStopReason.COMPLETE,
            WorkflowStage.CANCELLED: AutonomyStopReason.CANCELLED,
            WorkflowStage.SPEC_AMENDMENT: AutonomyStopReason.SPEC_AMENDMENT,
        }
        return reasons.get(stage)
