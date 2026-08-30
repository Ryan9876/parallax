from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
from time import perf_counter
from typing import Awaitable, Callable, Generic, TypeVar

from .model_routes import HOSTED_MODEL_ORDER, effective_model_order, provider_kind_for_model

T = TypeVar("T")

# Compatibility constant. Server-owned local-first configuration changes only
# the effective default route resolved when ModelRouter is constructed without
# an explicit model tuple.
MODEL_ORDER = HOSTED_MODEL_ORDER

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttemptRecord:
    model: str
    status: str
    duration_ms: int
    error: str | None = None
    provider_kind: str | None = None


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


class ModelOutputValidationError(RuntimeError):
    """Typed boundary for provider-successful output that fails protected decoding.

    The exception intentionally carries no raw model output, validation payload,
    repository text, or arbitrary provider exception details. Programs may use
    it only after a provider result exists and server-owned structured-output
    validation fails.
    """


class RoutingFailure(RuntimeError):
    def __init__(self, attempts: tuple[AttemptRecord, ...]):
        super().__init__("All configured Parallax models failed")
        self.attempts = attempts
        self.kind = classify_routing_failure(attempts)


AttemptFn = Callable[[str], Awaitable[T]]
ValidatorFn = Callable[[T], bool]


class ModelRouter(Generic[T]):
    def __init__(self, models: tuple[str, ...] | None = None):
        self.models = effective_model_order() if models is None else models

    async def route(self, attempt: AttemptFn[T], validate: ValidatorFn[T]) -> RouteResult[T]:
        records: list[AttemptRecord] = []
        for model in self.models:
            provider_kind = provider_kind_for_model(model)
            started = perf_counter()
            try:
                value = await attempt(model)
                duration = int((perf_counter() - started) * 1000)
                if not validate(value):
                    records.append(
                        AttemptRecord(
                            model=model,
                            status="validation_failed",
                            duration_ms=duration,
                            provider_kind=provider_kind,
                        )
                    )
                    logger.warning(
                        "parallax_model_route validation_failed model=%s provider=%s duration_ms=%s",
                        model,
                        provider_kind,
                        duration,
                    )
                    continue
                records.append(
                    AttemptRecord(
                        model=model,
                        status="ok",
                        duration_ms=duration,
                        provider_kind=provider_kind,
                    )
                )
                return RouteResult(value=value, model=model, attempts=tuple(records))
            except ModelOutputValidationError:
                duration = int((perf_counter() - started) * 1000)
                records.append(
                    AttemptRecord(
                        model=model,
                        status="validation_failed",
                        duration_ms=duration,
                        provider_kind=provider_kind,
                    )
                )
                logger.warning(
                    "parallax_model_route output_validation_failed model=%s provider=%s duration_ms=%s",
                    model,
                    provider_kind,
                    duration,
                )
            except Exception as exc:  # provider boundary intentionally sanitized here
                duration = int((perf_counter() - started) * 1000)
                error_class = type(exc).__name__
                records.append(
                    AttemptRecord(
                        model=model,
                        status="provider_failed",
                        duration_ms=duration,
                        error=error_class,
                        provider_kind=provider_kind,
                    )
                )
                logger.warning(
                    "parallax_model_route provider_failed model=%s provider=%s error_class=%s duration_ms=%s",
                    model,
                    provider_kind,
                    error_class,
                    duration,
                )
        raise RoutingFailure(tuple(records))
