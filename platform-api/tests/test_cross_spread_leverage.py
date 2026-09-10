from decimal import Decimal

import httpx
import pytest
from fastapi import HTTPException

from app import cross_spread_leverage as service
from app.config import get_settings


def test_leverage_gate_prevents_runtime_write(monkeypatch):
    monkeypatch.setattr(get_settings(), "live_trading_enabled", False)
    monkeypatch.setattr(
        service.runtime_transport,
        "post",
        lambda *a, **k: pytest.fail("Runtime write must not occur"),
    )
    with pytest.raises(HTTPException) as error:
        service.update_bybit_leverage(Decimal("20"))
    assert error.value.status_code == 403


def test_leverage_uses_bound_account_and_preserves_decimal(monkeypatch):
    monkeypatch.setattr(get_settings(), "live_trading_enabled", True)
    monkeypatch.setattr(service, "get_bybit_account_id", lambda: "bound-bybit-account")
    checks = []
    monkeypatch.setattr(
        service, "assert_execution_allowed", lambda strategy, accounts: checks.append(accounts)
    )
    writes = []

    def post(url, **kwargs):
        writes.append(kwargs["json"])
        return httpx.Response(
            200, json={**kwargs["json"], "source": "bybit_live"}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(service.runtime_transport, "post", post)
    result = service.update_bybit_leverage(Decimal("12.5"))
    assert checks == [["bound-bybit-account"]]
    assert writes == [
        {"accountId": "bound-bybit-account", "symbol": "XAUTUSDT", "leverage": "12.5"}
    ]
    assert result["leverage"] == "12.5"


def test_leverage_unknown_is_not_automatically_replayed(monkeypatch):
    monkeypatch.setattr(get_settings(), "live_trading_enabled", True)
    monkeypatch.setattr(service, "get_bybit_account_id", lambda: "bound")
    monkeypatch.setattr(service, "assert_execution_allowed", lambda *a: None)
    calls = []

    def post(*args, **kwargs):
        calls.append(kwargs)
        raise httpx.ReadTimeout("uncertain")

    monkeypatch.setattr(service.runtime_transport, "post", post)
    with pytest.raises(HTTPException) as error:
        service.update_bybit_leverage(Decimal("20"))
    assert error.value.status_code == 502
    assert len(calls) == 1


def test_leverage_uses_existing_ceo_permission_boundary():
    from app.auth import CEO_TRADE_WRITE_PATHS, permission_for_request

    path = "/api/v1/trading/cross-spread/leverage"
    assert path in CEO_TRADE_WRITE_PATHS
    assert permission_for_request("POST", path) == "trading.write"


@pytest.mark.parametrize("reported", [None, "NaN", "0", "10", "invalid"])
def test_unconfirmed_leverage_is_never_reported_as_success(reported):
    with pytest.raises(HTTPException) as error:
        service._validated(
            {"accountId": "bound", "symbol": "XAUTUSDT", "leverage": reported},
            "bound",
            expected=Decimal("20"),
        )
    assert error.value.status_code == 502
