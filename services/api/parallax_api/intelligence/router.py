from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
from time import perf_counter
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")

MODEL_ORDER = (
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-terra",
    "openai/gpt-5.6-sol",
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttemptRecord:
    model: str
    status: str
    duration_ms: int
    error: str | None = None


@dataclass(frozen=True)
class RouteResult(Generic[T]):
    value: T
    model: str
    attempts: tuple[AttemptRecord, ...]


class RoutingFailureKind(str, Enum):
    RATE_LIMITED = "RATE_LIMITED"
    VALIDATION_EXHAUSTED = "VALIDATION_EXHAUSTED"
    PROVIDER_EXHAUSTED = "PROVIDER_EXHAUSTED"


def classify_routing_failure(attempts: tuple[AttemptRecord, ...]) -> RoutingFailureKind:
    """Classify only from the already-sanitized bounded attempt record.

    Raw provider exceptions and payloads remain outside this contract. Mixed
    failures intentionally fall back to generic provider exhaustion rather than
    inferring account-wide capacity or protected-output semantics.
    """

    if attempts and all(
        item.status == "provider_failed" and item.error == "LMRateLimitError"
        for item in attempts
    ):
        return RoutingFailureKind.RATE_LIMITED
    if attempts and all(item.status == "validation_failed" for item in attempts):
        return RoutingFailureKind.VALIDATION_EXHAUSTED
    return RoutingFailureKind.PROVIDER_EXHAUSTED


class RoutingFailure(RuntimeError):
    def __init__(self, attempts: tuple[AttemptRecord, ...]):
        super().__init__("All configured Parallax models failed")
        self.attempts = attempts
        self.kind = classify_routing_failure(attempts)


AttemptFn = Callable[[str], Awaitable[T]]
ValidatorFn = Callable[[T], bool]


class ModelRouter(Generic[T]):
    def __init__(self, models: tuple[str, ...] = MODEL_ORDER):
        self.models = models

    async def route(self, attempt: AttemptFn[T], validate: ValidatorFn[T]) -> RouteResult[T]:
        records: list[AttemptRecord] = []
        for model in self.models:
            started = perf_counter()
            try:
                value = await attempt(model)
                duration = int((perf_counter() - started) * 1000)
                if not validate(value):
                    records.append(AttemptRecord(model, "validation_failed", duration))
                    logger.warning(
                        "parallax_model_route validation_failed model=%s duration_ms=%s",
                        model,
                        duration,
                    )
                    continue
                records.append(AttemptRecord(model, "ok", duration))
                return RouteResult(value=value, model=model, attempts=tuple(records))
            except Exception as exc:  # provider boundary intentionally sanitized here
                duration = int((perf_counter() - started) * 1000)
                error_class = type(exc).__name__
                records.append(AttemptRecord(model, "provider_failed", duration, error_class))
                logger.warning(
                    "parallax_model_route provider_failed model=%s error_class=%s duration_ms=%s",
                    model,
                    error_class,
                    duration,
                )
        raise RoutingFailure(tuple(records))
