from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from ..code.autonomy import AutonomyStopReason
from ..code.domain import WorkflowStage
from ..code.implementation_runtime import ImplementationRuntimeResult
from ..code.worker_recovery import (
    RecoveryAction,
    StallClassification,
    WorkerCheckpoint,
    WorkerLifecycleState,
    WorkerStaleLease,
    WorkerStallEvidence,
)
from ..code.worker_service import WorkerRecoveryService
from .app_builder import AppBuilderBenchmarkSuite, AppBuilderEvaluationReport
from .reference_app import (
    ReferenceDeliveryDriver,
    ReferenceRuntimeContext,
    ReferenceLoopError,
)
from .runtime_evidence import PersistedVerifiedDelivery, RuntimeEvidenceSnapshot


@dataclass(slots=True)
class Wave3ReferenceRuntimeContext(ReferenceRuntimeContext):
    worker_recovery: WorkerRecoveryService


class Wave3ReferenceRuntimeFactory(Protocol):
    def open(self) -> Wave3ReferenceRuntimeContext: ...


@dataclass(frozen=True, slots=True)
class Wave3RecoveryEvidence:
    execution_id: str
    original_generation: int
    replacement_generation: int
    process_loss_classification: str
    recovery_action: str
    stale_worker_rejected: bool
    checkpoint_lineage_ref: str
    no_manual_run_resume: bool


@dataclass(frozen=True, slots=True)
class Wave3ReferenceAppResult:
    run_id: str
    source_lineage_ref: str
    delivery: PersistedVerifiedDelivery
    evidence_snapshot: RuntimeEvidenceSnapshot
    evaluation: AppBuilderEvaluationReport
    review_state: str
    recovery: Wave3RecoveryEvidence

    @property
    def ready_for_production_promotion(self) -> bool:
        return self.review_state == "COMPLETE" and self.evaluation.protected_pass

    @property
    def production_deployed(self) -> bool:
        return False


