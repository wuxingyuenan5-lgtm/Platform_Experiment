import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.database import connection, initialize_database
from app.live_venue_snapshot_sync import _persist_venue_event, _persist_venue_snapshot
from app.strategy_financial_readmodel import (
    batch_fee_totals,
    funding_spot_cash,
    get_strategy_financials,
)

FUNDING = "strategy_funding_arbitrage_instance_default"
CROSS = "strategy_cross_venue_spread_instance_default"
ACCOUNT = "bybit-live-main"
INSTRUMENT = "instrument_xau_usdt_perp"
NOW = datetime.now(UTC).isoformat()


@pytest.fixture(autouse=True)
def database(tmp_path):
    get_settings().database_path = str(tmp_path / "finance.db")
    initialize_database()


def order(identity, strategy, side, quantity, price):
    with connection() as db:
        db.execute(
            "INSERT INTO trade_commands (id,idempotency_key,strategy_instance_id,account_id,"
            "instrument_id,command_type,side,order_type,quantity,status,created_at,updated_at) "
            "VALUES (?,?,?,?,?,'create_order',?,'market',?,'filled',?,?)",
            (identity, identity, strategy, ACCOUNT, INSTRUMENT, side, quantity, NOW, NOW),
        )
        db.execute(
            "INSERT INTO orders (id,command_id,account_id,instrument_id,symbol,side,order_type,"
            "quantity,status,external_order_id,created_at,updated_at) "
            "VALUES (?,?,?,?, 'XAUTUSDT',?,'market',?,'filled',?,?,?)",
            (identity, identity, ACCOUNT, INSTRUMENT, side, quantity, identity, NOW, NOW),
        )
        db.execute(
            "INSERT INTO fills "
            "(id,order_id,account_id,instrument_id,side,quantity,price,occurred_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (identity, identity, ACCOUNT, INSTRUMENT, side, quantity, price, NOW),
        )


def test_account_daily_closings_and_amounts_follow_beijing_midnight():
    from app.catalog import get_strategy_account_snapshot

    with connection() as db:
        for at, equity in [
            ("2026-09-01T15:59:59+00:00", "100"),
            ("2026-09-01T16:00:00+00:00", "101"),
            ("2026-09-02T15:59:59+00:00", "105"),
            ("2026-09-02T16:00:00+00:00", "108"),
        ]:
            db.execute(
                "INSERT INTO account_risk_snapshots(account_id,as_of,currency,equity,"
                "asset_scope,data_quality_state,created_at,payload_json) "
                "VALUES (?,?,'USDT',?,'unified_trading','complete',?,'{}')",
                (ACCOUNT, at, equity, at),
            )
        db.execute(
            "INSERT INTO account_capital_coverage VALUES(?, 'unified_trading',?,?,?)",
            (ACCOUNT, "2026-09-01T00:00:00+00:00", "2026-09-03T00:00:00+00:00", NOW),
        )
    result = get_strategy_account_snapshot(FUNDING, account_id=ACCOUNT, include_details=False)
    daily = result.model_dump(by_alias=True, mode="json")["dailyPnl"]
    assert [(p["date"], p["equityClose"]) for p in daily] == [
        ("2026-09-01", "100"), ("2026-09-02", "105"), ("2026-09-03", "108")
    ]
    assert [p["pnl"] for p in daily] == [None, "5", "3"]


def fill(identity, order_id, quantity, price, fee, currency="USDT"):
    with connection() as db:
        _persist_venue_event(
            db,
            ACCOUNT,
            "trade_fill",
            {
                "source": "bybit_live",
                "externalFillId": identity,
                "platformOrderId": order_id,
                "externalOrderId": order_id,
                "accountId": ACCOUNT,
                "instrumentId": INSTRUMENT,
                "symbol": "XAUTUSDT",
                "side": "buy",
                "quantity": quantity,
                "price": price,
                "fee": fee,
                "currency": currency,
                "occurredAt": NOW,
            },
        )


def test_shared_account_same_symbol_does_not_leak_position_or_fees():
    order("a", FUNDING, "buy", "1", "2000")
    order("b", CROSS, "buy", "3", "2500")
    fill("fa", "a", "1", "2000", "0.20")
    fill("fb", "b", "3", "2500", "9")
    result = get_strategy_financials(FUNDING)
    assert result["fees"] == "0.20"
    assert result["positions"][0]["netQuantity"] == "1"
    assert result["positions"][0]["averagePrice"] == "2000"
    assert result["tradingPnl"] is None  # No authoritative mark, never account UPL.


def test_native_realized_cashflow_matches_trade_id_without_double_counting():
    order("a", CROSS, "buy", "1", "2000")
    fill("native-a", "a", "1", "2000", "0.2")
    with connection() as db:
        _persist_venue_event(
            db,
            ACCOUNT,
            "realized_pnl",
            {
                "source": "bybit_live",
                "externalEventId": "cash-a",
                "eventType": "realized_pnl",
                "accountId": ACCOUNT,
                "externalOrderId": "a",
                "instrumentId": INSTRUMENT,
                "amount": "7.25",
                "currency": "USDT",
                "occurredAt": NOW,
                "payload": {"tradeId": "native-a"},
            },
        )
    result = get_strategy_financials(CROSS)
    assert Decimal(result["realizedPnl"]) == Decimal("7.25")
    assert Decimal(result["fees"]) == Decimal("0.2")


