from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import math
import re
from typing import Iterable
from uuid import UUID


PARALLAX_BENCH_VERSION = 1
_MAX_ACCEPTANCE_IDS = 128
_MAX_REASON = 96
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_AC_RE = re.compile(r"^AC-[0-9]{2,3}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,95}$")


class ParallaxBenchError(ValueError):
    """Fail-closed error for malformed, unsafe, or cross-context benchmark evidence."""


class BenchmarkEvidenceState(StrEnum):
    OBSERVED = "OBSERVED"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    INVALID = "INVALID"


class BenchmarkProvenance(StrEnum):
    PROTECTED = "PROTECTED"
    PARALLAX_OBSERVED = "PARALLAX_OBSERVED"
    PROVIDER_OBSERVED = "PROVIDER_OBSERVED"
    EVALUATOR = "EVALUATOR"
    FIXTURE_BOUND = "FIXTURE_BOUND"
    ESTIMATED = "ESTIMATED"


class BenchmarkDimension(StrEnum):
    OBJECTIVE_COMPLETION = "objective_completion"
    PROTECTED_CORRECTNESS = "protected_correctness"
    VISUAL_UX_QUALITY = "visual_ux_quality"
    HUMAN_INTERVENTIONS = "human_interventions"
    ELAPSED_TIME = "elapsed_time"
    COST_USAGE = "cost_usage"
    RETRY_RECOVERY = "retry_recovery"
    COMPLETION_RELIABILITY = "completion_reliability"


class ComparisonOutcome(StrEnum):
    IMPROVED = "IMPROVED"
    EQUIVALENT = "EQUIVALENT"
    REGRESSED = "REGRESSED"
    UNKNOWN = "UNKNOWN"
    INCOMPARABLE = "INCOMPARABLE"


class ParallaxBenchDisposition(StrEnum):
    SUPPORTED = "SUPPORTED"
    REGRESSED = "REGRESSED"
    DETERMINISTIC_BLOCKED = "DETERMINISTIC_BLOCKED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INCOMPARABLE = "INCOMPARABLE"
    POLICY_REJECTED = "POLICY_REJECTED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class ProtectedCeiling(StrEnum):
    REVIEW = "REVIEW"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    DETERMINISTIC_BLOCKED = "DETERMINISTIC_BLOCKED"


_RATIO_DIMENSIONS = {
    BenchmarkDimension.OBJECTIVE_COMPLETION,
    BenchmarkDimension.PROTECTED_CORRECTNESS,
    BenchmarkDimension.VISUAL_UX_QUALITY,
    BenchmarkDimension.COMPLETION_RELIABILITY,
}
_LOWER_IS_BETTER = {
    BenchmarkDimension.HUMAN_INTERVENTIONS,
    BenchmarkDimension.ELAPSED_TIME,
    BenchmarkDimension.COST_USAGE,
    BenchmarkDimension.RETRY_RECOVERY,
}
_DIMENSION_UNITS = {
    BenchmarkDimension.OBJECTIVE_COMPLETION: "ratio",
    BenchmarkDimension.PROTECTED_CORRECTNESS: "ratio",
    BenchmarkDimension.VISUAL_UX_QUALITY: "ratio",
    BenchmarkDimension.HUMAN_INTERVENTIONS: "count",
    BenchmarkDimension.ELAPSED_TIME: "ms",
    BenchmarkDimension.COST_USAGE: "usd",
    BenchmarkDimension.RETRY_RECOVERY: "count",
    BenchmarkDimension.COMPLETION_RELIABILITY: "ratio",
}


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    case_version: str
    objective_class: str
    project_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    repository_shape: str
    comparable_dimensions: tuple[BenchmarkDimension, ...]
    expected_ceiling: ProtectedCeiling
    fixture_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _token(self.case_id, "case_id"))
        object.__setattr__(self, "case_version", _version(self.case_version, "case_version"))
        object.__setattr__(self, "objective_class", _token(self.objective_class, "objective_class"))
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id, "work_specification_id"))
        if (
            not isinstance(self.work_specification_revision, int)
            or isinstance(self.work_specification_revision, bool)
            or self.work_specification_revision < 1
        ):
            raise ParallaxBenchError("work_specification_revision must be >= 1")
        object.__setattr__(
            self,
            "work_specification_digest",
            _sha(self.work_specification_digest, "work_specification_digest"),
        )
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        object.__setattr__(self, "repository_shape", _token(self.repository_shape, "repository_shape"))
        dimensions = tuple(
            item if isinstance(item, BenchmarkDimension) else BenchmarkDimension(item)
            for item in self.comparable_dimensions
        )
        if not dimensions or len(dimensions) != len(set(dimensions)):
            raise ParallaxBenchError("comparable_dimensions must be unique and non-empty")
        object.__setattr__(self, "comparable_dimensions", tuple(sorted(dimensions, key=lambda item: item.value)))
        try:
            ceiling = self.expected_ceiling if isinstance(self.expected_ceiling, ProtectedCeiling) else ProtectedCeiling(self.expected_ceiling)
        except (TypeError, ValueError) as exc:
            raise ParallaxBenchError("invalid expected_ceiling") from exc
        object.__setattr__(self, "expected_ceiling", ceiling)
        object.__setattr__(self, "fixture_digest", _sha(self.fixture_digest, "fixture_digest"))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "case_version": self.case_version,
            "objective_class": self.objective_class,
            "project_id": self.project_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "repository_shape": self.repository_shape,
            "comparable_dimensions": [item.value for item in self.comparable_dimensions],
            "expected_ceiling": self.expected_ceiling.value,
            "fixture_digest": self.fixture_digest,
        }


