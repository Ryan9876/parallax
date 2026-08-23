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

def test_change_impact_fast_lane_is_proven_and_promotion_or_unknown_is_full() -> None:
    graph = _impact_graph()
    fast = graph.select(("services/api/parallax_api/code/service.py",), boundary=ValidationBoundary.DEVELOPMENT_FAST)
    assert fast.conservative is False
    assert fast.selected_checks == ("check:api", "check:global")
    assert set(fast.excluded_checks) == {"check:client", "check:promotion"}
    assert len(fast.excluded_evidence) == 2
    assert fast.graph_digest == graph.digest

    unknown = graph.select(("README.md",), boundary=ValidationBoundary.DEVELOPMENT_FAST)
    assert unknown.conservative is True
    assert set(unknown.selected_checks) == set(graph.full_suite_checks)

    promotion = graph.select(("services/api/x.py",), boundary=ValidationBoundary.WORKER_ACCEPTANCE)
    assert promotion.conservative is True
    assert set(promotion.selected_checks) == set(graph.full_suite_checks)

    changed_policy = graph.select((".parallax/change-impact.json",), boundary=ValidationBoundary.DEVELOPMENT_FAST)
    assert changed_policy.conservative is True


def test_change_impact_conflict_expands_instead_of_skipping() -> None:
    graph = ChangeImpactGraph(
        version="impact:v2",
        rules=(
            ImpactRule("services/api/**", ("api",), (), ("python",), ("check:api",)),
            ImpactRule("services/api/**", ("api",), (), ("python",), ("check:other",)),
        ),
        global_invariants=("check:global",),
        full_suite_checks=("check:api", "check:other", "check:global"),
    )
    selection = graph.select(("services/api/x.py",), boundary=ValidationBoundary.DEVELOPMENT_FAST)
    assert selection.conservative is True
    assert set(selection.selected_checks) == set(graph.full_suite_checks)


def test_warm_environment_identity_is_exact_secret_free_and_provenance_complete() -> None:
    expected = WarmEnvironmentIdentity.build(
        runtime="python:3.13",
        operating_system="linux",
        architecture="x86_64",
        toolchain_digest=D1,
        dependency_digest=D2,
        configuration_digest=D3,
        source_digest=D4,
        cache_schema_version="cache:v1",
    )
    same = WarmEnvironmentIdentity.build(
        runtime="python:3.13",
        operating_system="linux",
        architecture="x86_64",
        toolchain_digest=D1,
        dependency_digest=D2,
        configuration_digest=D3,
        source_digest=D4,
        cache_schema_version="cache:v1",
    )
    changed = WarmEnvironmentIdentity.build(
        runtime="python:3.13",
        operating_system="linux",
        architecture="x86_64",
        toolchain_digest=D1,
        dependency_digest=D2,
        configuration_digest=D3,
        source_digest="5" * 64,
        cache_schema_version="cache:v1",
    )
    assert expected.digest == same.digest
    assert expected.digest != changed.digest
    record = WarmCacheRecord(expected.digest, True, ("cache:evidence:v1",))
    assert record.eligible_for(expected) is True
    assert record.eligible_for(changed) is False
    assert WarmCacheRecord(expected.digest, False, ("cache:evidence:v1",)).eligible_for(expected) is False

    with pytest.raises(OptimizationPolicyError):
        WarmEnvironmentIdentity.build(
            runtime="token:abcdefghi",
            operating_system="linux",
            architecture="x86_64",
            toolchain_digest=D1,
            dependency_digest=D2,
            configuration_digest=D3,
            source_digest=D4,
            cache_schema_version="cache:v1",
        )
