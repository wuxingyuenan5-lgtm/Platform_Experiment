import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.config import get_settings
from app.database import connection, initialize_database
from app.execution_risk import ensure_schema as ensure_risk_schema
from app.live_venue_snapshot_sync import _persist_venue_event
from app.schemas import CrossSpreadSnapshotResponse
from app.strategy_financial_readmodel import get_cross_spread_position_overview

CROSS = "strategy_cross_venue_spread_instance_default"
BYBIT = "bybit-live-main"
MT5 = "mt5-live-main"


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path / "groups.db"))
    initialize_database()
    ensure_risk_schema()


def add_group(
    identity, *, direction="LONG_SPREAD", quantity="1", bybit_price="100", mt5_price="101"
):
    now = datetime.now(UTC).isoformat()
    qty = Decimal(quantity)
    frozen_legs = []
    with connection() as db:
        db.execute(
            "INSERT INTO execution_batches (id,idempotency_key,strategy_instance_id,account_id,"
            "strategy_key,direction,status,requires_manual_intervention,created_at,updated_at) "
            "VALUES (?,?,?,?,?,'OPEN','hedged',0,?,?)",
            (identity, identity, CROSS, BYBIT, "cross_venue_spread", now, now),
        )
        for seq, role, account, instrument, symbol, side, size, price, multiplier in (
            (
                1,
                "bybit_leg",
                BYBIT,
                "instrument_xau_usdt_perp",
                "XAUTUSDT",
                "buy" if direction == "LONG_SPREAD" else "sell",
                qty,
                bybit_price,
                "1",
            ),
            (
                2,
                "mt5_leg",
                MT5,
                "instrument_xau_usd",
                "XAUUSD.s",
                "sell" if direction == "LONG_SPREAD" else "buy",
                qty / 100,
                mt5_price,
                "100",
            ),
        ):
            oid = f"{identity}:{role}"
            db.execute(
                "INSERT INTO trade_commands (id,idempotency_key,strategy_instance_id,account_id,"
                "instrument_id,command_type,side,order_type,quantity,status,created_at,updated_at) "
                "VALUES (?,?,?,?,?,'create_order',?,'market',?,'filled',?,?)",
                (oid, oid, CROSS, account, instrument, side, str(size), now, now),
            )
            db.execute(
                "INSERT INTO orders (id,command_id,account_id,instrument_id,symbol,side,order_type,"
                "quantity,status,external_order_id,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,'market',?,'filled',?,?,?)",
                (oid, oid, account, instrument, symbol, side, str(size), oid, now, now),
            )
            db.execute(
                "INSERT INTO execution_batch_legs (id,batch_id,sequence,role,account_id,"
                "instrument_id,symbol,side,order_type,quantity,order_id,status,"
                "created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,'market',?,?,'filled',?,?)",
                (
                    oid,
                    identity,
                    seq,
                    role,
                    account,
                    instrument,
                    symbol,
                    side,
                    str(size),
                    oid,
                    now,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO fills (id,order_id,account_id,instrument_id,side,quantity,price,"
                "occurred_at,origin,source) VALUES (?,?,?,?,?,?,?,?,"
                "'runtime_confirmation','runtime_v1')",
                (oid, oid, account, instrument, side, str(size), price, now),
            )
            frozen_legs.append(
                {
                    "role": role,
                    "account_id": account,
                    "instrument_id": instrument,
                    "external_symbol": symbol,
                    "side": side,
                    "maximum_quantity": str(size),
                    "sequence": seq,
                    "execution_policy": "market",
                    "quantity_step": "0.001",
                    "contract_multiplier": multiplier,
                    "minimum_quantity": "0.001",
                }
            )
        frozen = {
            "strategy_key": "cross_venue_spread",
            "action": "open",
            "adapter_version": "1",
            "account_capability_snapshot": {},
            "created_at": now,
            "legs": frozen_legs,
        }
        db.execute(
            "INSERT INTO strategy_runs (id,idempotency_key,strategy_instance_id,strategy_key,"
            "direction,status,execution_batch_id,created_at,updated_at,action,execution_plan_json) "
            "VALUES (?,?,?,'cross_venue_spread',?,'completed',?,?,?,'open',?)",
            (identity, identity, CROSS, direction, identity, now, now, json.dumps(frozen)),
        )
        db.execute(
            "INSERT INTO cross_spread_exit_plans (id,strategy_instance_id,open_batch_id,direction,"
            "quantity_oz,mt5_position_id,entry_spread,take_profit_spread,stop_loss_spread,"
            "status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,'active',?,?)",
            (
                identity,
                CROSS,
                identity,
                direction,
                quantity,
                f"ticket:{identity}",
                str(Decimal(bybit_price) - Decimal(mt5_price)),
                "5" if direction == "LONG_SPREAD" else "-5",
                "-5" if direction == "LONG_SPREAD" else "5",
                now,
                now,
            ),
        )


def market(*, bid="110", ask="110.2", positions=None, fx="0.9998"):
    now = datetime.now(UTC).isoformat()
    return CrossSpreadSnapshotResponse.model_validate(
        {
            "status": "available",
            "asOf": now,
            "bybit": {
                "venue": "bybit",
                "symbol": "XAUTUSDT",
                "status": "available",
                "asOf": now,
                "positions": [],
                "quote": {"bid": bid, "ask": ask, "mid": bid, "currency": "USDT"},
            },
            "mt5": {
                "venue": "mt5",
                "symbol": "XAUUSD.s",
                "status": "available",
                "asOf": now,
                "positions": positions or [],
                "quote": {"bid": "111", "ask": "111.2", "mid": "111.1", "currency": "USD"},
            },
            "metrics": {"usdtUsd": fx},
        }
    )


def mt5_position(identity, *, size="-0.01", price="101", pnl="-10.2", currency="USDT"):
    return {
        "symbol": "XAUUSD.s",
        "accountId": MT5,
        "side": "sell" if Decimal(size) < 0 else "buy",
        "quantity": size,
        "averagePrice": price,
        "unrealizedPnl": pnl,
        "currency": currency,
        "externalId": f"ticket:{identity}",
        "asOf": datetime.now(UTC).isoformat(),
    }


def overview(snapshot):
    return get_cross_spread_position_overview(
        snapshot, strategy_instance_id=CROSS, bybit_account_id=BYBIT, mt5_account_id=MT5
    )


@pytest.mark.parametrize("dispatched", [False, True])
def test_rejected_close_keeps_pnl_only_when_no_command_was_dispatched(dispatched):
    add_group("held")
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            "INSERT INTO execution_batches(id,idempotency_key,strategy_instance_id,account_id,"
            "strategy_key,direction,status,created_at,updated_at) "
            "VALUES ('failed-close','instruction:exit',?,?,'cross_venue_spread',"
            "'close','failed',?,?)",
            (CROSS, BYBIT, now, now),
        )
        db.execute(
            "INSERT INTO strategy_runs(id,idempotency_key,strategy_instance_id,"
            "strategy_key,direction,"
            "status,execution_batch_id,action,requested_parameters_json,created_at,updated_at) "
            "VALUES ('rejected','exit',?,'cross_venue_spread','close','rejected',"
            "'failed-close','close',?,?,?)",
            (CROSS, json.dumps({"mt5PositionId": "ticket:held"}), now, now),
        )
        db.execute(
            "INSERT INTO execution_batch_legs(id,batch_id,sequence,role,account_id,instrument_id,"
            "symbol,side,order_type,quantity,status,created_at,updated_at) "
            "SELECT 'close:'||role,'failed-close',sequence,role,account_id,instrument_id,symbol,"
            "side,order_type,quantity,'pending',created_at,updated_at "
            "FROM execution_batch_legs WHERE batch_id='held'"
        )
        db.execute(
            "UPDATE cross_spread_exit_plans SET status='manual_intervention',"
            "close_batch_id='failed-close' WHERE id='held'"
        )
        if dispatched:
            db.execute(
                "INSERT INTO trade_commands(id,idempotency_key,strategy_instance_id,account_id,"
                "instrument_id,command_type,side,order_type,quantity,status,created_at,updated_at) "
                "SELECT 'orphan-close','instruction:exit:bybit_leg',"
                "strategy_instance_id,account_id,"
                "instrument_id,command_type,side,order_type,quantity,'result_unknown',"
                "created_at,updated_at "
                "FROM trade_commands WHERE id='held:bybit_leg'"
            )
    result = overview(market(positions=[mt5_position("held")]))
    assert (result.groups[0].totalPnlUsdt is None) is dispatched
    assert result.totalPnlUsdt == 0  # Abnormal groups are excluded from normal totals.


def test_active_groups_do_not_hide_an_unattributed_native_position():
    add_group("long")
    add_group("short", direction="SHORT_SPREAD")
    snapshot = market(
        positions=[
            mt5_position("long"),
            mt5_position("short", size="0.01"),
            mt5_position("unexpected", size="-0.01", price="105"),
        ]
    )
    snapshot.bybit.positions = [
        type(snapshot.mt5.positions[0]).model_validate(
            {
                "symbol": "XAUTUSDT",
                "side": "buy",
                "quantity": "1",
                "accountId": BYBIT,
                "averagePrice": "103",
                "asOf": datetime.now(UTC).isoformat(),
            }
        )
    ]
    result = overview(snapshot)
    assert len(result.groups) == 2
    assert [(p.venue, p.quantity, p.external_id) for p in result.unattributedPositions] == [
        ("mt5", Decimal("-0.01"), "ticket:unexpected"),
        ("bybit", Decimal("1"), None),
    ]
    # Shared net cost must not be assigned to the unexplained Bybit difference.
    assert result.unattributedPositions[1].average_price is None


def test_opposite_groups_remain_valued_when_bybit_native_net_position_is_zero():
    add_group("long", bybit_price="4392.9", mt5_price="4396.12")
    add_group("short", direction="SHORT_SPREAD", bybit_price="4390.5", mt5_price="4395.44")
    snapshot = market(
        bid="4395.0",
        ask="4395.1",
        positions=[
            mt5_position("long", price="4396.12", pnl="-2.90"),
            mt5_position("short", size="0.01", price="4395.44", pnl="3.35"),
        ],
    )
    result = overview(snapshot)
    groups = {row.planId: row for row in result.groups}
    assert groups["long"].bybitPnlUsdt == Decimal("2.1")
    assert groups["short"].bybitPnlUsdt == Decimal("-4.6")
    assert groups["long"].totalPnlUsdt == Decimal("-0.80")
    assert groups["short"].totalPnlUsdt == Decimal("-1.25")
    assert result.bybitPnlUsdt == Decimal("-2.5")
    assert result.mt5PnlUsdt == Decimal("0.45")
    assert result.totalPnlUsdt == Decimal("-2.05")
    assert result.dataQualityState == "complete"


def test_same_direction_groups_use_own_cost_and_quantity_not_shared_account_profit():
    add_group("one", bybit_price="100")
    add_group("two", quantity="2", bybit_price="105", mt5_price="106")
    snapshot = market(
        positions=[mt5_position("one"), mt5_position("two", size="-0.02", price="106", pnl="-10.4")]
    )
    snapshot.bybit.positions = []  # Account net position is not a cost/PnL input.
    result = overview(snapshot)
    groups = {row.planId: row for row in result.groups}
    assert groups["one"].bybitEntryPrice == Decimal("100")
    assert groups["two"].bybitEntryPrice == Decimal("105")
    assert groups["one"].bybitPnlUsdt == groups["two"].bybitPnlUsdt == Decimal("10")
    assert result.totalPnlUsdt == Decimal("-0.6")


def test_partial_close_values_remaining_quantity_and_full_close_leaves_aggregate():
    add_group("partial", quantity="2")
    with connection() as db:
        db.execute("UPDATE cross_spread_exit_plans SET quantity_oz='0.5' WHERE id='partial'")
    snapshot = market(positions=[mt5_position("partial", size="-0.005", pnl="-5.1")])
    result = overview(snapshot)
    assert result.groups[0].bybitPnlUsdt == Decimal("5")
    assert result.totalPnlUsdt == Decimal("-0.1")
    with connection() as db:
        db.execute(
            "UPDATE cross_spread_exit_plans SET status='closed',quantity_oz='0' WHERE id='partial'"
        )
    assert overview(snapshot).groups == []
    assert overview(snapshot).totalPnlUsdt == 0


def test_native_component_fills_replace_confirmation_and_compute_weighted_entry_once():
    add_group("weighted", quantity="2", bybit_price="999")
    with connection() as db:
        for key, size, price in [("a", "0.5", "90"), ("b", "1.5", "100")]:
            payload = {
                "source": "bybit_live",
                "externalFillId": key,
                "externalOrderId": "weighted:bybit_leg",
                "platformOrderId": "weighted:bybit_leg",
                "accountId": BYBIT,
                "instrumentId": "instrument_xau_usdt_perp",
                "symbol": "XAUTUSDT",
                "side": "buy",
                "quantity": size,
                "price": price,
                "fee": "0",
                "currency": "USDT",
                "occurredAt": datetime.now(UTC).isoformat(),
            }
            _persist_venue_event(db, BYBIT, "trade_fill", payload)
            _persist_venue_event(db, BYBIT, "trade_fill", payload)
    snapshot = market(positions=[mt5_position("weighted", size="-0.02", pnl="-20.4")])
    first = overview(snapshot)
    assert first.groups[0].bybitEntryPrice == Decimal("97.5")
    assert first.bybitPnlUsdt == Decimal("25")
    assert overview(snapshot).model_dump() == first.model_dump()


@pytest.mark.parametrize(
    "currency,fx,expected",
    [
        ("USDT", None, Decimal("8")),
        ("USD", "0.8", Decimal("10")),
        ("USD", None, None),
        ("EUR", "1", None),
        (None, "1", None),
    ],
)
def test_mt5_profit_uses_native_settlement_currency_and_never_assumes_usdt_usd_parity(
    currency, fx, expected
):
    add_group("currency")
    result = overview(
        market(fx=fx, positions=[mt5_position("currency", pnl="8", currency=currency)])
    )
    assert result.mt5PnlUsdt == expected
    assert result.totalPnlUsdt == (Decimal("10") + expected if expected is not None else None)


@pytest.mark.parametrize("defect", ["ticket", "account", "quantity", "cost", "stale", "profit"])
def test_one_missing_mt5_leg_does_not_publish_a_partial_sum_as_the_total(defect):
    add_group("valid")
    add_group("invalid")
    bad = mt5_position("invalid")
    if defect == "ticket":
        bad["externalId"] = "different-ticket"
    if defect == "account":
        bad["accountId"] = "monitor-only"
    if defect == "quantity":
        bad["quantity"] = "-0.02"
    if defect == "cost":
        bad["averagePrice"] = "999"
    if defect == "stale":
        bad["asOf"] = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()
    if defect == "profit":
        bad["unrealizedPnl"] = None
    result = overview(market(positions=[mt5_position("valid"), bad]))
    groups = {row.planId: row for row in result.groups}
    assert groups["valid"].totalPnlUsdt == Decimal("-0.2")
    assert groups["invalid"].totalPnlUsdt is None
    assert result.bybitPnlUsdt == Decimal("20")
    assert result.mt5PnlUsdt is None and result.totalPnlUsdt is None
    assert result.dataQualityState == "partial"


def test_stale_quote_clears_pnl_without_reusing_prior_snapshot_valuation():
    add_group("stale")
    snapshot = market(positions=[mt5_position("stale")])
    assert overview(snapshot).totalPnlUsdt is not None
    snapshot.bybit.as_of = datetime.now(UTC) - timedelta(minutes=2)
    result = overview(snapshot)
    assert result.bybitPnlUsdt is None and result.totalPnlUsdt is None
    assert result.mt5PnlUsdt == Decimal("-10.2")


def test_corrupt_fills_block_only_the_affected_group_without_writing_financial_facts():
    add_group("good")
    add_group("bad")
    with connection() as db:
        db.execute("UPDATE fills SET quantity='2' WHERE id='bad:bybit_leg'")
        before = {
            table: db.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
            for table in (
                "orders",
                "fills",
                "trade_commands",
                "cross_spread_exit_plans",
                "financial_facts",
            )
        }
    result = overview(market(positions=[mt5_position("good"), mt5_position("bad")]))
    groups = {row.planId: row for row in result.groups}
    assert groups["good"].totalPnlUsdt == Decimal("-0.2")
    assert groups["bad"].totalPnlUsdt is None
    assert result.totalPnlUsdt is None
    with connection() as db:
        for table, rows in before.items():
            assert db.execute(f"SELECT * FROM {table} ORDER BY id").fetchall() == rows


def test_decimal_totals_preserve_values_larger_than_display_precision():
    add_group("precise", bybit_price="100")
    result = overview(
        market(
            bid="2100.123456789123456789",
            ask="2100.2",
            positions=[
                mt5_position("precise", pnl="-2000.12"),
            ],
        )
    )
    assert result.bybitPnlUsdt == Decimal("2000.123456789123456789")
    assert result.totalPnlUsdt == Decimal("0.003456789123456789")
    assert result.model_dump(mode="json")["bybitPnlUsdt"] == "2000.123456789123456789"
