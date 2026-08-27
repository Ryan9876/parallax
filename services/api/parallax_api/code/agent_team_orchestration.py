from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from itertools import combinations
import json
import re
from typing import Iterable
from uuid import UUID

from .agent_protocol import (
    AGENT_PROTOCOL_VERSION,
    AgentEvidenceReference,
    AgentIdentity,
    AgentResult,
    AgentSourceContext,
    AgentTaskRequest,
    MetricObservation,
    verify_result_admission,
)
from .worker_recovery import RecoveryAction, WorkerHealthSnapshot


ORCHESTRATION_PROTOCOL_VERSION = 1
_MAX_ROSTER = 32
_MAX_WORK_UNITS = 48
_MAX_DEPENDENCIES = 16
_MAX_DOMAINS = 16
_MAX_CONTEXT_REFS = 16
_MAX_GRAPH_DEPTH = 16
_MAX_FANOUT = 16

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ACCEPTANCE_ID_RE = re.compile(r"^AC-[0-9]{2,3}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")


class OrchestrationError(ValueError):
    pass


class OrchestrationDisposition(StrEnum):
    READY = "READY"
    WAITING_DEPENDENCY = "WAITING_DEPENDENCY"
    SERIALIZED_COORDINATION = "SERIALIZED_COORDINATION"
    BLOCKED = "BLOCKED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    COMPLETED = "COMPLETED"
    REASSIGNED = "REASSIGNED"


class PlanContextReason(StrEnum):
    MATCH = "MATCH"
    PROJECT_MISMATCH = "PROJECT_MISMATCH"
    RUN_MISMATCH = "RUN_MISMATCH"
    WORK_SPECIFICATION_MISMATCH = "WORK_SPECIFICATION_MISMATCH"
    ACCEPTANCE_CONTRACT_MISMATCH = "ACCEPTANCE_CONTRACT_MISMATCH"
    AGENT_PROTOCOL_MISMATCH = "AGENT_PROTOCOL_MISMATCH"
    POLICY_DRIFT = "POLICY_DRIFT"
    WORK_GRAPH_DRIFT = "WORK_GRAPH_DRIFT"
    ROSTER_DRIFT = "ROSTER_DRIFT"


@dataclass(frozen=True, slots=True)
class OrchestrationLimits:
    max_team_size: int = 4
    max_concurrency: int = 4
    max_reassignments_per_work_unit: int = 2
    max_replans: int = 3
    max_no_progress: int = 3

    def __post_init__(self) -> None:
        for field, value, maximum in (
            ("max_team_size", self.max_team_size, 8),
            ("max_concurrency", self.max_concurrency, 8),
            ("max_reassignments_per_work_unit", self.max_reassignments_per_work_unit, 8),
            ("max_replans", self.max_replans, 16),
            ("max_no_progress", self.max_no_progress, 16),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= maximum:
                raise OrchestrationError(f"{field} is outside protected bounds")
        if self.max_concurrency > self.max_team_size:
            raise OrchestrationError("max_concurrency cannot exceed max_team_size")

    def as_dict(self) -> dict[str, int]:
        return {
            "max_team_size": self.max_team_size,
            "max_concurrency": self.max_concurrency,
            "max_reassignments_per_work_unit": self.max_reassignments_per_work_unit,
            "max_replans": self.max_replans,
            "max_no_progress": self.max_no_progress,
        }


@dataclass(frozen=True, slots=True)
class WorkUnit:
    unit_id: str
    work_kind: str
    acceptance_ids: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    coordination_domains: tuple[str, ...] = ()
    requires_canonical_mutation: bool = False
    context_refs: tuple[AgentEvidenceReference, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "unit_id", _token(self.unit_id, field="unit_id"))
        object.__setattr__(self, "work_kind", _token(self.work_kind, field="work_kind"))
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids, required=True))
        dependencies = _token_set(self.dependencies, field="dependencies")
        if len(dependencies) > _MAX_DEPENDENCIES:
            raise OrchestrationError("work unit exceeds dependency bound")
        if self.unit_id in dependencies:
            raise OrchestrationError("work unit cannot depend on itself")
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(
            self,
            "required_capabilities",
            _token_set(self.required_capabilities, field="required_capabilities"),
        )
        domains = _token_set(self.coordination_domains, field="coordination_domains")
        if len(domains) > _MAX_DOMAINS:
            raise OrchestrationError("work unit exceeds coordination-domain bound")
        object.__setattr__(self, "coordination_domains", domains)
        if not isinstance(self.requires_canonical_mutation, bool):
            raise OrchestrationError("requires_canonical_mutation must be bool")
        refs = tuple(self.context_refs)
        if len(refs) > _MAX_CONTEXT_REFS or any(not isinstance(item, AgentEvidenceReference) for item in refs):
            raise OrchestrationError("context_refs must contain bounded S1 evidence references")
        if len({(item.kind, item.reference_id, item.digest) for item in refs}) != len(refs):
            raise OrchestrationError("context_refs must be unique")
        object.__setattr__(self, "context_refs", refs)

    def as_dict(self) -> dict[str, object]:
        return {
            "unit_id": self.unit_id,
            "work_kind": self.work_kind,
            "acceptance_ids": list(self.acceptance_ids),
            "dependencies": list(self.dependencies),
            "required_capabilities": list(self.required_capabilities),
            "coordination_domains": list(self.coordination_domains),
            "requires_canonical_mutation": self.requires_canonical_mutation,
            "context_refs": [item.as_dict() for item in self.context_refs],
            "canonical_source_writer": False,
        }


