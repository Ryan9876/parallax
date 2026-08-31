from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
import logging
from typing import Callable

from ..intelligence.implementation_generation import (
    ImplementationGenerationFailure,
    ImplementationGenerationRequest,
    ImplementationProposal,
    validate_implementation_proposal,
)
from ..intelligence.router import AttemptRecord, RoutingFailureKind
from .agent_protocol import AgentLifecycleStatus, AgentSourceContext
from .agent_team_orchestration import (
    AssignmentEvidence,
    OrchestrationDisposition,
    TeamPlan,
    admit_assignment_result,
    create_agent_task_request,
    observe_admitted_result,
    schedule_team_plan,
)
from .agentic_runtime import (
    AgenticRuntimeError,
    CandidateValidationExecutor,
    HostedImplementationAgent,
)
from .agentic_runtime_live import (
    DurableCandidateArtifactStore,
    LiveAgenticControlPlane,
)
from .lineage_persistence import ImmutableObjectStore
from .runtime_composition import DurableLineageAllocator, EngineeringRuntimeComposition
from .service import EngineeringRunService
from .worker_recovery import WorkerLifecycleState, WorkerStallEvidence, WorkerRecoveryError


CANDIDATE_RECOVERY_VERSION = "candidate-recovery-v0.23.24"
CANDIDATE_GENERATION_EXHAUSTED = "CANDIDATE_GENERATION_EXHAUSTED"
CANDIDATE_VALIDATION_REPAIR = "CANDIDATE_VALIDATION_REPAIR"
MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT = 1
_CANDIDATE_EXHAUSTED_BLOCKER = "AGENTIC_CANDIDATE_EXHAUSTED"
_FINAL_VALIDATOR_REPAIR_CONTEXT_DOMAIN = "parallax-final-validator-repair-context-v1"
_FINAL_VALIDATOR_REPAIR_CONTEXT_TOKEN_HEX = 24
logger = logging.getLogger(__name__)
VALIDATOR_REPAIR_GUIDANCE = (
    "The previous admitted candidate produced a parsed proposal but the server-owned safe proposal validator rejected it. "
    "Repair the proposal without changing the approved objective or acceptance criteria. Use only the supplied protected "
    "source context. For every existing target, copy the exact path and lowercase SHA-256 from source context; for a new "
    "file, bind to the SHA-256 of empty content. Emit one patch per target. Every unified diff must be strict single-file "
    "form with headers exactly matching the declared path (`--- a/path` and `+++ b/path`, or `--- /dev/null` for a new "
    "file), exact hunk coordinates and counts, and removed/context lines copied exactly from the supplied source text. "
    "Do not emit multi-file diffs, duplicate targets, unsupported or binary-prone paths, secret material, or no-op patches."
)
FINAL_VALIDATOR_REPAIR_GUIDANCE = (
    "This is the single final validator-repair generation for this work unit. "
    "Re-derive a fresh proposal from the supplied protected source context instead of reusing or repeating any prior response. "
    "Re-check every target path, base SHA-256, unified diff header, hunk coordinate and count, and every removed/context line "
    "against the supplied source before returning the proposal."
)
_BOUNDED_ROUTING_FAILURES = frozenset(item.value for item in RoutingFailureKind)


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    work_unit_id: str
    agent_identity_digest: str
    generation: int
    failure_kind: str | None = None
    validator_repair_attempt: bool = False

    def as_dict(self) -> dict[str, object]:
        evidence: dict[str, object] = {
            "work_unit_id": self.work_unit_id,
            "agent_identity_digest": self.agent_identity_digest,
            "generation": self.generation,
            "canonical_source_mutated": False,
            "source_lineage_accepted": False,
            "git_mutation": False,
            "deployment_mutation": False,
            "review_completed": False,
            "validator_repair_attempt": self.validator_repair_attempt,
        }
        if self.failure_kind is not None:
            evidence["failure_kind"] = self.failure_kind
        return evidence


def candidate_generation_failure_kind(exc: ImplementationGenerationFailure) -> str | None:
    evidence = exc.diagnostic_evidence
    if not isinstance(evidence, dict):
        return None
    routing = evidence.get("routing_failure")
    if not isinstance(routing, dict):
        return None
    reason = routing.get("reason_code")
    if isinstance(reason, str) and reason in _BOUNDED_ROUTING_FAILURES:
        return reason
    return None


