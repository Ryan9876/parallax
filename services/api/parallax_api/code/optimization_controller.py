"""Bounded development optimization control plane, including Wave 6 outcome routing."""

from __future__ import annotations

from .optimization_contracts import *  # noqa: F401,F403
from .optimization_graph import *  # noqa: F401,F403
from .optimization_worker import *  # noqa: F401,F403
from .optimization_impact import *  # noqa: F401,F403
from .optimization_reuse import *  # noqa: F401,F403
from .optimization_preflight import *  # noqa: F401,F403
from .optimization_telemetry import *  # noqa: F401,F403
from .optimization_state import *  # noqa: F401,F403

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import math
import re
from typing import Iterable
from uuid import UUID

from .agent_protocol import (
    AGENT_PROTOCOL_VERSION,
    MetricAvailability,
    MetricName,
    MetricObservation,
    MetricProvenanceKind,
)
from .agent_team_orchestration import ORCHESTRATION_PROTOCOL_VERSION
from parallax_api.evaluation.agent_judgment import (
    EVALUATION_PROTOCOL_VERSION,
    DimensionVerdict,
    EvaluationOutcome,
    EvaluationRecord,
)

ROUTING_PROTOCOL_VERSION = 1
_MAX_VALUE = 1_000_000_000_000.0
_SHA = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_AC = re.compile(r"^AC-[0-9]{2,3}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
_UNIT = re.compile(r"^[a-z][a-z0-9._/-]{0,31}$")


class OutcomeRoutingError(ValueError):
    pass


class StrategyKind(StrEnum):
    SINGLE_AGENT = "SINGLE_AGENT"
    TEAM = "TEAM"


class RoutingMetricName(StrEnum):
    DURATION = "duration"
    COST = "cost"
    RETRIES = "retries"
    REASSIGNMENTS = "reassignments"
    REPLANS = "replans"
    INTERVENTIONS = "interventions"


class EvidenceState(StrEnum):
    OBSERVED = "OBSERVED"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    INVALID = "INVALID"


class RoutingProvenance(StrEnum):
    PROVIDER = "PROVIDER"
    PARALLAX = "PARALLAX"
    ESTIMATE = "ESTIMATE"


class CompletionState(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    UNKNOWN = "UNKNOWN"


class EligibilityReason(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    CONTEXT_MISMATCH = "CONTEXT_MISMATCH"
    STRATEGY_NOT_PERMITTED = "STRATEGY_NOT_PERMITTED"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    AUTHORITY_MISMATCH = "AUTHORITY_MISMATCH"
    DEPENDENCY_MISMATCH = "DEPENDENCY_MISMATCH"
    MISSING_OUTCOME_EVIDENCE = "MISSING_OUTCOME_EVIDENCE"
    PROTECTED_VALIDATION_REQUIRED = "PROTECTED_VALIDATION_REQUIRED"
    EVALUATION_REQUIRED = "EVALUATION_REQUIRED"
    EVALUATION_POLICY_MISMATCH = "EVALUATION_POLICY_MISMATCH"
    EVALUATION_IDENTITY_MISMATCH = "EVALUATION_IDENTITY_MISMATCH"
    EVALUATION_REJECTED = "EVALUATION_REJECTED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    CROSS_PROJECT_EVIDENCE = "CROSS_PROJECT_EVIDENCE"
    UNTRUSTED_OBSERVED_EVIDENCE = "UNTRUSTED_OBSERVED_EVIDENCE"
    STALE_MANDATORY_EVIDENCE = "STALE_MANDATORY_EVIDENCE"
    INVALID_MANDATORY_EVIDENCE = "INVALID_MANDATORY_EVIDENCE"
    MISSING_MANDATORY_EVIDENCE = "MISSING_MANDATORY_EVIDENCE"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
    QUALITY_FLOOR_FAILED = "QUALITY_FLOOR_FAILED"
    QUALITY_EVIDENCE_INSUFFICIENT = "QUALITY_EVIDENCE_INSUFFICIENT"
    COMPLETION_REQUIRED = "COMPLETION_REQUIRED"


class RoutingDisposition(StrEnum):
    SELECTED = "SELECTED"
    FALLBACK_SELECTED = "FALLBACK_SELECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NO_ADMISSIBLE_STRATEGY = "NO_ADMISSIBLE_STRATEGY"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    POLICY_REJECTED = "POLICY_REJECTED"


class RoutingAdmissionReason(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
    CONTEXT_MISMATCH = "CONTEXT_MISMATCH"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    COMPETING_RECORD = "COMPETING_RECORD"


@dataclass(frozen=True, slots=True)
class RoutingContext:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    orchestration_identity_digest: str
    evaluation_policy_digest: str
    routing_policy_id: str
    routing_policy_version: str
    routing_policy_digest: str
    decision_id: str
    decision_sequence: int
    agent_protocol_version: int = AGENT_PROTOCOL_VERSION
    orchestration_protocol_version: int = ORCHESTRATION_PROTOCOL_VERSION
    evaluation_protocol_version: int = EVALUATION_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id, "work_specification_id"))
        if not isinstance(self.work_specification_revision, int) or isinstance(self.work_specification_revision, bool) or self.work_specification_revision < 1:
            raise OutcomeRoutingError("work_specification_revision must be >= 1")
        object.__setattr__(self, "work_specification_digest", _sha(self.work_specification_digest, "work_specification_digest"))
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        object.__setattr__(self, "orchestration_identity_digest", _sha(self.orchestration_identity_digest, "orchestration_identity_digest"))
        object.__setattr__(self, "evaluation_policy_digest", _sha(self.evaluation_policy_digest, "evaluation_policy_digest"))
        object.__setattr__(self, "routing_policy_id", _token(self.routing_policy_id, "routing_policy_id"))
        object.__setattr__(self, "routing_policy_version", _version(self.routing_policy_version, "routing_policy_version"))
        object.__setattr__(self, "routing_policy_digest", _sha(self.routing_policy_digest, "routing_policy_digest"))
        object.__setattr__(self, "decision_id", _reference(self.decision_id, "decision_id"))
        object.__setattr__(self, "decision_sequence", _integer(self.decision_sequence, 0, 1_000_000_000, "decision_sequence"))
        if (self.agent_protocol_version, self.orchestration_protocol_version, self.evaluation_protocol_version) != (AGENT_PROTOCOL_VERSION, ORCHESTRATION_PROTOCOL_VERSION, EVALUATION_PROTOCOL_VERSION):
            raise OutcomeRoutingError("accepted S1/S2/S3 protocol identity drift")

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "routing_protocol_version": ROUTING_PROTOCOL_VERSION,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "agent_protocol_version": self.agent_protocol_version,
            "orchestration_protocol_version": self.orchestration_protocol_version,
            "orchestration_identity_digest": self.orchestration_identity_digest,
            "evaluation_protocol_version": self.evaluation_protocol_version,
            "evaluation_policy_digest": self.evaluation_policy_digest,
            "routing_policy_id": self.routing_policy_id,
            "routing_policy_version": self.routing_policy_version,
            "routing_policy_digest": self.routing_policy_digest,
            "decision_id": self.decision_id,
            "decision_sequence": self.decision_sequence,
        }


@dataclass(frozen=True, slots=True)
class DevelopmentStrategy:
    strategy_id: str
    strategy_version: str
    kind: StrategyKind
    agent_identity_digests: tuple[str, ...]
    work_profile: str
    required_capabilities: tuple[str, ...] = ()
    team_plan_digest: str | None = None
    provider_class: str | None = None
    model_class: str | None = None
    conservative_fallback: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", _token(self.strategy_id, "strategy_id"))
        object.__setattr__(self, "strategy_version", _version(self.strategy_version, "strategy_version"))
        try:
            object.__setattr__(self, "kind", self.kind if isinstance(self.kind, StrategyKind) else StrategyKind(self.kind))
        except (TypeError, ValueError) as exc:
            raise OutcomeRoutingError("invalid strategy kind") from exc
        agents = tuple(sorted(_sha(v, "agent_identity_digest") for v in self.agent_identity_digests))
        if not agents or len(agents) > 16 or len(set(agents)) != len(agents):
            raise OutcomeRoutingError("invalid agent identity set")
        if self.kind is StrategyKind.SINGLE_AGENT and len(agents) != 1:
            raise OutcomeRoutingError("single-agent strategy requires exactly one agent")
        if self.kind is StrategyKind.TEAM and len(agents) < 2:
            raise OutcomeRoutingError("team strategy requires at least two agents")
        object.__setattr__(self, "agent_identity_digests", agents)
        object.__setattr__(self, "work_profile", _token(self.work_profile, "work_profile"))
        object.__setattr__(self, "required_capabilities", _tokens(self.required_capabilities, "required_capabilities"))
        if self.kind is StrategyKind.TEAM:
            if self.team_plan_digest is None:
                raise OutcomeRoutingError("team strategy requires team_plan_digest")
            object.__setattr__(self, "team_plan_digest", _sha(self.team_plan_digest, "team_plan_digest"))
        elif self.team_plan_digest is not None:
            raise OutcomeRoutingError("single-agent strategy cannot carry team_plan_digest")
        for field in ("provider_class", "model_class"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _token(value, field))
        if not isinstance(self.conservative_fallback, bool):
            raise OutcomeRoutingError("conservative_fallback must be bool")

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "kind": self.kind.value,
            "agent_identity_digests": list(self.agent_identity_digests),
            "work_profile": self.work_profile,
            "required_capabilities": list(self.required_capabilities),
            "team_plan_digest": self.team_plan_digest,
            "provider_class": self.provider_class,
            "model_class": self.model_class,
            "conservative_fallback": self.conservative_fallback,
            "grants_authority": False,
            "contains_credentials": False,
        }


