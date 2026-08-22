from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from parallax_api.evaluation.app_builder import (
    AppBuilderBenchmarkSuite,
    AppBuilderRecordedEvidence,
    REQUIRED_APP_BUILDER_CATEGORIES,
    evaluate_app_builder,
    load_app_builder_evidence,
    load_app_builder_suite,
)
from parallax_api.evaluation.security import SecurityViolation

ROOT = Path(__file__).resolve().parents[3]
BENCH = ROOT / "benchmarks" / "parallax-app-builder"
SCRIPT = ROOT / "scripts" / "validate_app_builder_benchmark.py"


def test_suites_are_versioned_separate_and_cover_required_categories():
    development = load_app_builder_suite(BENCH / "development-v0.1.json")
    promotion = load_app_builder_suite(BENCH / "promotion-v0.1.json")
    assert development.purpose == "development"
    assert promotion.purpose == "promotion"
    assert development.suite_id != promotion.suite_id
    assert {case.category for case in development.cases} == REQUIRED_APP_BUILDER_CATEGORIES
    assert {case.category for case in promotion.cases} == REQUIRED_APP_BUILDER_CATEGORIES
    assert set(development.category_minimums) == REQUIRED_APP_BUILDER_CATEGORIES
    assert set(promotion.category_minimums) == REQUIRED_APP_BUILDER_CATEGORIES


def test_suite_rejects_duplicate_cases_and_missing_category():
    payload = json.loads((BENCH / "development-v0.1.json").read_text(encoding="utf-8"))
    duplicate = json.loads(json.dumps(payload))
    duplicate["cases"].append(json.loads(json.dumps(duplicate["cases"][0])))
    with pytest.raises(ValidationError, match="duplicate case IDs"):
        AppBuilderBenchmarkSuite.model_validate(duplicate)

    missing = json.loads(json.dumps(payload))
    missing["cases"] = [case for case in missing["cases"] if case["category"] != "evidence_hygiene"]
    with pytest.raises(ValidationError):
        AppBuilderBenchmarkSuite.model_validate(missing)


def test_good_development_and_promotion_evidence_pass_deterministically():
    for purpose in ("development", "promotion"):
        suite = load_app_builder_suite(BENCH / f"{purpose}-v0.1.json")
        evidence = load_app_builder_evidence(BENCH / "fixtures" / f"{purpose}-good-v0.1.json")
        first = evaluate_app_builder(suite, evidence)
        second = evaluate_app_builder(suite, evidence)
        assert first.protected_pass
        assert first.aggregate_score == pytest.approx(1.0)
        assert first.report_id == second.report_id
        assert first.case_results == second.case_results
        assert first.category_results == second.category_results


def test_promotion_regression_is_rejected_for_multiple_critical_failures():
    suite = load_app_builder_suite(BENCH / "promotion-v0.1.json")
    evidence = load_app_builder_evidence(BENCH / "fixtures" / "promotion-regression-v0.1.json")
    report = evaluate_app_builder(suite, evidence)
    assert not report.protected_pass
    failed = {item.case_id: item for item in report.case_results if not item.passed}
    assert len(failed) >= 6
    assert failed["promo-project-isolation-01"].critical_failure
    assert "binding_mismatch:project_ref" in failed["promo-project-isolation-01"].failures
    assert failed["promo-spec-binding-01"].critical_failure
    assert "binding_mismatch:spec_digest" in failed["promo-spec-binding-01"].failures
    assert failed["promo-implementation-evidence-01"].critical_failure
    assert any(value.startswith("insufficient_evidence_digests") for value in failed["promo-implementation-evidence-01"].failures)
    assert failed["promo-tool-authority-01"].critical_failure


def test_evidence_must_match_suite_identity_purpose_and_exact_case_set():
    suite = load_app_builder_suite(BENCH / "development-v0.1.json")
    evidence_payload = json.loads((BENCH / "fixtures" / "development-good-v0.1.json").read_text(encoding="utf-8"))

    wrong_purpose = AppBuilderRecordedEvidence.model_validate({**evidence_payload, "suite_purpose": "promotion"})
    with pytest.raises(ValueError, match="suite purpose"):
        evaluate_app_builder(suite, wrong_purpose)

    missing = json.loads(json.dumps(evidence_payload))
    missing["cases"] = missing["cases"][:-1]
    with pytest.raises(ValueError, match="missing cases"):
        evaluate_app_builder(suite, AppBuilderRecordedEvidence.model_validate(missing))

    unknown = json.loads(json.dumps(evidence_payload))
    unknown["cases"][0]["case_id"] = "unknown-case"
    with pytest.raises(ValueError, match="unknown cases"):
        evaluate_app_builder(suite, AppBuilderRecordedEvidence.model_validate(unknown))


def test_hidden_reasoning_and_secret_payloads_fail_before_evaluation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    base = json.loads((BENCH / "fixtures" / "development-good-v0.1.json").read_text(encoding="utf-8"))

    hidden = json.loads(json.dumps(base))
    hidden["cases"][0]["scratchpad"] = "private reasoning"
    hidden_path = tmp_path / "hidden.json"
    hidden_path.write_text(json.dumps(hidden), encoding="utf-8")
    with pytest.raises(SecurityViolation, match="forbidden_reasoning_field:scratchpad"):
        load_app_builder_evidence(hidden_path)

    marker = "app-builder-test-secret-123456789"
    monkeypatch.setenv("APP_BUILDER_TEST_SECRET", marker)
    leaked = json.loads(json.dumps(base))
    leaked["cases"][0]["observations"].append(f"leaked={marker}")
    leaked_path = tmp_path / "leaked.json"
    leaked_path.write_text(json.dumps(leaked), encoding="utf-8")
    with pytest.raises(SecurityViolation, match="configured_secret_value_exposed"):
        load_app_builder_evidence(leaked_path)


def test_report_contains_digests_and_failure_codes_not_raw_observations():
    suite = load_app_builder_suite(BENCH / "promotion-v0.1.json")
    evidence = load_app_builder_evidence(BENCH / "fixtures" / "promotion-regression-v0.1.json")
    report = evaluate_app_builder(suite, evidence)
    serialized = report.model_dump_json()
    assert "input_evidence_digest" in serialized
    assert "evidence_digest" in serialized
    assert "binding_mismatch:project_ref" in serialized
    assert "cross_project.access=allowed" not in serialized
    assert '"no_chain_of_thought":true' in serialized


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "services" / "api")
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_has_zero_and_nonzero_protected_paths(tmp_path: Path):
    suite = BENCH / "promotion-v0.1.json"
    good = _run_cli(
        "--suite", str(suite),
        "--evidence", str(BENCH / "fixtures" / "promotion-good-v0.1.json"),
        "--report", str(tmp_path / "good-report.json"),
    )
    assert good.returncode == 0, good.stdout + good.stderr
    assert good.stdout.startswith("PASS:")
    assert (tmp_path / "good-report.json").exists()

    regression = _run_cli(
        "--suite", str(suite),
        "--evidence", str(BENCH / "fixtures" / "promotion-regression-v0.1.json"),
    )
    assert regression.returncode == 1, regression.stdout + regression.stderr
    assert regression.stdout.startswith("FAIL:")
    assert "promo-tool-authority-01" in regression.stdout


def test_cli_can_validate_suite_without_evidence():
    result = _run_cli("--suite", str(BENCH / "development-v0.1.json"))
    assert result.returncode == 0
    assert result.stdout.startswith("PASS:")
