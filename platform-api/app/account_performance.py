"""Observed-period, cash-flow-adjusted performance. Never feeds trading/accounting."""

import json
import logging
from bisect import bisect_left
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.database import connection
from app.venue_reconciliation import runtime_get

log = logging.getLogger(__name__)


def stamp(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Capital history requires timezone-aware timestamps")
    return result.astimezone(UTC)


def persist_valuation_rates(db, account_id, snapshot):
    for balance in snapshot.get("balances", []):
        if balance.get("usdValue") is None or not balance.get("currency"):
            continue
        equity = Decimal(str(balance["equity"]))
        usd = Decimal(str(balance["usdValue"]))
        if not equity.is_finite() or not usd.is_finite() or equity == 0 or usd / equity <= 0:
            continue
        db.execute(
            "INSERT OR IGNORE INTO account_valuation_rates "
            "(account_id,currency,as_of,usd_rate) VALUES (?,?,?,?)",
            (
                account_id,
                balance["currency"],
                stamp(balance["asOf"]).isoformat(),
                str(usd / equity),
            ),
        )


def persist_capital_window(db, account_id, payload, start, end):
    if (
        payload.get("accountId") != account_id
        or stamp(payload["startTime"]) != start
        or stamp(payload["endTime"]) != end
    ):
        raise ValueError("Capital history account/window mismatch")
    scopes = payload["scopes"]
    if not scopes or any(
        s not in {"full_account", "unified_trading", "mt5_trading"} for s in scopes
    ):
        raise ValueError("Invalid capital history scope")
    for event in payload["events"]:
        event_time = stamp(event["occurredAt"])
        # Funding history has second precision and inclusive endpoints.
        if event_time < start or event_time > end:
            continue
        scope, identity = event["assetScope"], event["externalEventId"]
        if scope not in scopes or not identity or not event["currency"]:
            raise ValueError("Invalid capital movement")
        amount = event["amount"]
        if amount is not None and not Decimal(amount).is_finite():
            raise ValueError("Invalid capital movement amount")
        values = (event_time.isoformat(), event["currency"], amount, event["eventType"])
        previous = db.execute(
            "SELECT occurred_at,currency,amount,event_type,payload_json FROM "
            "account_capital_movements WHERE account_id=? AND asset_scope=? AND "
            "external_event_id=?",
            (account_id, scope, identity),
        ).fetchone()
        if previous and tuple(previous)[:4] != values:
            # Resolve an unknown classification only against identical native evidence.
            prior_raw = json.loads(previous[4]).get("raw")
            if (
                previous[2] is None
                and amount is not None
                and tuple(previous)[:2] == values[:2]
                and previous[3] == values[3]
                and prior_raw is not None
                and prior_raw == event.get("raw")
            ):
                db.execute(
                    "UPDATE account_capital_movements SET amount=?,payload_json=? "
                    "WHERE account_id=? AND asset_scope=? AND external_event_id=?",
                    (amount, json.dumps(event, sort_keys=True), account_id, scope, identity),
                )
            else:
                raise ValueError("Capital movement changed after persistence")
        db.execute(
            "INSERT OR IGNORE INTO account_capital_movements VALUES (?,?,?,?,?,?,?,?)",
            (account_id, identity, scope, *values, json.dumps(event, sort_keys=True)),
        )
    for scope in scopes:
        db.execute(
            "INSERT INTO account_capital_coverage VALUES (?,?,?,?,?) ON "
            "CONFLICT(account_id,asset_scope,start_at) DO UPDATE SET "
            "end_at=excluded.end_at,updated_at=excluded.updated_at",
            (account_id, scope, start.isoformat(), end.isoformat(), datetime.now(UTC).isoformat()),
        )


def sync_capital_history(account_id, *, force=False):
    """One bounded window per snapshot cycle; oldest first, then overlapping refresh."""
    now = datetime.now(UTC)
    with connection() as db:
        state = db.execute(
            "SELECT attempted_at FROM account_capital_sync WHERE account_id=?", (account_id,)
        ).fetchone()
        if not force and state and now - stamp(state[0]) < timedelta(seconds=60):
            return
        bounds = db.execute(
            "SELECT min(as_of),max(as_of) FROM account_risk_snapshots WHERE account_id=?",
            (account_id,),
        ).fetchone()
        if not bounds or not bounds[0]:
            return
        covered = db.execute(
            "SELECT max(end_at) FROM account_capital_coverage WHERE account_id=?", (account_id,)
        ).fetchone()[0]
        latest = min(stamp(bounds[1]), now - timedelta(seconds=60))
        start = stamp(covered) - timedelta(minutes=10) if covered else stamp(bounds[0])
        end = min(start + timedelta(days=7), latest)
        if end <= start:
            return
        db.execute(
            "INSERT INTO account_capital_sync VALUES (?,?,'syncing',NULL) ON "
            "CONFLICT(account_id) DO UPDATE SET "
            "attempted_at=excluded.attempted_at,status='syncing',error_code=NULL",
            (account_id, now.isoformat()),
        )
    try:
        response = runtime_get(
            "/venue/capital-flows",
            params={
                "accountId": account_id,
                "startTime": start.isoformat(),
                "endTime": end.isoformat(),
            },
        )
        response.raise_for_status()
        with connection() as db:
            persist_capital_window(db, account_id, response.json(), start, end)
            db.execute(
                "UPDATE account_capital_sync SET status='ready',error_code=NULL WHERE account_id=?",
                (account_id,),
            )
    except Exception as exc:
        # Preserve previous coverage and distinguish a failed read from an empty ledger.
        code = f"{type(exc).__name__}"
        if getattr(exc, "response", None) is not None:
            code += f":{exc.response.status_code}"
        with connection() as db:
            db.execute(
                "UPDATE account_capital_sync SET status='failed',error_code=? WHERE account_id=?",
                (code, account_id),
            )
        log.warning("Capital history sync failed for %s: %s", account_id, code)
        if force:
            raise


def _classified_intervals(db, account_id, points, scope, value_key):
    """Yield the classified facts of every consecutive interval, oldest first.

    Each item is ``(initial, final, flow, denominator, reason)``. The capital-flow
    classification, coverage window, unclassified-flow handling, currency
    valuation and non-positive-capital rule live here so the drawdown series and
    the daily P&L series can never drift apart.
    """
    raw_windows = [
        (stamp(r[0]), stamp(r[1]))
        for r in db.execute(
            "SELECT start_at,end_at FROM account_capital_coverage WHERE account_id=? "
            "AND asset_scope=? ORDER BY start_at",
            (account_id, scope),
        )
    ]
    # Coverage is a union of windows. Merge it once so each interval can advance
    # through the ordered union instead of rescanning every persisted window.
    windows = []
    for start, end in sorted(raw_windows):
        if windows and start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(windows[-1][1], end))
        else:
            windows.append((start, end))
    events = db.execute(
        "SELECT occurred_at,currency,amount FROM account_capital_movements WHERE "
        "account_id=? AND asset_scope=? AND (amount IS NULL OR amount!='0') AND "
        "julianday(occurred_at)>=julianday(?) AND julianday(occurred_at)<=julianday(?) "
        "ORDER BY julianday(occurred_at)",
        (
            account_id,
            scope,
            stamp(points[0].as_of).isoformat(),
            stamp(points[-1].as_of).isoformat(),
        ),
    ).fetchall()
    events = [(stamp(row[0]), row[1], row[2]) for row in events]
    point_currencies = {point.currency.upper() for point in points if point.currency}
    rate_currencies = {
        currency
        for _, currency, amount in events
        if amount is not None
        and Decimal(amount) != 0
        and any(currency.upper() != point_currency for point_currency in point_currencies)
    }
    rates = []
    if rate_currencies:
        placeholders = ",".join("?" for _ in rate_currencies)
        event_times = [
            occurred_at for occurred_at, currency, amount in events if currency in rate_currencies
        ]
        rates = db.execute(
            "SELECT currency,as_of,usd_rate FROM account_valuation_rates WHERE "
            f"account_id=? AND currency IN ({placeholders}) "
            "AND julianday(as_of)>=julianday(?) AND julianday(as_of)<=julianday(?)",
            (
                account_id,
                *sorted(rate_currencies),
                (min(event_times) - timedelta(minutes=5)).isoformat(),
                (max(event_times) + timedelta(minutes=5)).isoformat(),
            ),
        ).fetchall()
    rates_by_currency = {}
    for row in rates:
        rates_by_currency.setdefault(row[0], []).append((stamp(row[1]), row[2]))
    for currency in rates_by_currency:
        rates_by_currency[currency].sort(key=lambda item: item[0])
    rate_times = {
        currency: [as_of for as_of, _ in values]
        for currency, values in rates_by_currency.items()
    }

    def nearest_rate(currency, occurred_at):
        candidates = rates_by_currency.get(currency, ())
        if not candidates:
            return None
        times = rate_times[currency]
        index = bisect_left(times, occurred_at)
        nearest = None
        candidate_indexes = set()
        for candidate_index in (index - 1, index):
            if 0 <= candidate_index < len(candidates):
                candidate_time = candidates[candidate_index][0]
                left = candidate_index
                while left >= 0 and candidates[left][0] == candidate_time:
                    candidate_indexes.add(left)
                    left -= 1
                right = candidate_index + 1
                while right < len(candidates) and candidates[right][0] == candidate_time:
                    candidate_indexes.add(right)
                    right += 1
        nearest = None
        for candidate_index in candidate_indexes:
            if 0 <= candidate_index < len(candidates):
                candidate = candidates[candidate_index]
                distance = abs((candidate[0] - occurred_at).total_seconds())
                candidate_value = (distance, Decimal(candidate[1]))
                if nearest is None or candidate_value < nearest:
                    nearest = candidate_value
        return nearest

    coverage_index = 0
    event_index = 0
    for previous, point in zip(points, points[1:], strict=False):
        a, b = stamp(previous.as_of), stamp(point.as_of)
        initial, final = getattr(previous, value_key), getattr(point, value_key)
        reason = None
        if initial is None or final is None or initial <= 0 or final < 0 or b <= a:
            reason = "invalid_equity"
        else:
            while coverage_index < len(windows) and windows[coverage_index][1] <= a:
                coverage_index += 1
            if (
                coverage_index >= len(windows)
                or windows[coverage_index][0] > a
                or windows[coverage_index][1] < b
            ):
                reason = "missing_history"
        flow = weighted = Decimal(0)
        while event_index < len(events) and events[event_index][0] <= a:
            event_index += 1
        interval_event_index = event_index
        while interval_event_index < len(events) and events[interval_event_index][0] <= b:
            t, currency, raw_amount = events[interval_event_index]
            interval_event_index += 1
            if raw_amount is None:
                reason = "unclassified_flow"
                continue
            amount = Decimal(raw_amount)
            if amount and currency.upper() != (point.currency or "").upper():
                nearest = nearest_rate(currency, t)
                if point.currency != "USD" or nearest is None or nearest[0] > 300:
                    reason = "missing_flow_valuation"
                    continue
                amount *= nearest[1]
            flow += amount
            weighted += (
                amount
                * Decimal(str((b - t).total_seconds()))
                / Decimal(str((b - a).total_seconds()))
            )
        event_index = interval_event_index
        denominator = (initial or Decimal(0)) + weighted
        if denominator <= 0:
            reason = reason or "invalid_capital"
        yield initial, final, flow, denominator, reason


