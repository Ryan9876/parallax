from __future__ import annotations

from dataclasses import replace
import json

import pytest

from parallax_api.evaluation.parallax_bench import (
    BenchmarkCase,
    BenchmarkDimension,
    BenchmarkEvidenceState,
    BenchmarkProvenance,
    CandidateBenchmarkEvidence,
    CandidateBinding,
    ComparisonOutcome,
    DimensionEvidence,
    ParallaxBenchDisposition,
    ParallaxBenchError,
    ProtectedCeiling,
    ProtectedFloor,
    evaluate_parallax_bench,
    parallax_bench_v1_fixtures,
    safe_parallax_bench_json,
)
from parallax_api.evaluation.parallax_bench_catalog import validate_case_catalog


PROJECT = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT = "99999999-9999-4999-8999-999999999999"
BASELINE_RUN = "22222222-2222-4222-8222-222222222222"
CHALLENGER_RUN = "44444444-4444-4444-8444-444444444444"
SPEC = "33333333-3333-4333-8333-333333333333"
SPEC_DIGEST = "a" * 64
ACCEPTANCE = ("AC-01", "AC-02", "AC-03")


def _case(
    *,
    case_id: str = "objective-case",
    comparable_dimensions: tuple[BenchmarkDimension, ...] = tuple(BenchmarkDimension),
    expected_ceiling: ProtectedCeiling = ProtectedCeiling.REVIEW,
) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=case_id,
        case_version="1.0.0",
        objective_class="new-application",
        project_id=PROJECT,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        repository_shape="client-web",
        comparable_dimensions=comparable_dimensions,
        expected_ceiling=expected_ceiling,
        fixture_digest="f" * 64,
    )


def _binding(*, challenger: bool = False, project_id: str = PROJECT) -> CandidateBinding:
    return CandidateBinding(
        project_id=project_id,
        run_id=CHALLENGER_RUN if challenger else BASELINE_RUN,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        candidate_id="challenger" if challenger else "baseline",
        source_context_digest=("2" if challenger else "1") * 64,
        protected_validation_digest=("4" if challenger else "3") * 64,
        evaluator_policy_digest="5" * 64,
    )


def _floor(
    *,
    passed: bool = True,
    human_required: bool = False,
    safety: bool = True,
    privacy: bool = True,
    governance: bool = True,
    review: bool = True,
) -> ProtectedFloor:
    return ProtectedFloor(
        acceptance_complete=passed,
        deterministic_validation_passed=passed,
        safety_preserved=safety,
        privacy_preserved=privacy,
        governance_preserved=governance,
        review_ceiling_preserved=review,
        human_required=human_required,
        evidence_digest=("6" if passed else "7") * 64,
    )


def _dimension(
    dimension: BenchmarkDimension,
    value: float | None,
    *,
    state: BenchmarkEvidenceState = BenchmarkEvidenceState.OBSERVED,
    provenance: BenchmarkProvenance | None = None,
    suffix: str = "a",
) -> DimensionEvidence:
    if provenance is None:
        if dimension is BenchmarkDimension.PROTECTED_CORRECTNESS:
            provenance = BenchmarkProvenance.PROTECTED
        elif dimension is BenchmarkDimension.VISUAL_UX_QUALITY:
            provenance = BenchmarkProvenance.EVALUATOR
        elif dimension is BenchmarkDimension.COST_USAGE:
            provenance = BenchmarkProvenance.PROVIDER_OBSERVED
        elif dimension is BenchmarkDimension.COMPLETION_RELIABILITY:
            provenance = BenchmarkProvenance.FIXTURE_BOUND
        else:
            provenance = BenchmarkProvenance.PARALLAX_OBSERVED
    return DimensionEvidence(
        dimension=dimension,
        state=state,
        provenance=provenance,
        value=value,
        evidence_ref=f"evidence:{dimension.value}:{suffix}",
        evidence_digest=(format(ord(suffix) % 16, "x") * 64),
    )