@dataclass(frozen=True, slots=True)
class StrategyAdmissionSnapshot:
    context_digest: str
    strategy_digest: str
    project_id: str
    source_ref: str
    source_digest: str
    capability_compatible: bool
    authority_compatible: bool
    dependency_compatible: bool
    admitted_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in ("context_digest", "strategy_digest", "source_digest"):
            object.__setattr__(self, field, _sha(getattr(self, field), field))
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "source_ref", _reference(self.source_ref, "source_ref"))
        for field in ("capability_compatible", "authority_compatible", "dependency_compatible"):
            if not isinstance(getattr(self, field), bool):
                raise OutcomeRoutingError(f"{field} must be bool")
        object.__setattr__(self, "admitted_capabilities", _tokens(self.admitted_capabilities, "admitted_capabilities"))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "context_digest": self.context_digest,
            "strategy_digest": self.strategy_digest,
            "project_id": self.project_id,
            "source_ref": self.source_ref,
            "source_digest": self.source_digest,
            "capability_compatible": self.capability_compatible,
            "authority_compatible": self.authority_compatible,
            "dependency_compatible": self.dependency_compatible,
            "admitted_capabilities": list(self.admitted_capabilities),
            "server_owned": True,
            "grants_new_authority": False,
        }


@dataclass(frozen=True, slots=True)
class RoutingMetricEvidence:
    metric: RoutingMetricName
    state: EvidenceState
    provenance: RoutingProvenance | None
    source_ref: str
    source_digest: str
    sequence: int
    project_id: str | None
    value: float | None = None
    unit: str | None = None
    currency: str | None = None
    sanitized_generalized: bool = False

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "metric", self.metric if isinstance(self.metric, RoutingMetricName) else RoutingMetricName(self.metric))
            object.__setattr__(self, "state", self.state if isinstance(self.state, EvidenceState) else EvidenceState(self.state))
            if self.provenance is not None:
                object.__setattr__(self, "provenance", self.provenance if isinstance(self.provenance, RoutingProvenance) else RoutingProvenance(self.provenance))
        except (TypeError, ValueError) as exc:
            raise OutcomeRoutingError("invalid metric enum") from exc
        object.__setattr__(self, "source_ref", _reference(self.source_ref, "source_ref"))
        object.__setattr__(self, "source_digest", _sha(self.source_digest, "source_digest"))
        object.__setattr__(self, "sequence", _integer(self.sequence, 0, 1_000_000_000, "sequence"))
        if not isinstance(self.sanitized_generalized, bool):
            raise OutcomeRoutingError("sanitized_generalized must be bool")
        if self.sanitized_generalized:
            if self.project_id is not None:
                raise OutcomeRoutingError("sanitized generalized metric cannot retain Project identity")
        elif self.project_id is None:
            raise OutcomeRoutingError("Project-private metric requires project_id")
        else:
            object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        numeric = self.state in {EvidenceState.OBSERVED, EvidenceState.ESTIMATED}
        if numeric:
            if self.provenance is None:
                raise OutcomeRoutingError("numeric evidence requires provenance")
            if self.state is EvidenceState.OBSERVED and self.provenance is RoutingProvenance.ESTIMATE:
                raise OutcomeRoutingError("estimate cannot masquerade as observed")
            if self.state is EvidenceState.ESTIMATED and self.provenance is not RoutingProvenance.ESTIMATE:
                raise OutcomeRoutingError("estimated state requires estimate provenance")
            object.__setattr__(self, "value", _number(self.value, "value"))
            if not isinstance(self.unit, str) or not _UNIT.fullmatch(self.unit):
                raise OutcomeRoutingError("numeric evidence requires bounded unit")
            if self.metric is RoutingMetricName.COST:
                if not isinstance(self.currency, str) or not re.fullmatch(r"[A-Z]{3}", self.currency):
                    raise OutcomeRoutingError("cost requires ISO currency")
            elif self.currency is not None:
                raise OutcomeRoutingError("currency is only valid for cost")
        elif any(v is not None for v in (self.provenance, self.value, self.unit, self.currency)):
            raise OutcomeRoutingError("non-numeric evidence cannot carry favorable numeric fields")

    @classmethod
    def from_agent_metric(
        cls,
        metric: MetricObservation,
        *,
        project_id: str,
        source_digest: str,
        sequence: int,
        admitted_source_digests: frozenset[str],
    ) -> "RoutingMetricEvidence":
        if not isinstance(metric, MetricObservation):
            raise OutcomeRoutingError("metric must be S1 MetricObservation")
        mapping = {MetricName.DURATION: RoutingMetricName.DURATION, MetricName.COST: RoutingMetricName.COST}
        if metric.metric not in mapping:
            raise OutcomeRoutingError("S1 metric is not an S4 economic metric")
        source_ref = metric.provenance_ref or f"metric:{metric.metric.value}:{metric.source}"
        if metric.availability is MetricAvailability.OBSERVED:
            if source_digest not in admitted_source_digests:
                return cls(mapping[metric.metric], EvidenceState.INVALID, None, source_ref, source_digest, sequence, project_id)
            pmap = {
                MetricProvenanceKind.PROVIDER: RoutingProvenance.PROVIDER,
                MetricProvenanceKind.PARALLAX: RoutingProvenance.PARALLAX,
                MetricProvenanceKind.ESTIMATE: RoutingProvenance.ESTIMATE,
            }
            provenance = pmap[metric.provenance_kind]
            state = EvidenceState.ESTIMATED if provenance is RoutingProvenance.ESTIMATE else EvidenceState.OBSERVED
            return cls(
                mapping[metric.metric], state, provenance, source_ref, source_digest, sequence, project_id,
                float(metric.value), metric.unit, metric.currency,
            )
        state = EvidenceState.UNAVAILABLE if metric.availability is MetricAvailability.UNAVAILABLE else EvidenceState.UNKNOWN
        return cls(mapping[metric.metric], state, None, source_ref, source_digest, sequence, project_id)

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric.value,
            "state": self.state.value,
            "provenance": self.provenance.value if self.provenance else None,
            "source_ref": self.source_ref,
            "source_digest": self.source_digest,
            "sequence": self.sequence,
            "project_id": self.project_id,
            "value": self.value,
            "unit": self.unit,
            "currency": self.currency,
            "sanitized_generalized": self.sanitized_generalized,
        }


