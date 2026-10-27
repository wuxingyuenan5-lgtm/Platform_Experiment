import asyncio
from decimal import Decimal

import httpx

from app.database import connection, initialize_database
from app.research_a_share_repository import start_refresh
from app.research_market_history import archive_snapshot
from app.research_provider_market_detail import (
    MarketDetailProvider,
    MarketDetailResponse,
    MarketDetailRow,
)


def test_price_archive_uses_source_instrument_identity_and_excludes_intraday():
    initialize_database()
    start_refresh("archive-test", None)

    def snapshot(kind):
        row = MarketDetailRow(
            status="ready",
            unit="price",
            change_unit="percent",
            frequency="daily",
            methodology_version="test-v1",
            id="consumer-alias",
            name="SPY",
            symbol="SPY",
            source="Yahoo Finance",
            source_url="https://finance.yahoo.com/",
            timezone="America/New_York",
            currency="USD",
            close=Decimal("123.123456789"),
            observation_date="2026-10-23",
            price_kind=kind,
        )
        return MarketDetailResponse(market_id="us", status="ready", rows=[row])

    archive_snapshot("us", snapshot("intraday"), "archive-test")
    with connection() as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM research_a_share_history WHERE dataset='market_price'"
            ).fetchone()[0]
            == 0
        )
    archive_snapshot("us", snapshot("close"), "archive-test")
    archive_snapshot("global", snapshot("close"), "archive-test")
    with connection() as db:
        rows = db.execute(
            "SELECT entity_code,payload_json FROM research_a_share_history "
            "WHERE dataset='market_price'"
        ).fetchall()
    assert len(rows) == 1 and rows[0]["entity_code"] == "Yahoo Finance:SPY"
    assert "123.123456789" in rows[0]["payload_json"]


def test_long_history_fetch_is_explicit_and_preserves_negative_futures_quotes():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "chart": {
                    "result": [
                        {
                            "meta": {"exchangeTimezoneName": "UTC", "currency": "USD"},
                            "timestamp": [1587340800, 1587427200],
                            "indicators": {"quote": [{"close": [-37.63, 10.01]}]},
                        }
                    ]
                }
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            provider = MarketDetailProvider(timeout_seconds=5, user_agent="test")
            return await provider._fetch_yahoo_history(client, "wti", "CL=F", full_history=True)

    _, points, _, _ = asyncio.run(run())
    assert requests[0].url.params["period1"] == "0"
    assert requests[0].url.params["interval"] == "1d"
    assert points[0][1] == Decimal("-37.63")


def test_hong_kong_history_uses_its_native_endpoint(monkeypatch):
    from app.research_provider_a_share import AShareResearchProvider

    provider = AShareResearchProvider(
        timeout_seconds=5, user_agent="test", akshare_loader=lambda: None
    )
    urls = []

    def fetch(_opener, url, *_args, **_kwargs):
        urls.append(url)
        return {"data": {"hk00700": {"qfqday": [["2026-10-23", "100", "101"]]}}}

    monkeypatch.setattr(provider, "_direct_json", fetch)
    assert len(provider._direct_stock_history("00700")) == 1
    assert "/hkfqkline/" in urls[0]
