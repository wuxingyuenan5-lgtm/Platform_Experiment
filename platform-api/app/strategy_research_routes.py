from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import Principal, require_permission
from app.config import get_settings
from app.strategy_research_ingest import LATEST, STATUS
from app.strategy_research_policy import scenario
from app.strategy_research_projection import (
    funding_basis_status,
    history_chart,
    price_coverage,
    projection_status,
    read_projection,
    second_statistics,
    spread_chart,
)
from app.strategy_research_repository import (
    cancel_experiment,
    capture_metadata,
    capture_status,
    enqueue_experiment,
    get_draft,
    get_experiment,
    read_rows,
    save_draft,
)
from app.strategy_research_responses import ResearchResponse
from app.strategy_research_schemas import DraftRequest, Experiment, Scenario
from app.strategy_research_series import distribution, time_ms

router = APIRouter(
    prefix=get_settings().api_prefix + "/research/strategies", tags=["strategy-research"]
)
Reader = Annotated[Principal, Depends(require_permission("research.read"))]
Writer = Annotated[Principal, Depends(require_permission("research.write"))]


FUNDING_RESOLUTION_MS = {"1h": 3_600_000, "8h": 28_800_000, "1d": 86_400_000}
FUNDING_SYMBOLS = {"BTC", "ETH", "SOL", "DOGE", "XRP", "XAUT", "CRCL", "MSTR"}
FUNDING_BASIS_SYMBOLS = ("XAUT", "BTC", "ETH", "CRCL", "MSTR")


def normalize_research_symbol(value: str, *, pair: str) -> str:
    symbol = value.strip().upper().removesuffix("USDT")
    if pair == "cross-gold":
        return "XAUT"
    if symbol not in FUNDING_SYMBOLS:
        raise HTTPException(422, "Unsupported research symbol")
    return symbol


def aggregate_funding_indications(rows, resolution_ms: int):
    """Return the last observed indication in each display bucket.

    The raw indication remains in the archive. This is only a read projection for
    the requested chart precision and never fills an unobserved bucket.
    """
    buckets = {}
    for row in rows:
        payload = row.get("payload", {})
        rate = payload.get("fundingRate")
        if rate in (None, ""):
            continue
        try:
            observed = time_ms(row["receivedAt"])
            Decimal(str(rate))
        except (KeyError, TypeError, ValueError):
            continue
        bucket = observed // resolution_ms * resolution_ms
        current = buckets.get(bucket)
        if current is None or observed >= current["observedMs"]:
            buckets[bucket] = {
                "observedMs": observed,
                "at": datetime.fromtimestamp(bucket / 1000, UTC).isoformat(),
                "rate": str(rate),
                "source": "bybit_funding_indication",
            }
    return [buckets[key] for key in sorted(buckets)]


def borrow_observations(rows, resolution_ms: int = 3_600_000):
    observations = []
    for row in rows:
        payload = row.get("payload", {})
        observed = row.get("observedAt") or row.get("receivedAt")
        if not observed:
            continue
        try:
            observed_ms = time_ms(observed)
        except (TypeError, ValueError):
            continue
        bucket = observed_ms // resolution_ms * resolution_ms
        for tier in payload.get("result", {}).get("vipCoinList", []):
            if tier.get("vipLevel") not in ("No VIP", "VIP 0", "0"):
                continue
            for rate in tier.get("list", []):
                if rate.get("currency") != "USDT" or rate.get("hourlyBorrowRate") in (None, ""):
                    continue
                observations.append(
                    {
                        "at": datetime.fromtimestamp(bucket / 1000, UTC).isoformat(),
                        "rate": str(rate["hourlyBorrowRate"]),
                        "resolution": "1h",
                        "source": "bybit_public_vip0",
                    }
                )
    deduped = {}
    for row in observations:
        deduped[row["at"]] = row
    return [deduped[key] for key in sorted(deduped)]


