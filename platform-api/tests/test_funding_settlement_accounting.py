import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.config import get_settings
from app.database import connection, initialize_database
from app.financial_facts import record_financial_fact
from app.funding_settlement_accounting import settlement_request, sync_funding_settlements
from app.live_venue_snapshot_sync import _persist_venue_event, _persist_venue_snapshot
from app.strategy_financial_readmodel import batch_fee_totals, get_strategy_financials

ACCOUNT = "bybit-live-main"
INSTRUMENT = "instrument_btc_usdt_perp"
FUNDING = "strategy_funding_arbitrage_instance_default"
CROSS = "strategy_cross_venue_spread_instance_default"
ANCHOR = "2026-09-09T16:12:44Z"
OPEN = "2026-09-10T02:30:00Z"
SETTLED = "2026-09-10T08:00:00Z"


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path / "funding.db"))
    initialize_database()


def persist(event):
    with connection() as db:
        _persist_venue_event(db, ACCOUNT, event["eventType"], event)


def transaction(identity, quantity, size, at, side="sell", group="open", owner=FUNDING):
    """One native execution, its economic receipt and its actual command owner."""
    event = {
        "source": "bybit_live", "accountId": ACCOUNT, "instrumentId": INSTRUMENT,
        "symbol": "BTCUSDT", "occurredAt": at, "dataQualityState": "complete",
        "externalEventId": "fee:" + identity, "eventType": "fee", "amount": "-0.01",
        "currency": "USDT", "payload": {
            "type": "TRADE", "category": "linear", "id": identity, "tradeId": "fill-" + identity,
            "orderId": identity, "qty": quantity, "size": size, "side": side.title(),
        },
    }
    persist(event)
    if group is None:
        return event
    with connection() as db:
        db.execute(
            "INSERT OR IGNORE INTO strategy_runs "
            "(id,idempotency_key,strategy_instance_id,strategy_key,direction,status,"
            "action,created_at,updated_at) "
            "VALUES (?,?,?,'funding_arbitrage','positive_carry','completed','open',?,?)",
            (group, group, owner, at, at),
        )
        db.execute(
            "INSERT OR IGNORE INTO execution_batches "
            "(id,account_id,strategy_key,direction,status,strategy_instruction_id,"
            "created_at,updated_at) "
            "VALUES (?,?,'funding_arbitrage','positive_carry','hedged',?,?,?)",
            ("batch-" + group, ACCOUNT, group, at, at),
        )
        db.execute("UPDATE strategy_runs SET execution_batch_id=? WHERE id=?",
                   ("batch-" + group, group))
        db.execute(
            "INSERT INTO trade_commands (id,idempotency_key,strategy_instance_id,account_id,"
            "instrument_id,command_type,side,order_type,quantity,status,created_at,updated_at) "
            "VALUES (?,?,?,?,?,'create_order',?,'market',?,'filled',?,?)",
            (identity, identity, owner, ACCOUNT, INSTRUMENT, side, quantity, at, at),
        )
        db.execute(
            "INSERT INTO orders (id,command_id,account_id,instrument_id,symbol,side,order_type,"
            "quantity,status,external_order_id,created_at,updated_at) "
            "VALUES (?,?,?,?,'BTCUSDT',?,'market',?,'filled',?,?,?)",
            (identity, identity, ACCOUNT, INSTRUMENT, side, quantity, identity, at, at),
        )
        db.execute(
            "INSERT INTO fills "
            "(id,order_id,account_id,instrument_id,side,quantity,price,occurred_at) "
            "VALUES (?,?,?,?,?,?,'78000',?)",
            (identity, identity, ACCOUNT, INSTRUMENT, side, quantity, at),
        )
        db.execute(
            "INSERT INTO execution_batch_legs (id,batch_id,sequence,role,account_id,instrument_id,"
            "symbol,side,order_type,quantity,order_id,status,created_at,updated_at) "
            "VALUES (?,?,?,'perpetual_leg',?,?,'BTCUSDT',?,'market',?,?,'filled',?,?)",
            (identity, "batch-" + group, db.execute("SELECT count(*) FROM orders").fetchone()[0],
             ACCOUNT, INSTRUMENT, side, quantity, identity, at, at),
        )
        _persist_venue_event(db, ACCOUNT, "trade_fill", {
            **{key: event[key] for key in (
                "source", "accountId", "instrumentId", "symbol", "occurredAt", "dataQualityState"
            )},
            "externalFillId": "fill-" + identity, "externalOrderId": identity,
            "platformOrderId": identity, "side": side, "quantity": quantity,
            "price": "78000", "fee": "0.01", "currency": "USDT",
        })
    return event


