import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.database import connection, initialize_database
from app.live_venue_snapshot_sync import _persist_fills, _persist_orders, _persist_venue_event
from app.schemas import CreateOrderRequest
from app.strategy_financial_readmodel import (
    batch_fee_totals,
    canonical_fills,
    funding_spot_cash,
    get_strategy_financials,
)
from app.trading import record_fill_and_update_operational_projections

ACCOUNT = "bybit-live-main"
INSTRUMENT = "instrument_xau_usdt_perp"
FUNDING = "strategy_funding_arbitrage_instance_default"
CROSS = "strategy_cross_venue_spread_instance_default"
NOW = datetime.now(UTC).isoformat()


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path / "identity.db"))
    initialize_database()


def receipt(**changes):
    return {
        "source": "bybit_live",
        "externalOrderId": "native-order",
        "externalFillId": "native-fill",
        "platformOrderId": "external:old-alias",
        "accountId": ACCOUNT,
        "instrumentId": INSTRUMENT,
        "symbol": "XAUTUSDT",
        "side": "buy",
        "quantity": "1",
        "price": "2000",
        "fee": "0.2",
        "currency": "USDT",
        "occurredAt": NOW,
        **changes,
    }


def persisted_order(identity, *, strategy=None, instrument=INSTRUMENT, quantity="1"):
    with connection() as db:
        if strategy:
            db.execute(
                "INSERT INTO trade_commands (id,idempotency_key,strategy_instance_id,account_id,"
                "instrument_id,command_type,side,order_type,quantity,status,created_at,updated_at) "
                "VALUES (?,?,?,?,?,'create_order','buy','market',?,'filled',?,?)",
                (identity, identity, strategy, ACCOUNT, instrument, quantity, NOW, NOW),
            )
        db.execute(
            "INSERT INTO orders (id,command_id,account_id,instrument_id,symbol,side,order_type,"
            "quantity,status,external_order_id,created_at,updated_at) "
            "VALUES (?,?,?,?, 'XAUTUSDT','buy','market',?,'filled','native-order',?,?)",
            (identity, identity, ACCOUNT, instrument, quantity, NOW, NOW),
        )


def operational_fill(identity, order_id, quantity="1"):
    with connection() as db:
        db.execute(
            "INSERT INTO fills "
            "(id,order_id,account_id,instrument_id,side,quantity,price,occurred_at) "
            "VALUES (?,?,?,?,'buy',?,'2000',?)",
            (identity, order_id, ACCOUNT, INSTRUMENT, quantity, NOW),
        )


def test_same_native_tickets_in_two_accounts_are_distinct_and_replay_once():
    from app.venue_identity_repository import load_order_identities

    with connection() as db:
        for account in ("mt5-live-main", "account_mt5_short_term_a"):
            fill = receipt(source="mt5_live", accountId=account, instrumentId="instrument_xau_usd")
            assert _persist_fills(db, account, [fill])[0] == 1
            assert _persist_fills(db, account, [fill])[0] == 0
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 2
        identities = load_order_identities(db, account_ids=["mt5-live-main"])
        assert len(identities.rows) == 1
        assert all(row["account_id"] == "mt5-live-main" for row in identities.rows.values())
        assert load_order_identities(db, account_ids=[]).rows == {}


def test_account_scope_keeps_competing_native_order_owners_fail_closed():
    from app.strategy_financial_readmodel import _native_fills_for_orders

    persisted_order("owned-first", strategy=CROSS)
    persisted_order("owned-second", strategy=FUNDING)
    with connection() as db:
        assert _native_fills_for_orders(db, {"owned-first"}) is None


def test_late_alias_uses_command_owner_without_rewriting_original_records():
    persisted_order("external:old-alias")
    operational_fill("old-monitor-fill", "external:old-alias")
    original = receipt()
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", original)
    persisted_order("owned", strategy=FUNDING)
    operational_fill("runtime-confirmation", "owned")
    with connection() as db:
        _persist_orders(db, ACCOUNT, [receipt(platformOrderId="external:new-alias", asOf=NOW)])
        _persist_fills(db, ACCOUNT, [receipt(platformOrderId="external:new-alias")])
    strategy = get_strategy_financials(FUNDING)
    account = get_strategy_financials(FUNDING, account_id=ACCOUNT, account_scope=True)
    assert Decimal(strategy["fees"]) == Decimal("0.2")
    assert Decimal(strategy["positions"][0]["netQuantity"]) == Decimal("1")
    assert Decimal(account["positions"][0]["netQuantity"]) == Decimal("1")
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 2
        assert db.execute("SELECT platform_order_id FROM venue_account_events").fetchone()[0] == (
            "external:old-alias"
        )