class ResearchEnvelope(BaseModel):
    source: str = "runtime_market_capture"
    observedAt: str | None = None
    receivedAt: str | None = None
    publishedThrough: str | None = None
    status: str
    stale: bool
    coverage: dict[str, Any] = Field(default_factory=dict)
    clockBasis: str = "observed"
    methodVersion: str = "observed-spread.v1"
    parameterHash: str | None = None
    dataVersion: str | None = None
    warnings: list[str] = Field(default_factory=list)
    data: Any = None


def access(pair, principal):
    if pair not in ("cross-gold", "funding-btc"):
        raise HTTPException(404, "Unknown research pair")
    if pair == "cross-gold" and not principal.has_permission("trade.read"):
        raise HTTPException(403, "Broker quote scope requires existing trade.read permission")


def envelope(data, warnings=None, method="observed-spread.v1"):
    state = capture_metadata()
    through = state["publishedThrough"]
    stale = through is None or datetime.now(UTC).timestamp() * 1000 - time_ms(through) > 120000
    return ResearchEnvelope(
        status="no_data" if through is None else "stale" if stale else "available",
        stale=stale,
        publishedThrough=through,
        receivedAt=through,
        dataVersion=state["dataVersion"],
        coverage={
            "historyStart": state["historyStart"],
            "publishedThrough": through,
            "calendar": "unverified",
            "sourceResolution": "native_ms",
            "localVisibility": "runtime_received",
            "highPrecisionPrehistory": "unavailable",
        },
        methodVersion=method,
        warnings=warnings or [],
        data=data,
    )


def rows_for(pair, start, end, part_ids=None):
    try:
        return read_rows(pair=pair, kind="spread", start=start, end=end, part_ids=part_ids)
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc


def funding_candle_basis_rows(symbol_base: str, lo: int, hi: int, interval_ms: int):
    """Pair same-bucket Bybit closes without filling either missing leg."""
    symbol = symbol_base + "USDT"
    legs: dict[int, dict[str, Decimal]] = {}
    # Check the usually-sparser spot leg first.  If it is absent, the pair
    # cannot produce a basis and we avoid touching the much larger perpetual
    # candle projection at all.
    for category in ("spot", "linear"):
        entity = f"{symbol}:{category}:trade"
        category_rows = read_projection(
            "historical_candle", entity, lo, hi, interval_ms=interval_ms, limit=10001
        )
        if category == "spot" and not category_rows:
            return []
        for row in category_rows:
            if row.get("quality"):
                continue
            try:
                at = int(row["closeTimeMs"])
                close = Decimal(str(row["close"]))
            except (KeyError, TypeError, ValueError):
                continue
            if lo <= at <= hi and close.is_finite() and close > 0:
                legs.setdefault(at, {})[category] = close

    rows = []
    for at, values in sorted(legs.items()):
        if "linear" not in values or "spot" not in values:
            continue
        basis = values["linear"] - values["spot"]
        rows.append(
            {
                "timeMs": str(at),
                "validDurationMs": interval_ms,
                "quality": [],
                "ohlc": {"midSpread": {"close": str(basis)}},
            }
        )
    return rows


def funding_basis_series_rows(
    symbol_base: str,
    lo: int,
    hi: int,
    interval_ms: int,
    view: str,
):
    """Read one backend-owned basis series without moving arithmetic to Web."""
    if symbol_base == "BTC":
        valid = read_projection(
            "spread_valid", "funding-btc", lo, hi, interval_ms=interval_ms, limit=10001
        )
        all_rows = read_projection(
            "spread_all", "funding-btc", lo, hi, interval_ms=interval_ms, limit=10001
        )
        return (valid if view == "valid" else all_rows), all_rows, "observed_paired_quotes"
    # Candle-derived basis is prepared by the background serving projector.
    # HTTP reads only this persisted read model; it never joins price legs or
    # performs Decimal arithmetic on demand.
    rows = read_projection(
        "funding_basis", symbol_base, lo, hi, interval_ms=interval_ms, limit=10001
    )
    return rows, rows, "persisted_candle_basis"


