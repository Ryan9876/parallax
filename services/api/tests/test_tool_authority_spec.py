from __future__ import annotations

import json
from pathlib import Path

from parallax_api.intelligence.protected_metrics import (
    evaluate_compiled_plan,
    evaluate_spec_contract,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = REPOSITORY_ROOT / "specs" / "P2-V0.14.3.md"
PLAN_PATH = REPOSITORY_ROOT / "specs" / "compiled" / "P2-V0.14.3.plan.json"


def test_tool_authority_spec_and_compiled_plan_pass_protected_contract():
    spec_text = SPEC_PATH.read_text(encoding="utf-8")
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

    spec_result = evaluate_spec_contract(spec_text)
    assert spec_result.passed, spec_result.failures

    plan_result = evaluate_compiled_plan(spec_text, plan, require_metadata=False)
    assert plan_result.passed, plan_result.failures