def test_native_fill_gap_backfill_paginates_and_is_idempotent(monkeypatch):
    from app import account_history_sync

    order("a", CROSS, "buy", "1", "2000")
    calls = []

    def read(path, params):
        calls.append(dict(params))
        index = 2 if params.get("cursor") else 1
        item = {
            "source": "bybit_live",
            "externalFillId": f"native-{index}",
            "externalOrderId": "a",
            "accountId": ACCOUNT,
            "instrumentId": INSTRUMENT,
            "symbol": "XAUTUSDT",
            "side": "buy",
            "quantity": "0.5",
            "price": "2000",
            "fee": "0.1",
            "currency": "USDT",
            "occurredAt": NOW,
        }

        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "accountId": ACCOUNT,
                    "items": [item],
                    "nextCursor": "next" if index == 1 else None,
                }

        return Response()

    monkeypatch.setattr(account_history_sync, "runtime_get", read)
    assert account_history_sync.backfill_missing_native_fills(ACCOUNT) == 2
    assert account_history_sync.backfill_missing_native_fills(ACCOUNT) == 0
    assert len(calls) == 2


def test_component_fills_replace_operational_aggregate_once_and_preserve_rebate():
    order("a", FUNDING, "buy", "1", "2000")
    fill("fa", "a", "0.4", "1900", "0.1")
    fill("fb", "a", "0.6", "2100", "-0.02")
    result = get_strategy_financials(FUNDING)
    assert Decimal(result["fees"]) == Decimal("0.08")
    assert Decimal(result["positions"][0]["averagePrice"]) == Decimal("2020")
    assert Decimal(result["positions"][0]["netQuantity"]) == Decimal("1")


def test_unassigned_funding_and_foreign_currency_are_not_fabricated_totals():
    order("a", FUNDING, "buy", "1", "2000")
    fill("fa", "a", "1", "2000", "0.1", "USD")
    with connection() as db:
        _persist_venue_event(
            db,
            ACCOUNT,
            "funding",
            {
                "source": "bybit_live",
                "externalEventId": "funding:1",
                "eventType": "funding",
                "accountId": ACCOUNT,
                "instrumentId": INSTRUMENT,
                "amount": "8",
                "currency": "USDT",
                "occurredAt": NOW,
            },
        )
    result = get_strategy_financials(FUNDING)
    assert result["fees"] is None
    assert result["unattributedEvents"][0]["amount"] == "8"
    assert "historical_fx_unavailable" in result["issues"]
    assert "unattributed_economic_events" in result["issues"]
    assert result["fundingPnl"] is None
    account = get_strategy_financials(FUNDING, account_id=ACCOUNT, account_scope=True)
    assert account["fundingPnl"] == "8"  # Preserve the receipt at its proven account scope.


@pytest.mark.parametrize("offset", [-2592000, -301, -300, 0, 300, 301, 2592000])
def test_historical_fx_requires_nearby_valuation_and_preserves_native_fee(offset):
    order("fx", FUNDING, "buy", "1", "2000")
    fill("fx-fill", "fx", "1", "2000", "1", "USD")
    observed = (datetime.fromisoformat(NOW) + timedelta(seconds=offset)).isoformat()
    with connection() as db:
        db.executemany(
            "INSERT INTO account_valuation_rates (account_id,currency,as_of,usd_rate) "
            "VALUES (?,?,?,?)",
            [(ACCOUNT, "USD", observed, "1"), (ACCOUNT, "USDT", observed, "0.5")],
        )
    result = get_strategy_financials(FUNDING)
    if abs(offset) <= 300:
        assert Decimal(result["fees"]) == Decimal("2")
        assert "historical_fx_unavailable" not in result["issues"]
    else:
        assert result["fees"] is None
        assert "historical_fx_unavailable" in result["issues"]
    native = next(row for row in result["byCurrency"] if row["currency"] == "USD")
    assert Decimal(native["fees"]) == Decimal("1")


@pytest.mark.parametrize("outside_exposure", ["before_open", "after_close"])
def test_instrument_history_does_not_assign_settlement_outside_position(outside_exposure):
    order("open", FUNDING, "buy", "1", "2000")
    if outside_exposure == "after_close":
        order("close", FUNDING, "sell", "1", "2000")
    at = (
        datetime.fromisoformat(NOW) + timedelta(days=-1 if outside_exposure == "before_open" else 1)
    ).isoformat()
    with connection() as db:
        _persist_venue_event(
            db,
            ACCOUNT,
            "funding",
            {
                "source": "bybit_live",
                "externalEventId": "unlinked-settlement",
                "eventType": "funding",
                "accountId": ACCOUNT,
                "instrumentId": INSTRUMENT,
                "amount": "8",
                "currency": "USDT",
                "occurredAt": at,
            },
        )
    strategy = get_strategy_financials(FUNDING)
    assert strategy["fundingPnl"] == "0"
    assert strategy["economicEvents"] == strategy["unattributedEvents"] == []


def test_empty_batch_fees_read_has_no_ddl_or_nonexistent_column():
    assert batch_fee_totals("not-yet-submitted") == (None, Decimal("0"))


@pytest.mark.parametrize("size,expected", [("-1", "0.1"), ("-2", None)])
def test_funding_receipt_requires_matching_signed_owned_position(size, expected):
    order("owned", FUNDING, "sell", "1", "2000")
    fill("native", "owned", "1", "2000", "0.1")
    with connection() as db:
        db.execute(
            "UPDATE venue_account_events SET payload_json=json_set(payload_json,'$.side','sell')"
        )
        _persist_venue_event(
            db,
            ACCOUNT,
            "funding",
            {
                "source": "bybit_live",
                "externalEventId": "settlement",
                "eventType": "funding",
                "accountId": ACCOUNT,
                "instrumentId": INSTRUMENT,
                "amount": "0.1",
                "currency": "USDT",
                "occurredAt": NOW,
                "payload": {"size": size, "side": "Sell", "tradePrice": "2000"},
            },
        )
    result = get_strategy_financials(FUNDING)
    assert result["fundingPnl"] == expected


