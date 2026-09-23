"""Isolated synthetic evidence for serving projection/recovery, not venue coverage."""

import json
from datetime import timedelta

import pytest
from test_strategy_research import T, event

from app.config import get_settings
from app.database import initialize_database
from app.database_connection import connection
from app.strategy_research_projection import price_coverage, project_next, read_projection
from app.strategy_research_repository import publish, read_rows
from app.strategy_research_series import seconds_series


@pytest.fixture
def archive(tmp_path):
    get_settings().strategy_research_path = str(tmp_path / "archive")
    get_settings().strategy_research_min_free_bytes = 0
    initialize_database()


def test_seconds_match_whole_archive_across_shards_and_cursor_replay(archive):
    events = [
        event(i, category="spot" if i % 2 else "linear", at=T + timedelta(milliseconds=i * 170))
        for i in range(50)
    ]
    cursor = None
    for offset in range(0, len(events), 7):
        end = str(offset + 7)
        publish(
            {
                "schemaVersion": "market-events.v1",
                "after": cursor,
                "nextCursor": end,
                "events": events[offset : offset + 7],
            }
        )
        while project_next():
            pass
        cursor = end
    expected = seconds_series(read_rows(kind="spread", pair="funding-btc"))
    actual = read_projection("spread_valid", "funding-btc")
    assert actual == expected
    # Replaying all already-upserted parts models interruption before cursor commit.
    with connection() as db:
        db.execute("UPDATE research_strategy_projection_cursor SET part_rowid=0,state_json='{}'")
    while project_next():
        pass
    assert read_projection("spread_valid", "funding-btc") == expected
    assert project_next() is False


def test_indexed_sampling_preserves_decimal_and_empty_intervals(archive):
    rows = [
        (
            "historical_candle",
            "BTCUSDT:linear:trade",
            n * 60000,
            json.dumps({"close": "123.456789012345678901", "closeTimeMs": str(n * 60000)}),
        )
        for n in [1, 2, 3, 16, 17, 29]
    ]
    with connection() as db:
        db.executemany("INSERT INTO research_strategy_projection VALUES(?,?,?,?)", rows)
    assert price_coverage("BTCUSDT", 0, 30 * 60000)["count"] == 6
    points = read_projection(
        "historical_candle", "BTCUSDT:linear:trade", 0, 30 * 60000, interval_ms=900000
    )
    assert [r["closeTimeMs"] for r in points] == [str(3 * 60000), str(29 * 60000)]
    assert all(r["close"] == "123.456789012345678901" for r in points)
    assert read_projection("historical_candle", "BTCUSDT:linear:trade", 4 * 60000, 15 * 60000) == []


def test_window_get_never_reads_archive_or_triggers_projection(archive, monkeypatch):
    from app import strategy_research_routes as routes
    from app.auth import Principal

    monkeypatch.setattr(routes, "read_rows", lambda **k: pytest.fail("GET scanned Parquet"))
    owner = Principal("owner", ("admin",), "test")
    routes.historical_prices("funding-btc", owner, T, T + timedelta(days=1))
    routes.series("cross-gold", owner, T, T + timedelta(minutes=5))
    routes.funding_board(owner)


def test_funding_defaults_sort_search_and_unknowns(archive):
    from app.auth import Principal
    from app.strategy_research_routes import funding_board

    with connection() as db:
        for symbol, rate in [("BTCUSDT", ".01"), ("ETHUSDT", "-.02"), ("DOGEUSDT", ".03")]:
            db.execute(
                "INSERT INTO research_strategy_projection VALUES('funding_latest',?,0,?)",
                (
                    symbol,
                    json.dumps(
                        {
                            "receivedAt": T.isoformat(),
                            "payload": {"symbol": symbol, "fundingRate": rate},
                        }
                    ),
                ),
            )
    owner = Principal("owner", ("admin",), "test")
    data = funding_board(owner).data
    assert [r["symbol"] for r in data["board"]["rows"]] == [
        "BTC",
        "ETH",
        "SOL",
        "XAUT",
        "CRCL",
        "MSTR",
    ]
    assert data["board"]["rows"][2]["usdtPerps"]["Bybit"] is None
    assert "DOGE" in data["board"]["symbolOptions"]
    assert [r["symbol"] for r in funding_board(owner, sort="rate_asc").data["board"]["rows"]][
        :2
    ] == ["ETH", "BTC"]
    assert [
        r["symbol"]
        for r in funding_board(owner, symbols="BTC,DOGE", search="dog").data["board"]["rows"]
    ] == ["DOGE"]


def test_history_chart_roles_no_marks_and_cross_has_no_funding(archive):
    from app.auth import Principal
    from app.strategy_research_routes import historical_prices

    result = historical_prices(
        "cross-gold", Principal("owner", ("admin",), "test"), T, T + timedelta(days=1)
    )
    assert result.data["settlements"] == []
    assert all(s["axis"] == 0 for s in result.data["chartSeries"])


def test_spread_chart_preserves_exact_prices_and_breaks_gaps():
    from app.strategy_research_projection import spread_chart

    value = "1.123456789012345678901"
    series = spread_chart([
        {"timeMs": "1000", "ohlc": {"midSpread": {"close": value}}},
        {"timeMs": "4000", "ohlc": {"midSpread": {"close": value}}},
    ])
    assert [s["selected"] for s in series] == [True, False, False]
    assert series[0]["data"] == [
        {"value": [1000, value], "exactPrice": value},
        {"value": [2000, None]},
        {"value": [4000, value], "exactPrice": value},
    ]