def adjusted_drawdowns(db, account_id, points, scope, value_key):
    if not points:
        return []
    nav = peak = Decimal(1)
    result = [(None, "baseline")]
    for initial, final, flow, denominator, reason in _classified_intervals(
        db, account_id, points, scope, value_key
    ):
        if reason:
            result.append((None, reason or "history_gap"))
            # Coverage is fetched in bounded windows and can leave a small
            # interval between two successful windows.  Keep that interval
            # explicitly unavailable, then establish a fresh baseline from
            # the first point after the gap so a current drawdown does not
            # disappear forever because of an old sync hole.
            nav = peak = Decimal(1)
            continue
        nav *= 1 + (final - initial - flow) / denominator
        if nav < 0:
            result.append((None, "invalid_capital"))
            nav = peak = Decimal(1)
            continue
        peak = max(peak, nav)
        result.append(((nav / peak - 1) * 100, "estimated"))
    return result


def daily_pnl(db, account_id, points, scope, value_key):
    """Cash-flow-adjusted P&L per interval between same-scope daily closings.

    The reported amount is the same ``final - initial - flow`` the drawdown series
    uses, so a day's trading result, funding, fees, swap and unrealised mark far
    are all inside it while deposits and withdrawals are not. The companion rate
    is that amount over the capital actually at work during the day.

    An interval whose history was never queried, whose flow is unclassified, or
    whose capital went non-positive is reported as unavailable rather than as a
    zero. Intervals do not chain: a day that cannot be valued does not suppress
    the next day, because each interval is measured against its own closings.
    """
    if not points:
        return []
    result = [(None, None, "baseline")]
    for index, (initial, final, flow, denominator, reason) in enumerate(
        _classified_intervals(db, account_id, points, scope, value_key), start=1
    ):
        if (stamp(points[index].as_of).date() - stamp(points[index - 1].as_of).date()).days > 1:
            reason = "missing_daily_baseline"
        if reason:
            result.append((None, None, reason))
            continue
        pnl = final - initial - flow
        result.append((pnl, pnl / denominator * 100, "estimated"))
    return result


def enrich_performance(account_id, points):
    if not points:
        return
    with connection() as db:
        for scope, value_key, field, quality in (
            (points[-1].asset_scope, "equity", "equity_drawdown", "equity_drawdown_quality"),
            (
                "full_account",
                "total_assets",
                "total_assets_drawdown",
                "total_assets_drawdown_quality",
            ),
        ):
            for point, (value, state) in zip(
                points, adjusted_drawdowns(db, account_id, points, scope, value_key), strict=True
            ):
                setattr(point, field, value)
                setattr(point, quality, state)
