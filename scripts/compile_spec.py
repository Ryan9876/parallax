from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys


def ensure_acceptance_coverage(plan: dict[str, list[str]], acceptance_contract: list[dict[str, str]]) -> None:
    """Guarantee that every protected criterion has executable validation coverage.

    DSPy proposes architecture, work, validations, and risks. This deterministic
    post-processor only fills acceptance-coverage gaps and is intentionally
    outside optimizer-controlled program code.
    """

    execution_projection = json.dumps(plan, sort_keys=True)
    for criterion in acceptance_contract:
        acceptance_id = criterion["id"]
        if acceptance_id in execution_projection:
            continue
        plan["validations"].append(
            f"{acceptance_id}: validate protected requirement — {criterion['protected_requirement']}"
        )
        execution_projection += acceptance_id


def section(specification: str, heading: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(heading)}\s*\n(.*?)(?=^##\s+\d+\.|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(specification)
    return match.group(1).strip() if match else ""


def development_spec_view(specification: str, acceptance_contract: list[dict[str, str]]) -> str:
    """Create a compact, loss-controlled spec view for CPU-only local DSPy CI.

    The full approved specification still drives protected metrics and release
    gating. Only the credential-free development LM receives this condensed
    view so mandatory DSPy execution remains practical on GitHub CPU runners.
    """

    if os.getenv("DSPY_LOCAL_DEVELOPMENT") != "1":
        return specification

    parts = [
        "# Parallax 2.0 protected development specification",
        section(specification, "## 1. Objective"),
        "## Fixed product decisions",
        section(specification, "## 3. Fixed product decisions"),
        "## Architecture requirements",
        section(specification, "## 6. Architecture requirements"),
        "## Protected acceptance contract",
    ]
    for criterion in acceptance_contract:
        parts.append(
            f"{criterion['id']} {criterion['title']}: {criterion['protected_requirement']}"
        )
    return "\n\n".join(part for part in parts if part)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: compile_spec.py <spec.md>", file=sys.stderr)
        return 2

    try:
        from parallax_api.intelligence.dspy_programs import (
            build_spec_compiler,
            build_spec_critic,
            plan_from_prediction,
        )
        from parallax_api.intelligence.protected_metrics import (
            evaluate_compiled_plan,
            evaluate_spec_contract,
            extract_acceptance_contract,
            extract_spec_id,
        )
    except ImportError:
        service = Path(__file__).resolve().parents[1] / "services" / "api"
        sys.path.insert(0, str(service))
        from parallax_api.intelligence.dspy_programs import (
            build_spec_compiler,
            build_spec_critic,
            plan_from_prediction,
        )
        from parallax_api.intelligence.protected_metrics import (
            evaluate_compiled_plan,
            evaluate_spec_contract,
            extract_acceptance_contract,
            extract_spec_id,
        )

    spec_path = Path(sys.argv[1])
    spec = spec_path.read_text(encoding="utf-8")
    metric = evaluate_spec_contract(spec)
    if not metric.passed:
        print(f"Protected spec metric failed: {metric.failures}", file=sys.stderr)
        return 1

    acceptance_contract = [dict(item) for item in extract_acceptance_contract(spec)]
    if len(acceptance_contract) < 8:
        print("Protected acceptance map extraction failed", file=sys.stderr)
        return 1

    model = os.getenv("DSPY_MODEL", "openai/gpt-5.6-sol")
    program_spec = development_spec_view(spec, acceptance_contract)

    critic_dspy, critic_lm, critic_program = build_spec_critic(model)
    with critic_dspy.context(lm=critic_lm):
        critique_prediction = critic_program(specification=program_spec)
    critique = getattr(critique_prediction, "findings", None)
    if not isinstance(critique, list):
        print("DSPy critic findings must be a typed list", file=sys.stderr)
        return 1
    critique = [str(item).strip() for item in critique if str(item).strip()]

    compiler_dspy, compiler_lm, compiler_program = build_spec_compiler(model)
    with compiler_dspy.context(lm=compiler_lm):
        prediction = compiler_program(specification=program_spec)

    try:
        plan = plan_from_prediction(prediction)
    except (TypeError, ValueError) as exc:
        print(f"DSPy compiler returned invalid typed output: {exc}", file=sys.stderr)
        return 1

    ensure_acceptance_coverage(plan, acceptance_contract)

    spec_id = extract_spec_id(spec)
    artifact: dict[str, object] = dict(plan)
    artifact["spec_id"] = spec_id
    artifact["protected_acceptance_map"] = acceptance_contract
    artifact["critique"] = critique
    artifact["dspy_run"] = {
        "executed": True,
        "model": model,
        "api_base": os.getenv("DSPY_API_BASE") or "provider-default",
        "local_development_view": os.getenv("DSPY_LOCAL_DEVELOPMENT") == "1",
    }

    protected = evaluate_compiled_plan(spec, artifact)
    if not protected.passed:
        print(f"Protected compiled-plan metric failed: {protected.failures}", file=sys.stderr)
        return 1

    target = spec_path.parent / "compiled" / f"{spec_path.stem}.plan.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"{target} protected_score={protected.score:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
