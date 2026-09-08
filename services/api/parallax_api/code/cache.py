from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from time import monotonic
from typing import Callable, Generic, Mapping, TypeVar


T = TypeVar("T")
_NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9_.:-]{0,63}$")


@dataclass(frozen=True, slots=True)
class DerivedCacheKey:
    """Deterministic identity for non-authoritative derived computation."""

    namespace: str
    digest: str

    @classmethod
    def build(cls, namespace: str, identity: Mapping[str, str | int | bool | None]) -> "DerivedCacheKey":
        if not isinstance(namespace, str) or not _NAMESPACE_RE.fullmatch(namespace):
            raise ValueError("cache namespace is invalid")
        if not isinstance(identity, Mapping) or not identity:
            raise ValueError("cache identity must be a non-empty mapping")
        canonical: dict[str, str | int | bool | None] = {}
        for key, value in identity.items():
            if not isinstance(key, str) or not key or len(key) > 80:
                raise ValueError("cache identity key is invalid")
            if value is not None and not isinstance(value, (str, int, bool)):
                raise TypeError("cache identity values must be scalar")
            if isinstance(value, str) and len(value) > 512:
                raise ValueError("cache identity value exceeds bound")
            canonical[key] = value
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return cls(namespace=namespace, digest=sha256(payload.encode("utf-8")).hexdigest())


@dataclass(slots=True)
class _Entry(Generic[T]):
    value: T
    expires_at: float


class BoundedDerivedCache(Generic[T]):
    """Small TTL/LRU cache for derived values only.

    This class deliberately has no persistence/session, Engineering Run, lease,
    source-lineage, credential or provider dependency. A hit can avoid repeated
    computation, but callers must perform every authorization and mutation check
    outside the cache exactly as they would on a miss.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float = 30.0,
        max_entries: int = 128,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("cache ttl must be positive")
        if not isinstance(max_entries, int) or isinstance(max_entries, bool) or max_entries <= 0:
            raise ValueError("cache max_entries must be a positive integer")
        self._ttl_seconds = float(ttl_seconds)
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[DerivedCacheKey, _Entry[T]] = OrderedDict()

    def get(self, key: DerivedCacheKey) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            self._entries.pop(key, None)
            return None
        self._entries.move_to_end(key)
        return entry.value

    def put(self, key: DerivedCacheKey, value: T) -> None:
        self._entries[key] = _Entry(value=value, expires_at=self._clock() + self._ttl_seconds)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def get_or_compute(self, key: DerivedCacheKey, compute: Callable[[], T]) -> tuple[T, bool]:
        cached = self.get(key)
        if cached is not None:
            return cached, True
        value = compute()
        self.put(key, value)
        return value, False

    def invalidate(self, key: DerivedCacheKey) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
