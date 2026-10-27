from datetime import UTC, datetime, timedelta

import pytest

import app.research_cumulative_volatility as cumulative
from app.config import get_settings
from app.database import initialize_database
from app.research_cumulative_volatility import (
    _rebase_points_to_window,
    calculate_cumulative_volatility,
    read_cumulative_volatility,
)


def _candle(timestamp: str, close: float) -> list[object]:
    epoch = int(datetime.fromisoformat(timestamp).replace(tzinfo=UTC).timestamp())
    return [str(epoch), str(close), str(close), str(close), str(close), "1", "1"]


def _points(result: dict, interval: str = "15m") -> list[dict]:
    return [point for point in result["points"] if point["interval"] == interval]


def test_uses_reference_utc_session_boundaries_and_carries_cumulative_value() -> None:
    candles = [
        _candle("2026-09-10T23:00:00", 100),
        _candle("2026-09-10T23:15:00", 101),
        _candle("2026-09-11T00:00:00", 100),
        _candle("2026-09-11T07:00:00", 102),
        _candle("2026-09-11T07:15:00", 100),
        _candle("2026-09-11T15:00:00", 105),
        _candle("2026-09-11T15:15:00", 105),
    ]

    points = _points(calculate_cumulative_volatility(candles))
    asia = [point for point in points if point["session"] == "asia"]
    europe = [point for point in points if point["session"] == "europe"]
    americas = [point for point in points if point["session"] == "americas"]

    assert asia[0]["sessionDate"] == "2026-09-11"
    assert float(asia[0]["value"]) == pytest.approx(0)
    assert float(asia[1]["value"]) == pytest.approx(1)
    assert float(asia[2]["value"]) == pytest.approx(1 + (100 / 101 - 1) * 100)
    assert europe[0]["value"] == "0"
    assert float(europe[1]["value"]) == pytest.approx(-2 / 102 * 100)
    assert americas[0]["value"] == "0"
    assert americas[1]["value"] == "0"


def test_returns_all_sampling_levels_without_crossing_session_boundaries() -> None:
    candles = [
        _candle(f"2026-09-10T{hour:02d}:{minute:02d}:00", 100 + hour + minute / 100)
        for hour in range(0, 24)
        for minute in (0, 15, 30, 45)
    ]
    points = calculate_cumulative_volatility(candles)["points"]
    assert {point["interval"] for point in points} == {"15m", "1h", "4h"}
    for interval in ("1h", "4h"):
        assert all(point["session"] for point in points if point["interval"] == interval)


def test_emits_price_and_americas_baseline_for_price_overlay() -> None:
    candles = [
        _candle("2026-09-10T15:00:00", 100),
        _candle("2026-09-10T15:15:00", 101),
        _candle("2026-09-10T23:00:00", 99),
    ]
    points = _points(calculate_cumulative_volatility(candles))
    americas = [point for point in points if point["session"] == "americas"]
    assert americas[0]["price"] == "100"
    assert americas[0]["priceBaseline"] == "100"
    assert float(americas[1]["priceChangePct"]) == pytest.approx(1)
    asia = [point for point in points if point["session"] == "asia"]
    assert asia[0]["price"] == "99"
    assert asia[0]["priceBaseline"] is None


def test_deduplicates_overlapping_provider_pages_by_timestamp() -> None:
    candles = [
        _candle("2026-09-10T07:00:00", 100),
        _candle("2026-09-10T07:15:00", 101),
        _candle("2026-09-10T07:15:00", 102),
    ]
    points = [
        point
        for point in calculate_cumulative_volatility(candles)["points"]
        if point["interval"] == "15m" and point["session"] == "europe"
    ]
    assert len(points) == 2
    assert float(points[-1]["value"]) == pytest.approx(2)


def test_read_window_rebases_each_session_to_zero() -> None:
    points = [
        {"session": "asia", "value": "12.5"},
        {"session": "europe", "value": "-3"},
        {"session": "asia", "value": "13.25"},
        {"session": "europe", "value": "-2.5"},
    ]
    _rebase_points_to_window(points)
    assert [point["value"] for point in points] == ["0", "0", "0.75", "0.5"]


def test_refresh_publishes_read_model_from_shared_strategy_archive(monkeypatch) -> None:
    initialize_database()

    def fake_shared(asset: str, _start: datetime, _end: datetime) -> list[tuple[datetime, object]]:
        close = 100 if asset == "btc" else 200
        return [
            (datetime(2026, 9, 10, 15, 0, tzinfo=UTC), close),
            (datetime(2026, 9, 10, 15, 15, tzinfo=UTC), close + 1),
        ]

    monkeypatch.setattr(cumulative, "_shared_bybit_bars", fake_shared)
    assert cumulative.refresh_cumulative_volatility(days=1) == "ready"
    result = read_cumulative_volatility("btc", 90, "15m")
    assert result["schemaVersion"] == "1.0"
    assert result["source"] == cumulative.SOURCE
    assert result["points"]
    assert get_settings().database_path


