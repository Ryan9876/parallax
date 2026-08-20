from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from parallax_api.evaluation.loader import load_candidate, load_optimizer_suite, load_suite
from parallax_api.evaluation.promotion import compare_promotion_artifacts
from parallax_api.evaluation.runner import evaluate_recorded_candidate, write_evaluation_artifact
from parallax_api.evaluation.schema import BenchmarkSuite
from parallax_api.evaluation.security import SecurityViolation, assert_safe_payload


ROOT = Path(__file__).resolve().parents[3]
BENCH = ROOT / "benchmarks" / "parallax-engineering"


def test_initial_benchmark_has_all_required_categories_and_separate_purposes():
    development = load_suite(BENCH / "development-v0.1.json")
    promotion = load_suite(BENCH / "promotion-v0.1.json")
    expected = {
        "specification_fidelity",
        "conversation_continuity",
        "implementation_plan_completeness",
        "protected_boundary_preservation",
        "failure_degradation_handling",
        "evidence_status_honesty",
        "security_secret_handling",
        "concise_engineering_communication",
    }
    assert development.purpose == "development"
    assert promotion.purpose == "promotion"
    assert {case.category for case in development.cases} == expected
    assert {case.category for case in promotion.cases} == expected


def test_optimizer_loader_rejects_promotion_suite():
    assert load_optimizer_suite(BENCH / "development-v0.1.json").purpose == "development"
    with pytest.raises(ValueError, match="development suites only"):
        load_optimizer_suite(BENCH / "promotion-v0.1.json")


def test_schema_rejects_duplicate_cases_bad_weights_missing_contract_and_invalid_purpose():
    suite = json.loads((BENCH / "development-v0.1.json").read_text(encoding="utf-8"))

    duplicate = json.loads(json.dumps(suite))
    duplicate["cases"].append(json.loads(json.dumps(duplicate["cases"][0])))
    with pytest.raises(ValidationError, match="duplicate case IDs"):
        BenchmarkSuite.model_validate(duplicate)

    bad_weights = json.loads(json.dumps(suite))
    bad_weights["cases"][0]["weights"]["required_coverage"] = 0.9
    with pytest.raises(ValidationError, match="sum to 1.0"):
        BenchmarkSuite.model_validate(bad_weights)

    no_contract = json.loads(json.dumps(suite))
    case = no_contract["cases"][0]
    case["required_terms"] = []
    case["forbidden_terms"] = []
    case["protected_assertions"] = []
    case["weights"] = {"required_coverage": 0.0, "forbidden": 0.0, "assertions": 1.0}
    with pytest.raises(ValidationError, match="no executable protected contract"):
        BenchmarkSuite.model_validate(no_contract)

    invalid_purpose = json.loads(json.dumps(suite))
    invalid_purpose["purpose"] = "optimizer-owned"
    with pytest.raises(ValidationError, match="development"):
        BenchmarkSuite.model_validate(invalid_purpose)


def test_recorded_good_fixtures_pass_deterministic_evaluation():
    development = load_suite(BENCH / "development-v0.1.json")
    dev_candidate = load_candidate(BENCH / "fixtures" / "development-good.json")
    dev_artifact = evaluate_recorded_candidate(development, dev_candidate)
    assert dev_artifact.protected_pass
    assert dev_artifact.aggregate_score == pytest.approx(1.0)

    promotion = load_suite(BENCH / "promotion-v0.1.json")
    base_candidate = load_candidate(BENCH / "fixtures" / "promotion-baseline.json")
    base_artifact = evaluate_recorded_candidate(promotion, base_candidate)
    assert base_artifact.protected_pass
    assert base_artifact.aggregate_score == pytest.approx(1.0)


def test_evidence_uses_digests_not_raw_candidate_output(tmp_path: Path):
    suite = load_suite(BENCH / "development-v0.1.json")
    candidate = load_candidate(BENCH / "fixtures" / "development-good.json")
    artifact = evaluate_recorded_candidate(suite, candidate)
    target = write_evaluation_artifact(artifact, tmp_path)
    evidence = target.read_text(encoding="utf-8")
    assert candidate.outputs["dev-spec-01"] not in evidence
    assert "output_digest" in evidence
    assert '"no_chain_of_thought": true' in evidence


def test_promotion_allows_equivalent_challenger_and_rejects_protected_regression():
    suite = load_suite(BENCH / "promotion-v0.1.json")
    baseline = evaluate_recorded_candidate(
        suite,
        load_candidate(BENCH / "fixtures" / "promotion-baseline.json"),
    )
    equivalent = evaluate_recorded_candidate(
        suite,
        load_candidate(BENCH / "fixtures" / "promotion-equivalent.json"),
    )
    regression = evaluate_recorded_candidate(
        suite,
        load_candidate(BENCH / "fixtures" / "promotion-regression.json"),
    )

    accepted = compare_promotion_artifacts(baseline, equivalent)
    rejected = compare_promotion_artifacts(baseline, regression)

    assert accepted.passed, accepted.reasons
    assert not regression.protected_pass
    assert not rejected.passed
    assert any(reason.startswith("new_critical_failure:promo-boundary-01") for reason in rejected.reasons)


def test_promotion_gate_rejects_development_evidence():
    suite = load_suite(BENCH / "development-v0.1.json")
    candidate = load_candidate(BENCH / "fixtures" / "development-good.json")
    artifact = evaluate_recorded_candidate(suite, candidate)
    decision = compare_promotion_artifacts(artifact, artifact)
    assert not decision.passed
    assert "baseline_not_promotion_suite" in decision.reasons
    assert "challenger_not_promotion_suite" in decision.reasons


def test_security_scanner_rejects_configured_secret_value(monkeypatch: pytest.MonkeyPatch):
    marker = "unit-test-secret-value-123456"
    monkeypatch.setenv("PARALLAX_TEST_SECRET", marker)
    with pytest.raises(SecurityViolation, match="configured_secret_value_exposed"):
        assert_safe_payload({"candidate_output": f"accidentally leaked {marker}"})


def test_security_scanner_rejects_hidden_reasoning_fields():
    with pytest.raises(SecurityViolation, match="forbidden_reasoning_field:chain_of_thought"):
        assert_safe_payload({"chain_of_thought": "private scratch reasoning"})
    with pytest.raises(SecurityViolation, match="forbidden_reasoning_field:scratchpad"):
        assert_safe_payload({"nested": {"scratchpad": "do not persist"}})
