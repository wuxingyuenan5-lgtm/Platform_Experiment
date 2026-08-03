from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock


@dataclass(frozen=True)
class ResearchCacheEntry[T]:
    value: T
    fetched_at: datetime


class LastKnownGoodResearchCache[T]:
    """Small in-process cache that never replaces valid data with an empty pull.

    Redis or persistent snapshots may replace this implementation later without changing the
    acceptance rule: only meaningful payloads become the new last-known-good value.
    """

    def __init__(
        self,
        *,
        ttl: timedelta,
        is_meaningful: Callable[[T], bool],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if ttl <= timedelta(0):
            raise ValueError("ttl must be positive")
        self._ttl = ttl
        self._is_meaningful = is_meaningful
        self._now = now or (lambda: datetime.now(UTC))
        self._entries: dict[str, ResearchCacheEntry[T]] = {}
        self._lock = RLock()

    def store(self, key: str, value: T, *, fetched_at: datetime | None = None) -> bool:
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("cache key must not be empty")
        if not self._is_meaningful(value):
            return False
        timestamp = fetched_at or self._now()
        if timestamp.tzinfo is None:
            raise ValueError("fetched_at must include a timezone")
        with self._lock:
            self._entries[normalized_key] = ResearchCacheEntry(
                value=value,
                fetched_at=timestamp,
            )
        return True

    def get(self, key: str) -> ResearchCacheEntry[T] | None:
        with self._lock:
            return self._entries.get(key.strip())

    def get_fresh(self, key: str) -> ResearchCacheEntry[T] | None:
        entry = self.get(key)
        if entry is None:
            return None
        if self._now() - entry.fetched_at > self._ttl:
            return None
        return entry

    def is_stale(self, entry: ResearchCacheEntry[T]) -> bool:
        return self._now() - entry.fetched_at > self._ttl