class ProtectedWave3ReferenceAppHarness:
    """Permanent Wave 3 reference route using accepted Wave 2 + Wave 3 authorities.

    This coordinator does not mutate source, publish to providers, score a
    candidate, or fabricate worker ownership itself. Those operations stay
    behind the existing protected implementation, delivery, evaluation and
    P2-V0.16.1 worker-recovery services supplied by the runtime factory.
    """

    def __init__(
        self,
        runtime_factory: Wave3ReferenceRuntimeFactory,
        delivery_driver: ReferenceDeliveryDriver,
        suite: AppBuilderBenchmarkSuite,
        *,
        reference_epoch: datetime | None = None,
    ) -> None:
        self.runtime_factory = runtime_factory
        self.delivery_driver = delivery_driver
        self.suite = suite
        self.reference_epoch = reference_epoch or datetime(2099, 8, 23, 20, 0, tzinfo=timezone.utc)
        if self.reference_epoch.tzinfo is None:
            raise ValueError("reference_epoch must be timezone-aware")

    def _checkpoint(self, run, lineage_id: str, *, step: str) -> WorkerCheckpoint:
        if not run.project_id or not run.work_specification_id or run.work_specification_revision is None or not run.work_specification_digest:
            raise ReferenceLoopError("Wave 3 worker checkpoint lacks canonical Project/Work Specification binding")
        return WorkerCheckpoint(
            project_id=run.project_id,
            run_id=run.id,
            work_specification_id=run.work_specification_id,
            work_specification_revision=run.work_specification_revision,
            work_specification_digest=run.work_specification_digest,
            plan_ref="spec:P2-V0.16.5",
            current_step=step,
            source_lineage_ref=lineage_id,
            last_known_good_lineage_ref=lineage_id,
            evidence_refs=("reference:accepted-lineage",),
            dependencies=("gate:browser", "gate:delivery", "gate:evaluation"),
        )

    def run(
        self,
        *,
        run_id: str,
        operation_key: str,
        candidate_version: str,
        operator_ref: str,
    ) -> Wave3ReferenceAppResult:
        if not operation_key or len(operation_key) > 100:
            raise ValueError("reference operation_key must be bounded")
        if not operator_ref or len(operator_ref) > 128 or any(ord(ch) < 33 for ch in operator_ref):
            raise ValueError("operator_ref must be a bounded opaque identity")

        # Process 1: protected PLAN and canonical Project binding.
        context = self.runtime_factory.open()
        try:
            run = context.service.get(run_id)
            if WorkflowStage(run.state) is WorkflowStage.PLAN:
                acceptance = sorted(item["id"] for item in context.service.acceptance_map_for_run(run))
                planned = context.service.complete_stage(
                    run_id=run.id,
                    stage=WorkflowStage.PLAN,
                    operation_key=f"{operation_key}:plan",
                    expected_revision=run.revision,
                    passed=True,
                    evidence={
                        "acceptance_ids_covered": acceptance,
                        "work_items": [
                            {"acceptance_id": item, "action": "satisfy protected Wave 3 reference acceptance"}
                            for item in acceptance
                        ],
                        "validation_checks": [
                            {"acceptance_id": item, "check": "verify protected Wave 3 reference acceptance"}
                            for item in acceptance
                        ],
                        "reference_harness": "P2-V0.16.5",
                    },
                    program_id="protected-wave3-reference-plan-v0.16.5",
                )
                run = planned.run
            if WorkflowStage(run.state) is not WorkflowStage.IMPLEMENT:
                raise ReferenceLoopError("Wave 3 reference run must enter IMPLEMENT after protected PLAN")
            project_id = run.project_id
            if not isinstance(project_id, str) or not project_id:
                raise ReferenceLoopError("Wave 3 reference run lacks canonical Project identity")
            project = (
                context.service.projects.get_for_owner(project_id, context.service.owner_subject or "")
                if context.service.projects
                else None
            )
            if project is None or not project.repository_ref:
                raise ReferenceLoopError("Wave 3 reference run lacks owner-scoped Project repository binding")
            repository_ref = project.repository_ref
        finally:
            context.close()

        # Bootstrap retry must return the same durable root lineage.
        initial_lineage = self.delivery_driver.ensure_bootstrap(
            project_id=project_id,
            run_id=run_id,
            repository_ref=repository_ref,
        )
        replayed_initial = self.delivery_driver.ensure_bootstrap(
            project_id=project_id,
            run_id=run_id,
            repository_ref=repository_ref,
        )
        if replayed_initial != initial_lineage:
            raise ReferenceLoopError("repository bootstrap retry changed accepted initial lineage")

        # Process 2: typed IMPLEMENT mutation.
        context = self.runtime_factory.open()
        implementation: ImplementationRuntimeResult
        try:
            run = context.service.get(run_id)
            implementation = context.implementation_runtime.execute(
                run_id=run.id,
                operation_key=f"{operation_key}:implement",
                expected_revision=run.revision,
            )
            if implementation.operation.replayed:
                raise ReferenceLoopError("first Wave 3 reference IMPLEMENT unexpectedly replayed")
            source_lineage_ref = implementation.source_lineage_ref
        finally:
            context.close()

        # Process 3: exact IMPLEMENT replay, then acquire/checkpoint the sole
        # accepted worker execution before simulated process loss.
        context = self.runtime_factory.open()
        try:
            current = context.service.get(run_id)
            replay = context.implementation_runtime.execute(
                run_id=current.id,
                operation_key=f"{operation_key}:implement",
                expected_revision=current.revision,
            )
            if not replay.operation.replayed or replay.source_lineage_ref != source_lineage_ref:
                raise ReferenceLoopError("recreated IMPLEMENT did not replay the durable accepted result")
            current = context.service.get(run_id)
            if WorkflowStage(current.state) is not WorkflowStage.BUILD:
                raise ReferenceLoopError("accepted IMPLEMENT did not advance to BUILD")
            original_lease = context.worker_recovery.acquire(
                run_id=run_id,
                now=self.reference_epoch,
                lease_seconds=5,
            )
            checkpoint = self._checkpoint(current, source_lineage_ref, step="BUILD")
            context.worker_recovery.checkpoint(
                original_lease,
                checkpoint,
                authoritative_source_lineage_ref=source_lineage_ref,
                state=WorkerLifecycleState.CHECKPOINTED,
                now=self.reference_epoch + timedelta(seconds=1),
                lease_seconds=5,
            )
        finally:
            context.close()

        # Process 4: the prior process is gone. A recreated worker service must
        # classify lease expiry/process loss, recover, reassign the same durable
        # execution, and reject the old lease generation. No Engineering Run
        # pause/resume shortcut is used.
        context = self.runtime_factory.open()
        try:
            expired_at = self.reference_epoch + timedelta(seconds=6)
            health = context.worker_recovery.health(run_id=run_id, now=expired_at)
            if health.lease_status != "EXPIRED":
                raise ReferenceLoopError("simulated worker lease did not expire")
            decision = context.worker_recovery.classify_and_stall(
                run_id=run_id,
                evidence=WorkerStallEvidence(process_lost=True),
                blocker_code="PROCESS_LOST",
                now=expired_at,
            )
            if decision.classification is not StallClassification.PROCESS_LOSS or decision.action is not RecoveryAction.REASSIGN:
                raise ReferenceLoopError("process loss did not select the accepted reassignment path")
            recovering = context.worker_recovery.begin_recovery(
                run_id=run_id,
                now=expired_at + timedelta(seconds=1),
            )
            if recovering.state != WorkerLifecycleState.RECOVERING.value:
                raise ReferenceLoopError("worker did not enter RECOVERING")
            replacement_lease = context.worker_recovery.reassign(
                run_id=run_id,
                now=expired_at + timedelta(seconds=2),
                lease_seconds=30,
            )
            if (
                replacement_lease.execution_id != original_lease.execution_id
                or replacement_lease.generation != original_lease.generation + 1
            ):
                raise ReferenceLoopError("worker reassignment changed execution identity or generation contract")
            stale_worker_rejected = False
            try:
                context.worker_recovery.checkpoint(
                    original_lease,
                    checkpoint,
                    authoritative_source_lineage_ref=source_lineage_ref,
                    now=expired_at + timedelta(seconds=3),
                )
            except WorkerStaleLease:
                stale_worker_rejected = True
            if not stale_worker_rejected:
                raise ReferenceLoopError("stale worker generation retained mutation/checkpoint authority")
            resumed = context.service.get(run_id)
            replacement_checkpoint = self._checkpoint(resumed, source_lineage_ref, step="BUILD")
            context.worker_recovery.checkpoint(
                replacement_lease,
                replacement_checkpoint,
                authoritative_source_lineage_ref=source_lineage_ref,
                state=WorkerLifecycleState.PROGRESSING,
                now=expired_at + timedelta(seconds=3),
                lease_seconds=30,
            )
            autonomy = context.autonomy.run(
                run_id=run_id,
                operation_key=f"{operation_key}:autonomy",
                expected_revision=resumed.revision,
            )
            if autonomy.stop_reason is not AutonomyStopReason.REVIEW_REQUIRED:
                raise ReferenceLoopError("recovered Wave 3 runtime did not reach operator REVIEW ceiling")
        finally:
            context.close()

        # Provider delivery retry must reuse exact external identities.
        first_delivery = self.delivery_driver.deliver_verified_source(
            project_id=project_id,
            run_id=run_id,
            lineage_id=source_lineage_ref,
        )
        replayed_delivery = self.delivery_driver.deliver_verified_source(
            project_id=project_id,
            run_id=run_id,
            lineage_id=source_lineage_ref,
        )
        if (
            replayed_delivery.published_revision != first_delivery.published_revision
            or replayed_delivery.pull_request_identity != first_delivery.pull_request_identity
            or replayed_delivery.preview_deployment_id != first_delivery.preview_deployment_id
            or not replayed_delivery.publication_replayed
        ):
            raise ReferenceLoopError("verified-source publication retry was not idempotent")

        # Process 5: derive persisted evidence, run unchanged protected scoring,
        # and require explicit operator REVIEW. No production action exists here.
        context = self.runtime_factory.open()
        try:
            snapshot = context.evidence_adapter.snapshot(run_id)
            evaluation = context.evidence_adapter.evaluate(
                self.suite,
                snapshot,
                candidate_version=candidate_version,
                model_id=implementation.model_id,
            )
            if not evaluation.protected_pass:
                raise ReferenceLoopError("unchanged AppBuilder protected evaluation rejected Wave 3 reference runtime")
            before_review = context.service.get(run_id)
            if WorkflowStage(before_review.state) is not WorkflowStage.REVIEW:
                raise ReferenceLoopError("provider/evaluation success bypassed the operator REVIEW ceiling")
            acceptance = sorted(item["id"] for item in context.service.acceptance_map_for_run(before_review))
            review = context.service.complete_stage(
                run_id=run_id,
                stage=WorkflowStage.REVIEW,
                operation_key=f"{operation_key}:operator-review",
                expected_revision=before_review.revision,
                passed=True,
                evidence={
                    "recommendation": "PASS",
                    "acceptance_ids_verified": acceptance,
                    "workspace_digest": snapshot.implementation_workspace_digest,
                    "claims": ["preview-evaluated", "operator-reviewed", "wave3-recovery-proved"],
                    "operator_ref": operator_ref,
                    "app_builder_report_id": evaluation.report_id,
                    "app_builder_evidence_digest": evaluation.input_evidence_digest,
                },
                program_id="operator-review-v0.16.5",
            )
            if WorkflowStage(review.run.state) is not WorkflowStage.COMPLETE:
                raise ReferenceLoopError("explicit operator REVIEW did not complete the Wave 3 reference run")
            terminal_checkpoint = self._checkpoint(review.run, source_lineage_ref, step="REVIEW")
            context.worker_recovery.checkpoint(
                replacement_lease,
                terminal_checkpoint,
                authoritative_source_lineage_ref=source_lineage_ref,
                state=WorkerLifecycleState.SUCCEEDED,
                now=self.reference_epoch + timedelta(seconds=12),
            )
        finally:
            context.close()

        recovery = Wave3RecoveryEvidence(
            execution_id=original_lease.execution_id,
            original_generation=original_lease.generation,
            replacement_generation=replacement_lease.generation,
            process_loss_classification=StallClassification.PROCESS_LOSS.value,
            recovery_action=RecoveryAction.REASSIGN.value,
            stale_worker_rejected=stale_worker_rejected,
            checkpoint_lineage_ref=source_lineage_ref,
            no_manual_run_resume=True,
        )
        return Wave3ReferenceAppResult(
            run_id=run_id,
            source_lineage_ref=source_lineage_ref,
            delivery=replayed_delivery,
            evidence_snapshot=snapshot,
            evaluation=evaluation,
            review_state=review.run.state,
            recovery=recovery,
        )


__all__ = [
    "ProtectedWave3ReferenceAppHarness",
    "Wave3RecoveryEvidence",
    "Wave3ReferenceAppResult",
    "Wave3ReferenceRuntimeContext",
    "Wave3ReferenceRuntimeFactory",
]
