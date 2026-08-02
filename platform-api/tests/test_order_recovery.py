from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schemas import CreateOrderRequest
from app.trading import apply_execution_events


def command_payload(idempotency_key: str) -> dict[str, str]:
    return {
        "idempotencyKey": idempotency_key,
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "accountId": "account_sim_usdt",
        "instrumentId": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": "1",
        "price": "100",
    }


def runtime_events(command_id: str, order_id: str) -> list[dict[str, object]]:
    return [
        {
            "event_id": "event-recovery-ack-001",
            "command_id": command_id,
            "platform_order_id": order_id,
            "event_type": "order_acknowledged",
            "external_order_id": "external-recovery-001",
            "fill_price": None,
            "fill_quantity": None,
            "occurred_at": "2026-07-23T06:00:00+00:00",
            "reason": None,
        },
        {
            "event_id": "event-recovery-fill-001",
            "command_id": command_id,
            "platform_order_id": order_id,
            "event_type": "order_filled",
            "external_order_id": "external-recovery-001",
            "fill_price": "100",
            "fill_quantity": "1",
            "occurred_at": "2026-07-23T06:00:01+00:00",
            "reason": None,
        },
    ]


def test_result_unknown_recovers_from_runtime_journal(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "recover.db")
    monkeypatch.setattr(
        "app.trade_command_execution.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("timeout")),
    )

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/trading/commands",
            json=command_payload("recovery-command-001"),
        )
        assert created.status_code == 200
        command = created.json()
        assert command["status"] == "result_unknown"
        order_id = command["platformOrderId"]
        command_id = command["tradeCommandId"]

        class FakeResponse:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self) -> list[dict[str, object]]:
                return runtime_events(command_id, order_id)

        monkeypatch.setattr(
            "app.runtime_recovery_client.httpx.post",
            lambda *args, **kwargs: FakeResponse(),
        )
        monkeypatch.setattr(
            "app.runtime_recovery_client.httpx.get",
            lambda *args, **kwargs: FakeResponse(),
        )
        recovered = client.post(f"/api/v1/trading/orders/{order_id}/reconcile")

        assert recovered.status_code == 200
        assert recovered.json()["status"] == "filled"
        assert recovered.json()["externalOrderId"] == "external-recovery-001"

        position = client.get(
            "/api/v1/accounts/account_sim_usdt/positions/instrument_btc_usdt"
        )
        assert position.status_code == 200
        assert position.json()["netQuantity"] == "1"

        command_after = client.get(f"/api/v1/trading/commands/{command_id}")
        assert command_after.json()["status"] == "filled"

        replay_request = CreateOrderRequest(
            accountId="account_sim_usdt",
            instrumentId="instrument_btc_usdt",
            symbol="BTCUSDT",
            side="buy",
            orderType="limit",
            quantity="1",
            price="100",
        )
        apply_execution_events(
            order_id,
            replay_request,
            runtime_events(command_id, order_id),
            expected_command_id=command_id,
        )

        position_after_replay = client.get(
            "/api/v1/accounts/account_sim_usdt/positions/instrument_btc_usdt"
        )
        assert position_after_replay.json()["netQuantity"] == "1"


def test_result_unknown_remains_unknown_when_runtime_has_no_events(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "recover-missing.db")
    monkeypatch.setattr(
        "app.trade_command_execution.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("timeout")),
    )

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/trading/commands",
            json=command_payload("recovery-command-missing-001"),
        )
        order_id = created.json()["platformOrderId"]

        monkeypatch.setattr(
            "app.runtime_recovery_client.httpx.post",
            lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("offline")),
        )
        recovered = client.post(f"/api/v1/trading/orders/{order_id}/reconcile")

        assert recovered.status_code == 200
        assert recovered.json()["status"] == "result_unknown"


def _versioned_event(
    *,
    event_id: str,
    command_id: str,
    order_id: str,
    event_type: str,
    external_order_id: str = "external-recovery-001",
    fill_price: str | None = None,
    fill_quantity: str | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    return {
        "contract_name": "runtime-event",
        "contract_version": "1.0",
        "payload_version": "1.0",
        "event_id": event_id,
        "command_id": command_id,
        "platform_order_id": order_id,
        "event_type": event_type,
        "external_order_id": external_order_id,
        "fill_price": fill_price,
        "fill_quantity": fill_quantity,
        "occurred_at": "2026-08-02T12:00:00+00:00",
        "reason": reason,
    }


class _RuntimeResponse:
    status_code = 200

    def __init__(self, payload: list[dict[str, object]]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, object]]:
        return self.payload


def _configure_runtime_recovery(monkeypatch, events: list[dict[str, object]]) -> None:
    response = _RuntimeResponse(events)
    monkeypatch.setattr("app.runtime_recovery_client.httpx.post", lambda *a, **k: response)
    monkeypatch.setattr("app.runtime_recovery_client.httpx.get", lambda *a, **k: response)


def _create_result_unknown(client: TestClient, monkeypatch, payload: dict[str, str]):
    monkeypatch.setattr(
        "app.trade_command_execution.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("timeout")),
    )
    response = client.post("/api/v1/trading/commands", json=payload)
    assert response.status_code == 200, response.json()
    assert response.json()["status"] == "result_unknown"
    return response.json()


