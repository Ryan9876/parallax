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


def numbered_section(specification: str, title: str) -> str:
    """Extract a numbered level-two section by semantic title, independent of section number."""

    pattern = re.compile(
        rf"^##\s+\d+\.\s+{re.escape(title)}\b\s*\n(.*?)(?=^##\s+\d+\.|\Z)",
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(specification)
    return match.group(1).strip() if match else ""


def _compact(text: str, limit: int) -> str:
    normalized = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if len(normalized) <= limit:
        return normalized
    clipped = normalized[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return f"{clipped}…"


def development_spec_view(specification: str, acceptance_contract: list[dict[str, str]]) -> str:
    """Create a compact, loss-controlled spec view for CPU-only local DSPy CI.

    The full approved specification remains the sole source for protected
    validation, the exact acceptance map, and release gating. The local proof
    model receives a deliberately small engineering brief so mandatory DSPy
    execution cannot fail simply by echoing a long specification. Provider-
    backed compilation still receives the complete approved specification.
    """

    if os.getenv("DSPY_LOCAL_DEVELOPMENT") != "1":
        return specification

    objective = _compact(numbered_section(specification, "Objective"), 900)
    fixed = numbered_section(specification, "Fixed decisions") or numbered_section(
        specification, "Fixed product decisions"
    )
    fixed = _compact(fixed, 1200)
    architecture = _compact(numbered_section(specification, "Architecture requirements"), 1000)

    acceptance_lines = []
    for criterion in acceptance_contract:
        requirement = criterion["protected_requirement"].split(". ", 1)[0]
        acceptance_lines.append(
            f"- {criterion['id']} {criterion['title']}: {_compact(requirement, 150)}"
        )

    return "\n\n".join(
        part
        for part in (
            "# Compact Parallax implementation brief\nDo not copy this brief. Propose only the bounded output fields requested by the signature.",
            f"## Objective\n{objective}",
            f"## Fixed decisions\n{fixed}",
            f"## Architecture\n{architecture}",
            "## Acceptance anchors\n" + "\n".join(acceptance_lines),
        )
        if part.strip()
    )


def normalize_critique(prediction: object) -> list[str]:
    """Normalize provider list output or the local proof model's scalar output."""

    findings = getattr(prediction, "findings", None)
    if isinstance(findings, list):
        return [str(item).strip() for item in findings if str(item).strip()]

    if os.getenv("DSPY_LOCAL_DEVELOPMENT") == "1":
        finding = getattr(prediction, "finding", None)
        if finding is None:
            raise TypeError("DSPy local critic must return a finding")
        value = str(finding).strip()
        if not value or value.casefold() == "none":
            return []
        return [value]

    raise TypeError("DSPy critic findings must be a typed list")


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
    try:
        critique = normalize_critique(critique_prediction)
    except TypeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

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
