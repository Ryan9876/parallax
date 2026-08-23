from __future__ import annotations

from dataclasses import dataclass

from .optimization_contracts import (
    MAX_GRAPH_EDGES, MAX_GRAPH_NODES, MAX_REFS,
    OptimizationGraphError, OptimizationNodeKind, OptimizationNodeState,
    OptimizationPolicyError, _canonical_digest, _refs, _safe_token,
)

@dataclass(frozen=True, slots=True)
class DependencyNode:
    node_id: str
    kind: OptimizationNodeKind
    state: OptimizationNodeState
    dependencies: tuple[str, ...] = ()
    remaining_cost: int = 1
    integration_cost: int = 0
    acceptance_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _safe_token(self.node_id, field="node_id"))
        object.__setattr__(self, "dependencies", _refs(self.dependencies, field="dependency", limit=MAX_GRAPH_NODES))
        object.__setattr__(self, "acceptance_refs", _refs(self.acceptance_refs, field="acceptance_ref", limit=MAX_REFS))
        for name in ("remaining_cost", "integration_cost"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100_000:
                raise OptimizationGraphError(f"{name} must be a bounded nonnegative integer")
        if self.kind is not OptimizationNodeKind.WORKSTREAM and self.acceptance_refs:
            raise OptimizationGraphError("only workstream nodes may own acceptance criteria")

    def to_record(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "kind": self.kind.value,
            "state": self.state.value,
            "dependencies": list(self.dependencies),
            "remaining_cost": self.remaining_cost,
            "integration_cost": self.integration_cost,
            "acceptance_refs": list(self.acceptance_refs),
        }

    @classmethod
    def from_record(cls, value: object) -> "DependencyNode":
        if not isinstance(value, dict):
            raise OptimizationGraphError("dependency node record must be an object")
        try:
            return cls(
                node_id=value["node_id"],
                kind=OptimizationNodeKind(value["kind"]),
                state=OptimizationNodeState(value["state"]),
                dependencies=tuple(value.get("dependencies", ())),
                remaining_cost=value.get("remaining_cost", 1),
                integration_cost=value.get("integration_cost", 0),
                acceptance_refs=tuple(value.get("acceptance_refs", ())),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OptimizationGraphError("dependency node record is invalid") from exc


@dataclass(frozen=True, slots=True)
class DependencyGraph:
    project_id: str
    revision: int
    nodes: tuple[DependencyNode, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _safe_token(self.project_id, field="project_id"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 0:
            raise OptimizationGraphError("graph revision must be nonnegative")
        if not self.nodes or len(self.nodes) > MAX_GRAPH_NODES:
            raise OptimizationGraphError("dependency graph must contain a bounded node set")
        if not all(isinstance(node, DependencyNode) for node in self.nodes):
            raise OptimizationGraphError("dependency graph contains invalid nodes")
        self.validate()

    def validate(self) -> None:
        by_id = {node.node_id: node for node in self.nodes}
        if len(by_id) != len(self.nodes):
            raise OptimizationGraphError("dependency graph contains duplicate node identities")
        edge_count = sum(len(node.dependencies) for node in self.nodes)
        if edge_count > MAX_GRAPH_EDGES:
            raise OptimizationGraphError("dependency graph exceeds edge bound")
        for node in self.nodes:
            for dependency in node.dependencies:
                if dependency not in by_id:
                    raise OptimizationGraphError(f"dangling dependency: {dependency}")
                if dependency == node.node_id:
                    raise OptimizationGraphError("dependency graph cannot contain self edges")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise OptimizationGraphError("dependency graph contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency in by_id[node_id].dependencies:
                visit(dependency)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in sorted(by_id):
            visit(node_id)

        acceptance_owner: dict[str, str] = {}
        for node in self.nodes:
            for acceptance in node.acceptance_refs:
                prior = acceptance_owner.setdefault(acceptance, node.node_id)
                if prior != node.node_id:
                    raise OptimizationGraphError(f"acceptance criterion {acceptance} has multiple workstream owners")

    @property
    def digest(self) -> str:
        return _canonical_digest(self.to_record())

    def to_record(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "revision": self.revision,
            "nodes": [node.to_record() for node in sorted(self.nodes, key=lambda item: item.node_id)],
        }

    @classmethod
    def from_record(cls, value: object) -> "DependencyGraph":
        if not isinstance(value, dict):
            raise OptimizationGraphError("dependency graph record must be an object")
        try:
            raw_nodes = value["nodes"]
            if not isinstance(raw_nodes, list):
                raise TypeError("nodes must be a list")
            return cls(
                project_id=value["project_id"],
                revision=value["revision"],
                nodes=tuple(DependencyNode.from_record(item) for item in raw_nodes),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OptimizationGraphError("dependency graph record is invalid") from exc


@dataclass(frozen=True, slots=True)
class SchedulingDecision:
    node_id: str
    rank: int
    critical_path_cost: int
    blocked_descendants: int
    deferred_by_backpressure: bool
    reason: str


@dataclass(frozen=True, slots=True)
class IntegrationBackpressure:
    capacity: int
    ready_items: int
    ready_cost: int
    cost_capacity: int

    def __post_init__(self) -> None:
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (self.capacity, self.ready_items, self.ready_cost, self.cost_capacity)):
            raise OptimizationPolicyError("backpressure values must be nonnegative integers")
        if self.capacity < 1 or self.cost_capacity < 1:
            raise OptimizationPolicyError("integration capacity must be positive")

    @property
    def saturated(self) -> bool:
        return self.ready_items >= self.capacity or self.ready_cost >= self.cost_capacity


class CriticalPathScheduler:
    def rank(
        self,
        graph: DependencyGraph,
        *,
        backpressure: IntegrationBackpressure | None = None,
        saturated_parallelism: int = 1,
    ) -> tuple[SchedulingDecision, ...]:
        graph.validate()
        if saturated_parallelism < 1:
            raise OptimizationPolicyError("saturated parallelism must be positive")
        nodes = {node.node_id: node for node in graph.nodes}
        children: dict[str, list[str]] = {node_id: [] for node_id in nodes}
        for node in graph.nodes:
            for dependency in node.dependencies:
                children[dependency].append(node.node_id)

        memo: dict[str, int] = {}
        descendant_memo: dict[str, set[str]] = {}

        def path_cost(node_id: str) -> int:
            if node_id in memo:
                return memo[node_id]
            child_cost = max((path_cost(child) for child in children[node_id]), default=0)
            memo[node_id] = nodes[node_id].remaining_cost + nodes[node_id].integration_cost + child_cost
            return memo[node_id]

        def descendants(node_id: str) -> set[str]:
            if node_id in descendant_memo:
                return descendant_memo[node_id]
            result: set[str] = set()
            for child in children[node_id]:
                result.add(child)
                result.update(descendants(child))
            descendant_memo[node_id] = result
            return result

        satisfied = {OptimizationNodeState.PASSED}
        ready: list[tuple[DependencyNode, int, int]] = []
        for node in graph.nodes:
            if node.state is not OptimizationNodeState.READY:
                continue
            if any(nodes[dependency].state not in satisfied for dependency in node.dependencies):
                continue
            ready.append((node, path_cost(node.node_id), len(descendants(node.node_id))))

        ready.sort(key=lambda item: (-item[1], -item[2], item[0].node_id))
        saturated = backpressure.saturated if backpressure is not None else False
        decisions: list[SchedulingDecision] = []
        for index, (node, cost, blocked) in enumerate(ready, start=1):
            deferred = saturated and index > saturated_parallelism
            decisions.append(
                SchedulingDecision(
                    node_id=node.node_id,
                    rank=index,
                    critical_path_cost=cost,
                    blocked_descendants=blocked,
                    deferred_by_backpressure=deferred,
                    reason="INTEGRATION_BACKPRESSURE" if deferred else "CRITICAL_PATH_READY",
                )
            )
        return tuple(decisions)
