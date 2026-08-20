import json
from pathlib import Path
from types import SimpleNamespace

from parallax_api.intelligence.dspy_programs import plan_from_prediction
from parallax_api.intelligence.protected_metrics import (
    evaluate_compiled_plan,
    evaluate_reasoning_output,
    evaluate_spec_contract,
    extract_acceptance_contract,
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
    assert tuple(item["id"] for item in extract_acceptance_contract(spec)) == extract_acceptance_ids(spec)


def test_typed_dspy_plan_normalization_requires_all_nonempty_lists():
    prediction = SimpleNamespace(
        architecture_decisions=["AC-01: preserve API boundaries"],
        work_items=["AC-02: implement DSPy program boundary"],
        validations=["AC-03: persistence test"],
        risks=["AC-10: verify static fallback"],
    )
    plan = plan_from_prediction(prediction)
    assert plan["architecture_decisions"] == ["AC-01: preserve API boundaries"]
    assert set(plan) == {"architecture_decisions", "work_items", "validations", "risks"}


def test_compiled_plan_must_map_every_acceptance_criterion():
    spec = SPEC_PATH.read_text(encoding="utf-8")
    plan = {
        "spec_id": "P2-V0.1.0",
        "dspy_run": {"executed": True, "model": "test"},
        "protected_acceptance_map": [dict(item) for item in extract_acceptance_contract(spec)],
        "architecture_decisions": ["AC-01"],
        "work_items": [{"acceptance": ["AC-02"]}],
        "validations": ["AC-03"],
        "risks": ["AC-04"],
    }
    result = evaluate_compiled_plan(spec, plan)
    assert not result.passed
    assert "acceptance_not_mapped:AC-13" in result.failures


def test_compiled_plan_rejects_modified_protected_acceptance_map():
    spec = SPEC_PATH.read_text(encoding="utf-8")
    contract = [dict(item) for item in extract_acceptance_contract(spec)]
    contract[0]["protected_requirement"] = "weakened"
    all_ids = list(extract_acceptance_ids(spec))
    plan = {
        "spec_id": "P2-V0.1.0",
        "dspy_run": {"executed": True, "model": "test"},
        "protected_acceptance_map": contract,
        "architecture_decisions": all_ids,
        "work_items": ["implementation work"],
        "validations": ["validation work"],
        "risks": ["risk review"],
    }
    result = evaluate_compiled_plan(spec, plan)
    assert not result.passed
    assert "protected_acceptance_map_mismatch" in result.failures


def test_bootstrap_plan_is_structurally_evaluable_without_claiming_dspy_execution():
    spec = SPEC_PATH.read_text(encoding="utf-8")
    plan_path = SPEC_PATH.parent / "compiled" / "P2-V0.1.0.plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    result = evaluate_compiled_plan(spec, plan, require_metadata=False)
    assert result.passed, result.failures


def test_reasoning_metric_accepts_normal_answer():
    result = evaluate_reasoning_output("This answer is long enough to satisfy the protected minimum contract.")
    assert result.passed