@dataclass(frozen=True, slots=True)
class WorkGraph:
    approved_acceptance_ids: tuple[str, ...]
    units: tuple[WorkUnit, ...]

    def __post_init__(self) -> None:
        approved = _acceptance_ids(self.approved_acceptance_ids, required=True)
        object.__setattr__(self, "approved_acceptance_ids", approved)
        units = tuple(self.units)
        if not units or len(units) > _MAX_WORK_UNITS:
            raise OrchestrationError("work graph is empty or exceeds protected bound")
        if any(not isinstance(item, WorkUnit) for item in units):
            raise OrchestrationError("work graph contains invalid work unit")
        ordered = tuple(sorted(units, key=lambda item: item.unit_id))
        ids = [item.unit_id for item in ordered]
        if len(set(ids)) != len(ids):
            raise OrchestrationError("work graph contains duplicate work-unit ids")
        known = set(ids)
        approved_set = set(approved)
        acceptance_owner: dict[str, str] = {}
        fanout = {item: 0 for item in ids}
        for unit in ordered:
            missing = set(unit.dependencies) - known
            if missing:
                raise OrchestrationError("work graph contains missing dependency")
            for dependency in unit.dependencies:
                fanout[dependency] += 1
                if fanout[dependency] > _MAX_FANOUT:
                    raise OrchestrationError("work graph exceeds dependency fan-out bound")
            if not set(unit.acceptance_ids) <= approved_set:
                raise OrchestrationError("work unit claims acceptance outside approved contract")
            for acceptance_id in unit.acceptance_ids:
                if acceptance_id in acceptance_owner:
                    raise OrchestrationError("acceptance identity has conflicting work-unit ownership")
                acceptance_owner[acceptance_id] = unit.unit_id
        _validate_acyclic_and_depth(ordered)
        object.__setattr__(self, "units", ordered)

    @property
    def digest(self) -> str:
        return _digest(self.as_dict(include_digest=False))

    def get(self, unit_id: str) -> WorkUnit:
        normalized = _token(unit_id, field="unit_id")
        for unit in self.units:
            if unit.unit_id == normalized:
                return unit
        raise OrchestrationError("unknown work unit")

    def as_dict(self, *, include_digest: bool = True) -> dict[str, object]:
        value: dict[str, object] = {
            "approved_acceptance_ids": list(self.approved_acceptance_ids),
            "units": [unit.as_dict() for unit in self.units],
        }
        if include_digest:
            value["digest"] = self.digest
        return value


@dataclass(frozen=True, slots=True)
class AdmittedAgent:
    identity: AgentIdentity
    admitted_work_kinds: tuple[str, ...]
    admitted_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.identity, AgentIdentity):
            raise OrchestrationError("admitted agent requires S1 AgentIdentity")
        work = _token_set(self.admitted_work_kinds, field="admitted_work_kinds", required=True)
        capabilities = _token_set(self.admitted_capabilities, field="admitted_capabilities")
        if any(item not in self.identity.declared_work_kinds for item in work):
            raise OrchestrationError("server admission cannot invent undeclared work kinds")
        if any(item not in self.identity.declared_capabilities for item in capabilities):
            raise OrchestrationError("server admission cannot invent undeclared capabilities")
        object.__setattr__(self, "admitted_work_kinds", work)
        object.__setattr__(self, "admitted_capabilities", capabilities)

    @property
    def identity_digest(self) -> str:
        return self.identity.digest

    def supports(self, unit: WorkUnit) -> bool:
        return (
            unit.work_kind in self.identity.declared_work_kinds
            and unit.work_kind in self.admitted_work_kinds
            and all(item in self.identity.declared_capabilities for item in unit.required_capabilities)
            and all(item in self.admitted_capabilities for item in unit.required_capabilities)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity.as_dict(),
            "identity_digest": self.identity_digest,
            "admitted_work_kinds": list(self.admitted_work_kinds),
            "admitted_capabilities": list(self.admitted_capabilities),
            "server_owned_admission": True,
            "grants_new_authority": False,
            "contains_credentials": False,
        }


@dataclass(frozen=True, slots=True)
class AdmittedRoster:
    entries: tuple[AdmittedAgent, ...]

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        if not entries or len(entries) > _MAX_ROSTER:
            raise OrchestrationError("admitted roster is empty or exceeds protected bound")
        if any(not isinstance(item, AdmittedAgent) for item in entries):
            raise OrchestrationError("admitted roster contains invalid entry")
        ordered = tuple(sorted(entries, key=lambda item: item.identity_digest))
        digests = [item.identity_digest for item in ordered]
        if len(set(digests)) != len(digests):
            raise OrchestrationError("admitted roster contains duplicate agent identity")
        object.__setattr__(self, "entries", ordered)

    @property
    def digest(self) -> str:
        return _digest([entry.as_dict() for entry in self.entries])

    def get(self, identity_digest: str) -> AdmittedAgent:
        normalized = _sha256(identity_digest, field="identity_digest")
        for entry in self.entries:
            if entry.identity_digest == normalized:
                return entry
        raise OrchestrationError("agent identity is not in admitted roster")

    def as_dict(self) -> dict[str, object]:
        return {
            "entries": [entry.as_dict() for entry in self.entries],
            "digest": self.digest,
            "contains_credentials": False,
        }