@dataclass(frozen=True, slots=True)
class CompletionObservation:
    state: CompletionState
    source_ref: str
    source_digest: str
    project_id: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "state", self.state if isinstance(self.state, CompletionState) else CompletionState(self.state))
        except (TypeError, ValueError) as exc:
            raise OutcomeRoutingError("invalid completion state") from exc
        object.__setattr__(self, "source_ref", _reference(self.source_ref, "source_ref"))
        object.__setattr__(self, "source_digest", _sha(self.source_digest, "source_digest"))
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "source_ref": self.source_ref,
            "source_digest": self.source_digest,
            "project_id": self.project_id,
            "provenance": "PARALLAX",
        }


@dataclass(frozen=True, slots=True)
class StrategyOutcomeEvidence:
    context_digest: str
    strategy_digest: str
    project_id: str
    protected_validation_passed: bool
    protected_validation_digest: str
    evaluation_record: EvaluationRecord
    completion: CompletionObservation
    metrics: tuple[RoutingMetricEvidence, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "context_digest", _sha(self.context_digest, "context_digest"))
        object.__setattr__(self, "strategy_digest", _sha(self.strategy_digest, "strategy_digest"))
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        if not isinstance(self.protected_validation_passed, bool):
            raise OutcomeRoutingError("protected_validation_passed must be bool")
        object.__setattr__(self, "protected_validation_digest", _sha(self.protected_validation_digest, "protected_validation_digest"))
        if not isinstance(self.evaluation_record, EvaluationRecord):
            raise OutcomeRoutingError("evaluation_record must be accepted S3 EvaluationRecord")
        if not isinstance(self.completion, CompletionObservation):
            raise OutcomeRoutingError("completion must be CompletionObservation")
        metrics = tuple(self.metrics)
        if len(metrics) > 32 or any(not isinstance(v, RoutingMetricEvidence) for v in metrics):
            raise OutcomeRoutingError("metrics must be bounded")
        object.__setattr__(self, "metrics", tuple(sorted(metrics, key=lambda v: (v.metric.value, v.digest))))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "context_digest": self.context_digest,
            "strategy_digest": self.strategy_digest,
            "project_id": self.project_id,
            "protected_validation_passed": self.protected_validation_passed,
            "protected_validation_digest": self.protected_validation_digest,
            "evaluation_record_digest": self.evaluation_record.digest,
            "evaluation_outcome": self.evaluation_record.outcome.value,
            "completion": self.completion.as_dict(),
            "metrics": [m.as_dict() for m in self.metrics],
        }