def test_native_order_number_is_scoped_by_instrument_for_shared_strategy_account():
    persisted_order("funding", strategy=FUNDING)
    persisted_order("cross", strategy=CROSS, instrument="instrument_btc_usdt")
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", receipt(platformOrderId="external:late"))
    result = get_strategy_financials(FUNDING)
    assert result["fees"] == "0.2"
    assert get_strategy_financials(CROSS)["fees"] == "0"


@pytest.mark.parametrize(
    "field,value",
    [
        ("externalOrderId", "different-order"),
        ("instrumentId", "instrument_btc_usdt"),
        ("positionId", "different-ticket"),
        ("quantity", "2"),
    ],
)
def test_replayed_native_event_cannot_change_identity_or_financial_facts(field, value):
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", receipt())
        with pytest.raises(ValueError):
            _persist_venue_event(db, ACCOUNT, "trade_fill", receipt(**{field: value}))


def test_monitoring_components_do_not_advance_partial_operational_confirmation():
    persisted_order("owned", strategy=FUNDING)
    operational_fill("runtime-partial", "owned", "0.4")
    with connection() as db:
        for fill_id in ("component-a", "component-b"):
            fill = receipt(platformOrderId="owned", externalFillId=fill_id, quantity="0.2")
            assert _persist_fills(db, ACCOUNT, [fill])[0] == 0
            _persist_venue_event(db, ACCOUNT, "trade_fill", fill)
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 1
    result = get_strategy_financials(FUNDING)
    assert Decimal(result["positions"][0]["netQuantity"]) == Decimal("0.4")


def test_fill_read_uses_native_components_once_and_keeps_fee_precision():
    from app.catalog import list_fills

    persisted_order("owned", strategy=CROSS)
    operational_fill("runtime-confirmation", "owned")
    with connection() as db:
        for identity, fee in (("component-a", "0.000000000000000123"), ("component-b", "-0.002")):
            _persist_venue_event(
                db,
                ACCOUNT,
                "trade_fill",
                receipt(platformOrderId="owned", externalFillId=identity, quantity="0.5", fee=fee),
            )
    rows = list_fills(CROSS)
    assert len(rows) == 2
    assert sum(row.quantity for row in rows) == Decimal("1")
    assert {row.external_fill_id for row in rows} == {"component-a", "component-b"}
    assert {row.fee for row in rows} == {Decimal("0.000000000000000123"), Decimal("-0.002")}
    assert all(row.origin == "venue_execution" and row.order_id == "owned" for row in rows)
    assert all(row.currency == "USDT" for row in rows)
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 1


def test_partial_native_fill_is_readable_without_advancing_an_acknowledged_command():
    from app.catalog import list_fills

    persisted_order("owned", strategy=CROSS)
    with connection() as db:
        db.execute("UPDATE orders SET status='acknowledged' WHERE id='owned'")
        db.execute("UPDATE trade_commands SET status='acknowledged' WHERE id='owned'")
        _persist_venue_event(
            db,
            ACCOUNT,
            "trade_fill",
            receipt(platformOrderId="owned", quantity="0.4", fee=None),
        )
    first = list_fills(CROSS)
    second = list_fills(CROSS)
    assert first == second
    assert len(first) == 1 and first[0].quantity == Decimal("0.4")
    assert first[0].fee is None
    assert get_strategy_financials(CROSS)["fees"] is None
    with connection() as db:
        assert (
            db.execute("SELECT status FROM orders WHERE id='owned'").fetchone()[0] == "acknowledged"
        )
        assert (
            db.execute("SELECT status FROM trade_commands WHERE id='owned'").fetchone()[0]
            == "acknowledged"
        )
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 0