def _candidate(
    *,
    challenger: bool = False,
    floor: ProtectedFloor | None = None,
    overrides: dict[BenchmarkDimension, tuple[BenchmarkEvidenceState, float | None, BenchmarkProvenance | None]] | None = None,
    project_id: str = PROJECT,
) -> CandidateBenchmarkEvidence:
    floor = floor or _floor()
    values = {
        BenchmarkDimension.OBJECTIVE_COMPLETION: 0.90 if challenger else 0.80,
        BenchmarkDimension.PROTECTED_CORRECTNESS: 1.0 if floor.hard_guardrails_passed else 0.0,
        BenchmarkDimension.VISUAL_UX_QUALITY: 0.82 if challenger else 0.75,
        BenchmarkDimension.HUMAN_INTERVENTIONS: 2.0 if challenger else 3.0,
        BenchmarkDimension.ELAPSED_TIME: 850.0 if challenger else 1000.0,
        BenchmarkDimension.COST_USAGE: 1.70 if challenger else 2.00,
        BenchmarkDimension.RETRY_RECOVERY: 1.0 if challenger else 2.0,
        BenchmarkDimension.COMPLETION_RELIABILITY: 0.90 if challenger else 0.80,
    }
    overrides = overrides or {}
    dimensions: list[DimensionEvidence] = []
    for index, dimension in enumerate(BenchmarkDimension):
        state, value, provenance = overrides.get(
            dimension,
            (BenchmarkEvidenceState.OBSERVED, values[dimension], None),
        )
        dimensions.append(
            _dimension(
                dimension,
                value,
                state=state,
                provenance=provenance,
                suffix=chr(ord("a") + index + (8 if challenger else 0)),
            )
        )
    return CandidateBenchmarkEvidence(
        binding=_binding(challenger=challenger, project_id=project_id),
        protected_floor=floor,
        dimensions=tuple(dimensions),
    )


def _comparison(result, dimension: BenchmarkDimension):
    return next(item for item in result.comparisons if item.dimension is dimension)


def test_material_improvement_requires_guardrail_parity_and_observed_evidence() -> None:
    result = evaluate_parallax_bench(
        case=_case(),
        baseline=_candidate(),
        challenger=_candidate(challenger=True),
    )

    assert result.disposition is ParallaxBenchDisposition.SUPPORTED
    assert result.material_improvement is True
    assert result.reason_code == "MATERIAL_IMPROVEMENT_WITH_GUARDRAIL_PARITY"
    assert _comparison(result, BenchmarkDimension.OBJECTIVE_COMPLETION).outcome is ComparisonOutcome.IMPROVED
    assert _comparison(result, BenchmarkDimension.ELAPSED_TIME).materially_improved is True
    assert len(result.comparisons) == len(BenchmarkDimension)


def test_deterministic_failure_blocks_before_visual_or_economic_judgment() -> None:
    failed = _floor(passed=False)
    overrides = {
        BenchmarkDimension.VISUAL_UX_QUALITY: (
            BenchmarkEvidenceState.UNKNOWN,
            None,
            BenchmarkProvenance.EVALUATOR,
        )
    }
    result = evaluate_parallax_bench(
        case=_case(),
        baseline=_candidate(),
        challenger=_candidate(challenger=True, floor=failed, overrides=overrides),
    )

    assert result.disposition is ParallaxBenchDisposition.DETERMINISTIC_BLOCKED
    assert result.material_improvement is False
    assert result.reason_code == "CHALLENGER_PROTECTED_FLOOR_FAILED"


def test_visual_evidence_is_rejected_when_deterministic_validation_failed() -> None:
    with pytest.raises(ParallaxBenchError, match="visual/UX evidence is inadmissible"):
        _candidate(challenger=True, floor=_floor(passed=False))


def test_protected_correctness_must_exactly_match_protected_floor() -> None:
    with pytest.raises(ParallaxBenchError, match="protected correctness dimension must match"):
        _candidate(
            floor=_floor(),
            overrides={
                BenchmarkDimension.PROTECTED_CORRECTNESS: (
                    BenchmarkEvidenceState.OBSERVED,
                    0.0,
                    BenchmarkProvenance.PROTECTED,
                )
            },
        )


