from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import ClassVar

from .optimization_contracts import (MAX_GRAPH_EDGES, MAX_REGISTRY_RECORDS, MAX_REFS, OptimizationGraphError, OptimizationPolicyError, PreflightFindingKind, _canonical_digest, _lineage, _refs, _safe_token)
from .optimization_graph import DependencyGraph

@dataclass(frozen=True, slots=True)
class PreflightFinding:
    kind: PreflightFindingKind
    code: str
    subject: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _safe_token(self.code, field="preflight_code"))
        object.__setattr__(self, "subject", _safe_token(self.subject, field="preflight_subject"))


@dataclass(frozen=True, slots=True)
class SpecPreflightRequest:
    graph: DependencyGraph
    acceptance_criteria: tuple[str, ...]
    validation_coverage: tuple[tuple[str, str], ...]
    acceptance_ownership: tuple[tuple[str, str], ...]
    requested_authorities: tuple[str, ...] = ()
    allowed_authorities: tuple[str, ...] = ()
    contradictory_pairs: tuple[tuple[str, str], ...] = ()
    missing_dependencies: tuple[str, ...] = ()
    architecture_conflicts: tuple[str, ...] = ()
    constitution_conflicts: tuple[str, ...] = ()


def preflight_spec(request: SpecPreflightRequest) -> tuple[PreflightFinding, ...]:
    findings: list[PreflightFinding] = []
    try:
        request.graph.validate()
    except OptimizationGraphError as exc:
        findings.append(PreflightFinding(PreflightFindingKind.GRAPH, "GRAPH_INVALID", sha256(str(exc).encode()).hexdigest()[:16]))
    acs = _refs(request.acceptance_criteria, field="acceptance_criterion", limit=MAX_REGISTRY_RECORDS)
    coverage: dict[str, set[str]] = {ac: set() for ac in acs}
    for ac, check in request.validation_coverage:
        ac_id = _safe_token(ac, field="coverage_ac")
        check_id = _safe_token(check, field="coverage_check")
        if ac_id in coverage:
            coverage[ac_id].add(check_id)
    for ac in acs:
        if not coverage[ac]:
            findings.append(PreflightFinding(PreflightFindingKind.UNTESTABLE_ACCEPTANCE, "NO_VALIDATION_COVERAGE", ac))

    owners: dict[str, set[str]] = {ac: set() for ac in acs}
    for ac, owner in request.acceptance_ownership:
        ac_id = _safe_token(ac, field="ownership_ac")
        owner_id = _safe_token(owner, field="ownership_owner")
        if ac_id in owners:
            owners[ac_id].add(owner_id)
    for ac in acs:
        if len(owners[ac]) != 1:
            findings.append(PreflightFinding(PreflightFindingKind.ACCEPTANCE_OWNERSHIP, "AMBIGUOUS_ACCEPTANCE_OWNER", ac))

    allowed = set(_refs(request.allowed_authorities, field="allowed_authority"))
    for authority in _refs(request.requested_authorities, field="requested_authority"):
        if authority not in allowed:
            findings.append(PreflightFinding(PreflightFindingKind.AUTHORITY_CONFLICT, "EXCESS_AUTHORITY", authority))
    for left, right in request.contradictory_pairs:
        subject = f"{_safe_token(left, field='contradiction_left')}:{_safe_token(right, field='contradiction_right')}"
        findings.append(PreflightFinding(PreflightFindingKind.CONTRADICTION, "CONTRADICTORY_REQUIREMENTS", subject))
    for dependency in _refs(request.missing_dependencies, field="missing_dependency"):
        findings.append(PreflightFinding(PreflightFindingKind.MISSING_DEPENDENCY, "MISSING_DEPENDENCY", dependency))
    for conflict in _refs(request.architecture_conflicts, field="architecture_conflict"):
        findings.append(PreflightFinding(PreflightFindingKind.ARCHITECTURE_CONFLICT, "ARCHITECTURE_CONFLICT", conflict))
    for conflict in _refs(request.constitution_conflicts, field="constitution_conflict"):
        findings.append(PreflightFinding(PreflightFindingKind.CONSTITUTION_CONFLICT, "CONSTITUTION_CONFLICT", conflict))
    return tuple(sorted(findings, key=lambda item: (item.kind.value, item.code, item.subject)))


