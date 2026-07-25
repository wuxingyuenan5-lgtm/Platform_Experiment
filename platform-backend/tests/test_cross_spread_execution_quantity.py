from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.execution_batches import resize_cross_spread_mt5_hedge
from app.main import app
from app.schemas import CreateTradeCommandRequest


def command_requests() -> list[tuple[str, CreateTradeCommandRequest]]:
    return [
        (
            "bybit_leg",
            CreateTradeCommandRequest(
                idempotencyKey="batch-1:bybit_leg",
                strategyInstanceId="strategy_cross_venue_spread_instance_default",
                accountId="account_crypto_test",
                instrumentId="instrument_xau_usdt_perp",
                symbol="XAUTUSDT",
                side="buy",
                orderType="market",
                quantity="100",
            ),
        ),
        (
            "mt5_leg",
            CreateTradeCommandRequest(
                idempotencyKey="batch-1:mt5_leg",
                strategyInstanceId="strategy_cross_venue_spread_instance_default",
                accountId="account_mt5_demo",
                instrumentId="instrument_xau_usd",
                symbol="XAUUSD+",
                side="sell",
                orderType="market",
                quantity="1",
            ),
        ),
    ]


def test_mt5_hedge_quantity_uses_confirmed_bybit_fill(tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-quantity.db")

    with TestClient(app):
        resized = resize_cross_spread_mt5_hedge(
            command_requests(),
            bybit_index=0,
            bybit_filled_quantity=Decimal("40"),
        )

    assert resized[0][1].quantity == Decimal("100")
    assert resized[1][1].quantity == Decimal("0.4")


def test_mt5_hedge_is_blocked_when_partial_fill_cannot_match_contract_step(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-invalid-step.db")

    with TestClient(app), pytest.raises(ValueError, match="hedge minimum|hedge step"):
        resize_cross_spread_mt5_hedge(
            command_requests(),
            bybit_index=0,
            bybit_filled_quantity=Decimal("0.5"),
        )
