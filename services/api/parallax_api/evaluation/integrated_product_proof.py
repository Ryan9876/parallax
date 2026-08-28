from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Iterable, Mapping

from parallax_api.code.agent_run_projection import (
    AgentRunProjection,
    DeterministicDisposition,
    ProjectionKnownState,
)
from parallax_api.code.agentic_observability import AgenticRunObservability
from parallax_api.code.domain import AttemptStatus, WorkflowStage
from parallax_api.tools.browser_evidence import (
    BrowserAction,
    BrowserEvidenceRecord,
    BrowserOutcome,
    BrowserTarget,
)

from .parallax_bench import (
    BenchmarkCase,
    BenchmarkDimension,
    CandidateBenchmarkEvidence,
    ComparisonOutcome,
    ParallaxBenchDisposition,
    ParallaxBenchResult,
    ProtectedCeiling,
    evaluate_parallax_bench,
)


INTEGRATED_PRODUCT_PROOF_VERSION = 1
_MAX_BROWSER_RECORDS = 16
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,191}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,95}$")


class IntegratedProductProofError(ValueError):
    """Fail-closed error for malformed, cross-context, or non-canonical S6 evidence."""


class ProofObjectiveClass(StrEnum):
    STATEFUL_WORKFLOW = "stateful-workflow"
    DATA_OPERATIONS = "data-operations"
    PUBLIC_UTILITY = "public-utility"


class ProofCoverageState(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class ProofBrowserState(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class ProofDisposition(StrEnum):
    RELEASE_QUALIFIED = "RELEASE_QUALIFIED"
    VALUE_NOT_DEMONSTRATED = "VALUE_NOT_DEMONSTRATED"
    PROTECTED_BLOCKED = "PROTECTED_BLOCKED"
    INCOMPLETE_EVIDENCE = "INCOMPLETE_EVIDENCE"


@dataclass(frozen=True, slots=True)
class IntegratedProofScenario:
    scenario_id: str
    scenario_version: str
    objective_class: ProofObjectiveClass
    benchmark_case_id: str
    repository_shape: str
    required_acceptance_ids: tuple[str, ...]
    baseline_candidate_id: str
    value_dimension: BenchmarkDimension
    requires_recovery: bool
    requires_parent_lineage: bool
    requires_preview: bool = True
    requires_browser: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _token(self.scenario_id, "scenario_id"))
        object.__setattr__(self, "scenario_version", _reference(self.scenario_version, "scenario_version"))
        try:
            objective = self.objective_class if isinstance(self.objective_class, ProofObjectiveClass) else ProofObjectiveClass(self.objective_class)
            value_dimension = self.value_dimension if isinstance(self.value_dimension, BenchmarkDimension) else BenchmarkDimension(self.value_dimension)
        except (TypeError, ValueError) as exc:
            raise IntegratedProductProofError("invalid scenario enum") from exc
        if value_dimension is BenchmarkDimension.PROTECTED_CORRECTNESS:
            raise IntegratedProductProofError("scenario value dimension must be non-protected")
        object.__setattr__(self, "objective_class", objective)
        object.__setattr__(self, "value_dimension", value_dimension)
        object.__setattr__(self, "benchmark_case_id", _token(self.benchmark_case_id, "benchmark_case_id"))
        object.__setattr__(self, "repository_shape", _token(self.repository_shape, "repository_shape"))
        acceptance = tuple(self.required_acceptance_ids)
        if not acceptance or len(acceptance) != len(set(acceptance)):
            raise IntegratedProductProofError("required_acceptance_ids must be unique and non-empty")
        if any(re.fullmatch(r"AC-[0-9]{2,3}", item) is None for item in acceptance):
            raise IntegratedProductProofError("required_acceptance_ids are invalid")
        object.__setattr__(self, "required_acceptance_ids", acceptance)
        object.__setattr__(self, "baseline_candidate_id", _token(self.baseline_candidate_id, "baseline_candidate_id"))
        for field in ("requires_recovery", "requires_parent_lineage", "requires_preview", "requires_browser"):
            if not isinstance(getattr(self, field), bool):
                raise IntegratedProductProofError(f"{field} must be bool")

    @property
    def fixture_digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_version": self.scenario_version,
            "objective_class": self.objective_class.value,
            "benchmark_case_id": self.benchmark_case_id,
            "repository_shape": self.repository_shape,
            "required_acceptance_ids": list(self.required_acceptance_ids),
            "baseline_candidate_id": self.baseline_candidate_id,
            "value_dimension": self.value_dimension.value,
            "requires_recovery": self.requires_recovery,
            "requires_parent_lineage": self.requires_parent_lineage,
            "requires_preview": self.requires_preview,
            "requires_browser": self.requires_browser,
        }


