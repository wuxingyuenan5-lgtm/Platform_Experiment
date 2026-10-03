from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import AuthenticationAssurance, assurance_for_request, permission_for_request
from app.config import Settings, get_settings
from app.cross_spread import (
    CrossSpreadLiveSizing,
    prepare_cross_spread_market_command,
)
from app.main import app
from app.schemas import CrossSpreadPreflightRequest


@pytest.mark.parametrize("status", ["closed", "triggered", "closing"])
def test_close_preflight_rejects_unavailable_group_before_venue_reads(monkeypatch, status):
    monkeypatch.setattr(
        "app.cross_spread_exit_repository.get_exit_plan",
        lambda _: SimpleNamespace(
            status=status,
            direction="LONG_SPREAD",
            quantity_oz=Decimal(1),
        ),
    )
    with pytest.raises(HTTPException, match="closed or already being processed"):
        prepare_cross_spread_market_command(
            CrossSpreadPreflightRequest(
                action="CLOSE_LONG",
                quantityOz="1",
                exitPlanId="stale",
            )
        )


def test_close_preflight_requires_selected_group_and_remaining_quantity(monkeypatch):
    with pytest.raises(HTTPException, match="requires a selected position group"):
        prepare_cross_spread_market_command(
            CrossSpreadPreflightRequest(
                action="CLOSE_LONG",
                quantityOz="1",
            )
        )
    monkeypatch.setattr(
        "app.cross_spread_exit_repository.get_exit_plan",
        lambda _: SimpleNamespace(
            status="active",
            direction="LONG_SPREAD",
            quantity_oz=Decimal("0.5"),
        ),
    )
    with pytest.raises(HTTPException, match="exceeds remaining"):
        prepare_cross_spread_market_command(
            CrossSpreadPreflightRequest(
                action="CLOSE_LONG",
                quantityOz="1",
                exitPlanId="partial",
            )
        )


def test_cross_spread_preflight_prepares_both_live_legs(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.cross_spread.assert_cross_spread_market_executable", lambda *, is_close: None
    )
    monkeypatch.setattr(
        "app.cross_spread._load_live_cross_spread_sizing",
        lambda: CrossSpreadLiveSizing(
            bybit_account_id="bybit-live-main",
            mt5_account_id="mt5-live-main",
            bybit_min=Decimal("0.001"),
            bybit_step=Decimal("0.001"),
            bybit_max=Decimal("100"),
            mt5_min=Decimal("0.01"),
            mt5_step=Decimal("0.01"),
            mt5_max=Decimal("100"),
            mt5_multiplier=Decimal("100"),
        ),
    )
    monkeypatch.setattr(
        "app.execution_batches._reservation_reference_price",
        lambda **kwargs: Decimal("4400") if kwargs["symbol"] == "XAUTUSDT" else Decimal("4405"),
    )
    monkeypatch.setattr(
        "app.execution_batches._reservation_margin_estimate",
        lambda **kwargs: (
            ("USDT", Decimal("220"))
            if kwargs["symbol"] == "XAUTUSDT"
            else ("USD", Decimal("44.05"))
        ),
    )

    result = prepare_cross_spread_market_command(
        CrossSpreadPreflightRequest(action="OPEN_SHORT", quantityOz="1")
    )

    assert result["status"] == "ready"
    assert result["legs"] == [
        {
            "accountId": "bybit-live-main",
            "symbol": "XAUTUSDT",
            "side": "sell",
            "quantity": "1",
            "referencePrice": "4400",
            "reservationCurrency": "USDT",
            "reservationAmount": "220",
        },
        {
            "accountId": "mt5-live-main",
            "symbol": "XAUUSD.s",
            "side": "buy",
            "quantity": "0.01",
            "referencePrice": "4405",
            "reservationCurrency": "USD",
            "reservationAmount": "44.05",
        },
    ]


def test_cross_spread_preflight_is_a_read_permission() -> None:
    assert (
        permission_for_request("POST", "/api/v1/trading/cross-spread/preflight") == "platform:read"
    )
    assert (
        assurance_for_request(
            "POST", "/api/v1/trading/cross-spread/preflight", Settings(environment="live")
        )
        == AuthenticationAssurance.PLATFORM_READ
    )


def test_instruction_lookup_uses_exact_idempotency_key(monkeypatch, tmp_path) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "instruction-lookup.db"))
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_mode", "development")
    monkeypatch.setattr(settings, "live_trading_enabled", False)
    monkeypatch.setattr(settings, "development_roles", "admin")

    def exact_lookup(strategy_instance_id: str, idempotency_key: str) -> dict[str, str]:
        assert strategy_instance_id == "strategy_cross_venue_spread_instance_default"
        if idempotency_key != "known-key":
            raise HTTPException(404, "Strategy instruction not found")
        return {"idempotencyKey": idempotency_key, "status": "completed"}

    monkeypatch.setattr("app.catalog_routes.get_instruction_by_idempotency", exact_lookup)
    url = (
        "/api/v1/strategies/strategy_cross_venue_spread_instance_default"
        "/instructions/by-idempotency/"
    )
    with TestClient(app) as client:
        found = client.get(f"{url}known-key")
        missing = client.get(f"{url}missing-key")
    assert found.status_code == 200
    assert found.json()["idempotencyKey"] == "known-key"
    assert missing.status_code == 404
