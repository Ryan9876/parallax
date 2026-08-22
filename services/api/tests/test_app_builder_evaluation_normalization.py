from __future__ import annotations

from pathlib import Path

from parallax_api.evaluation.app_builder import (
    evaluate_app_builder,
    load_app_builder_evidence,
    load_app_builder_suite,
)


ROOT = Path(__file__).resolve().parents[3]
BENCH = ROOT / "benchmarks" / "parallax-app-builder"


def test_observation_matching_is_case_and_whitespace_normalized():
    suite = load_app_builder_suite(BENCH / "promotion-v0.1.json")
    evidence = load_app_builder_evidence(BENCH / "fixtures" / "promotion-good-v0.1.json")
    target = next(item for item in evidence.cases if item.case_id == "promo-tool-authority-01")
    normalized = target.model_copy(
        update={
            "observations": [
                " TOOL.DECISION=DENY ",
                " tool.reason=project_scope_denied\t",
                "TOOL.SELF_GRANTED=FALSE",
                " TOOL.DECISION=ALLOW ",
            ]
        }
    )
    changed = evidence.model_copy(
        update={"cases": [normalized if item.case_id == normalized.case_id else item for item in evidence.cases]}
    )
    report = evaluate_app_builder(suite, changed)
    result = next(item for item in report.case_results if item.case_id == "promo-tool-authority-01")
    assert not result.passed
    assert "forbidden_present:allowed" in result.failures
