from __future__ import annotations

from typing import Any

import httpx

EASTMONEY_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"


class EastmoneyDataCenterClient:
    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent

    async def rows(
        self,
        *,
        report_name: str,
        filter_value: str,
        page_size: int = 30,
        sort_columns: str = "",
        sort_types: str = "-1",
    ) -> list[dict[str, Any]]:
        params = {
            "reportName": report_name,
            "columns": "ALL",
            "filter": filter_value,
            "pageNumber": "1",
            "pageSize": str(page_size),
            "sortColumns": sort_columns,
            "sortTypes": sort_types,
            "source": "WEB",
            "client": "WEB",
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                EASTMONEY_DATACENTER_URL,
                params=params,
                headers={"User-Agent": self._user_agent},
            )
            response.raise_for_status()
            result = response.json().get("result") or {}
        return result.get("data") or []