@router.get("/catalog", response_model=ResearchResponse)
def catalog(principal: Reader):
    catalog_rows = [
        {
            "pairId": "funding-btc",
            "venue": "Bybit",
            "left": "BTCUSDT perpetual",
            "right": "BTCUSDT spot",
            "economicUnit": "BTC",
            "currency": "USDT",
            "leftInstrumentId": "instrument_btc_usdt_perp",
            "rightInstrumentId": "instrument_btc_usdt",
            "mappingVersion": "existing.v1",
            "quoteScope": "public",
        }
    ]
    if principal.has_permission("trade.read"):
        catalog_rows.append(
            {
                "pairId": "cross-gold",
                "venue": "Bybit / MT5",
                "left": "XAUTUSDT",
                "right": "XAUUSD (native symbol from captured specification)",
                "economicUnit": "oz",
                "currency": "USD/USDT",
                "leftInstrumentId": "instrument_xau_usdt_perp",
                "rightInstrumentId": "instrument_xau_usd",
                "mappingVersion": "existing.v1",
                "quoteScope": "fixed_account_worker",
            }
        )
    return envelope(
        {
            "pairs": catalog_rows,
            "venues": [
                {"name": "Bybit", "available": True},
                {"name": "Binance", "available": False},
                {"name": "OKX", "available": False},
            ],
        }
    )


@router.get("/data-status", response_model=ResearchResponse)
def status(principal: Reader):
    data = capture_status()
    data["consumer"] = dict(STATUS)
    data["projection"] = projection_status()
    return envelope(data)


