from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

import pytest

from app import research_provider_market_detail as market_detail
from app.research_provider_errors import ResearchProviderError
from app.research_provider_market_detail import MarketDetailProvider

pytestmark = pytest.mark.unit


class _Response:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


class _Client:
    def __init__(self, payload: Any, **_: Any) -> None:
        self._payload = payload

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def get(self, _url: str, **_kwargs: Any) -> _Response:
        return _Response(self._payload)


def _payload() -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "marketId": "macro",
        "status": "ready",
        "asOf": "2026-08-31",
        "retrievedAt": "2026-09-01T06:37:19Z",
        "rows": [
            {
                "id": "macro-us10y",
                "name": "美国 10Y",
                "symbol": "US10Y",
                "status": "ready",
                "unit": "percent",
                "changeUnit": "basis_points",
                "frequency": "daily_business_day",
                "timezone": "America/New_York",
                "observationDate": "2026-08-31",
                "asOf": "2026-08-31",
                "source": "us_treasury",
                "methodologyVersion": "market_detail_windows_v1",
                "qualityFlags": ["insufficient_52w_history"],
                "close": 4.75,
                "change1d": 2,
                "change1w": 5,
                "change1m": 0,
                "changeQtd": 31,
                "changeYtd": None,
                "change1y": None,
                "high52w": None,
                "distance52wHigh": None,
                "spark30d": [4.7, 4.75],
            }
        ],
    }


def test_provider_preserves_decimal_and_unavailable_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(market_detail, "read_local_json", lambda _path: _payload())
    provider = MarketDetailProvider(timeout_seconds=5, user_agent="test")

    contract = asyncio.run(provider.get("macro"))

    assert str(contract.rows[0].close) == "4.75"
    assert str(contract.rows[0].change_1d) == "2"
    assert contract.rows[0].change_ytd is None


def test_provider_does_not_enable_deferred_market():
    provider = MarketDetailProvider(timeout_seconds=5, user_agent="test")

    with pytest.raises(ResearchProviderError, match="market_detail_not_enabled"):
        asyncio.run(provider.get("unsupported"))


def test_gold_provider_builds_real_90_day_series_and_ratio(monkeypatch: pytest.MonkeyPatch):
    yahoo_payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1_700_000_000 + day * 86_400 for day in range(100)],
                    "indicators": {"quote": [{"close": [100 + day for day in range(100)]}]},
                }
            ]
        }
    }
    monkeypatch.setattr(
        market_detail.httpx,
        "AsyncClient",
        lambda **kwargs: _Client(yahoo_payload, **kwargs),
    )
    provider = MarketDetailProvider(timeout_seconds=5, user_agent="test")

    contract = asyncio.run(provider._get_live_market_detail("gold"))

    assert contract.status == "partial"
    assert len(contract.rows) == 17
    assert all(len(row.spark_90d) == 90 for row in contract.rows if row.sample_size is None)
    ratio = next(row for row in contract.rows if row.id == "gold-ratio-row")
    assert ratio.spark_90d[-1] == Decimal("1")
    gold = next(row for row in contract.rows if row.id == "gold-xau-row")
    assert gold.close == Decimal("199")
    assert gold.change_1d == (Decimal("199") / Decimal("198") - 1) * Decimal("100")
    assert gold.change_1w is not None
    assert gold.change_1m is not None
    assert gold.change_qtd is not None
    assert gold.change_ytd is not None
    assert gold.high_52w is None


def test_live_provider_fails_closed_when_every_symbol_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        market_detail.httpx,
        "AsyncClient",
        lambda **kwargs: _Client({"chart": {"result": []}}, **kwargs),
    )
    provider = MarketDetailProvider(timeout_seconds=5, user_agent="test")

    with pytest.raises(ResearchProviderError, match="market_detail_no_live_rows"):
        asyncio.run(provider._get_live_market_detail("crypto"))


def test_crypto_provider_includes_hype_series():
    assert market_detail.CRYPTO_YAHOO_SYMBOLS["crypto-hype-row"] == "HYPE-USD"


def test_breadth_excludes_wrong_date_and_insufficient_history():
    from datetime import date, timedelta

    today = date.today() - timedelta(days=2)
    points = [((today - timedelta(days=209 - i)).isoformat(), Decimal(i + 1)) for i in range(210)]
    series = {key: points for key in market_detail.BREADTH_POOLS["crypto"]}
    series["crypto-eth-row"] = points[:-1]
    series["crypto-sol-row"] = points[-30:]
    result = market_detail._breadth_rows("crypto", series)
    assert [row.sample_size for row in result] == [6, 5, 5]
    assert all(row.expected_sample_size == 7 and row.status == "partial" for row in result)
    assert all(row.close == 100 for row in result)
    assert all(row.observation_date == today.isoformat() for row in result)
    assert market_detail._breadth_rows("us", series) == []


def test_breadth_equality_is_not_above_and_no_history_is_missing():
    from datetime import date, timedelta

    points = [((date.today() - timedelta(days=21 - i)).isoformat(), Decimal(10)) for i in range(20)]
    rows = market_detail._breadth_rows("gold", {"gold-xau-row": points})
    assert rows[0].close == 0
    assert rows[1].close is None and rows[1].status == "no_data"


def test_cboe_reader_preserves_source_and_does_not_refresh_old_data(monkeypatch):
    def document(path):
        symbol = path.rsplit("/", 1)[1].split(".")[0]
        return dict(
            seriesId=symbol,
            observations=[dict(date="2026-01-01", value="36.020000")],
            source="Cboe Global Indices",
            sourceUrl="https://cdn-api.cboe.com/",
            timezone="America/New_York",
            frequency="daily_business_day",
            status="ready",
            retrievedAt="2026-01-02T00:00:00Z",
        )

    monkeypatch.setattr(market_detail, "read_local_json", document)
    rows = market_detail._cboe_rows()
    assert len(rows) == 2
    assert rows[0].close == Decimal("36.020000")
    assert all(row.status == "stale" and row.source == "Cboe Global Indices" for row in rows)
    monkeypatch.setattr(market_detail, "read_local_json", lambda _: {})
    assert market_detail._cboe_rows() == []


def test_cboe_survives_independent_yahoo_outage(monkeypatch):
    monkeypatch.setattr(market_detail.httpx, "AsyncClient", lambda **kwargs: _Client({}, **kwargs))
    row = market_detail._market_row("us-dspx", [("2026-10-09", Decimal("36.02"))])
    row.source = "Cboe Global Indices"
    row.symbol = "DSPX"
    monkeypatch.setattr(market_detail, "_cboe_rows", lambda: [row])
    provider = MarketDetailProvider(timeout_seconds=5, user_agent="test")
    snapshot = asyncio.run(provider._get_live_market_detail("us"))
    assert snapshot.status == "partial"
    assert snapshot.rows[0].close == Decimal("36.02")
    assert snapshot.rows[0].source == "Cboe Global Indices"


def test_breadth_does_not_count_open_utc_day():
    from datetime import UTC, datetime, timedelta

    today = datetime.now(UTC).date()
    points = [((today - timedelta(days=20 - i)).isoformat(), Decimal(10)) for i in range(21)]
    points[-1] = (today.isoformat(), Decimal(100))
    rows = market_detail._breadth_rows("crypto", {"crypto-btc-row": points})
    assert rows[0].close == 0
    assert rows[0].observation_date == (today - timedelta(days=1)).isoformat()
