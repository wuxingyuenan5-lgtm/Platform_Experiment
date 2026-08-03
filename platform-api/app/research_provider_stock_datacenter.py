from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

from app.research_provider_datacenter import EastmoneyDataCenterClient
from app.research_provider_normalization import as_decimal as _decimal
from app.research_provider_normalization import percentage_change as _pct_change


class StockDataCenterResearchProvider:
    def __init__(self, *, data_center: EastmoneyDataCenterClient) -> None:
        self._data_center = data_center

    async def stock_margin(self, code: str) -> list[dict[str, Any]]:
        rows = await self._data_center.rows(
            report_name="RPTA_WEB_RZRQ_GGMX",
            filter_value=f'(SCODE="{code}")',
            sort_columns="DATE",
        )
        return [
            {
                "date": str(row.get("DATE") or "")[:10],
                "financingBalance": row.get("RZYE"),
                "financingBuy": row.get("RZMRE"),
                "financingRepay": row.get("RZCHE"),
                "securitiesBalance": row.get("RQYE"),
                "securitiesSell": row.get("RQMCL"),
                "totalBalance": row.get("RZRQYE"),
            }
            for row in rows
        ]

    async def stock_block_trades(self, code: str) -> list[dict[str, Any]]:
        rows = await self._data_center.rows(
            report_name="RPT_DATA_BLOCKTRADE",
            filter_value=f'(SECURITY_CODE="{code}")',
            page_size=20,
            sort_columns="TRADE_DATE",
        )
        output = []
        for row in rows:
            close = _decimal(row.get("CLOSE_PRICE"))
            deal = _decimal(row.get("DEAL_PRICE"))
            output.append(
                {
                    "date": str(row.get("TRADE_DATE") or "")[:10],
                    "price": deal,
                    "close": close,
                    "premiumPct": _pct_change(deal, close),
                    "volume": row.get("DEAL_VOLUME"),
                    "amount": row.get("DEAL_AMT"),
                    "buyer": row.get("BUYER_NAME"),
                    "seller": row.get("SELLER_NAME"),
                }
            )
        return output

    async def stock_holders(self, code: str) -> list[dict[str, Any]]:
        rows = await self._data_center.rows(
            report_name="RPT_HOLDERNUMLATEST",
            filter_value=f'(SECURITY_CODE="{code}")',
            page_size=12,
            sort_columns="END_DATE",
        )
        return [
            {
                "date": str(row.get("END_DATE") or "")[:10],
                "holderCount": row.get("HOLDER_NUM"),
                "changePct": row.get("HOLDER_NUM_RATIO"),
                "averageFreeShares": row.get("AVG_FREE_SHARES"),
            }
            for row in rows
        ]

    async def stock_dividends(self, code: str) -> list[dict[str, Any]]:
        rows = await self._data_center.rows(
            report_name="RPT_SHAREBONUS_DET",
            filter_value=f'(SECURITY_CODE="{code}")',
            page_size=20,
            sort_columns="EX_DIVIDEND_DATE",
        )
        return [
            {
                "date": str(row.get("EX_DIVIDEND_DATE") or "")[:10],
                "pretaxBonusRmb": row.get("PRETAX_BONUS_RMB"),
                "transferRatio": row.get("TRANSFER_RATIO"),
                "bonusRatio": row.get("BONUS_RATIO"),
                "progress": row.get("ASSIGN_PROGRESS"),
            }
            for row in rows
        ]

    async def stock_dragon_tiger(self, code: str) -> dict[str, Any]:
        end = date.today()
        start = end - timedelta(days=45)
        rows = await self._data_center.rows(
            report_name="RPT_DAILYBILLBOARD_DETAILSNEW",
            filter_value=(
                f"(TRADE_DATE>='{start.isoformat()}')(TRADE_DATE<='{end.isoformat()}')"
                f'(SECURITY_CODE="{code}")'
            ),
            page_size=50,
            sort_columns="TRADE_DATE",
        )
        records = [
            {
                "date": str(row.get("TRADE_DATE") or "")[:10],
                "reason": row.get("EXPLANATION"),
                "netBuyYuan": row.get("BILLBOARD_NET_AMT"),
                "turnoverPct": row.get("TURNOVERRATE"),
            }
            for row in rows
        ]
        seats: dict[str, list[dict[str, Any]]] = {"buy": [], "sell": []}
        if records:
            latest = records[0]["date"]
            for side, report, sort_column in (
                ("buy", "RPT_BILLBOARD_DAILYDETAILSBUY", "BUY"),
                ("sell", "RPT_BILLBOARD_DAILYDETAILSSELL", "SELL"),
            ):
                details = await self._data_center.rows(
                    report_name=report,
                    filter_value=f"(TRADE_DATE='{latest}')(SECURITY_CODE=\"{code}\")",
                    page_size=10,
                    sort_columns=sort_column,
                )
                seats[side] = [
                    {
                        "name": row.get("OPERATEDEPT_NAME"),
                        "buyYuan": row.get("BUY"),
                        "sellYuan": row.get("SELL"),
                        "netYuan": row.get("NET"),
                    }
                    for row in details[:5]
                ]
        return {"records": records, "seats": seats}

    async def stock_lockup(self, code: str) -> dict[str, Any]:
        today = date.today()
        end = today + timedelta(days=90)
        history_rows, upcoming_rows = await asyncio.gather(
            self._data_center.rows(
                report_name="RPT_LIFT_STAGE",
                filter_value=f'(SECURITY_CODE="{code}")',
                page_size=15,
                sort_columns="FREE_DATE",
            ),
            self._data_center.rows(
                report_name="RPT_LIFT_STAGE",
                filter_value=(
                    f'(SECURITY_CODE="{code}")(FREE_DATE>=\'{today.isoformat()}\')'
                    f"(FREE_DATE<='{end.isoformat()}')"
                ),
                page_size=20,
                sort_columns="FREE_DATE",
                sort_types="1",
            ),
        )

        def normalize(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
            return [
                {
                    "date": str(row.get("FREE_DATE") or "")[:10],
                    "type": row.get("FREE_SHARES_TYPE"),
                    "shares": row.get("FREE_SHARES"),
                    "availableShares": row.get("ABLE_FREE_SHARES"),
                    "ratioPct": row.get("FREE_RATIO"),
                }
                for row in rows
            ]

        return {"history": normalize(history_rows), "upcoming": normalize(upcoming_rows)}
