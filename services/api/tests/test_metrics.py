import json
from pathlib import Path

from parallax_api.intelligence.protected_metrics import (
    evaluate_compiled_plan,
    evaluate_reasoning_output,
    evaluate_spec_contract,
    extract_acceptance_ids,
)


SPEC_PATH = Path(__file__).resolve().parents[3] / "specs" / "P2-V0.1.0.md"


def test_protected_spec_metric_rejects_missing_contract():
    result = evaluate_spec_contract("# incomplete")
    assert not result.passed
    assert result.score < 1


def test_approved_spec_has_all_expected_acceptance_ids():
    spec = SPEC_PATH.read_text(encoding="utf-8")
    result = evaluate_spec_contract(spec)
    assert result.passed, result.failures
    assert extract_acceptance_ids(spec) == tuple(f"AC-{index:02d}" for index in range(1, 14))


def test_compiled_plan_must_map_every_acceptance_criterion():
    spec = SPEC_PATH.read_text(encoding="utf-8")
    plan = {
        "spec_id": "P2-V0.1.0",
        "dspy_run": {"executed": True, "model": "test"},
        "architecture_decisions": ["AC-01"],
        "work_items": [{"acceptance": ["AC-02"]}],
        "validations": ["AC-03"],
        "risks": ["AC-04"],
    }
    result = evaluate_compiled_plan(spec, plan)
    assert not result.passed
    assert "acceptance_not_mapped:AC-13" in result.failures


def test_bootstrap_plan_is_structurally_evaluable_without_claiming_dspy_execution():
    spec = SPEC_PATH.read_text(encoding="utf-8")
    plan_path = SPEC_PATH.parent / "compiled" / "P2-V0.1.0.plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    result = evaluate_compiled_plan(spec, plan, require_metadata=False)
    assert result.passed, result.failures


def test_reasoning_metric_accepts_normal_answer():
    result = evaluate_reasoning_output("This answer is long enough to satisfy the protected minimum contract.")
    assert result.passed
