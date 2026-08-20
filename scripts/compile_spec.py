from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from typing import Any


def parse_json_payload(raw: str, expected: type[list] | type[dict]) -> Any:
    """Accept plain JSON or a single fenced JSON payload, then validate type.

    Local development LMs sometimes wrap otherwise valid structured output in
    Markdown fences. We normalize only that presentation wrapper; protected
    metrics remain responsible for semantic acceptance of the resulting plan.
    """

    clean = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", clean, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        clean = fenced.group(1).strip()

    try:
        payload = json.loads(clean)
    except json.JSONDecodeError:
        opener, closer = ("[", "]") if expected is list else ("{", "}")
        start = clean.find(opener)
        end = clean.rfind(closer)
        if start < 0 or end < start:
            raise
        payload = json.loads(clean[start : end + 1])

    if not isinstance(payload, expected):
        raise TypeError(f"DSPy output must decode to {expected.__name__}")
    return payload


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
        critique = parse_json_payload(str(critique_prediction.critique_json), list)
    except (json.JSONDecodeError, TypeError) as exc:
        print(f"DSPy critic returned invalid JSON: {exc}", file=sys.stderr)
        return 1

    compiler_dspy, compiler_lm, compiler_program = build_spec_compiler(model)
    with compiler_dspy.context(lm=compiler_lm):
        prediction = compiler_program(specification=spec)

    try:
        plan = parse_json_payload(str(prediction.implementation_plan_json), dict)
    except (json.JSONDecodeError, TypeError) as exc:
        print(f"DSPy compiler returned invalid JSON: {exc}", file=sys.stderr)
        return 1

    spec_id = extract_spec_id(spec)
    plan["spec_id"] = spec_id
    plan["critique"] = critique
    plan["dspy_run"] = {
        "executed": True,
        "model": model,
        "api_base": os.getenv("DSPY_API_BASE") or "provider-default",
    }

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