_SCENARIOS = (
    IntegratedProofScenario(
        scenario_id="stateful-workflow",
        scenario_version="1.0.0",
        objective_class=ProofObjectiveClass.STATEFUL_WORKFLOW,
        benchmark_case_id="w7-stateful-workflow",
        repository_shape="multi-surface",
        required_acceptance_ids=("AC-01", "AC-02", "AC-03", "AC-04"),
        baseline_candidate_id="pre-wave7-stateful-v1",
        value_dimension=BenchmarkDimension.HUMAN_INTERVENTIONS,
        requires_recovery=True,
        requires_parent_lineage=False,
    ),
    IntegratedProofScenario(
        scenario_id="data-operations",
        scenario_version="1.0.0",
        objective_class=ProofObjectiveClass.DATA_OPERATIONS,
        benchmark_case_id="w7-data-operations",
        repository_shape="existing-repository",
        required_acceptance_ids=("AC-01", "AC-02", "AC-03", "AC-04"),
        baseline_candidate_id="pre-wave7-operations-v1",
        value_dimension=BenchmarkDimension.COMPLETION_RELIABILITY,
        requires_recovery=False,
        requires_parent_lineage=True,
    ),
    IntegratedProofScenario(
        scenario_id="public-utility",
        scenario_version="1.0.0",
        objective_class=ProofObjectiveClass.PUBLIC_UTILITY,
        benchmark_case_id="w7-public-utility",
        repository_shape="client-web",
        required_acceptance_ids=("AC-01", "AC-02", "AC-03", "AC-04"),
        baseline_candidate_id="pre-wave7-utility-v1",
        value_dimension=BenchmarkDimension.VISUAL_UX_QUALITY,
        requires_recovery=False,
        requires_parent_lineage=False,
    ),
)

WAVE7_PROOF_SCENARIOS: Mapping[str, IntegratedProofScenario] = MappingProxyType(
    {item.scenario_id: item for item in _SCENARIOS}
)
if len(WAVE7_PROOF_SCENARIOS) != 3:
    raise RuntimeError("Wave 7 integrated proof portfolio must remain exactly three scenarios")


@dataclass(frozen=True, slots=True)
class BrowserProofBundle:
    target: BrowserTarget
    records: tuple[BrowserEvidenceRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.target, BrowserTarget):
            raise IntegratedProductProofError("browser proof requires canonical BrowserTarget")
        records = tuple(self.records)
        if not records or len(records) > _MAX_BROWSER_RECORDS:
            raise IntegratedProductProofError("browser proof record cardinality is outside the protected bound")
        if any(not isinstance(item, BrowserEvidenceRecord) for item in records):
            raise IntegratedProductProofError("browser proof requires canonical BrowserEvidenceRecord values")
        object.__setattr__(self, "records", records)