@dataclass(frozen=True, slots=True)
class OrchestrationIdentity:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    agent_protocol_version: int
    policy_digest: str
    work_graph_digest: str
    roster_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id, field="project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, field="run_id"))
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id, field="work_specification_id"))
        if not isinstance(self.work_specification_revision, int) or isinstance(self.work_specification_revision, bool) or self.work_specification_revision < 1:
            raise OrchestrationError("work_specification_revision must be >= 1")
        object.__setattr__(self, "work_specification_digest", _sha256(self.work_specification_digest, field="work_specification_digest"))
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids, required=True))
        if self.agent_protocol_version != AGENT_PROTOCOL_VERSION:
            raise OrchestrationError("unsupported S1 agent protocol version")
        object.__setattr__(self, "policy_digest", _sha256(self.policy_digest, field="policy_digest"))
        object.__setattr__(self, "work_graph_digest", _sha256(self.work_graph_digest, field="work_graph_digest"))
        object.__setattr__(self, "roster_digest", _sha256(self.roster_digest, field="roster_digest"))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "agent_protocol_version": self.agent_protocol_version,
            "policy_digest": self.policy_digest,
            "work_graph_digest": self.work_graph_digest,
            "roster_digest": self.roster_digest,
        }


@dataclass(frozen=True, slots=True)
class UnitPlan:
    work_unit_id: str
    eligible_agent_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "work_unit_id", _token(self.work_unit_id, field="work_unit_id"))
        eligible = tuple(sorted(_sha256(item, field="eligible_agent_digest") for item in self.eligible_agent_digests))
        if not eligible or len(set(eligible)) != len(eligible):
            raise OrchestrationError("unit plan must contain unique eligible agents")
        object.__setattr__(self, "eligible_agent_digests", eligible)

    def as_dict(self) -> dict[str, object]:
        return {
            "work_unit_id": self.work_unit_id,
            "eligible_agent_digests": list(self.eligible_agent_digests),
        }


@dataclass(frozen=True, slots=True)
class TeamPlan:
    identity: OrchestrationIdentity
    graph: WorkGraph
    roster: AdmittedRoster
    limits: OrchestrationLimits
    selected_agent_digests: tuple[str, ...]
    unit_plans: tuple[UnitPlan, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, OrchestrationIdentity) or not isinstance(self.graph, WorkGraph) or not isinstance(self.roster, AdmittedRoster) or not isinstance(self.limits, OrchestrationLimits):
            raise OrchestrationError("team plan requires canonical orchestration values")
        if self.identity.work_graph_digest != self.graph.digest or self.identity.roster_digest != self.roster.digest:
            raise OrchestrationError("team plan identity does not match graph/roster")
        if self.identity.acceptance_ids != self.graph.approved_acceptance_ids:
            raise OrchestrationError("team plan acceptance contract mismatch")
        selected = tuple(sorted(_sha256(item, field="selected_agent_digest") for item in self.selected_agent_digests))
        if not selected or len(selected) > self.limits.max_team_size or len(set(selected)) != len(selected):
            raise OrchestrationError("selected team is empty, duplicate, or over limit")
        roster_ids = {entry.identity_digest for entry in self.roster.entries}
        if not set(selected) <= roster_ids:
            raise OrchestrationError("selected team contains non-admitted agent")
        object.__setattr__(self, "selected_agent_digests", selected)
        plans = tuple(sorted(self.unit_plans, key=lambda item: item.work_unit_id))
        if {item.work_unit_id for item in plans} != {item.unit_id for item in self.graph.units}:
            raise OrchestrationError("unit plan coverage does not match work graph")
        object.__setattr__(self, "unit_plans", plans)

    @property
    def plan_id(self) -> str:
        return _digest({
            "orchestration_protocol_version": ORCHESTRATION_PROTOCOL_VERSION,
            "identity": self.identity.as_dict(),
            "selected_agent_digests": list(self.selected_agent_digests),
            "unit_plans": [item.as_dict() for item in self.unit_plans],
            "limits": self.limits.as_dict(),
        })

    def unit_plan(self, unit_id: str) -> UnitPlan:
        normalized = _token(unit_id, field="unit_id")
        for item in self.unit_plans:
            if item.work_unit_id == normalized:
                return item
        raise OrchestrationError("unknown unit plan")

    def as_dict(self) -> dict[str, object]:
        return {
            "orchestration_protocol_version": ORCHESTRATION_PROTOCOL_VERSION,
            "plan_id": self.plan_id,
            "identity": self.identity.as_dict(),
            "selected_agent_digests": list(self.selected_agent_digests),
            "unit_plans": [item.as_dict() for item in self.unit_plans],
            "limits": self.limits.as_dict(),
            "accepts_source_lineage": False,
            "writes_canonical_source": False,
            "transitions_engineering_run": False,
            "grants_tools_or_provider_authority": False,
            "completes_review": False,
        }


@dataclass(frozen=True, slots=True)
class TeamPlanDecision:
    disposition: OrchestrationDisposition
    reason_code: str
    plan: TeamPlan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "disposition", _disposition(self.disposition))
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        if self.disposition is OrchestrationDisposition.READY and not isinstance(self.plan, TeamPlan):
            raise OrchestrationError("ready team decision requires plan")
        if self.disposition is not OrchestrationDisposition.READY and self.plan is not None:
            raise OrchestrationError("non-ready team decision cannot carry executable plan")

    def as_dict(self) -> dict[str, object]:
        return {
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "plan": self.plan.as_dict() if self.plan else None,
            "grants_authority": False,
        }