@pytest.mark.parametrize("interval", ["15m", "1h", "4h"])
def test_custom_window_rebases_in_backend_without_changing_stored_history(interval) -> None:
    from app.research_a_share_repository import start_refresh, write_history_points

    initialize_database()
    start_refresh("window-test", None)
    origin = datetime.now(UTC).replace(microsecond=0) - timedelta(days=10)
    stamps = [(origin + timedelta(days=i)).isoformat().replace("+00:00", "Z") for i in range(3)]
    records = [
        (
            stamp,
            f"btc:{session}:{interval}",
            {
                "timestamp": stamp,
                "session": session,
                "sessionDate": stamp[:10],
                "interval": interval,
                "value": str(10 * (n + 1) + i),
                "price": "100",
            },
        )
        for i, stamp in enumerate(stamps)
        for n, session in enumerate(("asia", "europe", "americas"))
    ]
    write_history_points("window-test", cumulative.DATASET, records, source=cumulative.SOURCE)
    full = read_cumulative_volatility("btc", 30, interval)
    selected = read_cumulative_volatility(
        "btc",
        30,
        interval,
        start=origin + timedelta(days=1),
        end=origin + timedelta(days=2),
    )
    assert len(selected["points"]) == 6
    for session in ("asia", "europe", "americas"):
        points = [p for p in selected["points"] if p["session"] == session]
        assert [p["value"] for p in points] == ["0", "1"]
    assert selected["availableFrom"] == stamps[0]
    assert selected["availableTo"] == stamps[-1]
    assert read_cumulative_volatility("btc", 30, interval)["points"] == full["points"]
    historical = read_cumulative_volatility("btc", 30, interval, end=origin)
    assert historical["asOf"] == stamps[-1]


def test_custom_window_rejects_naive_or_reversed_timestamps() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="timezone"):
        read_cumulative_volatility(start=now.replace(tzinfo=None))
    with pytest.raises(ValueError, match="after"):
        read_cumulative_volatility(start=now, end=now - timedelta(days=1))


def test_provisional_refresh_replaces_bucket_and_keeps_other_assets(monkeypatch) -> None:
    import json

    from app.database import connection
    from app.research_a_share_repository import start_refresh, write_history_points

    initialize_database()
    start_refresh("sample-test", None)
    day = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()

    def record(asset, time, value):
        stamp = f"{day}T{time}:00Z"
        return (
            stamp,
            f"{asset}:europe:4h",
            {
                "asset": asset,
                "timestamp": stamp,
                "session": "europe",
                "sessionDate": day,
                "interval": "4h",
                "value": str(value),
                "price": "100",
            },
        )

    initial = [
        record("btc", "07:10", 2),
        record("btc", "07:15", 3),
        record("gold", "07:10", 9),
        record("btc", "11:10", 4),
    ]
    write_history_points("sample-test", cumulative.DATASET, initial, source=cumulative.SOURCE)
    result = read_cumulative_volatility("btc", 30, "4h")
    assert [p["timestamp"][11:16] for p in result["points"]] == ["07:15", "11:10"]
    assert [p["value"] for p in result["points"]] == ["0", "1"]
    replacement = [record("btc", "07:20", 3.5)]
    cumulative._publish_samples("sample-test", replacement, set())
    with connection() as db:
        rows = db.execute(
            "SELECT entity_code,payload_json FROM research_a_share_history"
        ).fetchall()
    assert len(rows) == 3
    assert any(r["entity_code"].startswith("gold:") for r in rows)
    assert "07:20" in next(
        json.loads(r["payload_json"])["timestamp"]
        for r in rows
        if json.loads(r["payload_json"])["value"] == "3.5"
    )

    def fail_write(*args, **kwargs):
        raise RuntimeError("publication failure")

    monkeypatch.setattr(cumulative, "write_history_points", fail_write)
    with pytest.raises(RuntimeError, match="publication failure"):
        cumulative._publish_samples("sample-test", [record("btc", "07:25", 4)], {"btc"})
    timestamp = read_cumulative_volatility("btc", 30, "4h")["points"][0]["timestamp"]
    assert timestamp.endswith("07:20:00Z")