@dataclass(frozen=True, slots=True)
class ScenarioProofRecord:
    scenario_id: str
    scenario_version: str
    objective_class: str
    project_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    run_id: str
    run_revision: int
    run_state: str
    source_lineage_ref: str
    parent_source_lineage_ref: str | None
    preview_deployment_id: str | None
    projection_fingerprint: str
    observability_fingerprint: str
    observability_coverage: ProofCoverageState
    benchmark_case_digest: str
    benchmark_result_digest: str
    benchmark_fingerprint: str
    benchmark_disposition: str
    value_dimension: str
    value_outcome: str
    value_materially_improved: bool
    browser_state: ProofBrowserState
    browser_target_digest: str | None
    browser_evidence_digests: tuple[str, ...]
    recovery_proven: bool
    deterministic_disposition: str
    final_handoff: str | None
    protected_passed: bool
    evidence_complete: bool
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _token(self.scenario_id, "scenario_id"))
        object.__setattr__(self, "scenario_version", _reference(self.scenario_version, "scenario_version"))
        object.__setattr__(self, "objective_class", _token(self.objective_class, "objective_class"))
        for field in (
            "work_specification_digest",
            "projection_fingerprint",
            "observability_fingerprint",
            "benchmark_case_digest",
            "benchmark_result_digest",
            "benchmark_fingerprint",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field))
        if self.browser_target_digest is not None:
            object.__setattr__(self, "browser_target_digest", _sha(self.browser_target_digest, "browser_target_digest"))
        evidence_digests = tuple(_sha(item, "browser_evidence_digest") for item in self.browser_evidence_digests)
        object.__setattr__(self, "browser_evidence_digests", evidence_digests)
        try:
            object.__setattr__(self, "observability_coverage", ProofCoverageState(self.observability_coverage))
            object.__setattr__(self, "browser_state", ProofBrowserState(self.browser_state))
        except ValueError as exc:
            raise IntegratedProductProofError("invalid proof record state") from exc
        for field in ("value_materially_improved", "recovery_proven", "protected_passed", "evidence_complete"):
            if not isinstance(getattr(self, field), bool):
                raise IntegratedProductProofError(f"{field} must be bool")
        object.__setattr__(self, "reason_code", _reason(self.reason_code))

    @property
    def fingerprint(self) -> str:
        return _digest(self.as_dict(include_fingerprint=False))

    def as_dict(self, *, include_fingerprint: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "integrated_product_proof_version": INTEGRATED_PRODUCT_PROOF_VERSION,
            "scenario_id": self.scenario_id,
            "scenario_version": self.scenario_version,
            "objective_class": self.objective_class,
            "project_id": self.project_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "run_id": self.run_id,
            "run_revision": self.run_revision,
            "run_state": self.run_state,
            "source_lineage_ref": self.source_lineage_ref,
            "parent_source_lineage_ref": self.parent_source_lineage_ref,
            "preview_deployment_id": self.preview_deployment_id,
            "projection_fingerprint": self.projection_fingerprint,
            "observability_fingerprint": self.observability_fingerprint,
            "observability_coverage": self.observability_coverage.value,
            "benchmark_case_digest": self.benchmark_case_digest,
            "benchmark_result_digest": self.benchmark_result_digest,
            "benchmark_fingerprint": self.benchmark_fingerprint,
            "benchmark_disposition": self.benchmark_disposition,
            "value_dimension": self.value_dimension,
            "value_outcome": self.value_outcome,
            "value_materially_improved": self.value_materially_improved,
            "browser_state": self.browser_state.value,
            "browser_target_digest": self.browser_target_digest,
            "browser_evidence_digests": list(self.browser_evidence_digests),
            "recovery_proven": self.recovery_proven,
            "deterministic_disposition": self.deterministic_disposition,
            "final_handoff": self.final_handoff,
            "protected_passed": self.protected_passed,
            "evidence_complete": self.evidence_complete,
            "reason_code": self.reason_code,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
            "grants_provider_authority": False,
            "grants_tool_authority": False,
            "executes_arbitrary_command": False,
            "performs_arbitrary_network": False,
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
            "contains_unrestricted_logs": False,
            "contains_sensitive_urls": False,
        }
        if include_fingerprint:
            data["fingerprint"] = self.fingerprint
        return data


