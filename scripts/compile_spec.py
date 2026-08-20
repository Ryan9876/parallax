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
        from parallax_api.intelligence.dspy_programs import build_spec_compiler, build_spec_critic
        from parallax_api.intelligence.protected_metrics import evaluate_compiled_plan, evaluate_spec_contract, extract_spec_id
    except ImportError:
        service = Path(__file__).resolve().parents[1] / "services" / "api"
        sys.path.insert(0, str(service))
        from parallax_api.intelligence.dspy_programs import build_spec_compiler, build_spec_critic
        from parallax_api.intelligence.protected_metrics import evaluate_compiled_plan, evaluate_spec_contract, extract_spec_id

    spec_path = Path(sys.argv[1])
    spec = spec_path.read_text(encoding="utf-8")
    metric = evaluate_spec_contract(spec)
    if not metric.passed:
        print(f"Protected spec metric failed: {metric.failures}", file=sys.stderr)
        return 1

    model = os.getenv("DSPY_MODEL", "openai/gpt-5.6-sol")

    critic_dspy, critic_lm, critic_program = build_spec_critic(model)
    with critic_dspy.context(lm=critic_lm):
        critique_prediction = critic_program(specification=spec)
    try:
        critique = json.loads(str(critique_prediction.critique_json))
    except json.JSONDecodeError as exc:
        print(f"DSPy critic returned invalid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(critique, list):
        print("DSPy critic must return a JSON array", file=sys.stderr)
        return 1

    compiler_dspy, compiler_lm, compiler_program = build_spec_compiler(model)
    with compiler_dspy.context(lm=compiler_lm):
        prediction = compiler_program(specification=spec)

    raw = str(prediction.implementation_plan_json)
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"DSPy compiler returned invalid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(plan, dict):
        print("DSPy compiler must return a JSON object", file=sys.stderr)
        return 1

    spec_id = extract_spec_id(spec)
    plan["spec_id"] = spec_id
    plan["critique"] = critique
    plan["dspy_run"] = {"executed": True, "model": model}

    protected = evaluate_compiled_plan(spec, plan)
    if not protected.passed:
        print(f"Protected compiled-plan metric failed: {protected.failures}", file=sys.stderr)
        return 1

    target = spec_path.parent / "compiled" / f"{spec_path.stem}.plan.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"{target} protected_score={protected.score:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
