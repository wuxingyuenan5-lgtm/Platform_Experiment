from datetime import UTC, datetime, timedelta
from decimal import Decimal
import sqlite3

import pytest

from app.account_performance import adjusted_drawdowns, persist_capital_window
from app.schemas import StrategyEquityHistoryPointResponse as Point
from app.schema_migrations import PLATFORM_MIGRATIONS


@pytest.fixture
def db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    for migration in PLATFORM_MIGRATIONS:
        if migration.version >= 24:
            for sql in migration.statements:
                db.execute(sql)
    yield db
    db.close()


START = datetime(2026, 9, 1, tzinfo=UTC)


def points(values, currency="USD"):
    return [
        Point(
            asOf=START + timedelta(hours=i),
            equity=Decimal(str(v)),
            currency=currency,
            assetScope="mt5_trading",
        )
        for i, v in enumerate(values)
    ]


def window(db, movements=()):
    events = [
        {
            "externalEventId": str(i),
            "assetScope": "mt5_trading",
            "occurredAt": (START + timedelta(hours=t)).isoformat(),
            "currency": currency,
            "amount": amount,
            "eventType": "balance",
        }
        for i, (t, currency, amount) in enumerate(movements)
    ]
    payload = {
        "accountId": "a",
        "startTime": START.isoformat(),
        "endTime": (START + timedelta(hours=3)).isoformat(),
        "scopes": ["mt5_trading"],
        "events": events,
    }
    persist_capital_window(db, "a", payload, START, START + timedelta(hours=3))
    return payload


def test_withdrawal_and_deposit_are_not_performance(db):
    window(db, [(1, "USD", "-50"), (2, "USD", "100")])
    values = adjusted_drawdowns(db, "a", points([100, 50, 150, 135]), "mt5_trading", "equity")
    assert [x[0] for x in values] == [None, Decimal(0), Decimal(0), Decimal(-10)]


def test_weighted_flow_and_peak(db):
    window(db, [(0.5, "USD", "100")])
    values = adjusted_drawdowns(db, "a", points([100, 215, 193.5]), "mt5_trading", "equity")
    assert values[-1][0] == Decimal(-10)


def test_unqueried_history_is_not_zero(db):
    assert adjusted_drawdowns(db, "a", points([100, 90]), "mt5_trading", "equity")[-1] == (
        None,
        "missing_history",
    )


def test_usdt_is_not_usd_and_gap_is_not_bridged(db):
    window(db, [(0.5, "USDT", "100")])
    result = adjusted_drawdowns(db, "a", points([100, 200, 180]), "mt5_trading", "equity")
    assert result[1] == (None, "missing_flow_valuation")
    assert result[2] == (None, "history_gap")


def test_event_scope_and_valuation(db):
    window(db, [(1, "USDT", "100")])
    db.execute(
        "INSERT INTO account_valuation_rates (account_id,currency,as_of,usd_rate) VALUES (?,?,?,?)",
        ("a", "USDT", (START + timedelta(hours=1)).isoformat(), "0.99"),
    )
    assert adjusted_drawdowns(db, "a", points([100, 199]), "mt5_trading", "equity")[-1][0] == 0
    assert adjusted_drawdowns(db, "a", points([100, 199]), "full_account", "equity")[-1][0] is None


def test_idempotence_and_conflict(db):
    payload = window(db, [(1, "USD", "100")])
    persist_capital_window(db, "a", payload, START, START + timedelta(hours=3))
    assert db.execute("SELECT count(*) FROM account_capital_movements").fetchone()[0] == 1
    payload["events"][0]["amount"] = "101"
    with pytest.raises(ValueError, match="changed"):
        persist_capital_window(db, "a", payload, START, START + timedelta(hours=3))


def test_unknown_classification_fails_closed(db):
    window(db, [(1, "USD", None)])
    assert (
        adjusted_drawdowns(db, "a", points([100, 100]), "mt5_trading", "equity")[-1][1]
        == "unclassified_flow"
    )


def test_disjoint_windows_do_not_claim_coverage(db):
    window(db)
    db.execute(
        "UPDATE account_capital_coverage SET end_at=?",
        ((START + timedelta(minutes=20)).isoformat(),),
    )
    db.execute(
        "INSERT INTO account_capital_coverage VALUES(?,?,?,?,?)",
        (
            "a",
            "mt5_trading",
            (START + timedelta(minutes=40)).isoformat(),
            (START + timedelta(hours=2)).isoformat(),
            START.isoformat(),
        ),
    )
    assert adjusted_drawdowns(db, "a", points([100, 110]), "mt5_trading", "equity")[-1] == (
        None,
        "missing_history",
    )


def test_nonpositive_capital_is_unavailable(db):
    window(db, [(0.5, "USD", "-300")])
    assert adjusted_drawdowns(db, "a", points([100, 100]), "mt5_trading", "equity")[-1] == (
        None,
        "invalid_capital",
    )
