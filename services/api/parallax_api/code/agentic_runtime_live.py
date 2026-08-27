from __future__ import annotations

from dataclasses import replace

from parallax_api.intelligence.implementation_generation import (
    ImplementationGeneration,
    ImplementationGenerationRequest,
    ImplementationProposal,
    validate_implementation_proposal,
)
from parallax_api.intelligence.router import AttemptRecord

from .agent_protocol import AgentLifecycleStatus, AgentSourceContext
from .agent_team_orchestration import (
    OrchestrationDisposition,
    TeamPlan,
    admit_assignment_result,
    create_agent_task_request,
    observe_admitted_result,
    schedule_team_plan,
)
from .agentic_runtime import (
    AgenticControlPlane,
    AgenticRuntimeError,
    CandidateValidationExecutor,
    HostedImplementationAgent,
)
from .runtime_composition import DurableLineageAllocator, EngineeringRuntimeComposition
from .service import EngineeringRunService
from .worker_recovery import (
    RecoveryAction,
    WorkerCheckpoint,
    WorkerLease,
    WorkerLeaseConflict,
    WorkerLeaseExpired,
    WorkerLifecycleState,
    WorkerRecoveryError,
    WorkerStallEvidence,
)
from .worker_service import WorkerRecoveryService
from ..repositories.worker_executions import WorkerExecutionRepository


class DurableAgentWorkerBridge:
    """Bind live S2 dispatch to the accepted durable worker recovery contract.

    The bridge does not infer provider/model failure as a recoverable process
    loss. Automatic reassignment is permitted only when an existing lease has
    expired or accepted durable worker state already authorizes REASSIGN.
    """

    def __init__(self, service: EngineeringRunService) -> None:
        self.service = service
        self.recovery = WorkerRecoveryService(
            WorkerExecutionRepository(service.runs.session),
            service.runs,
            event_sink=service.event_sink,
        )

    def acquire(self, *, run_id: str) -> WorkerLease:
        try:
            return self.recovery.acquire(run_id=run_id)
        except WorkerLeaseExpired:
            decision = self.recovery.classify_and_stall(
                run_id=run_id,
                evidence=WorkerStallEvidence(process_lost=True),
                blocker_code="AGENTIC_PROCESS_LOSS",
            )
            if decision.action is not RecoveryAction.REASSIGN or decision.human_required:
                raise AgenticRuntimeError("expired agentic worker lease did not admit bounded reassignment")
            self.recovery.begin_recovery(run_id=run_id)
            return self.recovery.reassign(run_id=run_id)
        except WorkerLeaseConflict as exc:
            try:
                health = self.recovery.health(run_id=run_id)
            except WorkerRecoveryError as health_exc:
                raise AgenticRuntimeError("agentic worker lease conflict could not be resolved safely") from health_exc
            if (
                health.state is WorkerLifecycleState.STALLED
                and health.next_recovery_action is RecoveryAction.REASSIGN
                and not health.human_required
            ):
                self.recovery.begin_recovery(run_id=run_id)
                return self.recovery.reassign(run_id=run_id)
            if health.state is WorkerLifecycleState.RECOVERING and not health.human_required:
                return self.recovery.reassign(run_id=run_id)
            raise AgenticRuntimeError("competing or terminal agentic worker execution blocks dispatch") from exc

    def checkpoint(
        self,
        lease: WorkerLease,
        *,
        plan: TeamPlan,
        work_unit_id: str,
        source_lineage_ref: str,
        step: str,
        evidence_refs: tuple[str, ...],
        state: WorkerLifecycleState = WorkerLifecycleState.CHECKPOINTED,
    ) -> WorkerLease:
        run = self.service.get(plan.identity.run_id)
        unit = plan.graph.get(work_unit_id)
        progress = self.recovery.checkpoint(
            lease,
            WorkerCheckpoint(
                project_id=plan.identity.project_id,
                run_id=plan.identity.run_id,
                work_specification_id=plan.identity.work_specification_id,
                work_specification_revision=plan.identity.work_specification_revision,
                work_specification_digest=plan.identity.work_specification_digest,
                plan_ref=f"agentic-plan:{plan.plan_id}",
                current_step=step,
                source_lineage_ref=source_lineage_ref,
                last_known_good_lineage_ref=source_lineage_ref,
                evidence_refs=evidence_refs,
                dependencies=unit.dependencies,
            ),
            authoritative_source_lineage_ref=source_lineage_ref,
            state=state,
        )
        execution = progress.execution
        if execution.lease_owner_id is None or execution.lease_expires_at is None:
            if state not in {
                WorkerLifecycleState.READY_FOR_INTEGRATION,
                WorkerLifecycleState.SUCCEEDED,
                WorkerLifecycleState.FAILED,
            }:
                raise AgenticRuntimeError("agentic worker checkpoint unexpectedly released its lease")
            return lease
        return WorkerLease(
            execution_id=execution.id,
            run_id=execution.run_id,
            owner_id=execution.lease_owner_id,
            generation=int(execution.lease_generation),
            expires_at=execution.lease_expires_at,
        )

    def stop_bounded(self, *, run_id: str) -> None:
        try:
            self.recovery.classify_and_stall(
                run_id=run_id,
                evidence=WorkerStallEvidence(),
                blocker_code="AGENTIC_TASK_FAILED",
            )
        except WorkerRecoveryError:
            # Never replace the original bounded agent/task failure with cleanup
            # noise. The authoritative Engineering Run failure path remains above
            # this non-authoritative worker recovery projection.
            return


