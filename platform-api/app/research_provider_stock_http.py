from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from app.research_provider_errors import ResearchProviderError
from app.research_provider_normalization import as_decimal as _decimal

TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="


class StockHttpResearchProvider:
    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent

    async def stock_quote(self, code: str) -> dict[str, Any]:
        prefix = (
            "sh"
            if code.startswith(("6", "9", "5"))
            else ("bj" if code.startswith("8") else "sz")
        )
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                TENCENT_QUOTE_URL + prefix + code,
                headers={"User-Agent": self._user_agent},
            )
            response.raise_for_status()
        text = response.content.decode("gbk", errors="ignore")
        if '"' not in text:
            raise ResearchProviderError("tencent_quote_empty")
        values = text.split('"', 2)[1].split("~")
        if len(values) < 53:
            raise ResearchProviderError("tencent_quote_malformed")

        def number(index: int) -> Decimal | None:
            return _decimal(values[index] if index < len(values) else None)

        return {
            "name": values[1],
            "code": code,
            "price": number(3),
            "lastClose": number(4),
            "open": number(5),
            "changeAmount": number(31),
            "changePct": number(32),
            "high": number(33),
            "low": number(34),
            "turnoverYuan": (
                number(37) * Decimal("10000") if number(37) is not None else None
            ),
            "turnoverPct": number(38),
            "peTtm": number(39),
            "amplitudePct": number(43),
            "marketCapYuan": (
                number(44) * Decimal("100000000") if number(44) is not None else None
            ),
            "floatMarketCapYuan": (
                number(45) * Decimal("100000000") if number(45) is not None else None
            ),
            "pb": number(46),
            "limitUp": number(47),
            "limitDown": number(48),
            "volumeRatio": number(49),
            "peStatic": number(52),
        }

    async def stock_reports(self, code: str, limit: int = 30) -> list[dict[str, Any]]:
        params = {
            "industryCode": "*",
            "pageSize": str(limit),
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": "2000-01-01",
            "endTime": "2035-01-01",
            "pageNo": "1",
            "qType": "0",
            "code": code,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                "https://reportapi.eastmoney.com/report/list",
                params=params,
                headers={
                    "User-Agent": self._user_agent,
                    "Referer": "https://data.eastmoney.com/",
                },
            )
            response.raise_for_status()
            rows = response.json().get("data") or []
        return [
            {
                "title": row.get("title"),
                "organization": row.get("orgSName") or row.get("orgName"),
                "author": row.get("researcher"),
                "rating": row.get("emRatingName") or row.get("rating"),
                "publishedAt": row.get("publishDate"),
                "pdfUrl": (
                    f"https://pdf.dfcfw.com/pdf/H3_{row.get('infoCode')}_1.pdf"
                    if row.get("infoCode")
                    else None
                ),
            }
            for row in rows[:limit]
        ]

    async def stock_announcements(self, code: str, limit: int = 20) -> list[dict[str, Any]]:
        params = {
            "sr": -1,
            "page_size": limit,
            "page_index": 1,
            "ann_type": "A",
            "client_source": "web",
            "stock_list": code,
            "f_node": 0,
            "s_node": 0,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                "https://np-anotice-stock.eastmoney.com/api/security/ann",
                params=params,
                headers={"User-Agent": self._user_agent},
            )
            response.raise_for_status()
            rows = ((response.json().get("data") or {}).get("list") or [])
        output = []
        for row in rows:
            columns = [
                item.get("column_name")
                for item in row.get("columns") or []
                if item.get("column_name")
            ]
            article_code = row.get("art_code")
            output.append(
                {
                    "date": str(row.get("notice_date") or "")[:10],
                    "title": row.get("title"),
                    "type": columns[0] if columns else None,
                    "url": (
                        f"https://data.eastmoney.com/notices/detail/{code}/{article_code}.html"
                        if article_code
                        else None
                    ),
                }
            )
        return output

    async def stock_fund_flow(self, code: str) -> dict[str, Any]:
        market_code = 1 if code.startswith("6") else 0
        params = {
            "secid": f"{market_code}.{code}",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "lmt": "120",
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get",
                params=params,
                headers={
                    "User-Agent": self._user_agent,
                    "Referer": "https://quote.eastmoney.com/",
                },
            )
            response.raise_for_status()
            lines = (response.json().get("data") or {}).get("klines") or []
        rows = []
        for line in lines:
            parts = str(line).split(",")
            if len(parts) < 6:
                continue
            rows.append(
                {
                    "date": parts[0],
                    "mainNet": _decimal(parts[1]) or Decimal("0"),
                    "smallNet": _decimal(parts[2]) or Decimal("0"),
                    "mediumNet": _decimal(parts[3]) or Decimal("0"),
                    "largeNet": _decimal(parts[4]) or Decimal("0"),
                    "superNet": _decimal(parts[5]) or Decimal("0"),
                }
            )
        return {
            "history": rows,
            "mainNet20d": sum(
                (item["mainNet"] for item in rows[-20:]),
                Decimal("0"),
            ),
        }

    async def stock_investor_qa(self, code: str, limit: int = 30) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            lookup = await client.post(
                "https://irm.cninfo.com.cn/newircs/index/queryKeyboardInfo",
                data={"keyWord": code},
                headers={"User-Agent": self._user_agent},
            )
            lookup.raise_for_status()
            matches = lookup.json().get("data") or []
            if not matches:
                return []
            org_id = matches[0].get("secid")
            response = await client.post(
                "https://irm.cninfo.com.cn/newircs/company/question",
                params={
                    "_t": 1,
                    "stockcode": code,
                    "orgId": org_id,
                    "pageSize": limit,
                    "pageNum": 1,
                    "keyWord": "",
                    "startDay": "",
                    "endDay": "",
                },
                headers={"User-Agent": self._user_agent},
            )
            response.raise_for_status()
            rows = response.json().get("rows") or []
        output = []
        for row in rows:
            timestamp = row.get("pubDate")
            asked_at = None
            if isinstance(timestamp, (int, float)):
                asked_at = datetime.fromtimestamp(timestamp / 1000, tz=UTC).isoformat()
            output.append(
                {
                    "company": row.get("companyShortName"),
                    "question": row.get("mainContent"),
                    "answer": row.get("attachedContent"),
                    "answerer": row.get("attachedAuthor"),
                    "askedAt": asked_at,
                }
            )
        return output