@dataclass(frozen=True, slots=True)
class CandidateBinding:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    candidate_id: str
    source_context_digest: str
    protected_validation_digest: str
    evaluator_policy_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id, "work_specification_id"))
        if (
            not isinstance(self.work_specification_revision, int)
            or isinstance(self.work_specification_revision, bool)
            or self.work_specification_revision < 1
        ):
            raise ParallaxBenchError("work_specification_revision must be >= 1")
        object.__setattr__(
            self,
            "work_specification_digest",
            _sha(self.work_specification_digest, "work_specification_digest"),
        )
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        object.__setattr__(self, "candidate_id", _token(self.candidate_id, "candidate_id"))
        for field in ("source_context_digest", "protected_validation_digest", "evaluator_policy_digest"):
            object.__setattr__(self, field, _sha(getattr(self, field), field))

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
            "candidate_id": self.candidate_id,
            "source_context_digest": self.source_context_digest,
            "protected_validation_digest": self.protected_validation_digest,
            "evaluator_policy_digest": self.evaluator_policy_digest,
        }


@dataclass(frozen=True, slots=True)
class ProtectedFloor:
    acceptance_complete: bool
    deterministic_validation_passed: bool
    safety_preserved: bool
    privacy_preserved: bool
    governance_preserved: bool
    review_ceiling_preserved: bool
    human_required: bool
    evidence_digest: str

    def __post_init__(self) -> None:
        for field in (
            "acceptance_complete",
            "deterministic_validation_passed",
            "safety_preserved",
            "privacy_preserved",
            "governance_preserved",
            "review_ceiling_preserved",
            "human_required",
        ):
            if not isinstance(getattr(self, field), bool):
                raise ParallaxBenchError(f"{field} must be bool")
        object.__setattr__(self, "evidence_digest", _sha(self.evidence_digest, "evidence_digest"))

    @property
    def hard_guardrails_passed(self) -> bool:
        return (
            self.acceptance_complete
            and self.deterministic_validation_passed
            and self.safety_preserved
            and self.privacy_preserved
            and self.governance_preserved
            and self.review_ceiling_preserved
        )

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "acceptance_complete": self.acceptance_complete,
            "deterministic_validation_passed": self.deterministic_validation_passed,
            "safety_preserved": self.safety_preserved,
            "privacy_preserved": self.privacy_preserved,
            "governance_preserved": self.governance_preserved,
            "review_ceiling_preserved": self.review_ceiling_preserved,
            "human_required": self.human_required,
            "hard_guardrails_passed": self.hard_guardrails_passed,
            "evidence_digest": self.evidence_digest,
        }


