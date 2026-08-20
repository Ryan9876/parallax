from __future__ import annotations

from pathlib import Path
import json
import re
import sys

REQUIRED = (
    "## 1. Objective",
    "## 4. Scope for v0.1.0",
    "## 5. Non-goals for v0.1.0",
    "## 9. Security requirements",
    "## 11. Acceptance criteria",
    "## 12. Release gate",
)


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors = [f"missing heading: {heading}" for heading in REQUIRED if heading not in text]
    if "Status: APPROVED FOR IMPLEMENTATION" not in text:
        errors.append("spec is not approved for implementation")
    ids = re.findall(r"^### (AC-\d+)", text, flags=re.MULTILINE)
    if len(ids) < 10:
        errors.append("expected at least 10 explicit acceptance criteria")
    if len(ids) != len(set(ids)):
        errors.append("duplicate acceptance criterion IDs")

    spec_id_match = re.search(r"^Spec ID:\s*(\S+)", text, flags=re.MULTILINE)
    if not spec_id_match:
        errors.append("missing Spec ID")
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
    if plan.get("spec_id") != spec_id_match.group(1):
        errors.append("compiled plan does not reference the approved Spec ID")
    if not plan.get("work_items"):
        errors.append("compiled plan has no work items")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_spec.py <spec.md>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {path} satisfies the Parallax spec-first gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
