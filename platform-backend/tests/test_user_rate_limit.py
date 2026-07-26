from __future__ import annotations

import pytest

from app.user_rate_limit import PublicAuthRateLimiter


@pytest.mark.unit
def test_rate_limiter_blocks_until_window_expires() -> None:
    limiter = PublicAuthRateLimiter(max_keys=10)
    first = limiter.check("login:ip:user", limit=2, window_seconds=60, now=100.0)
    second = limiter.check("login:ip:user", limit=2, window_seconds=60, now=101.0)
    blocked = limiter.check("login:ip:user", limit=2, window_seconds=60, now=102.0)
    recovered = limiter.check("login:ip:user", limit=2, window_seconds=60, now=161.0)

    assert first.allowed
    assert second.allowed
    assert not blocked.allowed
    assert blocked.retry_after_seconds > 0
    assert recovered.allowed


@pytest.mark.unit
def test_rate_limiter_fails_closed_when_key_capacity_is_exhausted() -> None:
    limiter = PublicAuthRateLimiter(max_keys=1)
    assert limiter.check("first", limit=5, window_seconds=60, now=100.0).allowed

    exhausted = limiter.check("second", limit=5, window_seconds=60, now=101.0)
    assert not exhausted.allowed
    assert exhausted.retry_after_seconds == 60

    after_prune = limiter.check("second", limit=5, window_seconds=60, now=161.0)
    assert after_prune.allowed