@dataclass(frozen=True, slots=True)
class IntegratedProductProofResult:
    proof_version: int
    portfolio_digest: str
    scenario_fingerprints: tuple[str, ...]
    protected_passed: bool
    evidence_complete: bool
    material_value_demonstrated: bool
    disposition: ProofDisposition
    reason_code: str
    autonomous_ceiling: str = "HUMAN_REQUIRED"

    def __post_init__(self) -> None:
        if self.proof_version != INTEGRATED_PRODUCT_PROOF_VERSION:
            raise IntegratedProductProofError("unsupported integrated proof version")
        object.__setattr__(self, "portfolio_digest", _sha(self.portfolio_digest, "portfolio_digest"))
        fingerprints = tuple(_sha(item, "scenario_fingerprint") for item in self.scenario_fingerprints)
        if len(fingerprints) != len(WAVE7_PROOF_SCENARIOS):
            raise IntegratedProductProofError("aggregate proof must contain the complete immutable scenario portfolio")
        object.__setattr__(self, "scenario_fingerprints", fingerprints)
        for field in ("protected_passed", "evidence_complete", "material_value_demonstrated"):
            if not isinstance(getattr(self, field), bool):
                raise IntegratedProductProofError(f"{field} must be bool")
        try:
            disposition = self.disposition if isinstance(self.disposition, ProofDisposition) else ProofDisposition(self.disposition)
        except ValueError as exc:
            raise IntegratedProductProofError("invalid integrated proof disposition") from exc
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        if self.autonomous_ceiling != "HUMAN_REQUIRED":
            raise IntegratedProductProofError("integrated proof cannot raise the autonomous REVIEW ceiling")

    @property
    def release_qualified(self) -> bool:
        return self.disposition is ProofDisposition.RELEASE_QUALIFIED

    @property
    def fingerprint(self) -> str:
        return _digest(self.as_dict(include_fingerprint=False))

    def as_dict(self, *, include_fingerprint: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "integrated_product_proof_version": self.proof_version,
            "portfolio_digest": self.portfolio_digest,
            "scenario_fingerprints": list(self.scenario_fingerprints),
            "protected_passed": self.protected_passed,
            "evidence_complete": self.evidence_complete,
            "material_value_demonstrated": self.material_value_demonstrated,
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "autonomous_ceiling": self.autonomous_ceiling,
            "release_qualified": self.release_qualified,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
            "grants_provider_authority": False,
            "grants_tool_authority": False,
            "executes_arbitrary_command": False,
            "performs_arbitrary_network": False,
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
            "contains_unrestricted_logs": False,
            "contains_sensitive_urls": False,
        }
        if include_fingerprint:
            data["fingerprint"] = self.fingerprint
        return data