def seed(amount="0.00319691"):
    transaction("flat", "0.001", "0", ANCHOR, side="buy", group=None)
    transaction("entry", "0.001", "-0.001", OPEN)
    event = {
        "source": "bybit_live", "accountId": ACCOUNT, "instrumentId": INSTRUMENT,
        "symbol": "BTCUSDT", "occurredAt": SETTLED, "dataQualityState": "complete",
        "externalEventId": "funding:settlement", "eventType": "funding", "amount": amount,
        "currency": "USDT", "payload": {
            "type": "SETTLEMENT", "category": "linear", "id": "settlement",
            "qty": "0.001", "size": "-0.001", "side": "Sell", "funding": amount,
            "change": amount, "currency": "USDT",
        },
    }
    persist(event)
    snapshot = {
        "accountId": ACCOUNT, "source": "bybit_live", "venue": "bybit",
        "asOf": datetime.now(UTC).isoformat(), "historyStart": "2026-09-09T00:00:00Z",
        "historyEnd": "2026-09-10T08:10:00Z", "economicEventsQuality": "complete",
        "dataQualityState": "complete", "economicEvents": [event],
        "positions": [], "balances": [], "fills": [], "orders": [],
    }
    with connection() as db:
        _persist_venue_snapshot(db, ACCOUNT, snapshot)
    return event, snapshot


@pytest.mark.parametrize("amount", ["0.00319691", "-0.00319691"])
def test_exact_native_amount_owned_by_batch_and_repeated_sync_counts_once(amount):
    event, _ = seed(amount)
    assert sync_funding_settlements(ACCOUNT) == 1
    assert sync_funding_settlements(ACCOUNT) == 1
    with connection() as db:
        facts = db.execute("SELECT * FROM financial_facts").fetchall()
        assert len(facts) == 1
        assert facts[0]["amount"] == amount
        assert facts[0]["external_id"] == event["externalEventId"]
        assert json.loads(facts[0]["payload_json"])["batchId"] == "batch-open"
        assert db.execute(
            "SELECT count(*) FROM audit_events WHERE event_type='financial_fact_recorded'"
        ).fetchone()[0] == 1
    assert batch_fee_totals("batch-open")[0] == Decimal(amount)
    result = get_strategy_financials(FUNDING)
    assert result["fundingPnl"] == amount
    owned = next(e for e in result["economicEvents"] if e["eventType"] == "funding")
    assert owned["batchId"] == "batch-open"
    assert owned["instructionId"] == "open"
    assert get_strategy_financials(CROSS)["economicEvents"] == []


@pytest.mark.parametrize("gap", [
    "unknown_initial_position", "missing_fill", "missing_transaction", "unknown_owner",
    "size_mismatch",
    "partial_history", "history_starts_late", "settlement_during_trade", "currency_mismatch",
])
def test_incomplete_or_conflicting_evidence_is_never_assigned(gap):
    event, snapshot = seed()
    with connection() as db:
        if gap == "unknown_initial_position":
            db.execute("DELETE FROM venue_account_events WHERE external_id='fee:flat'")
            db.execute(
                "UPDATE venue_account_events SET payload_json=json_set(payload_json,"
                "'$.payload.size','-0.002') WHERE external_id='fee:entry'"
            )
            event["payload"].update(size="-0.002", qty="0.002")
        elif gap == "missing_fill":
            db.execute("DELETE FROM venue_account_events WHERE event_type='trade_fill'")
        elif gap == "missing_transaction":
            db.execute("DELETE FROM venue_account_events WHERE external_id='fee:entry'")
        elif gap == "unknown_owner":
            db.execute("UPDATE execution_batch_legs SET order_id=NULL WHERE id='entry'")
        elif gap == "size_mismatch":
            event["payload"].update(size="-0.002", qty="0.002")
        elif gap == "partial_history":
            snapshot["economicEventsQuality"] = "partial"
        elif gap == "history_starts_late":
            snapshot["historyStart"] = "2026-09-10T04:00:00Z"
        elif gap == "settlement_during_trade":
            event["occurredAt"] = OPEN
        elif gap == "currency_mismatch":
            event["currency"] = "USD"
        assert settlement_request(db, event, snapshot) is None
        assert db.execute("SELECT count(*) FROM financial_facts").fetchone()[0] == 0


def test_multiple_groups_not_allocated_by_shared_account_or_strategy():
    event, snapshot = seed()
    transaction("entry2", "0.001", "-0.002", "2026-09-10T03:00:00Z", group="second")
    event["payload"].update(size="-0.002", qty="0.002")
    with connection() as db:
        assert settlement_request(db, event, snapshot) is None


def test_native_net_zero_does_not_erase_offsetting_logical_groups():
    transaction("oldlong", "0.001", "0.001", "2026-09-09T12:00:00Z",
                side="buy", group="long")
    transaction("oldshort", "0.001", "0", "2026-09-09T13:00:00Z", group="short")
    event, snapshot = seed()
    with connection() as db:
        assert settlement_request(db, event, snapshot) is None


def test_native_first_opening_proves_flat_without_earlier_close_receipt():
    event, snapshot = seed()
    with connection() as db:
        db.execute("DELETE FROM venue_account_events WHERE external_id='fee:flat'")
        request = settlement_request(db, event, snapshot)
        assert request is not None
        assert request.payload["flatPositionPhase"] == "before"
        assert request.payload["flatTransactionId"] == "entry"


