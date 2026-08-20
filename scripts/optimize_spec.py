from __future__ import annotations

import json
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
    from parallax_api.intelligence.protected_metrics import evaluate_compiled_plan, evaluate_spec_contract

    spec_path = Path(sys.argv[1])
    spec = spec_path.read_text(encoding="utf-8")
    protected = evaluate_spec_contract(spec)
    if not protected.passed:
        print(f"Protected spec metric failed: {protected.failures}", file=sys.stderr)
        return 1

    model = os.getenv("DSPY_MODEL", "openai/gpt-5.6-sol")
    dspy_module, lm, program = build_spec_compiler(model)

    examples = [dspy.Example(specification=spec).with_inputs("specification")]

    def metric(example, prediction, trace=None):
        del trace
        try:
            parsed = json.loads(str(prediction.implementation_plan_json))
        except Exception:
            return 0.0
        result = evaluate_compiled_plan(example.specification, parsed, require_metadata=False)
        return result.score if result.passed else 0.0

    optimizer = dspy.MIPROv2(metric=metric, auto="light")
    with dspy.context(lm=lm):
        optimized = optimizer.compile(program, trainset=examples)

    # Promotion evidence: the optimized program must still produce a plan that
    # satisfies the protected criteria before the artifact is accepted.
    with dspy.context(lm=lm):
        prediction = optimized(specification=spec)
    try:
        optimized_plan = json.loads(str(prediction.implementation_plan_json))
    except json.JSONDecodeError as exc:
        print(f"Optimized compiler returned invalid JSON: {exc}", file=sys.stderr)
        return 1

    promotion = evaluate_compiled_plan(spec, optimized_plan, require_metadata=False)
    if not promotion.passed:
        print(f"Optimized compiler failed protected promotion metric: {promotion.failures}", file=sys.stderr)
        return 1

    target = spec_path.parent / "compiled" / "optimized-program.json"
    optimized.save(str(target))
    evidence = spec_path.parent / "compiled" / "optimized-program-evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "spec_id": "P2-V0.1.0",
                "model": model,
                "protected_score": promotion.score,
                "protected_failures": list(promotion.failures),
                "sample_plan": optimized_plan,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"{target} protected_score={promotion.score:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
