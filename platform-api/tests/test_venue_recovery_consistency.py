"""Venue recovery must keep command state atomic and preserve concurrent evidence."""

import httpx
import pytest

from app import application
from app import venue_reconciliation_service as service
from app.database import connection
from app.schemas import CreateTradeCommandRequest
from app.trade_commands import create_trade_command

pytestmark = pytest.mark.usefixtures("generic_trading_instance")


def unknown_order(monkeypatch):
    application.initialize_database()
    monkeypatch.setattr(
        "app.runtime_transport.post",
        lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError("lost response")),
    )
    return create_trade_command(
        CreateTradeCommandRequest(
            idempotencyKey="venue-consistency",
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


@pytest.mark.parametrize("status", ["canceled", "rejected"])
def test_venue_terminal_snapshot_without_fills_synchronizes_command(monkeypatch, status):
    command = unknown_order(monkeypatch)
    service.reconcile_order_snapshot(
        command.platform_order_id,
        external_order={
            "source": "fake",
            "externalOrderId": "native-1",
            "accountId": "account_sim_usdt",
            "instrumentId": "instrument_btc_usdt",
            "side": "buy",
            "symbol": "BTCUSDT",
            "status": status,
            "quantity": "1",
            "filledQuantity": "0",
            "price": "100",
            "asOf": "2026-10-02T00:00:00+00:00",
        },
        fills=[],
    )
    with connection() as db:
        row = db.execute(
            "SELECT o.status,c.status FROM orders o JOIN trade_commands c ON c.id=o.command_id"
        ).fetchone()
    assert tuple(row) == (status, status)


@pytest.mark.parametrize("late_status", ["acknowledged", "filled"])
def test_absent_resolution_rechecks_order_after_runtime_lookup(monkeypatch, late_status):
    command = unknown_order(monkeypatch)
    difference = service.standalone_order_difference(
        command.platform_order_id,
        "missing_external",
        {"status": "result_unknown"},
        {},
    )
    with connection() as db:
        db.execute(
            "UPDATE reconciliation_differences SET status='accepted' WHERE id=?", (difference,)
        )

    def lookup(*args, **kwargs):
        with connection() as db:
            db.execute(
                "UPDATE orders SET status=?,external_order_id='late-native' WHERE id=?",
                (late_status, command.platform_order_id),
            )
        return httpx.Response(404)

    monkeypatch.setattr(service, "runtime_get", lookup)
    with pytest.raises(service.ReconciliationDifferenceNotFoundError):
        service.resolve_owner_accepted_missing_external_order(command.platform_order_id)
    with connection() as db:
        assert (
            db.execute(
                "SELECT status FROM orders WHERE id=?", (command.platform_order_id,)
            ).fetchone()[0]
            == late_status
        )
