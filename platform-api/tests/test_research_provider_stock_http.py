from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

import pytest

from app import research_provider_stock_http as stock_http
from app.research_provider_errors import ResearchProviderError
from app.research_provider_stock_http import StockHttpResearchProvider

pytestmark = pytest.mark.unit


class _Response:
    def __init__(
        self,
        *,
        payload: Any = None,
        content: bytes = b"",
        error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self.content = content
        self._error = error

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error

    def json(self) -> Any:
        return self._payload


class _Transport:
    def __init__(self, responses: list[_Response]) -> None:
        self.responses = responses
        self.init_calls: list[dict[str, Any]] = []
        self.requests: list[dict[str, Any]] = []

    def factory(self, **kwargs: Any) -> _Client:
        self.init_calls.append(kwargs)
        return _Client(self)


class _Client:
    def __init__(self, transport: _Transport) -> None:
        self._transport = transport

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> _Response:
        self._transport.requests.append({"method": "GET", "url": url, **kwargs})
        return self._transport.responses.pop(0)

    async def post(self, url: str, **kwargs: Any) -> _Response:
        self._transport.requests.append({"method": "POST", "url": url, **kwargs})
        return self._transport.responses.pop(0)


def _provider(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[_Response],
) -> tuple[StockHttpResearchProvider, _Transport]:
    transport = _Transport(responses)
    monkeypatch.setattr(stock_http.httpx, "AsyncClient", transport.factory)
    provider = StockHttpResearchProvider(timeout_seconds=9.5, user_agent="research-test")
    return provider, transport


def _quote_content() -> bytes:
    values = [""] * 53
    values[1] = "浦发银行"
    values[3] = "10.50"
    values[4] = "10.00"
    values[5] = "10.10"
    values[31] = "0.50"
    values[32] = "5.00"
    values[33] = "10.80"
    values[34] = "9.90"
    values[37] = "12.3"
    values[38] = "1.20"
    values[39] = "8.50"
    values[43] = "9.00"
    values[44] = "100.5"
    values[45] = "80.25"
    values[46] = "1.10"
    values[47] = "11.00"
    values[48] = "9.00"
    values[49] = "1.50"
    values[52] = "9.20"
    return f'v_sh600000="{"~".join(values)}";'.encode("gbk")


def test_tencent_quote_preserves_gbk_contract_and_unit_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, transport = _provider(
        monkeypatch,
        [_Response(content=_quote_content())],
    )

    result = asyncio.run(provider.stock_quote("600000"))

    assert result == {
        "name": "浦发银行",
        "code": "600000",
        "price": Decimal("10.50"),
        "lastClose": Decimal("10.00"),
        "open": Decimal("10.10"),
        "changeAmount": Decimal("0.50"),
        "changePct": Decimal("5.00"),
        "high": Decimal("10.80"),
        "low": Decimal("9.90"),
        "turnoverYuan": Decimal("123000.0"),
        "turnoverPct": Decimal("1.20"),
        "peTtm": Decimal("8.50"),
        "amplitudePct": Decimal("9.00"),
        "marketCapYuan": Decimal("10050000000.0"),
        "floatMarketCapYuan": Decimal("8025000000.00"),
        "pb": Decimal("1.10"),
        "limitUp": Decimal("11.00"),
        "limitDown": Decimal("9.00"),
        "volumeRatio": Decimal("1.50"),
        "peStatic": Decimal("9.20"),
    }
    assert transport.init_calls == [{"timeout": 9.5, "trust_env": False}]
    assert transport.requests == [
        {
            "method": "GET",
            "url": "https://qt.gtimg.cn/q=sh600000",
            "headers": {"User-Agent": "research-test"},
        }
    ]


def test_tencent_quote_preserves_empty_and_malformed_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, _ = _provider(monkeypatch, [_Response(content=b"empty")])
    with pytest.raises(ResearchProviderError, match="tencent_quote_empty"):
        asyncio.run(provider.stock_quote("600000"))

    provider, _ = _provider(monkeypatch, [_Response(content=b'v="too~short";')])
    with pytest.raises(ResearchProviderError, match="tencent_quote_malformed"):
        asyncio.run(provider.stock_quote("600000"))


def test_eastmoney_reports_preserve_query_mapping_and_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, transport = _provider(
        monkeypatch,
        [
            _Response(
                payload={
                    "data": [
                        {
                            "title": "研报一",
                            "orgSName": "机构简称",
                            "orgName": "机构全称",
                            "researcher": "分析师",
                            "emRatingName": "买入",
                            "publishDate": "2026-07-31",
                            "infoCode": "INFO1",
                        },
                        {"title": "研报二"},
                    ]
                }
            )
        ],
    )

    result = asyncio.run(provider.stock_reports("600000", limit=1))

    assert result == [
        {
            "title": "研报一",
            "organization": "机构简称",
            "author": "分析师",
            "rating": "买入",
            "publishedAt": "2026-07-31",
            "pdfUrl": "https://pdf.dfcfw.com/pdf/H3_INFO1_1.pdf",
        }
    ]
    assert transport.requests == [
        {
            "method": "GET",
            "url": "https://reportapi.eastmoney.com/report/list",
            "params": {
                "industryCode": "*",
                "pageSize": "1",
                "industry": "*",
                "rating": "*",
                "ratingChange": "*",
                "beginTime": "2000-01-01",
                "endTime": "2035-01-01",
                "pageNo": "1",
                "qType": "0",
                "code": "600000",
            },
            "headers": {
                "User-Agent": "research-test",
                "Referer": "https://data.eastmoney.com/",
            },
        }
    ]


def test_eastmoney_announcements_preserve_columns_and_detail_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, transport = _provider(
        monkeypatch,
        [
            _Response(
                payload={
                    "data": {
                        "list": [
                            {
                                "notice_date": "2026-07-30T00:00:00",
                                "title": "公告标题",
                                "columns": [
                                    {"column_name": "重大事项"},
                                    {"column_name": "其他"},
                                ],
                                "art_code": "AN001",
                            }
                        ]
                    }
                }
            )
        ],
    )

    result = asyncio.run(provider.stock_announcements("600000", limit=5))

    assert result == [
        {
            "date": "2026-07-30",
            "title": "公告标题",
            "type": "重大事项",
            "url": "https://data.eastmoney.com/notices/detail/600000/AN001.html",
        }
    ]
    assert transport.requests[0] == {
        "method": "GET",
        "url": "https://np-anotice-stock.eastmoney.com/api/security/ann",
        "params": {
            "sr": -1,
            "page_size": 5,
            "page_index": 1,
            "ann_type": "A",
            "client_source": "web",
            "stock_list": "600000",
            "f_node": 0,
            "s_node": 0,
        },
        "headers": {"User-Agent": "research-test"},
    }


def test_eastmoney_fund_flow_preserves_kline_mapping_and_20d_sum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, transport = _provider(
        monkeypatch,
        [
            _Response(
                payload={
                    "data": {
                        "klines": [
                            "2026-07-29,1,2,3,4,5",
                            "malformed",
                            "2026-07-30,10,20,30,40,50",
                        ]
                    }
                }
            )
        ],
    )

    result = asyncio.run(provider.stock_fund_flow("600000"))

    assert result == {
        "history": [
            {
                "date": "2026-07-29",
                "mainNet": Decimal("1"),
                "smallNet": Decimal("2"),
                "mediumNet": Decimal("3"),
                "largeNet": Decimal("4"),
                "superNet": Decimal("5"),
            },
            {
                "date": "2026-07-30",
                "mainNet": Decimal("10"),
                "smallNet": Decimal("20"),
                "mediumNet": Decimal("30"),
                "largeNet": Decimal("40"),
                "superNet": Decimal("50"),
            },
        ],
        "mainNet20d": Decimal("11"),
    }
    assert transport.requests[0] == {
        "method": "GET",
        "url": "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get",
        "params": {
            "secid": "1.600000",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "lmt": "120",
        },
        "headers": {
            "User-Agent": "research-test",
            "Referer": "https://quote.eastmoney.com/",
        },
    }


def test_cninfo_investor_qa_preserves_two_post_contract_and_utc_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, transport = _provider(
        monkeypatch,
        [
            _Response(payload={"data": [{"secid": "ORG001"}]}),
            _Response(
                payload={
                    "rows": [
                        {
                            "companyShortName": "浦发银行",
                            "mainContent": "问题",
                            "attachedContent": "回答",
                            "attachedAuthor": "董秘",
                            "pubDate": 0,
                        }
                    ]
                }
            ),
        ],
    )

    result = asyncio.run(provider.stock_investor_qa("600000", limit=7))

    assert result == [
        {
            "company": "浦发银行",
            "question": "问题",
            "answer": "回答",
            "answerer": "董秘",
            "askedAt": "1970-01-01T00:00:00+00:00",
        }
    ]
    assert transport.requests == [
        {
            "method": "POST",
            "url": "https://irm.cninfo.com.cn/newircs/index/queryKeyboardInfo",
            "data": {"keyWord": "600000"},
            "headers": {"User-Agent": "research-test"},
        },
        {
            "method": "POST",
            "url": "https://irm.cninfo.com.cn/newircs/company/question",
            "params": {
                "_t": 1,
                "stockcode": "600000",
                "orgId": "ORG001",
                "pageSize": 7,
                "pageNum": 1,
                "keyWord": "",
                "startDay": "",
                "endDay": "",
            },
            "headers": {"User-Agent": "research-test"},
        },
    ]
