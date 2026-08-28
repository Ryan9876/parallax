from __future__ import annotations

from collections.abc import Iterable

from parallax_api.evaluation.parallax_bench import BenchmarkCase, ParallaxBenchError


def validate_case_catalog(cases: Iterable[BenchmarkCase]) -> tuple[BenchmarkCase, ...]:
    """Validate immutable `(case_id, case_version)` identity across one admitted catalog."""

    materialized = tuple(cases)
    if not materialized:
        raise ParallaxBenchError("benchmark case catalog must be non-empty")
    if any(not isinstance(case, BenchmarkCase) for case in materialized):
        raise ParallaxBenchError("benchmark case catalog contains non-canonical case")

    seen: dict[tuple[str, str], str] = {}
    for case in materialized:
        identity = (case.case_id, case.case_version)
        existing = seen.get(identity)
        if existing is not None:
            if existing != case.digest:
                raise ParallaxBenchError("benchmark case identity conflicts with different content")
            raise ParallaxBenchError("benchmark case identity must be unique")
        seen[identity] = case.digest

    return tuple(sorted(materialized, key=lambda case: (case.case_id, case.case_version)))