def test_native_mt5_close_without_opening_history_does_not_create_position():
    order("close", CROSS, "sell", "0.01", "2000")
    with connection() as db:
        for table in ("orders", "trade_commands", "fills"):
            db.execute(
                f"UPDATE {table} SET account_id='mt5-live-main',"
                "instrument_id='instrument_xau_usd' WHERE id='close'"
            )
        _persist_venue_event(
            db,
            "mt5-live-main",
            "trade_fill",
            {
                "source": "mt5_live",
                "externalFillId": "close",
                "platformOrderId": "close",
                "accountId": "mt5-live-main",
                "instrumentId": "instrument_xau_usd",
                "positionId": "already-closed",
                "entryType": 1,
                "side": "sell",
                "quantity": "0.01",
                "price": "2000",
                "realizedPnl": "9",
                "fee": "0",
                "currency": "USD",
                "occurredAt": NOW,
            },
        )
    result = get_strategy_financials(CROSS)
    assert result["positions"] == []
    assert "mark_price_unavailable" not in result["issues"]


def test_retained_two_leg_marks_include_matching_mt5_carry():
    from app.pnl_reporting import day_start, reporting_date
    from app.strategy_daily_valuation import daily_marks

    today = day_start(reporting_date(datetime.now(UTC)))
    yesterday = today - timedelta(days=1)
    at = today - timedelta(seconds=30)
    bybit_key = (ACCOUNT, INSTRUMENT, "")
    mt5_key = ("mt5-live-main", "instrument_xau_usd", "ticket")
    history = [
        (
            yesterday,
            {bybit_key: (Decimal(1), Decimal(100)), mt5_key: (Decimal("-0.01"), Decimal(100))},
        )
    ]
    specs = [
        {
            "account_id": ACCOUNT,
            "instrument_id": INSTRUMENT,
            "instrument_type": "crypto_perp",
            "symbol": "XAUTUSDT",
            "settle_currency": "USDT",
            "multiplier": "1",
        },
        {
            "account_id": "mt5-live-main",
            "instrument_id": "instrument_xau_usd",
            "instrument_type": "mt5_cfd",
            "symbol": "XAUUSD",
            "settle_currency": "USDT",
            "multiplier": "100",
        },
    ]
    payload = {
        "asOf": at.isoformat(),
        "bybit": {
            "positions": [
                {
                    "accountId": ACCOUNT,
                    "symbol": "XAUTUSDT",
                    "quantity": "1",
                    "side": "buy",
                    "unrealizedPnl": "8",
                }
            ]
        },
        "mt5": {
            "positions": [
                {
                    "accountId": "mt5-live-main",
                    "externalId": "ticket",
                    "quantity": "-0.01",
                    "side": "sell",
                    "unrealizedPnl": "-6",
                }
            ]
        },
    }
    with connection() as db:
        db.execute(
            "INSERT INTO market_spread_snapshots (id,strategy_key,strategy_instance_id,"
            "left_venue_code,left_symbol,right_venue_code,right_symbol,status,payload_json,"
            "observed_at,created_at) VALUES "
            "('test','cross_venue_spread',?,'bybit','XAUTUSDT','mt5','XAUUSD','available',?,?,?)",
            (CROSS, json.dumps(payload), at.isoformat(), at.isoformat()),
        )
        db.execute(
            "INSERT INTO account_risk_snapshots (account_id,as_of,currency,data_quality_state,"
            "created_at,payload_json) VALUES ('mt5-live-main',?,'USDT','complete',?,?)",
            (at.isoformat(), at.isoformat(), json.dumps({"unrealizedPnl": "-5.5"})),
        )
    marks, reasons = daily_marks(
        CROSS,
        history,
        specs,
        [],
        {
            bybit_key: {"currentPrice": "110"},
            mt5_key: {"netQuantity": "-0.01", "unrealizedPnl": "-8", "swap": "0.5"},
        },
        lambda account, currency, amount, stamp: amount,
    )
    assert reasons == {}
    assert marks[reporting_date(yesterday).isoformat()] == Decimal("2.5")
    assert marks[reporting_date(today).isoformat()] == Decimal("2.5")


@pytest.mark.parametrize("mode", ["live", "simulation"])
def test_live_strategy_does_not_include_historical_demo_orders(mode):
    order("real", CROSS, "buy", "1", "2000")
    order("demo", CROSS, "buy", "100", "2000")
    with connection() as db:
        db.execute("UPDATE strategy_instances SET trading_mode=? WHERE id=?", (mode, CROSS))
        for table in ("orders", "trade_commands", "fills"):
            db.execute(f"UPDATE {table} SET account_id='account_mt5_demo' WHERE id='demo'")
    result = get_strategy_financials(CROSS)
    assert all(row["accountId"] != "account_mt5_demo" for row in result["byAccount"])
    assert sum(Decimal(p["netQuantity"]) for p in result["positions"]) == 1


def test_daily_pnl_does_not_claim_completeness_when_settlement_is_unattributed():
    order("owned", FUNDING, "buy", "1", "2000")
    fill("native", "owned", "1", "2000", "0.1")
    with connection() as db:
        _persist_venue_event(
            db,
            ACCOUNT,
            "funding",
            {
                "source": "bybit_live",
                "externalEventId": "pending-daily",
                "eventType": "funding",
                "accountId": ACCOUNT,
                "instrumentId": INSTRUMENT,
                "amount": "8",
                "currency": "USDT",
                "occurredAt": NOW,
            },
        )
    result = get_strategy_financials(FUNDING)
    assert result["strategyDailyPnl"][-1]["pnl"] is None
    assert result["strategyDailyPnl"][-1]["quality"] != "complete"


def test_overnight_position_requires_historical_marks_for_daily_net_pnl():
    order("overnight", FUNDING, "buy", "1", "2000")
    fill("native-overnight", "overnight", "1", "2000", "0.1")
    yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    with connection() as db:
        db.execute("UPDATE fills SET occurred_at=?", (yesterday,))
        db.execute(
            "UPDATE venue_account_events SET occurred_at=?,"
            "payload_json=json_set(payload_json,'$.occurredAt',?)",
            (yesterday, yesterday),
        )
    result = get_strategy_financials(FUNDING)
    assert len(result["strategyDailyPnl"]) == 2
    assert all(row["pnl"] is None for row in result["strategyDailyPnl"])