def build_scenario_proof(
    *,
    scenario_id: str,
    projection: AgentRunProjection,
    observability: AgenticRunObservability,
    benchmark_case: BenchmarkCase,
    benchmark_baseline: CandidateBenchmarkEvidence,
    benchmark_challenger: CandidateBenchmarkEvidence,
    benchmark_result: ParallaxBenchResult,
    browser: BrowserProofBundle | None,
) -> ScenarioProofRecord:
    scenario = WAVE7_PROOF_SCENARIOS.get(scenario_id)
    if scenario is None:
        raise IntegratedProductProofError("scenario is not part of the immutable Wave 7 proof portfolio")
    if not isinstance(projection, AgentRunProjection):
        raise IntegratedProductProofError("S6 requires canonical S3 AgentRunProjection evidence")
    if not isinstance(observability, AgenticRunObservability):
        raise IntegratedProductProofError("S6 requires canonical S5 AgenticRunObservability evidence")
    if not isinstance(benchmark_case, BenchmarkCase):
        raise IntegratedProductProofError("S6 requires canonical ParallaxBench case evidence")
    if not isinstance(benchmark_baseline, CandidateBenchmarkEvidence) or not isinstance(benchmark_challenger, CandidateBenchmarkEvidence):
        raise IntegratedProductProofError("S6 requires canonical ParallaxBench candidate evidence")
    if not isinstance(benchmark_result, ParallaxBenchResult):
        raise IntegratedProductProofError("S6 requires canonical ParallaxBench result evidence")

    identity = projection.identity
    _validate_scenario_case(scenario, benchmark_case)
    _validate_identity_continuity(
        projection=projection,
        observability=observability,
        benchmark_case=benchmark_case,
        benchmark_baseline=benchmark_baseline,
        benchmark_challenger=benchmark_challenger,
    )

    recomputed = evaluate_parallax_bench(
        case=benchmark_case,
        baseline=benchmark_baseline,
        challenger=benchmark_challenger,
    )
    if recomputed.result_digest != benchmark_result.result_digest or recomputed.fingerprint != benchmark_result.fingerprint:
        raise IntegratedProductProofError("benchmark result does not match exact canonical benchmark inputs")

    lineage = projection.latest_source_lineage_ref
    if lineage is None or not lineage.startswith("src:") or len(lineage) != 68:
        raise IntegratedProductProofError("proof requires exact accepted source lineage")
    if projection.delivery.source_lineage_ref != lineage:
        raise IntegratedProductProofError("delivery lineage does not match the canonical projection lineage")
    if benchmark_challenger.binding.source_context_digest != lineage.removeprefix("src:"):
        raise IntegratedProductProofError("benchmark challenger is not bound to exact accepted source lineage")
    if scenario.requires_parent_lineage and projection.delivery.parent_source_lineage_ref is None:
        raise IntegratedProductProofError("scenario requires exact parent source lineage evidence")

    lifecycle_complete = _ordinary_lifecycle_complete(projection)
    recovery_proven = _recovery_proven(projection) if scenario.requires_recovery else True
    coverage = _observability_coverage(observability)
    browser_state, target_digest, browser_digests = _browser_proof(
        scenario=scenario,
        projection=projection,
        browser=browser,
    )

    protected_comparison = _comparison(recomputed, BenchmarkDimension.PROTECTED_CORRECTNESS)
    value_comparison = _comparison(recomputed, scenario.value_dimension)
    protected_passed = (
        projection.deterministic_disposition is DeterministicDisposition.PASSED
        and observability.quality.deterministic_disposition is DeterministicDisposition.PASSED
        and observability.quality.effective_disposition is DeterministicDisposition.PASSED
        and benchmark_challenger.protected_floor.hard_guardrails_passed
        and protected_comparison.outcome is not ComparisonOutcome.REGRESSED
        and recomputed.disposition not in {
            ParallaxBenchDisposition.DETERMINISTIC_BLOCKED,
            ParallaxBenchDisposition.REGRESSED,
            ParallaxBenchDisposition.POLICY_REJECTED,
        }
    )

    preview_complete = (
        not scenario.requires_preview
        or (
            projection.delivery.preview_deployment_id is not None
            and projection.delivery.preview_status is not None
            and projection.delivery.source_lineage_ref == lineage
        )
    )
    handoff_complete = (
        projection.current_state == WorkflowStage.REVIEW.value
        and projection.final_handoff == "HUMAN_REQUIRED"
        and benchmark_challenger.protected_floor.review_ceiling_preserved
        and benchmark_challenger.protected_floor.human_required
    )
    evidence_complete = (
        lifecycle_complete
        and recovery_proven
        and preview_complete
        and handoff_complete
        and coverage is not ProofCoverageState.UNAVAILABLE
        and (not scenario.requires_browser or browser_state is ProofBrowserState.PASSED)
    )

    if not protected_passed:
        reason = "PROTECTED_EVIDENCE_BLOCKED"
    elif not evidence_complete:
        reason = "INTEGRATED_EVIDENCE_INCOMPLETE"
    elif value_comparison.materially_improved:
        reason = "SCENARIO_VALUE_MATERIALLY_IMPROVED"
    elif value_comparison.outcome is ComparisonOutcome.REGRESSED:
        reason = "SCENARIO_VALUE_REGRESSED"
    else:
        reason = "SCENARIO_VALUE_NOT_MATERIALLY_IMPROVED"

    return ScenarioProofRecord(
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.scenario_version,
        objective_class=scenario.objective_class.value,
        project_id=identity.project_id,
        work_specification_id=identity.work_specification_id,
        work_specification_revision=identity.work_specification_revision,
        work_specification_digest=identity.work_specification_digest,
        acceptance_ids=identity.acceptance_ids,
        run_id=identity.run_id,
        run_revision=projection.run_revision,
        run_state=projection.current_state,
        source_lineage_ref=lineage,
        parent_source_lineage_ref=projection.delivery.parent_source_lineage_ref,
        preview_deployment_id=projection.delivery.preview_deployment_id,
        projection_fingerprint=projection.fingerprint,
        observability_fingerprint=observability.fingerprint,
        observability_coverage=coverage,
        benchmark_case_digest=benchmark_case.digest,
        benchmark_result_digest=recomputed.result_digest,
        benchmark_fingerprint=recomputed.fingerprint,
        benchmark_disposition=recomputed.disposition.value,
        value_dimension=scenario.value_dimension.value,
        value_outcome=value_comparison.outcome.value,
        value_materially_improved=value_comparison.materially_improved,
        browser_state=browser_state,
        browser_target_digest=target_digest,
        browser_evidence_digests=browser_digests,
        recovery_proven=recovery_proven,
        deterministic_disposition=projection.deterministic_disposition.value,
        final_handoff=projection.final_handoff,
        protected_passed=protected_passed,
        evidence_complete=evidence_complete,
        reason_code=reason,
    )