def test_historical_instrument_alias_uses_same_native_identity():
    event, snapshot = seed()
    with connection() as db:
        db.execute(
            "UPDATE venue_account_events SET instrument_id=?,payload_json="
            "json_set(payload_json,'$.instrumentId',?) WHERE external_id='fee:entry'",
            ("monitor:bybit:bybit-live-main:linear:BTCUSDT",) * 2,
        )
        assert settlement_request(db, event, snapshot) is not None


def test_account_identity_cannot_be_substituted():
    event, snapshot = seed()
    snapshot["accountId"] = "another-account"
    with connection() as db:
        assert settlement_request(db, event, snapshot) is None


def test_missing_instrument_differs_from_a_conflicting_instrument_alias():
    from app.venue_identity_repository import OrderIdentities, VenueIdentityConflict

    identities = OrderIdentities([], {(ACCOUNT, "ambiguous"): None})
    assert identities.instrument(ACCOUNT, None) is None
    with pytest.raises(VenueIdentityConflict):
        identities.instrument(ACCOUNT, "ambiguous")


def test_close_after_settlement_does_not_change_historical_ownership():
    event, snapshot = seed()
    transaction("later", "0.001", "0", "2026-09-10T08:01:00Z", side="buy", group="close")
    with connection() as db:
        request = settlement_request(db, event, snapshot)
        assert request is not None
        assert request.payload["batchId"] == "batch-open"


def test_fact_commit_before_projection_failure_recovers_on_restart(monkeypatch):
    seed()
    import app.financial_facts as facts
    rebuild = facts.rebuild_account_instrument_projection
    def interrupted(*args):
        raise RuntimeError("process stopped after fact commit")
    monkeypatch.setattr(facts, "rebuild_account_instrument_projection", interrupted)
    with pytest.raises(RuntimeError, match="process stopped"):
        sync_funding_settlements(ACCOUNT)
    monkeypatch.setattr(facts, "rebuild_account_instrument_projection", rebuild)
    assert sync_funding_settlements(ACCOUNT) == 1
    with connection() as db:
        assert db.execute("SELECT count(*) FROM financial_facts").fetchone()[0] == 1
        assert db.execute("SELECT fact_count FROM formal_pnl_results").fetchone()[0] == 1


def test_concurrent_identical_settlement_posts_one_fact():
    event, snapshot = seed()
    with connection() as db:
        request = settlement_request(db, event, snapshot)
    assert request is not None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(record_financial_fact, [request, request]))
    assert results[0].fact_id == results[1].fact_id
    with connection() as db:
        assert db.execute("SELECT count(*) FROM financial_facts").fetchone()[0] == 1


def test_changed_amount_cannot_overwrite_the_settlement():
    from fastapi import HTTPException

    event, snapshot = seed()
    with connection() as db:
        request = settlement_request(db, event, snapshot)
    assert request is not None
    record_financial_fact(request)
    with pytest.raises(HTTPException) as error:
        record_financial_fact(request.model_copy(update={"amount": Decimal("12")}))
    assert error.value.status_code == 409
    assert batch_fee_totals("batch-open")[0] == Decimal("0.00319691")


def test_missing_fee_fx_does_not_hide_settled_base_currency_funding():
    seed()
    with connection() as db:
        db.execute(
            "UPDATE venue_account_events SET currency='BTC',payload_json="
            "json_set(payload_json,'$.currency','BTC') WHERE event_type='trade_fill'"
        )
    sync_funding_settlements(ACCOUNT)
    result = get_strategy_financials(FUNDING)
    assert result["fundingPnl"] == "0.00319691"
    assert result["fees"] is None
    assert result["netPnl"] is None
    assert "historical_fx_unavailable" in result["issues"]


def test_other_symbol_and_pre_open_settlements_do_not_poison_owned_total():
    event, _ = seed()
    other = deepcopy(event)
    other.update(externalEventId="funding:other", instrumentId="instrument_xau_usdt_perp",
                 symbol="XAUTUSDT", amount="-100")
    persist(other)
    earlier = deepcopy(event)
    earlier.update(externalEventId="funding:earlier", occurredAt=ANCHOR, amount="100")
    persist(earlier)
    sync_funding_settlements(ACCOUNT)
    result = get_strategy_financials(FUNDING)
    assert result["fundingPnl"] == "0.00319691"
    assert result["unattributedEvents"] == []


def test_account_sync_ingests_then_posts_without_order_submission(monkeypatch):
    _, snapshot = seed()
    import httpx

    from app import account_performance
    from app import live_venue_snapshot_sync as sync
    monkeypatch.setattr(account_performance, "sync_capital_history", lambda *_: None)
    monkeypatch.setattr(account_performance, "persist_valuation_rates", lambda *_: None)
    reads = []
    def get(path, *, params):
        reads.append((path, params))
        return httpx.Response(
            200, request=httpx.Request("GET", "http://runtime.test"), json=snapshot
        )
    monkeypatch.setattr(sync, "runtime_get", get)
    sync._sync_one_account(ACCOUNT)
    sync._sync_one_account(ACCOUNT)
    assert reads == [("/venue/account-snapshot", {"accountId": ACCOUNT})] * 2
    with connection() as db:
        assert db.execute("SELECT count(*) FROM financial_facts").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
