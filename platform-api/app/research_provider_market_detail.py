from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from pydantic import Field, ValidationError, field_validator

from app.research_data_schemas import ResearchApiModel
from app.research_equity_catalog import US_EXTRA_SYMBOLS
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
    signals: dict[str, str | None] = Field(default_factory=dict)
    sample_size: int | None = None
    expected_sample_size: int | None = None
    currency: str | None = None
    price_kind: Literal["intraday", "close", "observation"] = "observation"
    history: list[dict[str, str]] = Field(default_factory=list)


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
        self._snapshot_revisions: dict[str, tuple] = {}
        self._snapshot_locks: dict[str, asyncio.Lock] = {}

    def _read_snapshot(self, market_id: str) -> MarketDetailResponse:
        from app.config import get_settings
        from app.research_a_share_repository import read_dataset, read_dataset_metadata

        dataset = f"market_detail_{market_id}"
        metadata = read_dataset_metadata(dataset)
        if metadata is None:
            self._snapshot_revisions.pop(market_id, None)
            self._last_known_good.pop(market_id, None)
            return MarketDetailResponse(market_id=market_id, status="no_data")
        revision = (str(get_settings().database_path), *metadata.values())
        contract = self._last_known_good.get(market_id)
        if contract is None or self._snapshot_revisions.get(market_id) != revision:
            document = read_dataset(dataset)
            if document is None:
                return MarketDetailResponse(market_id=market_id, status="no_data")
            try:
                contract = MarketDetailResponse.model_validate(document)
            except ValidationError as exc:
                raise ResearchProviderError("market_detail_invalid_snapshot") from exc
            if contract.market_id != market_id:
                raise ResearchProviderError("market_detail_schema_mismatch")
            self._last_known_good[market_id] = contract
            self._snapshot_revisions[market_id] = revision
        if contract.rows and (
            contract.retrieved_at is None
            or datetime.now(UTC) - contract.retrieved_at > timedelta(hours=1)
        ):
            contract.status = "stale"
            for row in contract.rows:
                if row.status not in {"no_data", "error"}:
                    row.status = "stale"
        return contract

    async def get(self, market_id: str) -> MarketDetailResponse:
        if market_id in MARKET_SYMBOLS:
            lock = self._snapshot_locks.setdefault(market_id, asyncio.Lock())
            async with lock:
                return await asyncio.to_thread(self._read_snapshot, market_id)
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
        yahoo_symbols = MARKET_SYMBOLS[market_id]
        semaphore = asyncio.Semaphore(6)
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=True) as client:

            async def fetch(row_id: str, symbol: str):
                async with semaphore:
                    if market_id == "gold" and symbol in {"AU0", "AG0", "LC0"}:
                        return await _fetch_sina_futures(client, row_id, symbol)
                    if market_id == "global" and row_id == "global-rsx":
                        from app.research_source_moex import fetch_imoex

                        return await fetch_imoex(client, self._user_agent)
                    return await self._fetch_yahoo_history(client, row_id, symbol)

            results = await asyncio.gather(
                *(fetch(row_id, symbol) for row_id, symbol in yahoo_symbols.items()),
                return_exceptions=True,
            )
        series: dict[str, list[tuple[str, Decimal]]] = {}
        timezones: dict[str, str] = {}
        quote_meta: dict[str, dict] = {}
        for result in results:
            if isinstance(result, BaseException):
                continue
            row_id, points, source_timezone, metadata = result
            timezones[row_id] = source_timezone
            quote_meta[row_id] = metadata
            if points:
                series[row_id] = points
        derived = (
            GOLD_DERIVED if market_id == "gold" else CRYPTO_DERIVED if market_id == "crypto" else {}
        )
        for row_id, (numerator, denominator) in derived.items():
            ratio = _ratio_series(series.get(numerator, []), series.get(denominator, []))
            if ratio:
                series[row_id] = ratio
                timezones[row_id] = timezones.get(numerator, "UTC")
        rows = [_market_row(row_id, points) for row_id, points in series.items() if points]
        for row in rows:
            row.timezone = timezones.get(row.id, "UTC")
            metadata = quote_meta.get(row.id, {})
            if market_id == "us" and row.name == row.id and metadata.get("name"):
                row.name = metadata["name"]
            row.currency = metadata.get("currency")
            row.price_kind = metadata.get("price_kind", "observation")
            row.as_of = metadata.get("as_of") or row.as_of
            if metadata.get("source"):
                row.source = metadata["source"]
                row.source_url = metadata["source_url"]
                row.name = metadata["name"]
                row.unit = metadata["unit"]
                row.quality_flags.extend(metadata.get("quality_flags", []))
            if row.price_kind == "intraday":
                row.quality_flags.append("unfinished_daily_bar")
            # Date-labelled returns must not include an unfinished session.
            today = datetime.now(ZoneInfo(row.timezone)).date().isoformat()
            row.history = (
                [
                    {"date": day, "value": str(value)}
                    for day, value in series[row.id]
                    if day < today or (day == today and row.price_kind == "close")
                ][-260:]
                if market_id == "us" or row.id in {"gold-gld-row", "crypto-btc-row", "global-rsx"}
                else []
            )
            row.symbol = metadata.get("symbol") or yahoo_symbols.get(row.id, row.id).replace(
                "%5E", "^"
            )
            if row.symbol.startswith("^"):
                row.unit = "index"
            if row.id in GOLD_DERIVED or row.id in CRYPTO_DERIVED:
                row.unit = "ratio"
            if row.id in FUTURES_LABELS:
                row.name = FUTURES_LABELS[row.id]
                row.quality_flags.append("continuous_futures_not_spot")
            if row.observation_date and date.fromisoformat(row.observation_date) < datetime.now(
                UTC
            ).date() - timedelta(days=7):
                row.status = "stale"
                row.quality_flags.append("old_source_observation")
        if market_id == "crypto":
            rows.extend(await asyncio.to_thread(_crypto_cap_rows))
        if market_id == "us":
            rows.extend(await asyncio.to_thread(_cboe_rows))
        rows.extend(_breadth_rows(market_id, series))
        if not rows:
            raise ResearchProviderError("market_detail_no_live_rows")
        now = datetime.now(UTC)
        return MarketDetailResponse(
            market_id=market_id,
            status="partial"
            if len(series) < len(yahoo_symbols) + len(derived)
            or (
                market_id == "us" and not {"us-dspx", "us-cor1m"}.issubset({row.id for row in rows})
            )
            or any(row.status != "ready" for row in rows)
            else "ready",
            as_of=max(row.observation_date or "" for row in rows),
            retrieved_at=now,
            rows=[row for row in rows if not row.id.endswith("-source")],
        )

    async def _fetch_yahoo_history(
        self, client: httpx.AsyncClient, row_id: str, symbol: str, *, full_history: bool = False
    ) -> tuple[str, list[tuple[str, Decimal]], str, dict]:
        response = await client.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params=(
                {
                    "period1": 0,
                    "period2": int(datetime.now(UTC).timestamp()),
                    "interval": "1d",
                    "events": "history",
                }
                if full_history
                else {"range": "2y", "interval": "1d", "events": "history"}
            ),
            headers={"User-Agent": self._user_agent},
        )
        response.raise_for_status()
        result = ((response.json().get("chart") or {}).get("result") or [None])[0] or {}
        timestamps = result.get("timestamp") or []
        closes = (((result.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
        meta = result.get("meta") or {}
        timezone = ZoneInfo(meta.get("exchangeTimezoneName") or "UTC")
        points: dict[str, Decimal] = {}
        for timestamp, close in zip(timestamps, closes, strict=False):
            if close is None:
                continue
            value = Decimal(str(close))
            if not value.is_finite():
                continue
            points[datetime.fromtimestamp(timestamp, tz=timezone).date().isoformat()] = value
        ordered = sorted(points.items())
        today = datetime.now(timezone).date().isoformat()
        latest_day = ordered[-1][0] if ordered else None
        regular_end = ((meta.get("currentTradingPeriod") or {}).get("regular") or {}).get("end")
        open_bar = latest_day == today and (
            meta.get("instrumentType") == "CRYPTOCURRENCY"
            or regular_end is None
            or datetime.now(UTC).timestamp() < regular_end
        )
        quote_time = meta.get("regularMarketTime")
        as_of = datetime.fromtimestamp(quote_time, tz=timezone).isoformat() if quote_time else None
        if as_of and as_of[:10] != latest_day:
            as_of = None
        return (
            row_id,
            ordered,
            timezone.key,
            {
                "currency": meta.get("currency"),
                "name": meta.get("longName") or meta.get("shortName"),
                "as_of": as_of,
                "price_kind": "intraday" if open_bar else "close",
            },
        )


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

GOLD_YAHOO_SYMBOLS.update(
    {
        "gold-au1": "AU0",
        "gold-ag1": "AG0",
        "gold-ltc1": "LC0",
        "gold-zijin": "601899.SS",
        "gold-luoyang": "603993.SS",
        "gold-tongling": "000630.SZ",
        "gold-spy-source": "SPY",
    }
)
GOLD_DERIVED = {
    "gold-ratio-xaucopper": ("gold-xau-row", "gold-copper-row"),
    "gold-ratio-xauoil": ("gold-xau-row", "gold-wti-row"),
    "gold-ratio-xauspy": ("gold-xau-row", "gold-spy-source"),
    "gold-ratio-gdxxau": ("gold-gdx-row", "gold-xau-row"),
    "gold-ratio-row": ("gold-xau-row", "gold-slv-row"),
}

FUTURES_LABELS = {
    "gold-xau-row": "黄金期货（连续合约）",
    "gold-slv-row": "白银期货（连续合约）",
    "gold-copper-row": "铜期货（连续合约）",
    "gold-plat-row": "铂金期货（连续合约）",
    "gold-pall-row": "钯金期货（连续合约）",
    "gold-wti-row": "WTI 期货（连续合约）",
    "gold-brent-row": "布伦特期货（连续合约）",
    "gold-gas-row": "天然气期货（连续合约）",
}

CRYPTO_YAHOO_SYMBOLS = {
    "crypto-btc-row": "BTC-USD",
    "crypto-ibit-row": "IBIT",
    "crypto-eth-row": "ETH-USD",
    "crypto-sol-row": "SOL-USD",
    "crypto-bnb-row": "BNB-USD",
    "crypto-xrp-row": "XRP-USD",
    "crypto-doge-row": "DOGE-USD",
    "crypto-hype-row": "HYPE32196-USD",
    "crypto-mstr-row": "MSTR",
    "crypto-crcl-row": "CRCL",
    "crypto-coin-row": "COIN",
    "crypto-bmnr-row": "BMNR",
    "crypto-hood-row": "HOOD",
    "crypto-usdc-row": "USDC-USD",
}

CRYPTO_YAHOO_SYMBOLS.update(
    {
        f"crypto-{coin.lower()}usd": f"{coin}-USD"
        for coin in ["AAVE", "UNI", "HUMA", "ONDO", "PLUME", "PEPE", "SUI", "USDT"]
    }
)
CRYPTO_YAHOO_SYMBOLS.update(
    {
        "crypto-uniusd": "UNI7083-USD",
        "crypto-pepeusd": "PEPE24478-USD",
        "crypto-suiusd": "SUI20947-USD",
    }
)
CRYPTO_YAHOO_SYMBOLS.update({"crypto-xau-source": "GC=F", "crypto-spy-source": "SPY"})
CRYPTO_DERIVED = {
    "crypto-ratio-mstrbtc": ("crypto-mstr-row", "crypto-btc-row"),
    "crypto-ratio-crclbtc": ("crypto-crcl-row", "crypto-btc-row"),
    "crypto-ratio-coinbtc": ("crypto-coin-row", "crypto-btc-row"),
    "crypto-ratio-ethbtc": ("crypto-eth-row", "crypto-btc-row"),
    "crypto-ratio-btcxau": ("crypto-btc-row", "crypto-xau-source"),
    "crypto-ratio-btcspy": ("crypto-btc-row", "crypto-spy-source"),
    "crypto-ratio-ethsol": ("crypto-eth-row", "crypto-sol-row"),
}


US_YAHOO_SYMBOLS = {
    f"us-{symbol.lower()}": symbol
    for symbol in (
        "SPY DIA IWM MDY MAGS COST JNK MOAT VNQ XLB XLC XLE XLF XLI XLK XLP XLRE XLU XLV "
        "XLY SOXX ITA SCHD IBB ARKK BOTZ CLOU AAPL NVDA TSLA AMZN GOOGL META MSFT PLTR "
        "SNDK AMD BAC MU TSM QQQ GDX"
    ).split()
}
US_YAHOO_SYMBOLS.update({"us-ndx": "^NDX", "us-dji": "^DJI", "us-vix": "^VIX", "us-move": "^MOVE"})
for _symbol in US_EXTRA_SYMBOLS:
    if _symbol not in US_YAHOO_SYMBOLS.values():
        US_YAHOO_SYMBOLS[f"us-{_symbol.lower().lstrip('^')}"] = _symbol
GLOBAL_YAHOO_SYMBOLS = {
    f"global-{symbol.lower()}": symbol
    for symbol in (
        "EWA EWC EWQ EWG EWH EWI EWJ EWN EWS EWP EWL EWU ARGT EWZ ECH MCHI INDA EIDO "
        "EWM EWW EPHE EPOL EZA EWY EWT THD TUR VNM EFA EEM IEMG VEA VWO VIGI AIA"
    ).split()
}
MARKET_SYMBOLS = {
    "gold": GOLD_YAHOO_SYMBOLS,
    "crypto": CRYPTO_YAHOO_SYMBOLS,
    "us": US_YAHOO_SYMBOLS,
    # Retain the catalogue identity for saved user layouts; the instrument is IMOEX.
    "global": {**GLOBAL_YAHOO_SYMBOLS, "global-rsx": "IMOEX"},
}

# Fixed research pools; never presented as whole-market or S&P 500 breadth.
BREADTH_POOLS = {
    "gold": tuple(FUTURES_LABELS),
    "crypto": tuple(
        f"crypto-{symbol}-row" for symbol in ("btc", "eth", "sol", "bnb", "xrp", "doge", "hype")
    ),
}


def _cboe_rows() -> list[MarketDetailRow]:
    rows = []
    for symbol in ("DSPX", "COR1M"):
        try:
            document = read_local_json(f"public/v1/macro/series/{symbol.lower()}.json")
            if document.get("seriesId") != symbol.lower():
                raise ValueError("Cboe series identity mismatch")
            points = [
                (item["date"], Decimal(str(item["value"])))
                for item in document["observations"]
                if item["value"] is not None
            ]
            if not points or any(not value.is_finite() for _, value in points):
                raise ValueError("invalid Cboe values")
            if [day for day, _ in points] != sorted({day for day, _ in points}):
                raise ValueError("unordered or duplicate Cboe dates")
            row = _market_row(f"us-{symbol.lower()}", points)
            row.symbol, row.name, row.unit = symbol, f"Cboe {symbol}", "index"
            row.source, row.source_url = document["source"], document["sourceUrl"]
            row.timezone, row.frequency = document["timezone"], document["frequency"]
            row.status = document["status"]
            row.quality_flags = list(document.get("qualityFlags", []))
            retrieved = datetime.fromisoformat(document["retrievedAt"].replace("Z", "+00:00"))
            if retrieved.tzinfo is None:
                raise ValueError("Cboe retrieval timestamp lacks timezone")
            if datetime.now(UTC) - retrieved > timedelta(days=1) or date.fromisoformat(
                points[-1][0]
            ) < datetime.now(UTC).date() - timedelta(days=7):
                row.status = "stale"
                row.quality_flags.append("stale_source_artifact")
            rows.append(row)
        except (ResearchProviderError, ValueError, KeyError, TypeError, OSError):
            # The refresh layer preserves this symbol's last good row as stale.
            continue
    return rows


def _breadth_rows(
    market_id: str, series: dict[str, list[tuple[str, Decimal]]]
) -> list[MarketDetailRow]:
    pool = BREADTH_POOLS.get(market_id, ())
    timezone_name = "UTC" if market_id == "crypto" else "America/New_York"
    today = datetime.now(ZoneInfo(timezone_name)).date().isoformat()
    # A day must have ended in the source timezone. Do not mix an open daily
    # bar into participation while the research table still shows live quotes.
    available = [[point for point in series.get(key, []) if point[0] < today] for key in pool]
    available = [points for points in available if points]
    if not available:
        return []
    observed = max(points[-1][0] for points in available)
    rows = []
    for window in (20, 50, 200):
        eligible = [
            points for points in available if points[-1][0] == observed and len(points) >= window
        ]
        above = sum(
            points[-1][1] > sum((value for _, value in points[-window:]), Decimal(0)) / window
            for points in eligible
        )
        value = Decimal(above) * 100 / len(eligible) if eligible else None
        status = "ready" if len(eligible) == len(pool) else "partial" if eligible else "no_data"
        if eligible and date.fromisoformat(observed) < datetime.now(UTC).date() - timedelta(days=7):
            status = "stale"
        rows.append(
            MarketDetailRow(
                id=f"{market_id}-b{window}",
                name=f"{window}日参与度",
                symbol=f"BREADTH{window}",
                status=status,
                unit="percent",
                change_unit="absolute",
                frequency="daily",
                timezone=timezone_name,
                observation_date=observed,
                as_of=observed,
                source="Yahoo Finance / Platform research pool",
                source_url="https://finance.yahoo.com/",
                methodology_version="fixed-pool-same-date-sma-v1",
                close=value,
                sample_size=len(eligible),
                expected_sample_size=len(pool),
                quality_flags=[
                    "fixed_pool:" + ",".join(pool),
                    "strictly_above_sma",
                    "same_observation_date_only",
                    "completed_source_calendar_dates_only",
                ]
                + (["incomplete_sample"] if len(eligible) != len(pool) else []),
            )
        )
    return rows


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
    parsed_points = [(date.fromisoformat(point_date), value) for point_date, value in points]
    latest_day = parsed_points[-1][0]
    trailing_year = [
        value
        for point_date, value in parsed_points
        if point_date >= latest_day - timedelta(days=366)
    ]
    high = max(trailing_year) if parsed_points[0][0] <= latest_day - timedelta(days=365) else None
    quarter_month = ((latest_day.month - 1) // 3) * 3 + 1
    averages = {
        days: sum((value for _, value in points[-days:]), Decimal(0)) / days
        if len(points) >= days
        else None
        for days in (10, 20, 50, 200)
    }

    def direction(left: Decimal | None, right: Decimal | None) -> str | None:
        if left is None or right is None:
            return None
        return "▲" if left > right else "▼" if left < right else "—"

    signals = {f"d{days}": direction(latest, average) for days, average in averages.items()}
    signals.update(
        {
            "x2050": direction(averages[20], averages[50]),
            "x50200": direction(averages[50], averages[200]),
        }
    )
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
        methodology_version="market-detail-observation-v3",
        quality_flags=["price_return_excludes_distributions"],
        close=latest,
        change_1d=_change_from_previous(parsed_points),
        change_1w=_change_from_cutoff(parsed_points, latest_day - timedelta(days=7)),
        change_1m=_change_from_cutoff(parsed_points, latest_day - timedelta(days=30)),
        change_qtd=_change_from_period_start(
            parsed_points, date(latest_day.year, quarter_month, 1)
        ),
        change_ytd=_change_from_period_start(parsed_points, date(latest_day.year, 1, 1)),
        change_1y=_change_from_cutoff(parsed_points, latest_day - timedelta(days=365)),
        high_52w=high,
        distance_52w_high=(latest / high - 1) * Decimal("100") if high else None,
        spark_30d=[value for _, value in points[-30:]],
        spark_90d=[value for _, value in points[-90:]],
        signals=signals,
    )


def _percent_change(latest: Decimal, baseline: Decimal | None) -> Decimal | None:
    if baseline is None or baseline == 0:
        return None
    return (latest / baseline - 1) * Decimal("100")


def _change_from_previous(points: list[tuple[date, Decimal]]) -> Decimal | None:
    if len(points) < 2:
        return None
    return _percent_change(points[-1][1], points[-2][1])


def _change_from_cutoff(points: list[tuple[date, Decimal]], cutoff: date) -> Decimal | None:
    baseline = next((value for point_date, value in reversed(points) if point_date <= cutoff), None)
    return _percent_change(points[-1][1], baseline)


def _change_from_period_start(
    points: list[tuple[date, Decimal]], period_start: date
) -> Decimal | None:
    baseline = next(
        (value for point_date, value in reversed(points) if point_date < period_start), None
    )
    return _percent_change(points[-1][1], baseline)


def _crypto_cap_rows():
    """CoinGecko public global snapshot; preserve native update time and collected history."""
    import requests

    from app.research_a_share_repository import read_dataset

    try:
        response = requests.get("https://api.coingecko.com/api/v3/global", timeout=25)
        response.raise_for_status()
        data = response.json()["data"]
        total = Decimal(str(data["total_market_cap"]["usd"]))
        shares = data["market_cap_percentage"]
        btc = Decimal(str(shares["btc"]))
        eth = Decimal(str(shares["eth"]))
        metrics = {
            "crypto-total": total,
            "crypto-total2": total * (100 - btc) / 100,
            "crypto-total3": total * (100 - btc - eth) / 100,
            "crypto-btcd": btc,
            "crypto-usdtd": Decimal(str(shares["usdt"])),
            "crypto-othersd": 100
            - sum(Decimal(str(v)) for v in sorted(shares.values(), reverse=True)[:10]),
        }
        timestamp = datetime.fromtimestamp(data["updated_at"], UTC)
        day = timestamp.date().isoformat()
        prior = {
            row["id"]: row for row in (read_dataset("market_detail_crypto") or {}).get("rows", [])
        }
        result = []
        for sid, value in metrics.items():
            history = {
                r["date"]: Decimal(r["value"]) for r in prior.get(sid, {}).get("history", [])
            }
            history[day] = value
            row = _market_row(sid, sorted(history.items()))
            row.source = "CoinGecko"
            row.source_url = "https://www.coingecko.com/en/global-charts"
            row.symbol = sid.removeprefix("crypto-").upper()
            row.currency = "USD" if "total" in sid else None
            row.unit = "price" if "total" in sid else "percent"
            row.price_kind = "intraday"
            row.as_of = timestamp.isoformat()
            row.history = [{"date": d, "value": str(v)} for d, v in sorted(history.items())][-260:]
            row.quality_flags = [
                "coingecko_coverage_not_tradingview_index",
                "history_since_first_collection",
            ]
            result.append(row)
        return result
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Public crypto capitalization refresh failed")
        return []


async def _fetch_sina_futures(client, row_id, symbol):
    import json

    url = f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_{symbol}=/InnerFuturesNewService.getDailyKLine"
    response = await client.get(
        url, params={"symbol": symbol}, headers={"User-Agent": "Mozilla/5.0"}
    )
    response.raise_for_status()
    text = response.text
    rows = json.loads(text[text.index("[") : text.rindex("]") + 1])
    points = sorted(
        {
            str(r["d"]): Decimal(str(r["c"]))
            for r in rows
            if r.get("c") is not None
            and str(r["d"]) <= datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
        }.items()
    )
    if not points or any(not v.is_finite() or v <= 0 for _, v in points):
        raise ValueError("invalid Sina futures history")
    name, unit, tv = {
        "AU0": ("沪金主力连续", "cny_per_gram", "AU1!"),
        "AG0": ("沪银主力连续", "cny_per_kg", "AG1!"),
        "LC0": ("碳酸锂主力连续", "cny_per_tonne", "LC1!"),
    }[symbol]
    return (
        row_id,
        points,
        "Asia/Shanghai",
        {
            "source": "Sina Finance",
            "source_url": str(response.url),
            "name": name,
            "unit": unit,
            "currency": "CNY",
            "symbol": tv,
            "price_kind": "close",
            "as_of": points[-1][0],
            "quality_flags": ["source_native_continuous_contract", "continuous_futures_not_spot"],
        },
    )
