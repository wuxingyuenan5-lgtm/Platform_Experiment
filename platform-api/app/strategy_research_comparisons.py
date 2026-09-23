"""Paired entry-cohort diagnostics; quotes imply scenarios, never fills."""

from app.strategy_research_series import decimal, quantile, time_ms


def compare_rules(rows, events, params):
    from app.strategy_research_experiments import cash_at, executable, summary

    index = {r["eventId"]: i for i, r in enumerate(rows)}
    buy = params["direction"] == "buy_spread"
    q = decimal(params["quantity"])
    slip = (
        decimal(params["mt5SlippagePerUnit"])
        if params.get("mt5SlippagePerUnit") is not None
        else None
    )
    output = []
    for rule in ("target_only", "fixed_horizon", "target_or_horizon", "after_settlement"):
        paired = []
        for event in events:
            if event.get("entryEventId") not in index:
                paired.append({"id": event["id"], "exitReason": "right_censored", "netPnl": None})
                continue
            entry = rows[index[event["entryEventId"]]]
            begin = time_ms(entry["receivedAt"])
            last = begin
            unknown = False
            end = None
            minimum = None
            stream = "bybit:linear:" + (
                "XAUTUSDT" if params["pairId"] == "cross-gold" else "BTCUSDT"
            )
            visible = [
                v
                for v in params.get("_indications", [])
                if v["stream"] == stream and time_ms(v["receivedAt"]) <= begin
            ]
            settlement = visible[-1]["payload"].get("nextFundingTime") if visible else None
            for row in rows[index[event["entryEventId"]] :]:
                params["_workPoints"] = params.get("_workPoints", 0) + 1
                if params["_workPoints"] > 300000:
                    raise ValueError("paired replay budget exceeded; narrow window")
                if params["_workPoints"] % 1000 == 0 and params.get("_cancelled", lambda: False)():
                    raise ValueError("experiment cancelled")
                t = time_ms(row["receivedAt"])
                if t - last > params.get("maxQuoteAgeMs", 2000) or row.get("quality"):
                    unknown = True
                last = t
                if row.get("quality") or "buySpread" not in row:
                    continue
                price = executable(row, q, buy, False, slip)
                if price is None:
                    unknown = True
                    continue
                cash = cash_at(params, entry, row, decimal(event["entrySpread"]), price, q)
                pnl = q * (price - decimal(event["entrySpread"])) * (1 if buy else -1)
                minimum = min(minimum, pnl) if minimum is not None else pnl
                target = (
                    price >= decimal(params["exitTarget"])
                    if buy
                    else price <= decimal(params["exitTarget"])
                )
                due = t >= begin + params["maxHoldingSeconds"] * 1000
                leave = (
                    rule == "target_only"
                    and target
                    or rule == "fixed_horizon"
                    and due
                    or rule == "target_or_horizon"
                    and (target or due)
                    or rule == "after_settlement"
                    and settlement is not None
                    and t > int(settlement) + 5000
                )
                if leave:
                    reason = (
                        "path_unknown"
                        if unknown
                        else "target"
                        if target and rule != "fixed_horizon"
                        else "timeout"
                    )
                    end = {
                        "id": event["id"],
                        "entryAt": entry["receivedAt"],
                        "exitAt": row["receivedAt"],
                        "exitReason": reason,
                        "netPnl": None if unknown else cash["netPnl"],
                        "holdingMs": t - begin,
                        "priceMAE": str(minimum),
                        "cashflow": cash,
                    }
                    break
            paired.append(
                end
                or {
                    "id": event["id"],
                    "exitReason": "path_unknown" if unknown else "right_censored",
                    "netPnl": None,
                }
            )
        output.append(
            {
                "rule": rule,
                "entryCohortCount": len(events),
                "summary": summary(paired),
                "events": paired,
                "settlementKnowledge": "entry_visible_indication_only",
            }
        )
    return output


def opportunity_durations(rows, params):
    from app.strategy_research_experiments import executable

    buy = params["direction"] == "buy_spread"
    q = decimal(params["quantity"])
    slip = (
        decimal(params["mt5SlippagePerUnit"])
        if params.get("mt5SlippagePerUnit") is not None
        else None
    )
    intervals = []
    active = None
    for row, nxt in zip(rows, rows[1:], strict=False):
        t = time_ms(row["receivedAt"])
        end = min(time_ms(nxt["receivedAt"]), t + params.get("maxQuoteAgeMs", 2000))
        valid = not row.get("quality") and "buySpread" in row
        if valid:
            for leg in ("left", "right"):
                end = min(end, time_ms(row[leg]["receivedAt"]) + params.get("maxQuoteAgeMs", 2000))
        price = executable(row, q, buy, True, slip) if valid else None
        meets = price is not None and (
            price <= decimal(params["entryThreshold"])
            if buy
            else price >= decimal(params["entryThreshold"])
        )
        if meets and end > t:
            if active is not None and active[1] == t:
                active[1] = end
            else:
                if active:
                    intervals.append(active)
                active = [t, end]
        elif active:
            intervals.append(active)
            active = None
    if active:
        intervals.append(active)
    durations = [b - a for a, b in intervals]
    return {
        "quantity": str(q),
        "intervals": [
            {"fromMs": str(a), "toMs": str(b), "durationMs": str(b - a)} for a, b in intervals
        ],
        "count": len(durations),
        "p10Ms": quantile(durations, ".1"),
        "p50Ms": quantile(durations, ".5"),
        "p90Ms": quantile(durations, ".9"),
        "meaning": "healthy_quote_and_depth_condition_not_fill_probability",
        "lastObservationTail": "not_extrapolated",
    }
