from __future__ import annotations

import asyncio
import ssl
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app import research_provider_a_share as a_share
from app.research_data_schemas import AShareIndexSnapshot
from app.research_provider_a_share import AShareResearchProvider
from app.research_providers import FreeResearchProvider

pytestmark = pytest.mark.unit


def test_sector_flow_uses_single_level_and_counts_all_firms(monkeypatch):
    async def quotes(_client, params, _headers):
        assert params["fs"] == "m:90+s:2+f:!50"
        return {
            "data": {
                "diff": [
                    {
                        "f12": "BK1",
                        "f14": "测试行业",
                        "f62": "123.456789",
                        "f104": 3,
                        "f105": 4,
                        "f106": 2,
                    },
                    {"f12": "BK2", "f14": "缺失家数", "f62": "-1", "f104": 3},
                ]
            }
        }

    monkeypatch.setattr(a_share, "_eastmoney_clist", quotes)
    provider = AShareResearchProvider(
        timeout_seconds=1, user_agent="test", akshare_loader=lambda: None
    )
    rows = asyncio.run(provider.sector_fund_flow())
    assert rows[0]["firm_count"] == 9
    assert rows[0]["net_inflow_yuan"] == Decimal("123.456789")
    assert rows[1]["firm_count"] is None


class _Frame:
    empty = False

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    def to_dict(self, orient: str) -> list[dict[str, Any]]:
        assert orient == "records"
        return self._records


class _Akshare:
    def stock_zh_a_spot_em(self) -> _Frame:
        return _Frame(
            [
                {"代码": "1", "名称": "测试股份", "成交额": "12,345", "涨跌幅": "3.2"},
                {"代码": "invalid", "名称": "无效", "成交额": "100"},
            ]
        )


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {"data": {"qdate": 20260731, "pool": [{"c": "600000"}]}}


class _Client:
    init_kwargs: dict[str, Any] | None = None
    request: dict[str, Any] | None = None

    def __init__(self, **kwargs: Any) -> None:
        type(self).init_kwargs = kwargs

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> _Response:
        type(self).request = {"url": url, **kwargs}
        return _Response()


def _provider() -> AShareResearchProvider:
    return AShareResearchProvider(
        timeout_seconds=7.5,
        user_agent="research-test",
        akshare_loader=_Akshare,
    )


def test_a_share_spot_preserves_field_normalization() -> None:
    result = asyncio.run(_provider()._akshare_a_share_spot())

    assert len(result) == 1
    assert result[0].security_code == "000001"
    assert result[0].security_name == "测试股份"
    assert result[0].turnover_yuan == Decimal("12345")
    assert result[0].return_pct == Decimal("3.2")


def test_eastmoney_clist_uses_delay2_node_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(a_share, "_EM_DELAY_HOST_INDEX", 0)
    monkeypatch.setattr(a_share.httpx, "AsyncClient", _Client)

    async def run() -> dict[str, Any]:
        async with a_share.httpx.AsyncClient() as client:
            return await a_share._eastmoney_clist(client, {"pn": "1"}, {})

    assert asyncio.run(run()) == {"data": {"qdate": 20260731, "pool": [{"c": "600000"}]}}
    assert _Client.request is not None
    assert _Client.request["url"] == ("https://push2delay2.eastmoney.com/api/qt/clist/get")


def test_eastmoney_clist_fails_over_after_node_disconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []
    monkeypatch.setattr(a_share, "_EM_DELAY_HOST_INDEX", 0)

    class FailoverClient:
        async def get(self, url: str, **_: Any) -> _Response:
            attempts.append(url)
            if "push2delay2" in url:
                raise httpx.ConnectError("node reset", request=httpx.Request("GET", url))
            return _Response()

    async def run() -> dict[str, Any]:
        return await a_share._eastmoney_clist(FailoverClient(), {"pn": "1"}, {})

    assert asyncio.run(run())["data"]["pool"][0]["c"] == "600000"
    assert attempts == [
        "https://push2delay2.eastmoney.com/api/qt/clist/get",
        "https://push2delay.eastmoney.com/api/qt/clist/get",
    ]


def test_innovation_drug_snapshot_normalizes_quote_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    class QuoteResponse(_Response):
        def json(self) -> dict[str, Any]:
            return {
                "data": {
                    "f43": 1495.63,
                    "f47": 50728424,
                    "f48": 80353669607.0,
                    "f86": 1790149171,
                    "f168": 3.27,
                    "f170": -0.02,
                }
            }

    class QuoteClient(_Client):
        async def get(self, url: str, **kwargs: Any) -> QuoteResponse:
            type(self).request = {"url": url, **kwargs}
            return QuoteResponse()

    monkeypatch.setattr(a_share, "_EM_DELAY_HOST_INDEX", 0)
    monkeypatch.setattr(a_share.httpx, "AsyncClient", QuoteClient)

    result = asyncio.run(_provider().innovation_drug_snapshot())

    assert result["amount_yuan"] == Decimal("80353669607")
    assert result["turnover_pct"] == Decimal("3.27")
    assert result["return_pct"] == Decimal("-0.0002")
    assert result["observed_at"].isoformat() == "2026-09-23T07:39:31+00:00"
    assert QuoteClient.request is not None
    assert QuoteClient.request["url"] == ("https://push2delay2.eastmoney.com/api/qt/stock/get")


