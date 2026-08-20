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

    from parallax_api.intelligence.dspy_programs import build_spec_compiler, plan_from_prediction
    from parallax_api.intelligence.protected_metrics import (
        evaluate_compiled_plan,
        evaluate_spec_contract,
        extract_acceptance_contract,
        extract_acceptance_ids,
    )

    spec_path = Path(sys.argv[1])
    spec = spec_path.read_text(encoding="utf-8")
    protected = evaluate_spec_contract(spec)
    if not protected.passed:
        print(f"Protected spec metric failed: {protected.failures}", file=sys.stderr)
        return 1

    model = os.getenv("DSPY_MODEL", "openai/gpt-5.6-sol")
    _dspy_module, lm, program = build_spec_compiler(model)
    examples = [dspy.Example(specification=spec).with_inputs("specification")]

    def normalize_plan(specification: str, prediction) -> tuple[dict[str, list[str]], float]:
        plan = plan_from_prediction(prediction)
        acceptance_ids = extract_acceptance_ids(specification)
        proposal = json.dumps(plan, sort_keys=True)
        proposed_coverage = sum(1 for acceptance_id in acceptance_ids if acceptance_id in proposal)
        coverage_ratio = proposed_coverage / max(1, len(acceptance_ids))

        for criterion in extract_acceptance_contract(specification):
            acceptance_id = criterion["id"]
            if acceptance_id in proposal:
                continue
            plan["validations"].append(
                f"{acceptance_id}: validate protected requirement — {criterion['protected_requirement']}"
            )
            proposal += acceptance_id
        return plan, coverage_ratio

    def metric(example, prediction, trace=None):
        del trace
        try:
            parsed, coverage_ratio = normalize_plan(example.specification, prediction)
        except (TypeError, ValueError):
            return 0.0
        result = evaluate_compiled_plan(example.specification, parsed, require_metadata=False)
        if not result.passed:
            return 0.0
        # Protected validity is mandatory; among valid plans, reward the DSPy
        # proposal for natively mapping more of the acceptance contract itself.
        return 0.75 * result.score + 0.25 * coverage_ratio

    optimizer = dspy.MIPROv2(metric=metric, auto="light")
    with dspy.context(lm=lm):
        optimized = optimizer.compile(program, trainset=examples)

    with dspy.context(lm=lm):
        prediction = optimized(specification=spec)
    try:
        optimized_plan, proposal_coverage = normalize_plan(spec, prediction)
    except (TypeError, ValueError) as exc:
        print(f"Optimized compiler returned invalid typed output: {exc}", file=sys.stderr)
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
                "proposal_acceptance_coverage": proposal_coverage,
                "protected_failures": list(promotion.failures),
                "sample_plan": optimized_plan,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"{target} protected_score={promotion.score:.3f} proposal_coverage={proposal_coverage:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
