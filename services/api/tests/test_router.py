import asyncio

import pytest

from parallax_api.intelligence.router import (
    MODEL_ORDER,
    AttemptRecord,
    ModelRouter,
    RoutingFailure,
    RoutingFailureKind,
    classify_routing_failure,
)


def test_router_falls_back_luna_terra_sol():
    seen = []

    async def attempt(model: str):
        seen.append(model)
        if model != MODEL_ORDER[-1]:
            raise RuntimeError("provider down")
        return "valid result"

    result = asyncio.run(ModelRouter[str]().route(attempt, lambda value: value.startswith("valid")))
    assert seen == list(MODEL_ORDER)
    assert result.model == "openai/gpt-5.6-sol"
    assert [record.status for record in result.attempts] == ["provider_failed", "provider_failed", "ok"]


def test_all_rate_limit_failures_are_classified_without_raw_provider_content():
    attempts = tuple(
        AttemptRecord(model, "provider_failed", 10, "LMRateLimitError")
        for model in MODEL_ORDER
    )
    assert classify_routing_failure(attempts) is RoutingFailureKind.RATE_LIMITED


def test_validation_exhaustion_is_distinct_from_provider_capacity():
    attempts = tuple(AttemptRecord(model, "validation_failed", 10) for model in MODEL_ORDER)
    assert classify_routing_failure(attempts) is RoutingFailureKind.VALIDATION_EXHAUSTED


def test_mixed_routing_failures_fail_closed_as_generic_provider_exhaustion():
    attempts = (
        AttemptRecord(MODEL_ORDER[0], "provider_failed", 10, "LMRateLimitError"),
        AttemptRecord(MODEL_ORDER[1], "validation_failed", 10),
        AttemptRecord(MODEL_ORDER[2], "provider_failed", 10, "RuntimeError"),
    )
    assert classify_routing_failure(attempts) is RoutingFailureKind.PROVIDER_EXHAUSTED


def test_router_failure_preserves_only_sanitized_failure_classification():
    class LMRateLimitError(RuntimeError):
        pass

    async def attempt(_model: str):
        raise LMRateLimitError("raw provider quota response must not cross the router boundary")

    with pytest.raises(RoutingFailure) as failed:
        asyncio.run(ModelRouter[str]().route(attempt, lambda _value: True))

    assert failed.value.kind is RoutingFailureKind.RATE_LIMITED
    assert [item.error for item in failed.value.attempts] == ["LMRateLimitError"] * len(MODEL_ORDER)
    assert "quota" not in str(failed.value).lower()
