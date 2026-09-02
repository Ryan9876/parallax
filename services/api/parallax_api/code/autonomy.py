from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Protocol

from ..models import EngineeringRun
from .domain import AttemptStatus, WorkflowStage
from .execution import ExecutionSpec
from .implementation_runtime import ImplementationRuntimeError, ProtectedImplementationRuntime
from .protected import STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE
from .run_events import RunEventError
from .sandbox_execution import ProtectedCommandRegistry
from .service import EngineeringRunService
from .state_machine import RevisionConflict
from .validation_toolchains import (
    ExecutionBindingReason,
    ExecutionContract,
    ExecutionContractCode,
    ExecutionContractIdentity,
    ValidationProfileError,
    ValidationProfileReason,
)


class AutonomousExecutor(Protocol):
    def execute(self, spec: ExecutionSpec) -> dict[str, object]: ...

    def probe(self, *, operation_key: str) -> dict[str, object]: ...


class LineageAwareAutonomousExecutor(Protocol):
    def execute_on_lineage(
        self,
        spec: ExecutionSpec,
        *,
        project_ref: str,
        run_id: str,
        source_lineage_ref: str,
        execution_contract: ExecutionContract,
    ) -> dict[str, object]: ...


class AutonomousPlanRuntime(Protocol):
    """Optional server-owned PLAN seam used by governed runtime composition."""

    program_id: str

    def plan(
        self,
        *,
        run: EngineeringRun,
        operation_key: str,
    ) -> dict[str, object]: ...


class AutonomyStopReason(str, Enum):
    IMPLEMENTATION_REQUIRED = "IMPLEMENTATION_REQUIRED"
    IMPLEMENTATION_FAILED = "IMPLEMENTATION_FAILED"
    LINEAGE_EXECUTOR_REQUIRED = "LINEAGE_EXECUTOR_REQUIRED"
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


@dataclass(frozen=True, slots=True)
class _AcceptedImplementationLineage:
    project_ref: str
    base_source_lineage_ref: str
    source_lineage_ref: str
    attempt_index: int


