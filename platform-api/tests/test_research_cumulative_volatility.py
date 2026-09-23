from datetime import UTC, datetime

import pytest

import app.research_cumulative_volatility as cumulative
from app.config import get_settings
from app.database import initialize_database
from app.research_cumulative_volatility import (
    calculate_cumulative_volatility,
    read_cumulative_volatility,
)
from app.research_cumulative_volatility import _rebase_points_to_window


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
