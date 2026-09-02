from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, cast

import httpx
from pydantic import Field, field_validator

from app.research_data_schemas import ResearchApiModel
from app.research_provider_errors import ResearchProviderError

PLATFORM_DATA_MARKET_DETAIL_URL = (
    "https://raw.githubusercontent.com/wuxingyuenan5-lgtm/platform-data/"
    "main/public/v1/{market_id}/market-detail.json"
)
MarketDetailStatus = Literal["ready", "partial", "degraded", "stale", "no_data", "error"]


class MarketDetailRow(ResearchApiModel):
    id: str
    name: str
    symbol: str
    status: MarketDetailStatus
    unit: str
    change_unit: Literal["percent", "basis_points", "absolute"]
    frequency: str
    timezone: str
    observation_date: str | None = None
    as_of: str | None = None
    source: str
    source_url: str | None = None
    methodology_version: str
    quality_flags: list[str] = Field(default_factory=list)
    close: Decimal | None = None
    change_1d: Decimal | None = None
    change_1w: Decimal | None = None
    change_1m: Decimal | None = None
    change_qtd: Decimal | None = None
    change_ytd: Decimal | None = None
    change_1y: Decimal | None = None
    high_52w: Decimal | None = None
    distance_52w_high: Decimal | None = None
    spark_30d: list[Decimal] = Field(default_factory=list)


class MarketDetailResponse(ResearchApiModel):
    schema_version: Literal["1.0"] = "1.0"
    market_id: str
    status: MarketDetailStatus
    as_of: str | None = None
    retrieved_at: datetime | None = None
    rows: list[MarketDetailRow] = Field(default_factory=list)

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("market detail timestamps must include a timezone")
        return value


class MarketDetailProvider:
    """Read versioned market-detail artifacts without inventing missing values."""

    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._last_known_good: dict[str, MarketDetailResponse] = {}

    async def get(self, market_id: str) -> MarketDetailResponse:
        if market_id != "macro":
            raise ResearchProviderError("market_detail_not_enabled")
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
                response = await client.get(
                    PLATFORM_DATA_MARKET_DETAIL_URL.format(market_id=market_id),
                    headers={"User-Agent": self._user_agent},
                )
                response.raise_for_status()
                payload = response.json()
            if not isinstance(payload, dict):
                raise ResearchProviderError("market_detail_invalid_payload")
            document = cast(dict[str, Any], payload)
            if document.get("schemaVersion") != "1.0" or document.get("marketId") != market_id:
                raise ResearchProviderError("market_detail_schema_mismatch")
            contract = MarketDetailResponse.model_validate(document)
            if contract.status == "ready" and not contract.rows:
                raise ResearchProviderError("market_detail_ready_without_rows")
            if contract.status in {"ready", "partial", "stale"} and contract.rows:
                self._last_known_good[market_id] = contract.model_copy(deep=True)
            return contract
        except Exception as exc:
            cached = self._last_known_good.get(market_id)
            if cached is not None:
                stale = cached.model_copy(deep=True)
                stale.status = "stale"
                return stale
            if isinstance(exc, ResearchProviderError):
                raise
            raise ResearchProviderError(f"market_detail_unavailable:{type(exc).__name__}") from exc
