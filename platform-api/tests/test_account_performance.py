import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.account_performance import adjusted_drawdowns, daily_pnl, persist_capital_window
from app.schema_migrations import PLATFORM_MIGRATIONS
from app.schemas import StrategyEquityHistoryPointResponse as Point


@pytest.fixture
def db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    # This unit fixture needs only capital history and valuation provenance.
    for migration in PLATFORM_MIGRATIONS:
        if migration.version in (24, 25):
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


def test_capital_flow_offset_is_compared_as_an_instant(db):
    window(db, [(0.5, "USD", "100")])
    db.execute("UPDATE account_capital_movements SET occurred_at='2026-09-01T08:30:00+08:00'")
    assert daily_pnl(db, "a", points([100, 200]), "mt5_trading", "equity")[1][0] == 0


def test_missing_closing_day_is_not_booked_as_single_day_profit(db):
    window(db)
    db.execute("UPDATE account_capital_coverage SET end_at='2026-09-04T00:00:00Z'")
    rows = points([100, 130])
    rows[1].as_of = START + timedelta(days=2)
    assert daily_pnl(db, "a", rows, "mt5_trading", "equity")[1] == (
        None, None, "missing_daily_baseline"
    )


def test_daily_gap_uses_beijing_midnight(db):
    window(db)
    db.execute("UPDATE account_capital_coverage SET end_at='2026-09-04T00:00:00Z'")
    rows = points([100, 110])
    # Consecutive UTC dates, but September 2 has no Beijing closing observation.
    rows[0].as_of = START + timedelta(hours=15, minutes=59)
    rows[1].as_of = START + timedelta(days=1, hours=16)
    assert daily_pnl(db, "a", rows, "mt5_trading", "equity")[1][2] == "missing_daily_baseline"


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


def test_duplicate_points_keep_invalid_equity_classification(db):
    window(db)
    duplicate_points = points([100, 100, 90])
    duplicate_points[1].as_of = duplicate_points[0].as_of
    values = adjusted_drawdowns(
        db,
        "a",
        duplicate_points,
        "mt5_trading",
        "equity",
    )
    assert [state for _, state in values] == ["baseline", "invalid_equity", "estimated"]


def test_usdt_is_not_usd_and_gap_is_not_bridged(db):
    window(db, [(0.5, "USDT", "100")])
    result = adjusted_drawdowns(db, "a", points([100, 200, 180]), "mt5_trading", "equity")
    assert result[1] == (None, "missing_flow_valuation")
    assert result[2][1] == "estimated"


def test_event_scope_and_valuation(db):
    window(db, [(1, "USDT", "100")])
    db.execute(
        "INSERT INTO account_valuation_rates (account_id,currency,as_of,usd_rate) VALUES (?,?,?,?)",
        ("a", "USDT", (START + timedelta(hours=1)).isoformat(), "0.99"),
    )
    assert adjusted_drawdowns(db, "a", points([100, 199]), "mt5_trading", "equity")[-1][0] == 0
    assert adjusted_drawdowns(db, "a", points([100, 199]), "full_account", "equity")[-1][0] is None


def test_equal_distance_rates_choose_lowest_decimal_rate(db):
    window(db, [(1, "USDT", "100")])
    db.executemany(
        "INSERT INTO account_valuation_rates (account_id,currency,as_of,usd_rate) VALUES (?,?,?,?)",
        [
            ("a", "USDT", (START + timedelta(minutes=55)).isoformat(), "1.01"),
            ("a", "USDT", (START + timedelta(hours=1, minutes=5)).isoformat(), "0.99"),
        ],
    )
    result = adjusted_drawdowns(db, "a", points([100, 199]), "mt5_trading", "equity")
    assert result[-1][0] == Decimal(0)


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


def test_overlapping_windows_are_merged_for_contiguous_coverage(db):
    window(db)
    db.execute(
        "UPDATE account_capital_coverage SET end_at=?",
        ((START + timedelta(hours=1)).isoformat(),),
    )
    db.execute(
        "INSERT INTO account_capital_coverage VALUES(?,?,?,?,?)",
        (
            "a",
            "mt5_trading",
            (START + timedelta(minutes=30)).isoformat(),
            (START + timedelta(hours=2)).isoformat(),
            START.isoformat(),
        ),
    )
    result = adjusted_drawdowns(db, "a", points([100, 110, 121]), "mt5_trading", "equity")
    assert result[1][1] == "estimated"
    assert result[2][1] == "estimated"


def test_nonpositive_capital_is_unavailable(db):
    window(db, [(0.5, "USD", "-300")])
    assert adjusted_drawdowns(db, "a", points([100, 100]), "mt5_trading", "equity")[-1] == (
        None,
        "invalid_capital",
    )


def test_daily_pnl_excludes_withdrawals_and_deposits(db):
    window(db, [(1, "USD", "-50"), (2, "USD", "100")])
    series = daily_pnl(db, "a", points([100, 50, 150, 135]), "mt5_trading", "equity")
    assert [x[0] for x in series] == [None, Decimal(0), Decimal(0), Decimal(-15)]


def test_daily_pnl_rate_uses_the_capital_at_work(db):
    window(db, [(0.5, "USD", "100")])
    series = daily_pnl(db, "a", points([100, 215, 193.5]), "mt5_trading", "equity")
    assert series[2][:2] == (Decimal("-21.5"), Decimal("-10.0"))


def test_daily_pnl_unqueried_history_is_not_zero(db):
    assert daily_pnl(db, "a", points([100, 90]), "mt5_trading", "equity")[-1] == (
        None,
        None,
        "missing_history",
    )


def test_daily_pnl_reports_an_unclassified_day_without_suppressing_the_next(db):
    window(db, [(1, "USD", None)])
    series = daily_pnl(db, "a", points([100, 100, 110]), "mt5_trading", "equity")
    assert series[1] == (None, None, "unclassified_flow")
    assert series[2][0] == Decimal(10)


def test_daily_pnl_never_guesses_a_flow_valuation(db):
    window(db, [(0.5, "USDT", "100")])
    series = daily_pnl(db, "a", points([100, 200, 180]), "mt5_trading", "equity")
    assert series[1] == (None, None, "missing_flow_valuation")
    # The unvaluable interval carries no amount, and the next day is still read
    # against its own closings rather than inheriting the gap.
    assert series[2] == (Decimal(-20), Decimal(-10.0), "estimated")