@router.get("/funding/board", response_model=ResearchResponse)
def funding_board(
    principal: Reader,
    venue: Literal["Bybit"] = "Bybit",
    symbols: Annotated[str, Query(max_length=2000)] = "BTC,ETH,SOL,XAUT,CRCL,MSTR",
    search: Annotated[str, Query(max_length=40)] = "",
    sort: Literal["default", "name", "rate_desc", "rate_asc"] = "default",
    resolution: Literal["1h", "8h", "1d"] = "1h",
    start: Annotated[datetime | None, Query(alias="from")] = None,
    end: Annotated[datetime | None, Query(alias="to")] = None,
):
    if (start and start.tzinfo is None) or (end and end.tzinfo is None):
        raise HTTPException(422, "Require timezone-aware timestamps")
    hi = time_ms(end.isoformat()) if end else int(datetime.now(UTC).timestamp() * 1000)
    lo = time_ms(start.isoformat()) if start else hi - 86400000
    if (
        (start and start.tzinfo is None)
        or (end and end.tzinfo is None)
        or not 0 < hi - lo <= 2678400000
    ):
        raise HTTPException(422, "Require an aware window of at most 31 days")
    resolution_ms = FUNDING_RESOLUTION_MS[resolution]
    rows = read_projection("funding_minute", "BTCUSDT", lo, hi)
    latest = {}
    for row in read_projection("funding_latest"):
        latest[row["payload"]["symbol"]] = row
    selected = list(
        dict.fromkeys(
            s.strip().upper().removesuffix("USDT") for s in symbols.split(",") if s.strip()
        )
    )[:100]
    table = [
        {
            "symbol": s,
            "usdtPerps": {
                "Bybit": (
                    float(Decimal(latest[s + "USDT"]["payload"]["fundingRate"]) * 100)
                    if s + "USDT" in latest
                    else None
                )
            },
            "inversePerps": {},
        }
        for s in selected
        if search.upper() in s
    ]
    if sort == "name":
        table.sort(key=lambda r: r["symbol"])
    elif sort != "default":
        table.sort(
            key=lambda r: (
                r["usdtPerps"]["Bybit"] is None,
                (r["usdtPerps"]["Bybit"] or 0) * (-1 if sort == "rate_desc" else 1),
            )
        )
    ranked = sorted(
        [
            {"market": r["symbol"], "value": r["usdtPerps"]["Bybit"]}
            for r in table
            if r["usdtPerps"]["Bybit"] is not None
        ],
        key=lambda r: r["value"],
    )
    borrow = read_projection("borrow_profile", "Bybit", lo, hi)
    observations = borrow_observations(
        read_projection("borrow_profile", "Bybit", lo, hi, interval_ms=3_600_000)
    )
    funding_indications = aggregate_funding_indications(rows, resolution_ms)
    current = latest.get("BTCUSDT", {}).get("payload", {}).get("fundingRate")
    board = {
        "updatedAt": max((r["receivedAt"] for r in latest.values()), default=""),
        "symbolOptions": sorted(s.removesuffix("USDT") for s in latest if s.endswith("USDT")),
                "resolutionOptions": ["1H", "8H", "日"],
        "usdtExchanges": ["Bybit"],
        "inverseExchanges": [],
        "rows": table,
        "highest": list(reversed(ranked[-3:])),
        "lowest": ranked[:3],
        "summaryCards": [
            {
                "title": "当前关注标的",
                "value": str(len(selected)),
                "subtitle": "Bybit 单交易所 · 缺数据不填零",
                "tone": "positive",
            },
            {
                "title": "BTC 指示资金费率",
                "value": "—" if current is None else f"{Decimal(current) * 100:.4f}%",
                "subtitle": "指示值，非已结算现金",
                "tone": "positive" if current is not None and Decimal(current) >= 0 else "negative",
            },
            {
                "title": "高精度研究标的",
                "value": "BTC / XAUT",
                "subtitle": "其他标的为公开资费扫描",
                "tone": "positive",
            },
            {
                "title": "借贷历史",
                "value": "已有公开观测" if observations else "暂无覆盖",
                "subtitle": "账户实际费率与有效期另行核对",
                "tone": "positive",
            },
        ],
    }
    return envelope(
        {
            "venue": venue,
            "rows": list(latest.values()),
            "board": board,
            "fundingChart": {
                "title": "Bybit 指示资金费率",
                "legendFunding": "指示资金费率",
                "legendPrice": "",
                "points": [
                    {
                        "date": r["at"],
                        "funding": float(Decimal(r["rate"]) * 100),
                    }
                    for r in funding_indications
                ],
            },
            "borrowObservations": observations,
            "fundingIndications": funding_indications,
            "history": rows,
            "settlements": read_projection("funding_settlement"),
            "borrowRates": borrow,
            "aggregation": "single_venue_no_OI_weighting",
        }
    )


