from app import monitor_health


def test_monitor_reports_stall_failure_and_recovery(monkeypatch):
    monkeypatch.setattr(monitor_health, "_states", {})
    clock = [100.0]
    monkeypatch.setattr(monitor_health, "monotonic", lambda: clock[0])
    assert monitor_health.snapshot("x", enabled=False, deadline=10)["status"] == "disabled"
    monitor_health.begin("x")
    clock[0] = 111
    assert monitor_health.snapshot("x", enabled=True, deadline=10)["status"] == "stalled"
    monitor_health.finish("x", "quotes unavailable")
    result = monitor_health.snapshot("x", enabled=True, deadline=10)
    assert result["status"] == "degraded"
    assert "lastSuccessAt" not in result
    monitor_health.begin("x")
    monitor_health.finish("x")
    result = monitor_health.snapshot("x", enabled=True, deadline=10)
    assert result["status"] == "healthy"
    assert result["lastSuccessAt"]


def test_exit_monitor_records_failure_then_recovers(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from app import cross_spread_synthetic_service as service

    monkeypatch.setattr(monitor_health, "_states", {})
    monkeypatch.setattr(
        service,
        "get_settings",
        lambda: SimpleNamespace(cross_spread_exit_monitor_interval_seconds=1),
    )
    calls = []

    def evaluate():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("test failure")
        return SimpleNamespace(skipped_reason=None)

    monkeypatch.setattr(service, "evaluate_cross_spread_exit_plans", evaluate)

    async def sleep(_):
        status = monitor_health.snapshot("cross_exit", enabled=True, deadline=60)["status"]
        if len(calls) == 1:
            assert status == "degraded"
        else:
            assert status == "healthy"
            raise asyncio.CancelledError

    monkeypatch.setattr(service.asyncio, "sleep", sleep)

    async def run():
        try:
            await service.run_cross_spread_exit_monitor()
        except asyncio.CancelledError:
            pass

    asyncio.run(run())
    assert len(calls) == 2


def test_exit_monitor_treats_intentional_skip_as_healthy_cycle(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from app import cross_spread_synthetic_service as service

    monkeypatch.setattr(monitor_health, "_states", {})
    monkeypatch.setattr(
        service,
        "get_settings",
        lambda: SimpleNamespace(cross_spread_exit_monitor_interval_seconds=1),
    )
    monkeypatch.setattr(
        service,
        "evaluate_cross_spread_exit_plans",
        lambda: SimpleNamespace(skipped_reason="Live cross-spread execution is disabled"),
    )

    async def sleep(_):
        result = monitor_health.snapshot("cross_exit", enabled=True, deadline=60)
        assert result["status"] == "healthy"
        assert result["lastSuccessAt"]
        raise asyncio.CancelledError

    monkeypatch.setattr(service.asyncio, "sleep", sleep)

    async def run():
        try:
            await service.run_cross_spread_exit_monitor()
        except asyncio.CancelledError:
            pass

    asyncio.run(run())
