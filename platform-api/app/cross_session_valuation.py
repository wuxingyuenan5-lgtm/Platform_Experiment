"""Cross-only reporting cutoffs; never used by live balances or execution."""

import json
import time
from bisect import bisect_left
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache

from app.account_performance import stamp
from app.config import get_settings
from app.database import connection
from app.pnl_reporting import day_start


def is_cross(db, instance_id):
    row = db.execute(
        "SELECT d.strategy_key FROM strategy_instances s JOIN strategy_definitions d "
        "ON d.id=s.strategy_definition_id WHERE s.id=?",
        (instance_id,),
    ).fetchone()
    return bool(row and row[0] == "cross_venue_spread")


def valid_observation(payload):
    # Exit guard windows still have valid marks; execution permission is not a calendar.
    return all(
        payload.get(venue, {}).get("marketStatus") == "open"
        and payload.get(venue, {}).get("status") == "available"
        and payload.get(venue, {}).get("executionBlockReason") != "quote_stale"
        for venue in ("mt5", "bybit")
    )


def legacy_observation(db, instance_id, at):
    """Older receipts lacked marketStatus. A changing native MT5 quote proves
    activity; a mere repeated poll timestamp never proves an open market."""
    rows = db.execute(
        "SELECT payload_json FROM market_spread_snapshots "
        "WHERE strategy_key='cross_venue_spread' AND strategy_instance_id=? "
        "AND observed_at>=? AND observed_at<=? ORDER BY observed_at",
        (instance_id, (stamp(at) - timedelta(seconds=120)).isoformat(), at),
    ).fetchall()
    previous, selected = None, None
    for row in rows:
        p = json.loads(row[0])
        mt5, bybit = p.get("mt5", {}), p.get("bybit", {})
        quote = mt5.get("quote")
        if (
            mt5.get("marketStatus") is None
            and mt5.get("status") == "available"
            and bybit.get("status") == "available"
            and quote
            and previous
            and (quote.get("bid"), quote.get("ask")) != previous
        ):
            mt5["marketStatus"] = "open"
            bybit.setdefault("marketStatus", "open")
            if valid_observation(p):
                selected = p
        previous = (quote.get("bid"), quote.get("ask")) if quote else None
    return selected