def test_monitor_symbol_without_trading_metadata_keeps_account_and_native_receipts():
    order("monitor", FUNDING, "buy", "1", "2000")
    with connection() as db:
        db.execute("UPDATE orders SET instrument_id='monitor:unmapped' WHERE id='monitor'")
        _persist_venue_event(
            db,
            ACCOUNT,
            "trade_fill",
            {
                "source": "mt5_live",
                "externalFillId": "monitor-fill",
                "platformOrderId": "monitor",
                "accountId": ACCOUNT,
                "instrumentId": "monitor:unmapped",
                "symbol": "US500Z",
                "side": "buy",
                "quantity": "1",
                "price": "2000",
                "fee": "0.2",
                "currency": "USDT",
                "realizedPnl": "3.7",
                "occurredAt": NOW,
            },
        )
    result = get_strategy_financials(FUNDING, account_id=ACCOUNT, account_scope=True)
    assert result["realizedPnl"] == "3.7"
    assert result["fees"] == "0.2"
    assert result["scope"] == "account"


def test_cross_settlement_stays_with_instruction_owner_on_shared_account():
    order("funding", FUNDING, "buy", "1", "2000")
    order("cross", CROSS, "sell", "1", "2000")
    with connection() as db:
        _persist_venue_event(
            db,
            ACCOUNT,
            "funding",
            {
                "source": "bybit_live",
                "externalEventId": "cross-funding",
                "eventType": "funding",
                "platformOrderId": "cross",
                "accountId": ACCOUNT,
                "instrumentId": INSTRUMENT,
                "amount": "7.3",
                "currency": "USDT",
                "occurredAt": NOW,
            },
        )
    funding = get_strategy_financials(FUNDING)
    cross = get_strategy_financials(CROSS)
    assert funding["fundingPnl"] == "0"
    assert funding["economicEvents"] == funding["unattributedEvents"] == []
    assert cross["fundingPnl"] == "7.3"
    assert cross["economicEvents"][0]["externalEventId"] == "cross-funding"


def test_mt5_usdt_cash_is_not_labeled_usd_from_contract_name():
    order("native", CROSS, "buy", "0.01", "2000")
    account = "mt5-live-main"
    with connection() as db:
        for table in ("orders", "trade_commands", "fills"):
            db.execute(
                f"UPDATE {table} SET account_id=?,instrument_id='instrument_xau_usd' "
                "WHERE id='native'",
                (account,),
            )
        _persist_venue_event(
            db,
            account,
            "trade_fill",
            {
                "source": "mt5_live",
                "externalFillId": "native-fill",
                "platformOrderId": "native",
                "accountId": account,
                "instrumentId": "instrument_xau_usd",
                "symbol": "XAUUSD.S",
                "side": "buy",
                "quantity": "0.01",
                "price": "2000",
                "fee": "0.2",
                "currency": "USDT",
                "realizedPnl": "0",
                "positionId": "ticket",
                "occurredAt": NOW,
            },
        )
        _persist_venue_snapshot(
            db,
            account,
            {
                "accountId": account,
                "venue": "mt5",
                "source": "mt5_live",
                "asOf": NOW,
                "economicEventsQuality": "complete",
                "accountRisk": {"currency": "USDT"},
                "balances": [],
                "positions": [
                    {
                        "instrumentId": "instrument_xau_usd",
                        "externalPositionId": "ticket",
                        "netQuantity": "0.01",
                        "unrealizedPnl": "12.34",
                        "currentPrice": "2013",
                        "currency": "USDT",
                    }
                ],
            },
        )
    result = get_strategy_financials(CROSS)
    assert [row["currency"] for row in result["byCurrency"]] == ["USDT"]
    assert result["tradingPnl"] == "12.34"
    assert result["fees"] == "0.2"


def test_mt5_opposite_tickets_keep_separate_open_pnl():
    for identity, side, price, ticket in (
        ("a", "buy", "2000", "101"),
        ("b", "sell", "2100", "102"),
    ):
        order(identity, CROSS, side, "0.01", price)
        with connection() as db:
            for table in ("orders", "trade_commands", "fills"):
                db.execute(
                    f"UPDATE {table} SET account_id='mt5-live-main', "
                    "instrument_id='instrument_xau_usd' WHERE id=?",
                    (identity,),
                )
            _persist_venue_event(
                db,
                "mt5-live-main",
                "trade_fill",
                {
                    "source": "mt5_live",
                    "externalFillId": identity,
                    "platformOrderId": identity,
                    "accountId": "mt5-live-main",
                    "instrumentId": "instrument_xau_usd",
                    "symbol": "XAUUSD",
                    "positionId": ticket,
                    "side": side,
                    "quantity": "0.01",
                    "price": price,
                    "fee": "0",
                    "realizedPnl": "0",
                    "swap": "0",
                    "currency": "USD",
                    "occurredAt": NOW,
                },
            )
    with connection() as db:
        _persist_venue_snapshot(
            db,
            "mt5-live-main",
            {
                "accountId": "mt5-live-main",
                "venue": "mt5",
                "source": "mt5_live",
                "asOf": NOW,
                "economicEventsQuality": "complete",
                "balances": [],
                "positions": [
                    {
                        "instrumentId": "instrument_xau_usd",
                        "externalPositionId": ticket,
                        "netQuantity": quantity,
                        "currentPrice": "2050",
                        "currency": "USD",
                    }
                    for ticket, quantity in (("101", "0.01"), ("102", "-0.01"))
                ],
            },
        )
    result = get_strategy_financials(CROSS)
    assert len(result["positions"]) == 2
    usd = next(row for row in result["byCurrency"] if row["currency"] == "USD")
    assert Decimal(usd["realizedPnl"]) == 0
    assert Decimal(usd["tradingPnl"]) == 100


