from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json

from parallax_api.intelligence.implementation_generation import (
    ImplementationGeneration,
    ImplementationGenerationFailure,
    ImplementationGenerationRequest,
    ImplementationProposal,
    validate_implementation_proposal,
)
from parallax_api.intelligence.router import AttemptRecord

from .agent_protocol import AgentLifecycleStatus, AgentSourceContext
from .agent_team_orchestration import (
    TeamPlan,
    admit_assignment_result,
    create_agent_task_request,
    observe_admitted_result,
    schedule_team_plan,
)
from .agentic_runtime import (
    AGENTIC_RUNTIME_VERSION,
    AgenticControlPlane,
    AgenticRuntimeError,
    CandidateValidationExecutor,
    HostedImplementationAgent,
)
from .lineage_persistence import (
    ImmutableObjectStore,
    ObjectStoreError,
    VercelPrivateBlobObjectStore,
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
from ..models import EngineeringRun
from ..repositories.worker_executions import WorkerExecutionRepository


_CANDIDATE_ARTIFACT_SCHEMA_VERSION = 1
_MAX_CANDIDATE_ARTIFACT_BYTES = 2_500_000
_CANDIDATE_OBJECT_PREFIX = "parallax/agentic-candidates/v1/sha256"


class DurableCandidateArtifactStore:
    """Persist exact selected candidate evidence without accepting source lineage.

    Candidate artifacts are immutable private content-addressed objects. The
    durable worker checkpoint stores only the artifact digest; canonical source
    authority remains exclusively with ProtectedImplementationRuntime and the
    durable lineage allocator.
    """

    def __init__(self, objects: ImmutableObjectStore | None = None) -> None:
        self.objects = objects or VercelPrivateBlobObjectStore(prefix=_CANDIDATE_OBJECT_PREFIX)

    @staticmethod
    def _encode(value: dict[str, object]) -> bytes:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        if len(payload) > _MAX_CANDIDATE_ARTIFACT_BYTES:
            raise AgenticRuntimeError("selected candidate artifact exceeds protected durable bound")
        return payload

    def persist(
        self,
        *,
        generation: ImplementationGeneration,
        controller_evidence: dict[str, object],
        project_ref: str,
        run_id: str,
        work_specification_id: str,
        work_specification_revision: int,
        work_specification_digest: str,
        acceptance_ids: tuple[str, ...],
        plan_id: str,
        base_source_lineage_ref: str,
        base_revision: str,
        source_context_digest: str,
    ) -> str:
        proposal_digest = generation.proposal.digest()
        envelope: dict[str, object] = {
            "schema_version": _CANDIDATE_ARTIFACT_SCHEMA_VERSION,
            "project_ref": project_ref,
            "run_id": run_id,
            "work_specification_id": work_specification_id,
            "work_specification_revision": work_specification_revision,
            "work_specification_digest": work_specification_digest,
            "acceptance_ids": list(acceptance_ids),
            "plan_id": plan_id,
            "base_source_lineage_ref": base_source_lineage_ref,
            "base_revision": base_revision,
            "source_context_digest": source_context_digest,
            "proposal_digest": proposal_digest,
            "proposal": generation.proposal.model_dump(mode="json"),
            "model": generation.model,
            "program_version": generation.program_version,
            "controller_evidence": controller_evidence,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
            "performs_deployment": False,
            "completes_review": False,
        }
        encoded = self._encode(envelope)
        digest = sha256(encoded).hexdigest()
        try:
            self.objects.put_if_absent(digest, encoded)
        except ObjectStoreError as exc:
            raise AgenticRuntimeError("selected candidate artifact could not be persisted durably") from exc
        return digest

    def restore(
        self,
        digest: str,
        *,
        request: ImplementationGenerationRequest,
        project_ref: str,
        run_id: str,
        plan_id: str,
        base_source_lineage_ref: str,
        base_revision: str,
    ) -> tuple[ImplementationGeneration, dict[str, object]]:
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise AgenticRuntimeError("durable candidate artifact reference is invalid")
        try:
            encoded = self.objects.get(digest)
        except ObjectStoreError as exc:
            raise AgenticRuntimeError("durable selected candidate artifact is unavailable") from exc
        if len(encoded) > _MAX_CANDIDATE_ARTIFACT_BYTES or sha256(encoded).hexdigest() != digest:
            raise AgenticRuntimeError("durable selected candidate artifact failed integrity validation")
        try:
            value = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AgenticRuntimeError("durable selected candidate artifact is malformed") from exc
        if not isinstance(value, dict) or value.get("schema_version") != _CANDIDATE_ARTIFACT_SCHEMA_VERSION:
            raise AgenticRuntimeError("durable selected candidate artifact schema is unsupported")

        expected = {
            "project_ref": project_ref,
            "run_id": run_id,
            "work_specification_id": request.work_specification_id,
            "work_specification_revision": request.work_specification_revision,
            "work_specification_digest": request.work_specification_digest,
            "acceptance_ids": list(request.required_acceptance_ids),
            "plan_id": plan_id,
            "base_source_lineage_ref": base_source_lineage_ref,
            "base_revision": base_revision,
            "source_context_digest": request.source_context.digest,
        }
        for key, expected_value in expected.items():
            if value.get(key) != expected_value:
                raise AgenticRuntimeError(f"durable selected candidate drifted at {key}")
        for authority_claim in (
            "accepts_source_lineage",
            "transitions_engineering_run",
            "performs_deployment",
            "completes_review",
        ):
            if value.get(authority_claim) is not False:
                raise AgenticRuntimeError("durable selected candidate asserted authority it does not own")

        try:
            proposal = ImplementationProposal.model_validate(value.get("proposal"))
        except Exception as exc:
            raise AgenticRuntimeError("durable selected candidate proposal is malformed") from exc
        proposal_digest = proposal.digest()
        if value.get("proposal_digest") != proposal_digest:
            raise AgenticRuntimeError("durable selected candidate proposal digest mismatch")
        if not validate_implementation_proposal(proposal, request.required_acceptance_ids):
            raise AgenticRuntimeError("durable selected candidate acceptance contract drifted")
        model = value.get("model")
        program_version = value.get("program_version")
        controller_evidence = value.get("controller_evidence")
        if not isinstance(model, str) or not model or not isinstance(program_version, str) or not program_version:
            raise AgenticRuntimeError("durable selected candidate generation identity is malformed")
        if not isinstance(controller_evidence, dict) or not controller_evidence:
            raise AgenticRuntimeError("durable selected candidate controller evidence is malformed")
        if controller_evidence.get("selected_proposal_digest") != proposal_digest:
            raise AgenticRuntimeError("durable selected candidate controller evidence drifted from proposal")
        return (
            ImplementationGeneration(
                proposal=proposal,
                model=model,
                attempts=(),
                program_version=program_version,
            ),
            dict(controller_evidence),
        )


class DurableAgentWorkerBridge:
    """Bind live S2 dispatch to the accepted durable worker recovery contract.

    The bridge does not infer provider/model failure as a recoverable process
    loss. Automatic reassignment is permitted only when an existing lease has
    expired or accepted durable worker state already authorizes REASSIGN.
    """

    def __init__(
        self,
        service: EngineeringRunService,
        *,
        recovery: WorkerRecoveryService | None = None,
    ) -> None:
        self.service = service
        self.recovery = recovery or WorkerRecoveryService(
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

    def active_lease(self, *, run_id: str) -> WorkerLease:
        execution = self.recovery.executions.get_for_run(run_id)
        if execution is None:
            raise AgenticRuntimeError("agentic worker execution is unavailable")
        if execution.lease_owner_id is None or execution.lease_expires_at is None:
            raise AgenticRuntimeError("agentic worker execution does not retain active mutation lease")
        return WorkerLease(
            execution_id=execution.id,
            run_id=execution.run_id,
            owner_id=execution.lease_owner_id,
            generation=int(execution.lease_generation),
            expires_at=execution.lease_expires_at,
        )

    def selected_candidate_artifact(
        self,
        *,
        run_id: str,
        plan_id: str,
        source_lineage_ref: str,
    ) -> str | None:
        execution = self.recovery.executions.get_for_run(run_id)
        if execution is None or execution.state != WorkerLifecycleState.READY_FOR_INTEGRATION.value:
            return None
        try:
            payload = json.loads(execution.checkpoint_json or "{}")
        except json.JSONDecodeError as exc:
            raise AgenticRuntimeError("durable agentic worker checkpoint is corrupt") from exc
        if not isinstance(payload, dict):
            raise AgenticRuntimeError("durable agentic worker checkpoint is malformed")
        if payload.get("plan_ref") != f"agentic-plan:{plan_id}":
            raise AgenticRuntimeError("durable selected candidate plan identity drifted")
        if payload.get("source_lineage_ref") != source_lineage_ref:
            raise AgenticRuntimeError("durable selected candidate source lineage drifted")
        if payload.get("current_step") != "CANDIDATE_SELECTED":
            raise AgenticRuntimeError("READY_FOR_INTEGRATION worker lacks selected-candidate checkpoint")
        refs = payload.get("evidence_refs")
        if not isinstance(refs, list):
            raise AgenticRuntimeError("durable selected candidate evidence references are malformed")
        candidate_refs = [
            item.removeprefix("candidate:")
            for item in refs
            if isinstance(item, str) and item.startswith("candidate:")
        ]
        if len(candidate_refs) != 1:
            raise AgenticRuntimeError("durable selected candidate checkpoint lacks exact artifact identity")
        digest = candidate_refs[0]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise AgenticRuntimeError("durable selected candidate artifact digest is invalid")
        return digest

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

    def candidate_ready(
        self,
        lease: WorkerLease,
        *,
        plan: TeamPlan,
        source_lineage_ref: str,
        artifact_digest: str,
        proposal_digest: str,
        routing_digest: str,
        competition_digest: str,
    ) -> None:
        self.checkpoint(
            lease,
            plan=plan,
            work_unit_id=plan.graph.units[-1].unit_id,
            source_lineage_ref=source_lineage_ref,
            step="CANDIDATE_SELECTED",
            evidence_refs=(
                f"candidate:{artifact_digest}",
                f"proposal:{proposal_digest}",
                f"routing:{routing_digest}",
                f"competition:{competition_digest}",
            ),
            state=WorkerLifecycleState.READY_FOR_INTEGRATION,
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
        candidate_objects: ImmutableObjectStore | None = None,
    ) -> None:
        super().__init__(
            service,
            allocator,
            adapters=adapters,
            candidate_validator=candidate_validator,
        )
        self.worker_bridge = DurableAgentWorkerBridge(service)
        self.candidate_artifacts = DurableCandidateArtifactStore(candidate_objects)
        # W6-R1 currently has no trustworthy runtime source for material-quality
        # uncertainty. The base controller's 0.10 team heuristic must therefore
        # not trigger extra candidate spend merely because a team has >1 agent.
        # S5 still evaluates/selects the single validated candidate. A future
        # governed evidence source can deliberately change this threshold.
        self.competition_policy = replace(
            self.competition_policy,
            minimum_expected_quality_gain=1.0,
        )

    def plan(
        self,
        *,
        run: EngineeringRun,
        operation_key: str,
    ) -> dict[str, object]:
        """Project S2 planning into the existing protected PLAN contract."""

        evidence = super().plan(run=run, operation_key=operation_key)
        acceptance_ids = tuple(str(value) for value in evidence["acceptance_ids_covered"])
        evidence.update(
            {
                "work_items": [
                    {
                        "acceptance_id": acceptance_id,
                        "action": "dispatch through the admitted bounded agentic work graph",
                    }
                    for acceptance_id in acceptance_ids
                ],
                "validation_checks": [
                    {
                        "acceptance_id": acceptance_id,
                        "check": "require protected deterministic candidate validation and independent evaluation",
                    }
                    for acceptance_id in acceptance_ids
                ],
                "planner": AGENTIC_RUNTIME_VERSION,
                "executor_preflight": "passed",
            }
        )
        return evidence

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
        except Exception:
            self.worker_bridge.stop_bounded(run_id=run.id)
            raise

    def generate_protected(
        self,
        request: ImplementationGenerationRequest,
        *,
        workspace_root,
        project_ref: str,
        run_id: str,
        base_source_lineage_ref: str,
        base_revision: str,
        proposal_validator,
        operation_key: str,
    ) -> tuple[ImplementationGeneration, dict[str, object]]:
        run = self.service.get(run_id)
        if run.project_id != project_ref:
            raise ImplementationGenerationFailure("agentic runtime Project identity mismatch")
        lineage = self._lineage(run)
        if lineage.lineage_id != base_source_lineage_ref:
            raise ImplementationGenerationFailure("agentic runtime base lineage drifted before generation")
        try:
            primary_plan = self._verify_plan_evidence(
                run=run,
                base_source_lineage_ref=base_source_lineage_ref,
                source_content_digest=lineage.content_digest,
            )
            artifact_digest = self.worker_bridge.selected_candidate_artifact(
                run_id=run_id,
                plan_id=primary_plan.plan_id,
                source_lineage_ref=base_source_lineage_ref,
            )
            if artifact_digest is not None:
                generation, evidence = self.candidate_artifacts.restore(
                    artifact_digest,
                    request=request,
                    project_ref=project_ref,
                    run_id=run_id,
                    plan_id=primary_plan.plan_id,
                    base_source_lineage_ref=base_source_lineage_ref,
                    base_revision=base_revision,
                )
                if not proposal_validator(generation.proposal):
                    raise AgenticRuntimeError("durable selected candidate is stale against current protected workspace")
                replay_evidence = dict(evidence)
                replay_evidence["candidate_artifact_digest"] = artifact_digest
                replay_evidence["candidate_artifact_replayed"] = True
                return generation, replay_evidence

            generation, evidence = super().generate_protected(
                request,
                workspace_root=workspace_root,
                project_ref=project_ref,
                run_id=run_id,
                base_source_lineage_ref=base_source_lineage_ref,
                base_revision=base_revision,
                proposal_validator=proposal_validator,
                operation_key=operation_key,
            )
            artifact_digest = self.candidate_artifacts.persist(
                generation=generation,
                controller_evidence=evidence,
                project_ref=project_ref,
                run_id=run_id,
                work_specification_id=request.work_specification_id,
                work_specification_revision=request.work_specification_revision,
                work_specification_digest=request.work_specification_digest,
                acceptance_ids=request.required_acceptance_ids,
                plan_id=primary_plan.plan_id,
                base_source_lineage_ref=base_source_lineage_ref,
                base_revision=base_revision,
                source_context_digest=request.source_context.digest,
            )
            lease = self.worker_bridge.active_lease(run_id=run_id)
            routing_digest = evidence.get("routing_record_digest")
            competition_digest = evidence.get("competition_record_digest")
            if not isinstance(routing_digest, str) or not isinstance(competition_digest, str):
                raise AgenticRuntimeError("selected candidate lacks routing or competition identity")
            self.worker_bridge.candidate_ready(
                lease,
                plan=primary_plan,
                source_lineage_ref=base_source_lineage_ref,
                artifact_digest=artifact_digest,
                proposal_digest=generation.proposal.digest(),
                routing_digest=routing_digest,
                competition_digest=competition_digest,
            )
            durable_evidence = dict(evidence)
            durable_evidence["candidate_artifact_digest"] = artifact_digest
            durable_evidence["candidate_artifact_replayed"] = False
            return generation, durable_evidence
        except ImplementationGenerationFailure:
            raise
        except (AgenticRuntimeError, ValueError, ObjectStoreError) as exc:
            raise ImplementationGenerationFailure(
                "agentic runtime could not establish durable selected-candidate evidence"
            ) from exc


def build_live_agentic_runtime_composition(
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
    """Attach the release-safe Wave 6 runtime to ordinary Engineering Runs."""

    composition = EngineeringRuntimeComposition(
        service,
        allocator,
        legacy_executor,
        lineage_executor=lineage_executor,
        source_delivery=source_delivery,
        max_steps=max_steps,
    )
    control = LiveAgenticControlPlane(
        service,
        allocator,
        adapters=adapters,
        candidate_validator=candidate_validator,
        candidate_objects=candidate_objects,
    )
    # Keep one canonical SafeImplementationEngine instance across candidate
    # preflight and final commit-time validation.
    control.implementation_engine = composition.implementation_runtime.implementation_engine
    composition.implementation_runtime.generator = control
    composition.coordinator.plan_runtime = control
    return composition


__all__ = [
    "DurableAgentWorkerBridge",
    "DurableCandidateArtifactStore",
    "LiveAgenticControlPlane",
    "build_live_agentic_runtime_composition",
]