@dataclass(frozen=True, slots=True)
class PlanContextDecision:
    matched: bool
    reason: PlanContextReason

    def as_dict(self) -> dict[str, object]:
        return {"matched": self.matched, "reason": self.reason.value, "grants_authority": False}


@dataclass(frozen=True, slots=True)
class AssignmentEvidence:
    plan_id: str
    work_unit_id: str
    agent_identity_digest: str | None
    generation: int
    dependency_digest: str
    disposition: OrchestrationDisposition
    reason_code: str
    operation_id: str | None = None
    request_id: str | None = None
    attempt_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _sha256(self.plan_id, field="plan_id"))
        object.__setattr__(self, "work_unit_id", _token(self.work_unit_id, field="work_unit_id"))
        if self.agent_identity_digest is not None:
            object.__setattr__(self, "agent_identity_digest", _sha256(self.agent_identity_digest, field="agent_identity_digest"))
        if not isinstance(self.generation, int) or isinstance(self.generation, bool) or self.generation < 1:
            raise OrchestrationError("assignment generation must be >= 1")
        object.__setattr__(self, "dependency_digest", _sha256(self.dependency_digest, field="dependency_digest"))
        object.__setattr__(self, "disposition", _disposition(self.disposition))
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        has_agent = self.agent_identity_digest is not None
        ids = (self.operation_id, self.request_id, self.attempt_id)
        if has_agent:
            if any(item is None for item in ids):
                raise OrchestrationError("assigned work requires deterministic dispatch identities")
            for field, value in zip(("operation_id", "request_id", "attempt_id"), ids, strict=True):
                object.__setattr__(self, field, _dispatch_ref(value, field=field))
        elif any(item is not None for item in ids):
            raise OrchestrationError("unassigned work cannot carry dispatch identities")

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "work_unit_id": self.work_unit_id,
            "agent_identity_digest": self.agent_identity_digest,
            "generation": self.generation,
            "dependency_digest": self.dependency_digest,
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "operation_id": self.operation_id,
            "request_id": self.request_id,
            "attempt_id": self.attempt_id,
            "canonical_source_writer": False,
            "transitions_engineering_run": False,
        }


@dataclass(frozen=True, slots=True)
class TeamSchedule:
    plan_id: str
    assignments: tuple[AssignmentEvidence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _sha256(self.plan_id, field="plan_id"))
        assignments = tuple(sorted(self.assignments, key=lambda item: item.work_unit_id))
        if any(not isinstance(item, AssignmentEvidence) or item.plan_id != self.plan_id for item in assignments):
            raise OrchestrationError("schedule contains invalid assignment")
        object.__setattr__(self, "assignments", assignments)

    @property
    def ready(self) -> tuple[AssignmentEvidence, ...]:
        return tuple(item for item in self.assignments if item.disposition in {OrchestrationDisposition.READY, OrchestrationDisposition.REASSIGNED})

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "assignments": [item.as_dict() for item in self.assignments],
            "grants_dispatch_authority": False,
        }


@dataclass(frozen=True, slots=True)
class AssignmentAdmissionDecision:
    admitted: bool
    reason_code: str
    evidence_digest: str
    duplicate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        object.__setattr__(self, "evidence_digest", _sha256(self.evidence_digest, field="evidence_digest"))

    def as_dict(self) -> dict[str, object]:
        return {
            "admitted": self.admitted,
            "reason_code": self.reason_code,
            "evidence_digest": self.evidence_digest,
            "duplicate": self.duplicate,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
        }


@dataclass(frozen=True, slots=True)
class AgentOutcomeObservation:
    plan_id: str
    work_unit_id: str
    assignment_generation: int
    agent_identity_digest: str
    result_digest: str
    status: str
    metrics: tuple[MetricObservation, ...]
    evidence_refs: tuple[AgentEvidenceReference, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _sha256(self.plan_id, field="plan_id"))
        object.__setattr__(self, "work_unit_id", _token(self.work_unit_id, field="work_unit_id"))
        if not isinstance(self.assignment_generation, int) or self.assignment_generation < 1:
            raise OrchestrationError("assignment_generation must be >= 1")
        object.__setattr__(self, "agent_identity_digest", _sha256(self.agent_identity_digest, field="agent_identity_digest"))
        object.__setattr__(self, "result_digest", _sha256(self.result_digest, field="result_digest"))
        if not isinstance(self.status, str) or not self.status:
            raise OrchestrationError("status is required")
        if any(not isinstance(item, MetricObservation) for item in self.metrics):
            raise OrchestrationError("metrics must be S1 observations")
        if any(not isinstance(item, AgentEvidenceReference) for item in self.evidence_refs):
            raise OrchestrationError("evidence refs must be S1 references")

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "work_unit_id": self.work_unit_id,
            "assignment_generation": self.assignment_generation,
            "agent_identity_digest": self.agent_identity_digest,
            "result_digest": self.result_digest,
            "status": self.status,
            "metrics": [item.as_dict() for item in self.metrics],
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
            "quality_is_authoritative": False,
            "cost_is_inferred": False,
            "grants_authority": False,
        }