def seed_spot_receipt(fee="0.001", currency="BTC"):
    order("spot", FUNDING, "buy", "1", "1000")
    with connection() as db:
        db.execute("UPDATE orders SET instrument_id='instrument_btc_usdt' WHERE id='spot'")
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
            {
                "source": "bybit_live",
                "externalFillId": "fspot",
                "platformOrderId": "spot",
                "accountId": ACCOUNT,
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "quantity": "1",
                "price": "1000",
                "fee": fee,
                "currency": currency,
                "occurredAt": NOW,
            },
        )


def test_spot_native_fee_reduces_actual_cash_and_is_valued_at_execution_price():
    seed_spot_receipt()
    assert funding_spot_cash("batch", Decimal("1")) == Decimal("0.999")
    assert batch_fee_totals("batch") == (None, Decimal("1.000"))


@pytest.mark.parametrize("fee,currency", [("0.001", "BTC"), (None, "BTC"), ("0.001", "UNKNOWN")])
def test_native_receipt_controls_close_quantity_and_missing_fee_blocks_submission(
    monkeypatch, fee, currency
):
    from app.strategies import funding_workspace as workspace

    seed_spot_receipt(fee, currency)
    instruction = {
        "instructionId": "open",
        "executionBatchId": "batch",
        "action": "open",
        "status": "completed",
        "updatedAt": NOW,
        "executionPlan": {
            "legs": [
                {
                    "role": "perpetual_leg",
                    "accountId": ACCOUNT,
                    "externalSymbol": "BTCUSDT",
                    "side": "sell",
                    "maximumQuantity": "1",
                },
                {
                    "role": "spot_leg",
                    "accountId": ACCOUNT,
                    "externalSymbol": "BTCUSDT",
                    "side": "buy",
                    "maximumQuantity": "1",
                    "quantityStep": "0.001",
                },
            ]
        },
    }
    monkeypatch.setattr(workspace, "get_instruction", lambda _: instruction)
    monkeypatch.setattr(workspace, "list_instructions", lambda _: [instruction])
    monkeypatch.setattr(
        workspace,
        "_workspace_state_from_instruction",
        lambda _: {
            "executionState": "completed",
            "cumulativePerpetualFill": "1",
            "cumulativeSpotFill": "1",
        },
    )

    def no_existing(*_):
        raise HTTPException(status_code=404)

    monkeypatch.setattr(workspace, "get_instruction_by_idempotency", no_existing)
    created = []

    def record_request(_, request, **__):
        created.append(request)
        return {"instructionId": "close"}

    # The submit boundary is intercepted so this test cannot dispatch an order.
    monkeypatch.setattr(workspace, "create_instruction", record_request)
    monkeypatch.setattr(workspace, "get_funding_instruction_workspace", lambda item: item)
    monkeypatch.setattr(workspace, "funding_account_binding", lambda *_: {
        "trading_mode": "live", "account_id": ACCOUNT,
    })
    monkeypatch.setattr(workspace, "get_funding_controlled_live_readiness", lambda **_: {
        "ready": True,
    })
    group = workspace._funding_group_snapshot(instruction_id="open", batch_id="batch")
    assert group["spotFeeAdjusted"] is True
    if fee is None or currency == "UNKNOWN":
        assert group["netSpotAcquired"] is None
        assert group["remainingSpotQuantity"] is None
        with pytest.raises(HTTPException, match="手续费尚未核实"):
            workspace.submit_funding_instruction(
                action="close",
                idempotency_key="missing-fee",
                perpetual_symbol="BTCUSDT",
                spot_symbol="BTCUSDT",
                quantity=Decimal("1"),
                requested_by="demo_ceo",
                target_open_instruction_id="open",
            )
        assert created == []
        return

    assert group["netSpotAcquired"] == "0.999"
    workspace.submit_funding_instruction(
        action="close",
        idempotency_key="close-all",
        perpetual_symbol="BTCUSDT",
        spot_symbol="BTCUSDT",
        quantity=Decimal("1"),
        requested_by="demo_ceo",
        target_open_instruction_id="open",
    )
    assert created[0].parameters["perpetualQuantity"] == Decimal("1")
    assert created[0].parameters["spotQuantity"] == Decimal("0.999")
    workspace.submit_funding_instruction(
        action="close",
        idempotency_key="close-half",
        perpetual_symbol="BTCUSDT",
        spot_symbol="BTCUSDT",
        quantity=Decimal("0.5"),
        requested_by="demo_ceo",
        target_open_instruction_id="open",
    )
    assert created[1].parameters["spotQuantity"] == Decimal("0.499")
    remainder = workspace._funding_group_snapshot(
        instruction_id="open",
        batch_id="batch",
        close_summary={
            "authoritativeClosedQuantity": Decimal("0.5"),
            "spotSoldOrReserved": Decimal("0.499"),
        },
    )
    assert remainder["remainingClosableQuantity"] == "0.5"
    assert remainder["remainingSpotQuantity"] == "0.500"


