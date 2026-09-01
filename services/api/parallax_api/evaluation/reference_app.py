from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..code.autonomy import AutonomyCoordinator, AutonomyStopReason
from ..code.domain import WorkflowStage
from ..code.implementation_runtime import ImplementationRuntimeResult, ProtectedImplementationRuntime
from ..code.service import EngineeringRunService, RunOperationResult
from .app_builder import AppBuilderBenchmarkSuite, AppBuilderEvaluationReport
from .runtime_evidence import (
    PersistedVerifiedDelivery,
    RuntimeAppBuilderEvidenceAdapter,
    RuntimeEvidenceSnapshot,
    VerifiedSourceDeliveryReader,
)


class ReferenceLoopError(RuntimeError):
    pass


class ReferenceDeliveryDriver(VerifiedSourceDeliveryReader, Protocol):
    """Provisional #79 driver seam used only by the protected reference harness."""

    def ensure_bootstrap(
        self,
        *,
        project_id: str,
        run_id: str,
        repository_ref: str,
    ) -> str: ...

    def deliver_verified_source(
        self,
        *,
        project_id: str,
        run_id: str,
        lineage_id: str,
    ) -> PersistedVerifiedDelivery: ...


@dataclass(slots=True)
class ReferenceRuntimeContext:
    service: EngineeringRunService
    implementation_runtime: ProtectedImplementationRuntime
    autonomy: AutonomyCoordinator
    evidence_adapter: RuntimeAppBuilderEvidenceAdapter

    def close(self) -> None:
        """Override when a factory owns a request-scoped Session/resources."""


class ReferenceRuntimeFactory(Protocol):
    def open(self) -> ReferenceRuntimeContext: ...


@dataclass(frozen=True, slots=True)
class ReferenceAppResult:
    run_id: str
    source_lineage_ref: str
    delivery: PersistedVerifiedDelivery
    evidence_snapshot: RuntimeEvidenceSnapshot
    evaluation: AppBuilderEvaluationReport
    review: RunOperationResult


