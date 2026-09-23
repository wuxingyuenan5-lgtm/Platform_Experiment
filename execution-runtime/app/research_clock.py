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
    if abs((after_ns - before_ns) - elapsed) > 10_000_000:
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
