from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class PublicAuthRateLimiter:
    def __init__(self, *, max_keys: int) -> None:
        if max_keys < 1:
            raise ValueError("max_keys must be positive")
        self._max_keys = max_keys
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        if limit < 1 or window_seconds < 1:
            raise ValueError("Rate limit and window must be positive")
        current = monotonic() if now is None else now
        cutoff = current - window_seconds
        with self._lock:
            events = self._events.get(key)
            if events is None:
                self._prune_keys(cutoff)
                if len(self._events) >= self._max_keys:
                    # Fail closed for a new attacker-controlled key when the bounded
                    # process-local map is exhausted.
                    return RateLimitDecision(False, window_seconds)
                events = deque()
                self._events[key] = events
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(events[0] + window_seconds - current) + 1)
                return RateLimitDecision(False, retry_after)
            events.append(current)
            return RateLimitDecision(True, 0)

    def _prune_keys(self, cutoff: float) -> None:
        stale: list[str] = []
        for key, events in self._events.items():
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                stale.append(key)
        for key in stale:
            self._events.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


_limiter: PublicAuthRateLimiter | None = None
_limiter_max_keys: int | None = None
_limiter_lock = Lock()


def get_public_auth_rate_limiter(max_keys: int) -> PublicAuthRateLimiter:
    global _limiter, _limiter_max_keys
    with _limiter_lock:
        if _limiter is None or _limiter_max_keys != max_keys:
            _limiter = PublicAuthRateLimiter(max_keys=max_keys)
            _limiter_max_keys = max_keys
        return _limiter