@dataclass(frozen=True, slots=True)
class ReassignmentDecision:
    disposition: OrchestrationDisposition
    reason_code: str
    assignment: AssignmentEvidence | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "disposition", _disposition(self.disposition))
        object.__setattr__(self, "reason_code", _reason(self.reason_code))

    def as_dict(self) -> dict[str, object]:
        return {
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "assignment": self.assignment.as_dict() if self.assignment else None,
            "mutates_worker_state": False,
            "grants_authority": False,
        }


@dataclass(frozen=True, slots=True)
class BoundDecision:
    allowed: bool
    disposition: OrchestrationDisposition
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "disposition", _disposition(self.disposition))
        object.__setattr__(self, "reason_code", _reason(self.reason_code))

    def as_dict(self) -> dict[str, object]:
        return {"allowed": self.allowed, "disposition": self.disposition.value, "reason_code": self.reason_code}


def build_team_plan(
    *,
    project_id: str,
    run_id: str,
    work_specification_id: str,
    work_specification_revision: int,
    work_specification_digest: str,
    graph: WorkGraph,
    roster: AdmittedRoster,
    policy_digest: str,
    limits: OrchestrationLimits | None = None,
) -> TeamPlanDecision:
    limits = limits or OrchestrationLimits()
    identity = OrchestrationIdentity(
        project_id=project_id,
        run_id=run_id,
        work_specification_id=work_specification_id,
        work_specification_revision=work_specification_revision,
        work_specification_digest=work_specification_digest,
        acceptance_ids=graph.approved_acceptance_ids,
        agent_protocol_version=AGENT_PROTOCOL_VERSION,
        policy_digest=policy_digest,
        work_graph_digest=graph.digest,
        roster_digest=roster.digest,
    )
    eligibility: dict[str, tuple[str, ...]] = {}
    for unit in graph.units:
        eligible = tuple(entry.identity_digest for entry in roster.entries if entry.supports(unit))
        if not eligible:
            return TeamPlanDecision(OrchestrationDisposition.HUMAN_REQUIRED, "NO_COMPATIBLE_ADMITTED_AGENT")
        eligibility[unit.unit_id] = eligible

    all_agents = tuple(entry.identity_digest for entry in roster.entries)
    parallel_pair = _parallel_pair(graph, eligibility)
    selected: tuple[str, ...] | None = None
    minimum_size = 2 if parallel_pair else 1
    for size in range(minimum_size, min(limits.max_team_size, len(all_agents)) + 1):
        for candidate in combinations(all_agents, size):
            if not all(set(eligibility[unit.unit_id]) & set(candidate) for unit in graph.units):
                continue
            if parallel_pair and not _candidate_supports_pair(candidate, parallel_pair, eligibility):
                continue
            selected = candidate
            break
        if selected:
            break
    if selected is None:
        return TeamPlanDecision(OrchestrationDisposition.HUMAN_REQUIRED, "TEAM_SIZE_OR_CAPABILITY_BOUND")

    plan = TeamPlan(
        identity=identity,
        graph=graph,
        roster=roster,
        limits=limits,
        selected_agent_digests=selected,
        unit_plans=tuple(UnitPlan(unit.unit_id, eligibility[unit.unit_id]) for unit in graph.units),
    )
    return TeamPlanDecision(OrchestrationDisposition.READY, "TEAM_PLAN_READY", plan)


def verify_plan_context(
    plan: TeamPlan,
    *,
    project_id: str,
    run_id: str,
    work_specification_id: str,
    work_specification_revision: int,
    work_specification_digest: str,
    acceptance_ids: tuple[str, ...],
    policy_digest: str,
    graph: WorkGraph,
    roster: AdmittedRoster,
    agent_protocol_version: int = AGENT_PROTOCOL_VERSION,
) -> PlanContextDecision:
    checks = (
        (plan.identity.project_id == _uuid(project_id, field="project_id"), PlanContextReason.PROJECT_MISMATCH),
        (plan.identity.run_id == _uuid(run_id, field="run_id"), PlanContextReason.RUN_MISMATCH),
        (
            plan.identity.work_specification_id == _uuid(work_specification_id, field="work_specification_id")
            and plan.identity.work_specification_revision == work_specification_revision
            and plan.identity.work_specification_digest == work_specification_digest,
            PlanContextReason.WORK_SPECIFICATION_MISMATCH,
        ),
        (plan.identity.acceptance_ids == _acceptance_ids(acceptance_ids, required=True), PlanContextReason.ACCEPTANCE_CONTRACT_MISMATCH),
        (plan.identity.agent_protocol_version == agent_protocol_version, PlanContextReason.AGENT_PROTOCOL_MISMATCH),
        (plan.identity.policy_digest == _sha256(policy_digest, field="policy_digest"), PlanContextReason.POLICY_DRIFT),
        (plan.identity.work_graph_digest == graph.digest, PlanContextReason.WORK_GRAPH_DRIFT),
        (plan.identity.roster_digest == roster.digest, PlanContextReason.ROSTER_DRIFT),
    )
    for matched, reason in checks:
        if not matched:
            return PlanContextDecision(False, reason)
    return PlanContextDecision(True, PlanContextReason.MATCH)