@router.get("/pairs/{pair}/history", response_model=ResearchResponse)
def historical_prices(
    pair: str,
    principal: Reader,
    start: Annotated[datetime, Query(alias="from")],
    end: Annotated[datetime, Query(alias="to")],
    symbol: Annotated[str, Query(max_length=24)] = "BTC",
    resolution: Literal["1h", "8h", "1d"] = "1h",
):
    access(pair, principal)
    if (
        start.tzinfo is None
        or end.tzinfo is None
        or not 0 < (end - start).total_seconds() <= 2678400
    ):
        raise HTTPException(422, "Require an aware window of at most 31 days")
    symbol_base = normalize_research_symbol(symbol, pair=pair)
    symbol = symbol_base + "USDT"
    lo, hi = time_ms(start.isoformat()), time_ms(end.isoformat())
    display_ms = (
        FUNDING_RESOLUTION_MS[resolution]
        if pair == "funding-btc"
        else 60000 if hi - lo <= 86400000 else 300000 if hi - lo <= 7 * 86400000 else 900000
    )
    stored = price_coverage(symbol, lo, hi)
    prices = {}
    for row in [
        r
        for category in ("linear", "spot")
        for r in read_projection(
            "historical_candle", symbol + ":" + category + ":trade", lo, hi, interval_ms=display_ms
        )
    ]:
        if (
            row["symbol"] == symbol
            and lo <= int(row["closeTimeMs"]) <= hi
            and int(row["intervalMs"]) == 60000
            and not row.get("quality")
        ):
            prices[(row["stream"], row["sourceTimeMs"])] = row
    settlements = {}
    for row in (
        read_projection("funding_settlement", symbol, lo, hi) if pair == "funding-btc" else []
    ):
        at = int(row["payload"]["fundingRateTimestamp"])
        if row["payload"].get("symbol") == symbol and lo <= at <= hi:
            settlements[at] = row
    indication_rows = (
        read_projection("funding_minute", symbol, lo, hi) if pair == "funding-btc" else []
    )
    funding_indications = aggregate_funding_indications(
        indication_rows, FUNDING_RESOLUTION_MS[resolution]
    )
    borrow = (
        read_projection("borrow_profile", "Bybit", lo, hi, interval_ms=3_600_000)
        if pair == "funding-btc"
        else []
    )
    # Long-window chart sampling never replaces the retained one-minute source bars.
    display_ms = 60000 if hi - lo <= 86400000 else 300000 if hi - lo <= 7 * 86400000 else 900000
    display = {}
    for row in sorted(prices.values(), key=lambda r: int(r["closeTimeMs"])):
        display[(row["stream"], (int(row["closeTimeMs"]) - 1) // display_ms)] = row
    broker = {}
    if pair == "cross-gold":
        for row in read_projection("mt5_history_quote", "cross-gold", lo - 60000, hi):
            stamp = int(row["sourceTimeMs"])
            if lo <= stamp <= hi:
                key = stamp // 60000
                if key not in broker or stamp >= int(broker[key]["sourceTimeMs"]):
                    broker[key] = row
    return envelope(
        {
            "prices": sorted(display.values(), key=lambda r: int(r["closeTimeMs"])),
            "settlements": [settlements[k] for k in sorted(settlements)],
            "brokerHistory": [broker[k] for k in sorted(broker)],
            "chartSeries": history_chart(
                sorted(display.values(), key=lambda r: int(r["closeTimeMs"])),
                [settlements[k] for k in sorted(settlements)],
                [broker[k] for k in sorted(broker)],
                display_ms,
                funding_indications,
            ),
            "fundingIndications": funding_indications,
            "borrowObservations": borrow_observations(borrow),
            "fundingResolution": resolution,
            "historyResolution": "1m_closed_candles" if pair != "funding-btc" else resolution,
            "displayIntervalMs": str(display_ms),
            "displaySampling": "last_available_source_close_per_bucket_not_OHLC",
            "sourcePriceCount": stored["count"],
            "projection": projection_status(),
            "historyAvailability": "retrieved_after_event_not_entry_visible",
            "coverage": {
                "priceStart": stored["start"],
                "priceEnd": stored["end"],
                "settlementCount": len(settlements),
                "nativeQuotePrehistory": "not_available_from_candles",
            },
        }
    )


@router.get("/pairs/{pair}/latest", response_model=ResearchResponse)
def latest(pair: str, principal: Reader):
    access(pair, principal)
    row = LATEST.get(pair)
    provisional = row is not None
    if row is None:
        rows = read_projection("spread_latest", pair)
        row = rows[-1] if rows else None
    result = envelope(row, ["provisional_until_manifest_commit"] if provisional else [])
    if row:
        result.receivedAt = row["receivedAt"]
        result.stale = (
            bool(row["quality"])
            or datetime.now(UTC).timestamp() * 1000 - time_ms(row["receivedAt"]) > 2000
        )
        result.status = (
            "unavailable" if result.stale else "provisional" if provisional else "available"
        )
    return result


@router.get("/pairs/{pair}/series", response_model=ResearchResponse)
def series(
    pair: str,
    principal: Reader,
    start: Annotated[datetime, Query(alias="from")],
    end: Annotated[datetime, Query(alias="to")],
    view: Literal["valid", "all"] = "valid",
    resolution: Literal["1s", "15m", "1h", "8h", "1d", "event"] = "1s",
    symbol: Annotated[str, Query(max_length=24)] = "BTC",
):
    access(pair, principal)
    if (
        start.tzinfo is None
        or end.tzinfo is None
        or not 0 < (end - start).total_seconds() <= 2678400
    ):
        raise HTTPException(422, "Require an aware window of at most 31 days")
    lo, hi = time_ms(start.isoformat()), time_ms(end.isoformat())
    interval_ms = {
        "15m": 900_000,
        "1h": 3_600_000,
        "8h": 28_800_000,
        "1d": 86_400_000,
    }.get(resolution)
    if pair == "funding-btc" and symbol.strip().upper() in {"ALL", "*"}:
        if interval_ms is None:
            raise HTTPException(422, "A candle resolution is required for all funding basis series")
        series_by_symbol: dict[str, list[dict[str, Any]]] = {}
        distributions: dict[str, dict[str, Any]] = {}
        for symbol_base in FUNDING_BASIS_SYMBOLS:
            data, all_rows, _ = funding_basis_series_rows(
                symbol_base, lo, hi, interval_ms, view
            )
            if len(all_rows) > 10000:
                raise HTTPException(422, "Narrow the window: maximum 10000 returned points")
            series_by_symbol[symbol_base] = data
            distributions[symbol_base] = second_statistics(data, all_rows)
        return envelope(
            {
                "resolution": resolution,
                "symbol": "ALL",
                "symbols": list(FUNDING_BASIS_SYMBOLS),
                "seriesBySymbol": series_by_symbol,
                "distributionBySymbol": distributions,
                "view": view,
                "projection": {**projection_status(), "fundingBasis": funding_basis_status()},
                "basisSource": "backend_series_projection",
                "emptyReason": None
                if any(series_by_symbol.values())
                else "所选窗口暂无有效期现价差观测。",
                "qualityProfileId": "research-quality.v2",
            }
        )
    symbol_base = normalize_research_symbol(symbol, pair=pair)
    if pair == "funding-btc" and symbol_base != "BTC":
        data, all_rows, basis_source = funding_basis_series_rows(
            symbol_base, lo, hi, interval_ms or 900_000, view
        )
        stats = second_statistics(data, all_rows)
    elif resolution in ("1s", "15m", "1h", "8h", "1d"):
        valid = read_projection("spread_valid", pair, lo, hi, interval_ms=interval_ms, limit=10001)
        all_rows = read_projection("spread_all", pair, lo, hi, interval_ms=interval_ms, limit=10001)
        if len(all_rows) > 10000:
            raise HTTPException(422, "Narrow the window: maximum 10000 returned points")
        data = valid if view == "valid" else all_rows
        stats = second_statistics(valid, all_rows)
    else:
        rows = rows_for(pair, start.astimezone(UTC).isoformat(), end.astimezone(UTC).isoformat())
        data = [r for r in rows if not r["quality"]] if view == "valid" else rows
        stats = distribution(rows)
    if len(data) > 10000:
        raise HTTPException(422, "Narrow the window: maximum 10000 returned points")
    return envelope(
        {
            "resolution": resolution,
            "symbol": symbol_base,
            "chartSeries": spread_chart(data),
            "view": view,
            "rows": data,
            "distribution": stats,
            "projection": {**projection_status(), "fundingBasis": funding_basis_status()},
            "basisSource": (
                basis_source
                if pair == "funding-btc" and symbol_base != "BTC"
                else "observed_paired_quotes"
            ),
            "borrowObservations": borrow_observations(
                read_projection("borrow_profile", "Bybit", lo, hi, interval_ms=3_600_000)
                if pair == "funding-btc"
                else []
            ),
            "emptyReason": None
            if data
            else (
                "所选窗口没有通过质量校验的同时报价。MT5 历史 Tick 与 Bybit 分钟 K 线"
                "不能合成为跨所报价；源时钟未验证的观测也不进入有效序列。"
                if pair == "cross-gold"
                else "所选窗口暂无有效观测；请检查采集状态与索引进度。"
            ),
            "qualityProfileId": "research-quality.v2",
        }
    )


@router.get("/pairs/{pair}/distribution", response_model=ResearchResponse)
def get_distribution(
    pair: str,
    principal: Reader,
    start: Annotated[datetime, Query(alias="from")],
    end: Annotated[datetime, Query(alias="to")],
):
    result = series(pair, principal, start, end)
    result.data = result.data["distribution"]
    return result


@router.post("/scenario", response_model=ResearchResponse)
def calculate(request: Scenario, principal: Reader):
    access(request.pairId, principal)
    result = envelope(scenario(request), method="cashflow.v1")
    result.status = result.data["status"]
    return result


@router.post("/experiments", response_model=ResearchResponse, status_code=202)
def create_experiment(request: Experiment, principal: Writer):
    access(request.pairId, principal)
    if not get_settings().strategy_research_enabled:
        raise HTTPException(503, "Research worker is disabled")
    job = enqueue_experiment(principal.user_id, request.model_dump(mode="json", by_alias=True))
    return envelope(job, method="experiment.v1")


@router.get("/experiments/{run_id}", response_model=ResearchResponse)
def experiment(run_id: str, principal: Reader):
    job = get_experiment(run_id, principal.user_id)
    if not job:
        raise HTTPException(404, "Research run not found")
    access(job["parameters"]["pairId"], principal)
    result = envelope(job, method="experiment.v1")
    result.status = job["status"]
    return result


@router.post("/experiments/{run_id}/cancel", response_model=ResearchResponse)
def cancel(run_id: str, principal: Writer):
    experiment(run_id, principal)
    cancel_experiment(run_id, principal.user_id)
    return experiment(run_id, principal)


@router.get("/experiments/{run_id}/events", response_model=ResearchResponse)
def events(
    run_id: str,
    principal: Reader,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    result = experiment(run_id, principal)
    outcomes = (result.data["result"] or {}).get("events", [])
    result.data = {
        "rows": [
            {k: v for k, v in e.items() if k != "replay"} for e in outcomes[offset : offset + limit]
        ],
        "total": len(outcomes),
    }
    return result


@router.get("/experiments/{run_id}/events/{event_id}/replay", response_model=ResearchResponse)
def replay(run_id: str, event_id: str, principal: Reader):
    result = experiment(run_id, principal)
    output = result.data["result"] or {}
    candidates = list(output.get("events", []))
    for cell in output.get("matrix", []):
        candidates.extend(cell.get("events", []))
    event = next((e for e in candidates if e["id"] == event_id), None)
    if event is None:
        raise HTTPException(404, "Research event not found")
    result.data = event
    return result


@router.post("/drafts", response_model=ResearchResponse)
def draft(request: DraftRequest, principal: Writer):
    access(request.pairId, principal)
    return envelope(
        save_draft(principal.user_id, request.model_dump(mode="json")),
        ["execution_must_reauthorize_reprice_and_check_risk"],
    )


@router.get("/drafts/{draft_id}", response_model=ResearchResponse)
def read_draft(draft_id: str, principal: Reader):
    payload = get_draft(principal.user_id, draft_id)
    if payload is None:
        raise HTTPException(404, "Research draft not found")
    access(payload["pairId"], principal)
    return envelope({"id": draft_id, "parameters": payload, "executionAuthorized": False})
