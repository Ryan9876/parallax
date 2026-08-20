from __future__ import annotations

from dataclasses import dataclass

REQUIRED_SPEC_HEADINGS = (
    "## 1. Objective",
    "## 4. Scope for v0.1.0",
    "## 5. Non-goals for v0.1.0",
    "## 9. Security requirements",
    "## 11. Acceptance criteria",
    "## 12. Release gate",
)


@dataclass(frozen=True)
class MetricResult:
    passed: bool
    score: float
    failures: tuple[str, ...]


def evaluate_spec_contract(spec_text: str) -> MetricResult:
    failures = tuple(heading for heading in REQUIRED_SPEC_HEADINGS if heading not in spec_text)
    score = (len(REQUIRED_SPEC_HEADINGS) - len(failures)) / len(REQUIRED_SPEC_HEADINGS)
    return MetricResult(passed=not failures, score=score, failures=failures)


def evaluate_reasoning_output(answer: str) -> MetricResult:
    failures: list[str] = []
    clean = answer.strip()
    if len(clean) < 24:
        failures.append("answer_too_short")
    if "```" in clean and len(clean) > 20_000:
        failures.append("excessive_unbounded_code")
    return MetricResult(passed=not failures, score=1.0 if not failures else 0.0, failures=tuple(failures))