def test_mt5_position_exposure_prefers_venue_notional_and_restores_lot_contracts():
    """A matching venue notional wins; otherwise LOT quantity is restored through the multiplier."""

    for identity, side, price, ticket in (
        ("a", "buy", "2000", "101"),
        ("b", "sell", "2100", "102"),
    ):
        order(identity, CROSS, side, "0.01", price)
        with connection() as db:
            for table in ("orders", "trade_commands", "fills"):
                db.execute(
                    f"UPDATE {table} SET account_id='mt5-live-main', "
                    "instrument_id='instrument_xau_usd' WHERE id=?",
                    (identity,),
                )
            _persist_venue_event(
                db,
                "mt5-live-main",
                "trade_fill",
                {
                    "source": "mt5_live",
                    "externalFillId": identity,
                    "platformOrderId": identity,
                    "accountId": "mt5-live-main",
                    "instrumentId": "instrument_xau_usd",
                    "symbol": "XAUUSD",
                    "positionId": ticket,
                    "side": side,
                    "quantity": "0.01",
                    "price": price,
                    "fee": "0",
                    "realizedPnl": "0",
                    "swap": "0",
                    "currency": "USD",
                    "occurredAt": NOW,
                },
            )
    with connection() as db:
        _persist_venue_snapshot(
            db,
            "mt5-live-main",
            {
                "accountId": "mt5-live-main",
                "venue": "mt5",
                "source": "mt5_live",
                "asOf": NOW,
                "economicEventsQuality": "complete",
                "balances": [],
                "positions": [
                    {
                        "instrumentId": "instrument_xau_usd",
                        "externalPositionId": "101",
                        "netQuantity": "0.01",
                        "currentPrice": "2000",
                        "positionValue": "1980",
                        "currency": "USD",
                    },
                    {
                        "instrumentId": "instrument_xau_usd",
                        "externalPositionId": "102",
                        "netQuantity": "-0.01",
                        "currentPrice": "2100",
                        "currency": "USD",
                    },
                ],
            },
        )
    result = get_strategy_financials(CROSS)
    # Gross keeps both hedged legs; net keeps only the residual directional exposure.
    exposure = result["exposure"]
    assert Decimal(exposure["positionValue"]) == Decimal("4080")
    assert Decimal(exposure["positionValueNet"]) == Decimal("120")
    assert exposure["positionValueCurrency"] == "USD"
    legs = {row["externalPositionId"]: row for row in result["positions"]}
    # 101 has a matching venue notional (1980), so the mark price 2000 is not used.
    assert Decimal(legs["101"]["positionValue"]) == Decimal("1980")
    # 102 has no venue notional, so LOT 0.01 is restored as 0.01 x 2100 x 100.
    assert Decimal(legs["102"]["positionValue"]) == Decimal("2100")
    assert {row["positionValueCurrency"] for row in legs.values()} == {"USD"}


def test_mixed_currency_positions_never_combine_into_one_exposure():
    """Legs valued in different currencies stay separate; no FX rate is invented."""

    order("a", CROSS, "buy", "0.01", "2000")
    order("b", CROSS, "buy", "1", "50000")
    with connection() as db:
        for table in ("orders", "trade_commands", "fills"):
            db.execute(
                f"UPDATE {table} SET account_id='mt5-live-main', "
                "instrument_id='instrument_xau_usd' WHERE id='a'",
            )
            db.execute(
                f"UPDATE {table} SET instrument_id='instrument_btc_usdt' WHERE id='b'",
            )
        _persist_venue_event(
            db,
            "mt5-live-main",
            "trade_fill",
            {
                "source": "mt5_live",
                "externalFillId": "a",
                "platformOrderId": "a",
                "accountId": "mt5-live-main",
                "instrumentId": "instrument_xau_usd",
                "symbol": "XAUUSD",
                "positionId": "101",
                "side": "buy",
                "quantity": "0.01",
                "price": "2000",
                "fee": "0",
                "realizedPnl": "0",
                "swap": "0",
                "currency": "USD",
                "occurredAt": NOW,
            },
        )
        _persist_venue_snapshot(
            db,
            "mt5-live-main",
            {
                "accountId": "mt5-live-main",
                "venue": "mt5",
                "source": "mt5_live",
                "asOf": NOW,
                "economicEventsQuality": "complete",
                "balances": [],
                "positions": [
                    {
                        "instrumentId": "instrument_xau_usd",
                        "externalPositionId": "101",
                        "netQuantity": "0.01",
                        "currentPrice": "2000",
                        "currency": "USD",
                    }
                ],
            },
        )
        _persist_venue_snapshot(
            db,
            ACCOUNT,
            {
                "accountId": ACCOUNT,
                "venue": "bybit",
                "source": "bybit_live",
                "asOf": NOW,
                "economicEventsQuality": "complete",
                "balances": [],
                "positions": [
                    {
                        "instrumentId": "instrument_btc_usdt",
                        "netQuantity": "1",
                        "currentPrice": "50000",
                        "currency": "USDT",
                    }
                ],
            },
        )
    result = get_strategy_financials(CROSS)
    assert result["exposure"] == {
        "positionValue": None,
        "positionValueNet": None,
        "positionValueCurrency": None,
    }
    assert {row["positionValueCurrency"] for row in result["positions"]} == {"USD", "USDT"}