@pytest.mark.parametrize(
    ("event_type", "expected_status"),
    [
        ("order_acknowledged", "acknowledged"),
        ("order_rejected", "rejected"),
    ],
)
def test_recovery_synchronizes_platform_order_and_trade_command(
    monkeypatch,
    tmp_path: Path,
    event_type: str,
    expected_status: str,
) -> None:
    get_settings().database_path = str(tmp_path / f"recover-{expected_status}.db")
    with TestClient(app) as client:
        created = _create_result_unknown(
            client,
            monkeypatch,
            command_payload(f"recovery-{expected_status}-001"),
        )
        order_id = created["platformOrderId"]
        command_id = created["tradeCommandId"]
        events = [
            _versioned_event(
                event_id=f"event-{expected_status}-001",
                command_id=command_id,
                order_id=order_id,
                event_type=event_type,
                reason="venue rejected" if event_type == "order_rejected" else None,
            )
        ]
        _configure_runtime_recovery(monkeypatch, events)

        recovered = client.post(f"/api/v1/trading/orders/{order_id}/reconcile")
        command_after = client.get(f"/api/v1/trading/commands/{command_id}")

    assert recovered.status_code == 200
    assert recovered.json()["status"] == expected_status
    assert command_after.json))["status"] == expected_status


def test_partial_fill_recovery_is_decimal_exact_and_idempotent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from decimal import Decimal

    from app.database import connection

    get_settings().database_path = str(tmp_path / "recover-partial.db")
    payload = command_payload("recovery-partial-001")
    payload.update({"side": "sell", "quantity": "1.00000000", "price": "100.12"})

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO positions (
                    account_id, instrument_id, net_quantity, average_price, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "account_sim_usdt",
                    "instrument_btc_usdt",
                    "1.00000000",
                    "100.00000000",
                    "2026-08-02T11:59:00+00:00",
                ),
            )
        created = _create_result_unknown(client, monkeypatch, payload)
        order_id = created["platformOrderId"]
        command_id = created["tradeCommandId"]
        events = [
            _versioned_event(
                event_id="event-partial-ack-001",
                command_id=command_id,
                order_id=order_id,
                event_type="order_acknowledged",
            ),
            _versioned_event(
                event_id="event-partial-fill-001",
                command_id=command_id,
                order_id=order_id,
                event_type="order_filled",
                fill_price="100.12345678",
                fill_quantity="0.33333333",
            ),
        ]
        _configure_runtime_recovery(monkeypatch, events)

        first = client.post(f"/api/v1/trading/orders/{order_id}/reconcile")
        second = client.post(f"/api/v1/trading/orders/{order_id}/reconcile")
        command_after = client.get(f"/api/v1/trading/commands/{command_id}")

        with connection() as db:
            position = db.execute(
                """
                SELECT net_quantity, average_price
                FROM positions
                WHERE account_id = ? AND instrument_id = ?
                """,
                ("account_sim_usdt", "instrument_btc_usdt"),
            ).fetchone()
            fill = db.execute(
                "SELECT quantity, price FROM fills WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            pnl = db.execute(
                """
                SELECT realized_pnl, trading_pnl
                FROM pnl_results
                WHERE account_id = ? AND instrument_id = ?
                """,
                ("account_sim_usdt", "instrument_btc_usdt"),
            ).fetchone()
            fill_count = db.execute(
                "SELECT COUNT(*) AS count FROM fills WHERE order_id = ?",
                (order_id,),
            ).fetchone()["count"]

    expected_pnl = (Decimal("100.12345678") - Decimal("100.00000000")) * Decimal(
        "0.33333333"
    )
    assert first.json()["status"] == "filled"
    assert second.json() == first.json()
    assert command_after.json()["status"] == "filled"
    assert position["net_quantity"] == "0.66666667"
    assert position["average_price"] == "100.00000000"
    assert fill["quantity"] == "0.33333333"
    assert fill["price"] == "100.12345678"
    assert Decimal(pnl["realized_pnl"]) == expected_pnl
    assert Decimal(pnl["trading_pnl"]) == expected_pnl
    assert fill_count == 1


def test_recovery_rejects_wrong_platform_order_without_pollution(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from app.database import connection

    get_settings().database_path = str(tmp_path / "recover-mismatch.db")
    with TestClient(app) as client:
        created = _create_result_unknown(
            client,
            monkeypatch,
            command_payload("recovery-mismatch-001"),
        )
        order_id = created["platformOrderId"]
        command_id = created["tradeCommandId"]
        events = [
            _versioned_event(
                event_id="event-mismatch-001",
                command_id=command_id,
                order_id="different-platform-order",
                event_type="order_filled",
                fill_price="100",
                fill_quantity="1",
            )
        ]
        _configure_runtime_recovery(monkeypatch, events)
        response = client.post(f"/api/v1/trading/orders/{order_id}/reconcile")
        order_after = client.get(f"/api/v1/trading/orders/{order_id}")
        command_after = client.get(f"/api/v1/trading/commands/{command_id}")
        with connection() as db:
            fill_count = db.execute(
                "SELECT COUNT(*) AS count FROM fills WHERE order_id = ?", (order_id,)
            ).fetchone()["count"]

    assert response.status_code == 502
    assert order_after.json()["status"] == "result_unknown"
    assert command_after.json()["status"] == "result_unknown"
    assert fill_count == 0