def test_sector_crowding_snapshot_collects_direct_board_amount_and_turnover(monkeypatch) -> None:
    class QuoteResponse(_Response):
        def json(self) -> dict[str, Any]:
            return {
                "data": {
                    "f43": 1000,
                    "f47": 123456,
                    "f48": 123456789000,
                    "f86": 1790149171,
                    "f168": 3.52,
                }
            }

    class QuoteClient(_Client):
        async def get(self, url: str, **kwargs: Any) -> QuoteResponse:
            type(self).request = {"url": url, **kwargs}
            return QuoteResponse()

    monkeypatch.setattr(a_share, "_EM_DELAY_HOST_INDEX", 0)
    monkeypatch.setattr(a_share.httpx, "AsyncClient", QuoteClient)

    result = asyncio.run(_provider().sector_crowding_snapshot())

    assert [row["code"] for row in result] == ["801102", "801101", "801083", "801081"]
    assert all(row["amount_yuan"] == Decimal("123456789000") for row in result)
    assert all(row["turnover_pct"] == Decimal("3.52") for row in result)
    assert all(row["observed_at"].isoformat() == "2026-09-23T07:39:31+00:00" for row in result)
    assert QuoteClient.request is not None
    assert QuoteClient.request["url"] == "https://push2delay2.eastmoney.com/api/qt/stock/get"


def test_free_provider_exposes_sector_crowding_adapter() -> None:
    provider = FreeResearchProvider()
    expected = [{"code": "801102", "amount_yuan": Decimal("1")}]

    async def collect():
        return expected

    provider._a_share.sector_crowding_snapshot = collect

    assert asyncio.run(provider.sector_crowding_snapshot()) == expected


def test_index_snapshots_preserve_partial_success(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider()

    async def fake_snapshot(code: str, name: str, symbol: str) -> AShareIndexSnapshot:
        if code != "000001":
            raise RuntimeError("provider unavailable")
        return AShareIndexSnapshot(code=code, name=name, source_symbol=symbol)

    monkeypatch.setattr(provider, "_index_snapshot", fake_snapshot)

    result = asyncio.run(provider.index_snapshots())

    assert [item.code for item in result] == ["000001"]


def test_tencent_hk_quote_uses_native_amount_and_hk_timestamp(monkeypatch):
    values = [""] * 78
    for index, value in {
        1: "腾讯控股",
        3: "438.400",
        4: "442.800",
        30: "2026/09/07 16:08:17",
        37: "4591565063.448",
        38: "0",
        39: "16.03",
        45: "39908.2542",
        46: "TENCENT",
    }.items():
        values[index] = value

    class QuoteResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self):
            return ('v_hk00700="' + "~".join(values) + '";').encode("gbk")

    class Opener:
        def open(self, *_args, **_kwargs):
            return QuoteResponse()

    monkeypatch.setattr(a_share, "build_opener", lambda *_: Opener())
    quote = asyncio.run(_provider().tracked_stock_spot(["00700"]))[0]
    assert quote.turnover_yuan == Decimal("4591565063.448")
    assert quote.currency == "HKD"
    assert quote.observed_at.isoformat() == "2026-09-07T16:08:17+08:00"
    assert quote.turnover_pct is None and quote.pb is None


def test_short_term_emotion_preserves_pool_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider()

    async def fake_pool(
        endpoint: str, _trade_date: str, _sort: str
    ) -> tuple[date, list[dict[str, Any]]]:
        pools = {
            "getTopicZTPool": [
                {"c": "1", "n": "二板股", "lbc": 2, "amount": "300"},
                {"c": "2", "n": "首板股", "lbc": 1, "amount": "100"},
            ],
            "getTopicZBPool": [{"c": "3"}],
            "getTopicDTPool": [{"c": "4"}],
            "getYesterdayZTPool": [{"c": "5"}, {"c": "6"}],
        }
        return date(2026, 9, 24), pools[endpoint]

    monkeypatch.setattr(provider, "_limit_pool", fake_pool)

    result = asyncio.run(provider.short_term_emotion())

    assert result.limit_up_count == 2
    assert result.broken_board_count == 1
    assert result.limit_down_count == 1
    assert result.highest_board_count == 2
    assert result.consecutive_board_count == 1
    assert result.leaders[0].security_code == "000001"
    assert result.leaders[0].turnover_yuan == Decimal("300")
    assert next(item.stock_count for item in result.ladder if item.board_count == "2板") == 1
    assert result.trade_date == date(2026, 9, 24)


def test_limit_pool_preserves_eastmoney_http_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(a_share.httpx, "AsyncClient", _Client)
    provider = _provider()

    result = asyncio.run(provider._limit_pool("getTopicZTPool", "20260731", "fbt:asc"))

    assert result == (date(2026, 7, 31), [{"c": "600000"}])
    assert _Client.init_kwargs == {
        "timeout": 7.5,
        "trust_env": False,
        "verify": a_share._HTTP_SSL_CONTEXT,
    }
    assert a_share._HTTP_SSL_CONTEXT.verify_mode == ssl.CERT_REQUIRED
    assert a_share._HTTP_SSL_CONTEXT.check_hostname is True
    assert _Client.request is not None
    assert _Client.request["url"] == "https://push2ex.eastmoney.com/getTopicZTPool"
    assert _Client.request["params"] == {
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "dpt": "wz.ztzt",
        "Pageindex": 0,
        "pagesize": 10000,
        "sort": "fbt:asc",
        "date": "20260731",
    }
    assert _Client.request["headers"] == {
        "User-Agent": "research-test",
        "Referer": "https://quote.eastmoney.com/",
    }