def build_integrated_product_proof(records: Iterable[ScenarioProofRecord]) -> IntegratedProductProofResult:
    rows = tuple(records)
    if len(rows) != len(WAVE7_PROOF_SCENARIOS):
        raise IntegratedProductProofError("all immutable Wave 7 proof scenarios must be supplied")
    if any(not isinstance(item, ScenarioProofRecord) for item in rows):
        raise IntegratedProductProofError("aggregate proof requires canonical ScenarioProofRecord values")
    by_id = {item.scenario_id: item for item in rows}
    if set(by_id) != set(WAVE7_PROOF_SCENARIOS) or len(by_id) != len(rows):
        raise IntegratedProductProofError("proof scenario portfolio cannot be cherry-picked, duplicated, or substituted")

    ordered = tuple(by_id[item.scenario_id] for item in _SCENARIOS)
    protected_passed = all(item.protected_passed for item in ordered)
    evidence_complete = all(item.evidence_complete for item in ordered)
    material_value = any(item.value_materially_improved for item in ordered)
    value_regressed = any(item.value_outcome == ComparisonOutcome.REGRESSED.value for item in ordered)

    if not protected_passed:
        disposition = ProofDisposition.PROTECTED_BLOCKED
        reason = "PORTFOLIO_PROTECTED_EVIDENCE_BLOCKED"
    elif not evidence_complete:
        disposition = ProofDisposition.INCOMPLETE_EVIDENCE
        reason = "PORTFOLIO_EVIDENCE_INCOMPLETE"
    elif value_regressed or not material_value:
        disposition = ProofDisposition.VALUE_NOT_DEMONSTRATED
        reason = "PORTFOLIO_VALUE_NOT_DEMONSTRATED"
    else:
        disposition = ProofDisposition.RELEASE_QUALIFIED
        reason = "PORTFOLIO_VALUE_DEMONSTRATED_WITH_PROTECTED_PARITY"

    return IntegratedProductProofResult(
        proof_version=INTEGRATED_PRODUCT_PROOF_VERSION,
        portfolio_digest=wave7_proof_portfolio_digest(),
        scenario_fingerprints=tuple(item.fingerprint for item in ordered),
        protected_passed=protected_passed,
        evidence_complete=evidence_complete,
        material_value_demonstrated=material_value and not value_regressed,
        disposition=disposition,
        reason_code=reason,
    )


