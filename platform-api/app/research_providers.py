from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.research_data_schemas import (
    AShareBreadthSnapshot,
    AShareIndexSnapshot,
    AShareTurnoverStock,
    MacroExpectationEvent,
    ShenwanMembership,
    ShortTermEmotionSnapshot,
)
from app.research_provider_a_share import AShareResearchProvider
from app.research_provider_datacenter import EastmoneyDataCenterClient
from app.research_provider_errors import ResearchProviderError
from app.research_provider_macro import MacroResearchProvider
from app.research_provider_stock_akshare import StockAkshareResearchProvider
from app.research_provider_stock_datacenter import StockDataCenterResearchProvider
from app.research_provider_stock_http import StockHttpResearchProvider

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/150.0 Safari/537.36"
)



def _akshare() -> Any:
    try:
        import akshare as ak
    except ImportError as exc:  # pragma: no cover - protected by dependency installation
        raise ResearchProviderError("akshare_dependency_missing") from exc
    return ak



class FreeResearchProvider:
    """Free-source adapters used only by the research domain.

    The provider normalizes third-party fields before they cross the Platform API boundary. It never
    supplies execution-authoritative quotes and never imports Venue or Broker SDKs.
    """

    def __init__(self, *, timeout_seconds: float = 20.0) -> None:
        self._timeout_seconds = timeout_seconds
        self._a_share = AShareResearchProvider(
            timeout_seconds=timeout_seconds,
            user_agent=USER_AGENT,
            akshare_loader=_akshare,
        )
        self._data_center = EastmoneyDataCenterClient(
            timeout_seconds=timeout_seconds,
            user_agent=USER_AGENT,
        )
        self._stock_akshare = StockAkshareResearchProvider(
            akshare_loader=_akshare,
        )
        self._stock_http = StockHttpResearchProvider(
            timeout_seconds=timeout_seconds,
            user_agent=USER_AGENT,
        )
        self._stock_data_center = StockDataCenterResearchProvider(
            data_center=self._data_center,
        )
        self._macro = MacroResearchProvider(
            timeout_seconds=timeout_seconds,
            user_agent=USER_AGENT,
        )

    async def a_share_spot(self) -> list[AShareTurnoverStock]:
        return await self._a_share.a_share_spot()

    async def market_activity(self) -> AShareBreadthSnapshot:
        return await self._a_share.market_activity()

    async def index_snapshots(self) -> list[AShareIndexSnapshot]:
        return await self._a_share.index_snapshots()



    async def shenwan_memberships(self) -> list[ShenwanMembership]:
        return await self._a_share.shenwan_memberships()

    async def short_term_emotion(self) -> ShortTermEmotionSnapshot:
        return await self._a_share.short_term_emotion()


    async def stock_quote(self, code: str) -> dict[str, Any]:
        return await self._stock_http.stock_quote(code)

    async def stock_financials(self, code: str) -> dict[str, Any]:
        return await self._stock_akshare.stock_financials(code)

    async def stock_forecast(
        self, code: str, price: Decimal | None
    ) -> dict[str, Any]:
        return await self._stock_akshare.stock_forecast(code, price)

    async def stock_valuation_percentile(self, code: str) -> dict[str, Any]:
        return await self._stock_akshare.stock_valuation_percentile(code)

    async def stock_news(
        self, code: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        return await self._stock_akshare.stock_news(code, limit=limit)

    async def stock_reports(
        self, code: str, limit: int = 30
    ) -> list[dict[str, Any]]:
        return await self._stock_http.stock_reports(code, limit=limit)

    async def stock_announcements(
        self, code: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        return await self._stock_http.stock_announcements(code, limit=limit)

    async def datacenter_rows(
        self,
        *,
        report_name: str,
        filter_value: str,
        page_size: int = 30,
        sort_columns: str = "",
        sort_types: str = "-1",
    ) -> list[dict[str, Any]]:
        return await self._data_center.rows(
            report_name=report_name,
            filter_value=filter_value,
            page_size=page_size,
            sort_columns=sort_columns,
            sort_types=sort_types,
        )

    async def stock_margin(self, code: str) -> list[dict[str, Any]]:
        return await self._stock_data_center.stock_margin(code)

    async def stock_block_trades(self, code: str) -> list[dict[str, Any]]:
        return await self._stock_data_center.stock_block_trades(code)

    async def stock_holders(self, code: str) -> list[dict[str, Any]]:
        return await self._stock_data_center.stock_holders(code)

    async def stock_dividends(self, code: str) -> list[dict[str, Any]]:
        return await self._stock_data_center.stock_dividends(code)

    async def stock_fund_flow(self, code: str) -> dict[str, Any]:
        return await self._stock_http.stock_fund_flow(code)

    async def stock_dragon_tiger(self, code: str) -> dict[str, Any]:
        return await self._stock_data_center.stock_dragon_tiger(code)

    async def stock_lockup(self, code: str) -> dict[str, Any]:
        return await self._stock_data_center.stock_lockup(code)

    async def stock_investor_qa(
        self, code: str, limit: int = 30
    ) -> list[dict[str, Any]]:
        return await self._stock_http.stock_investor_qa(code, limit=limit)

    async def macro_expectation_events(
        self, limit: int = 12
    ) -> list[MacroExpectationEvent]:
        return await self._macro.macro_expectation_events(limit=limit)
