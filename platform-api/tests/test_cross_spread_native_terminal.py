from pathlib import Path

import pytest
from fastapi import HTTPException

from app.application import initialize_database
from app.config import get_settings
from app.database import connection
from app.execution_batches import _confirmed_terminal_chase_fill
from app.schemas import CreateOrderRequest
from app.trading import apply_execution_events


def _seed_order(tmp_path: Path, policy: str) -> tuple[str, CreateOrderRequest]:
    get_settings().database_path = str(tmp_path / f"terminal-{policy}.db")
    initialize_database()
    order_id = f"order-{policy}"
    command_id = f"command-{policy}"
    key = f"instruction:terminal-{policy}:bybit_leg"
    request = CreateOrderRequest(
        accountId="account_crypto_test",
        instrumentId="instrument_xau_usdt_perp",
        symbol="XAUTUSDT",
        side="buy",
        orderType="limit",
        quantity="1",
        price="2350",
    )
    with connection() as db:
        db.execute(
            "INSERT INTO trade_commands (id,idempotency_key,strategy_instance_id,account_id,"
            "instrument_id,command_type,side,order_type,quantity,price,status,"
            "created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                command_id,
                key,
                "strategy_cross_venue_spread_instance_default",
                request.account_id,
                request.instrument_id,
                "create_order",
                request.side,
                request.order_type,
                "1",
                "2350",
                "accepted",
                "2026-09-14T00:00:00+00:00",
                "2026-09-14T00:00:00+00:00",
            ),
        )
        db.execute(
            "INSERT INTO order_execution_intents "
            "(idempotency_key,reduce_only,position_id,execution_policy) VALUES (?,?,?,?)",
            (key, 0, None, policy),
        )
        db.execute(
            "INSERT INTO orders (id,command_id,account_id,instrument_id,symbol,side,order_type,"
            "quantity,price,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                order_id,
                command_id,
                request.account_id,
                request.instrument_id,
                request.symbol,
                request.side,
                request.order_type,
                "1",
                "2350",
                "processing",
                "2026-09-14T00:00:00+00:00",
                "2026-09-14T00:00:00+00:00",
            ),
        )
    return order_id, request


def _event(order_id: str, event_id: str, *, terminal: bool, quantity: str = "0.4") -> dict:
    return {
        "event_id": event_id,
        "command_id": f"command-{order_id.removeprefix('order-')}",
        "platform_order_id": order_id,
        "event_type": "order_filled",
        "external_order_id": "ext",
        "fill_price": "2350",
        "fill_quantity": quantity,
        "occurred_at": "2026-09-14T00:00:01+00:00",
        "terminal": terminal,
    }


def test_terminal_partial_is_persisted_and_releases_only_chase(tmp_path: Path) -> None:
    order_id, request = _seed_order(tmp_path, "post_only_chase")
    apply_execution_events(
        order_id,
        request,
        [_event(order_id, "fill-1", terminal=True)],
        expected_command_id="command-post_only_chase",
    )
    apply_execution_events(
        order_id,
        request,
        [_event(order_id, "fill-1", terminal=True)],
        expected_command_id="command-post_only_chase",
    )
    assert _confirmed_terminal_chase_fill(order_id)
    with connection() as db:
        assert (
            db.execute(
                "SELECT filled_quantity FROM runtime_order_terminals WHERE order_id=?", (order_id,)
            ).fetchone()[0]
            == "0.4"
        )


@pytest.mark.parametrize("policy,terminal", [("fok", True), ("post_only_chase", False)])
def test_nonterminal_or_fok_partial_does_not_release(tmp_path: Path, policy, terminal) -> None:
    order_id, request = _seed_order(tmp_path, policy)
    apply_execution_events(
        order_id,
        request,
        [_event(order_id, "fill-1", terminal=terminal)],
        expected_command_id=f"command-{policy}",
    )
    assert not _confirmed_terminal_chase_fill(order_id)


def test_terminal_fill_quantity_cannot_change(tmp_path: Path) -> None:
    order_id, request = _seed_order(tmp_path, "post_only_chase")
    apply_execution_events(
        order_id,
        request,
        [_event(order_id, "fill-1", terminal=True)],
        expected_command_id="command-post_only_chase",
    )
    with pytest.raises(HTTPException, match="Terminal order fill quantity changed"):
        apply_execution_events(
            order_id,
            request,
            [_event(order_id, "fill-2", terminal=False, quantity="0.1")],
            expected_command_id="command-post_only_chase",
        )
