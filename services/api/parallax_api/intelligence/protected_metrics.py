from __future__ import annotations

import json
import re
from dataclasses import dataclass
from math import isfinite
from typing import Any

REQUIRED_SPEC_SECTIONS = (
    ("objective", re.compile(r"^##\s+\d+\.\s+Objective\b", flags=re.MULTILINE | re.IGNORECASE)),
    ("scope", re.compile(r"^##\s+\d+\.\s+Scope\b", flags=re.MULTILINE | re.IGNORECASE)),
    ("non_goals", re.compile(r"^##\s+\d+\.\s+Non-goals\b", flags=re.MULTILINE | re.IGNORECASE)),
    ("security", re.compile(r"^##\s+\d+\.\s+Security\b", flags=re.MULTILINE | re.IGNORECASE)),
    (
        "acceptance_criteria",
        re.compile(r"^##\s+\d+\.\s+Acceptance criteria\b", flags=re.MULTILINE | re.IGNORECASE),
    ),
    ("release_gate", re.compile(r"^##\s+\d+\.\s+Release gate\b", flags=re.MULTILINE | re.IGNORECASE)),
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

HIDDEN_REASONING_KEYS = {
    "chain_of_thought",
    "chain-of-thought",
    "scratchpad",
    "hidden_reasoning",
    "internal_reasoning",
    "rationale_trace",
}

# Observable prose may safely say that hidden chain-of-thought cannot be
# provided. Reject actual exposed private-reasoning payload markers instead of
# punishing the safe refusal language required by P2-V0.3.0.
HIDDEN_REASONING_TERMS = (
    "scratchpad:",
    "hidden reasoning:",
    "internal reasoning:",
    "private reasoning trace:",
)

SCOPE_DECISIONS = {"CONTINUE", "CLARIFY", "SPEC_AMENDMENT"}


@dataclass(frozen=True)
class MetricResult:
    passed: bool
    score: float
    failures: tuple[str, ...]


def _score(failures: list[str], checks: int) -> float:
    return max(0.0, 1.0 - (len(failures) / max(1, checks)))


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _has_secret(value: Any) -> bool:
    serialized = json.dumps(_plain(value), sort_keys=True, default=str)
    return any(pattern.search(serialized) for pattern in SECRET_PATTERNS)


def _hidden_reasoning_present(value: Any) -> bool:
    plain = _plain(value)
    if isinstance(plain, dict):
        lowered_keys = {str(key).strip().lower() for key in plain}
        if lowered_keys & HIDDEN_REASONING_KEYS:
            return True
        if any(_hidden_reasoning_present(item) for item in plain.values()):
            return True
    elif isinstance(plain, list):
        if any(_hidden_reasoning_present(item) for item in plain):
            return True
    elif isinstance(plain, str):
        lowered = plain.lower()
        if any(term in lowered for term in HIDDEN_REASONING_TERMS):
            return True
    return False


def extract_spec_id(spec_text: str) -> str | None:
    match = re.search(r"^Spec ID:\s*([^\s]+)\s*$", spec_text, flags=re.MULTILINE)
    return match.group(1) if match else None


def extract_acceptance_ids(spec_text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"^###\s+(AC-\d+)\b", spec_text, flags=re.MULTILINE))