def test_cross_session_freeze_and_reopen_preserves_real_costs():
    from app.catalog import get_strategy_pnl
    from app.cross_session_valuation import _load_sessions, load_sessions
    from app.pnl_reporting import day_start, reporting_date

    start = day_start(reporting_date(datetime.now(UTC))) - timedelta(days=3)
    order("session", CROSS, "buy", "1", "100")
    fill("session-fill", "session", "1", "100", "0.2")
    with connection() as db:
        db.execute("UPDATE fills SET occurred_at=? WHERE order_id='session'", (start.isoformat(),))
        row = db.execute(
            "SELECT payload_json FROM venue_account_events WHERE external_id='session-fill'"
        ).fetchone()
        raw = json.loads(row[0])
        raw["occurredAt"] = start.isoformat()
        db.execute(
            "UPDATE venue_account_events SET occurred_at=?,payload_json=? "
            "WHERE external_id='session-fill'",
            (start.isoformat(), json.dumps(raw)),
        )
        _persist_venue_snapshot(
            db,
            ACCOUNT,
            {
                "accountId": ACCOUNT,
                "venue": "bybit",
                "source": "bybit_live",
                "asOf": NOW,
                "economicEventsQuality": "complete",
                "balances": [],
                "positions": [
                    {
                        "instrumentId": INSTRUMENT,
                        "netQuantity": "1",
                        "currentPrice": "20",
                        "currency": "USDT",
                    }
                ],
            },
        )
        _persist_venue_event(
            db,
            ACCOUNT,
            "funding",
            {
                "source": "bybit_live",
                "externalEventId": "closed-cost",
                "eventType": "funding",
                "accountId": ACCOUNT,
                "externalOrderId": "session",
                "instrumentId": INSTRUMENT,
                "amount": "-2",
                "currency": "USDT",
                "occurredAt": (start + timedelta(days=1)).isoformat(),
            },
        )

    def observe(index, opened, upl):
        at = min(
            start + timedelta(days=index, hours=23, minutes=59),
            datetime.now(UTC) - timedelta(seconds=30),
        ).isoformat()
        payload = {
            "asOf": at,
            "bybit": {
                "status": "available",
                "marketStatus": "open",
                "quote": {"mid": "110"},
                "positions": [
                    {
                        "accountId": ACCOUNT,
                        "symbol": "XAUTUSDT",
                        "quantity": "1",
                        "side": "buy",
                        "unrealizedPnl": str(upl),
                        "currency": "USDT",
                    }
                ],
            },
            "mt5": {
                "status": "available",
                "marketStatus": "open" if opened else "closed",
                "positions": [],
            },
        }
        with connection() as db:
            db.execute(
                "INSERT INTO market_spread_snapshots (id,strategy_key,strategy_instance_id,"
                "left_venue_code,left_symbol,right_venue_code,right_symbol,status,payload_json,"
                "observed_at,created_at) VALUES "
                "(?,'cross_venue_spread',?,'bybit','XAUTUSDT','mt5','XAUUSD','available',?,?,?)",
                (f"session-{index}", CROSS, json.dumps(payload), at, at),
            )
        _load_sessions.cache_clear()

    observe(0, True, 10)
    observe(1, False, -80)
    observe(2, False, -90)
    frozen = get_strategy_pnl(CROSS).model_dump(by_alias=True, mode="json")
    assert Decimal(frozen["tradingPnl"]) == 10
    assert Decimal(frozen["fundingPnl"]) == 0
    assert Decimal(frozen["netPnl"]) == Decimal("9.8")
    assert frozen["valuationMarketStatus"] == "closed"
    assert any(d["quality"] == "market_closed" for d in frozen["strategyDailyPnl"])
    # Unfiltered finance used by account/risk remains live, with weekend costs.
    live = get_strategy_financials(CROSS)
    assert Decimal(live["tradingPnl"]) == -80
    assert Decimal(live["fundingPnl"]) == -2
    observe(3, True, 10)
    reopened = get_strategy_pnl(CROSS).model_dump(by_alias=True, mode="json")
    assert Decimal(reopened["netPnl"]) == Decimal("7.8")
    assert Decimal(reopened["strategyDailyPnl"][-1]["pnl"]) == -2
    assert load_sessions(FUNDING) is None


def test_session_observation_ignores_exit_guard_but_rejects_stale_quotes():
    from app.cross_session_valuation import valid_observation

    p = {
        venue: {"marketStatus": "open", "status": "available", "automaticExitAllowed": False}
        for venue in ["mt5", "bybit"]
    }
    assert valid_observation(p)
    p["mt5"]["executionBlockReason"] = "quote_stale"
    assert not valid_observation(p)


def test_cross_filtered_capital_recomputes_drawdown_and_retains_archive_baseline():
    from app.cross_session_valuation import filter_capital_history
    from app.schemas import StrategyEquityHistoryPointResponse as Point

    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=3)
    points = []
    with connection() as db:
        for scope in ["unified_trading", "full_account"]:
            db.execute(
                "INSERT INTO account_capital_coverage VALUES(?,?,?,?,?)",
                (ACCOUNT, scope, start.isoformat(), NOW, NOW),
            )
        for index, value in enumerate([100, 10, 200]):
            at = min(
                start + timedelta(days=index, hours=23, minutes=59),
                datetime.now(UTC) - timedelta(seconds=30),
            ).isoformat()
            opened = index != 1
            payload = {
                "asOf": at,
                **{
                    v: {
                        "status": "available",
                        "marketStatus": "closed" if v == "mt5" and not opened else "open",
                    }
                    for v in ["mt5", "bybit"]
                },
            }
            db.execute(
                "INSERT INTO market_spread_snapshots (id,strategy_key,strategy_instance_id,"
                "left_venue_code,left_symbol,right_venue_code,right_symbol,status,payload_json,"
                "observed_at,created_at) VALUES "
                "(?,'cross_venue_spread',?,'bybit','XAUTUSDT','mt5','XAUUSD','available',?,?,?)",
                (str(index), CROSS, json.dumps(payload), at, at),
            )
            db.execute(
                "INSERT INTO account_risk_snapshots (account_id,as_of,currency,equity,"
                "total_assets,asset_scope,data_quality_state,created_at,payload_json) "
                "VALUES (?,?,'USD',?,?,'unified_trading','complete',?,'{}')",
                (ACCOUNT, at, str(value), str(value), at),
            )
            points.append(
                Point(
                    asOf=at,
                    equity=str(value),
                    totalAssets=str(value),
                    currency="USD",
                    assetScope="unified_trading",
                    totalAssetsDrawdown="-90",
                )
            )
        # A real deposit during closure must not become reopening profit/drawdown.
        db.execute(
            "INSERT INTO account_capital_movements VALUES(?,?,?,?,?,?,?,?)",
            (
                ACCOUNT,
                "deposit",
                "full_account",
                points[1].as_of.isoformat(),
                "USD",
                "100",
                "deposit",
                "{}",
            ),
        )
    result = filter_capital_history(CROSS, ACCOUNT, points)
    assert [p.total_assets for p in result] == [Decimal(100), Decimal(200)]
    assert result[-1].total_assets_drawdown == 0
    assert points[-1].total_assets_drawdown == -90  # original live points remain unchanged
    # Even if the live chart's tail only retains closed/recent points, archive closes remain.
    assert len(filter_capital_history(CROSS, ACCOUNT, points[-1:])) == 2
    assert filter_capital_history(FUNDING, ACCOUNT, points) == []


