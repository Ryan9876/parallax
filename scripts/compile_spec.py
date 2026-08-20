from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: compile_spec.py <spec.md>", file=sys.stderr)
        return 2

    try:
        from parallax_api.intelligence.dspy_programs import build_spec_compiler
        from parallax_api.intelligence.protected_metrics import evaluate_spec_contract
    except ImportError:
        service = Path(__file__).resolve().parents[1] / "services" / "api"
        sys.path.insert(0, str(service))
        from parallax_api.intelligence.dspy_programs import build_spec_compiler
        from parallax_api.intelligence.protected_metrics import evaluate_spec_contract

    spec_path = Path(sys.argv[1])
    spec = spec_path.read_text(encoding="utf-8")
    metric = evaluate_spec_contract(spec)
    if not metric.passed:
        print(f"Protected spec metric failed: {metric.failures}", file=sys.stderr)
        return 1

    model = os.getenv("DSPY_MODEL", "openai/gpt-5.6-sol")
    dspy, lm, program = build_spec_compiler(model)
    with dspy.context(lm=lm):
        prediction = program(specification=spec)

    raw = str(prediction.implementation_plan_json)
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"DSPy compiler returned invalid JSON: {exc}", file=sys.stderr)
        return 1

    plan["spec_id"] = "P2-V0.1.0"
    plan["dspy_run"] = {"executed": True, "model": model}
    target = spec_path.parent / "compiled" / f"{spec_path.stem}.plan.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