def test_unknown_evidence_stays_unknown_and_cannot_carry_favorable_default() -> None:
    case = _case(comparable_dimensions=(BenchmarkDimension.COST_USAGE,))
    unknown = {
        BenchmarkDimension.COST_USAGE: (
            BenchmarkEvidenceState.UNKNOWN,
            None,
            BenchmarkProvenance.PROVIDER_OBSERVED,
        )
    }
    result = evaluate_parallax_bench(
        case=case,
        baseline=_candidate(overrides=unknown),
        challenger=_candidate(challenger=True, overrides=unknown),
    )

    assert result.disposition is ParallaxBenchDisposition.INSUFFICIENT_EVIDENCE
    assert _comparison(result, BenchmarkDimension.COST_USAGE).outcome is ComparisonOutcome.UNKNOWN
    assert result.material_improvement is False

    with pytest.raises(ParallaxBenchError, match="non-numeric evidence state cannot carry value"):
        _dimension(
            BenchmarkDimension.COST_USAGE,
            0.0,
            state=BenchmarkEvidenceState.UNKNOWN,
            provenance=BenchmarkProvenance.PROVIDER_OBSERVED,
        )


def test_observed_and_estimated_values_are_not_silently_compared() -> None:
    estimated = {
        BenchmarkDimension.ELAPSED_TIME: (
            BenchmarkEvidenceState.ESTIMATED,
            800.0,
            BenchmarkProvenance.ESTIMATED,
        )
    }
    result = evaluate_parallax_bench(
        case=_case(comparable_dimensions=(BenchmarkDimension.ELAPSED_TIME,)),
        baseline=_candidate(),
        challenger=_candidate(challenger=True, overrides=estimated),
    )

    assert result.disposition is ParallaxBenchDisposition.INCOMPARABLE
    assert _comparison(result, BenchmarkDimension.ELAPSED_TIME).outcome is ComparisonOutcome.INCOMPARABLE
    assert result.material_improvement is False

    with pytest.raises(ParallaxBenchError, match="estimated evidence requires ESTIMATED provenance"):
        _dimension(
            BenchmarkDimension.ELAPSED_TIME,
            800.0,
            state=BenchmarkEvidenceState.ESTIMATED,
            provenance=BenchmarkProvenance.PARALLAX_OBSERVED,
        )


def test_cross_project_or_work_spec_identity_cannot_satisfy_case() -> None:
    with pytest.raises(ParallaxBenchError, match="exact benchmark case identity"):
        evaluate_parallax_bench(
            case=_case(),
            baseline=_candidate(),
            challenger=_candidate(challenger=True, project_id=OTHER_PROJECT),
        )

    drifted_binding = replace(
        _binding(challenger=True),
        work_specification_digest="b" * 64,
    )
    drifted = replace(_candidate(challenger=True), binding=drifted_binding)
    with pytest.raises(ParallaxBenchError, match="exact benchmark case identity"):
        evaluate_parallax_bench(case=_case(), baseline=_candidate(), challenger=drifted)


def test_catalog_rejects_duplicate_identity_even_when_content_differs() -> None:
    original = _case()
    conflicting = replace(original, repository_shape="workspace")

    with pytest.raises(ParallaxBenchError, match="conflicts with different content"):
        validate_case_catalog((original, conflicting))

    with pytest.raises(ParallaxBenchError, match="must be unique"):
        validate_case_catalog((original, original))


def test_replay_is_deterministic_and_evidence_drift_changes_identity() -> None:
    case = _case()
    baseline = _candidate()
    challenger = _candidate(challenger=True)
    first = evaluate_parallax_bench(case=case, baseline=baseline, challenger=challenger)
    replay = evaluate_parallax_bench(case=case, baseline=baseline, challenger=challenger)

    assert replay.fingerprint == first.fingerprint
    assert replay.result_digest == first.result_digest
    assert safe_parallax_bench_json(replay) == safe_parallax_bench_json(first)

    changed = _candidate(
        challenger=True,
        overrides={
            BenchmarkDimension.COST_USAGE: (
                BenchmarkEvidenceState.OBSERVED,
                1.65,
                BenchmarkProvenance.PROVIDER_OBSERVED,
            )
        },
    )
    drift = evaluate_parallax_bench(case=case, baseline=baseline, challenger=changed)
    assert drift.fingerprint != first.fingerprint
    assert drift.result_digest != first.result_digest