def test_internal_gap_rebuild_requires_valid_shared_source_and_does_not_loop_on_real_gaps():
    import json

    from app.database import connection
    from app.research_a_share_repository import start_refresh, write_history_points

    initialize_database()
    start_refresh("gap-test", None)
    origin = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=10
    )
    records = []
    for offset in (0, 4):
        stamp = (origin + timedelta(days=offset, hours=8)).isoformat().replace("+00:00", "Z")
        records.append(
            (
                stamp,
                "gold:europe:15m",
                {
                    "timestamp": stamp,
                    "session": "europe",
                    "sessionDate": stamp[:10],
                    "interval": "15m",
                    "value": "0",
                    "price": "100",
                },
            )
        )
    write_history_points("gap-test", cumulative.DATASET, records, source=cumulative.SOURCE)
    assert not cumulative._has_recoverable_gap("gold", origin, origin + timedelta(days=5))
    time = int((origin + timedelta(days=2, hours=8)).timestamp() * 1000)
    payload = {
        "symbol": "XAUTUSDT",
        "category": "linear",
        "priceType": "trade",
        "close": "100",
        "quality": ["invalid"],
    }
    with connection() as db:
        db.execute(
            "INSERT INTO research_strategy_projection VALUES(?,?,?,?)",
            ("historical_candle", "XAUTUSDT:linear:trade", time, json.dumps(payload)),
        )
    assert not cumulative._has_recoverable_gap("gold", origin, origin + timedelta(days=5))
    payload["quality"] = []
    with connection() as db:
        db.execute(
            "UPDATE research_strategy_projection SET payload_json=? "
            "WHERE kind='historical_candle' AND entity='XAUTUSDT:linear:trade'",
            (json.dumps(payload),),
        )
    assert cumulative._has_recoverable_gap("gold", origin, origin + timedelta(days=5))
    assert not cumulative._has_recoverable_gap("btc", origin, origin + timedelta(days=5))
    stamp = (origin + timedelta(days=2, hours=8)).isoformat().replace("+00:00", "Z")
    write_history_points(
        "gap-test",
        cumulative.DATASET,
        [
            (
                stamp,
                "gold:europe:15m",
                {
                    "timestamp": stamp,
                    "session": "europe",
                    "sessionDate": stamp[:10],
                    "interval": "15m",
                    "value": "1",
                    "price": "100",
                },
            )
        ],
        source=cumulative.SOURCE,
    )
    assert not cumulative._has_recoverable_gap("gold", origin, origin + timedelta(days=5))


def test_all_range_reads_stored_points_before_one_year():
    from app.research_a_share_repository import start_refresh, write_history_points

    initialize_database()
    start_refresh("all-range-test", None)
    day = (datetime.now(UTC) - timedelta(days=500)).date().isoformat()
    stamp = day + "T08:00:00Z"
    write_history_points(
        "all-range-test",
        cumulative.DATASET,
        [
            (
                stamp,
                "btc:europe:15m",
                {
                    "timestamp": stamp,
                    "session": "europe",
                    "sessionDate": day,
                    "interval": "15m",
                    "value": "1",
                    "price": "100",
                },
            )
        ],
        source=cumulative.SOURCE,
    )
    assert read_cumulative_volatility("btc", 365, "15m")["points"] == []
    assert read_cumulative_volatility("btc", 0, "15m")["points"][0]["timestamp"] == stamp


def test_incremental_refresh_republishes_revised_cumulative_overlap(monkeypatch) -> None:
    import json
    from decimal import Decimal

    from app.database import connection

    initialize_database()
    now = datetime.now(UTC)
    day = (now - timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
    candles = [
        (day, Decimal("100")),
        (day + timedelta(minutes=15), Decimal("110")),
        (day + timedelta(hours=1), Decimal("105")),
        (now - timedelta(minutes=1), Decimal("108")),
    ]
    monkeypatch.setattr(cumulative, "_shared_bybit_bars", lambda *_: candles)
    monkeypatch.setattr(cumulative, "_needs_price_backfill", lambda *_: False)
    monkeypatch.setattr(cumulative, "_has_recoverable_gap", lambda *_: False)
    monkeypatch.setattr(
        cumulative, "_earliest_persisted_timestamp", lambda *_: now - timedelta(days=367)
    )
    cumulative.refresh_cumulative_volatility()
    # An archive repair changes an earlier first close, well outside the last
    # two hours. Its later cumulative values must be replaced together.
    candles[0] = (day, Decimal("90"))
    cumulative.refresh_cumulative_volatility()
    expected = calculate_cumulative_volatility(candles)["points"]
    with connection() as db:
        for point in expected:
            row = db.execute(
                "SELECT payload_json FROM research_a_share_history "
                "WHERE dataset=? AND entity_code=? AND observed_at=?",
                (
                    cumulative.DATASET,
                    f"btc:{point['session']}:{point['interval']}",
                    point["timestamp"],
                ),
            ).fetchone()
            assert json.loads(row[0])["value"] == point["value"]


def test_runtime_repair_starts_at_session_boundary_when_archive_is_empty(monkeypatch):
    from types import SimpleNamespace

    import app.strategy_research_projection as projection

    monkeypatch.setattr(projection, "read_projection", lambda *_: [])
    requests = []
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"rows": []})

    def get(_url, **kwargs):
        requests.append(kwargs["params"])
        return response

    monkeypatch.setattr(cumulative.runtime_transport, "get", get)
    end = datetime(2026, 10, 26, 17, 26, tzinfo=UTC)
    start = datetime(2026, 10, 24, 15, tzinfo=UTC)
    assert cumulative._shared_bybit_bars("btc", start, end) == []
    assert int(requests[0]["startMs"]) == int(start.timestamp() * 1000)