def schedule_team_plan(
    plan: TeamPlan,
    *,
    completed_work_units: Iterable[str] = (),
    generation_by_work_unit: dict[str, int] | None = None,
) -> TeamSchedule:
    completed = {_token(item, field="completed_work_unit") for item in completed_work_units}
    known = {unit.unit_id for unit in plan.graph.units}
    if not completed <= known:
        raise OrchestrationError("completed work contains unknown unit")
    generations = generation_by_work_unit or {}
    assignments: list[AssignmentEvidence] = []
    active_units: list[WorkUnit] = []
    used_agents: set[str] = set()

    for unit in plan.graph.units:
        generation = generations.get(unit.unit_id, 1)
        if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
            raise OrchestrationError("assignment generation must be >= 1")
        if unit.unit_id in completed:
            assignments.append(_assignment(plan, unit, None, generation, OrchestrationDisposition.COMPLETED, "WORK_UNIT_COMPLETED"))
            continue
        if not set(unit.dependencies) <= completed:
            assignments.append(_assignment(plan, unit, None, generation, OrchestrationDisposition.WAITING_DEPENDENCY, "DEPENDENCY_NOT_COMPLETE"))
            continue
        selected_eligible = tuple(
            item for item in plan.unit_plan(unit.unit_id).eligible_agent_digests if item in plan.selected_agent_digests
        )
        agent = next((item for item in selected_eligible if item not in used_agents), None)
        if agent is None:
            assignments.append(_assignment(plan, unit, None, generation, OrchestrationDisposition.SERIALIZED_COORDINATION, "AGENT_CONCURRENCY_SERIALIZED"))
            continue
        if len(active_units) >= plan.limits.max_concurrency:
            assignments.append(_assignment(plan, unit, None, generation, OrchestrationDisposition.SERIALIZED_COORDINATION, "CONCURRENCY_BOUND"))
            continue
        if any(_units_conflict(unit, active) for active in active_units):
            assignments.append(_assignment(plan, unit, None, generation, OrchestrationDisposition.SERIALIZED_COORDINATION, "COORDINATION_DOMAIN_SERIALIZED"))
            continue
        assignments.append(_assignment(plan, unit, agent, generation, OrchestrationDisposition.READY, "DEPENDENCIES_READY"))
        active_units.append(unit)
        used_agents.add(agent)
    return TeamSchedule(plan.plan_id, tuple(assignments))


def create_agent_task_request(
    plan: TeamPlan,
    assignment: AssignmentEvidence,
    *,
    source_context: AgentSourceContext | None = None,
) -> AgentTaskRequest:
    _validate_assignment_for_plan(plan, assignment)
    if assignment.disposition not in {OrchestrationDisposition.READY, OrchestrationDisposition.REASSIGNED}:
        raise OrchestrationError("only ready/reassigned work can create S1 task request")
    if assignment.agent_identity_digest is None or assignment.operation_id is None or assignment.request_id is None or assignment.attempt_id is None:
        raise OrchestrationError("assignment lacks agent or dispatch identity")
    unit = plan.graph.get(assignment.work_unit_id)
    agent = plan.roster.get(assignment.agent_identity_digest).identity
    return AgentTaskRequest.create(
        project_id=plan.identity.project_id,
        run_id=plan.identity.run_id,
        work_specification_id=plan.identity.work_specification_id,
        work_specification_revision=plan.identity.work_specification_revision,
        work_specification_digest=plan.identity.work_specification_digest,
        acceptance_ids=unit.acceptance_ids,
        operation_id=assignment.operation_id,
        request_id=assignment.request_id,
        attempt_number=assignment.generation,
        attempt_id=assignment.attempt_id,
        agent=agent,
        work_kind=unit.work_kind,
        source_context=source_context,
        requested_capabilities=unit.required_capabilities,
        context_refs=unit.context_refs,
    )


def admit_assignment_result(
    plan: TeamPlan,
    assignment: AssignmentEvidence,
    *,
    expected_task: AgentTaskRequest,
    result: AgentResult,
    current_generation: int,
    revoked: bool = False,
    accepted_terminal_digest: str | None = None,
) -> AssignmentAdmissionDecision:
    _validate_assignment_for_plan(plan, assignment)
    if current_generation != assignment.generation:
        return AssignmentAdmissionDecision(False, "STALE_ASSIGNMENT_GENERATION", result.digest)
    if not _task_matches_assignment(plan, assignment, expected_task):
        return AssignmentAdmissionDecision(False, "TASK_ASSIGNMENT_MISMATCH", result.digest)
    decision = verify_result_admission(
        expected_task=expected_task,
        result=result,
        current_attempt_number=current_generation,
        revoked=revoked,
        accepted_terminal_digest=accepted_terminal_digest,
    )
    reason = "S1_" + decision.reason.value
    return AssignmentAdmissionDecision(decision.admitted, reason, decision.evidence_digest, decision.duplicate)


def observe_admitted_result(
    plan: TeamPlan,
    assignment: AssignmentEvidence,
    *,
    admission: AssignmentAdmissionDecision,
    result: AgentResult,
) -> AgentOutcomeObservation:
    _validate_assignment_for_plan(plan, assignment)
    if not admission.admitted:
        raise OrchestrationError("only admitted S1 result can become orchestration observation")
    if assignment.agent_identity_digest is None:
        raise OrchestrationError("assignment has no agent identity")
    return AgentOutcomeObservation(
        plan_id=plan.plan_id,
        work_unit_id=assignment.work_unit_id,
        assignment_generation=assignment.generation,
        agent_identity_digest=assignment.agent_identity_digest,
        result_digest=result.digest,
        status=result.status.value,
        metrics=result.metrics,
        evidence_refs=result.evidence_refs,
    )


