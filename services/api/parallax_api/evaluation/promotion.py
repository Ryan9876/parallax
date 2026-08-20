from __future__ import annotations

from pathlib import Path

from .schema import EvaluationArtifact, PromotionDecision
from .security import assert_safe_payload

PROMOTION_POLICY_VERSION = "P2-PROMOTION-V1"
MAX_AGGREGATE_REGRESSION = 0.01
MAX_CATEGORY_REGRESSION = 0.02


def compare_promotion_artifacts(
    baseline: EvaluationArtifact,
    challenger: EvaluationArtifact,
) -> PromotionDecision:
    reasons: list[str] = []

    if baseline.suite_purpose != "promotion":
        reasons.append("baseline_not_promotion_suite")
    if challenger.suite_purpose != "promotion":
        reasons.append("challenger_not_promotion_suite")
    if (baseline.suite_id, baseline.suite_version) != (challenger.suite_id, challenger.suite_version):
        reasons.append("suite_version_mismatch")
    if baseline.evaluator_version != challenger.evaluator_version:
        reasons.append("evaluator_version_mismatch")
    if not baseline.protected_pass:
        reasons.append("baseline_failed_protected_evaluation")
    if not challenger.protected_pass:
        reasons.append("challenger_failed_protected_evaluation")

    baseline_cases = {result.case_id: result for result in baseline.case_results}
    challenger_cases = {result.case_id: result for result in challenger.case_results}
    if set(baseline_cases) != set(challenger_cases):
        reasons.append("case_set_mismatch")
    else:
        for case_id, challenger_case in challenger_cases.items():
            baseline_case = baseline_cases[case_id]
            if challenger_case.critical_failure and not baseline_case.critical_failure:
                reasons.append(f"new_critical_failure:{case_id}")

    aggregate_delta = challenger.aggregate_score - baseline.aggregate_score
    if aggregate_delta < -MAX_AGGREGATE_REGRESSION:
        reasons.append(
            f"aggregate_regression:{aggregate_delta:.4f}<-{MAX_AGGREGATE_REGRESSION:.4f}"
        )

    baseline_categories = {item.category: item for item in baseline.category_results}
    challenger_categories = {item.category: item for item in challenger.category_results}
    category_deltas: dict[str, float] = {}
    if set(baseline_categories) != set(challenger_categories):
        reasons.append("category_set_mismatch")
    else:
        for category in sorted(baseline_categories):
            baseline_category = baseline_categories[category]
            challenger_category = challenger_categories[category]
            delta = challenger_category.score - baseline_category.score
            category_deltas[category] = delta
            if not challenger_category.passed:
                reasons.append(f"challenger_category_floor_failed:{category}")
            if delta < -MAX_CATEGORY_REGRESSION:
                reasons.append(
                    f"category_regression:{category}:{delta:.4f}<-{MAX_CATEGORY_REGRESSION:.4f}"
                )

    decision = PromotionDecision(
        policy_version=PROMOTION_POLICY_VERSION,
        baseline_run_id=baseline.run_id,
        challenger_run_id=challenger.run_id,
        passed=not reasons,
        reasons=reasons,
        aggregate_delta=aggregate_delta,
        category_deltas=category_deltas,
    )
    assert_safe_payload(decision)
    return decision


def write_promotion_decision(decision: PromotionDecision, evidence_dir: str | Path) -> Path:
    assert_safe_payload(decision)
    root = Path(evidence_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = (root / f"promotion-{decision.challenger_run_id}.json").resolve()
    if target.parent != root:
        raise ValueError("promotion evidence path escaped configured evidence directory")
    target.write_text(decision.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target