def test_fill_read_follows_late_alias_without_leaking_to_another_strategy():
    from app.catalog import list_fills

    persisted_order("external:old-alias")
    operational_fill("old-fill", "external:old-alias")
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", receipt())
    persisted_order("owned", strategy=CROSS)
    operational_fill("confirmation", "owned")
    rows = list_fills(CROSS)
    assert len(rows) == 1
    assert rows[0].order_id == "owned"
    assert rows[0].external_fill_id == "native-fill"
    assert list_fills(FUNDING) == []


def test_native_overfill_remains_visible_without_increasing_executable_quantity():
    persisted_order("owned", strategy=FUNDING)
    operational_fill("runtime-confirmation", "owned")
    with connection() as db:
        fill = receipt(platformOrderId="owned", quantity="1.1")
        _persist_fills(db, ACCOUNT, [fill])
        _persist_venue_event(db, ACCOUNT, "trade_fill", fill)
        assert db.execute("SELECT quantity FROM fills").fetchone()[0] == "1"
    result = get_strategy_financials(FUNDING)
    assert Decimal(result["positions"][0]["netQuantity"]) == Decimal("1.1")
    assert "venue_fill_quantity_exceeds_order" in result["issues"]


def test_ambiguous_command_ownership_stays_unattributed_and_blocks_snapshot_projection():
    persisted_order("first", strategy=FUNDING)
    persisted_order("second", strategy=CROSS)
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", receipt())
        with pytest.raises(ValueError, match="multiple command owners"):
            _persist_orders(db, ACCOUNT, [receipt(asOf=NOW)])
    for strategy in (FUNDING, CROSS):
        result = get_strategy_financials(strategy)
        assert result["fees"] is None
        assert result["positions"] == []
        assert "venue_order_identity_conflict" in result["issues"]


def test_snapshot_cannot_resolve_unknown_command_or_increase_its_executable_quantity():
    persisted_order("unknown", strategy=FUNDING)
    with connection() as db:
        db.execute("UPDATE orders SET status='result_unknown' WHERE id='unknown'")
        _persist_orders(
            db, ACCOUNT, [receipt(platformOrderId="unknown", status="filled", asOf=NOW)]
        )
        _persist_fills(db, ACCOUNT, [receipt(platformOrderId="unknown")])
        assert db.execute("SELECT status FROM orders WHERE id='unknown'").fetchone()[0] == (
            "result_unknown"
        )
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 0


def test_equivalent_receipt_replay_keeps_legacy_fill_id_and_original_payload():
    persisted_order("external:old-alias")
    operational_fill("native-fill", "external:old-alias")
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", receipt())
        original = db.execute("SELECT payload_json FROM venue_account_events").fetchone()[0]
        replay = receipt(
            platformOrderId="external:new-alias",
            quantity="1.000",
            price="2000.0",
            occurredAt=NOW.replace("+00:00", "Z"),
        )
        assert _persist_fills(db, ACCOUNT, [replay])[0] == 0
        _persist_venue_event(db, ACCOUNT, "trade_fill", replay)
        assert db.execute("SELECT id FROM fills").fetchone()[0] == "native-fill"
        assert db.execute("SELECT payload_json FROM venue_account_events").fetchone()[0] == original


def test_replayed_monitor_fill_rejects_changed_price():
    with connection() as db:
        _persist_fills(db, ACCOUNT, [receipt()])
        with pytest.raises(ValueError, match="financial data"):
            _persist_fills(db, ACCOUNT, [receipt(price="1999")])


def test_fee_and_spot_close_cash_follow_late_native_order_mapping():
    persisted_order("spot", strategy=FUNDING, instrument="instrument_btc_usdt")
    with connection() as db:
        db.execute(
            "INSERT INTO execution_batches "
            "(id,account_id,strategy_key,direction,status,created_at,updated_at) "
            "VALUES ('batch',?,'funding_arbitrage','open','hedged',?,?)",
            (ACCOUNT, NOW, NOW),
        )
        db.execute(
            "INSERT INTO funding_spot_release_commands "
            "(child_id,batch_id,cumulative_perpetual_fill,release_quantity,"
            "cumulative_spot_quantity,order_id,status,created_at,updated_at) "
            "VALUES ('child','batch','1','1','1','spot','filled',?,?)",
            (NOW, NOW),
        )
        _persist_venue_event(
            db,
            ACCOUNT,
            "trade_fill",
            receipt(
                instrumentId="instrument_btc_usdt",
                symbol="BTCUSDT",
                currency="BTC",
                fee="0.001",
            ),
        )
    assert funding_spot_cash("batch", Decimal("1")) == Decimal("0.999")
    assert funding_spot_cash("batch", Decimal("2")) is None
    assert batch_fee_totals("batch") == (None, Decimal("2.000"))


