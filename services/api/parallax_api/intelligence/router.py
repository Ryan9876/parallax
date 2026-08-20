from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")

MODEL_ORDER = (
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-terra",
    "openai/gpt-5.6-sol",
)


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


class RoutingFailure(RuntimeError):
    def __init__(self, attempts: tuple[AttemptRecord, ...]):
        super().__init__("All configured Parallax models failed")
        self.attempts = attempts


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
                    continue
                records.append(AttemptRecord(model, "ok", duration))
                return RouteResult(value=value, model=model, attempts=tuple(records))
            except Exception as exc:  # provider boundary intentionally sanitized here
                duration = int((perf_counter() - started) * 1000)
                records.append(AttemptRecord(model, "provider_failed", duration, type(exc).__name__))
        raise RoutingFailure(tuple(records))
