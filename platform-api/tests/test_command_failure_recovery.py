"""Failures after dispatch must retain one recoverable business identity."""

import httpx
import pytest
from fastapi import HTTPException

from app import application
from app.database import connection
from app.schemas import CreateTradeCommandRequest
from app.trade_commands import create_trade_command
from app.trading import apply_execution_events, reconcile_order, request_from_order_row

pytestmark = pytest.mark.usefixtures("generic_trading_instance")


@pytest.mark.parametrize("failure", ["invalid_json", "http_error", "empty", "invalid_event"])
def test_uncertain_response_keeps_command_and_order_recoverable(monkeypatch, failure):
    application.initialize_database()
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        request = httpx.Request("POST", url)
        if failure == "invalid_json":
            return httpx.Response(200, text="interrupted response", request=request)
        if failure == "http_error":
            return httpx.Response(502, json={"detail": "uncertain"}, request=request)
        return httpx.Response(
            200,
            json=[] if failure == "empty" else [{"event_type": "invalid"}],
            request=request,
        )

    monkeypatch.setattr("app.runtime_transport.post", post)
    request = CreateTradeCommandRequest(
        idempotencyKey="uncertain-command",
        strategyInstanceId="strategy_generic_pipeline_test",
        accountId="account_sim_usdt",
        instrumentId="instrument_btc_usdt",
        symbol="BTCUSDT",
        side="buy",
        orderType="limit",
        quantity="1",
        price="100",
    )
    try:
        create_trade_command(request)
    except HTTPException as exc:
        assert exc.status_code == 502
    with connection() as db:
        rows = db.execute(
            "SELECT tc.status AS command_status, o.status AS order_status "
            "FROM trade_commands tc JOIN orders o ON o.command_id=tc.id"
        ).fetchall()
    assert len(rows) == 1
    assert dict(rows[0]) == {"command_status": "result_unknown", "order_status": "result_unknown"}
    replay = create_trade_command(request)
    assert replay.status == "result_unknown"
    assert len(calls) == 1


def test_terminal_order_reconciliation_repairs_command_without_runtime(monkeypatch):
    application.initialize_database()
    monkeypatch.setattr(
        "app.runtime_transport.post",
        lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError("interrupted")),
    )
    command = create_trade_command(
        CreateTradeCommandRequest(
            idempotencyKey="terminal-command",
            strategyInstanceId="strategy_generic_pipeline_test",
            accountId="account_sim_usdt",
            instrumentId="instrument_btc_usdt",
            symbol="BTCUSDT",
            side="buy",
            orderType="limit",
            quantity="1",
            price="100",
        )
    )
    with connection() as db:
        db.execute("UPDATE orders SET status='rejected' WHERE id=?", (command.platform_order_id,))
    monkeypatch.setattr(
        "app.runtime_transport.post",
        lambda *a, **kw: pytest.fail("terminal order re-dispatched"),
    )
    assert reconcile_order(command.platform_order_id).status == "rejected"
    with connection() as db:
        assert db.execute("SELECT status FROM trade_commands").fetchone()[0] == "rejected"


def test_late_ack_does_not_erase_partial_fill_or_native_identity(monkeypatch):
    application.initialize_database()
    monkeypatch.setattr(
        "app.runtime_transport.post",
        lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError("interrupted")),
    )
    command = create_trade_command(
        CreateTradeCommandRequest(
            idempotencyKey="partial-command",
            strategyInstanceId="strategy_generic_pipeline_test",
            accountId="account_sim_usdt",
            instrumentId="instrument_btc_usdt",
            symbol="BTCUSDT",
            side="buy",
            orderType="limit",
            quantity="1",
            price="100",
        )
    )
    with connection() as db:
        row = db.execute("SELECT * FROM orders WHERE id=?", (command.platform_order_id,)).fetchone()
    request = request_from_order_row(row)
    identity = dict(
        command_id=command.trade_command_id, platform_order_id=command.platform_order_id
    )
    apply_execution_events(
        command.platform_order_id,
        request,
        [
            {
                **identity,
                "event_id": "partial-fill",
                "event_type": "order_filled",
                "external_order_id": "native-order",
                "fill_quantity": "0.5",
                "fill_price": "100",
                "occurred_at": "2026-10-02T00:00:01+00:00",
            }
        ],
        expected_command_id=command.trade_command_id,
    )
    apply_execution_events(
        command.platform_order_id,
        request,
        [
            {
                **identity,
                "event_id": "late-ack",
                "event_type": "order_acknowledged",
                "occurred_at": "2026-10-02T00:00:00+00:00",
            }
        ],
        expected_command_id=command.trade_command_id,
    )
    with connection() as db:
        row = db.execute("SELECT status,external_order_id,updated_at FROM orders").fetchone()
        assert tuple(row) == (
            "partially_filled", "native-order", "2026-10-02T00:00:01Z",
        )
