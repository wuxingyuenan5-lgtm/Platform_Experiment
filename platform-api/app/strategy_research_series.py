"""Versioned observed-clock derivation. Raw batches are archived before filtering."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, localcontext
from functools import wraps

METHOD = "observed-spread.v1"
QUALITY = "research-quality.v2"


def exact_math(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with localcontext() as ctx:
            ctx.prec = 80
            return fn(*args, **kwargs)

    return wrapped


def decimal(value):
    d = Decimal(str(value))
    if not d.is_finite():
        raise ValueError("nonfinite")
    return d


def time_ms(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timezone required")
    delta = stamp.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds // 1000


def source_age_bounds(event):
    """Use only clock evidence attached at receipt; preserve native timestamps."""
    c = event.get("sourceClock")
    if not c or c.get("methodVersion") != "bybit-clock-interval.v1":
        return None
    try:
        if c["collectorSessionId"] != event["collectorSessionId"]:
            return None
        age = int(event["runtimeMonotonicNs"]) - int(c["localMonotonicNs"])
        local_ns = time_ms(event["runtimeReceivedAt"]) * 1_000_000
        if not 0 <= age <= int(c["maxAgeNs"]):
            return None
        if abs(local_ns - int(c["localReceivedNs"]) - age) > 20_000_000:
            return None
        source_ns = int(event["sourceEventTimeMs"]) * 1_000_000
        allowance = int(c["driftAllowanceNs"])
        lower = local_ns + int(c["offsetLowerNs"]) - source_ns - allowance
        upper = local_ns + int(c["offsetUpperNs"]) - source_ns + allowance
        return {
            "lowerMs": str(lower // 1_000_000),
            "upperMs": str(-(-upper // 1_000_000)),
            "calibrationId": c["eventId"],
            "methodVersion": c["methodVersion"],
        }
    except (ValueError, KeyError, TypeError):
        return None


def stable_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


class Deriver:
    def __init__(self, state=None, *, max_age_ms=2000):
        self.state = state or {"books": {}, "quotes": {}, "tickCounts": {}, "tickers": {}}
        self.max_age_ms = max_age_ms

    @exact_math
    def consume(self, event):
        out = []
        kind, stream = event["kind"], event["stream"]
        p = event["payload"]
        if kind == "quality":
            for key in list(self.state["quotes"]):
                if stream == "runtime" or key.startswith(stream):
                    self.state["quotes"].pop(key)
            for key in list(self.state["books"]):
                if stream == "runtime" or key.startswith(stream):
                    self.state["books"].pop(key)
            for key in list(self.state["tickers"]):
                if stream == "runtime" or key.startswith(stream):
                    self.state["tickers"].pop(key)
            return self._gaps(event, stream, event.get("quality", ["source_gap"]))
        if kind == "market_scan":
            symbols = {
                x.get("symbol")
                for x in p.get("spot", {}).get("result", {}).get("list", [])
                if x.get("status") == "Trading"
            }
            return [
                {
                    "kind": "funding_scan",
                    "stream": "bybit:linear:" + x["symbol"],
                    "receivedAt": event["runtimeReceivedAt"],
                    "eventId": event["eventId"] + ":" + x["symbol"],
                    "payload": x,
                    "quoteScope": "public",
                    "sourceResolution": "60s_scan",
                    "highPrecisionHistory": "core_only",
                }
                for x in p.get("linearTickers", {}).get("result", {}).get("list", [])
                if x.get("symbol") in symbols and x.get("fundingRate") is not None
            ]
        if kind == "mt5_historical_batch":
            minutes = {}
            for tick in p.get("ticks", []):
                minute = int(tick["time_msc"]) // 60000
                if minute not in minutes or int(tick["time_msc"]) >= int(
                    minutes[minute]["time_msc"]
                ):
                    minutes[minute] = tick
            return [
                {
                    "kind": "mt5_history_quote",
                    "stream": stream,
                    "eventId": event["eventId"] + ":" + str(minute),
                    "receivedAt": event["runtimeReceivedAt"],
                    "sourceTimeMs": tick["time_msc"],
                    "bid": tick["bid"],
                    "ask": tick["ask"],
                    "nativeSymbol": p.get("symbol"),
                    "quoteScope": event["quoteScope"],
                    "quality": ["clock_unverified", "backfill_only"],
                    "sampling": "last_native_tick_per_minute",
                    "ingestionMode": "backfill",
                }
                for minute, tick in sorted(minutes.items())
            ]
        if kind == "price_history":
            seen = self.state.setdefault("closedCandles", {})
            interval = int(p["intervalMs"])
            for item in p.get("response", {}).get("result", {}).get("list", []):
                try:
                    if len(item) < 5:
                        raise ValueError("short candle")
                    int(item[0])
                except (TypeError, ValueError, IndexError):
                    # The complete malformed response remains in the raw layer.
                    out.append(
                        {
                            "kind": "invalid_history",
                            "eventId": event["eventId"],
                            "stream": stream,
                            "receivedAt": event["runtimeReceivedAt"],
                            "quality": ["numeric_invalid"],
                            "quoteScope": "public",
                        }
                    )
                    continue
                key = stream + ":" + item[0]
                revision = stable_hash(item)
                if seen.get(key) == revision:
                    continue
                flags = list(event.get("quality", []))
                if key in seen:
                    flags.append("history_revision")
                try:
                    op, high, low, close = [decimal(x) for x in item[1:5]]
                    if not 0 < low <= min(op, close) <= max(op, close) <= high:
                        flags.append("numeric_invalid")
                except (ValueError, InvalidOperation):
                    flags.append("numeric_invalid")
                seen[key] = revision
                # Only the overlap/recent page needs cursor state; raw history lives in Parquet.
                while len(seen) > 6000:
                    seen.pop(next(iter(seen)))
                out.append(
                    {
                        "kind": "historical_candle",
                        "stream": stream,
                        "eventId": event["eventId"] + ":" + item[0],
                        "receivedAt": event["runtimeReceivedAt"],
                        "sourceTimeMs": item[0],
                        "closeTimeMs": str(int(item[0]) + interval),
                        "intervalMs": str(interval),
                        "priceType": p["priceType"],
                        "category": p["category"],
                        "symbol": p["symbol"],
                        "open": item[1],
                        "high": item[2],
                        "low": item[3],
                        "close": item[4],
                        "quality": flags,
                        "revision": revision,
                        "ingestionMode": "backfill",
                        "availability": "historical_not_observed_quote",
                        "quoteScope": "public",
                    }
                )
            return out
        if kind == "funding_settlements":
            seen = self.state.setdefault("settlements", {})
            for item in p.get("result", {}).get("list", []):
                key = stream + ":" + str(item.get("fundingRateTimestamp"))
                revision = stable_hash(item)
                if seen.get(key) == revision:
                    continue
                flags = ["settlement_revision_conflict"] if key in seen else []
                seen[key] = revision
                out.append(
                    {
                        "kind": "funding_settlement",
                        "stream": stream,
                        "eventId": event["eventId"] + ":" + key,
                        "receivedAt": event["runtimeReceivedAt"],
                        "quoteScope": "public",
                        "payload": item,
                        "revision": revision,
                        "quality": flags,
                        "mark": None,
                    }
                )
            return out
        if kind == "borrow_rates":
            return [
                {
                    "kind": "borrow_profile",
                    "eventId": event["eventId"],
                    "stream": stream,
                    "receivedAt": event["runtimeReceivedAt"],
                    "observedAt": event["runtimeReceivedAt"],
                    "effectiveFrom": None,
                    "quoteScope": "public",
                    "payload": p,
                    "billingRuleVersion": "bybit-uta-2026-09-03",
                    "rateUnit": "hourly_fraction",
                    "historyCoverage": "observations_only",
                }
            ]
        if kind == "bybit_message":
            category = stream.split(":")[1]
            topic = p.get("topic", "")
            symbol = topic.rsplit(".", 1)[-1]
            key = f"bybit:{category}:{symbol}"
            if topic.startswith("tickers."):
                old = {} if p.get("type") == "snapshot" else self.state["tickers"].get(key, {})
                if p.get("type") != "snapshot" and not old:
                    return []
                before = dict(old)
                old.update(p.get("data", {}))
                if old == before:
                    return []
                self.state["tickers"][key] = old
                out.append(
                    {
                        "kind": "funding_indication",
                        "stream": key,
                        "payload": dict(old),
                        "receivedAt": event["runtimeReceivedAt"],
                        "eventId": event["eventId"],
                    }
                )
                return out
            if not topic.startswith("orderbook."):
                return []
            data = p.get("data", {})
            snapshot = p.get("type") == "snapshot" or data.get("u") == 1
            book = {"b": {}, "a": {}, "u": None} if snapshot else self.state["books"].get(key)
            if book is None:
                return [
                    self._invalid(event, key, ["book_unsynced"]),
                    *self._gaps(event, key, ["book_unsynced"]),
                ]
            try:
                # Native u/seq are not required to increment by one on ordinary L50.
                if not snapshot and book["u"] is not None and int(data["u"]) <= int(book["u"]):
                    return []
                for side in ("a", "b"):
                    for price, size in data.get(side, []):
                        if decimal(price) <= 0 or decimal(size) < 0:
                            raise ValueError("invalid level")
                        if decimal(size) == 0:
                            book[side].pop(price, None)
                        else:
                            book[side][price] = size
                book["u"] = data.get("u")
                self.state["books"][key] = book
                bids = sorted(book["b"].items(), key=lambda x: decimal(x[0]), reverse=True)
                asks = sorted(book["a"].items(), key=lambda x: decimal(x[0]))
                bid, ask = bids[0][0], asks[0][0]
                quote = self._quote(event, key, bid, ask)
                quote["bids"], quote["asks"] = bids, asks
            except (ValueError, InvalidOperation, IndexError, KeyError):
                self.state["books"].pop(key, None)
                self.state["quotes"].pop(key, None)
                return [
                    self._invalid(event, key, ["numeric_invalid", "book_unsynced"]),
                    *self._gaps(event, key, ["numeric_invalid", "book_unsynced"]),
                ]
            out.extend(self._accept(quote))
        elif kind == "mt5_batch":
            key = "mt5:XAUUSD"
            scope_key = event["quoteScope"] + ":" + p.get("server", "") + ":" + p["symbol"]
            previous = self.state["tickCounts"].get(scope_key, {})
            counts = Counter()
            # Preserve native order, including multiple records in the same millisecond.
            for index, tick in enumerate(p.get("ticks", [])):
                signature = stable_hash(tick)
                counts[signature] += 1
                if counts[signature] <= previous.get(signature, 0):
                    continue
                qevent = dict(event)
                qevent["eventId"] += ":" + str(index)
                qevent["sourceEventTimeMs"] = tick.get("time_msc")
                quote = self._quote(qevent, key, tick.get("bid"), tick.get("ask"))
                quote["quoteScope"] = scope_key
                quote["specification"] = p.get("specification", {})
                quote["quality"] = sorted(set(quote["quality"] + ["clock_unverified"]))
                out.extend(self._accept(quote))
            self.state["tickCounts"][scope_key] = dict(counts)
        return out

    def _gaps(self, event, stream, flags):
        result = []
        for pair, keys in (
            ("cross-gold", ("bybit:linear:XAUTUSDT", "mt5:XAUUSD")),
            ("funding-btc", ("bybit:linear:BTCUSDT", "bybit:spot:BTCUSDT")),
        ):
            if stream == "runtime" or any(
                k.startswith(stream) or stream.startswith(k) for k in keys
            ):
                result.append(
                    {
                        "kind": "spread",
                        "pairId": pair,
                        "eventId": event.get("eventId", "quality"),
                        "receivedAt": event.get("runtimeReceivedAt"),
                        "quality": flags,
                        "quoteScope": "private" if pair == "cross-gold" else "public",
                        "methodVersion": METHOD,
                        "clockBasis": "observed",
                    }
                )
        return result

    def _invalid(self, event, key, flags):
        self.state["quotes"].pop(key, None)
        return {
            "kind": "invalid_quote",
            "stream": key,
            "eventId": event["eventId"],
            "receivedAt": event["runtimeReceivedAt"],
            "quality": flags,
            "quoteScope": event["quoteScope"],
        }

    def _quote(self, event, key, bid, ask):
        flags = list(event.get("quality", []))
        try:
            if decimal(bid) <= 0 or decimal(ask) < decimal(bid):
                flags.append("numeric_invalid")
            elif (decimal(ask) - decimal(bid)) / decimal(bid) > Decimal("0.05"):
                flags.append("wide_spread")
        except (ValueError, InvalidOperation):
            flags.append("numeric_invalid")
        if event["ingestionMode"] != "realtime":
            flags.append("backfill_only")
        source = event.get("sourceEventTimeMs")
        bounds = source_age_bounds(event) if key.startswith("bybit:") else None
        if source is None or (key.startswith("bybit:") and bounds is None):
            flags.append("clock_unverified")
        return {
            "kind": "quote",
            "stream": key,
            "eventId": event["eventId"],
            "receivedAt": event["runtimeReceivedAt"],
            "sourceTimeMs": source,
            "sourceAgeAtReceive": bounds,
            "sessionId": event["collectorSessionId"],
            "sequence": event["ingestSequence"],
            "quoteScope": event["quoteScope"],
            "bid": str(bid),
            "ask": str(ask),
            "quality": flags,
            "ingestionMode": event["ingestionMode"],
        }

    def _accept(self, quote):
        self.state["quotes"][quote["stream"]] = quote
        out = [quote]
        pairs = (
            ("cross-gold", "bybit:linear:XAUTUSDT", "mt5:XAUUSD"),
            ("funding-btc", "bybit:linear:BTCUSDT", "bybit:spot:BTCUSDT"),
        )
        for pair, a, b in pairs:
            if quote["stream"] not in (a, b):
                continue
            left, right = self.state["quotes"].get(a), self.state["quotes"].get(b)
            if left is None or right is None:
                continue
            now = time_ms(quote["receivedAt"])
            flags = set(left["quality"] + right["quality"])
            ages = [now - time_ms(q["receivedAt"]) for q in (left, right)]
            if min(ages) < 0:
                flags.add("clock_unverified")
            if max(ages) > self.max_age_ms:
                flags.add("stale_quote")
            if left["sessionId"] != right["sessionId"]:
                flags.add("capture_gap")
            for q in (left, right):
                bounds = q.get("sourceAgeAtReceive")
                if bounds:
                    upper = now - time_ms(q["receivedAt"]) + int(bounds["upperMs"])
                    if upper > self.max_age_ms:
                        flags.add("stale_quote")
                    if upper < 0:
                        flags.add("clock_unverified")
                elif q["sourceTimeMs"] and abs(now - int(q["sourceTimeMs"])) > self.max_age_ms:
                    flags.add("stale_quote")
            values = {}
            if "numeric_invalid" not in flags:
                ab, aa, bb, ba = [
                    decimal(x) for x in (left["bid"], left["ask"], right["bid"], right["ask"])
                ]
                values = {
                    "midSpread": str((ab + aa - bb - ba) / 2),
                    "buySpread": str(aa - bb),
                    "sellSpread": str(ab - ba),
                }
            out.append(
                {
                    "kind": "spread",
                    "pairId": pair,
                    "clockBasis": "observed",
                    "eventId": quote["eventId"],
                    "receivedAt": quote["receivedAt"],
                    "sourceTimeMs": quote["sourceTimeMs"],
                    "quoteScope": right["quoteScope"],
                    "inputEventIds": [left["eventId"], right["eventId"]],
                    "left": left,
                    "right": right,
                    "quality": sorted(flags),
                    "methodVersion": METHOD,
                    "qualityProfileId": QUALITY,
                    **values,
                }
            )
        return out


def seconds_series(events, *, valid_only=True, max_age_ms=2000):
    """OHLC from spread events, duration-weighted coverage; never leg extrema."""
    buckets = {}
    for i, row in enumerate(events):
        if row.get("kind") != "spread":
            continue
        start = time_ms(row["receivedAt"])
        valid = not row["quality"] and "midSpread" in row
        # Last event is a point, not evidence of future coverage.
        end = start
        if i + 1 < len(events):
            end = min(time_ms(events[i + 1]["receivedAt"]), start + max_age_ms)
            for leg in ("left", "right"):
                if row.get(leg):
                    end = min(end, time_ms(row[leg]["receivedAt"]) + max_age_ms)
            end = max(start, end)
        if not valid and valid_only:
            continue
        while True:
            second = start // 1000
            b = buckets.setdefault(
                second,
                {
                    "timeMs": str(second * 1000),
                    "validDurationMs": 0,
                    "updates": 0,
                    "quality": [],
                    "ohlc": {},
                },
            )
            if start == time_ms(row["receivedAt"]):
                b["updates"] += 1
            b["quality"] = sorted(set(b["quality"] + row["quality"]))
            boundary = min(end, (second + 1) * 1000)
            if valid:
                b["validDurationMs"] += max(0, boundary - start)
            for field in ("midSpread", "buySpread", "sellSpread"):
                if field not in row:
                    continue
                value = row[field]
                if field not in b["ohlc"]:
                    b["ohlc"][field] = {"open": value, "high": value, "low": value, "close": value}
                else:
                    o = b["ohlc"][field]
                    o["high"] = str(max(decimal(o["high"]), decimal(value)))
                    o["low"] = str(min(decimal(o["low"]), decimal(value)))
                    o["close"] = value
            if boundary >= end:
                break
            start = boundary
    return [buckets[k] for k in sorted(buckets)]


@exact_math
def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(decimal(v) for v in values)
    index = Decimal(len(ordered) - 1) * Decimal(str(fraction))
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    return str(ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo))


def distribution(events):
    seconds = seconds_series(events)
    values = [r["ohlc"]["midSpread"]["close"] for r in seconds if r["validDurationMs"] > 0]
    excluded = Counter(flag for r in events for flag in r.get("quality", []))
    return {
        "sampling": "equal_1s_close",
        "quantileMethod": "linear_R7",
        "sampleCount": len(values),
        "p10": quantile(values, ".1"),
        "p50": quantile(values, ".5"),
        "p90": quantile(values, ".9"),
        "exclusions": dict(excluded),
        "validDurationMs": str(sum(r["validDurationMs"] for r in seconds)),
        "observedWindowMs": str(
            time_ms(events[-1]["receivedAt"]) - time_ms(events[0]["receivedAt"])
        )
        if events
        else None,
        "excludedOrUnobservedMs": str(
            max(
                0,
                time_ms(events[-1]["receivedAt"])
                - time_ms(events[0]["receivedAt"])
                - sum(r["validDurationMs"] for r in seconds),
            )
        )
        if events
        else None,
        "theoreticalTradableMs": None,
        "calendarStatus": "unverified_not_inferred_from_gaps",
    }
