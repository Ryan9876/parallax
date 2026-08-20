from __future__ import annotations

from hashlib import sha256

from .schema import BenchmarkCase, CaseEvaluation

EVALUATOR_VERSION = "p2-deterministic-v1"


def text_digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _contains(haystack: str, needle: str) -> bool:
    return needle.casefold() in haystack.casefold()


def evaluate_case(case: BenchmarkCase, output: str) -> CaseEvaluation:
    failures: list[str] = []

    required_found = [term for term in case.required_terms if _contains(output, term)]
    required_score = len(required_found) / len(case.required_terms) if case.required_terms else 1.0
    for term in case.required_terms:
        if term not in required_found:
            failures.append(f"missing_required:{term}")

    forbidden_found = [term for term in case.forbidden_terms if _contains(output, term)]
    forbidden_score = (
        1.0 - (len(forbidden_found) / len(case.forbidden_terms))
        if case.forbidden_terms
        else 1.0
    )
    for term in forbidden_found:
        failures.append(f"forbidden_present:{term}")

    assertion_passes = 0
    critical_failure = False
    stripped = output.strip()
    for assertion in case.protected_assertions:
        if assertion.kind == "contains":
            passed = _contains(output, assertion.value)
        elif assertion.kind == "not_contains":
            passed = not _contains(output, assertion.value)
        else:
            passed = stripped == assertion.value.strip()
        if passed:
            assertion_passes += 1
        else:
            failures.append(f"assertion_failed:{assertion.assertion_id}:{assertion.kind}")
            critical_failure = critical_failure or assertion.critical

    assertion_score = (
        assertion_passes / len(case.protected_assertions)
        if case.protected_assertions
        else 1.0
    )

    score = (
        required_score * case.weights.required_coverage
        + forbidden_score * case.weights.forbidden
        + assertion_score * case.weights.assertions
    )

    if case.max_output_chars is not None and len(output) > case.max_output_chars:
        failures.append(f"output_too_long:{len(output)}>{case.max_output_chars}")
        score = 0.0

    score = max(0.0, min(1.0, score))
    if score < case.minimum_score:
        failures.append(f"below_case_threshold:{score:.4f}<{case.minimum_score:.4f}")

    passed = not critical_failure and score >= case.minimum_score
    return CaseEvaluation(
        case_id=case.case_id,
        category=case.category,
        score=score,
        passed=passed,
        critical_failure=critical_failure,
        failures=failures,
        required_coverage=required_score,
        forbidden_score=forbidden_score,
        assertion_score=assertion_score,
        output_digest=text_digest(output),
    )