@dataclass(frozen=True, slots=True)
class DimensionEvidence:
    dimension: BenchmarkDimension
    state: BenchmarkEvidenceState
    provenance: BenchmarkProvenance
    value: float | None
    evidence_ref: str
    evidence_digest: str

    def __post_init__(self) -> None:
        try:
            dimension = self.dimension if isinstance(self.dimension, BenchmarkDimension) else BenchmarkDimension(self.dimension)
            state = self.state if isinstance(self.state, BenchmarkEvidenceState) else BenchmarkEvidenceState(self.state)
            provenance = self.provenance if isinstance(self.provenance, BenchmarkProvenance) else BenchmarkProvenance(self.provenance)
        except (TypeError, ValueError) as exc:
            raise ParallaxBenchError("invalid dimension evidence enum") from exc
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "evidence_ref", _reference(self.evidence_ref, "evidence_ref"))
        object.__setattr__(self, "evidence_digest", _sha(self.evidence_digest, "evidence_digest"))

        numeric = state in {BenchmarkEvidenceState.OBSERVED, BenchmarkEvidenceState.ESTIMATED}
        if numeric:
            if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
                raise ParallaxBenchError("observed/estimated dimension requires numeric value")
            value = float(self.value)
            if not math.isfinite(value) or value < 0:
                raise ParallaxBenchError("dimension value must be finite and non-negative")
            if dimension in _RATIO_DIMENSIONS and value > 1:
                raise ParallaxBenchError("ratio dimension must be between 0 and 1")
            object.__setattr__(self, "value", value)
        elif self.value is not None:
            raise ParallaxBenchError("non-numeric evidence state cannot carry value")

        if state is BenchmarkEvidenceState.ESTIMATED and provenance is not BenchmarkProvenance.ESTIMATED:
            raise ParallaxBenchError("estimated evidence requires ESTIMATED provenance")
        if state is BenchmarkEvidenceState.OBSERVED and provenance is BenchmarkProvenance.ESTIMATED:
            raise ParallaxBenchError("observed evidence cannot use ESTIMATED provenance")
        if dimension is BenchmarkDimension.PROTECTED_CORRECTNESS and state is not BenchmarkEvidenceState.OBSERVED:
            raise ParallaxBenchError("protected correctness must be observed")

    @property
    def unit(self) -> str:
        return _DIMENSION_UNITS[self.dimension]

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension.value,
            "state": self.state.value,
            "provenance": self.provenance.value,
            "value": self.value,
            "unit": self.unit,
            "evidence_ref": self.evidence_ref,
            "evidence_digest": self.evidence_digest,
        }


@dataclass(frozen=True, slots=True)
class CandidateBenchmarkEvidence:
    binding: CandidateBinding
    protected_floor: ProtectedFloor
    dimensions: tuple[DimensionEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.binding, CandidateBinding) or not isinstance(self.protected_floor, ProtectedFloor):
            raise ParallaxBenchError("candidate evidence requires canonical binding and protected floor")
        dimensions = tuple(self.dimensions)
        if any(not isinstance(item, DimensionEvidence) for item in dimensions):
            raise ParallaxBenchError("candidate dimensions must be canonical DimensionEvidence")
        actual = {item.dimension for item in dimensions}
        expected = set(BenchmarkDimension)
        if actual != expected or len(dimensions) != len(expected):
            raise ParallaxBenchError("candidate must report every benchmark dimension exactly once")
        ordered = tuple(sorted(dimensions, key=lambda item: item.dimension.value))
        object.__setattr__(self, "dimensions", ordered)

        protected = self.dimension(BenchmarkDimension.PROTECTED_CORRECTNESS)
        expected_protected = 1.0 if self.protected_floor.hard_guardrails_passed else 0.0
        if protected.value != expected_protected or protected.provenance is not BenchmarkProvenance.PROTECTED:
            raise ParallaxBenchError("protected correctness dimension must match exact protected floor")

        visual = self.dimension(BenchmarkDimension.VISUAL_UX_QUALITY)
        if not self.protected_floor.deterministic_validation_passed and visual.state in {
            BenchmarkEvidenceState.OBSERVED,
            BenchmarkEvidenceState.ESTIMATED,
        }:
            raise ParallaxBenchError("visual/UX evidence is inadmissible after deterministic failure")

    def dimension(self, dimension: BenchmarkDimension) -> DimensionEvidence:
        target = dimension if isinstance(dimension, BenchmarkDimension) else BenchmarkDimension(dimension)
        for item in self.dimensions:
            if item.dimension is target:
                return item
        raise ParallaxBenchError("benchmark dimension is missing")

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "binding": self.binding.as_dict(),
            "protected_floor": self.protected_floor.as_dict(),
            "dimensions": [item.as_dict() for item in self.dimensions],
        }


