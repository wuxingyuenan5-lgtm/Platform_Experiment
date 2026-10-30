"""Observed minute aggregates; no invented ticks, gap filling or leg extrema subtraction."""

from decimal import Decimal, InvalidOperation
from threading import RLock
from typing import Any


class MinuteHistory:
    def __init__(self):
        self.lock = RLock()
        self.buckets = {}
        self.latest = {}
        self.first_bucket = None
        self.invalid_counts = {}

    def observe(self, stream, at_ms, source_ms, bid, ask, quality=()):
        with self.lock:
            bucket = at_ms // 60000 * 60000
            if self.first_bucket is None:
                self.first_bucket = bucket
            try:
                bid, ask = Decimal(str(bid)), Decimal(str(ask))
                if not bid.is_finite() or not ask.is_finite() or bid <= 0 or ask < bid:
                    raise ValueError("invalid quote")
            except (ValueError, InvalidOperation):
                self.latest.pop(stream, None)
                key = (stream, bucket)
                self.invalid_counts[key] = self.invalid_counts.get(key, 0) + 1
                self._add("quote_minute", stream, bucket, at_ms, {}, ("numeric_invalid",))
                return
            quote = dict(at=at_ms, source=source_ms, bid=bid, ask=ask, quality=list(quality))
            self.latest[stream] = quote
            self._add("quote_minute", stream, bucket, at_ms, {"bid": bid, "ask": ask}, quality)
            for pair, left, right in (
                ("funding-btc", "bybit:linear:BTCUSDT", "bybit:spot:BTCUSDT"),
                ("cross-gold", "bybit:linear:XAUTUSDT", "mt5:XAUUSD"),
            ):
                if (
                    stream not in (left, right)
                    or left not in self.latest
                    or right not in self.latest
                ):
                    continue
                a, b = self.latest[left], self.latest[right]
                flags = set(a["quality"] + b["quality"])
                ages = [at_ms - q["at"] for q in (a, b)]
                if min(ages) < 0 or max(ages) > 2000:
                    continue  # Never turn stale legs into an observed spread.
                self._add(
                    "spread_minute",
                    pair,
                    bucket,
                    at_ms,
                    {
                        "buySpread": a["ask"] - b["bid"],
                        "sellSpread": a["bid"] - b["ask"],
                        "midSpread": (a["bid"] + a["ask"] - b["bid"] - b["ask"]) / 2,
                    },
                    flags,
                )

    def _add(self, kind, entity, bucket, at, values, flags):
        key = (kind, entity, bucket)
        row = self.buckets.setdefault(
            key,
            dict(
                kind=kind,
                entity=entity,
                bucketStartMs=bucket,
                intervalMs=60000,
                count=0,
                firstObservedMs=at,
                lastObservedMs=at,
                maxGapMs=0,
                quality=set(),
                values={},
                coverage="observed_updates_only",
            ),
        )
        row["maxGapMs"] = max(row["maxGapMs"], at - row["lastObservedMs"])
        row["lastObservedMs"] = at
        row["count"] += 1
        row["quality"].update(flags)
        if bucket == self.first_bucket:
            row["quality"].add("collector_partial_minute")
        for metric, value in values.items():
            ohlc = row["values"].setdefault(
                metric, dict(open=value, high=value, low=value, close=value)
            )
            ohlc.update(high=max(ohlc["high"], value), low=min(ohlc["low"], value), close=value)

    def flush(self, now_ms, emit):
        with self.lock:
            for key in sorted(self.buckets):
                row = self.buckets[key]
                if row["bucketStartMs"] + 62000 > now_ms:
                    continue
                result: dict[str, Any] = dict(
                    row,
                    quality=sorted(row["quality"]),
                    values={
                        metric: {field: str(value) for field, value in ohlc.items()}
                        for metric, ohlc in row["values"].items()
                    },
                )
                result["maxGapMs"] = max(
                    row["maxGapMs"],
                    row["firstObservedMs"] - row["bucketStartMs"],
                    row["bucketStartMs"] + 60000 - row["lastObservedMs"],
                )
                invalid_key = (row["entity"], row["bucketStartMs"])
                result["invalidQuoteCount"] = self.invalid_counts.get(invalid_key, 0)
                if result["invalidQuoteCount"]:
                    result["quality"] = sorted(set(result["quality"] + ["numeric_invalid"]))
                if result["maxGapMs"] > 2000:
                    result["quality"] = sorted(set(result["quality"] + ["observation_gap"]))
                if emit(result) is False:
                    return
                del self.buckets[key]
                self.invalid_counts.pop(invalid_key, None)
