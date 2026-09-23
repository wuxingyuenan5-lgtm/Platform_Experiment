"""Sequential, non-overlapping touch scenarios. Never claims execution or fills."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal

from app.strategy_research_policy import scenario, vwap
from app.strategy_research_schemas import Scenario
from app.strategy_research_series import decimal, exact_math, quantile, stable_hash, time_ms


def leg_prices(row, quantity, buy, entry, mt5_slippage):
    left, right = row["left"], row["right"]
    # Entry buy: ask A - bid B. Exit buy: bid A - ask B.
    buy_a = buy if entry else not buy
    a_levels = left.get("asks" if buy_a else "bids")
    a = vwap(a_levels, quantity) if a_levels else None
    if a is None:
        return None
    b_levels = right.get("bids" if buy_a else "asks")
    if b_levels is not None:
        b = vwap(b_levels, quantity)
    else:
        if mt5_slippage is None:
            return None
        b = decimal(right["bid" if buy_a else "ask"]) + (-mt5_slippage if buy_a else mt5_slippage)
    if b is None:
        return None
    return a, b


def executable(row, quantity, buy, entry, mt5_slippage):
    prices = leg_prices(row, quantity, buy, entry, mt5_slippage)
    return prices[0] - prices[1] if prices is not None else None


def cash_at(params, entry, row, entry_spread, exit_spread, quantity):
    profile = Scenario.model_validate(params["costProfile"])
    ratio = quantity / profile.quantity
    updates = {
        "quantity": quantity,
        "entrySpread": entry_spread,
        "exitSpread": exit_spread,
        "openedAt": datetime.fromisoformat(entry["receivedAt"]),
        "closedAt": datetime.fromisoformat(row["receivedAt"]),
    }
    for key in ("tradingFees", "additionalExecutionCost"):
        value = getattr(profile, key)
        if value is not None:
            updates[key] = value * ratio
    updates["borrow"] = profile.borrow.model_copy(
        update={"principal": profile.borrow.principal * ratio}
    )
    if profile.ownCapital is not None:
        updates["ownCapital"] = profile.ownCapital * ratio
    # Input is validated once above; derived VWAP/division keeps the declared 80-digit context.
    return scenario(profile.model_copy(update=updates))


@exact_math
def scan(rows, params, *, latency=0, quantity=None, entry_threshold=None, exit_target=None):
    quantity = decimal(quantity if quantity is not None else params["quantity"])
    buy = params["direction"] == "buy_spread"
    threshold = decimal(
        entry_threshold if entry_threshold is not None else params["entryThreshold"]
    )
    target = decimal(exit_target if exit_target is not None else params["exitTarget"])
    max_ms = params["maxHoldingSeconds"] * 1000
    quote_age = params.get("maxQuoteAgeMs", 2000)
    slip = params.get("mt5SlippagePerUnit")
    slip = decimal(slip) if slip is not None else None
    armed, active, pending = True, None, None
    events = []
    valid_rows = 0
    for index, row in enumerate(rows):
        if index % 1000 == 0 and params.get("_cancelled", lambda: False)():
            raise ValueError("experiment cancelled")
        t = time_ms(row["receivedAt"])
        if row.get("quality") or "buySpread" not in row:
            if active:
                active["pathUnknown"] = True
            continue
        valid_rows += 1
        entry_value = executable(row, quantity, buy, True, slip)
        exit_value = executable(row, quantity, buy, False, slip)
        if entry_value is None or exit_value is None:
            if active:
                active["pathUnknown"] = True
            continue
        condition = entry_value <= threshold if buy else entry_value >= threshold
        if active is None and pending is None:
            if not condition:
                armed = True
            if armed and condition:
                # Quote arrival evidence is required independently for both legs.
                pending = {"trigger": t, "index": index, "event": row["eventId"]}
                armed = False
        if pending is not None:
            if latency == 0:
                execution_row = row
            else:
                if (
                    pending.get("left") is None
                    and time_ms(row["left"]["receivedAt"]) >= pending["trigger"] + latency
                ):
                    pending["left"] = row["left"]
                if pending.get("left") is None:
                    continue
                due_b = time_ms(pending["left"]["receivedAt"]) + latency
                if time_ms(row["right"]["receivedAt"]) < due_b:
                    continue
                execution_row = dict(row, left=pending["left"])
            execution_price = executable(execution_row, quantity, buy, True, slip)
            if execution_price is None:
                continue
            active = {
                "id": stable_hash(
                    [pending["event"], index, str(quantity), latency, str(threshold), str(target)]
                )[:24],
                "triggerAt": pending["trigger"],
                "entryIndex": index,
                "entry": execution_row,
                "entrySpread": execution_price,
                "last": t,
                "pathUnknown": False,
                "entryLegPrices": leg_prices(execution_row, quantity, buy, True, slip),
                "legMAE": [Decimal("0"), Decimal("0")],
                "mae": Decimal("0"),
                "mfe": Decimal("0"),
                "netMae": None,
                "netMfe": None,
                "path": [],
                "exitPending": None,
            }
            pending = None
        if active is None:
            continue
        if t - active["last"] > quote_age:
            active["pathUnknown"] = True
        active["last"] = t
        prices = leg_prices(row, quantity, buy, False, slip)
        entry_prices = active["entryLegPrices"]
        assert prices is not None and entry_prices is not None
        legs = [
            quantity * (prices[0] - entry_prices[0]) * (1 if buy else -1),
            quantity * (prices[1] - entry_prices[1]) * (-1 if buy else 1),
        ]
        active["legMAE"] = [min(active["legMAE"][i], legs[i]) for i in range(2)]
        pnl = quantity * (exit_value - active["entrySpread"]) * (1 if buy else -1)
        active["mae"], active["mfe"] = min(active["mae"], pnl), max(active["mfe"], pnl)
        cash = cash_at(params, active["entry"], row, active["entrySpread"], exit_value, quantity)
        net = decimal(cash["netPnl"]) if cash["netPnl"] is not None else None
        if net is not None:
            active["netMae"] = min(active["netMae"], net) if active["netMae"] is not None else net
            active["netMfe"] = max(active["netMfe"], net) if active["netMfe"] is not None else net
        params["_workPoints"] = params.get("_workPoints", 0) + 1
        if params["_workPoints"] > 300000:
            raise ValueError("replay computation budget exceeded; narrow window or parameter grid")
        active["path"].append(
            {
                "eventId": row["eventId"],
                "at": row["receivedAt"],
                "inputEventIds": row["inputEventIds"],
                "pricePnl": str(pnl),
                "legPricePnl": [str(v) for v in legs],
                "netPnl": cash["netPnl"],
                "fundingCash": cash["fundingCash"],
                "borrowCash": cash["borrowCash"],
                "swapCash": cash["swapCash"],
            }
        )
        held = t - time_ms(active["entry"]["receivedAt"])
        risk = params.get("riskPnl")
        # Sequential events resolve boundary order; no OHLC inference.
        reason = None
        if risk is not None and pnl <= decimal(risk):
            reason = "risk"
        elif exit_value >= target if buy else exit_value <= target:
            reason = "target"
        elif held >= max_ms:
            reason = "timeout"
        if reason and active["exitPending"] is None:
            active["exitPending"] = {"reason": reason, "trigger": t, "left": None}
        leaving = active["exitPending"]
        if leaving is not None:
            if latency:
                if (
                    leaving["left"] is None
                    and time_ms(row["left"]["receivedAt"]) >= leaving["trigger"] + latency
                ):
                    leaving["left"] = row["left"]
                if (
                    leaving["left"] is None
                    or time_ms(row["right"]["receivedAt"])
                    < time_ms(leaving["left"]["receivedAt"]) + latency
                ):
                    continue
                exit_value = executable(dict(row, left=leaving["left"]), quantity, buy, False, slip)
                if exit_value is None:
                    active["pathUnknown"] = True
                    continue
                cash = cash_at(
                    params, active["entry"], row, active["entrySpread"], exit_value, quantity
                )
            reason = "path_unknown" if active["pathUnknown"] else leaving["reason"]
            events.append(outcome(active, row, cash, reason, held, max_ms))
            active = None
            if len(events) > 2000:
                raise ValueError("too many independent events; narrow the input")
    if active is not None:
        events.append(
            outcome(
                active,
                None,
                None,
                "path_unknown" if active["pathUnknown"] else "right_censored",
                None,
                max_ms,
            )
        )
    if pending:
        events.append(
            {
                "id": stable_hash(pending)[:24],
                "exitReason": "right_censored",
                "entryAt": None,
                "triggerAt": str(pending["trigger"]),
                "netPnl": None,
                "warnings": ["no_quote_after_hypothetical_leg_action"],
            }
        )
    return {
        "events": events,
        "validEventObservations": valid_rows,
        "latencyMs": latency,
        "quantity": str(quantity),
    }


def outcome(active, row, cash, reason, held, max_ms):
    uncertain = reason in ("path_unknown", "right_censored")
    return {
        "id": active["id"],
        "entryAt": active["entry"]["receivedAt"],
        "exitAt": row["receivedAt"] if row else None,
        "entryEventId": active["entry"]["eventId"],
        "exitEventId": row["eventId"] if row else None,
        "exitReason": reason,
        "entrySpread": str(active["entrySpread"]),
        "legPriceMAE": [str(v) for v in active["legMAE"]],
        "marginStress": "price_only_no_liquidation_distance",
        "priceMAE": str(active["mae"]),
        "priceMFE": str(active["mfe"]),
        "netMAE": str(active["netMae"]) if active["netMae"] is not None else None,
        "netMFE": str(active["netMfe"]) if active["netMfe"] is not None else None,
        "netPnl": cash["netPnl"] if cash and not uncertain else None,
        "cashflow": cash,
        "holdingMs": held,
        "overdueMs": max(0, held - max_ms) if held else None,
        "replay": active["path"],
        "model": "hypothetical_quote_touch",
    }


def summary(events):
    resolved = [x for x in events if x["exitReason"] in ("target", "risk", "timeout")]
    values = [decimal(x["netPnl"]) for x in resolved if x["netPnl"] is not None]
    counts = Counter(x["exitReason"] for x in events)
    return {
        "independentEvents": len(events),
        "outcomes": dict(counts),
        "netSampleCount": len(values),
        "targetBeforeRiskRatio": str(Decimal(counts["target"]) / len(resolved))
        if resolved
        else None,
        "netMean": str(sum(values) / len(values)) if values else None,
        "netP10": quantile(values, ".1"),
        "netP50": quantile(values, ".5"),
        "netP90": quantile(values, ".9"),
        "unknownRatio": str(Decimal(len(events) - len(resolved)) / len(events)) if events else None,
        "holdingMsP50": quantile([x["holdingMs"] for x in resolved], ".5"),
    }


@exact_math
def run_experiment(rows, params):
    params = dict(params)
    params["_workPoints"] = 0
    rows = [r for r in rows if time_ms(r["receivedAt"]) <= time_ms(params["to"])]
    # Archive order preserves Runtime session order; wall-clock reversal is unknown.
    for previous, current in zip(rows, rows[1:], strict=False):
        if time_ms(current["receivedAt"]) < time_ms(previous["receivedAt"]):
            raise ValueError("clock reversal: observed replay requires a verified clock segment")
    base = scan(rows, params)
    events = base["events"]
    split = time_ms(params["validationFrom"])
    purge = params["maxHoldingSeconds"] * 1000
    training = [e for e in events if e.get("exitAt") and time_ms(e["exitAt"]) < split - purge]
    validation = [e for e in events if e.get("entryAt") and time_ms(e["entryAt"]) >= split]
    matrix = []
    for entry in params.get("entryThresholds") or [params["entryThreshold"]]:
        for target in params.get("exitTargets") or [params["exitTarget"]]:
            cell = scan(rows, params, entry_threshold=entry, exit_target=target)
            matrix.append(
                {
                    "entry": str(entry),
                    "target": str(target),
                    "summary": summary(cell["events"]),
                    "eventIds": [e["id"] for e in cell["events"]],
                    "events": cell["events"],
                }
            )
    latency = [
        {"latencyMs": ms, "summary": summary(scan(rows, params, latency=ms)["events"])}
        for ms in params.get("latencyMs", [0])
    ]
    quantities = [
        {"quantity": str(q), "summary": summary(scan(rows, params, quantity=q)["events"])}
        for q in params.get("quantities") or [params["quantity"]]
    ]
    curves = []
    # Same base entries at every horizon, including failed/early-exit entries.
    by_id = {r["eventId"]: i for i, r in enumerate(rows)}
    for seconds in params.get("holdingSeconds", []):
        values = []
        missing = 0
        for event in events:
            if event.get("entryEventId") not in by_id:
                missing += 1
                continue
            entry = rows[by_id[event["entryEventId"]]]
            later = rows[by_id[event["entryEventId"]] :]
            target_time = time_ms(entry["receivedAt"]) + seconds * 1000
            candidate = next(
                (r for r in later if time_ms(r["receivedAt"]) >= target_time and not r["quality"]),
                None,
            )
            if candidate is None:
                missing += 1
                continue
            path = [
                r for r in later if time_ms(r["receivedAt"]) <= time_ms(candidate["receivedAt"])
            ]
            if any(r.get("quality") for r in path) or any(
                time_ms(b["receivedAt"]) - time_ms(a["receivedAt"])
                > params.get("maxQuoteAgeMs", 2000)
                for a, b in zip(path, path[1:], strict=False)
            ):
                missing += 1
                continue
            price = executable(
                candidate,
                decimal(params["quantity"]),
                params["direction"] == "buy_spread",
                False,
                decimal(params["mt5SlippagePerUnit"])
                if params.get("mt5SlippagePerUnit") is not None
                else None,
            )
            if price is None:
                missing += 1
                continue
            cash = cash_at(
                params,
                entry,
                candidate,
                decimal(event["entrySpread"]),
                price,
                decimal(params["quantity"]),
            )
            if cash["netPnl"] is None:
                missing += 1
            else:
                values.append(cash["netPnl"])
        curves.append(
            {
                "seconds": seconds,
                "entryCohortCount": len(events),
                "sampleCount": len(values),
                "unknownCount": missing,
                "p10": quantile(values, ".1"),
                "p50": quantile(values, ".5"),
                "p90": quantile(values, ".9"),
            }
        )
    joint_groups = {}
    for event in events:
        if not event.get("entryAt"):
            continue
        stream = "bybit:linear:" + ("XAUTUSDT" if params["pairId"] == "cross-gold" else "BTCUSDT")
        visible = [
            i
            for i in params.get("_indications", [])
            if i["stream"] == stream and time_ms(i["receivedAt"]) <= time_ms(event["entryAt"])
        ]
        indication = visible[-1]["payload"] if visible else {}
        rate = indication.get("fundingRate")
        next_at = indication.get("nextFundingTime")
        event["entryInformation"] = {
            "indicatedFundingRate": rate,
            "nextFundingTimeMs": next_at,
            "timeToSettlementMs": str(int(next_at) - time_ms(event["entryAt"]))
            if next_at
            else None,
            "borrowRate": params["costProfile"].get("borrow", {}).get("hourlyRate"),
        }
        group = "unknown" if rate is None else "positive" if decimal(rate) > 0 else "nonpositive"
        joint_groups.setdefault(group, []).append(event)
    joint = [{"entryFundingGroup": k, "summary": summary(v)} for k, v in joint_groups.items()]
    time_groups = {}
    for event in events:
        if event.get("entryAt"):
            stamp = datetime.fromisoformat(event["entryAt"]).astimezone(__import__("datetime").UTC)
            time_groups.setdefault((stamp.weekday(), stamp.hour), []).append(event)
    calendar_groups = [
        {"weekdayUTC": k[0], "hourUTC": k[1], "summary": summary(v)}
        for k, v in sorted(time_groups.items())
    ]
    settlements = []
    for settlement in params.get("_settlements", []):
        expected_stream = "bybit:linear:" + (
            "XAUTUSDT" if params["pairId"] == "cross-gold" else "BTCUSDT"
        )
        if settlement["stream"] != expected_stream:
            continue
        data = settlement["payload"]
        at = int(data["fundingRateTimestamp"])
        points = [
            {
                "relativeMs": str(time_ms(r["receivedAt"]) - at),
                "midSpread": r.get("midSpread"),
                "buySpread": r.get("buySpread"),
                "sellSpread": r.get("sellSpread"),
                "quality": r["quality"],
            }
            for r in rows
            if abs(time_ms(r["receivedAt"]) - at) <= 3600000
        ]
        if points:
            settlements.append(
                {
                    "settlementTimeMs": str(at),
                    "settledRate": data["fundingRate"],
                    "quality": settlement.get("quality", []),
                    "settlementMark": None,
                    "fundingCash": None,
                    "points": points,
                    "warning": "rate_only_until_settlement_mark_is_observed",
                }
            )
    from app.strategy_research_comparisons import compare_rules, opportunity_durations

    return {
        "exitRuleComparison": compare_rules(rows, events, params),
        "opportunityDurations": opportunity_durations(rows, params),
        "methodVersion": "experiment.v1",
        "parameterHash": stable_hash({k: v for k, v in params.items() if not k.startswith("_")}),
        "dataVersion": params.get("_dataVersion") or stable_hash(rows),
        "summary": summary(events),
        "events": events,
        "matrix": matrix,
        "jointFundingSpread": joint,
        "weekdayHourUTC": calendar_groups,
        "settlementEvents": settlements,
        "holdingCurve": curves,
        "latencyScenarios": latency,
        "quantityScenarios": quantities,
        "sampleOutOfTraining": summary(validation),
        "training": summary(training),
        "purgeSeconds": params["maxHoldingSeconds"],
        "trialCount": len(matrix) + len(latency) + len(quantities),
        "warnings": [
            "touch_is_not_fill",
            "zero_latency_is_idealized",
            "MT5_top_quote_plus_explicit_slippage_only",
            "no_account_margin_or_liquidation_model",
            "parameter_stability_requires_neighbouring_cells",
        ],
        "coverage": {
            "observations": len(rows),
            "validObservations": base["validEventObservations"],
            "first": rows[0]["receivedAt"] if rows else None,
            "last": rows[-1]["receivedAt"] if rows else None,
        },
    }