@dataclass(frozen=True, slots=True)
class DimensionComparison:
    dimension: BenchmarkDimension
    outcome: ComparisonOutcome
    materially_improved: bool
    baseline_digest: str
    challenger_digest: str

    def __post_init__(self) -> None:
        try:
            dimension = self.dimension if isinstance(self.dimension, BenchmarkDimension) else BenchmarkDimension(self.dimension)
            outcome = self.outcome if isinstance(self.outcome, ComparisonOutcome) else ComparisonOutcome(self.outcome)
        except (TypeError, ValueError) as exc:
            raise ParallaxBenchError("invalid comparison enum") from exc
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "outcome", outcome)
        if not isinstance(self.materially_improved, bool):
            raise ParallaxBenchError("materially_improved must be bool")
        if self.materially_improved and outcome is not ComparisonOutcome.IMPROVED:
            raise ParallaxBenchError("material improvement requires IMPROVED outcome")
        object.__setattr__(self, "baseline_digest", _sha(self.baseline_digest, "baseline_digest"))
        object.__setattr__(self, "challenger_digest", _sha(self.challenger_digest, "challenger_digest"))

    def as_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension.value,
            "outcome": self.outcome.value,
            "materially_improved": self.materially_improved,
            "baseline_digest": self.baseline_digest,
            "challenger_digest": self.challenger_digest,
        }


@dataclass(frozen=True, slots=True)
class ParallaxBenchResult:
    benchmark_version: int
    case_digest: str
    baseline_digest: str
    challenger_digest: str
    comparisons: tuple[DimensionComparison, ...]
    disposition: ParallaxBenchDisposition
    material_improvement: bool
    reason_code: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.benchmark_version != PARALLAX_BENCH_VERSION:
            raise ParallaxBenchError("unsupported benchmark version")
        for field in ("case_digest", "baseline_digest", "challenger_digest", "fingerprint"):
            object.__setattr__(self, field, _sha(getattr(self, field), field))
        comparisons = tuple(self.comparisons)
        if {item.dimension for item in comparisons} != set(BenchmarkDimension) or len(comparisons) != len(BenchmarkDimension):
            raise ParallaxBenchError("result must compare every benchmark dimension exactly once")
        object.__setattr__(self, "comparisons", tuple(sorted(comparisons, key=lambda item: item.dimension.value)))
        try:
            disposition = self.disposition if isinstance(self.disposition, ParallaxBenchDisposition) else ParallaxBenchDisposition(self.disposition)
        except (TypeError, ValueError) as exc:
            raise ParallaxBenchError("invalid benchmark disposition") from exc
        object.__setattr__(self, "disposition", disposition)
        if not isinstance(self.material_improvement, bool):
            raise ParallaxBenchError("material_improvement must be bool")
        object.__setattr__(self, "reason_code", _reason(self.reason_code))

    @property
    def result_digest(self) -> str:
        return _digest(self.as_dict(include_result_digest=False))

    def as_dict(self, *, include_result_digest: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "parallax_bench_version": self.benchmark_version,
            "case_digest": self.case_digest,
            "baseline_digest": self.baseline_digest,
            "challenger_digest": self.challenger_digest,
            "comparisons": [item.as_dict() for item in self.comparisons],
            "disposition": self.disposition.value,
            "material_improvement": self.material_improvement,
            "reason_code": self.reason_code,
            "fingerprint": self.fingerprint,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
            "grants_tool_capability": False,
            "grants_provider_authority": False,
            "performs_merge": False,
            "performs_production_deployment": False,
            "approves_release": False,
            "completes_review": False,
            "contains_source_bytes": False,
            "contains_patch": False,
            "contains_credentials": False,
            "contains_provider_payload": False,
            "contains_prompts": False,
            "contains_hidden_reasoning": False,
            "contains_arbitrary_commands": False,
            "contains_arbitrary_urls": False,
        }
        if include_result_digest:
            data["result_digest"] = self.result_digest
        return data


