"""Derived BTC/gold intraday movement from the shared Bybit research archive.

The strategy research collector owns high-resolution Bybit candle storage. This
module only derives the three UTC-session cumulative series (and persists that
small derived projection for fast board reads); it never stores a second copy of
BTC/XAUT price history or calls a second venue.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from app.database import connection
from app import runtime_transport
from app.config import get_settings
from app.research_a_share_repository import finish_refresh, start_refresh, write_history_points
from app.research_provider_errors import ResearchProviderError

DATASET = "cumulative_volatility"
SOURCE = "Bybit strategy research archive (shared high-resolution source; sampled 15m/1h/4h)"
_ASSETS = {"btc": "BTCUSDT", "gold": "XAUTUSDT"}
_INTERVALS = {"15m": 15, "1h": 60, "4h": 240}
_MAX_RANGE_DAYS = 365
_SESSION_LABELS = {
    "asia": "亚洲盘 23:00–07:00 UTC",
    "europe": "欧洲盘 07:00–15:00 UTC",
    "americas": "美洲盘 15:00–23:00 UTC",
}
_STALE_AFTER = timedelta(minutes=45)
_DERIVED_WINDOW_TOLERANCE = timedelta(days=2)


def _shared_bybit_bars(asset: str, start: datetime, end: datetime) -> list[tuple[datetime, Decimal]]:
    """Read strategy-owned closed trade candles; raw prices are not duplicated."""
    from app.strategy_research_projection import read_projection

    symbol = _ASSETS[asset]
    rows = read_projection(
        "historical_candle",
        f"{symbol}:linear:trade",
        int(start.timestamp() * 1000),
        int(end.timestamp() * 1000),
    )
    bars: dict[datetime, Decimal] = {}
    for row in rows:
        if row.get("symbol") != symbol or row.get("category") != "linear":
            continue
        if row.get("priceType") != "trade" or row.get("quality"):
            continue
        try:
            timestamp = datetime.fromtimestamp(int(row["closeTimeMs"]) / 1000, UTC)
            close = Decimal(str(row["close"]))
        except (KeyError, TypeError, ValueError, InvalidOperation, OSError):
            continue
        if close > 0 and start <= timestamp <= end:
            bars[timestamp] = close
    # The strategy archive can be temporarily behind while replaying a large
    # order-book backlog.  Read only the missing recent window through the
    # same Runtime capture owner; the Hedge Board still persists just its
    # derived cumulative series and never duplicates raw candles.
    latest = max(bars, default=None)
    if latest is None or latest < end - timedelta(minutes=30):
        settings = get_settings()
        repair_start = max(
            start,
            (latest - timedelta(hours=2)) if latest else (end - timedelta(days=2)),
        )
        response = runtime_transport.get(
            settings.runtime_base_url.rstrip("/") + "/v1/market-data/price-history",
            params={
                "symbol": symbol,
                "category": "linear",
                "priceType": "trade",
                "startMs": int(repair_start.timestamp() * 1000),
                "endMs": int(end.timestamp() * 1000),
                "limit": 5000,
            },
            timeout=20,
        )
        response.raise_for_status()
        for item in response.json().get("rows", []):
            try:
                timestamp = datetime.fromtimestamp(int(item[0]) / 1000, UTC) + timedelta(minutes=1)
                close = Decimal(str(item[4]))
            except (IndexError, TypeError, ValueError, InvalidOperation, OSError):
                continue
            if close > 0 and start <= timestamp <= end:
                bars[timestamp] = close
    return sorted(bars.items(), key=lambda item: item[0])


def _bars(candles: Iterable[Any]) -> list[tuple[datetime, Decimal]]:
    result: dict[datetime, Decimal] = {}
    for row in candles:
        # Keep compatibility with the historical KuCoin-shaped test fixture,
        # while the production path receives `(timestamp, close)` tuples from
        # the shared strategy projection.
        try:
            if isinstance(row, tuple) and len(row) >= 2 and isinstance(row[0], datetime):
                timestamp = row[0].astimezone(UTC)
                close = Decimal(str(row[1]))
            else:
                if len(row) < 3:
                    continue
                timestamp = datetime.fromtimestamp(int(row[0]), UTC)
                close = Decimal(str(row[2]))
        except (TypeError, ValueError, OSError, InvalidOperation):
            continue
        if close > 0:
            result[timestamp] = close
    return sorted(result.items(), key=lambda item: item[0])


def _session_start(session: str, session_date: str) -> datetime:
    date = datetime.fromisoformat(session_date).replace(tzinfo=UTC)
    if session == "asia":
        return date - timedelta(days=1) + timedelta(hours=23)
    if session == "europe":
        return date + timedelta(hours=7)
    return date + timedelta(hours=15)


def _sample(bars: list[tuple[datetime, Decimal]], interval: str) -> list[tuple[datetime, Decimal]]:
    """Sample the last close in each session-relative UTC bucket.

    Buckets restart at each 23:00/07:00/15:00 session boundary, so a 4-hour
    sample never combines the tail of one session with the head of another.
    """
    if interval not in _INTERVALS:
        raise ValueError("interval must be 15m|1h|4h")
    minutes = _INTERVALS[interval]
    grouped: dict[tuple[str, str, int], tuple[datetime, Decimal]] = {}
    for timestamp, close in bars:
        session, session_date = _session_for(timestamp)
        start = _session_start(session, session_date)
        bucket_index = max(0, int((timestamp - start).total_seconds() // (minutes * 60)))
        key = (session, session_date, bucket_index)
        # Keep the last observed close and its timestamp for each bucket. The
        # timestamp is therefore the actual observation used for freshness,
        # instead of the bucket's opening boundary (important for 4h samples).
        grouped[key] = (timestamp, close)
    return sorted(grouped.values(), key=lambda item: item[0])


def _session_for(timestamp: datetime) -> tuple[str, str]:
    """Return the UTC session and its owning date."""
    hour = timestamp.hour
    if hour >= 23 or hour < 7:
        session_date = (
            (timestamp.date() + timedelta(days=1)).isoformat()
            if hour >= 23
            else timestamp.date().isoformat()
        )
        return "asia", session_date
    if hour < 15:
        return "europe", timestamp.date().isoformat()
    return "americas", timestamp.date().isoformat()


def calculate_cumulative_volatility(
    candles: Iterable[Any],
    *,
    initial_cumulative: dict[str, dict[str, Decimal]] | None = None,
) -> dict[str, Any]:
    """Calculate signed cumulative close-to-close movement in percentage points.

    Every session day starts at the prior value for that session; the first
    observation itself contributes zero, and later observations add the signed
    percentage change from the preceding observation in that same session.
    The first valid Americas-session close for each UTC day is also emitted as
    the day's price baseline. The frontend only renders these backend-derived
    fields; it does not perform session or price calculations.
    """
    bars = _bars(candles)
    points: list[dict[str, Any]] = []
    for interval in _INTERVALS:
        previous_cumulative = {
            session: (initial_cumulative or {}).get(interval, {}).get(session, Decimal("0"))
            for session in _SESSION_LABELS
        }
        previous_close: dict[tuple[str, str], Decimal] = {}
        sampled = _sample(bars, interval)
        price_baselines: dict[str, Decimal] = {}
        for timestamp, close in sampled:
            session, session_date = _session_for(timestamp)
            if session == "americas":
                price_baselines.setdefault(session_date, close)
        for timestamp, close in sampled:
            session, session_date = _session_for(timestamp)
            key = (session, session_date)
            if key not in previous_close:
                cumulative = previous_cumulative[session]
            else:
                prior = previous_close[key]
                cumulative = previous_cumulative[session] + (
                    ((close / prior) - Decimal("1")) * Decimal("100")
                )
            previous_close[key] = close
            previous_cumulative[session] = cumulative
            baseline = price_baselines.get(session_date)
            price_change = ((close / baseline) - Decimal("1")) * Decimal("100") if baseline else None
            points.append(
                {
                    "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                    "session": session,
                    "sessionDate": session_date,
                    "interval": interval,
                    "value": format(cumulative, "f"),
                    "price": format(close, "f"),
                    "priceBaseline": format(baseline, "f") if baseline else None,
                    "priceChangePct": format(price_change, "f") if price_change is not None else None,
                }
            )
    points.sort(key=lambda point: (point["timestamp"], point["interval"], point["session"]))
    return {"points": points}


def _point_payload(point: dict[str, Any], asset: str) -> dict[str, Any]:
    return {
        "asset": asset,
        "timestamp": point["timestamp"],
        "session": point["session"],
        "sessionDate": point["sessionDate"],
        "interval": point["interval"],
        "value": point["value"],
        "price": point.get("price"),
        "priceBaseline": point.get("priceBaseline"),
        "priceChangePct": point.get("priceChangePct"),
    }


def _latest_persisted_timestamp(asset: str) -> datetime | None:
    with connection() as db:
        row = db.execute(
            "SELECT MAX(observed_at) AS observed_at FROM research_a_share_history "
            "WHERE dataset=? AND entity_code LIKE ?",
            (DATASET, f"{asset}:%"),
        ).fetchone()
    value = row["observed_at"] if row else None
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _earliest_persisted_timestamp(asset: str) -> datetime | None:
    with connection() as db:
        row = db.execute(
            "SELECT MIN(observed_at) AS observed_at FROM research_a_share_history "
            "WHERE dataset=? AND entity_code LIKE ?",
            (DATASET, f"{asset}:%"),
        ).fetchone()
    value = row["observed_at"] if row else None
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _needs_price_backfill(asset: str) -> bool:
    """Detect pre-price-overlay derived rows and upgrade them in place once."""
    with connection() as db:
        row = db.execute(
            """SELECT 1
               FROM research_a_share_history
               WHERE dataset=? AND entity_code LIKE ? AND payload_json NOT LIKE '%\"price\"%'
               LIMIT 1""",
            (DATASET, f"{asset}:%"),
        ).fetchone()
    return row is not None


def _seed_cumulative(asset: str, before: datetime) -> dict[str, dict[str, Decimal]]:
    """Read the last value of every session/interval before an incremental pull."""
    seeds: dict[str, dict[str, Decimal]] = {}
    cutoff = before.isoformat().replace("+00:00", "Z")
    with connection() as db:
        rows = db.execute(
            """SELECT entity_code, payload_json
               FROM research_a_share_history
               WHERE dataset=? AND entity_code LIKE ? AND observed_at<?
               ORDER BY observed_at DESC""",
            (DATASET, f"{asset}:%", cutoff),
        ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
            interval = str(payload["interval"])
            session = str(payload["session"])
            interval_seeds = seeds.setdefault(interval, {})
            if (
                interval in _INTERVALS
                and session in _SESSION_LABELS
                and session not in interval_seeds
            ):
                interval_seeds[session] = Decimal(str(payload["value"]))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
    return seeds


def _rebase_points_to_window(points: list[dict[str, Any]]) -> None:
    """Rebase each session to zero at its first point in the requested window."""
    baselines: dict[str, Decimal] = {}
    for point in points:
        session = str(point.get("session") or "")
        try:
            value = Decimal(str(point["value"]))
        except (KeyError, TypeError, InvalidOperation):
            continue
        if session and session not in baselines:
            baselines[session] = value
    for point in points:
        session = str(point.get("session") or "")
        baseline = baselines.get(session)
        if baseline is None:
            continue
        try:
            rebased = Decimal(str(point["value"])) - baseline
            point["value"] = "0" if rebased == 0 else format(rebased, "f")
        except (KeyError, TypeError, InvalidOperation):
            continue


def read_cumulative_volatility(
    asset: str = "btc", days: int = _MAX_RANGE_DAYS, interval: str = "15m"
) -> dict[str, Any]:
    if asset not in _ASSETS or interval not in _INTERVALS:
        raise ValueError("asset must be btc|gold and interval must be 15m|1h|4h")
    cutoff = datetime.now(UTC) - timedelta(days=max(1, min(days, _MAX_RANGE_DAYS)))
    with connection() as db:
        rows = db.execute(
            """SELECT observed_at, entity_code, payload_json, source
               FROM research_a_share_history
               WHERE dataset=? AND entity_code LIKE ? AND observed_at>=?
               ORDER BY observed_at ASC""",
            (DATASET, f"{asset}:%", cutoff.isoformat().replace("+00:00", "Z")),
        ).fetchall()
    points: list[dict[str, Any]] = []
    source = SOURCE
    for row in rows:
        source = row["source"] or source
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except (TypeError, ValueError):
            continue
        if payload.get("interval") != interval:
            continue
        value = payload.get("value")
        if value is None:
            continue
        points.append(
            {
                "timestamp": payload.get("timestamp") or row["observed_at"],
                "session": payload.get("session"),
                "sessionDate": payload.get("sessionDate"),
                "value": value,
                "price": payload.get("price"),
                "priceBaseline": payload.get("priceBaseline"),
                "priceChangePct": payload.get("priceChangePct"),
            }
        )
    points.sort(key=lambda point: (point["timestamp"], point["session"]))
    # Stored values are absolute within retained history; the chart contract
    # is relative to the requested window, just like the reference notebook.
    _rebase_points_to_window(points)
    as_of = points[-1]["timestamp"] if points else None
    is_stale = bool(
        as_of
        and datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        < datetime.now(UTC) - _STALE_AFTER
    )
    return {
        "schemaVersion": "1.0",
        "asset": asset,
        "interval": interval,
        "baseInterval": "15m",
        "timezone": "UTC",
        "source": source,
        "asOf": as_of,
        "availableFrom": points[0]["timestamp"] if points else None,
        "availableTo": points[-1]["timestamp"] if points else None,
        "isStale": is_stale,
        "message": ("当前范围暂无已落库观测。" if not points else None),
        "points": points,
    }


def refresh_cumulative_volatility(*, days: int = _MAX_RANGE_DAYS, force: bool = False) -> str:
    """Collect and publish both assets; one source failure does not erase the other."""
    del force  # Kept for the shared refresh worker's interface.
    end = datetime.now(UTC)
    full_start = end - timedelta(days=max(1, min(days, _MAX_RANGE_DAYS)) + 1)
    run_id = f"volatility-{uuid4().hex}"
    start_refresh(run_id, None)
    points: list[tuple[str, str, dict[str, Any]]] = []
    failures: list[str] = []
    successful_backfills: set[str] = set()
    for asset in _ASSETS:
        latest = _latest_persisted_timestamp(asset)
        earliest = _earliest_persisted_timestamp(asset)
        rebuild_requested = bool(
            latest
            and (
                _needs_price_backfill(asset)
                or (
                    earliest
                    and earliest > full_start + _DERIVED_WINDOW_TOLERANCE
                )
            )
        )
        needs_backfill = rebuild_requested
        if needs_backfill or not latest:
            start = full_start
        else:
            start = max(full_start, latest - timedelta(days=2))
        write_cutoff = None if needs_backfill or not latest else latest - timedelta(hours=2)
        seeds = _seed_cumulative(asset, start) if latest and not needs_backfill else None
        try:
            candles = _shared_bybit_bars(asset, start, end)
        except (KeyError, OSError, TypeError, ValueError):
            candles = []
        if not candles:
            failures.append(asset)
            continue
        # Do not repeatedly replace the read model while the shared source
        # archive is still catching up. Once the source reaches the requested
        # historical floor, the next refresh performs the bounded rebuild.
        rebuild_ready = bool(
            rebuild_requested
            and min(timestamp for timestamp, _ in candles)
            <= full_start + _DERIVED_WINDOW_TOLERANCE
        )
        if rebuild_requested and not rebuild_ready and latest:
            needs_backfill = False
            start = max(full_start, latest - timedelta(days=2))
            write_cutoff = latest - timedelta(hours=2)
            seeds = _seed_cumulative(asset, start)
            try:
                candles = _shared_bybit_bars(asset, start, end)
            except (KeyError, OSError, TypeError, ValueError):
                candles = []
            if not candles:
                failures.append(asset)
                continue
        try:
            calculated = calculate_cumulative_volatility(candles, initial_cumulative=seeds)
            if rebuild_ready:
                successful_backfills.add(asset)
            points.extend(
                (
                    point["timestamp"],
                    f"{asset}:{point['session']}:{point['interval']}",
                    _point_payload(point, asset),
                )
                for point in calculated["points"]
                if write_cutoff is None
                or datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00")) >= write_cutoff
            )
        except (TypeError, ValueError, InvalidOperation) as exc:
            failures.append(f"{asset}:{type(exc).__name__}")
    if successful_backfills:
        # The first price-overlay rollout replaces the derived rows for each
        # successfully recalculated asset. This removes obsolete pre-overlay
        # sampling points (which cannot be safely upserted by timestamp alone)
        # without touching the strategy-owned raw archive or a failed asset.
        with connection() as db:
            for asset in successful_backfills:
                db.execute(
                    "DELETE FROM research_a_share_history WHERE dataset=? AND entity_code LIKE ?",
                    (DATASET, f"{asset}:%"),
                )
    if points:
        write_history_points(run_id, DATASET, points, source=SOURCE)
    if failures and not points:
        message = f"Shared Bybit strategy candles unavailable for: {', '.join(failures)}"
        finish_refresh(run_id, "error", error_code="ResearchProviderError", message=message)
        raise ResearchProviderError(message)
    if failures:
        finish_refresh(
            run_id,
            "partial",
            error_code="partial_source_failure",
            message=", ".join(failures),
        )
        return "partial"
    finish_refresh(run_id, "ready")
    return "ready"