def extract_acceptance_contract(spec_text: str) -> tuple[dict[str, str], ...]:
    """Return the exact approved acceptance contract from any P2 spec version.

    Acceptance criteria end at the next acceptance criterion, the next numbered
    level-two section, or EOF. The representation is deterministic and lives
    with the protected evaluator rather than in DSPy-controlled program code.
    """

    pattern = re.compile(
        r"^###\s+(AC-\d+)\s+([^\n]+)\n(.*?)(?=^###\s+AC-\d+\b|^##\s+\d+\.|\Z)",
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
    for section_name, section_pattern in REQUIRED_SPEC_SECTIONS:
        if not section_pattern.search(spec_text):
            failures.append(f"missing_section:{section_name}")

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

    checks = len(REQUIRED_SPEC_SECTIONS) + 5
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
    executable_projection = {key: plan_object.get(key) for key in REQUIRED_PLAN_KEYS}
    executable_serialized = json.dumps(executable_projection, sort_keys=True)
    for acceptance_id in extract_acceptance_ids(spec_text):
        if acceptance_id not in executable_serialized:
            failures.append(f"acceptance_not_mapped:{acceptance_id}")

    if _has_secret(plan_object):
        failures.append("possible_secret_in_artifact")

    return MetricResult(passed=not failures, score=_score(failures, 28), failures=tuple(failures))


def evaluate_scope_output(value: Any) -> MetricResult:
    failures: list[str] = []
    plain = _plain(value)
    if not isinstance(plain, dict):
        return MetricResult(False, 0.0, ("scope_not_object",))

    decision = plain.get("decision")
    if decision not in SCOPE_DECISIONS:
        failures.append("scope_invalid_decision")

    confidence = plain.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        failures.append("scope_invalid_confidence")
    elif not isfinite(float(confidence)) or not 0.0 <= float(confidence) <= 1.0:
        failures.append("scope_confidence_out_of_bounds")

    factors = plain.get("material_factors")
    if not isinstance(factors, list) or not 1 <= len(factors) <= 4:
        failures.append("scope_invalid_material_factors")
    else:
        for factor in factors:
            if not isinstance(factor, str) or not factor.strip() or len(factor.strip()) > 240:
                failures.append("scope_invalid_material_factor")
                break

    version = plain.get("program_version")
    if not isinstance(version, str) or not version.strip() or len(version) > 100:
        failures.append("scope_invalid_program_version")

    if _has_secret(plain):
        failures.append("scope_possible_secret_leak")
    if _hidden_reasoning_present(plain):
        failures.append("scope_hidden_reasoning_exposed")

    return MetricResult(passed=not failures, score=_score(failures, 6), failures=tuple(failures))


def evaluate_reason_result(value: Any, *, scope_decision: str) -> MetricResult:
    failures: list[str] = []
    plain = _plain(value)
    if not isinstance(plain, dict):
        return MetricResult(False, 0.0, ("reason_not_object",))

    if scope_decision not in {"CONTINUE", "CLARIFY"}:
        failures.append("reason_invalid_scope_path")

    answer = plain.get("answer")
    if not isinstance(answer, str) or len(answer.strip()) < 24:
        failures.append("reason_answer_too_short")
    elif len(answer) > 40_000:
        failures.append("reason_answer_too_long")

    confidence = plain.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        failures.append("reason_invalid_confidence")
    elif not isfinite(float(confidence)) or not 0.0 <= float(confidence) <= 1.0:
        failures.append("reason_confidence_out_of_bounds")

    for key in ("material_uncertainties", "assumptions"):
        items = plain.get(key)
        if not isinstance(items, list) or len(items) > 4:
            failures.append(f"reason_invalid_{key}")
            continue
        for item in items:
            if not isinstance(item, str) or not item.strip() or len(item.strip()) > 300:
                failures.append(f"reason_invalid_{key}_item")
                break

    version = plain.get("program_version")
    if not isinstance(version, str) or not version.strip() or len(version) > 100:
        failures.append("reason_invalid_program_version")

    if scope_decision == "CLARIFY" and isinstance(answer, str):
        if answer.count("?") != 1 or len(answer.strip()) > 1_000:
            failures.append("reason_clarification_not_focused")

    if _has_secret(plain):
        failures.append("reason_possible_secret_leak")
    if _hidden_reasoning_present(plain):
        failures.append("reason_hidden_reasoning_exposed")

    return MetricResult(passed=not failures, score=_score(failures, 8), failures=tuple(failures))


def evaluate_reasoning_output(answer: str) -> MetricResult:
    """Legacy foundation check retained for inherited regression compatibility."""

    failures: list[str] = []
    clean = answer.strip()
    if len(clean) < 24:
        failures.append("answer_too_short")
    if "```" in clean and len(clean) > 20_000:
        failures.append("excessive_unbounded_code")
    return MetricResult(passed=not failures, score=1.0 if not failures else 0.0, failures=tuple(failures))