def validator_guided_candidate_request(
    request: ImplementationGenerationRequest,
    failure_kind: str | None,
) -> ImplementationGenerationRequest:
    if failure_kind != RoutingFailureKind.VALIDATION_EXHAUSTED.value:
        return request
    if VALIDATOR_REPAIR_GUIDANCE in request.constraints:
        return request
    return replace(
        request,
        constraints=(*request.constraints, VALIDATOR_REPAIR_GUIDANCE),
    )


def final_validator_repair_context_token(
    *,
    run_revision: int,
    work_unit_id: str,
    generation: int,
) -> str:
    if (
        not isinstance(run_revision, int)
        or isinstance(run_revision, bool)
        or run_revision < 0
    ):
        raise AgenticRuntimeError("final validator repair run revision must be a non-negative integer")
    if (
        not isinstance(generation, int)
        or isinstance(generation, bool)
        or generation < 0
    ):
        raise AgenticRuntimeError("final validator repair generation must be a non-negative integer")
    if (
        not isinstance(work_unit_id, str)
        or not work_unit_id
        or len(work_unit_id) > 180
        or work_unit_id.strip() != work_unit_id
        or any(ord(ch) < 32 for ch in work_unit_id)
    ):
        raise AgenticRuntimeError("final validator repair work-unit identity is invalid")

    payload = json.dumps(
        {
            "domain": _FINAL_VALIDATOR_REPAIR_CONTEXT_DOMAIN,
            "generation": generation,
            "run_revision": run_revision,
            "work_unit_id": work_unit_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()[:_FINAL_VALIDATOR_REPAIR_CONTEXT_TOKEN_HEX]


def final_validator_repair_request(
    request: ImplementationGenerationRequest,
    *,
    run_revision: int,
    work_unit_id: str,
    generation: int,
) -> tuple[ImplementationGenerationRequest, str]:
    guided = validator_guided_candidate_request(
        request,
        RoutingFailureKind.VALIDATION_EXHAUSTED.value,
    )
    context_token = final_validator_repair_context_token(
        run_revision=run_revision,
        work_unit_id=work_unit_id,
        generation=generation,
    )
    final_constraint = (
        f"{FINAL_VALIDATOR_REPAIR_GUIDANCE} "
        f"Server-owned final-repair context token: {context_token}."
    )
    if final_constraint in guided.constraints:
        return guided, context_token
    return (
        replace(
            guided,
            constraints=(*guided.constraints, final_constraint),
        ),
        context_token,
    )


def candidate_recovery_assignment(
    plan: TeamPlan,
    current: AssignmentEvidence,
    *,
    attempted_agent_digests: tuple[str, ...],
    rejection_count: int,
) -> AssignmentEvidence | None:
    """Return the next deterministic admitted agent for candidate generation only.

    This is intentionally separate from worker-loss reassignment. A rejected model
    proposal is not process/lease loss and therefore must not borrow worker-health
    authority. The returned assignment grants no canonical source authority.
    """

    if current.agent_identity_digest is None:
        raise AgenticRuntimeError("candidate recovery requires an assigned work unit")
    if not isinstance(rejection_count, int) or isinstance(rejection_count, bool) or rejection_count < 1:
        raise AgenticRuntimeError("candidate rejection count must be a positive integer")
    if rejection_count > plan.limits.max_reassignments_per_work_unit:
        return None

    unit_plan = plan.unit_plan(current.work_unit_id)
    attempted = set(attempted_agent_digests)
    eligible = tuple(
        digest for digest in unit_plan.eligible_agent_digests
        if digest not in attempted
    )
    if not eligible:
        return None

    next_agent = eligible[0]
    generation = current.generation + 1
    stem = f"{plan.plan_id[:20]}:{current.work_unit_id}:g{generation}"
    return AssignmentEvidence(
        plan_id=plan.plan_id,
        work_unit_id=current.work_unit_id,
        agent_identity_digest=next_agent,
        generation=generation,
        dependency_digest=current.dependency_digest,
        disposition=OrchestrationDisposition.REASSIGNED,
        reason_code="CANDIDATE_GENERATION_RETRY",
        operation_id=f"orchestration:{stem}",
        request_id=f"request:{stem}",
        attempt_id=f"attempt:{stem}",
    )


def validator_repair_assignment(
    plan: TeamPlan,
    current: AssignmentEvidence,
    *,
    validator_rejected_agent_digests: tuple[str, ...],
    repair_count: int,
) -> AssignmentEvidence | None:
    """Return one final deterministic repair assignment after validator rejection.

    This budget is deliberately separate from distinct-agent candidate recovery and
    worker-loss reassignment. It reuses only the most recent already-admitted agent
    that produced a server-classified VALIDATION_EXHAUSTED result, and it never
    grants source, lineage, Git, deployment, or REVIEW authority.
    """

    if current.agent_identity_digest is None:
        raise AgenticRuntimeError("validator repair requires an assigned work unit")
    if not isinstance(repair_count, int) or isinstance(repair_count, bool) or repair_count < 0:
        raise AgenticRuntimeError("validator repair count must be a non-negative integer")
    if repair_count >= MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT:
        return None
    if not validator_rejected_agent_digests:
        return None

    eligible = plan.unit_plan(current.work_unit_id).eligible_agent_digests
    for digest in validator_rejected_agent_digests:
        if digest not in eligible:
            raise AgenticRuntimeError("validator repair identity is outside admitted work-unit agents")
    repair_agent = validator_rejected_agent_digests[-1]
    generation = current.generation + 1
    stem = f"{plan.plan_id[:20]}:{current.work_unit_id}:g{generation}:repair"
    return AssignmentEvidence(
        plan_id=plan.plan_id,
        work_unit_id=current.work_unit_id,
        agent_identity_digest=repair_agent,
        generation=generation,
        dependency_digest=current.dependency_digest,
        disposition=OrchestrationDisposition.REASSIGNED,
        reason_code=CANDIDATE_VALIDATION_REPAIR,
        operation_id=f"orchestration:{stem}",
        request_id=f"request:{stem}",
        attempt_id=f"attempt:{stem}",
    )


class ResilientLiveAgenticControlPlane(LiveAgenticControlPlane):
    """Live control plane with bounded recovery from pre-mutation candidate rejection."""

    def _mark_candidate_exhausted(self, *, run_id: str) -> None:
        try:
            self.worker_bridge.recovery.classify_and_stall(
                run_id=run_id,
                evidence=WorkerStallEvidence(),
                blocker_code=_CANDIDATE_EXHAUSTED_BLOCKER,
            )
        except WorkerRecoveryError:
            return

    def _proposal_for_plan(
        self,
        plan: TeamPlan,
        request: ImplementationGenerationRequest,
        *,
        proposal_validator: Callable[[ImplementationProposal], bool],
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
        rejections: list[CandidateRejection] = []

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
                for scheduled_assignment in ready:
                    if scheduled_assignment.work_unit_id in completed:
                        continue
                    unit = plan.graph.get(scheduled_assignment.work_unit_id)
                    last_unit_id = unit.unit_id
                    assignment = scheduled_assignment
                    attempted_agents: list[str] = []
                    rejection_count = 0
                    validator_rejected_agent_digests: list[str] = []
                    validator_repair_count = 0
                    previous_failure_kind: str | None = None

                    while True:
                        agent_digest = assignment.agent_identity_digest or ""
                        attempted_agents.append(agent_digest)
                        task = create_agent_task_request(
                            plan,
                            assignment,
                            source_context=AgentSourceContext(
                                lineage_id=request.source_context.digest,
                                revision_id=f"source:{request.source_context.digest[:24]}",
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
                        subrequest = validator_guided_candidate_request(
                            subrequest,
                            previous_failure_kind,
                        )
                        if assignment.reason_code == CANDIDATE_VALIDATION_REPAIR:
                            subrequest, repair_context_token = final_validator_repair_request(
                                subrequest,
                                run_revision=run.revision,
                                work_unit_id=unit.unit_id,
                                generation=assignment.generation,
                            )
                            logger.info(
                                "parallax_final_validator_repair_dispatch generation=%s context=%s",
                                assignment.generation,
                                repair_context_token,
                            )
                        adapter = self._adapter(agent_digest)
                        try:
                            result, generation = adapter.generate(
                                task,
                                subrequest,
                                proposal_validator=proposal_validator,
                            )
                        except ImplementationGenerationFailure as exc:
                            rejection_count += 1
                            failure_kind = candidate_generation_failure_kind(exc)
                            rejection = CandidateRejection(
                                work_unit_id=unit.unit_id,
                                agent_identity_digest=agent_digest,
                                generation=assignment.generation,
                                failure_kind=failure_kind,
                                validator_repair_attempt=(
                                    assignment.reason_code == CANDIDATE_VALIDATION_REPAIR
                                ),
                            )
                            rejections.append(rejection)
                            if failure_kind == RoutingFailureKind.VALIDATION_EXHAUSTED.value:
                                validator_rejected_agent_digests.append(agent_digest)
                            lease = self.worker_bridge.checkpoint(
                                lease,
                                plan=plan,
                                work_unit_id=unit.unit_id,
                                source_lineage_ref=lineage.lineage_id,
                                step="CANDIDATE_REJECTED",
                                evidence_refs=(
                                    f"candidate-rejected:{agent_digest}",
                                    f"assignment:{assignment.attempt_id}",
                                ),
                                state=WorkerLifecycleState.PROGRESSING,
                            )
                            replacement = candidate_recovery_assignment(
                                plan,
                                assignment,
                                attempted_agent_digests=tuple(attempted_agents),
                                rejection_count=rejection_count,
                            )
                            repair_selected = False
                            if replacement is None:
                                replacement = validator_repair_assignment(
                                    plan,
                                    assignment,
                                    validator_rejected_agent_digests=tuple(
                                        validator_rejected_agent_digests
                                    ),
                                    repair_count=validator_repair_count,
                                )
                                if replacement is not None:
                                    validator_repair_count += 1
                                    repair_selected = True
                            if replacement is None:
                                self._mark_candidate_exhausted(run_id=run.id)
                                raise ImplementationGenerationFailure(
                                    "all bounded admitted implementation candidates were rejected",
                                    diagnostic_evidence={
                                        "candidate_generation_failure": {
                                            "reason_code": CANDIDATE_GENERATION_EXHAUSTED,
                                            "rejection_count": rejection_count,
                                            "max_reassignments_per_work_unit": plan.limits.max_reassignments_per_work_unit,
                                            "validator_repair_attempted": validator_repair_count > 0,
                                            "validator_repair_count": validator_repair_count,
                                            "validator_repair_limit": MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT,
                                            "rejections": [item.as_dict() for item in rejections],
                                            "canonical_source_mutated": False,
                                            "source_lineage_accepted": False,
                                            "worker_process_loss": False,
                                        }
                                    },
                                )
                            previous_failure_kind = (
                                RoutingFailureKind.VALIDATION_EXHAUSTED.value
                                if repair_selected
                                else failure_kind
                            )
                            assignment = replacement
                            generation_by_work_unit[unit.unit_id] = replacement.generation
                            continue

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
                        break

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
                step="AGENT_PROPOSAL",
                evidence_refs=(f"proposal:{proposal.digest()}",),
            )
            return (
                proposal,
                tuple(attempts),
                tuple(models),
                tuple(result_digests),
                tuple(task_digests),
            )
        except ImplementationGenerationFailure:
            raise
        except Exception:
            self.worker_bridge.stop_bounded(run_id=run.id)
            raise


def build_resilient_live_agentic_runtime_composition(
    service: EngineeringRunService,
    allocator: DurableLineageAllocator,
    legacy_executor,
    *,
    source_delivery=None,
    lineage_executor=None,
    candidate_validator: CandidateValidationExecutor | None = None,
    adapters: tuple[HostedImplementationAgent, ...] | None = None,
    candidate_objects: ImmutableObjectStore | None = None,
    max_steps: int = 8,
) -> EngineeringRuntimeComposition:
    composition = EngineeringRuntimeComposition(
        service,
        allocator,
        legacy_executor,
        lineage_executor=lineage_executor,
        source_delivery=source_delivery,
        max_steps=max_steps,
    )
    control = ResilientLiveAgenticControlPlane(
        service,
        allocator,
        adapters=adapters,
        candidate_validator=candidate_validator,
        candidate_objects=candidate_objects,
    )
    control.implementation_engine = composition.implementation_runtime.implementation_engine
    composition.implementation_runtime.generator = control
    composition.coordinator.plan_runtime = control
    return composition


__all__ = [
    "CANDIDATE_GENERATION_EXHAUSTED",
    "CANDIDATE_RECOVERY_VERSION",
    "CANDIDATE_VALIDATION_REPAIR",
    "MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT",
    "CandidateRejection",
    "FINAL_VALIDATOR_REPAIR_GUIDANCE",
    "ResilientLiveAgenticControlPlane",
    "VALIDATOR_REPAIR_GUIDANCE",
    "build_resilient_live_agentic_runtime_composition",
    "candidate_generation_failure_kind",
    "candidate_recovery_assignment",
    "final_validator_repair_context_token",
    "final_validator_repair_request",
    "validator_guided_candidate_request",
    "validator_repair_assignment",
]