def reassign_assignment(
    plan: TeamPlan,
    current_assignment: AssignmentEvidence,
    *,
    worker_health: WorkerHealthSnapshot,
    expected_worker_execution_id: str,
    expected_worker_lease_generation: int,
    reassignment_count: int,
) -> ReassignmentDecision:
    _validate_assignment_for_plan(plan, current_assignment)
    if worker_health.project_id != plan.identity.project_id or worker_health.run_id != plan.identity.run_id:
        return ReassignmentDecision(OrchestrationDisposition.BLOCKED, "WORKER_IDENTITY_MISMATCH")
    if worker_health.execution_id != expected_worker_execution_id:
        return ReassignmentDecision(OrchestrationDisposition.BLOCKED, "WORKER_EXECUTION_MISMATCH")
    if worker_health.lease_generation != expected_worker_lease_generation:
        return ReassignmentDecision(OrchestrationDisposition.BLOCKED, "STALE_WORKER_GENERATION")
    if worker_health.human_required:
        return ReassignmentDecision(OrchestrationDisposition.HUMAN_REQUIRED, "WORKER_HUMAN_REQUIRED")
    if worker_health.next_recovery_action is not RecoveryAction.REASSIGN:
        return ReassignmentDecision(OrchestrationDisposition.BLOCKED, "WORKER_DID_NOT_AUTHORIZE_REASSIGN")
    if not isinstance(reassignment_count, int) or isinstance(reassignment_count, bool) or reassignment_count < 0:
        raise OrchestrationError("reassignment_count must be non-negative integer")
    if reassignment_count >= plan.limits.max_reassignments_per_work_unit:
        return ReassignmentDecision(OrchestrationDisposition.HUMAN_REQUIRED, "REASSIGNMENT_BOUND_EXHAUSTED")
    if current_assignment.agent_identity_digest is None:
        return ReassignmentDecision(OrchestrationDisposition.BLOCKED, "CURRENT_ASSIGNMENT_HAS_NO_AGENT")
    unit = plan.graph.get(current_assignment.work_unit_id)
    alternates = tuple(
        item for item in plan.unit_plan(unit.unit_id).eligible_agent_digests if item != current_assignment.agent_identity_digest
    )
    if not alternates:
        return ReassignmentDecision(OrchestrationDisposition.HUMAN_REQUIRED, "NO_ALTERNATE_ADMITTED_AGENT")
    replacement = _assignment(
        plan,
        unit,
        alternates[0],
        current_assignment.generation + 1,
        OrchestrationDisposition.REASSIGNED,
        "AUTHORITATIVE_WORKER_REASSIGNMENT",
    )
    return ReassignmentDecision(OrchestrationDisposition.REASSIGNED, "AUTHORITATIVE_WORKER_REASSIGNMENT", replacement)