@dataclass(frozen=True, slots=True)
class EconomicMetricPolicy:
    metric: RoutingMetricName
    weight: float
    ceiling: float
    required: bool = False
    allow_estimated: bool = False
    missing_penalty: float = 1.0
    allowed_provenance: tuple[RoutingProvenance, ...] = (
        RoutingProvenance.PROVIDER,
        RoutingProvenance.PARALLAX,
    )

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "metric", self.metric if isinstance(self.metric, RoutingMetricName) else RoutingMetricName(self.metric))
        except (TypeError, ValueError) as exc:
            raise OutcomeRoutingError("invalid policy metric") from exc
        object.__setattr__(self, "weight", _unit(self.weight, "weight"))
        object.__setattr__(self, "ceiling", _positive(self.ceiling, "ceiling"))
        object.__setattr__(self, "missing_penalty", _unit(self.missing_penalty, "missing_penalty"))
        if not isinstance(self.required, bool) or not isinstance(self.allow_estimated, bool):
            raise OutcomeRoutingError("metric policy flags must be bool")
        values = tuple(sorted({v if isinstance(v, RoutingProvenance) else RoutingProvenance(v) for v in self.allowed_provenance}, key=lambda v: v.value))
        if RoutingProvenance.ESTIMATE in values:
            raise OutcomeRoutingError("estimate cannot be admitted as observed provenance")
        object.__setattr__(self, "allowed_provenance", values)

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric.value,
            "weight": self.weight,
            "ceiling": self.ceiling,
            "required": self.required,
            "allow_estimated": self.allow_estimated,
            "missing_penalty": self.missing_penalty,
            "allowed_provenance": [v.value for v in self.allowed_provenance],
        }


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    policy_id: str
    policy_version: str
    permitted_strategy_kinds: tuple[StrategyKind, ...]
    metric_policies: tuple[EconomicMetricPolicy, ...]
    quality_floor: float = 0.0
    confidence_floor: float = 0.0
    quality_weight: float = 1.0
    max_sequence_age: int = 100
    minimum_comparable_metrics: int = 1
    fallback_strategy_id: str | None = None
    human_required_on_insufficient: bool = True
    max_explorations: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _token(self.policy_id, "policy_id"))
        object.__setattr__(self, "policy_version", _version(self.policy_version, "policy_version"))
        kinds = tuple(sorted({v if isinstance(v, StrategyKind) else StrategyKind(v) for v in self.permitted_strategy_kinds}, key=lambda v: v.value))
        if not kinds:
            raise OutcomeRoutingError("policy requires permitted strategy kinds")
        object.__setattr__(self, "permitted_strategy_kinds", kinds)
        rules = tuple(self.metric_policies)
        if not rules or any(not isinstance(r, EconomicMetricPolicy) for r in rules) or len({r.metric for r in rules}) != len(rules):
            raise OutcomeRoutingError("metric policies must be bounded and unique")
        object.__setattr__(self, "metric_policies", tuple(sorted(rules, key=lambda r: r.metric.value)))
        object.__setattr__(self, "quality_floor", _unit(self.quality_floor, "quality_floor"))
        object.__setattr__(self, "confidence_floor", _unit(self.confidence_floor, "confidence_floor"))
        object.__setattr__(self, "quality_weight", _unit(self.quality_weight, "quality_weight"))
        object.__setattr__(self, "max_sequence_age", _integer(self.max_sequence_age, 0, 1_000_000, "max_sequence_age"))
        object.__setattr__(self, "minimum_comparable_metrics", _integer(self.minimum_comparable_metrics, 0, len(rules), "minimum_comparable_metrics"))
        object.__setattr__(self, "max_explorations", _integer(self.max_explorations, 0, 32, "max_explorations"))
        if self.fallback_strategy_id is not None:
            object.__setattr__(self, "fallback_strategy_id", _token(self.fallback_strategy_id, "fallback_strategy_id"))
        if not isinstance(self.human_required_on_insufficient, bool):
            raise OutcomeRoutingError("human_required_on_insufficient must be bool")

    @property
    def digest(self) -> str:
        return _digest(self.as_dict(include_digest=False))

    def as_dict(self, *, include_digest: bool = True) -> dict[str, object]:
        data = {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "permitted_strategy_kinds": [v.value for v in self.permitted_strategy_kinds],
            "metric_policies": [v.as_dict() for v in self.metric_policies],
            "quality_floor": self.quality_floor,
            "confidence_floor": self.confidence_floor,
            "quality_weight": self.quality_weight,
            "max_sequence_age": self.max_sequence_age,
            "minimum_comparable_metrics": self.minimum_comparable_metrics,
            "fallback_strategy_id": self.fallback_strategy_id,
            "human_required_on_insufficient": self.human_required_on_insufficient,
            "max_explorations": self.max_explorations,
            "tie_breaker": "strategy_id_ascending",
            "server_owned": True,
            "can_change_acceptance": False,
            "can_weaken_validation": False,
        }
        if include_digest:
            data["policy_digest"] = self.digest
        return data


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    metric: RoutingMetricName
    state: EvidenceState
    provenance: RoutingProvenance | None
    raw_value: float | None
    normalized_value: float | None
    weight: float
    contribution: float
    source_digest: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric.value,
            "state": self.state.value,
            "provenance": self.provenance.value if self.provenance else None,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "weight": self.weight,
            "contribution": self.contribution,
            "source_digest": self.source_digest,
        }


