from __future__ import annotations

import os
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: optimize_spec.py <spec.md>", file=sys.stderr)
        return 2

    service = Path(__file__).resolve().parents[1] / "services" / "api"
    sys.path.insert(0, str(service))

    try:
        import dspy
    except ImportError:
        print("DSPy is not installed. Install services/api dependencies first.", file=sys.stderr)
        return 1

    from parallax_api.intelligence.dspy_programs import build_spec_compiler
    from parallax_api.intelligence.protected_metrics import evaluate_spec_contract

    spec = Path(sys.argv[1]).read_text(encoding="utf-8")
    protected = evaluate_spec_contract(spec)
    if not protected.passed:
        print(f"Protected spec metric failed: {protected.failures}", file=sys.stderr)
        return 1

    model = os.getenv("DSPY_MODEL", "openai/gpt-5.6-sol")
    dspy_module, lm, program = build_spec_compiler(model)

    examples = [
        dspy.Example(specification=spec).with_inputs("specification"),
    ]

    def metric(_example, prediction, trace=None):
        try:
            import json
            parsed = json.loads(str(prediction.implementation_plan_json))
        except Exception:
            return 0.0
        required = {"architecture_decisions", "work_items", "validations", "risks"}
        return len(required.intersection(parsed.keys())) / len(required)

    optimizer = dspy.MIPROv2(metric=metric, auto="light")
    with dspy.context(lm=lm):
        optimized = optimizer.compile(program, trainset=examples)

    target = Path(sys.argv[1]).parent / "compiled" / "optimized-program.json"
    optimized.save(str(target))
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