def evaluate_parallax_bench(
    *,
    case: BenchmarkCase,
    baseline: CandidateBenchmarkEvidence,
    challenger: CandidateBenchmarkEvidence,
) -> ParallaxBenchResult:
    """Evaluate exact bounded evidence without mutating runtime or promotion state."""

    if not isinstance(case, BenchmarkCase):
        raise ParallaxBenchError("case must be BenchmarkCase")
    if not isinstance(baseline, CandidateBenchmarkEvidence) or not isinstance(challenger, CandidateBenchmarkEvidence):
        raise ParallaxBenchError("baseline/challenger must be canonical benchmark evidence")
    _bind_case(case, baseline.binding)
    _bind_case(case, challenger.binding)

    comparisons = tuple(
        _compare_dimension(baseline.dimension(dimension), challenger.dimension(dimension))
        for dimension in BenchmarkDimension
    )

    if challenger.protected_floor.human_required:
        disposition = ParallaxBenchDisposition.HUMAN_REQUIRED
        reason = "CHALLENGER_HUMAN_REQUIRED"
        material = False
    elif not challenger.protected_floor.hard_guardrails_passed:
        disposition = ParallaxBenchDisposition.DETERMINISTIC_BLOCKED
        reason = "CHALLENGER_PROTECTED_FLOOR_FAILED"
        material = False
    elif baseline.protected_floor.hard_guardrails_passed and _protected_regression(baseline.protected_floor, challenger.protected_floor):
        disposition = ParallaxBenchDisposition.REGRESSED
        reason = "PROTECTED_GUARDRAIL_REGRESSION"
        material = False
    elif any(
        item.outcome is ComparisonOutcome.REGRESSED and item.dimension is BenchmarkDimension.PROTECTED_CORRECTNESS
        for item in comparisons
    ):
        disposition = ParallaxBenchDisposition.REGRESSED
        reason = "PROTECTED_CORRECTNESS_REGRESSION"
        material = False
    else:
        declared = set(case.comparable_dimensions)
        declared_pairs = tuple(item for item in comparisons if item.dimension in declared)
        if not declared_pairs:
            disposition = ParallaxBenchDisposition.POLICY_REJECTED
            reason = "NO_DECLARED_COMPARABLE_DIMENSIONS"
            material = False
        elif all(item.outcome is ComparisonOutcome.UNKNOWN for item in declared_pairs):
            disposition = ParallaxBenchDisposition.INSUFFICIENT_EVIDENCE
            reason = "DECLARED_EVIDENCE_UNKNOWN"
            material = False
        elif all(item.outcome in {ComparisonOutcome.UNKNOWN, ComparisonOutcome.INCOMPARABLE} for item in declared_pairs):
            disposition = ParallaxBenchDisposition.INCOMPARABLE
            reason = "DECLARED_EVIDENCE_INCOMPARABLE"
            material = False
        elif any(item.outcome is ComparisonOutcome.REGRESSED for item in declared_pairs):
            disposition = ParallaxBenchDisposition.REGRESSED
            reason = "COMPARABLE_DIMENSION_REGRESSION"
            material = False
        else:
            material = any(item.materially_improved for item in declared_pairs)
            disposition = ParallaxBenchDisposition.SUPPORTED
            reason = "MATERIAL_IMPROVEMENT_WITH_GUARDRAIL_PARITY" if material else "GUARDRAIL_PARITY_NO_MATERIAL_CHANGE"

    fingerprint = _digest(
        {
            "parallax_bench_version": PARALLAX_BENCH_VERSION,
            "case_digest": case.digest,
            "baseline_digest": baseline.digest,
            "challenger_digest": challenger.digest,
            "comparisons": [item.as_dict() for item in comparisons],
            "disposition": disposition.value,
            "material_improvement": material,
            "reason_code": reason,
        }
    )
    return ParallaxBenchResult(
        benchmark_version=PARALLAX_BENCH_VERSION,
        case_digest=case.digest,
        baseline_digest=baseline.digest,
        challenger_digest=challenger.digest,
        comparisons=comparisons,
        disposition=disposition,
        material_improvement=material,
        reason_code=reason,
        fingerprint=fingerprint,
    )


