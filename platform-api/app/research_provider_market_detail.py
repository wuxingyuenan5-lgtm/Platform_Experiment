from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

import httpx

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
        if market_id in {"gold", "crypto"}:
            return await self._get_live_market_detail(market_id)
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

    async def _get_live_market_detail(self, market_id: str) -> MarketDetailResponse:
        yahoo_symbols = GOLD_YAHOO_SYMBOLS if market_id == "gold" else CRYPTO_YAHOO_SYMBOLS
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=True) as client:
            results = await asyncio.gather(
                *(self._fetch_yahoo_history(client, row_id, symbol) for row_id, symbol in yahoo_symbols.items()),
                return_exceptions=True,
            )
        series: dict[str, list[tuple[str, Decimal]]] = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            row_id, points = result
            if points:
                series[row_id] = points
        derived = GOLD_DERIVED if market_id == "gold" else CRYPTO_DERIVED
        for row_id, (numerator, denominator) in derived.items():
            ratio = _ratio_series(series.get(numerator, []), series.get(denominator, []))
            if ratio:
                series[row_id] = ratio
        rows = [_market_row(row_id, points) for row_id, points in series.items() if points]
        now = datetime.now(UTC)
        return MarketDetailResponse(
            market_id=market_id,
            status="partial" if len(rows) < len(yahoo_symbols) + len(derived) else "ready",
            as_of=now.date().isoformat(),
            retrieved_at=now,
            rows=rows,
        )

    async def _fetch_yahoo_history(
        self, client: httpx.AsyncClient, row_id: str, symbol: str
    ) -> tuple[str, list[tuple[str, Decimal]]]:
        response = await client.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"range": "2y", "interval": "1d", "events": "history"},
            headers={"User-Agent": self._user_agent},
        )
        response.raise_for_status()
        result = ((response.json().get("chart") or {}).get("result") or [None])[0] or {}
        timestamps = result.get("timestamp") or []
        closes = (((result.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
        points = []
        for timestamp, close in zip(timestamps, closes, strict=False):
            if close is None:
                continue
            points.append((datetime.fromtimestamp(timestamp, tz=UTC).date().isoformat(), Decimal(str(close))))
        return row_id, points


GOLD_YAHOO_SYMBOLS = {
    "gold-xau-row": "GC=F",
    "gold-gld-row": "GLD",
    "gold-slv-row": "SI=F",
    "gold-gdx-row": "GDX",
    "gold-gdxj-row": "GDXJ",
    "gold-copper-row": "HG=F",
    "gold-plat-row": "PL=F",
    "gold-pall-row": "PA=F",
    "gold-bcom-row": "%5EBCOM",
    "gold-spgsci-row": "%5ESPGSCI",
    "gold-wti-row": "CL=F",
    "gold-brent-row": "BZ=F",
    "gold-gas-row": "NG=F",
}

GOLD_DERIVED = {
    "gold-ratio-row": ("gold-xau-row", "gold-slv-row"),
}

CRYPTO_YAHOO_SYMBOLS = {
    "crypto-btc-row": "BTC-USD",
    "crypto-ibit-row": "IBIT",
    "crypto-eth-row": "ETH-USD",
    "crypto-sol-row": "SOL-USD",
    "crypto-bnb-row": "BNB-USD",
    "crypto-xrp-row": "XRP-USD",
    "crypto-doge-row": "DOGE-USD",
    "crypto-mstr-row": "MSTR",
    "crypto-crcl-row": "CRCL",
    "crypto-coin-row": "COIN",
    "crypto-bmnr-row": "BMNR",
    "crypto-hood-row": "HOOD",
    "crypto-usdc-row": "USDC-USD",
}

CRYPTO_DERIVED: dict[str, tuple[str, str]] = {}


def _ratio_series(
    numerator: list[tuple[str, Decimal]], denominator: list[tuple[str, Decimal]]
) -> list[tuple[str, Decimal]]:
    denominator_by_date = dict(denominator)
    return [
        (date, value / denominator_by_date[date])
        for date, value in numerator
        if date in denominator_by_date and denominator_by_date[date] != 0
    ]


def _market_row(row_id: str, points: list[tuple[str, Decimal]]) -> MarketDetailRow:
    latest_date, latest = points[-1]
    trailing_year = [value for _, value in points[-366:]]
    high = max(trailing_year) if trailing_year else latest
    return MarketDetailRow(
        id=row_id,
        name=row_id,
        symbol=row_id,
        status="ready",
        unit="price",
        change_unit="percent",
        frequency="daily",
        timezone="UTC",
        observation_date=latest_date,
        as_of=latest_date,
        source="Yahoo Finance",
        source_url="https://finance.yahoo.com/",
        methodology_version="market-detail-live-v1",
        close=latest,
        distance_52w_high=(latest / high - 1) * Decimal("100") if high else None,
        spark_30d=[value for _, value in points[-30:]],
        spark_90d=[value for _, value in points[-90:]],
    )
