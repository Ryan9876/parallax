from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.optimization_controller import (
    AcceptanceAssignment,
    AdaptiveModelRouter,
    CancellationAction,
    ChangeImpactGraph,
    CriticalPathScheduler,
    DependencyGraph,
    DependencyNode,
    DevelopmentPhase,
    EngineeringAttemptOptimizationStateStore,
    FailureFingerprint,
    ImpactRule,
    IntegrationBackpressure,
    ModelClass,
    ModelProfile,
    OptimizationGraphError,
    OptimizationNodeKind,
    OptimizationNodeState,
    OptimizationPolicyError,
    OptimizationState,
    OptimizationStateConflict,
    OptimizationWorkerConflict,
    PathOwnership,
    PhaseObservation,
    PreflightFindingKind,
    RepairMemory,
    RepairMemoryRecord,
    ReusablePatternRecord,
    ReusablePatternRegistry,
    SafeBoundary,
    SpecPreflightRequest,
    SpeculativeIntegrationCandidate,
    ValidationBoundary,
    WarmCacheRecord,
    WarmEnvironmentIdentity,
    WorkstreamSizer,
    WorkstreamSizingProposal,
    apply_work_steal,
    cancellation_decision,
    preflight_spec,
    propose_work_steal,
    summarize_telemetry,
)
from parallax_api.code.worker_recovery import WorkerStallEvidence
from parallax_api.code.worker_service import WorkerRecoveryService
from parallax_api.db import Base, make_engine
from parallax_api.models import EngineeringRun
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.worker_executions import EngineeringWorkerExecution, WorkerExecutionRepository


T0 = datetime(2099, 8, 23, 20, 0, tzinfo=timezone.utc)
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
LINEAGE_A = "src:" + "a" * 64
LINEAGE_B = "src:" + "b" * 64


def _node(
    node_id: str,
    kind: OptimizationNodeKind,
    state: OptimizationNodeState,
    *,
    dependencies: tuple[str, ...] = (),
    cost: int = 1,
    integration_cost: int = 0,
    acceptance: tuple[str, ...] = (),
) -> DependencyNode:
    return DependencyNode(
        node_id=node_id,
        kind=kind,
        state=state,
        dependencies=dependencies,
        remaining_cost=cost,
        integration_cost=integration_cost,
        acceptance_refs=acceptance,
    )


def _graph(project_id: str = "project:alpha") -> DependencyGraph:
    return DependencyGraph(
        project_id=project_id,
        revision=7,
        nodes=(
            _node("contract:worker", OptimizationNodeKind.CONTRACT, OptimizationNodeState.PASSED, cost=0),
            _node(
                "ws:critical",
                OptimizationNodeKind.WORKSTREAM,
                OptimizationNodeState.READY,
                dependencies=("contract:worker",),
                cost=4,
                acceptance=("AC-01", "AC-02"),
            ),
            _node(
                "ws:small",
                OptimizationNodeKind.WORKSTREAM,
                OptimizationNodeState.READY,
                dependencies=("contract:worker",),
                cost=3,
                acceptance=("AC-03",),
            ),
            _node(
                "gate:test",
                OptimizationNodeKind.VALIDATION_GATE,
                OptimizationNodeState.BLOCKED,
                dependencies=("ws:critical",),
                cost=8,
            ),
            _node(
                "gate:release",
                OptimizationNodeKind.RELEASE_GATE,
                OptimizationNodeState.BLOCKED,
                dependencies=("gate:test",),
                cost=1,
            ),
        ),
    )


def _db_context(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'optimization.db'}")
    assert EngineeringWorkerExecution.__tablename__ == "engineering_worker_executions"
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _insert_run(Session):
    run = EngineeringRun(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        spec_id="P2-V0.16.4",
        project_id=str(uuid4()),
        work_specification_id=str(uuid4()),
        work_specification_revision=4,
        work_specification_digest="d" * 64,
        state="IMPLEMENT",
        revision=0,
        workspace_ref=None,
    )
    with Session() as session:
        session.add(run)
        session.commit()
    return run