def load_sessions(instance_id):
    # The archive scan took 5 seconds on the live dataset. Share a bounded 30s
    # reporting cache; balances, risk and execution do not consume this cache.
    with connection() as db:
        if not is_cross(db, instance_id):
            return None
    return _load_sessions(get_settings().database_path, instance_id, int(time.monotonic() // 30))


@lru_cache(maxsize=8)
def _load_sessions(database_path, instance_id, bucket):
    """Read actual recorded market states, including holidays and broker timezone rules."""
    with connection() as db:
        if not is_cross(db, instance_id):
            return None
        rows = db.execute(
            "SELECT date(observed_at,'+8 hours') day, max(observed_at) latest, count(*) n "
            "FROM market_spread_snapshots WHERE strategy_key='cross_venue_spread' "
            "AND strategy_instance_id=? AND observed_at>=? AND observed_at<=? "
            "GROUP BY day ORDER BY day",
            (
                instance_id,
                (datetime.now(UTC) - timedelta(days=400)).date().isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        ).fetchall()
    observations, excluded, latest = {}, {}, None
    for row in rows:
        valid, latest, closed_only = _day_session(
            database_path, instance_id, row["day"], row["latest"], row["n"]
        )
        closed = latest.get("mt5", {}).get("marketStatus") == "closed"
        if valid and (
            closed or (stamp(latest["asOf"]) - stamp(valid["asOf"])).total_seconds() <= 300
        ):
            observations[row["day"]] = valid
        else:
            excluded[row["day"]] = "market_closed" if closed_only else "session_marks_unavailable"
        day_end = min(
            day_start(date.fromisoformat(row["day"]) + timedelta(days=1)), datetime.now(UTC)
        )
        if (day_end - stamp(latest["asOf"])).total_seconds() > 300:
            # A known quote earlier in a day is a usable as-of valuation, but
            # does not prove the day's close or an entire holiday closure.
            excluded[row["day"]] = "session_marks_unavailable"
    return {"observations": observations, "excluded": excluded, "latest": latest}


@lru_cache(maxsize=512)
def _day_session(database_path, instance_id, day, latest_at, count):
    # Historical days reuse their exact archive revision; a backfill changes count.
    start = day_start(date.fromisoformat(day)).isoformat()
    with connection() as db:
        latest = json.loads(
            db.execute(
                "SELECT payload_json FROM market_spread_snapshots "
                "WHERE strategy_key='cross_venue_spread' "
                "AND strategy_instance_id=? AND observed_at=? LIMIT 1",
                (instance_id, latest_at),
            ).fetchone()[0]
        )
        if latest.get("mt5", {}).get("marketStatus") not in {"open", "closed"}:
            legacy = legacy_observation(db, instance_id, latest_at)
            return legacy, latest, False
        row = db.execute(
            "SELECT payload_json FROM market_spread_snapshots "
            "WHERE strategy_key='cross_venue_spread' AND strategy_instance_id=? "
            "AND observed_at>=? AND observed_at<=? "
            "AND json_extract(payload_json,'$.mt5.marketStatus')='open' "
            "AND json_extract(payload_json,'$.bybit.marketStatus')='open' "
            "AND json_extract(payload_json,'$.mt5.status')='available' "
            "AND json_extract(payload_json,'$.bybit.status')='available' "
            "AND COALESCE(json_extract(payload_json,'$.mt5.executionBlockReason'),'') "
            "!='quote_stale' "
            "AND COALESCE(json_extract(payload_json,'$.bybit.executionBlockReason'),'') "
            "!='quote_stale' ORDER BY observed_at DESC LIMIT 1",
            (instance_id, start, latest_at),
        ).fetchone()
        non_closed = None
        if row is None:
            non_closed = db.execute(
                "SELECT 1 FROM market_spread_snapshots "
                "WHERE strategy_key='cross_venue_spread' AND strategy_instance_id=? "
                "AND observed_at>=? AND observed_at<=? "
                "AND COALESCE(json_extract(payload_json,'$.mt5.marketStatus'),'unknown') "
                "!='closed' LIMIT 1",
                (instance_id, start, latest_at),
            ).fetchone()
    closed_only = latest.get("mt5", {}).get("marketStatus") == "closed" and not non_closed
    return json.loads(row[0]) if row else None, latest, closed_only


def reporting_day(occurred_at, observations):
    cutoffs = [(stamp(p["asOf"]), day) for day, p in sorted(observations.items())]
    index = bisect_left([at for at, _ in cutoffs], stamp(occurred_at))
    return cutoffs[index][1] if index < len(cutoffs) else None


def historical_snapshots(snapshots, observation, orders):
    """Rebuild only the read projection at a retained two-leg observation."""
    result = []
    at = observation["asOf"]
    with connection() as db:
        for row in snapshots:
            payload = json.loads(row["payload_json"])
            venue = payload.get("venue")
            positions = []
            for p in observation.get(venue, {}).get("positions", []):
                if p.get("accountId") != row["account_id"]:
                    continue
                order = next(
                    (
                        o
                        for o in orders
                        if o["account_id"] == row["account_id"] and o["symbol"] == p["symbol"]
                    ),
                    None,
                )
                if order is None:
                    continue
                positions.append(
                    {
                        "instrumentId": order["instrument_id"],
                        "symbol": p["symbol"],
                        "externalPositionId": p.get("externalId") if venue == "mt5" else None,
                        "netQuantity": str(
                            -abs(Decimal(str(p["quantity"])))
                            if p.get("side") == "sell"
                            else Decimal(str(p["quantity"]))
                        ),
                        "unrealizedPnl": p.get("unrealizedPnl"),
                        "currentPrice": observation[venue].get("quote", {}).get("mid"),
                        "currency": p.get("currency"),
                        "asOf": at,
                    }
                )
            if venue == "mt5" and positions:
                risk = db.execute(
                    "SELECT payload_json FROM account_risk_snapshots WHERE account_id=? "
                    "AND as_of>=? AND as_of<=? ORDER BY as_of DESC LIMIT 1",
                    (
                        row["account_id"],
                        (stamp(at) - timedelta(seconds=120)).isoformat(),
                        stamp(at).isoformat(),
                    ),
                ).fetchone()
                observed_positions = [
                    p
                    for p in observation[venue].get("positions", [])
                    if p.get("accountId") == row["account_id"]
                ]
                if risk and len(positions) == len(observed_positions):
                    raw = json.loads(risk[0]).get("unrealizedPnl")
                    if raw is not None and all(p["unrealizedPnl"] is not None for p in positions):
                        for p in positions:
                            p["swap"] = "0"
                        positions[0]["swap"] = str(
                            Decimal(str(raw))
                            - sum(Decimal(str(p["unrealizedPnl"])) for p in positions)
                        )
            payload.update(positions=positions, asOf=at)
            result.append({**dict(row), "as_of": at, "payload_json": json.dumps(payload)})
    return result


def filter_capital_history(instance_id, account_id, points):
    """Filter observations first, then recompute flow-adjusted drawdown on that path."""
    from app.account_performance import enrich_performance
    from app.schemas import StrategyEquityHistoryPointResponse

    sessions = load_sessions(instance_id)
    if sessions is None or not points:
        return []
    with connection() as db:
        if not is_cross(db, instance_id):
            return []

        def eligible(at):
            row = db.execute(
                "SELECT payload_json FROM market_spread_snapshots "
                "WHERE strategy_key='cross_venue_spread' AND strategy_instance_id=? "
                "AND observed_at>=? AND observed_at<=? ORDER BY observed_at DESC LIMIT 1",
                (instance_id, (at - timedelta(seconds=120)).isoformat(), at.isoformat()),
            ).fetchone()
            if not row:
                return False
            p = json.loads(row[0])
            return valid_observation(p) or (
                p.get("mt5", {}).get("marketStatus") is None
                and legacy_observation(db, instance_id, at.isoformat()) is not None
            )

        selected = []
        for point in points:
            at = stamp(point.as_of)
            if sessions["excluded"].get(at.date().isoformat()) == "market_closed":
                continue
            if eligible(at):
                selected.append(point.model_copy(deep=True))
        # The live chart retains 1000 recent samples and can consist entirely
        # of closed-market points. Retrieve each valid session close from the
        # original archive instead of filtering that truncated slice to empty.
        for observation in sessions["observations"].values():
            at = stamp(observation["asOf"])
            if at > stamp(points[-1].as_of):
                continue
            row = db.execute(
                "SELECT * FROM account_risk_snapshots WHERE account_id=? "
                "AND asset_scope=? AND currency=? AND as_of>=? AND as_of<=? "
                "AND equity IS NOT NULL ORDER BY as_of DESC LIMIT 1",
                (
                    account_id,
                    points[-1].asset_scope,
                    points[-1].currency,
                    (at - timedelta(seconds=120)).isoformat(),
                    at.isoformat(),
                ),
            ).fetchone()
            if row and eligible(stamp(row["as_of"])):
                selected.append(
                    StrategyEquityHistoryPointResponse(
                        asOf=row["as_of"],
                        equity=row["equity"],
                        currency=row["currency"],
                        assetScope=row["asset_scope"],
                        totalAssets=row["total_assets"],
                    )
                )
    selected = sorted({stamp(p.as_of): p for p in selected}.values(), key=lambda p: stamp(p.as_of))
    enrich_performance(account_id, selected)
    return selected
