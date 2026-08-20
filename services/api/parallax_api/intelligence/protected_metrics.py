from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

REQUIRED_SPEC_HEADINGS = (
    "## 1. Objective",
    "## 4. Scope for v0.1.0",
    "## 5. Non-goals for v0.1.0",
    "## 9. Security requirements",
    "## 11. Acceptance criteria",
    "## 12. Release gate",
)

REQUIRED_PLAN_KEYS = (
    "architecture_decisions",
    "work_items",
    "validations",
    "risks",
)

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{16,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
)


@dataclass(frozen=True)
class MetricResult:
    passed: bool
    score: float
    failures: tuple[str, ...]


def _score(failures: list[str], checks: int) -> float:
    return max(0.0, 1.0 - (len(failures) / max(1, checks)))


def extract_spec_id(spec_text: str) -> str | None:
    match = re.search(r"^Spec ID:\s*([^\s]+)\s*$", spec_text, flags=re.MULTILINE)
    return match.group(1) if match else None


def extract_acceptance_ids(spec_text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"^###\s+(AC-\d+)\b", spec_text, flags=re.MULTILINE))


def extract_acceptance_contract(spec_text: str) -> tuple[dict[str, str], ...]:
    """Return the exact approved acceptance contract from the specification.

    This representation is deterministic and intentionally lives with the
    protected evaluator rather than in DSPy-controlled program code.
    """

    pattern = re.compile(
        r"^###\s+(AC-\d+)\s+([^\n]+)\n(.*?)(?=^###\s+AC-\d+\b|^##\s+12\.|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    contract: list[dict[str, str]] = []
    for acceptance_id, title, body in pattern.findall(spec_text):
        requirement = " ".join(line.strip() for line in body.strip().splitlines() if line.strip())
        contract.append(
            {
                "id": acceptance_id,
                "title": title.strip(),
                "protected_requirement": requirement,
            }
        )
    return tuple(contract)


def evaluate_spec_contract(spec_text: str) -> MetricResult:
    failures: list[str] = []
    for heading in REQUIRED_SPEC_HEADINGS:
        if heading not in spec_text:
            failures.append(f"missing_heading:{heading}")

    if "Status: APPROVED FOR IMPLEMENTATION" not in spec_text:
        failures.append("spec_not_approved")

    spec_id = extract_spec_id(spec_text)
    if not spec_id or not re.fullmatch(r"P2-V\d+\.\d+\.\d+", spec_id):
        failures.append("invalid_spec_id")

    acceptance_ids = extract_acceptance_ids(spec_text)
    acceptance_contract = extract_acceptance_contract(spec_text)
    if len(acceptance_ids) < 8:
        failures.append(f"insufficient_acceptance_criteria:{len(acceptance_ids)}")
    if len(set(acceptance_ids)) != len(acceptance_ids):
        failures.append("duplicate_acceptance_ids")
    if tuple(item["id"] for item in acceptance_contract) != acceptance_ids:
        failures.append("acceptance_contract_extraction_mismatch")

    checks = len(REQUIRED_SPEC_HEADINGS) + 5
    return MetricResult(passed=not failures, score=_score(failures, checks), failures=tuple(failures))


def evaluate_compiled_plan(
    spec_text: str,
    plan: dict[str, Any] | str,
    *,
    require_metadata: bool = True,
) -> MetricResult:
    failures = list(evaluate_spec_contract(spec_text).failures)

    if isinstance(plan, str):
        try:
            plan_object = json.loads(plan)
        except json.JSONDecodeError:
            failures.append("plan_invalid_json")
            return MetricResult(False, _score(failures, 28), tuple(failures))
    else:
        plan_object = plan

    if not isinstance(plan_object, dict):
        failures.append("plan_not_object")
        return MetricResult(False, _score(failures, 28), tuple(failures))

    for key in REQUIRED_PLAN_KEYS:
        value = plan_object.get(key)
        if not isinstance(value, list) or not value:
            failures.append(f"plan_missing_or_empty:{key}")

    spec_id = extract_spec_id(spec_text)
    if require_metadata:
        if plan_object.get("spec_id") != spec_id:
            failures.append("plan_spec_id_mismatch")
        dspy_run = plan_object.get("dspy_run")
        if not isinstance(dspy_run, dict) or dspy_run.get("executed") is not True:
            failures.append("dspy_execution_not_recorded")

        expected_contract = [dict(item) for item in extract_acceptance_contract(spec_text)]
        if plan_object.get("protected_acceptance_map") != expected_contract:
            failures.append("protected_acceptance_map_mismatch")

    # The protected acceptance map preserves the contract but does not count as
    # implementation coverage. Each criterion must also appear in the plan's
    # architecture/work/validation/risk content.
    executable_projection = {
        key: plan_object.get(key)
        for key in REQUIRED_PLAN_KEYS
    }
    executable_serialized = json.dumps(executable_projection, sort_keys=True)
    for acceptance_id in extract_acceptance_ids(spec_text):
        if acceptance_id not in executable_serialized:
            failures.append(f"acceptance_not_mapped:{acceptance_id}")

    serialized = json.dumps(plan_object, sort_keys=True)
    if any(pattern.search(serialized) for pattern in SECRET_PATTERNS):
        failures.append("possible_secret_in_artifact")

    return MetricResult(passed=not failures, score=_score(failures, 28), failures=tuple(failures))


def evaluate_reasoning_output(answer: str) -> MetricResult:
    failures: list[str] = []
    clean = answer.strip()
    if len(clean) < 24:
        failures.append("answer_too_short")
    if "```" in clean and len(clean) > 20_000:
        failures.append("excessive_unbounded_code")
    return MetricResult(passed=not failures, score=1.0 if not failures else 0.0, failures=tuple(failures))