@dataclass(frozen=True, slots=True)
class BenchmarkFixtureTemplate:
    case_id: str
    case_version: str
    objective_class: str
    repository_shape: str
    scenario: str
    adversarial: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _token(self.case_id, "case_id"))
        object.__setattr__(self, "case_version", _version(self.case_version, "case_version"))
        object.__setattr__(self, "objective_class", _token(self.objective_class, "objective_class"))
        object.__setattr__(self, "repository_shape", _token(self.repository_shape, "repository_shape"))
        if not isinstance(self.scenario, str) or not self.scenario.strip() or len(self.scenario.strip()) > 240:
            raise ParallaxBenchError("fixture scenario must be bounded non-empty text")
        object.__setattr__(self, "scenario", self.scenario.strip())
        if not isinstance(self.adversarial, bool):
            raise ParallaxBenchError("fixture adversarial flag must be bool")

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "case_version": self.case_version,
            "objective_class": self.objective_class,
            "repository_shape": self.repository_shape,
            "scenario": self.scenario,
            "adversarial": self.adversarial,
        }


def parallax_bench_v1_fixtures() -> tuple[BenchmarkFixtureTemplate, ...]:
    """Return permanent reviewable fixture templates; runtime logic never branches on their IDs."""

    fixtures = (
        BenchmarkFixtureTemplate("single-surface", "1.0.0", "new-application", "single-surface", "Build a bounded single-surface application objective.", False),
        BenchmarkFixtureTemplate("persisted-multi-surface", "1.0.0", "new-application", "multi-surface", "Build multiple surfaces with persisted application state.", False),
        BenchmarkFixtureTemplate("existing-repository", "1.0.0", "repository-change", "existing-repository", "Modify an existing repository while preserving compatibility evidence.", False),
        BenchmarkFixtureTemplate("browser-visible-ux", "1.0.0", "ux-behavior", "client-web", "Prove browser-visible behavior and UX using admitted evidence only.", False),
        BenchmarkFixtureTemplate("bounded-recovery", "1.0.0", "recovery", "service", "Recover from a bounded worker or candidate failure without duplicate mutation.", False),
        BenchmarkFixtureTemplate("deterministic-block", "1.0.0", "negative-validation", "client-web", "Deterministic failure must block subjective quality support.", True),
        BenchmarkFixtureTemplate("unknown-economics", "1.0.0", "unknown-evidence", "service", "Preserve unknown cost or elapsed-time evidence without favorable defaults.", True),
        BenchmarkFixtureTemplate("cross-project-privacy", "1.0.0", "privacy-negative", "workspace", "Reject cross-Project evidence substitution and private-evidence leakage.", True),
        BenchmarkFixtureTemplate("benchmark-gaming", "1.0.0", "gaming-negative", "workspace", "Reject benchmark-only special casing or expected-answer behavior.", True),
    )
    if len({item.case_id for item in fixtures}) != len(fixtures):
        raise ParallaxBenchError("fixture IDs must remain unique")
    return fixtures


def safe_parallax_bench_json(result: ParallaxBenchResult) -> str:
    if not isinstance(result, ParallaxBenchResult):
        raise ParallaxBenchError("result must be ParallaxBenchResult")
    return json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _bind_case(case: BenchmarkCase, binding: CandidateBinding) -> None:
    expected = (
        case.project_id,
        case.work_specification_id,
        case.work_specification_revision,
        case.work_specification_digest,
        case.acceptance_ids,
    )
    actual = (
        binding.project_id,
        binding.work_specification_id,
        binding.work_specification_revision,
        binding.work_specification_digest,
        binding.acceptance_ids,
    )
    if actual != expected:
        raise ParallaxBenchError("candidate binding does not match exact benchmark case identity")