@dataclass(frozen=True, slots=True)
class StrategyEligibility:
    strategy_id: str
    strategy_digest: str
    eligible: bool
    reasons: tuple[EligibilityReason, ...]
    quality_score: float | None
    quality_confidence: float | None
    comparable_metrics: int
    components: tuple[ScoreComponent, ...]
    total_score: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_digest": self.strategy_digest,
            "eligible": self.eligible,
            "reasons": [v.value for v in self.reasons],
            "quality_score": self.quality_score,
            "quality_confidence": self.quality_confidence,
            "comparable_metrics": self.comparable_metrics,
            "components": [v.as_dict() for v in self.components],
            "total_score": self.total_score,
        }


@dataclass(frozen=True, slots=True)
class RoutingRequest:
    context: RoutingContext
    policy: RoutingPolicy
    strategies: tuple[DevelopmentStrategy, ...]
    admissions: tuple[StrategyAdmissionSnapshot, ...]
    outcomes: tuple[StrategyOutcomeEvidence, ...]
    explorations_used: int = 0
    exploration_strategy_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.context, RoutingContext) or not isinstance(self.policy, RoutingPolicy):
            raise OutcomeRoutingError("canonical context and policy required")
        strategies = tuple(sorted(self.strategies, key=lambda v: v.strategy_id))
        if not strategies or len(strategies) > 32 or len({v.strategy_id for v in strategies}) != len(strategies):
            raise OutcomeRoutingError("strategies must be bounded and unique")
        if any(not isinstance(v, DevelopmentStrategy) for v in strategies):
            raise OutcomeRoutingError("invalid strategy")
        object.__setattr__(self, "strategies", strategies)
        if any(not isinstance(v, StrategyAdmissionSnapshot) for v in self.admissions) or any(not isinstance(v, StrategyOutcomeEvidence) for v in self.outcomes):
            raise OutcomeRoutingError("invalid routing evidence")
        object.__setattr__(self, "admissions", tuple(self.admissions))
        object.__setattr__(self, "outcomes", tuple(self.outcomes))
        object.__setattr__(self, "explorations_used", _integer(self.explorations_used, 0, 32, "explorations_used"))
        if self.exploration_strategy_id is not None:
            object.__setattr__(self, "exploration_strategy_id", _token(self.exploration_strategy_id, "exploration_strategy_id"))

    @property
    def fingerprint(self) -> str:
        return _digest({
            "context": self.context.as_dict(),
            "policy": self.policy.as_dict(),
            "strategies": [v.as_dict() for v in self.strategies],
            "admissions": sorted(v.digest for v in self.admissions),
            "outcomes": sorted(v.digest for v in self.outcomes),
            "explorations_used": self.explorations_used,
            "exploration_strategy_id": self.exploration_strategy_id,
        })