@dataclass(frozen=True, slots=True)
class SpeculativeIntegrationCandidate:
    project_id: str
    lineage_refs: tuple[str, ...]
    validation_refs: tuple[str, ...]
    candidate_digest: str
    authoritative: ClassVar[bool] = False

    @classmethod
    def build(cls, *, project_id: str, lineage_refs: tuple[str, ...], validation_refs: tuple[str, ...]) -> "SpeculativeIntegrationCandidate":
        project = _safe_token(project_id, field="project_id")
        lineages = tuple(_lineage(value, field="speculative_lineage") for value in lineage_refs)
        if not lineages or len(lineages) > MAX_REFS or len(set(lineages)) != len(lineages):
            raise OptimizationPolicyError("speculative candidate requires unique bounded lineages")
        evidence = _refs(validation_refs, field="speculative_validation")
        payload = {"project_id": project, "lineages": lineages, "validation_refs": evidence, "authoritative": False}
        return cls(project_id=project, lineage_refs=lineages, validation_refs=evidence, candidate_digest=_canonical_digest(payload))

    def to_record(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "lineage_refs": list(self.lineage_refs),
            "validation_refs": list(self.validation_refs),
            "candidate_digest": self.candidate_digest,
            "authoritative": False,
        }


@dataclass(frozen=True, slots=True)
class AcceptanceAssignment:
    acceptance_id: str
    workstream_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "acceptance_id", _safe_token(self.acceptance_id, field="acceptance_id"))
        object.__setattr__(self, "workstream_id", _safe_token(self.workstream_id, field="workstream_id"))


@dataclass(frozen=True, slots=True)
class WorkstreamSizingProposal:
    assignments: tuple[AcceptanceAssignment, ...]
    dependency_edges: tuple[tuple[str, str], ...]

    def validate(self, expected_acceptance_ids: tuple[str, ...]) -> None:
        if len(self.assignments) > MAX_REGISTRY_RECORDS or len(self.dependency_edges) > MAX_GRAPH_EDGES:
            raise OptimizationPolicyError("workstream sizing proposal exceeds protected bounds")
        expected = set(_refs(expected_acceptance_ids, field="expected_acceptance", limit=MAX_REGISTRY_RECORDS))
        seen: dict[str, str] = {}
        for assignment in self.assignments:
            if assignment.acceptance_id in seen:
                raise OptimizationPolicyError("workstream sizing duplicates acceptance ownership")
            seen[assignment.acceptance_id] = assignment.workstream_id
        if set(seen) != expected:
            raise OptimizationPolicyError("workstream sizing orphans or adds acceptance criteria")
        normalized_edges: set[tuple[str, str]] = set()
        for parent, child in self.dependency_edges:
            edge = (_safe_token(parent, field="dependency_parent"), _safe_token(child, field="dependency_child"))
            if edge[0] == edge[1]:
                raise OptimizationPolicyError("workstream sizing cannot add self dependency")
            if edge in normalized_edges:
                raise OptimizationPolicyError("workstream sizing dependency edges must be unique")
            normalized_edges.add(edge)


class WorkstreamSizer:
    """Deterministically split oversized workstreams without orphaning acceptance ownership."""

    def recommend(
        self,
        proposal: WorkstreamSizingProposal,
        *,
        max_acceptance_per_workstream: int,
    ) -> WorkstreamSizingProposal:
        expected = tuple(assignment.acceptance_id for assignment in proposal.assignments)
        proposal.validate(expected)
        if not isinstance(max_acceptance_per_workstream, int) or isinstance(max_acceptance_per_workstream, bool) or max_acceptance_per_workstream < 1:
            raise OptimizationPolicyError("workstream sizing limit must be a positive integer")

        by_owner: dict[str, list[str]] = {}
        for assignment in proposal.assignments:
            by_owner.setdefault(assignment.workstream_id, []).append(assignment.acceptance_id)

        owner_parts: dict[str, tuple[str, ...]] = {}
        assignments: list[AcceptanceAssignment] = []
        extra_edges: list[tuple[str, str]] = []
        for owner in sorted(by_owner):
            criteria = sorted(by_owner[owner])
            chunks = [criteria[index:index + max_acceptance_per_workstream] for index in range(0, len(criteria), max_acceptance_per_workstream)]
            if len(chunks) == 1:
                part_ids = (owner,)
            else:
                part_ids = tuple(f"{owner}:part-{index}" for index in range(1, len(chunks) + 1))
                extra_edges.extend((part_ids[index - 1], part_ids[index]) for index in range(1, len(part_ids)))
            owner_parts[owner] = part_ids
            for part_id, chunk in zip(part_ids, chunks, strict=True):
                assignments.extend(AcceptanceAssignment(ac, part_id) for ac in chunk)

        edges: set[tuple[str, str]] = set(extra_edges)
        for parent, child in proposal.dependency_edges:
            parent_parts = owner_parts.get(parent, (parent,))
            child_parts = owner_parts.get(child, (child,))
            edges.add((parent_parts[-1], child_parts[0]))

        result = WorkstreamSizingProposal(
            assignments=tuple(sorted(assignments, key=lambda item: item.acceptance_id)),
            dependency_edges=tuple(sorted(edges)),
        )
        result.validate(tuple(sorted(expected)))
        return result