def evaluate_orchestration_bounds(plan: TeamPlan, *, replan_count: int, no_progress_count: int) -> BoundDecision:
    for field, value in (("replan_count", replan_count), ("no_progress_count", no_progress_count)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise OrchestrationError(f"{field} must be a non-negative integer")
    if replan_count >= plan.limits.max_replans:
        return BoundDecision(False, OrchestrationDisposition.HUMAN_REQUIRED, "REPLAN_BOUND_EXHAUSTED")
    if no_progress_count >= plan.limits.max_no_progress:
        return BoundDecision(False, OrchestrationDisposition.HUMAN_REQUIRED, "NO_PROGRESS_BOUND_EXHAUSTED")
    return BoundDecision(True, OrchestrationDisposition.READY, "BOUNDS_AVAILABLE")


def safe_orchestration_json(value: object) -> str:
    allowed = (
        AdmittedRoster,
        WorkGraph,
        OrchestrationIdentity,
        TeamPlan,
        TeamPlanDecision,
        PlanContextDecision,
        AssignmentEvidence,
        TeamSchedule,
        AssignmentAdmissionDecision,
        AgentOutcomeObservation,
        ReassignmentDecision,
        BoundDecision,
    )
    if not isinstance(value, allowed):
        raise OrchestrationError("safe_orchestration_json requires canonical S2 evidence")
    return json.dumps(value.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _parallel_pair(graph: WorkGraph, eligibility: dict[str, tuple[str, ...]]) -> tuple[str, str] | None:
    dependencies = {unit.unit_id: set(unit.dependencies) for unit in graph.units}

    def depends_on(unit_id: str, ancestor_id: str) -> bool:
        pending = list(dependencies[unit_id])
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current == ancestor_id:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(dependencies[current])
        return False

    for left, right in combinations(graph.units, 2):
        if depends_on(left.unit_id, right.unit_id) or depends_on(right.unit_id, left.unit_id):
            continue
        if _units_conflict(left, right):
            continue
        if any(a != b for a in eligibility[left.unit_id] for b in eligibility[right.unit_id]):
            return (left.unit_id, right.unit_id)
    return None


def _candidate_supports_pair(candidate: tuple[str, ...], pair: tuple[str, str], eligibility: dict[str, tuple[str, ...]]) -> bool:
    allowed = set(candidate)
    left = [item for item in eligibility[pair[0]] if item in allowed]
    right = [item for item in eligibility[pair[1]] if item in allowed]
    return any(a != b for a in left for b in right)


def _units_conflict(left: WorkUnit, right: WorkUnit) -> bool:
    if not left.coordination_domains or not right.coordination_domains:
        return True
    if set(left.coordination_domains) & set(right.coordination_domains):
        return True
    if left.requires_canonical_mutation and right.requires_canonical_mutation:
        return True
    return False


def _assignment(
    plan: TeamPlan,
    unit: WorkUnit,
    agent_digest: str | None,
    generation: int,
    disposition: OrchestrationDisposition,
    reason_code: str,
) -> AssignmentEvidence:
    dependency_digest = _digest({"plan_id": plan.plan_id, "work_unit_id": unit.unit_id, "dependencies": list(unit.dependencies)})
    if agent_digest is None:
        return AssignmentEvidence(plan.plan_id, unit.unit_id, None, generation, dependency_digest, disposition, reason_code)
    stem = f"{plan.plan_id[:20]}:{unit.unit_id}:g{generation}"
    return AssignmentEvidence(
        plan.plan_id,
        unit.unit_id,
        agent_digest,
        generation,
        dependency_digest,
        disposition,
        reason_code,
        f"orchestration:{stem}",
        f"request:{stem}",
        f"attempt:{stem}",
    )


def _validate_assignment_for_plan(plan: TeamPlan, assignment: AssignmentEvidence) -> None:
    if not isinstance(plan, TeamPlan) or not isinstance(assignment, AssignmentEvidence):
        raise OrchestrationError("plan and assignment are required")
    if assignment.plan_id != plan.plan_id:
        raise OrchestrationError("assignment belongs to different team plan")
    plan.graph.get(assignment.work_unit_id)
    if assignment.agent_identity_digest is not None and assignment.agent_identity_digest not in plan.unit_plan(assignment.work_unit_id).eligible_agent_digests:
        raise OrchestrationError("assignment agent is not eligible for work unit")


def _task_matches_assignment(plan: TeamPlan, assignment: AssignmentEvidence, task: AgentTaskRequest) -> bool:
    if not isinstance(task, AgentTaskRequest) or assignment.agent_identity_digest is None:
        return False
    unit = plan.graph.get(assignment.work_unit_id)
    binding = task.binding
    return (
        binding.project_id == plan.identity.project_id
        and binding.run_id == plan.identity.run_id
        and binding.work_specification_id == plan.identity.work_specification_id
        and binding.work_specification_revision == plan.identity.work_specification_revision
        and binding.work_specification_digest == plan.identity.work_specification_digest
        and binding.acceptance_ids == unit.acceptance_ids
        and binding.operation_id == assignment.operation_id
        and binding.request_id == assignment.request_id
        and binding.attempt_number == assignment.generation
        and binding.attempt_id == assignment.attempt_id
        and binding.agent_identity_digest == assignment.agent_identity_digest
        and task.agent.digest == assignment.agent_identity_digest
        and task.work_kind == unit.work_kind
        and task.requested_capabilities == unit.required_capabilities
        and task.context_refs == unit.context_refs
    )


def _validate_acyclic_and_depth(units: tuple[WorkUnit, ...]) -> None:
    by_id = {unit.unit_id: unit for unit in units}
    visiting: set[str] = set()
    visited: set[str] = set()
    depth_cache: dict[str, int] = {}

    def visit(unit_id: str) -> int:
        if unit_id in visiting:
            raise OrchestrationError("work graph contains dependency cycle")
        if unit_id in visited:
            return depth_cache[unit_id]
        visiting.add(unit_id)
        depth = 1
        for dependency in by_id[unit_id].dependencies:
            depth = max(depth, 1 + visit(dependency))
        visiting.remove(unit_id)
        visited.add(unit_id)
        depth_cache[unit_id] = depth
        if depth > _MAX_GRAPH_DEPTH:
            raise OrchestrationError("work graph exceeds depth bound")
        return depth

    for unit in units:
        visit(unit.unit_id)


def _uuid(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise OrchestrationError(f"{field} must be UUID string")
    try:
        return str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise OrchestrationError(f"{field} must be UUID string") from exc


def _sha256(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise OrchestrationError(f"{field} must be sha256 hex")
    return value


def _token(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise OrchestrationError(f"{field} must be bounded normalized token")
    return value


def _dispatch_ref(value: str | None, *, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 191 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,190}", value):
        raise OrchestrationError(f"{field} must be bounded dispatch reference")
    return value


def _token_set(values: Iterable[str], *, field: str, required: bool = False) -> tuple[str, ...]:
    normalized = tuple(sorted(_token(item, field=field) for item in tuple(values)))
    if required and not normalized:
        raise OrchestrationError(f"{field} is required")
    if len(set(normalized)) != len(normalized):
        raise OrchestrationError(f"{field} must be unique")
    return normalized


def _acceptance_ids(values: Iterable[str], *, required: bool = False) -> tuple[str, ...]:
    items = tuple(values)
    if required and not items:
        raise OrchestrationError("acceptance_ids are required")
    if any(not isinstance(item, str) or not _ACCEPTANCE_ID_RE.fullmatch(item) for item in items):
        raise OrchestrationError("acceptance_ids contain invalid value")
    if len(set(items)) != len(items):
        raise OrchestrationError("acceptance_ids must be unique")
    return items


def _reason(value: str) -> str:
    if not isinstance(value, str) or not _REASON_RE.fullmatch(value):
        raise OrchestrationError("reason code is invalid")
    return value


def _disposition(value: OrchestrationDisposition | str) -> OrchestrationDisposition:
    try:
        return value if isinstance(value, OrchestrationDisposition) else OrchestrationDisposition(value)
    except (TypeError, ValueError) as exc:
        raise OrchestrationError("invalid orchestration disposition") from exc


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