def _compare_dimension(baseline: DimensionEvidence, challenger: DimensionEvidence) -> DimensionComparison:
    if baseline.dimension is not challenger.dimension:
        raise ParallaxBenchError("dimension comparison mismatch")
    dimension = baseline.dimension
    unknown_states = {BenchmarkEvidenceState.UNAVAILABLE, BenchmarkEvidenceState.UNKNOWN}
    incomparable_states = {BenchmarkEvidenceState.STALE, BenchmarkEvidenceState.INVALID}
    if baseline.state in unknown_states or challenger.state in unknown_states:
        outcome = ComparisonOutcome.UNKNOWN
        material = False
    elif baseline.state in incomparable_states or challenger.state in incomparable_states:
        outcome = ComparisonOutcome.INCOMPARABLE
        material = False
    elif baseline.state is not challenger.state:
        outcome = ComparisonOutcome.INCOMPARABLE
        material = False
    else:
        baseline_value = float(baseline.value)
        challenger_value = float(challenger.value)
        if math.isclose(baseline_value, challenger_value, rel_tol=1e-9, abs_tol=1e-12):
            outcome = ComparisonOutcome.EQUIVALENT
            material = False
        else:
            higher_is_better = dimension not in _LOWER_IS_BETTER
            improved = challenger_value > baseline_value if higher_is_better else challenger_value < baseline_value
            outcome = ComparisonOutcome.IMPROVED if improved else ComparisonOutcome.REGRESSED
            material = improved and baseline.state is BenchmarkEvidenceState.OBSERVED and _material_delta(
                dimension, baseline_value, challenger_value
            )
    return DimensionComparison(
        dimension=dimension,
        outcome=outcome,
        materially_improved=material,
        baseline_digest=baseline.digest,
        challenger_digest=challenger.digest,
    )


def _material_delta(dimension: BenchmarkDimension, baseline: float, challenger: float) -> bool:
    if dimension in _RATIO_DIMENSIONS:
        return challenger - baseline >= 0.05
    if dimension in {BenchmarkDimension.HUMAN_INTERVENTIONS, BenchmarkDimension.RETRY_RECOVERY}:
        return baseline - challenger >= 1.0
    if baseline <= 0:
        return False
    return (baseline - challenger) / baseline >= 0.10


def _protected_regression(baseline: ProtectedFloor, challenger: ProtectedFloor) -> bool:
    if not baseline.hard_guardrails_passed:
        return False
    return not challenger.hard_guardrails_passed


def _acceptance_ids(values: Iterable[str]) -> tuple[str, ...]:
    result = tuple(values)
    if not result or len(result) > _MAX_ACCEPTANCE_IDS:
        raise ParallaxBenchError("acceptance_ids must be bounded and non-empty")
    if any(not isinstance(item, str) or _AC_RE.fullmatch(item) is None for item in result):
        raise ParallaxBenchError("invalid acceptance ID")
    if len(set(result)) != len(result):
        raise ParallaxBenchError("acceptance_ids must be unique")
    return result


def _uuid(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ParallaxBenchError(f"{field} must be UUID text")
    try:
        parsed = UUID(value)
    except (TypeError, ValueError) as exc:
        raise ParallaxBenchError(f"{field} must be UUID text") from exc
    return str(parsed)


def _sha(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ParallaxBenchError(f"{field} must be lowercase sha256 hex")
    return value


def _token(value: str, field: str) -> str:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None:
        raise ParallaxBenchError(f"{field} must be a bounded token")
    return value


def _version(value: str, field: str) -> str:
    if not isinstance(value, str) or _VERSION_RE.fullmatch(value) is None:
        raise ParallaxBenchError(f"{field} must be a bounded version")
    return value


def _reference(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ParallaxBenchError(f"{field} must be text")
    normalized = value.strip()
    if not normalized or len(normalized) > 192 or any(char in normalized for char in ("\n", "\r", "\x00")):
        raise ParallaxBenchError(f"{field} must be a bounded reference")
    return normalized


def _reason(value: str) -> str:
    if not isinstance(value, str) or len(value) > _MAX_REASON or _REASON_RE.fullmatch(value) is None:
        raise ParallaxBenchError("reason_code must be a bounded uppercase token")
    return value


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()
