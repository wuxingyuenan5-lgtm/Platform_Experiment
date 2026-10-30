from app.research_clock import Mt5ObservedClock, live_mt5_clock


def test_live_only_clock_requires_advancing_samples_and_expires(monkeypatch):
    clock = Mt5ObservedClock()
    assert clock.observe(10860000, 60000, "owner", "XAUUSD.s") is None
    assert clock.observe(10861000, 61000, "owner", "XAUUSD.s") is None
    evidence = clock.observe(10862000, 62000, "owner", "XAUUSD.s")
    assert evidence["nativeUtcOffsetMs"] == 10800000
    assert evidence["scope"] == "live_observations_only"
    assert live_mt5_clock(evidence) == evidence
    monkeypatch.setattr(
        "app.research_clock.time.monotonic_ns",
        lambda: int(evidence["measuredMonotonicNs"]) + 31000000000,
    )
    assert live_mt5_clock(evidence) is None


def test_cached_ticks_and_fractional_shift_do_not_validate():
    clock = Mt5ObservedClock()
    for i in range(4):
        assert clock.observe(10860000, 60000 + i * 100, "owner", "XAUUSD.s") is None
    assert clock.observe(10860000 + 120000, 60000, "owner", "XAUUSD.s") is None


def test_minute_quote_quality_uses_calibrated_utc_age(monkeypatch):
    from app.research_clock import quote_time_quality

    monkeypatch.setattr("app.research_clock.time.monotonic_ns", lambda: 2000000000)
    evidence = {
        "localMonotonicNs": "1000000000",
        "localReceivedNs": "1000000000",
        "offsetUpperNs": "0",
        "driftAllowanceNs": "100000000",
        "maxAgeNs": "120000000000",
    }
    assert quote_time_quality(evidence, 1700) == []
    assert quote_time_quality(evidence, 0) == ["stale_quote"]
    assert quote_time_quality(evidence, 3000) == ["clock_unverified"]
    assert quote_time_quality(None, 1700) == ["clock_unverified"]
