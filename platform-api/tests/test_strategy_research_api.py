"""Real FastAPI/SQLite route calls against an isolated database, no venue network."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import Principal, require_principal
from app.config import get_settings
from app.database import initialize_database
from app.strategy_research_projection import project_next
from app.strategy_research_repository import publish as publish_archive
from app.strategy_research_routes import router


def publish(batch):
    result = publish_archive(batch)
    while project_next():
        pass
    return result




@pytest.fixture
def client(tmp_path):
    get_settings().strategy_research_path = str(tmp_path / "archive")
    get_settings().strategy_research_min_free_bytes = 0
    initialize_database()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_principal] = lambda: Principal("owner", ("admin",), "test")
    return TestClient(app)


def test_empty_data_and_scenario_without_fake_market(client):
    assert client.get("/api/v1/research/strategies/pairs/funding-btc/latest").json()["data"] is None
    t = datetime(2026, 9, 19, tzinfo=UTC)
    body = {
        "pairId": "funding-btc",
        "direction": "sell_spread",
        "quantity": "2",
        "entrySpread": "3.000000000000000001",
        "exitSpread": "1",
        "openedAt": t.isoformat(),
        "closedAt": (t + timedelta(minutes=1)).isoformat(),
        "costProfileId": "explicit",
        "tradingFees": "0",
        "additionalExecutionCost": "0",
        "fundingCoverage": "scenario",
        "swapCoverage": "not_applicable",
    }
    response = client.post("/api/v1/research/strategies/scenario", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["netPnl"] == "4.000000000000000002"


def test_funding_basis_all_series_are_returned_from_one_backend_route(client, monkeypatch):
    from app import strategy_research_routes as routes

    stamp = "1789776000000"
    btc_row = {
        "timeMs": stamp,
        "validDurationMs": 900000,
        "quality": [],
        "ohlc": {"midSpread": {"close": "1.25"}},
    }
    monkeypatch.setattr(
        routes,
        "read_projection",
        lambda kind, *args, **kwargs: [btc_row]
        if kind in {"spread_valid", "spread_all"}
        else [],
    )
    monkeypatch.setattr(
        routes,
        "funding_candle_basis_rows",
        lambda symbol, *args: [
            {
                "timeMs": stamp,
                "validDurationMs": 900000,
                "quality": [],
                "ohlc": {"midSpread": {"close": "2.5"}},
            }
        ],
    )

    response = client.get(
        "/api/v1/research/strategies/pairs/funding-btc/series",
        params={
            "from": "2026-09-18T00:00:00Z",
            "to": "2026-09-19T00:00:00Z",
            "view": "valid",
            "resolution": "15m",
            "symbol": "ALL",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["basisSource"] == "backend_series_projection"
    assert data["symbols"] == ["XAUT", "BTC", "ETH", "CRCL", "MSTR"]
    assert set(data["seriesBySymbol"]) == set(data["symbols"])
    assert data["seriesBySymbol"]["BTC"][0]["ohlc"]["midSpread"]["close"] == "1.25"
    assert data["seriesBySymbol"]["ETH"][0]["ohlc"]["midSpread"]["close"] == "2.5"


def test_private_scope_denied_to_public_research_reader(client):
    client.app.dependency_overrides[require_principal] = lambda: Principal(
        "viewer", ("viewer",), "test"
    )
    response = client.get("/api/v1/research/strategies/pairs/cross-gold/latest")
    assert response.status_code == 403
    assert len(client.get("/api/v1/research/strategies/catalog").json()["data"]["pairs"]) == 1


def test_get_does_not_migrate_or_backfill(client, monkeypatch):
    from app import database, runtime_transport

    monkeypatch.setattr(database, "initialize_database", lambda: pytest.fail("GET did DDL"))
    monkeypatch.setattr(
        runtime_transport, "get", lambda *a, **k: pytest.fail("GET fetched Runtime")
    )
    for url in ["catalog", "data-status", "funding/board", "pairs/funding-btc/latest"]:
        assert client.get("/api/v1/research/strategies/" + url).status_code == 200
    assert client.get("/api/v1/research/strategies/funding/board?venue=OKX").status_code == 422


def test_native_funding_settlement_revision_and_ticker_delta(client):
    from app.strategy_research_repository import read_rows
    from app.strategy_research_series import Deriver

    d = Deriver()
    base = {
        "kind": "bybit_message",
        "stream": "bybit:linear:tickers.BTCUSDT",
        "eventId": "s:1",
        "runtimeReceivedAt": "2026-09-19T00:00:00+00:00",
        "payload": {
            "type": "snapshot",
            "topic": "tickers.BTCUSDT",
            "data": {"symbol": "BTCUSDT", "fundingRate": ".1", "markPrice": "100"},
        },
    }
    d.consume(base)
    base["payload"] = {"type": "delta", "topic": "tickers.BTCUSDT", "data": {"markPrice": "101"}}
    assert d.consume(base)[0]["payload"]["fundingRate"] == ".1"
    e = dict(
        base,
        kind="funding_settlements",
        quoteScope="public",
        payload={
            "result": {
                "list": [{"symbol": "BTCUSDT", "fundingRate": ".1", "fundingRateTimestamp": "1"}]
            }
        },
    )
    assert len(d.consume(e)) == 1
    assert d.consume(e) == []
    e["payload"]["result"]["list"][0]["fundingRate"] = ".2"
    assert d.consume(e)[0]["quality"] == ["settlement_revision_conflict"]
    publish(
        {
            "schemaVersion": "market-events.v1",
            "after": None,
            "nextCursor": "one:1",
            "events": [e],
            "capture": {},
        }
    )
    assert read_rows(kind="funding_settlement")[0]["mark"] is None
    response = client.get("/api/v1/research/strategies/funding/board")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["settlements"][0]["payload"]["fundingRate"] == ".2"


def test_history_filters_source_time_not_retrieval_time_and_keeps_old_parts(client, monkeypatch):
    from app import strategy_research_routes as routes

    stamp = "1789776000000"
    price = {
        "kind": "historical_candle",
        "stream": "bybit:linear:BTCUSDT:trade",
        "symbol": "BTCUSDT",
        "category": "linear",
        "priceType": "trade",
        "sourceTimeMs": stamp,
        "closeTimeMs": stamp,
        "intervalMs": "60000",
        "close": "123.456789012345678901",
        "receivedAt": "2026-09-20T10:00:00+00:00",
    }
    settled = {
        "stream": "bybit:linear:BTCUSDT",
        "payload": {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingRateTimestamp": stamp},
        "receivedAt": "2026-09-20T10:00:00+00:00",
    }

    def read(kind, entity=None, *window, **kwargs):
        return (
            [price, dict(price), dict(price, intervalMs="900000", stream="old-overview")]
            if kind == "historical_candle"
            else [settled]
        )

    monkeypatch.setattr(
        routes, "price_coverage", lambda *a: {"count": 1, "start": stamp, "end": stamp}
    )
    monkeypatch.setattr(routes, "read_projection", read)
    response = client.get(
        "/api/v1/research/strategies/pairs/funding-btc/history",
        params={"from": "2026-09-18T00:00:00Z", "to": "2026-09-20T00:00:00Z"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data["prices"]) == 1 and len(data["settlements"]) == 1
    assert data["prices"][0]["close"] == price["close"]
    assert data["historyResolution"] == "1h"
    assert data["fundingResolution"] == "1h"
    assert data["sourcePriceCount"] == 1


def test_history_long_window_samples_display_without_rounding_source(client, monkeypatch):
    from app import strategy_research_routes as routes

    start = datetime(2026, 9, 1, tzinfo=UTC)
    stamp = int(start.timestamp() * 1000)
    rows = [
        {
            "symbol": "BTCUSDT",
            "category": "linear",
            "priceType": "trade",
            "stream": "one",
            "intervalMs": "60000",
            "sourceTimeMs": str(stamp + i * 60000),
            "closeTimeMs": str(stamp + (i + 1) * 60000),
            "close": "123.456789012345678901",
            "receivedAt": "2026-09-20T00:00:00Z",
        }
        for i in range(30)
    ]
    monkeypatch.setattr(
        routes,
        "read_projection",
        lambda kind, *args, **kwargs: rows if kind == "historical_candle" else [],
    )
    monkeypatch.setattr(
        routes,
        "price_coverage",
        lambda *a: {"count": 30, "start": str(stamp), "end": str(stamp + 30 * 60000)},
    )
    result = client.get(
        "/api/v1/research/strategies/pairs/funding-btc/history",
        params={"from": start.isoformat(), "to": (start + timedelta(days=30)).isoformat()},
    )
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["sourcePriceCount"] == 30 and len(data["prices"]) == 2
    assert [r["closeTimeMs"] for r in data["prices"]] == [
        rows[14]["closeTimeMs"],
        rows[29]["closeTimeMs"],
    ]
    assert data["prices"][0]["close"] == rows[14]["close"]


def test_history_merges_indicated_and_settled_funding_at_requested_resolution(client, monkeypatch):
    from app import strategy_research_routes as routes

    base = datetime(2026, 9, 19, tzinfo=UTC)
    price = {
        "symbol": "BTCUSDT",
        "category": "linear",
        "priceType": "trade",
        "stream": "bybit:linear:BTCUSDT:trade",
        "intervalMs": "60000",
        "sourceTimeMs": str(int(base.timestamp() * 1000)),
        "closeTimeMs": str(int((base + timedelta(minutes=1)).timestamp() * 1000)),
        "close": "81234.123456789012345678",
        "receivedAt": base.isoformat(),
    }
    indications = [
        {
            "receivedAt": (base + timedelta(minutes=5)).isoformat(),
            "payload": {"symbol": "BTCUSDT", "fundingRate": "0.0001"},
        },
        {
            "receivedAt": (base + timedelta(minutes=55)).isoformat(),
            "payload": {"symbol": "BTCUSDT", "fundingRate": "0.0002"},
        },
    ]
    settlement = {
        "receivedAt": base.isoformat(),
        "payload": {
            "symbol": "BTCUSDT",
            "fundingRate": "0.0003",
            "fundingRateTimestamp": str(int((base + timedelta(minutes=30)).timestamp() * 1000)),
        },
    }

    def read(kind, entity=None, *window, **kwargs):
        if kind == "historical_candle":
            return [price]
        if kind == "funding_minute":
            return indications
        if kind == "funding_settlement":
            return [settlement]
        return []

    monkeypatch.setattr(routes, "read_projection", read)
    monkeypatch.setattr(
        routes,
        "price_coverage",
        lambda *args: {"count": 1, "start": price["closeTimeMs"], "end": price["closeTimeMs"]},
    )
    result = client.get(
        "/api/v1/research/strategies/pairs/funding-btc/history",
        params={
            "from": base.isoformat(),
            "to": (base + timedelta(hours=1)).isoformat(),
            "symbol": "BTC",
            "resolution": "1h",
        },
    )
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["fundingResolution"] == "1h"
    assert len(data["fundingIndications"]) == 1
    assert {item["name"] for item in data["chartSeries"]} >= {
        "指标资金费率（%）",
        "已结算资金费率（%）",
    }
