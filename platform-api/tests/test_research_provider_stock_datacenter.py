from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

import pytest

from app.research_provider_stock_datacenter import StockDataCenterResearchProvider

pytestmark = pytest.mark.unit


class _DataCenter:
    def __init__(self, responses: dict[tuple[str, int], list[dict[str, Any]]]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def rows(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(kwargs)
        key = (kwargs["report_name"], kwargs.get("page_size", 30))
        return self.responses.get(key, [])


def _provider(
    responses: dict[tuple[str, int], list[dict[str, Any]]],
) -> tuple[StockDataCenterResearchProvider, _DataCenter]:
    client = _DataCenter(responses)
    return StockDataCenterResearchProvider(data_center=client), client  # type: ignore[arg-type]


def test_margin_holders_and_dividends_preserve_report_contracts() -> None:
    provider, client = _provider(
        {
            ("RPTA_WEB_RZRQ_GGMX", 30): [
                {
                    "DATE": "2026-07-31T00:00:00",
                    "RZYE": 1,
                    "RZMRE": 2,
                    "RZCHE": 3,
                    "RQYE": 4,
                    "RQMCL": 5,
                    "RZRQYE": 6,
                }
            ],
            ("RPT_HOLDERNUMLATEST", 12): [
                {
                    "END_DATE": "2026-06-30T00:00:00",
                    "HOLDER_NUM": 100,
                    "HOLDER_NUM_RATIO": -2.5,
                    "AVG_FREE_SHARES": 2000,
                }
            ],
            ("RPT_SHAREBONUS_DET", 20): [
                {
                    "EX_DIVIDEND_DATE": "2026-05-10T00:00:00",
                    "PRETAX_BONUS_RMB": 1.2,
                    "TRANSFER_RATIO": 0,
                    "BONUS_RATIO": 0,
                    "ASSIGN_PROGRESS": "实施",
                }
            ],
        }
    )

    margin = asyncio.run(provider.stock_margin("600000"))
    holders = asyncio.run(provider.stock_holders("600000"))
    dividends = asyncio.run(provider.stock_dividends("600000"))

    assert margin[0] == {
        "date": "2026-07-31",
        "financingBalance": 1,
        "financingBuy": 2,
        "financingRepay": 3,
        "securitiesBalance": 4,
        "securitiesSell": 5,
        "totalBalance": 6,
    }
    assert holders[0]["date"] == "2026-06-30"
    assert dividends[0]["progress"] == "实施"
    assert client.calls == [
        {
            "report_name": "RPTA_WEB_RZRQ_GGMX",
            "filter_value": '(SCODE="600000")',
            "sort_columns": "DATE",
        },
        {
            "report_name": "RPT_HOLDERNUMLATEST",
            "filter_value": '(SECURITY_CODE="600000")',
            "page_size": 12,
            "sort_columns": "END_DATE",
        },
        {
            "report_name": "RPT_SHAREBONUS_DET",
            "filter_value": '(SECURITY_CODE="600000")',
            "page_size": 20,
            "sort_columns": "EX_DIVIDEND_DATE",
        },
    ]


def test_block_trade_preserves_decimal_premium_calculation() -> None:
    provider, client = _provider(
        {
            ("RPT_DATA_BLOCKTRADE", 20): [
                {
                    "TRADE_DATE": "2026-07-30T00:00:00",
                    "CLOSE_PRICE": "10",
                    "DEAL_PRICE": "11",
                    "DEAL_VOLUME": 100,
                    "DEAL_AMT": 1100,
                    "BUYER_NAME": "买方",
                    "SELLER_NAME": "卖方",
                }
            ]
        }
    )

    result = asyncio.run(provider.stock_block_trades("600000"))

    assert result[0]["price"] == Decimal("11")
    assert result[0]["close"] == Decimal("10")
    assert result[0]["premiumPct"] == Decimal("10.0")
    assert client.calls[0] == {
        "report_name": "RPT_DATA_BLOCKTRADE",
        "filter_value": '(SECURITY_CODE="600000")',
        "page_size": 20,
        "sort_columns": "TRADE_DATE",
    }


def test_dragon_tiger_preserves_detail_queries_and_seat_limits() -> None:
    provider, client = _provider(
        {
            ("RPT_DAILYBILLBOARD_DETAILSNEW", 50): [
                {
                    "TRADE_DATE": "2026-07-30T00:00:00",
                    "EXPLANATION": "日涨幅偏离值达7%",
                    "BILLBOARD_NET_AMT": 500,
                    "TURNOVERRATE": 8.8,
                }
            ],
            ("RPT_BILLBOARD_DAILYDETAILSBUY", 10): [
                {"OPERATEDEPT_NAME": f"买方{i}", "BUY": i, "SELL": 0, "NET": i}
                for i in range(7)
            ],
            ("RPT_BILLBOARD_DAILYDETAILSSELL", 10): [
                {"OPERATEDEPT_NAME": f"卖方{i}", "BUY": 0, "SELL": i, "NET": -i}
                for i in range(7)
            ],
        }
    )

    result = asyncio.run(provider.stock_dragon_tiger("600000"))

    assert result["records"][0]["date"] == "2026-07-30"
    assert len(result["seats"]["buy"]) == 5
    assert len(result["seats"]["sell"]) == 5
    assert client.calls[1] == {
        "report_name": "RPT_BILLBOARD_DAILYDETAILSBUY",
        "filter_value": "(TRADE_DATE='2026-07-30')(SECURITY_CODE=\"600000\")",
        "page_size": 10,
        "sort_columns": "BUY",
    }
    assert client.calls[2]["report_name"] == "RPT_BILLBOARD_DAILYDETAILSSELL"


def test_lockup_preserves_history_and_upcoming_queries() -> None:
    provider, client = _provider(
        {
            ("RPT_LIFT_STAGE", 15): [
                {
                    "FREE_DATE": "2026-01-01T00:00:00",
                    "FREE_SHARES_TYPE": "首发原股东限售股份",
                    "FREE_SHARES": 100,
                    "ABLE_FREE_SHARES": 90,
                    "FREE_RATIO": 1.5,
                }
            ],
            ("RPT_LIFT_STAGE", 20): [
                {
                    "FREE_DATE": "2026-08-20T00:00:00",
                    "FREE_SHARES_TYPE": "定向增发机构配售股份",
                    "FREE_SHARES": 200,
                    "ABLE_FREE_SHARES": 180,
                    "FREE_RATIO": 2.5,
                }
            ],
        }
    )

    result = asyncio.run(provider.stock_lockup("600000"))

    assert result["history"][0]["date"] == "2026-01-01"
    assert result["upcoming"][0]["date"] == "2026-08-20"
    assert len(client.calls) == 2
    assert client.calls[0] == {
        "report_name": "RPT_LIFT_STAGE",
        "filter_value": '(SECURITY_CODE="600000")',
        "page_size": 15,
        "sort_columns": "FREE_DATE",
    }
    assert client.calls[1]["report_name"] == "RPT_LIFT_STAGE"
    assert client.calls[1]["sort_types"] == "1"
    assert '(SECURITY_CODE="600000")' in client.calls[1]["filter_value"]
    assert "FREE_DATE>=" in client.calls[1]["filter_value"]
    assert "FREE_DATE<=" in client.calls[1]["filter_value"]
