from datetime import UTC, datetime
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


def test_empty_batch_fees_read_has_no_ddl_or_nonexistent_column():
    assert batch_fee_totals("not-yet-submitted") == (None, Decimal("0"))


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
    monkeypatch.setattr(workspace, "_execute_funding_instruction", lambda item: item)
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
