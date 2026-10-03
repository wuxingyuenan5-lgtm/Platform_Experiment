"""Daily strategy valuation from retained venue observations, never account returns."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.database import connection
from app.pnl_reporting import day_start, reporting_date

ZERO = Decimal(0)


def instant(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)


def daily_marks(
    strategy_id, history, orders, events, current_marks, to_base, *, reporting_sessions=None
):
    """Return end-of-day owned unrealized values and reasons for unavailable marks.

    Historical Cross observations retain both quotes and ticket-level positions.
    Spot marks come from observed native coin valuations; perpetual marks require
    their own settlement price, not the spot price. Missing days stay missing.
    """
    if not history:
        return {}, {}
    history = sorted(history, key=lambda item: item[0])
    specifications = {(o["account_id"], o["instrument_id"]): o for o in orders}
    first = reporting_date(history[0][0])
    today = reporting_date(datetime.now(UTC))
    day = max(first, today - timedelta(days=400))
    cursor, held = 0, {}
    values, reasons = {}, {}
    with connection() as db:
        while day <= today:
            end = day_start(day + timedelta(days=1))
            key = day.isoformat()
            session = (reporting_sessions or {}).get("observations", {}).get(key)
            if reporting_sessions is not None:
                if session is None or key in reporting_sessions.get("excluded", {}):
                    values[key] = None
                    reasons[key] = reporting_sessions.get("excluded", {}).get(
                        key, "session_marks_unavailable"
                    )
                    day += timedelta(days=1)
                    continue
                end = instant(session["asOf"]) + timedelta(microseconds=1)
            while cursor < len(history) and history[cursor][0] < end:
                held = history[cursor][1]
                cursor += 1
            spread = session
            live_day = day == today and reporting_sessions is None
            if reporting_sessions is None and any(k[2] for k in held):
                row = db.execute(
                    "SELECT payload_json,observed_at FROM market_spread_snapshots "
                    "WHERE strategy_key='cross_venue_spread' AND strategy_instance_id=? "
                    "AND observed_at>=? AND observed_at<? AND status='available' "
                    "ORDER BY observed_at DESC LIMIT 1",
                    (strategy_id, day_start(day).isoformat(), end.isoformat()),
                ).fetchone()
                if row and (end - instant(row["observed_at"])).total_seconds() <= 300:
                    spread = json.loads(row["payload_json"])
            total = ZERO
            mt5_values = {}
            mt5_tickets = {}
            for (account, instrument, ticket), (quantity, average) in held.items():
                if quantity == 0:
                    continue
                spec = specifications[account, instrument]
                mark = current_marks.get((account, instrument, ticket), {}) if live_day else {}
                price = mark.get("markPrice") or mark.get("currentPrice")
                native = None
                observed_at = mark.get("asOf") or datetime.now(UTC).isoformat()
                if not live_day and spread:
                    venue = spread.get("mt5" if ticket else "bybit", {})
                    candidates = [
                        p for p in venue.get("positions", []) if p.get("accountId") == account
                    ]
                    if ticket:
                        candidates = [p for p in candidates if str(p.get("externalId")) == ticket]
                    else:
                        candidates = [p for p in candidates if p.get("symbol") == spec["symbol"]]
                    if len(candidates) == 1:
                        candidate = candidates[0]
                        observed_quantity = Decimal(str(candidate["quantity"]))
                        if candidate.get("side") == "sell":
                            observed_quantity = -abs(observed_quantity)
                        if (
                            observed_quantity == quantity
                            and candidate.get("unrealizedPnl") is not None
                        ):
                            native = Decimal(str(candidate["unrealizedPnl"]))
                            observed_at = spread["asOf"]
                if live_day and mark.get("unrealizedPnl") is not None and ticket:
                    if Decimal(str(mark.get("netQuantity", 0))) == quantity:
                        native = Decimal(str(mark["unrealizedPnl"]))
                if spec["instrument_type"] == "crypto_spot":
                    at = min(end, datetime.now(UTC))
                    rates = {}
                    for coin in (spec["base_asset"], spec["quote_currency"]):
                        row = db.execute(
                            "SELECT as_of,usd_rate FROM account_valuation_rates "
                            "WHERE account_id=? AND currency=? AND as_of>=? AND as_of<? "
                            "ORDER BY as_of DESC LIMIT 1",
                            (
                                account,
                                coin,
                                (at - timedelta(minutes=5)).isoformat(),
                                at.isoformat(),
                            ),
                        ).fetchone()
                        if row:
                            rates[coin] = Decimal(row["usd_rate"])
                            observed_at = row["as_of"]
                    if all(rates.get(c) for c in (spec["base_asset"], spec["quote_currency"])):
                        price = rates[spec["base_asset"]] / rates[spec["quote_currency"]]
                elif not live_day and native is None:
                    # Funding receipts contain the actual perpetual settlement mark.
                    marks = []
                    for event in events:
                        if event["account_id"] != account or event["instrument_id"] != instrument:
                            continue
                        if event["event_type"] != "funding":
                            continue
                        payload = json.loads(event["payload_json"])
                        raw = payload.get("payload", {})
                        if (
                            raw.get("tradePrice")
                            and abs((instant(event["occurred_at"]) - end).total_seconds()) <= 300
                        ):
                            marks.append((instant(event["occurred_at"]), raw["tradePrice"]))
                    if marks:
                        observed_at, price = min(
                            marks, key=lambda item: abs((item[0] - end).total_seconds())
                        )
                        observed_at = observed_at.isoformat()
                if native is None and price is not None and average is not None:
                    native = (
                        quantity * (Decimal(str(price)) - average) * Decimal(spec["multiplier"])
                    )
                converted = (
                    to_base(account, spec["settle_currency"], native, observed_at)
                    if native is not None
                    else None
                )
                if converted is None:
                    reasons[key] = "historical_position_marks_unavailable"
                    break
                total += converted
                if ticket:
                    mt5_values[account] = mt5_values.get(account, ZERO) + converted
                    mt5_tickets.setdefault(account, set()).add(ticket)
                    if live_day and mark.get("swap") is not None:
                        swap = to_base(
                            account,
                            spec["settle_currency"],
                            Decimal(str(mark["swap"])),
                            observed_at,
                        )
                        if swap is not None:
                            total += swap
            # A complete ticket match permits using the native MT5 floating
            # result (including open-position swap) for exactly these positions.
            if not live_day and spread and key not in reasons:
                all_mt5 = spread.get("mt5", {}).get("positions", [])
                for account, tickets in mt5_tickets.items():
                    native_tickets = {
                        str(p.get("externalId")) for p in all_mt5 if p.get("accountId") == account
                    }
                    if tickets != native_tickets:
                        if reporting_sessions is not None:
                            reasons[key] = "historical_carry_unavailable"
                        continue
                    risk = db.execute(
                        "SELECT payload_json,currency,as_of FROM account_risk_snapshots "
                        "WHERE account_id=? AND as_of>=? AND as_of<? ORDER BY as_of DESC LIMIT 1",
                        (account, (end - timedelta(minutes=5)).isoformat(), end.isoformat()),
                    ).fetchone()
                    if reporting_sessions is not None and not risk:
                        reasons[key] = "historical_carry_unavailable"
                    if risk:
                        raw = json.loads(risk["payload_json"]).get("unrealizedPnl")
                        converted = (
                            to_base(account, risk["currency"], Decimal(str(raw)), risk["as_of"])
                            if raw is not None
                            else None
                        )
                        if converted is not None:
                            total += converted - mt5_values[account]
                        elif reporting_sessions is not None:
                            reasons[key] = "historical_carry_unavailable"
            values[key] = None if key in reasons else total
            day += timedelta(days=1)
    return values, reasons
