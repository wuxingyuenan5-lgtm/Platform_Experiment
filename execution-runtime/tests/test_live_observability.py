from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.fake_gateway import FakeGateway
from app.main import app, create_app
from app.strict_live_acceptance_adapters import (
    StrictBybitAcceptanceAdapter,
    StrictMt5AcceptanceAdapter,
)


class FakeBybitObservabilityClient:
    def get_positions(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": "XAUTUSDT",
                        "side": "Buy",
                        "size": "1",
                        "positionIdx": 1,
                        "avgPrice": "2400",
                        "markPrice": "2410",
                        "breakEvenPrice": "2401",
                        "liqPrice": "1800",
                        "positionValue": "2410",
                        "leverage": "3",
                        "positionIM": "803.33",
                        "positionMM": "12.05",
                        "unrealisedPnl": "10",
                        "curRealisedPnl": "1.2",
                        "stopLoss": "2200",
                        "takeProfit": "2500",
                        "positionStatus": "Normal",
                        "riskLimitValue": "200000",
                        "isReduceOnly": False,
                        "autoAddMargin": 0,
                        "updatedTime": "1784800000000",
                    }
                ]
            },
        }

    def get_wallet_balance(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "totalEquity": "1000",
                        "totalWalletBalance": "990",
                        "totalMarginBalance": "1000",
                        "totalAvailableBalance": "190",
                        "totalInitialMargin": "803.33",
                        "totalMaintenanceMargin": "12.05",
                        "totalPerpUPL": "10",
                        "accountIMRate": "0.80333",
                        "accountMMRate": "0.01205",
                    }
                ]
            },
        }

    def get_account_info(self):
        return {"retCode": 0, "result": {"marginMode": "REGULAR_MARGIN"}}


class FakeMt5ObservabilityProvider:
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1

    def positions_get(self):
        return (
            SimpleNamespace(
                ticket=789,
                type=self.POSITION_TYPE_BUY,
                symbol="XAUUSD+",
                volume=0.01,
                price_open=2400.0,
                price_current=2410.0,
                profit=10.0,
                swap=-0.5,
                sl=2200.0,
                tp=2500.0,
                time_update=1784800000,
                time_update_msc=1784800000000,
            ),
        )

    def account_info(self):
        return SimpleNamespace(
            login=123456,
            currency="USD",
            balance=990.0,
            equity=1000.0,
            profit=10.0,
            margin=100.0,
            margin_free=900.0,
            margin_level=1000.0,
            margin_so_call=100.0,
            margin_so_so=50.0,
            margin_so_mode=0,
            margin_maintenance=50.0,
            leverage=100,
            margin_mode=2,
            trade_allowed=True,
            trade_expert=True,
        )

    def terminal_info(self):
        return SimpleNamespace(trade_allowed=True)

    def last_error(self):
        return (0, "ok")


def bybit_settings() -> Settings:
    return Settings(
        environment="live",
        bybit_account_ids="account-bybit",
        bybit_instrument_map="XAUTUSDT=instrument-xaut",
    )


def mt5_settings() -> Settings:
    return Settings(
        environment="live",
        mt5_account_ids="account-mt5",
        mt5_instrument_map="XAUUSD+=instrument-xauusd",
    )


def configure_mt5_secret(monkeypatch) -> None:
    monkeypatch.setenv("VG_SECRET_MT5_LIVE_001_LOGIN", "123456")
    monkeypatch.setenv("VG_SECRET_MT5_LIVE_001_PASSWORD", "not-exposed")
    monkeypatch.setenv("VG_SECRET_MT5_LIVE_001_SERVER", "Broker-Live")


def test_bybit_liquidation_and_margin_fields_are_venue_reported() -> None:
    adapter = StrictBybitAcceptanceAdapter(
        bybit_settings(),
        FakeBybitObservabilityClient(),
    )

    position = adapter.list_positions("account-bybit")[0]
    risk = adapter.get_account_risk("account-bybit")

    assert position.liquidation_price == Decimal("1800")
    assert position.liquidation_price_source == "venue_reported"
    assert position.mark_price == Decimal("2410")
    assert position.maintenance_margin == Decimal("12.05")
    assert risk.account_mm_rate == Decimal("0.01205")
    assert risk.maintenance_margin == Decimal("12.05")


def test_mt5_uses_account_stopout_without_inventing_position_liquidation(
    monkeypatch,
) -> None:
    configure_mt5_secret(monkeypatch)
    adapter = StrictMt5AcceptanceAdapter(
        mt5_settings(),
        FakeMt5ObservabilityProvider(),
    )

    position = adapter.list_positions("account-mt5")[0]
    risk = adapter.get_account_risk("account-mt5")

    assert position.liquidation_price is None
    assert position.liquidation_price_source == "not_available_mt5_api"
    assert position.current_price == Decimal("2410.0")
    assert position.swap == Decimal("-0.5")
    assert risk.margin_level == Decimal("1000.0")
    assert risk.margin_call_level == Decimal("100.0")
    assert risk.stop_out_level == Decimal("50.0")


def test_runtime_history_window_is_bounded_to_seven_days() -> None:
    now = datetime.now(UTC)
    too_early = now - timedelta(days=8)

    with TestClient(app) as client:
        response = client.get(
            "/venue/order-history",
            params={
                "accountId": "account_sim_usdt",
                "startTime": too_early.isoformat(),
                "endTime": now.isoformat(),
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "History query window cannot exceed 7 days"


def test_fake_history_and_account_risk_are_read_only_and_pageable(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "observability.db")
    now = datetime.now(UTC)
    command = {
        "command_id": "observability-command-001",
        "platform_order_id": "observability-order-001",
        "account_id": "account_sim_usdt",
        "instrument_id": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": "1",
    }

    with TestClient(create_app(FakeGateway())) as client:
        assert client.post("/commands/orders", json=command).status_code == 200
        orders = client.get(
            "/venue/order-history",
            params={
                "accountId": "account_sim_usdt",
                "symbol": "BTCUSDT",
                "startTime": (now - timedelta(hours=1)).isoformat(),
                "endTime": (now + timedelta(hours=1)).isoformat(),
                "limit": 1,
            },
        )
        fills = client.get(
            "/venue/fill-history",
            params={
                "accountId": "account_sim_usdt",
                "symbol": "BTCUSDT",
                "startTime": (now - timedelta(hours=1)).isoformat(),
                "endTime": (now + timedelta(hours=1)).isoformat(),
                "limit": 1,
            },
        )
        risk = client.get(
            "/venue/account-risk",
            params={"accountId": "account_sim_usdt"},
        )

    assert orders.status_code == 200
    assert orders.json()["items"][0]["externalOrderId"] == "FAKE-observability-order-001"
    assert fills.status_code == 200
    assert fills.json()["items"][0]["externalFillId"] == "FAKE-FILL-observability-order-001"
    assert risk.status_code == 200
    assert risk.json()["source"] == "fake"