def test_human_required_is_never_hidden_by_better_metrics() -> None:
    result = evaluate_parallax_bench(
        case=_case(expected_ceiling=ProtectedCeiling.HUMAN_REQUIRED),
        baseline=_candidate(),
        challenger=_candidate(challenger=True, floor=_floor(human_required=True)),
    )
    assert result.disposition is ParallaxBenchDisposition.HUMAN_REQUIRED
    assert result.material_improvement is False


def test_safe_serialization_exposes_no_authority_or_sensitive_payload_fields() -> None:
    result = evaluate_parallax_bench(
        case=_case(),
        baseline=_candidate(),
        challenger=_candidate(challenger=True),
    )
    payload = json.loads(safe_parallax_bench_json(result))

    for field in (
        "accepts_source_lineage",
        "transitions_engineering_run",
        "grants_tool_capability",
        "grants_provider_authority",
        "performs_merge",
        "performs_production_deployment",
        "approves_release",
        "completes_review",
        "contains_source_bytes",
        "contains_patch",
        "contains_credentials",
        "contains_provider_payload",
        "contains_prompts",
        "contains_hidden_reasoning",
        "contains_arbitrary_commands",
        "contains_arbitrary_urls",
    ):
        assert payload[field] is False

    serialized = safe_parallax_bench_json(result).lower()
    for forbidden in ("authorization", "bearer ", "password", "chain-of-thought", "private key"):
        assert forbidden not in serialized


def test_fixture_catalog_is_diverse_bounded_and_reviewable() -> None:
    fixtures = parallax_bench_v1_fixtures()
    assert len(fixtures) == 9
    assert len({item.case_id for item in fixtures}) == len(fixtures)
    assert len({item.objective_class for item in fixtures}) >= 6
    assert len({item.repository_shape for item in fixtures}) >= 5
    assert sum(item.adversarial for item in fixtures) >= 4
    assert all(len(item.scenario) <= 240 for item in fixtures)
    assert len({item.digest for item in fixtures}) == len(fixtures)


def test_evaluator_does_not_special_case_fixture_or_case_id() -> None:
    baseline = _candidate()
    challenger = _candidate(challenger=True)
    arbitrary = evaluate_parallax_bench(
        case=_case(case_id="arbitrary-objective"),
        baseline=baseline,
        challenger=challenger,
    )
    fixture_named = evaluate_parallax_bench(
        case=_case(case_id="benchmark-gaming"),
        baseline=baseline,
        challenger=challenger,
    )

    assert arbitrary.disposition is fixture_named.disposition
    assert arbitrary.material_improvement == fixture_named.material_improvement
    assert [item.outcome for item in arbitrary.comparisons] == [
        item.outcome for item in fixture_named.comparisons
    ]
    assert arbitrary.fingerprint != fixture_named.fingerprint


def test_candidate_requires_every_dimension_exactly_once() -> None:
    evidence = _candidate()
    with pytest.raises(ParallaxBenchError, match="every benchmark dimension exactly once"):
        CandidateBenchmarkEvidence(
            binding=evidence.binding,
            protected_floor=evidence.protected_floor,
            dimensions=evidence.dimensions[:-1],
        )


def test_guardrail_regression_cannot_be_purchased_by_lower_cost_or_faster_time() -> None:
    unsafe_floor = _floor(safety=False)
    result = evaluate_parallax_bench(
        case=_case(),
        baseline=_candidate(),
        challenger=_candidate(challenger=True, floor=unsafe_floor),
    )

    assert result.disposition is ParallaxBenchDisposition.DETERMINISTIC_BLOCKED
    assert result.material_improvement is False
    assert _comparison(result, BenchmarkDimension.ELAPSED_TIME).outcome is ComparisonOutcome.IMPROVED
    assert _comparison(result, BenchmarkDimension.COST_USAGE).outcome is ComparisonOutcome.IMPROVED