def test_external_monitor_order_retains_all_native_partial_executions():
    with connection() as db:
        for identity, quantity in (("first", "0.3"), ("second", "0.7")):
            fill = receipt(externalFillId=identity, quantity=quantity)
            _persist_fills(db, ACCOUNT, [fill])
            _persist_venue_event(db, ACCOUNT, "trade_fill", fill)
        assert [
            tuple(row)
            for row in db.execute(
                "SELECT origin,source,external_fill_id FROM fills ORDER BY external_fill_id"
            )
        ] == [
            ("venue_execution", "bybit_live", "first"),
            ("venue_execution", "bybit_live", "second"),
        ]
    result = get_strategy_financials(FUNDING, account_id=ACCOUNT, account_scope=True)
    assert Decimal(result["positions"][0]["netQuantity"]) == Decimal("1")
    assert "venue_fill_quantity_exceeds_order" not in result["issues"]


def test_known_native_provenance_never_uses_full_quantity_row_to_hide_an_extra_fill():
    rows = [
        {
            "fill_id": identity,
            "order_id": "order",
            "quantity": quantity,
            "requested_quantity": "1",
            "occurred_at": NOW,
            "origin": "venue_execution",
        }
        for identity, quantity in (("first", "1"), ("extra", "0.1"))
    ]
    with pytest.raises(ValueError, match="quantity is inconsistent"):
        canonical_fills(rows)


def test_runtime_confirmation_records_provenance_and_keeps_replay_and_ceiling_guards():
    persisted_order("owned", strategy=FUNDING)
    request = CreateOrderRequest(
        accountId=ACCOUNT,
        instrumentId=INSTRUMENT,
        symbol="XAUTUSDT",
        side="buy",
        orderType="market",
        quantity="1",
    )
    values = {
        "fill_id": "runtime-event",
        "order_id": "owned",
        "request": request,
        "fill_price": Decimal("2000"),
        "fill_quantity": Decimal("0.4"),
        "occurred_at": NOW,
    }
    assert record_fill_and_update_operational_projections(**values)
    assert not record_fill_and_update_operational_projections(**values)
    with pytest.raises(HTTPException, match="Cumulative fill quantity"):
        record_fill_and_update_operational_projections(
            **{**values, "fill_id": "too-large", "fill_quantity": Decimal("0.7")}
        )
    with connection() as db:
        assert tuple(
            db.execute("SELECT origin,source,external_fill_id,quantity FROM fills").fetchone()
        ) == ("runtime_confirmation", "runtime_v1", None, "0.4")


def test_native_time_does_not_rewrite_or_conflict_with_legacy_confirmation_time():
    persisted_order("owned", strategy=FUNDING)
    operational_fill("native-fill", "owned")
    native = receipt(platformOrderId="owned")
    with connection() as db:
        db.execute("UPDATE fills SET occurred_at='2026-09-01T00:00:00+00:00'")
        assert _persist_fills(db, ACCOUNT, [native])[0] == 0
        _persist_venue_event(db, ACCOUNT, "trade_fill", native)
        _persist_venue_event(db, ACCOUNT, "trade_fill", native)
        with pytest.raises(ValueError, match="different financial data"):
            _persist_venue_event(db, ACCOUNT, "trade_fill", {**native, "price": "2100"})
        assert db.execute("SELECT occurred_at FROM fills").fetchone()[0] == (
            "2026-09-01T00:00:00+00:00"
        )


def test_monitor_instrument_alias_resolves_to_owned_market_without_rewriting_receipt():
    alias = f"monitor:bybit:{ACCOUNT}:linear:XAUTUSDT"
    old = receipt(instrumentId=alias)
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", old)
    persisted_order("owned", strategy=CROSS)
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", receipt(platformOrderId="owned"))
        assert (
            json.loads(db.execute("SELECT payload_json FROM venue_account_events").fetchone()[0])
            == old
        )
        assert db.execute("SELECT COUNT(*) FROM venue_account_events").fetchone()[0] == 1
    assert get_strategy_financials(CROSS)["fees"] == "0.2"