class ProtectedReferenceAppHarness:
    """Prove the Wave 2 app-builder path across recreated runtime contexts.

    The harness has no provider or release authority of its own. Bootstrap and
    verified-source delivery remain behind the narrow #79 driver; all stage
    transitions remain protected by the existing EngineeringRunService and #61
    runtime; all evaluation remains owned by the unchanged #46 evaluator.
    """

    def __init__(
        self,
        runtime_factory: ReferenceRuntimeFactory,
        delivery_driver: ReferenceDeliveryDriver,
        suite: AppBuilderBenchmarkSuite,
    ) -> None:
        self.runtime_factory = runtime_factory
        self.delivery_driver = delivery_driver
        self.suite = suite

    def run(
        self,
        *,
        run_id: str,
        operation_key: str,
        candidate_version: str,
        operator_ref: str,
    ) -> ReferenceAppResult:
        if not operation_key or len(operation_key) > 100:
            raise ValueError("reference operation_key must be bounded")
        if not operator_ref or len(operator_ref) > 128 or any(ord(ch) < 33 for ch in operator_ref):
            raise ValueError("operator_ref must be a bounded opaque identity")

        # Request/runtime composition 1: resolve canonical Project binding. The
        # initial accepted lineage is bootstrapped before PLAN because PLAN now
        # binds the immutable execution contract from that exact lineage.
        context = self.runtime_factory.open()
        try:
            run = context.service.get(run_id)
            if WorkflowStage(run.state) is not WorkflowStage.PLAN:
                raise ReferenceLoopError("reference run must begin at protected PLAN")
            project_id = run.project_id
            if not isinstance(project_id, str) or not project_id:
                raise ReferenceLoopError("reference run lacks canonical Project identity")
            project = context.service.projects.get_for_owner(project_id, context.service.owner_subject or "") if context.service.projects else None
            if project is None or not project.repository_ref:
                raise ReferenceLoopError("reference run lacks owner-scoped Project repository binding")
            repository_ref = project.repository_ref
        finally:
            context.close()

        # #79 bootstrap is the only source initialization seam. Repeating it
        # after process recreation must return the same accepted initial lineage.
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

        # Request/runtime composition 2: bind the exact execution contract at
        # protected PLAN through the configured server-owned plan runtime.
        context = self.runtime_factory.open()
        try:
            run = context.service.get(run_id)
            plan_runtime = context.autonomy.plan_runtime
            if plan_runtime is None:
                raise ReferenceLoopError("reference runtime lacks PLAN-bound execution-contract authority")
            plan_key = f"{operation_key}:plan"
            evidence = plan_runtime.plan(run=run, operation_key=plan_key)
            planned = context.service.complete_stage(
                run_id=run.id,
                stage=WorkflowStage.PLAN,
                operation_key=plan_key,
                expected_revision=run.revision,
                passed=True,
                evidence=evidence,
                program_id=plan_runtime.program_id,
            )
            if WorkflowStage(planned.run.state) is not WorkflowStage.IMPLEMENT:
                raise ReferenceLoopError("reference run must enter IMPLEMENT after protected PLAN")
        finally:
            context.close()

        # Request/runtime composition 3: typed generation -> safe mutation -> durable lineage.
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
                raise ReferenceLoopError("first reference IMPLEMENT unexpectedly replayed")
            source_lineage_ref = implementation.source_lineage_ref
        finally:
            context.close()

        # Request/runtime composition 4: exact IMPLEMENT replay must not mutate again.
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

            # Persist a real interruption boundary after mutation. Resume is done
            # by a new context so interruption/recovery evidence is durable.
            paused = context.service.pause(
                run_id=current.id,
                operation_key=f"{operation_key}:pause",
                expected_revision=current.revision,
            )
            if WorkflowStage(paused.run.state) is not WorkflowStage.PAUSED:
                raise ReferenceLoopError("reference interruption did not persist PAUSED state")
        finally:
            context.close()

        # Request/runtime composition 5: resume, exact-lineage BUILD/TEST/VERIFY.
        context = self.runtime_factory.open()
        try:
            paused = context.service.get(run_id)
            resumed = context.service.resume(
                run_id=paused.id,
                operation_key=f"{operation_key}:resume",
                expected_revision=paused.revision,
            )
            if WorkflowStage(resumed.run.state) is not WorkflowStage.BUILD:
                raise ReferenceLoopError("reference recovery did not resume at BUILD")
            autonomy = context.autonomy.run(
                run_id=run_id,
                operation_key=f"{operation_key}:autonomy",
                expected_revision=resumed.run.revision,
            )
            if autonomy.stop_reason is not AutonomyStopReason.REVIEW_REQUIRED:
                raise ReferenceLoopError("reference runtime did not reach operator REVIEW ceiling")
        finally:
            context.close()

        # Provider/delivery composition is recreated by the caller's #79 driver.
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

        # Request/runtime composition 6: derive observable evidence from durable facts.
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
                raise ReferenceLoopError("unchanged #46 protected evaluation rejected reference runtime")
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
                    "claims": ["preview-evaluated", "operator-reviewed"],
                    "operator_ref": operator_ref,
                    "app_builder_report_id": evaluation.report_id,
                    "app_builder_evidence_digest": evaluation.input_evidence_digest,
                },
                program_id="operator-review-v0.15.10",
            )
            if WorkflowStage(review.run.state) is not WorkflowStage.COMPLETE:
                raise ReferenceLoopError("explicit operator REVIEW did not complete the protected run")
        finally:
            context.close()

        return ReferenceAppResult(
            run_id=run_id,
            source_lineage_ref=source_lineage_ref,
            delivery=replayed_delivery,
            evidence_snapshot=snapshot,
            evaluation=evaluation,
            review=review,
        )


__all__ = [
    "ProtectedReferenceAppHarness",
    "ReferenceAppResult",
    "ReferenceDeliveryDriver",
    "ReferenceLoopError",
    "ReferenceRuntimeContext",
    "ReferenceRuntimeFactory",
]
