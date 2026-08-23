from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath

from .optimization_contracts import (
    MAX_REFS,
    CancellationAction,
    OptimizationNodeKind,
    OptimizationNodeState,
    OptimizationPolicyError,
    OptimizationWorkerConflict,
    SafeBoundary,
    _digest,
    _repo_path,
    _safe_token,
)
from .optimization_graph import DependencyGraph
from .worker_recovery import WorkerLease, WorkerLifecycleState
from .worker_service import WorkerRecoveryService


@dataclass(frozen=True, slots=True)
class PathOwnership:
    path: str
    execution_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _repo_path(self.path))
        object.__setattr__(self, "execution_id", _safe_token(self.execution_id, field="execution_id"))


def _paths_overlap(left: str, right: str) -> bool:
    left_parts = PurePosixPath(left).parts
    right_parts = PurePosixPath(right).parts
    length = min(len(left_parts), len(right_parts))
    return left_parts[:length] == right_parts[:length]


def _ready_workstream(graph: DependencyGraph, node_id: str) -> bool:
    nodes = {node.node_id: node for node in graph.nodes}
    node = nodes.get(node_id)
    if node is None or node.kind is not OptimizationNodeKind.WORKSTREAM or node.state is not OptimizationNodeState.READY:
        return False
    return all(nodes[dependency].state is OptimizationNodeState.PASSED for dependency in node.dependencies)


@dataclass(frozen=True, slots=True)
class WorkStealProposal:
    run_id: str
    node_id: str
    graph_digest: str
    execution_id: str
    expected_lease_generation: int
    requested_paths: tuple[str, ...]
    target_capability: str
    safe_boundary: SafeBoundary
    eligible: bool
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _safe_token(self.run_id, field="run_id"))
        object.__setattr__(self, "node_id", _safe_token(self.node_id, field="node_id"))
        _digest(self.graph_digest, field="graph_digest")
        object.__setattr__(self, "execution_id", _safe_token(self.execution_id, field="execution_id"))
        object.__setattr__(self, "target_capability", _safe_token(self.target_capability, field="target_capability"))
        object.__setattr__(self, "reason", _safe_token(self.reason, field="work_steal_reason"))
        paths = tuple(_repo_path(value) for value in self.requested_paths)
        if not paths or len(paths) > MAX_REFS or len(set(paths)) != len(paths):
            raise OptimizationPolicyError("requested work-steal paths must be non-empty, unique and bounded")
        object.__setattr__(self, "requested_paths", paths)
        if not isinstance(self.expected_lease_generation, int) or self.expected_lease_generation < 0:
            raise OptimizationPolicyError("expected lease generation must be nonnegative")


def propose_work_steal(
    *,
    graph: DependencyGraph,
    run_id: str,
    node_id: str,
    worker_health,
    requested_paths: tuple[str, ...],
    ownership: tuple[PathOwnership, ...],
    target_capability: str,
    safe_boundary: SafeBoundary,
    protected_operation_in_flight: bool = False,
) -> WorkStealProposal:
    graph.validate()
    paths = tuple(_repo_path(value) for value in requested_paths)
    reason = "ELIGIBLE_RECOVERING_WORK"
    eligible = True
    if not _ready_workstream(graph, node_id):
        eligible = False
        reason = "WORK_NOT_READY"
    elif worker_health.state is not WorkerLifecycleState.RECOVERING or worker_health.lease_status != "UNOWNED":
        eligible = False
        reason = "ACTIVE_OR_NONRECOVERING_WORKER"
    elif safe_boundary is SafeBoundary.UNSAFE or protected_operation_in_flight:
        eligible = False
        reason = "UNSAFE_PROTECTED_OPERATION"
    else:
        for item in ownership:
            if item.execution_id == worker_health.execution_id:
                continue
            if any(_paths_overlap(path, item.path) for path in paths):
                eligible = False
                reason = "PATH_OWNERSHIP_CONFLICT"
                break
    return WorkStealProposal(
        run_id=run_id,
        node_id=node_id,
        graph_digest=graph.digest,
        execution_id=worker_health.execution_id,
        expected_lease_generation=worker_health.lease_generation,
        requested_paths=paths,
        target_capability=target_capability,
        safe_boundary=safe_boundary,
        eligible=eligible,
        reason=reason,
    )


def apply_work_steal(
    service: WorkerRecoveryService,
    proposal: WorkStealProposal,
    *,
    current_graph: DependencyGraph,
    now: datetime | None = None,
    lease_seconds: int = 90,
) -> WorkerLease:
    if not proposal.eligible:
        raise OptimizationWorkerConflict(f"work steal is not eligible: {proposal.reason}")
    current_graph.validate()
    if current_graph.digest != proposal.graph_digest:
        raise OptimizationWorkerConflict("work steal rejected because optimization graph state is stale")
    if not _ready_workstream(current_graph, proposal.node_id):
        raise OptimizationWorkerConflict("work steal rejected because work is no longer dependency-ready")
    health = service.health(run_id=proposal.run_id, now=now)
    if health.execution_id != proposal.execution_id or health.lease_generation != proposal.expected_lease_generation:
        raise OptimizationWorkerConflict("work steal rejected because worker execution generation is stale")
    if health.state is not WorkerLifecycleState.RECOVERING or health.lease_status != "UNOWNED":
        raise OptimizationWorkerConflict("work steal requires the accepted RECOVERING unowned worker state")
    lease = service.reassign(run_id=proposal.run_id, now=now, lease_seconds=lease_seconds)
    if lease.execution_id != proposal.execution_id or lease.generation != proposal.expected_lease_generation + 1:
        raise OptimizationWorkerConflict("worker recovery service returned an unexpected reassignment generation")
    return lease


@dataclass(frozen=True, slots=True)
class CancellationDecision:
    action: CancellationAction
    boundary: SafeBoundary
    reason: str

    @property
    def allowed(self) -> bool:
        return self.action is not CancellationAction.WAIT


def cancellation_decision(
    *,
    boundary: SafeBoundary,
    supersede: bool = False,
    protected_operation_in_flight: bool = False,
) -> CancellationDecision:
    if boundary is SafeBoundary.UNSAFE or protected_operation_in_flight:
        return CancellationDecision(CancellationAction.WAIT, boundary, "UNSAFE_BOUNDARY")
    return CancellationDecision(
        CancellationAction.SUPERSEDE_AT_CHECKPOINT if supersede else CancellationAction.CANCEL_AT_CHECKPOINT,
        boundary,
        "SAFE_CHECKPOINT",
    )
