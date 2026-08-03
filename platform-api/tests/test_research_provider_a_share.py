from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

import pytest

from app import research_provider_a_share as a_share
from app.research_data_schemas import AShareIndexSnapshot
from app.research_provider_a_share import AShareResearchProvider

pytestmark = pytest.mark.unit


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
        return {"data": {"pool": [{"c": "600000"}]}}


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
    result = asyncio.run(_provider().a_share_spot())

    assert len(result) == 1
    assert result[0].security_code == "000001"
    assert result[0].security_name == "测试股份"
    assert result[0].turnover_yuan == Decimal("12345")
    assert result[0].return_pct == Decimal("3.2")


def test_index_snapshots_preserve_partial_success(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider()

    async def fake_snapshot(code: str, name: str, symbol: str) -> AShareIndexSnapshot:
        if code != "000001":
            raise RuntimeError("provider unavailable")
        return AShareIndexSnapshot(code=code, name=name, source_symbol=symbol)

    monkeypatch.setattr(provider, "_index_snapshot", fake_snapshot)

    result = asyncio.run(provider.index_snapshots())

    assert [item.code for item in result] == ["000001"]


def test_short_term_emotion_preserves_pool_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider()

    async def fake_pool(endpoint: str, _trade_date: str, _sort: str) -> list[dict[str, Any]]:
        pools = {
            "getTopicZTPool": [
                {"c": "1", "n": "二板股", "lbc": 2, "amount": "300"},
                {"c": "2", "n": "首板股", "lbc": 1, "amount": "100"},
            ],
            "getTopicZBPool": [{"c": "3"}],
            "getTopicDTPool": [{"c": "4"}],
            "getYesterdayZTPool": [{"c": "5"}, {"c": "6"}],
        }
        return pools[endpoint]

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


def test_limit_pool_preserves_eastmoney_http_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(a_share.httpx, "AsyncClient", _Client)
    provider = _provider()

    result = asyncio.run(provider._limit_pool("getTopicZTPool", "20260731", "fbt:asc"))

    assert result == [{"c": "600000"}]
    assert _Client.init_kwargs == {"timeout": 7.5, "trust_env": False}
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
