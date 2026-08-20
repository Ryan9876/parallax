from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _protected_metrics():
    service = Path(__file__).resolve().parents[1] / "services" / "api"
    sys.path.insert(0, str(service))
    from parallax_api.intelligence.protected_metrics import (  # noqa: PLC0415
        evaluate_compiled_plan,
        evaluate_spec_contract,
    )

    return evaluate_spec_contract, evaluate_compiled_plan


def validate(path: Path, *, require_plan: bool = True, require_dspy: bool = False) -> list[str]:
    evaluate_spec_contract, evaluate_compiled_plan = _protected_metrics()
    text = path.read_text(encoding="utf-8")
    contract = evaluate_spec_contract(text)
    errors = [f"protected spec contract: {failure}" for failure in contract.failures]
    if errors or not require_plan:
        return errors

    plan_path = path.parent / "compiled" / f"{path.stem}.plan.json"
    if not plan_path.exists():
        errors.append(f"missing compiled plan: {plan_path}")
        return errors

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"compiled plan is invalid JSON: {exc}")
        return errors

    plan_result = evaluate_compiled_plan(text, plan, require_metadata=require_dspy)
    errors.extend(f"protected compiled plan: {failure}" for failure in plan_result.failures)
    return errors


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Validate a Parallax approved specification and optional compiled plan.")
    result.add_argument("spec", type=Path)
    result.add_argument(
        "--spec-only",
        action="store_true",
        help="validate only the approved specification contract before DSPy compilation",
    )
    result.add_argument(
        "--require-dspy",
        action="store_true",
        help="require compiled-plan metadata proving DSPy execution and the exact protected acceptance map",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    if args.spec_only and args.require_dspy:
        print("FAIL: --spec-only and --require-dspy cannot be combined")
        return 2

    errors = validate(
        args.spec,
        require_plan=not args.spec_only,
        require_dspy=args.require_dspy,
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    scope = "spec contract" if args.spec_only else "spec + compiled plan"
    if args.require_dspy:
        scope += " + DSPy evidence"
    print(f"PASS: {args.spec} satisfies the Parallax {scope} gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