@dataclass(frozen=True, slots=True)
class RoutingDecisionRecord:
    context: RoutingContext
    policy_id: str
    policy_version: str
    policy_digest: str
    fingerprint: str
    disposition: RoutingDisposition
    reason_code: str
    selected_strategy_id: str | None
    exploration: bool
    eligibility: tuple[StrategyEligibility, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _token(self.policy_id, "policy_id"))
        object.__setattr__(self, "policy_version", _version(self.policy_version, "policy_version"))
        object.__setattr__(self, "policy_digest", _sha(self.policy_digest, "policy_digest"))
        object.__setattr__(self, "fingerprint", _sha(self.fingerprint, "fingerprint"))
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        try:
            object.__setattr__(self, "disposition", self.disposition if isinstance(self.disposition, RoutingDisposition) else RoutingDisposition(self.disposition))
        except (TypeError, ValueError) as exc:
            raise OutcomeRoutingError("invalid disposition") from exc
        if self.selected_strategy_id is not None:
            object.__setattr__(self, "selected_strategy_id", _token(self.selected_strategy_id, "selected_strategy_id"))
        if not isinstance(self.exploration, bool):
            raise OutcomeRoutingError("exploration must be bool")
        ids = {v.strategy_id: v for v in self.eligibility}
        selected = self.disposition in {RoutingDisposition.SELECTED, RoutingDisposition.FALLBACK_SELECTED}
        if selected != (self.selected_strategy_id is not None):
            raise OutcomeRoutingError("selection disposition and selected strategy mismatch")
        if selected and (self.selected_strategy_id not in ids or not ids[self.selected_strategy_id].eligible):
            raise OutcomeRoutingError("decision can select only an eligible admitted strategy")

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "routing_protocol_version": ROUTING_PROTOCOL_VERSION,
            "context": self.context.as_dict(),
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_digest": self.policy_digest,
            "fingerprint": self.fingerprint,
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "selected_strategy_id": self.selected_strategy_id,
            "exploration": self.exploration,
            "eligibility": [v.as_dict() for v in self.eligibility],
            "grants_capabilities": False,
            "invokes_provider": False,
            "routes_spending": False,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
            "performs_merge": False,
            "performs_deployment": False,
            "completes_review": False,
            "chooses_candidate_winner": False,
            "contains_credentials": False,
            "contains_provider_payload": False,
            "contains_hidden_reasoning": False,
        }


@dataclass(frozen=True, slots=True)
class RoutingAdmissionDecision:
    admitted: bool
    reason: RoutingAdmissionReason
    record_digest: str
    duplicate: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.admitted, bool) or not isinstance(self.duplicate, bool):
            raise OutcomeRoutingError("admission flags must be bool")
        try:
            object.__setattr__(self, "reason", self.reason if isinstance(self.reason, RoutingAdmissionReason) else RoutingAdmissionReason(self.reason))
        except (TypeError, ValueError) as exc:
            raise OutcomeRoutingError("invalid admission reason") from exc
        object.__setattr__(self, "record_digest", _sha(self.record_digest, "record_digest"))
        if self.duplicate and (self.admitted or self.reason is not RoutingAdmissionReason.DUPLICATE):
            raise OutcomeRoutingError("duplicate cannot be authoritative")


def route_outcomes(request: RoutingRequest) -> RoutingDecisionRecord:
    context, policy = request.context, request.policy
    if (context.routing_policy_id, context.routing_policy_version, context.routing_policy_digest) != (policy.policy_id, policy.policy_version, policy.digest):
        results = tuple(_result(strategy, [EligibilityReason.CONTEXT_MISMATCH]) for strategy in request.strategies)
        return _record(request, RoutingDisposition.POLICY_REJECTED, "ROUTING_POLICY_MISMATCH", None, False, results)
    admissions = {value.strategy_digest: value for value in request.admissions}
    outcomes = {value.strategy_digest: value for value in request.outcomes}
    results = tuple(_evaluate(context, policy, strategy, admissions.get(strategy.digest), outcomes.get(strategy.digest)) for strategy in request.strategies)
    human = any(EligibilityReason.HUMAN_REQUIRED in result.reasons for result in results)
    eligible = [result for result in results if result.eligible]
    if not eligible:
        return _record(
            request,
            RoutingDisposition.HUMAN_REQUIRED if human else RoutingDisposition.NO_ADMISSIBLE_STRATEGY,
            "HUMAN_BOUNDARY" if human else "NO_ADMISSIBLE_STRATEGY",
            None,
            False,
            results,
        )
    hint = request.exploration_strategy_id
    if hint and request.explorations_used < policy.max_explorations:
        chosen = next((result for result in eligible if result.strategy_id == hint and result.total_score is None), None)
        if chosen:
            return _record(request, RoutingDisposition.SELECTED, "BOUNDED_EXPLORATION", chosen.strategy_id, True, results)
    comparable = [result for result in eligible if result.total_score is not None]
    if comparable:
        chosen = sorted(comparable, key=lambda result: (-float(result.total_score), result.strategy_id))[0]
        return _record(request, RoutingDisposition.SELECTED, "ECONOMIC_POLICY_SELECTED", chosen.strategy_id, False, results)
    if policy.fallback_strategy_id:
        chosen = next((result for result in eligible if result.strategy_id == policy.fallback_strategy_id), None)
        if chosen:
            return _record(request, RoutingDisposition.FALLBACK_SELECTED, "CONSERVATIVE_FALLBACK", chosen.strategy_id, False, results)
    return _record(
        request,
        RoutingDisposition.HUMAN_REQUIRED if policy.human_required_on_insufficient else RoutingDisposition.INSUFFICIENT_EVIDENCE,
        "INSUFFICIENT_ECONOMIC_EVIDENCE",
        None,
        False,
        results,
    )