@pytest.mark.parametrize(
    "alias",
    [
        f"monitor:bybit:{ACCOUNT}:spot:XAUTUSDT",
        f"monitor:bybit:{ACCOUNT}:inverse:XAUTUSDT",
        "monitor:bybit:another-account:linear:XAUTUSDT",
    ],
)
def test_monitor_alias_cannot_cross_account_or_market(alias):
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", receipt())
        with pytest.raises(ValueError):
            _persist_venue_event(db, ACCOUNT, "trade_fill", receipt(instrumentId=alias))


@pytest.mark.parametrize("accept,changed", [(True, False), (False, False), (True, True)])
def test_native_time_correction_requires_exact_accepted_evidence(accept, changed):
    from app.catalog import list_fills
    from app.venue_reconciliation_repository import (
        create_account_snapshot_run,
        ensure_schema,
        resolve_difference_row,
        store_difference,
    )

    persisted_order("owned", strategy=CROSS)
    old = receipt(platformOrderId="owned", occurredAt="2026-09-01T01:00:00Z")
    new = {**old, "occurredAt": "2026-09-01T04:00:00Z"}
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, "trade_fill", old)
    ensure_schema()
    create_account_snapshot_run(
        run_id="timestamp-review",
        idempotency_key="timestamp-review",
        payload_hash="proof",
        strategy_instance_id=CROSS,
        account_id=ACCOUNT,
        source="bybit_live",
        position_count=0,
        balance_count=0,
        started_at=NOW,
    )
    correction = {**new, "price": "2001"} if changed else new
    identity = store_difference(
        "timestamp-review",
        "fill-time",
        "timestamp_mismatch",
        "venue_event",
        "native-fill",
        "trade_fill:native-fill",
        old,
        correction,
    )
    if accept:
        resolve_difference_row(
            difference_id=identity,
            status="accepted",
            actor="owner",
            reason="Review source epoch",
            resolved_at=NOW,
        )
    with connection() as db:
        if accept and not changed:
            _persist_venue_event(db, ACCOUNT, "trade_fill", new)
            _persist_venue_event(db, ACCOUNT, "trade_fill", new)
            with pytest.raises(ValueError, match="occurrence time"):
                _persist_venue_event(db, ACCOUNT, "trade_fill", {**new, "occurredAt": NOW})
        else:
            with pytest.raises(ValueError):
                _persist_venue_event(db, ACCOUNT, "trade_fill", new)
        assert (
            json.loads(db.execute("SELECT payload_json FROM venue_account_events").fetchone()[0])
            == old
        )
    if accept and not changed:
        assert list_fills(CROSS)[0].occurred_at == datetime(2026, 9, 1, 4, tzinfo=UTC)
        from app.strategy_financial_readmodel import _native_fills_for_orders

        with connection() as db:
            rows = _native_fills_for_orders(db, {"owned"})
        assert rows and json.loads(rows[0]["payload_json"])["occurredAt"] == new["occurredAt"]


def test_native_fee_read_batches_correction_queries_without_caching_receipts():
    from app.strategy_financial_readmodel import _native_fills_for_orders
    from app.venue_reconciliation_repository import ensure_schema

    persisted_order("owned", strategy=CROSS, quantity="50")
    ensure_schema()
    with connection() as db:
        for index in range(50):
            _persist_venue_event(db, ACCOUNT, "trade_fill", receipt(
                platformOrderId="owned", externalFillId=f"fill-{index}"
            ))
    with connection() as db:
        queries = []
        db.set_trace_callback(queries.append)
        rows = _native_fills_for_orders(db, {"owned"})
        assert rows is not None and len(rows) == 50
        assert len(queries) <= 8  # Independent of historical fill count.
        db.set_trace_callback(None)
        _persist_venue_event(db, ACCOUNT, "trade_fill", receipt(
            platformOrderId="owned", externalFillId="new-fill", fee="0.123456789"
        ))
        latest = _native_fills_for_orders(db, {"owned"})
        assert latest is not None and len(latest) == 51
        assert any(json.loads(row["payload_json"])["fee"] == "0.123456789" for row in latest)


