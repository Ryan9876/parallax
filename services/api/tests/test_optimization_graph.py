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


def test_dependency_graph_round_trip_digest_cycle_and_acceptance_ownership() -> None:
    graph = _graph()
    recreated = DependencyGraph.from_record(graph.to_record())
    assert recreated == graph
    assert recreated.digest == graph.digest

    with pytest.raises(OptimizationGraphError, match="cycle"):
        DependencyGraph(
            project_id="project:alpha",
            revision=0,
            nodes=(
                _node("ws:a", OptimizationNodeKind.WORKSTREAM, OptimizationNodeState.READY, dependencies=("ws:b",)),
                _node("ws:b", OptimizationNodeKind.WORKSTREAM, OptimizationNodeState.READY, dependencies=("ws:a",)),
            ),
        )

    with pytest.raises(OptimizationGraphError, match="dangling"):
        DependencyGraph(
            project_id="project:alpha",
            revision=0,
            nodes=(_node("ws:a", OptimizationNodeKind.WORKSTREAM, OptimizationNodeState.READY, dependencies=("missing:node",)),),
        )

    with pytest.raises(OptimizationGraphError, match="multiple workstream owners"):
        DependencyGraph(
            project_id="project:alpha",
            revision=0,
            nodes=(
                _node("ws:a", OptimizationNodeKind.WORKSTREAM, OptimizationNodeState.READY, acceptance=("AC-01",)),
                _node("ws:b", OptimizationNodeKind.WORKSTREAM, OptimizationNodeState.READY, acceptance=("AC-01",)),
            ),
        )


def test_critical_path_ranking_is_stable_and_backpressure_defers_lower_priority() -> None:
    graph = _graph()
    scheduler = CriticalPathScheduler()
    decisions = scheduler.rank(graph)
    assert [item.node_id for item in decisions] == ["ws:critical", "ws:small"]
    assert decisions[0].critical_path_cost == 13
    assert decisions[0].blocked_descendants == 2

    pressure = IntegrationBackpressure(capacity=1, ready_items=1, ready_cost=10, cost_capacity=10)
    pressured = scheduler.rank(graph, backpressure=pressure, saturated_parallelism=1)
    assert pressured[0].deferred_by_backpressure is False
    assert pressured[1].deferred_by_backpressure is True
    assert pressured[1].reason == "INTEGRATION_BACKPRESSURE"

    tie_graph = DependencyGraph(
        project_id="project:alpha",
        revision=1,
        nodes=(
            _node("ws:b", OptimizationNodeKind.WORKSTREAM, OptimizationNodeState.READY, cost=2),
            _node("ws:a", OptimizationNodeKind.WORKSTREAM, OptimizationNodeState.READY, cost=2),
        ),
    )
    assert [item.node_id for item in scheduler.rank(tie_graph)] == ["ws:a", "ws:b"]


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
