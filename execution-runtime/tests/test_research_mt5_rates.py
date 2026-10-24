from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import research_mt5_rates as module
from app.gateway_errors import GatewayConfigurationError
from app.research_market_capture import create_research_market_router

pytestmark = pytest.mark.unit


def test_native_closed_bars_use_fixed_worker_and_exclude_forming_bar(monkeypatch):
    calls = []
    rates = np.array(
        [(1792108800, 4200.1, 4250.2, 4190.0, 4240.12)],
        dtype=[("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8")],
    )
    mt5 = SimpleNamespace(
        account_info=lambda: SimpleNamespace(login=1, server="fixture", company="fixture"),
        terminal_info=lambda: SimpleNamespace(connected=True),
        TIMEFRAME_D1=1440,
        copy_rates_from_pos=lambda *args: calls.append(args) or rates,
    )
    checked = []
    adapter = SimpleNamespace(
        settings=SimpleNamespace(live_write_enabled=False),
        _assert_account=checked.append,
        _connect=lambda: mt5,
    )
    monkeypatch.setattr(
        module, "resolve_mt5_symbol", lambda **_: SimpleNamespace(symbol="XAUUSD.s")
    )
    monkeypatch.setattr(module, "with_mt5_read_session", lambda **kw: kw["callback"](None))
    result = module.read_daily_rates(adapter, account_id="fixed", count=1500)
    assert checked == ["fixed"]
    assert calls == [("XAUUSD.s", 1440, 1, 1500)]
    assert result["closedOnly"] is True and result["rows"][0]["close"] == "4240.12"
    assert result["symbol"] == "XAUUSD.s" and result["server"] == "fixture"
    for count in (0, 2001):
        with pytest.raises(GatewayConfigurationError):
            module.read_daily_rates(adapter, account_id="fixed", count=count)
    adapter.settings.live_write_enabled = True
    with pytest.raises(GatewayConfigurationError):
        module.read_daily_rates(adapter, account_id="fixed")
    assert len(calls) == 1


def test_daily_route_bounds_fixed_account_and_live_write_gate():
    calls = []
    capture = SimpleNamespace(
        settings=SimpleNamespace(
            mt5_primary_account_id="fixed", mt5_accounts={"fixed": {}}, live_write_enabled=False
        ),
        gateway=SimpleNamespace(
            get_research_daily_rates=lambda **kw: calls.append(kw) or {"rows": []}
        ),
    )
    app = FastAPI()
    app.include_router(create_research_market_router(capture))
    with TestClient(app) as client:
        assert client.get("/v1/market-data/xauusd-daily?count=10").status_code == 200
        assert calls == [{"account_id": "fixed", "count": 10}]
        assert client.get("/v1/market-data/xauusd-daily?count=2001").status_code == 422
        capture.settings.live_write_enabled = True
        assert client.get("/v1/market-data/xauusd-daily").status_code == 503
        assert len(calls) == 1


def test_worker_daily_research_yields_before_starting_for_busy_or_live_account():
    from app.config import Settings
    from app.mt5_account_worker import Mt5AccountWorkerClient

    client = Mt5AccountWorkerClient(
        settings=Settings(live_write_enabled=True), account_id="fixed", terminal_path=None
    )
    with pytest.raises(GatewayConfigurationError, match="yielded"):
        client.get_research_daily_rates(account_id="fixed", count=10)
    client.settings.live_write_enabled = False
    client._lock.acquire()
    try:
        with pytest.raises(GatewayConfigurationError, match="yielded"):
            client.get_research_daily_rates(account_id="fixed", count=10)
    finally:
        client._lock.release()
    assert client._process is None