class LiveAgenticControlPlane(AgenticControlPlane):
    """Production composition of accepted S1-S5 primitives with durable S6 recovery."""

    def __init__(
        self,
        service: EngineeringRunService,
        allocator: DurableLineageAllocator,
        *,
        adapters: tuple[HostedImplementationAgent, ...] | None = None,
        candidate_validator: CandidateValidationExecutor | None = None,
    ) -> None:
        super().__init__(
            service,
            allocator,
            adapters=adapters,
            candidate_validator=candidate_validator,
        )
        self.worker_bridge = DurableAgentWorkerBridge(service)
        # The base W6-R1 candidate currently has no trustworthy runtime source
        # for material-quality uncertainty. Its hard-coded 0.10 heuristic must
        # therefore never trigger extra candidate spend merely because a team has
        # multiple agents. S5 still evaluates/selects the single validated
        # candidate; future evidence-backed signals can deliberately lower this
        # threshold in a separately governed change.
        self.competition_policy = replace(
            self.competition_policy,
            minimum_expected_quality_gain=1.0,
        )

    def _proposal_for_plan(
        self,
        plan: TeamPlan,
        request: ImplementationGenerationRequest,
        *,
        proposal_validator,
        alternative_round: int,
    ) -> tuple[
        ImplementationProposal,
        tuple[AttemptRecord, ...],
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        run = self.service.get(plan.identity.run_id)
        lineage = self._lineage(run)
        lease = self.worker_bridge.acquire(run_id=run.id)
        generation_by_work_unit = {
            unit.unit_id: lease.generation for unit in plan.graph.units
        }
        completed: set[str] = set()
        patches = []
        covered: list[str] = []
        attempts: list[AttemptRecord] = []
        models: list[str] = []
        result_digests: list[str] = []
        task_digests: list[str] = []
        seen_paths: set[str] = set()
        last_unit_id = plan.graph.units[0].unit_id

        try:
            while len(completed) < len(plan.graph.units):
                schedule = schedule_team_plan(
                    plan,
                    completed_work_units=tuple(completed),
                    generation_by_work_unit=generation_by_work_unit,
                )
                ready = schedule.ready
                if not ready:
                    raise AgenticRuntimeError("agent team schedule made no progress")
                progress = False
                for assignment in ready:
                    if assignment.work_unit_id in completed:
                        continue
                    unit = plan.graph.get(assignment.work_unit_id)
                    last_unit_id = unit.unit_id
                    task = create_agent_task_request(
                        plan,
                        assignment,
                        source_context=AgentSourceContext(
                            lineage_id=request.source_context.content_digest,
                            revision_id=f"source:{request.source_context.content_digest[:24]}",
                        ),
                    )
                    lease = self.worker_bridge.checkpoint(
                        lease,
                        plan=plan,
                        work_unit_id=unit.unit_id,
                        source_lineage_ref=lineage.lineage_id,
                        step="AGENT_DISPATCH",
                        evidence_refs=(
                            f"task:{task.digest}",
                            f"assignment:{assignment.attempt_id}",
                        ),
                        state=WorkerLifecycleState.PROGRESSING,
                    )
                    subrequest = self._subrequest(
                        request,
                        unit.acceptance_ids,
                        alternative_round=alternative_round,
                    )
                    adapter = self._adapter(assignment.agent_identity_digest or "")
                    result, generation = adapter.generate(
                        task,
                        subrequest,
                        proposal_validator=proposal_validator,
                    )
                    admission = admit_assignment_result(
                        plan,
                        assignment,
                        expected_task=task,
                        result=result,
                        current_generation=assignment.generation,
                    )
                    if not admission.admitted:
                        raise AgenticRuntimeError(
                            f"agent result admission failed: {admission.reason_code}"
                        )
                    observe_admitted_result(
                        plan,
                        assignment,
                        admission=admission,
                        result=result,
                    )
                    if result.status is not AgentLifecycleStatus.COMPLETED:
                        raise AgenticRuntimeError(
                            f"admitted agent did not complete work: {result.reason_code}"
                        )
                    if tuple(generation.proposal.acceptance_ids_covered) != unit.acceptance_ids:
                        raise AgenticRuntimeError("agent proposal acceptance ownership drifted")
                    for patch in generation.proposal.patches:
                        if patch.path in seen_paths:
                            raise AgenticRuntimeError(
                                "multi-agent proposal overlap requires human coordination"
                            )
                        seen_paths.add(patch.path)
                        patches.append(patch)
                    covered.extend(unit.acceptance_ids)
                    attempts.extend(generation.attempts)
                    models.append(generation.model)
                    result_digests.append(result.digest)
                    task_digests.append(task.digest)
                    lease = self.worker_bridge.checkpoint(
                        lease,
                        plan=plan,
                        work_unit_id=unit.unit_id,
                        source_lineage_ref=lineage.lineage_id,
                        step="AGENT_RESULT",
                        evidence_refs=(
                            f"task:{task.digest}",
                            f"result:{result.digest}",
                        ),
                    )
                    completed.add(unit.unit_id)
                    progress = True
                if not progress:
                    raise AgenticRuntimeError("agent team schedule stalled without protected progress")

            ordered_coverage = request.required_acceptance_ids
            if set(covered) != set(ordered_coverage) or len(covered) != len(ordered_coverage):
                raise AgenticRuntimeError("agent team did not cover exact protected acceptance contract")
            proposal = ImplementationProposal(
                acceptance_ids_covered=list(ordered_coverage),
                patches=patches,
            )
            if not validate_implementation_proposal(proposal, ordered_coverage):
                raise AgenticRuntimeError("combined agent proposal failed exact acceptance validation")
            self.worker_bridge.checkpoint(
                lease,
                plan=plan,
                work_unit_id=last_unit_id,
                source_lineage_ref=lineage.lineage_id,
                step="AGENT_SELECTED",
                evidence_refs=(f"proposal:{proposal.digest()}",),
            )
            return (
                proposal,
                tuple(attempts),
                tuple(models),
                tuple(result_digests),
                tuple(task_digests),
            )
        except Exception:
            self.worker_bridge.stop_bounded(run_id=run.id)
            raise


def build_live_agentic_runtime_composition(
    service: EngineeringRunService,
    allocator: DurableLineageAllocator,
    legacy_executor,
    *,
    source_delivery=None,
    lineage_executor=None,
    candidate_validator: CandidateValidationExecutor | None = None,
    adapters: tuple[HostedImplementationAgent, ...] | None = None,
) -> EngineeringRuntimeComposition:
    """Attach the release-safe Wave 6 runtime to ordinary Engineering Runs."""

    composition = EngineeringRuntimeComposition(
        service,
        allocator,
        legacy_executor,
        lineage_executor=lineage_executor,
        source_delivery=source_delivery,
    )
    control = LiveAgenticControlPlane(
        service,
        allocator,
        adapters=adapters,
        candidate_validator=candidate_validator,
    )
    # Keep one canonical SafeImplementationEngine instance across candidate
    # preflight and final commit-time validation.
    control.implementation_engine = composition.implementation_runtime.implementation_engine
    composition.implementation_runtime.generator = control
    composition.coordinator.plan_runtime = control
    return composition


__all__ = [
    "DurableAgentWorkerBridge",
    "LiveAgenticControlPlane",
    "build_live_agentic_runtime_composition",
]