@pytest.mark.parametrize(
    "origin,quantity,quality",
    [
        ("runtime_confirmation", "1", "source_clock_conflict"),
        ("runtime_confirmation", "0.4", "source_clock_unverified"),
        ("legacy", "1", "source_clock_unverified"),
    ],
)
def test_management_time_requires_full_confirmation(origin, quantity, quality):
    from datetime import timedelta

    from app.catalog import list_fills

    persisted_order("owned", strategy=CROSS)
    operational_fill("confirmation", "owned", quantity)
    future = (datetime.fromisoformat(NOW) + timedelta(hours=3)).isoformat()
    with connection() as db:
        db.execute("UPDATE fills SET origin=? WHERE id='confirmation'", (origin,))
        _persist_venue_event(
            db,
            ACCOUNT,
            "trade_fill",
            receipt(
                source="mt5_live",
                platformOrderId="owned",
                occurredAt=future,
            ),
        )
        original = db.execute("SELECT payload_json FROM venue_account_events").fetchone()[0]
    rows = list_fills(CROSS)
    assert len(rows) == 1
    assert rows[0].occurred_at == datetime.fromisoformat(future)
    assert rows[0].time_quality == quality
    assert rows[0].order_confirmed_at == (
        datetime.fromisoformat(NOW) if quality == "source_clock_conflict" else None
    )
    assert list_fills(CROSS) == rows
    with connection() as db:
        assert db.execute("SELECT payload_json FROM venue_account_events").fetchone()[0] == original
        assert db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 1


def test_management_orders_canonicalize_before_limit_and_keep_known_intent():
    from app.catalog import get_order, list_orders

    persisted_order("external:old-alias")
    persisted_order("owned", strategy=CROSS)
    with connection() as db:
        db.execute(
            "INSERT INTO execution_batches "
            "(id,account_id,strategy_key,direction,status,created_at,updated_at) "
            "VALUES ('batch',?,'cross_venue_spread','CLOSE_LONG_SPREAD','hedged',?,?)",
            (ACCOUNT, NOW, NOW),
        )
        db.execute(
            "INSERT INTO execution_batch_legs "
            "(id,batch_id,role,sequence,account_id,instrument_id,symbol,side,order_type,"
            "quantity,status,order_id,created_at,updated_at) "
            "VALUES ('leg','batch','bybit',1,?,?,'XAUTUSDT','buy','market',"
            "'1','filled','owned',?,?)",
            (ACCOUNT, INSTRUMENT, NOW, NOW),
        )
    rows = list_orders(account_id=ACCOUNT, limit=1)
    assert len(rows) == 1 and rows[0].order_id == "owned"
    assert rows[0].action == "close"  # Buy alone cannot distinguish opening from closing.
    assert rows[0].time_quality == "platform_submission"
    assert get_order("owned").action == "close"
    assert len(list_orders(account_id=ACCOUNT)) == 1
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 2


def test_management_orders_fail_closed_on_ambiguous_ownership():
    from app.catalog import list_orders

    persisted_order("first", strategy=CROSS)
    persisted_order("second", strategy=FUNDING)
    with pytest.raises(HTTPException) as caught:
        list_orders(CROSS)
    assert caught.value.status_code == 409


@pytest.mark.parametrize("reduce_only,expected", [(True, "close"), (False, None)])
def test_monitor_order_uses_explicit_reduce_only_and_never_infers_open(reduce_only, expected):
    from app.catalog import list_orders

    persisted_order("monitor")
    with connection() as db:
        db.execute(
            "UPDATE orders SET venue_payload_json=? WHERE id='monitor'",
            (json.dumps({"reduceOnly": reduce_only}),),
        )
    assert list_orders(account_id=ACCOUNT)[0].action == expected


@pytest.mark.parametrize(
    "entry,expected", [(0, "open"), (1, "close"), (2, "reverse"), (3, "close"), (None, None)]
)
def test_mt5_monitor_records_use_native_entry_and_keep_account_scope(entry, expected):
    from app.catalog import list_fills, list_orders

    persisted_order("monitor")
    with connection() as db:
        _persist_venue_event(
            db,
            ACCOUNT,
            "trade_fill",
            receipt(
                source="mt5_live",
                platformOrderId="monitor",
                entryType=entry,
            ),
        )
    assert list_fills(account_id=ACCOUNT)[0].action == expected
    assert list_orders(account_id=ACCOUNT)[0].action == expected
    assert list_fills(CROSS) == []
