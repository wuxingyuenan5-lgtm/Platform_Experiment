"""Read-only Bybit clock interval evidence; never sets OS or venue clocks."""

import time
from datetime import UTC, datetime, timedelta


def sample_clock(client):
    before_ns, before_mono = time.time_ns(), time.monotonic_ns()
    response = client.get_server_time()
    after_mono, after_ns = time.monotonic_ns(), time.time_ns()
    elapsed = after_mono - before_mono
    if response.get("retCode") != 0 or not 0 <= elapsed <= 1_000_000_000:
        raise ValueError("clock_sample_unavailable_or_rtt_exceeds_1s")
    # Windows wall-clock reads can differ from monotonic elapsed by one timer tick.
    # The 100 ms conservative drift allowance below still covers this tolerance.
    if abs((after_ns - before_ns) - elapsed) > 25_000_000:
        raise ValueError("local_clock_stepped_during_sample")
    server_ns = int(response["result"]["timeNano"])
    if server_ns <= 0 or abs(server_ns - after_ns) > 60_000_000_000:
        raise ValueError("clock_offset_exceeds_60s")
    return {
        "methodVersion": "bybit-clock-interval.v1",
        "localSentNs": str(before_ns),
        "localReceivedNs": str(after_ns),
        "localMonotonicNs": str(after_mono),
        "serverTimeNs": str(server_ns),
        "offsetLowerNs": str(server_ns - after_ns),
        "offsetUpperNs": str(server_ns - before_ns),
        "rttNs": str(elapsed),
        "maxAgeNs": "120000000000",
        "driftAllowanceNs": "100000000",
    }


def conservative_utc_now(evidence):
    """Bound the UTC query horizon without changing the host or MT5 native clock."""
    if evidence is None:
        return None
    elapsed = time.monotonic_ns() - int(evidence["localMonotonicNs"])
    if not 0 <= elapsed <= int(evidence["maxAgeNs"]):
        return None
    lower_ns = (
        int(evidence["localReceivedNs"])
        + elapsed
        + int(evidence["offsetLowerNs"])
        - int(evidence["driftAllowanceNs"])
    )
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=lower_ns // 1000)


class Mt5ObservedClock:
    """Live-only whole-hour native-label calibration against witnessed UTC.

    Requires advancing ticks and consistent elapsed time. Never applies today's
    offset to historical records or changes execution/OS clocks.
    """

    def __init__(self):
        self.previous = None
        self.count = 0
        self.evidence = None

    def observe(self, native_ms, utc_ms, account, symbol):
        offset = round((native_ms - utc_ms) / 3600000) * 3600000
        age = utc_ms - (native_ms - offset)
        previous = self.previous
        if abs(offset) > 14 * 3600000 or not -250 <= age <= 2000:
            self.previous, self.count, self.evidence = None, 0, None
            return None
        if previous and previous[2:] == (offset, account, symbol):
            advance = native_ms - previous[0]
            elapsed = utc_ms - previous[1]
            if advance == 0:
                return self.evidence
            if advance < 0 or abs(advance - elapsed) > 1000:
                self.count, self.evidence = 0, None
            else:
                self.count += 1
        else:
            self.count, self.evidence = 1, None
        self.previous = (native_ms, utc_ms, offset, account, symbol)
        if self.count >= 3:
            self.evidence = dict(
                methodVersion="mt5-observed-utc-offset.v1",
                nativeUtcOffsetMs=offset,
                account=account,
                symbol=symbol,
                nativeTimeMs=str(native_ms),
                referenceUtcMs=str(utc_ms),
                samples=self.count,
                measuredMonotonicNs=str(time.monotonic_ns()),
                maxAgeNs="30000000000",
                scope="live_observations_only",
            )
        return self.evidence


def live_mt5_clock(evidence):
    if not evidence:
        return None
    age = time.monotonic_ns() - int(evidence["measuredMonotonicNs"])
    return evidence if 0 <= age <= int(evidence["maxAgeNs"]) else None


def quote_time_quality(evidence, source_ms):
    """Use the UTC interval, including drift, without treating host wall time as UTC."""
    if evidence is None or source_ms is None:
        return ["clock_unverified"]
    elapsed = time.monotonic_ns() - int(evidence["localMonotonicNs"])
    if not 0 <= elapsed <= int(evidence["maxAgeNs"]):
        return ["clock_unverified"]
    upper = (
        int(evidence["localReceivedNs"])
        + elapsed
        + int(evidence["offsetUpperNs"])
        + int(evidence["driftAllowanceNs"])
        - int(source_ms) * 1000000
    )
    if upper < 0:
        return ["clock_unverified"]
    return ["stale_quote"] if upper > 2000000000 else []
