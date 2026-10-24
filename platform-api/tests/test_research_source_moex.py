import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app import research_provider_market_detail as provider
from app import research_source_moex as moex

NOW = datetime(2026, 10, 15, 17, tzinfo=UTC)


def block(cols, rows):
    return dict(columns=cols, data=rows)


def history(offset=0):
    return {
        "history": block(
            ["SECID", "BOARDID", "CURRENCYID", "TRADEDATE", "CLOSE"],
            [
                [
                    "IMOEX",
                    "SNDX",
                    "RUB",
                    "2026-10-13" if offset == 0 else "2026-10-14",
                    2400 if offset == 0 else 2410,
                ]
            ],
        ),
        "history.cursor": block(["INDEX", "TOTAL", "PAGESIZE"], [[offset, 2, 1]]),
    }


def quote():
    return {
        "securities": block(
            ["SECID", "BOARDID", "CURRENCYID", "CALCMODE"], [["IMOEX", "SNDX", "RUB", "PR"]]
        ),
        "marketdata": block(
            ["SECID", "BOARDID", "TRADEDATE", "SYSTIME", "CURRENTVALUE"],
            [["IMOEX", "SNDX", "2026-10-15", "2026-10-15 20:00:00", 2420.12]],
        ),
    }


class Response:
    def __init__(self, payload):
        self.payload = payload
        self.content = json.dumps(payload).encode()

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class Client:
    def __init__(self):
        self.calls = []
        self.broken = False

    async def get(self, url, params, **kwargs):
        self.calls.append((url, params))
        payload = history(params["start"]) if url == moex.HISTORY_URL else quote()
        if self.broken and url == moex.HISTORY_URL:
            payload["history"]["data"][0][0] = "RSX"
        return Response(payload)


def test_official_history_pagination_incremental_cache_and_intraday(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    client = Client()
    result = asyncio.run(moex.fetch_imoex(client, "test", now=NOW))
    assert len(client.calls) == 3
    assert result[0] == "global-rsx" and result[1][-1] == ("2026-10-15", Decimal("2420.12"))
    assert result[2] == "Europe/Moscow" and result[3]["price_kind"] == "intraday"
    assert result[3]["as_of"] == "2026-10-15T20:00:00+03:00"
    cache = moex.read_local_json(moex.CACHE_PATH)
    assert not list((tmp_path / "public/v1").glob("*/series/*.json"))
    assert [r["date"] for r in cache["observations"]] == ["2026-10-13", "2026-10-14"]
    client.calls = []
    asyncio.run(moex.fetch_imoex(client, "test", now=NOW))
    assert client.calls[0][1]["from"] == "2026-10-07"
    before = (tmp_path / moex.CACHE_PATH).read_bytes()
    client.broken = True
    with pytest.raises(ValueError, match="identity"):
        asyncio.run(moex.fetch_imoex(client, "test", now=NOW))
    assert (tmp_path / moex.CACHE_PATH).read_bytes() == before
    assert list((tmp_path / "raw/market-detail/moex").rglob("*.metadata.json"))


def test_global_uses_moex_and_preserves_identity_and_units(monkeypatch):
    monkeypatch.setattr(provider, "MARKET_SYMBOLS", {"global": {"global-rsx": "IMOEX"}})

    async def source(*args, **kwargs):
        return (
            "global-rsx",
            [("2026-10-13", Decimal("2400")), ("2026-10-14", Decimal("2410"))],
            "Europe/Moscow",
            dict(
                currency="RUB",
                price_kind="close",
                source="Moscow Exchange",
                source_url=moex.SOURCE_URL,
                name="俄罗斯（MOEX 指数）",
                unit="index",
                quality_flags=["local_currency_price_index"],
            ),
        )

    monkeypatch.setattr(moex, "fetch_imoex", source)
    result = asyncio.run(
        provider.MarketDetailProvider(timeout_seconds=1, user_agent="test")._get_live_market_detail(
            "global"
        )
    )
    row = result.rows[0]
    assert result.status == "ready" and row.symbol == "IMOEX"
    assert row.unit == "index" and row.currency == "RUB" and row.source == "Moscow Exchange"
    assert row.change_1d == (Decimal("2410") / Decimal("2400") - 1) * 100