def test_work_steal_reuses_worker_recovery_generation_and_rejects_conflicts(tmp_path) -> None:
    Session = _db_context(tmp_path)
    run = _insert_run(Session)
    session = Session()
    try:
        service = WorkerRecoveryService(WorkerExecutionRepository(session), EngineeringRunRepository(session))
        lease = service.acquire(run_id=run.id, now=T0, lease_seconds=30)
        assert lease.generation == 1
        service.classify_and_stall(run_id=run.id, evidence=WorkerStallEvidence(process_lost=True), now=T0 + timedelta(seconds=31))
        service.begin_recovery(run_id=run.id, now=T0 + timedelta(seconds=32))
        health = service.health(run_id=run.id, now=T0 + timedelta(seconds=32))
        assert health.lease_status == "UNOWNED"

        conflict = propose_work_steal(
            run_id=run.id,
            node_id="ws:critical",
            worker_health=health,
            requested_paths=("services/api/parallax_api/code",),
            ownership=(PathOwnership("services/api", "other-execution"),),
            target_capability="python:api",
            safe_boundary=SafeBoundary.BEFORE_MUTATION,
        )
        assert conflict.eligible is False
        assert conflict.reason == "PATH_OWNERSHIP_CONFLICT"

        proposal = propose_work_steal(
            run_id=run.id,
            node_id="ws:critical",
            worker_health=health,
            requested_paths=("services/api/parallax_api/code",),
            ownership=(),
            target_capability="python:api",
            safe_boundary=SafeBoundary.BEFORE_MUTATION,
        )
        new_lease = apply_work_steal(service, proposal, now=T0 + timedelta(seconds=33), lease_seconds=30)
        assert new_lease.execution_id == lease.execution_id
        assert new_lease.generation == 2

        with pytest.raises(OptimizationWorkerConflict, match="stale"):
            apply_work_steal(service, proposal, now=T0 + timedelta(seconds=34), lease_seconds=30)
    finally:
        session.close()


def test_work_steal_and_cancellation_fail_closed_during_protected_operation(tmp_path) -> None:
    Session = _db_context(tmp_path)
    run = _insert_run(Session)
    session = Session()
    try:
        service = WorkerRecoveryService(WorkerExecutionRepository(session), EngineeringRunRepository(session))
        service.acquire(run_id=run.id, now=T0, lease_seconds=30)
        active = service.health(run_id=run.id, now=T0 + timedelta(seconds=1))
        denied = propose_work_steal(
            run_id=run.id,
            node_id="ws:critical",
            worker_health=active,
            requested_paths=("services/api",),
            ownership=(),
            target_capability="python:api",
            safe_boundary=SafeBoundary.UNSAFE,
            protected_operation_in_flight=True,
        )
        assert denied.eligible is False
        with pytest.raises(OptimizationWorkerConflict):
            apply_work_steal(service, denied, now=T0 + timedelta(seconds=2))

        wait = cancellation_decision(boundary=SafeBoundary.AFTER_RECORDED_SIDE_EFFECT, protected_operation_in_flight=True)
        assert wait.action is CancellationAction.WAIT
        assert wait.allowed is False
        safe = cancellation_decision(boundary=SafeBoundary.AFTER_ACCEPTED_VALIDATION, supersede=True)
        assert safe.action is CancellationAction.SUPERSEDE_AT_CHECKPOINT
        assert safe.allowed is True
    finally:
        session.close()


def _impact_graph() -> ChangeImpactGraph:
    return ChangeImpactGraph(
        version="impact:v1",
        rules=(
            ImpactRule(
                pattern="services/api/**",
                components=("api",),
                contracts=("contract:api",),
                platforms=("python",),
                checks=("check:api",),
            ),
            ImpactRule(
                pattern="apps/client/**",
                components=("client",),
                contracts=("contract:client",),
                platforms=("web",),
                checks=("check:client",),
            ),
        ),
        global_invariants=("check:global",),
        full_suite_checks=("check:api", "check:client", "check:global", "check:promotion"),
    )
