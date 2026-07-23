from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app

STRATEGY = "strategy_funding_arbitrage_instance_default"


def filled_runtime_response(command: dict[str, object]) -> object:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_acknowledged",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "occurred_at": "2026-07-23T00:00:00+00:00",
                },
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_filled",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": command.get("price") or "100",
                    "fill_quantity": command["quantity"],
                    "occurred_at": "2026-07-23T00:00:01+00:00",
                },
            ]

    return FakeResponse()


def batch(key: str) -> dict[str, object]:
    return {
        "idempotencyKey": key,
        "strategyInstanceId": STRATEGY,
        "accountId": "account_sim_usdt",
        "strategyKey": "funding_arbitrage",
        "direction": "collect",
        "maxLegDelayMs": 3000,
        "maxResidualNotional": "0",
        "allowPartialFill": False,
        "emergencyFlatten": True,
        "dispositionPolicy": "flatten_filled_legs",
        "legs": [
            {
                "role": "spot",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "market",
                "quantity": "0.01",
                "timeInForce": "FOK",
                "allowPartialFill": False,
            },
            {
                "role": "perp",
                "instrumentId": "instrument_btc_usdt_perp",
                "symbol": "BTCUSDT",
                "side": "sell",
                "orderType": "market",
                "quantity": "0.01",
                "timeInForce": "FOK",
                "allowPartialFill": False,
            },
        ],
    }


def test_phase4_batch_is_hedged_and_idempotent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    get_settings().database_path = str(tmp_path / "hedged.db")
    monkeypatch.setattr(
        "app.trading.httpx.post",
        lambda *args, **kwargs: filled_runtime_response(kwargs["json"]),
    )
    with TestClient(app) as client:
        first = client.post("/api/v1/trading/execution-batches", json=batch("phase4-hedged"))
        assert first.status_code == 200
        assert first.json()["status"] == "hedged"
        assert first.json()["riskState"] == "hedged"
        duplicate = client.post("/api/v1/trading/execution-batches", json=batch("phase4-hedged"))
        assert duplicate.json()["batchId"] == first.json()["batchId"]
        assert len(client.get("/api/v1/trading/orders").json()) == 2


def test_kill_switch_blocks_execution(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "switch.db")
    with TestClient(app) as client:
        switch = client.put(
            f"/api/v1/trading/kill-switches/strategy/{STRATEGY}",
            json={"engaged": True, "reason": "test stop"},
        )
        assert switch.status_code == 200
        blocked = client.post("/api/v1/trading/execution-batches", json=batch("blocked"))
        assert blocked.status_code == 423


def test_second_leg_failure_repairs_actual_first_fill(tmp_path: Path, monkeypatch) -> None:
    get_settings().database_path = str(tmp_path / "repair.db")
    with TestClient(app) as client:
        from app import phase4_risk
        from app.schemas import TradeCommandResponse

        calls = []

        def fake_create(request):
            calls.append(request)
            if len(calls) == 1:
                with connection() as db:
                    db.execute(
                        """
                        INSERT INTO orders (
                            id, command_id, account_id, instrument_id, symbol,
                            side, order_type, quantity, price, status,
                            created_at, updated_at
                        ) VALUES (
                            'o1', 'c1', ?, ?, ?, ?, ?, ?, NULL, 'filled',
                            '2026-07-23T00:00:00+00:00',
                            '2026-07-23T00:00:00+00:00'
                        )
                    """,
                        (
                            request.account_id,
                            request.instrument_id,
                            request.symbol,
                            request.side,
                            request.order_type,
                            str(request.quantity),
                        ),
                    )
                    db.execute(
                        """
                        INSERT INTO fills (
                            id, order_id, account_id, instrument_id,
                            side, quantity, price, occurred_at
                        ) VALUES (
                            'f1', 'o1', ?, ?, ?, '0.01', '100',
                            '2026-07-23T00:00:00+00:00'
                        )
                    """,
                        (request.account_id, request.instrument_id, request.side),
                    )
                status, order_id = "filled", "o1"
            elif len(calls) == 2:
                status, order_id = "rejected", None
            else:
                status, order_id = "filled", "repair"
            return TradeCommandResponse(
                tradeCommandId=f"c{len(calls)}",
                idempotencyKey=request.idempotency_key,
                strategyInstanceId=request.strategy_instance_id,
                accountId=request.account_id,
                instrumentId=request.instrument_id,
                platformOrderId=order_id,
                status=status,
                createdAt="2026-07-23T00:00:00+00:00",
                updatedAt="2026-07-23T00:00:00+00:00",
            )

        monkeypatch.setattr(phase4_risk, "create_trade_command", fake_create)
        result = client.post("/api/v1/trading/execution-batches", json=batch("repair"))
        assert result.status_code == 200
        assert result.json()["status"] == "compensated"
        assert calls[-1].reduce_only is True
        assert calls[-1].time_in_force == "FOK"
        assert calls[-1].quantity == calls[0].quantity
        assert calls[-1].side == "sell"