def wave7_proof_portfolio_digest() -> str:
    return _digest([item.as_dict() for item in _SCENARIOS])


def safe_integrated_product_proof_json(result: IntegratedProductProofResult) -> str:
    if not isinstance(result, IntegratedProductProofResult):
        raise IntegratedProductProofError("result must be IntegratedProductProofResult")
    return json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def safe_scenario_proof_json(record: ScenarioProofRecord) -> str:
    if not isinstance(record, ScenarioProofRecord):
        raise IntegratedProductProofError("record must be ScenarioProofRecord")
    return json.dumps(record.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _validate_scenario_case(scenario: IntegratedProofScenario, case: BenchmarkCase) -> None:
    expected_dimensions = tuple(sorted(
        (BenchmarkDimension.PROTECTED_CORRECTNESS, scenario.value_dimension),
        key=lambda item: item.value,
    ))
    if (
        case.case_id != scenario.benchmark_case_id
        or case.case_version != scenario.scenario_version
        or case.objective_class != scenario.objective_class.value
        or case.repository_shape != scenario.repository_shape
        or case.acceptance_ids != scenario.required_acceptance_ids
        or case.comparable_dimensions != expected_dimensions
        or case.fixture_digest != scenario.fixture_digest
        or case.expected_ceiling is ProtectedCeiling.DETERMINISTIC_BLOCKED
    ):
        raise IntegratedProductProofError("benchmark case does not match immutable S6 scenario policy")


def _validate_identity_continuity(
    *,
    projection: AgentRunProjection,
    observability: AgenticRunObservability,
    benchmark_case: BenchmarkCase,
    benchmark_baseline: CandidateBenchmarkEvidence,
    benchmark_challenger: CandidateBenchmarkEvidence,
) -> None:
    identity = projection.identity
    expected = (
        identity.project_id,
        identity.work_specification_id,
        identity.work_specification_revision,
        identity.work_specification_digest,
        identity.acceptance_ids,
    )
    case_identity = (
        benchmark_case.project_id,
        benchmark_case.work_specification_id,
        benchmark_case.work_specification_revision,
        benchmark_case.work_specification_digest,
        benchmark_case.acceptance_ids,
    )
    if case_identity != expected:
        raise IntegratedProductProofError("ParallaxBench case crosses canonical Project/Work Specification identity")
    if benchmark_baseline.binding.project_id != identity.project_id:
        raise IntegratedProductProofError("baseline Project identity does not match the canonical scenario Project")
    if benchmark_challenger.binding.project_id != identity.project_id or benchmark_challenger.binding.run_id != identity.run_id:
        raise IntegratedProductProofError("challenger Project/run identity does not match the canonical projection")
    if observability.project_id != identity.project_id or observability.run_id != identity.run_id:
        raise IntegratedProductProofError("S5 observability crosses canonical Project/run identity")
    if observability.run_revision != projection.run_revision:
        raise IntegratedProductProofError("S5 observability revision is stale relative to S3 projection")
    if observability.projection_fingerprint != projection.fingerprint:
        raise IntegratedProductProofError("S5 observability is not bound to the exact S3 projection")

    challenger = benchmark_challenger.binding
    challenger_identity = (
        challenger.project_id,
        challenger.work_specification_id,
        challenger.work_specification_revision,
        challenger.work_specification_digest,
        challenger.acceptance_ids,
    )
    if challenger_identity != expected:
        raise IntegratedProductProofError("benchmark challenger crosses canonical Work Specification identity")
    scenario = next((item for item in _SCENARIOS if item.benchmark_case_id == benchmark_case.case_id), None)
    if scenario is None or benchmark_baseline.binding.candidate_id != scenario.baseline_candidate_id:
        raise IntegratedProductProofError("benchmark baseline is not the predeclared server-owned scenario baseline")


def _ordinary_lifecycle_complete(projection: AgentRunProjection) -> bool:
    required = (
        WorkflowStage.PLAN.value,
        WorkflowStage.IMPLEMENT.value,
        WorkflowStage.BUILD.value,
        WorkflowStage.TEST.value,
        WorkflowStage.VERIFY.value,
    )
    by_stage = {stage: [item for item in projection.tasks if item.stage == stage] for stage in required}
    if any(not rows for rows in by_stage.values()):
        return False
    return all(rows[-1].status == AttemptStatus.PASSED.value for rows in by_stage.values())


def _recovery_proven(projection: AgentRunProjection) -> bool:
    recovery = projection.recovery
    return (
        recovery.execution_id is not None
        and recovery.state is not None
        and recovery.checkpoint_revision is not None
        and recovery.checkpoint_revision >= 1
        and recovery.retry_count is not None
        and recovery.retry_count >= 1
        and recovery.no_progress_count is not None
        and recovery.no_progress_count >= 0
        and recovery.oscillation_count is not None
        and recovery.oscillation_count >= 0
    )


def _observability_coverage(observability: AgenticRunObservability) -> ProofCoverageState:
    coverage = observability.coverage
    if not coverage.event_plane_available:
        return ProofCoverageState.UNAVAILABLE
    if coverage.event_plane_complete:
        return ProofCoverageState.COMPLETE
    return ProofCoverageState.PARTIAL


def _browser_proof(
    *,
    scenario: IntegratedProofScenario,
    projection: AgentRunProjection,
    browser: BrowserProofBundle | None,
) -> tuple[ProofBrowserState, str | None, tuple[str, ...]]:
    if browser is None:
        return (
            ProofBrowserState.UNAVAILABLE if scenario.requires_browser else ProofBrowserState.PASSED,
            None,
            (),
        )
    target = browser.target
    identity = projection.identity
    if target.project_id != identity.project_id or target.run_id != identity.run_id:
        raise IntegratedProductProofError("browser target crosses canonical Project/run identity")
    if target.source_lineage_ref != projection.delivery.source_lineage_ref:
        raise IntegratedProductProofError("browser target is not bound to exact accepted source lineage")
    if target.preview_deployment_id != projection.delivery.preview_deployment_id:
        raise IntegratedProductProofError("browser target is not bound to exact Preview delivery identity")

    assertion_passed = False
    digests: list[str] = []
    for record in browser.records:
        if (
            record.project_id != identity.project_id
            or record.run_id != identity.run_id
            or record.target_id != target.target_id
            or record.target_digest != target.digest
        ):
            raise IntegratedProductProofError("browser evidence record crosses admitted target identity")
        if record.outcome is not BrowserOutcome.SUCCEEDED:
            return ProofBrowserState.FAILED, target.digest, tuple(item.digest for item in browser.records)
        if record.action is BrowserAction.ASSERT and record.assertion_passed is True:
            assertion_passed = True
        digests.append(record.digest)
    return (
        ProofBrowserState.PASSED if assertion_passed else ProofBrowserState.FAILED,
        target.digest,
        tuple(digests),
    )


def _comparison(result: ParallaxBenchResult, dimension: BenchmarkDimension):
    for item in result.comparisons:
        if item.dimension is dimension:
            return item
    raise IntegratedProductProofError("benchmark result is missing a required comparison")


def _token(value: str, field: str) -> str:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None:
        raise IntegratedProductProofError(f"{field} must be a bounded token")
    return value


def _reference(value: str, field: str) -> str:
    if not isinstance(value, str) or _REF_RE.fullmatch(value) is None:
        raise IntegratedProductProofError(f"{field} must be a bounded reference")
    return value


def _sha(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise IntegratedProductProofError(f"{field} must be lowercase sha256 hex")
    return value


def _reason(value: str) -> str:
    if not isinstance(value, str) or _REASON_RE.fullmatch(value) is None:
        raise IntegratedProductProofError("reason_code must be a bounded uppercase token")
    return value


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()