class AutonomyCoordinator:
    """Advance only stages with explicit protected autonomous authority.

    IMPLEMENT remains opt-in: a concrete protected runtime must be injected by
    serialized Project/workspace integration. Once IMPLEMENT has accepted a new
    source lineage, BUILD/TEST/VERIFY are also fail-closed unless a lineage-aware
    executor is explicitly injected. A legacy executor must never silently test
    unrelated source after a successful protected mutation.

    A composed PLAN runtime is likewise optional. When present it replaces only
    the bounded PLAN evidence producer; durable PLAN authority remains the same
    EngineeringRunService.complete_stage transition used by the legacy planner.
    """

    def __init__(
        self,
        service: EngineeringRunService,
        executor: AutonomousExecutor,
        *,
        registry: ProtectedCommandRegistry | None = None,
        implementation_runtime: ProtectedImplementationRuntime | None = None,
        lineage_executor: LineageAwareAutonomousExecutor | None = None,
        plan_runtime: AutonomousPlanRuntime | None = None,
        max_steps: int = 8,
    ) -> None:
        self.service = service
        self.executor = executor
        self.registry = registry or ProtectedCommandRegistry()
        self.implementation_runtime = implementation_runtime
        self.lineage_executor = lineage_executor
        self.plan_runtime = plan_runtime
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
                steps.append(
                    AutonomyStep(
                        stage="EXECUTOR",
                        outcome="PASSED" if probe_passed else "FAILED",
                        tool_id=str(probe.get("tool_id") or "python"),
                    )
                )
                if not probe_passed:
                    return AutonomyResult(
                        run=run,
                        stop_reason=AutonomyStopReason.EXECUTOR_UNAVAILABLE,
                        steps=tuple(steps),
                    )

                stage_key = self._stage_key(operation_key, stage, run.revision)
                if self.plan_runtime is None:
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
                    program_id = "protected-autonomy-plan-v0.13.0"
                else:
                    program_id = str(self.plan_runtime.program_id)
                    try:
                        evidence = self.plan_runtime.plan(
                            run=run,
                            operation_key=stage_key,
                        )
                        if not isinstance(evidence, dict) or not evidence:
                            raise ValueError("composed PLAN runtime returned invalid evidence")
                    except ValueError as exc:
                        failed = self.service.complete_stage(
                            run_id=run.id,
                            stage=WorkflowStage.PLAN,
                            operation_key=stage_key,
                            expected_revision=run.revision,
                            passed=False,
                            evidence={
                                "planner": program_id,
                                "executor_preflight": "passed",
                                "error_class": type(exc).__name__,
                                "agentic_plan_admission": "failed",
                                "protected_stage_authority": False,
                            },
                            failure_code="AUTONOMOUS_PLAN_ADMISSION_FAILED",
                            program_id=program_id,
                        )
                        steps.append(
                            AutonomyStep(
                                stage=stage.value,
                                outcome="FAILED",
                                attempt_id=failed.attempt_id,
                                replayed=failed.replayed,
                            )
                        )
                        return AutonomyResult(
                            run=failed.run,
                            stop_reason=AutonomyStopReason.FAILED,
                            steps=tuple(steps),
                        )

                rework_context = self.service.review_rework_context_for_run(run)
                if rework_context is not None:
                    evidence["review_rework_context_digest"] = rework_context.digest
                    evidence["review_rework_acceptance_ids"] = list(rework_context.acceptance_ids)

                result = self.service.complete_stage(
                    run_id=run.id,
                    stage=WorkflowStage.PLAN,
                    operation_key=stage_key,
                    expected_revision=run.revision,
                    passed=True,
                    evidence=evidence,
                    program_id=program_id,
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

            if stage is WorkflowStage.IMPLEMENT:
                if self.implementation_runtime is None:
                    return AutonomyResult(
                        run=run,
                        stop_reason=AutonomyStopReason.IMPLEMENTATION_REQUIRED,
                        steps=tuple(steps),
                    )
                stage_key = self._stage_key(operation_key, stage, run.revision)
                try:
                    implementation = self.implementation_runtime.execute(
                        run_id=run.id,
                        operation_key=stage_key,
                        expected_revision=run.revision,
                    )
                except ImplementationRuntimeError as exc:
                    if exc.mutation_applied:
                        steps.append(
                            AutonomyStep(
                                stage=stage.value,
                                outcome="FAILED_AFTER_MUTATION",
                                tool_id="implementation-runtime",
                            )
                        )
                        return AutonomyResult(
                            run=self.service.get(run.id),
                            stop_reason=AutonomyStopReason.IMPLEMENTATION_FAILED,
                            steps=tuple(steps),
                        )
                    failure_evidence: dict[str, object] = {
                        "error_class": type(exc).__name__,
                        "mutation_applied": False,
                    }
                    if exc.diagnostic_evidence is not None:
                        failure_evidence["diagnostic_evidence"] = exc.diagnostic_evidence
                    try:
                        failed = self.service.complete_stage(
                            run_id=run.id,
                            stage=WorkflowStage.IMPLEMENT,
                            operation_key=stage_key,
                            expected_revision=run.revision,
                            passed=False,
                            evidence=failure_evidence,
                            failure_code="AUTONOMOUS_IMPLEMENT_FAILED",
                            program_id="protected-implementation-runtime-v0.15.4",
                            tool_id="safe-source-implementation-v1",
                        )
                    except RunEventError:
                        # EngineeringRun/attempt persistence commits before optional
                        # observation projection. Recover only the exact expected
                        # durable failure; never fabricate an unknown mutation.
                        recorded = self.service.runs.find_operation(run.id, stage_key)
                        durable_run = self.service.get(run.id)
                        if (
                            recorded is None
                            or recorded.stage != WorkflowStage.IMPLEMENT.value
                            or recorded.status != AttemptStatus.FAILED.value
                            or recorded.failure_code != "AUTONOMOUS_IMPLEMENT_FAILED"
                            or durable_run.state != WorkflowStage.FAILED.value
                            or durable_run.resume_stage != WorkflowStage.IMPLEMENT.value
                            or durable_run.last_failure_code != "AUTONOMOUS_IMPLEMENT_FAILED"
                        ):
                            raise
                        steps.append(
                            AutonomyStep(
                                stage=stage.value,
                                outcome="FAILED",
                                attempt_id=recorded.id,
                                replayed=False,
                                tool_id="implementation-runtime",
                            )
                        )
                        return AutonomyResult(
                            run=durable_run,
                            stop_reason=AutonomyStopReason.IMPLEMENTATION_FAILED,
                            steps=tuple(steps),
                        )
                    steps.append(
                        AutonomyStep(
                            stage=stage.value,
                            outcome="FAILED",
                            attempt_id=failed.attempt_id,
                            replayed=failed.replayed,
                            tool_id="implementation-runtime",
                        )
                    )
                    return AutonomyResult(
                        run=failed.run,
                        stop_reason=AutonomyStopReason.IMPLEMENTATION_FAILED,
                        steps=tuple(steps),
                    )
                steps.append(
                    AutonomyStep(
                        stage=stage.value,
                        outcome="PASSED",
                        attempt_id=implementation.operation.attempt_id,
                        replayed=implementation.operation.replayed,
                        tool_id="safe-source-implementation-v1",
                    )
                )
                continue

            if stage in {WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY}:
                stage_key = self._stage_key(operation_key, stage, run.revision)
                spec = self.registry.spec_for(stage, operation_key=stage_key)
                execution_contract: ExecutionContract | None = None
                try:
                    accepted_lineage = self._accepted_implementation_lineage(run)
                except ValidationProfileError as exc:
                    evidence = self._execution_contract_failure_evidence(spec, exc.code)
                else:
                    evidence = None
                if evidence is None and accepted_lineage is not None:
                    if self.lineage_executor is None:
                        return AutonomyResult(
                            run=run,
                            stop_reason=AutonomyStopReason.LINEAGE_EXECUTOR_REQUIRED,
                            steps=tuple(steps),
                        )
                    try:
                        execution_contract = self._plan_bound_execution_contract(run, accepted_lineage)
                    except ValidationProfileError as exc:
                        evidence = self._execution_contract_failure_evidence(spec, exc.code)
                    else:
                        evidence = self.lineage_executor.execute_on_lineage(
                            spec,
                            project_ref=accepted_lineage.project_ref,
                            run_id=run.id,
                            source_lineage_ref=accepted_lineage.source_lineage_ref,
                            execution_contract=execution_contract,
                        )
                    # These identities are server-owned. Any executor-provided
                    # values are overwritten rather than trusted.
                    evidence["project_ref"] = accepted_lineage.project_ref
                    evidence["source_lineage_ref"] = accepted_lineage.source_lineage_ref
                    evidence["lineage_bound_execution"] = True
                elif evidence is None:
                    # Wave 1 / pre-lineage runs preserve their existing executor
                    # behavior. #61 only tightens runs that accepted IMPLEMENT
                    # lineage evidence.
                    evidence = self.executor.execute(spec)

                acceptance_ids = sorted(item["id"] for item in self.service.acceptance_map_for_run(run))
                if stage is WorkflowStage.BUILD:
                    evidence["acceptance_ids_targeted"] = acceptance_ids
                elif (
                    execution_contract is not None
                    and execution_contract.contract_id is ExecutionContractCode.STATIC_WEB
                    and execution_contract.binding_reason is ExecutionBindingReason.GREENFIELD_STATIC_WEB
                ):
                    evidence["acceptance_verification_scope"] = STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE
                    evidence["acceptance_ids_targeted"] = acceptance_ids
                    evidence["acceptance_ids_verified"] = []
                    evidence["acceptance_ids_unverified"] = acceptance_ids
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

        run = self.service.get(run_id)
        terminal_reason = self._stop_reason(WorkflowStage(run.state))
        return AutonomyResult(
            run=run,
            stop_reason=terminal_reason or AutonomyStopReason.MAX_STEPS_REACHED,
            steps=tuple(steps),
        )

    @staticmethod
    def _stage_key(operation_key: str, stage: WorkflowStage, revision: int) -> str:
        suffix = f":{stage.value.lower()}:{revision}"
        return f"{operation_key[: max(1, 160 - len(suffix))]}{suffix}"

    @staticmethod
    def _accepted_implementation_lineage(run: EngineeringRun) -> _AcceptedImplementationLineage | None:
        for attempt_index in range(len(run.attempts) - 1, -1, -1):
            attempt = run.attempts[attempt_index]
            if attempt.stage != WorkflowStage.IMPLEMENT.value or attempt.status != "PASSED":
                continue
            try:
                evidence = json.loads(attempt.evidence_json)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT) from exc
            project_ref = evidence.get("project_ref")
            base_source_lineage_ref = evidence.get("base_source_lineage_ref")
            source_lineage_ref = evidence.get("source_lineage_ref")
            if project_ref is None and base_source_lineage_ref is None and source_lineage_ref is None:
                # Historical pre-lineage IMPLEMENT evidence retains its legacy
                # executor path. A partially present lineage envelope is drift.
                return None
            if (
                isinstance(project_ref, str)
                and project_ref
                and isinstance(base_source_lineage_ref, str)
                and base_source_lineage_ref
                and isinstance(source_lineage_ref, str)
                and source_lineage_ref
            ):
                return _AcceptedImplementationLineage(
                    project_ref=project_ref,
                    base_source_lineage_ref=base_source_lineage_ref,
                    source_lineage_ref=source_lineage_ref,
                    attempt_index=attempt_index,
                )
            raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
        return None

    @staticmethod
    def _plan_bound_execution_contract(
        run: EngineeringRun,
        lineage: _AcceptedImplementationLineage,
    ) -> ExecutionContract:
        if lineage.project_ref != run.project_id:
            raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
        for attempt in reversed(run.attempts[: lineage.attempt_index]):
            if attempt.stage != WorkflowStage.PLAN.value or attempt.status != "PASSED":
                continue
            try:
                evidence = json.loads(attempt.evidence_json)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT) from exc
            if not isinstance(evidence, dict):
                raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
            expected = {
                "project_id": run.project_id,
                "run_id": run.id,
                "work_specification_id": run.work_specification_id,
                "work_specification_revision": run.work_specification_revision,
                "work_specification_digest": run.work_specification_digest,
                "base_source_lineage_ref": lineage.base_source_lineage_ref,
            }
            if any(evidence.get(key) != value for key, value in expected.items()):
                raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT)
            return ExecutionContractIdentity.from_evidence(evidence).resolve()
        raise ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_UNAVAILABLE)

    @staticmethod
    def _execution_contract_failure_evidence(
        spec: ExecutionSpec,
        reason: ValidationProfileReason,
    ) -> dict[str, object]:
        code = reason.value
        return {
            "tool_id": spec.tool_id,
            "exit_code": None,
            "duration_ms": 0,
            "stdout_excerpt": "",
            "stderr_excerpt": code,
            "stderr_digest": sha256(code.encode("utf-8")).hexdigest(),
            "protected_success": False,
            "executor": "same-lineage-contract-admission",
            "network_policy": "not-created",
            "persistent": False,
            "execution_contract_reason": code,
            "lineage_source_transfer": False,
            "execution_snapshot_verified": False,
            "mutation_applied": False,
            "source_lineage_accepted": False,
            "git_mutated": False,
            "production_deployed": False,
            "review_completed": False,
        }

    @staticmethod
    def _stop_reason(stage: WorkflowStage) -> AutonomyStopReason | None:
        reasons = {
            WorkflowStage.REVIEW: AutonomyStopReason.REVIEW_REQUIRED,
            WorkflowStage.PAUSED: AutonomyStopReason.PAUSED,
            WorkflowStage.FAILED: AutonomyStopReason.FAILED,
            WorkflowStage.COMPLETE: AutonomyStopReason.COMPLETE,
            WorkflowStage.CANCELLED: AutonomyStopReason.CANCELLED,
            WorkflowStage.SPEC_AMENDMENT: AutonomyStopReason.SPEC_AMENDMENT,
        }
        return reasons.get(stage)