def test_background_projection_http_read_never_recomputes_and_preserves_failure(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app import catalog
    from app.catalog_routes import create_catalog_router
    from app.schemas import StrategyPnlResponse
    from app.strategy_management_projection import read_projection, refresh_one, request_projection

    request_projection(FUNDING, None, "pnl")
    with pytest.raises(HTTPException) as error:
        read_projection(FUNDING)
    assert error.value.status_code == 503
    value = StrategyPnlResponse(
        strategyInstanceId=FUNDING,
        realizedPnl="1",
        tradingPnl="2",
        fees="0.1",
        currency="USDT",
        dataQualityState="complete",
        netPnl="2.9",
    )
    monkeypatch.setattr(catalog, "get_strategy_pnl", lambda _: value)
    assert refresh_one()
    monkeypatch.setattr(
        catalog, "get_strategy_pnl", lambda _: pytest.fail("HTTP must not calculate")
    )
    app = FastAPI()
    app.include_router(create_catalog_router("/api/v1"))
    # Another producer owns the writer reservation, but published reads still work.
    with connection() as writer:
        writer.execute("BEGIN IMMEDIATE")
        response = TestClient(app).get(f"/api/v1/strategies/instances/{FUNDING}/pnl")
    assert response.status_code == 200
    assert response.json()["netPnl"] == "2.9"
    with connection() as db:
        db.execute("UPDATE strategy_management_projection SET error_code='upstream_failure'")
    stale = read_projection(FUNDING)
    assert stale.net_pnl == Decimal("2.9")
    assert stale.data_quality_state == "stale"
    assert "management_projection_stale" in stale.issues


@pytest.mark.parametrize(
    "module_name,worker,monitor",
    [
        ("strategy_management_projection", "refresh_one", "run_management_projection_monitor"),
        ("account_history_sync", "sync_due_histories", "run_history_sync_monitor"),
    ],
)
def test_monitor_database_checks_do_not_run_on_event_loop(
    monkeypatch, module_name, worker, monitor
):
    import asyncio
    import importlib
    import threading
    from contextlib import contextmanager

    module = importlib.import_module(f"app.{module_name}")
    database_threads = []

    @contextmanager
    def observed_connection():
        database_threads.append(threading.get_ident())
        with connection() as db:
            yield db

    def finished(*args):
        raise asyncio.CancelledError

    monkeypatch.setattr(module, "connection", observed_connection)
    monkeypatch.setattr(module, worker, lambda: False)
    if hasattr(module, "prepare_keys"):
        monkeypatch.setattr(module, "prepare_keys", lambda: None)
    monkeypatch.setattr(module.monitor_health, "finish", finished)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(getattr(module, monitor)())
    assert database_threads
    assert threading.get_ident() not in database_threads


def test_detail_demand_renews_after_read_without_blocking_published_payload():
    import asyncio

    from fastapi import BackgroundTasks, FastAPI
    from fastapi.testclient import TestClient

    from app.catalog_routes import create_catalog_router
    from app.schemas import StrategyAccountSnapshotResponse
    from app.strategy_management_projection import read_projection, request_projection

    request_projection(FUNDING, None, "detail")
    old = (datetime.now(UTC) - timedelta(minutes=20)).isoformat()
    payload = StrategyAccountSnapshotResponse(
        strategyInstanceId=FUNDING, dataQualityState="complete", isStale=False
    )
    with connection() as db:
        db.execute(
            "UPDATE strategy_management_projection SET payload_json=?,updated_at=?,requested_at=?",
            (payload.model_dump_json(by_alias=True), datetime.now(UTC).isoformat(), old),
        )
    tasks = BackgroundTasks()
    with connection() as writer:
        writer.execute("BEGIN IMMEDIATE")
        result = read_projection(FUNDING, kind="detail", background_tasks=tasks)
        assert result.strategy_instance_id == FUNDING
        assert (
            writer.execute("SELECT requested_at FROM strategy_management_projection").fetchone()[0]
            == old
        )
    assert len(tasks.tasks) == 1
    asyncio.run(tasks())
    with connection() as db:
        assert (
            db.execute("SELECT requested_at FROM strategy_management_projection").fetchone()[0]
            > old
        )
        db.execute("UPDATE strategy_management_projection SET requested_at=?", (old,))
    app = FastAPI()
    app.include_router(create_catalog_router("/api/v1"))
    response = TestClient(app).get(f"/api/v1/strategies/instances/{FUNDING}/account-snapshot")
    assert response.status_code == 200
    with connection() as db:
        assert (
            db.execute("SELECT requested_at FROM strategy_management_projection").fetchone()[0]
            > old
        )


def test_legacy_history_requires_changing_quote_not_poll_time():
    from app.cross_session_valuation import legacy_observation

    at = datetime.now(UTC) - timedelta(minutes=5)

    def insert(index, price):
        stamp = (at + timedelta(seconds=index)).isoformat()
        payload = {
            "asOf": stamp,
            "mt5": {"status": "available", "quote": {"bid": price, "ask": price}},
            "bybit": {"status": "available", "quote": {"bid": "100", "ask": "101"}},
        }
        with connection() as db:
            db.execute(
                "INSERT INTO market_spread_snapshots (id,strategy_key,strategy_instance_id,"
                "left_venue_code,left_symbol,right_venue_code,right_symbol,status,payload_json,"
                "observed_at,created_at) VALUES "
                "(?,'cross_venue_spread',?,'bybit','XAUTUSDT','mt5','XAUUSD','available',?,?,?)",
                (str(index), CROSS, json.dumps(payload), stamp, stamp),
            )

    insert(0, "100")
    insert(10, "100")
    with connection() as db:
        assert legacy_observation(db, CROSS, (at + timedelta(seconds=10)).isoformat()) is None
    insert(20, "101")
    with connection() as db:
        observed = legacy_observation(db, CROSS, (at + timedelta(seconds=20)).isoformat())
        assert observed["mt5"]["marketStatus"] == "open"
