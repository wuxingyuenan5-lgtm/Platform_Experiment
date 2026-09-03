from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.research_data_schemas import ResearchApiModel
from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError

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
    spark_90d: list[Decimal] = Field(default_factory=list)


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
            document = read_local_json(f"public/v1/{market_id}/market-detail.json")
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
