from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app
from app.venue_reconciliation import compare_order

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


def test_order_fill_quantity_comparison_preserves_exact_decimal_sum(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "venue-decimal-quantity.db")
    monkeypatch.setattr(
        "app.trade_command_execution.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("timeout")),
    )

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/trading/commands",
            json={
                "idempotencyKey": "venue-decimal-command-001",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "0.3",
                "price": "100",
            },
        )
        assert created.status_code == 200
        order_id = created.json()["platformOrderId"]

        with connection() as db:
            db.executemany(
                """
                INSERT INTO fills (
                    id, order_id, account_id, instrument_id, side, quantity, price, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "decimal-fill-1",
                        order_id,
                        ACCOUNT_ID,
                        INSTRUMENT_ID,
                        "buy",
                        "0.1",
                        "100",
                        "2026-07-24T00:00:00+00:00",
                    ),
                    (
                        "decimal-fill-2",
                        order_id,
                        ACCOUNT_ID,
                        INSTRUMENT_ID,
                        "buy",
                        "0.2000000000000000000000000001",
                        "100",
                        "2026-07-24T00:00:01+00:00",
                    ),
                ],
            )

        differences = compare_order(
            order_id,
            {"status": "result_unknown"},
            {"status": "unknown"},
            [
                {"quantity": "0.1"},
                {"quantity": "0.2000000000000000000000000001"},
            ],
        )

    assert differences == []