def admit_routing_record(
    record: RoutingDecisionRecord,
    *,
    expected_context: RoutingContext,
    expected_policy: RoutingPolicy,
    expected_fingerprint: str,
    existing: RoutingDecisionRecord | None = None,
) -> RoutingAdmissionDecision:
    if record.context.digest != expected_context.digest:
        return RoutingAdmissionDecision(False, RoutingAdmissionReason.CONTEXT_MISMATCH, record.digest)
    if record.policy_digest != expected_policy.digest:
        return RoutingAdmissionDecision(False, RoutingAdmissionReason.POLICY_MISMATCH, record.digest)
    if record.fingerprint != expected_fingerprint:
        return RoutingAdmissionDecision(False, RoutingAdmissionReason.FINGERPRINT_MISMATCH, record.digest)
    if existing is None:
        return RoutingAdmissionDecision(True, RoutingAdmissionReason.ACCEPTED, record.digest)
    if existing.fingerprint != record.fingerprint or existing.context.digest != record.context.digest:
        return RoutingAdmissionDecision(False, RoutingAdmissionReason.COMPETING_RECORD, record.digest)
    if existing.digest == record.digest:
        return RoutingAdmissionDecision(False, RoutingAdmissionReason.DUPLICATE, record.digest, True)
    return RoutingAdmissionDecision(False, RoutingAdmissionReason.COMPETING_RECORD, record.digest)


def safe_routing_json(record: RoutingDecisionRecord) -> str:
    return json.dumps(record.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _evaluate(
    context: RoutingContext,
    policy: RoutingPolicy,
    strategy: DevelopmentStrategy,
    admission: StrategyAdmissionSnapshot | None,
    outcome: StrategyOutcomeEvidence | None,
) -> StrategyEligibility:
    reasons: list[EligibilityReason] = []
    if strategy.kind not in policy.permitted_strategy_kinds:
        reasons.append(EligibilityReason.STRATEGY_NOT_PERMITTED)
    if admission is None or admission.context_digest != context.digest or admission.strategy_digest != strategy.digest or admission.project_id != context.project_id:
        reasons.append(EligibilityReason.CONTEXT_MISMATCH)
    else:
        if not admission.capability_compatible or not set(strategy.required_capabilities) <= set(admission.admitted_capabilities):
            reasons.append(EligibilityReason.CAPABILITY_MISMATCH)
        if not admission.authority_compatible:
            reasons.append(EligibilityReason.AUTHORITY_MISMATCH)
        if not admission.dependency_compatible:
            reasons.append(EligibilityReason.DEPENDENCY_MISMATCH)
    if outcome is None:
        reasons.append(EligibilityReason.MISSING_OUTCOME_EVIDENCE)
        return _result(strategy, reasons)
    if outcome.context_digest != context.digest or outcome.strategy_digest != strategy.digest or outcome.project_id != context.project_id:
        reasons.append(EligibilityReason.CONTEXT_MISMATCH)
    if not outcome.protected_validation_passed:
        reasons.append(EligibilityReason.PROTECTED_VALIDATION_REQUIRED)
    if outcome.completion.project_id != context.project_id or outcome.completion.state is not CompletionState.COMPLETED:
        reasons.append(EligibilityReason.HUMAN_REQUIRED if outcome.completion.state is CompletionState.HUMAN_REQUIRED else EligibilityReason.COMPLETION_REQUIRED)
    evaluation = outcome.evaluation_record
    candidate = evaluation.candidate
    if evaluation.policy_digest != context.evaluation_policy_digest:
        reasons.append(EligibilityReason.EVALUATION_POLICY_MISMATCH)
    if (
        candidate.project_id,
        candidate.run_id,
        candidate.work_specification_id,
        candidate.work_specification_revision,
        candidate.work_specification_digest,
        candidate.acceptance_ids,
    ) != (
        context.project_id,
        context.run_id,
        context.work_specification_id,
        context.work_specification_revision,
        context.work_specification_digest,
        context.acceptance_ids,
    ):
        reasons.append(EligibilityReason.EVALUATION_IDENTITY_MISMATCH)
    if candidate.producer_identity_digest not in strategy.agent_identity_digests:
        reasons.append(EligibilityReason.EVALUATION_IDENTITY_MISMATCH)
    if evaluation.outcome is EvaluationOutcome.HUMAN_REQUIRED:
        reasons.append(EligibilityReason.HUMAN_REQUIRED)
    elif evaluation.outcome is not EvaluationOutcome.SUPPORTED:
        reasons.append(EligibilityReason.EVALUATION_REJECTED)
    support_dimensions = [dimension for dimension in evaluation.dimensions if dimension.verdict is DimensionVerdict.SUPPORT]
    quality_score = min((dimension.score for dimension in support_dimensions if dimension.score is not None), default=None)
    quality_confidence = min((dimension.confidence for dimension in support_dimensions), default=None)
    if policy.quality_floor and (quality_score is None or quality_score < policy.quality_floor):
        reasons.append(EligibilityReason.QUALITY_FLOOR_FAILED if quality_score is not None else EligibilityReason.QUALITY_EVIDENCE_INSUFFICIENT)
    if policy.confidence_floor and (quality_confidence is None or quality_confidence < policy.confidence_floor):
        reasons.append(EligibilityReason.QUALITY_EVIDENCE_INSUFFICIENT)
    grouped: dict[RoutingMetricName, list[RoutingMetricEvidence]] = {}
    for metric in outcome.metrics:
        grouped.setdefault(metric.metric, []).append(metric)
        if not metric.sanitized_generalized and metric.project_id != context.project_id:
            reasons.append(EligibilityReason.CROSS_PROJECT_EVIDENCE)
    components: list[ScoreComponent] = []
    comparable = 0
    for rule in policy.metric_policies:
        values = grouped.get(rule.metric, [])
        unique = {value.digest: value for value in values}
        if len(unique) > 1:
            reasons.append(EligibilityReason.CONTRADICTORY_EVIDENCE)
            components.append(_missing(rule, EvidenceState.INVALID))
            continue
        metric = next(iter(unique.values()), None)
        if metric is None:
            if rule.required:
                reasons.append(EligibilityReason.MISSING_MANDATORY_EVIDENCE)
            components.append(_missing(rule, EvidenceState.UNKNOWN))
            continue
        if metric.state is EvidenceState.INVALID:
            if rule.required:
                reasons.append(EligibilityReason.INVALID_MANDATORY_EVIDENCE)
            reasons.append(EligibilityReason.UNTRUSTED_OBSERVED_EVIDENCE)
            components.append(_missing(rule, EvidenceState.INVALID, metric.source_digest))
            continue
        age = context.decision_sequence - metric.sequence
        if metric.state is EvidenceState.STALE or age < 0 or age > policy.max_sequence_age:
            if rule.required:
                reasons.append(EligibilityReason.STALE_MANDATORY_EVIDENCE)
            components.append(_missing(rule, EvidenceState.STALE, metric.source_digest))
            continue
        if metric.state in {EvidenceState.UNKNOWN, EvidenceState.UNAVAILABLE}:
            if rule.required:
                reasons.append(EligibilityReason.MISSING_MANDATORY_EVIDENCE)
            components.append(_missing(rule, metric.state, metric.source_digest))
            continue
        provenance_factor = 1.0
        if metric.state is EvidenceState.ESTIMATED:
            if not rule.allow_estimated:
                if rule.required:
                    reasons.append(EligibilityReason.MISSING_MANDATORY_EVIDENCE)
                components.append(_missing(rule, metric.state, metric.source_digest))
                continue
            provenance_factor = 0.8
        elif metric.provenance not in rule.allowed_provenance:
            if rule.required:
                reasons.append(EligibilityReason.INVALID_MANDATORY_EVIDENCE)
            components.append(_missing(rule, EvidenceState.INVALID, metric.source_digest))
            continue
        normalized = 1.0 - min(float(metric.value) / rule.ceiling, 1.0)
        contribution = normalized * rule.weight * provenance_factor
        components.append(ScoreComponent(rule.metric, metric.state, metric.provenance, float(metric.value), normalized, rule.weight, contribution, metric.source_digest))
        comparable += 1
    reasons = list(dict.fromkeys(reasons))
    eligible = not reasons
    total_score = None
    if eligible and comparable >= policy.minimum_comparable_metrics:
        total_score = (quality_score or 0.0) * policy.quality_weight + sum(value.contribution for value in components)
    return _result(strategy, reasons or [EligibilityReason.ELIGIBLE], quality_score, quality_confidence, comparable, tuple(components), total_score)


def _missing(rule: EconomicMetricPolicy, state: EvidenceState, digest: str | None = None) -> ScoreComponent:
    return ScoreComponent(rule.metric, state, None, None, None, rule.weight, -(rule.weight * rule.missing_penalty), digest)


def _result(
    strategy: DevelopmentStrategy,
    reasons: list[EligibilityReason],
    quality_score: float | None = None,
    quality_confidence: float | None = None,
    comparable: int = 0,
    components: tuple[ScoreComponent, ...] = (),
    total_score: float | None = None,
) -> StrategyEligibility:
    eligible = reasons == [EligibilityReason.ELIGIBLE] or not reasons
    return StrategyEligibility(strategy.strategy_id, strategy.digest, eligible, tuple(reasons or [EligibilityReason.ELIGIBLE]), quality_score, quality_confidence, comparable, components, total_score)


def _record(
    request: RoutingRequest,
    disposition: RoutingDisposition,
    reason: str,
    selected: str | None,
    exploration: bool,
    results: tuple[StrategyEligibility, ...],
) -> RoutingDecisionRecord:
    return RoutingDecisionRecord(request.context, request.policy.policy_id, request.policy.policy_version, request.policy.digest, request.fingerprint, disposition, reason, selected, exploration, results)


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _sha(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise OutcomeRoutingError(f"{field} must be sha256")
    return value


def _uuid(value: str, field: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise OutcomeRoutingError(f"{field} must be UUID") from exc


def _token(value: str, field: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise OutcomeRoutingError(f"{field} must be bounded token")
    return value


def _version(value: str, field: str) -> str:
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        raise OutcomeRoutingError(f"{field} must be bounded version")
    return value


def _reference(value: str, field: str) -> str:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise OutcomeRoutingError(f"{field} must be bounded reference")
    return value


def _reason(value: str) -> str:
    if not isinstance(value, str) or not _REASON.fullmatch(value):
        raise OutcomeRoutingError("reason_code must be normalized")
    return value


def _acceptance_ids(values: Iterable[str]) -> tuple[str, ...]:
    result = tuple(values)
    if not result or len(result) > 128 or len(set(result)) != len(result) or any(not isinstance(value, str) or not _AC.fullmatch(value) for value in result):
        raise OutcomeRoutingError("acceptance_ids must be bounded unique stable ids")
    return result


def _tokens(values: Iterable[str], field: str) -> tuple[str, ...]:
    return tuple(sorted({_token(value, field) for value in values}))


def _integer(value: int, low: int, high: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise OutcomeRoutingError(f"{field} outside protected bounds")
    return value


def _number(value: float | int | None, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OutcomeRoutingError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= _MAX_VALUE:
        raise OutcomeRoutingError(f"{field} outside protected bounds")
    return result


def _positive(value: float | int, field: str) -> float:
    result = _number(value, field)
    if result <= 0:
        raise OutcomeRoutingError(f"{field} must be positive")
    return result


def _unit(value: float | int, field: str) -> float:
    result = _number(value, field)
    if result > 1:
        raise OutcomeRoutingError(f"{field} must be between 0 and 1")
    return result
