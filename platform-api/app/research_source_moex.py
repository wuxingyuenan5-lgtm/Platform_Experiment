"""Official IMOEX prices, incrementally cached by the scheduled producer."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.research_local_data import hedge_board_data_root, read_local_json, write_local_json
from app.research_provider_errors import ResearchProviderError

HISTORY_URL = (
    "https://iss.moex.com/iss/history/engines/stock/markets/index/boards/SNDX/securities/IMOEX.json"
)
QUOTE_URL = "https://iss.moex.com/iss/engines/stock/markets/index/securities/IMOEX.json"
SOURCE_URL = "https://www.moex.com/ru/index/IMOEX"
# Incremental source cache is not a canonical serving-series document. Keep it
# outside public/v1/*/series, which the scheduled DuckDB mirror imports.
CACHE_PATH = "history/market-detail/moex/imoex.json"


def records(payload, key):
    block = payload[key]
    return [dict(zip(block["columns"], row, strict=True)) for row in block["data"]]


def price(value):
    result = Decimal(str(value))
    if not result.is_finite() or result <= 0:
        raise ValueError("invalid_moex_index_value")
    return result


async def fetch_imoex(client, user_agent, *, now=None):
    now = now or datetime.now(UTC)
    today = now.astimezone(ZoneInfo("Europe/Moscow")).date()
    first = today - timedelta(days=740)
    points = {}
    try:
        cache = read_local_json(CACHE_PATH)
    except ResearchProviderError as exc:
        if "local_data_not_found:" not in str(exc):
            raise
        cache = None
    if cache:
        if cache.get("symbol") != "IMOEX" or cache.get("sourceUrl") != SOURCE_URL:
            raise ValueError("moex_cache_identity_mismatch")
        points = {
            item["date"]: price(item["value"])
            for item in cache["observations"]
            if first.isoformat() <= item["date"] < today.isoformat()
        }
    # Re-read recent closes to capture revisions without fetching two years each tick.
    start_day = (
        max(first, datetime.fromisoformat(max(points)).date() - timedelta(days=7))
        if points
        else first
    )

    async def fetch(url, params):
        response = await client.get(url, params=params, headers={"User-Agent": user_agent})
        response.raise_for_status()
        digest = hashlib.sha256(response.content).hexdigest()
        raw = (
            hedge_board_data_root()
            / "raw/market-detail/moex"
            / now.date().isoformat()
            / f"{digest}.json"
        )
        raw.parent.mkdir(parents=True, exist_ok=True)
        if not raw.exists():
            raw.write_bytes(response.content)
        write_local_json(
            str(raw.with_suffix(".metadata.json").relative_to(hedge_board_data_root())),
            dict(url=url, params=params, retrievedAt=now.isoformat(), sha256=digest),
        )
        return response.json()

    offset = 0
    seen = set()
    for _ in range(20):
        payload = await fetch(
            HISTORY_URL,
            {
                "from": start_day.isoformat(),
                "till": (today - timedelta(days=1)).isoformat(),
                "iss.meta": "off",
                "start": offset,
            },
        )
        rows = records(payload, "history")
        cursor = records(payload, "history.cursor")[0]
        if cursor["INDEX"] != offset:
            raise ValueError("moex_cursor_mismatch")
        for row in rows:
            if row["SECID"] != "IMOEX" or row["BOARDID"] != "SNDX" or row["CURRENCYID"] != "RUB":
                raise ValueError("moex_history_identity_mismatch")
            day = datetime.fromisoformat(row["TRADEDATE"]).date()
            if not start_day <= day < today or row["TRADEDATE"] in seen:
                raise ValueError("moex_history_date_mismatch")
            seen.add(row["TRADEDATE"])
            if row["CLOSE"] is not None:
                points[row["TRADEDATE"]] = price(row["CLOSE"])
        offset += len(rows)
        if offset >= cursor["TOTAL"]:
            break
        if not rows:
            raise ValueError("moex_incomplete_history")
    else:
        raise ValueError("moex_history_page_limit")
    if not points:
        raise ValueError("moex_empty_history")
    quote = await fetch(QUOTE_URL, {"iss.meta": "off"})
    identity = next(
        row
        for row in records(quote, "securities")
        if row["SECID"] == "IMOEX" and row["BOARDID"] == "SNDX"
    )
    if identity["CURRENCYID"] != "RUB" or identity["CALCMODE"] != "PR":
        raise ValueError("moex_quote_identity_mismatch")
    current = next(
        row
        for row in records(quote, "marketdata")
        if row["SECID"] == "IMOEX" and row["BOARDID"] == "SNDX"
    )
    quote_day = datetime.fromisoformat(current["TRADEDATE"]).date()
    if quote_day > today:
        raise ValueError("moex_future_quote")
    # Today's value is always intraday. Only the history endpoint supplies closes.
    ordered = sorted(points.items())
    kind, as_of = "close", ordered[-1][0]
    if quote_day == today:
        stamp = datetime.fromisoformat(current["SYSTIME"]).replace(tzinfo=ZoneInfo("Europe/Moscow"))
        if stamp.date() != quote_day or stamp > now.astimezone(stamp.tzinfo) + timedelta(minutes=5):
            raise ValueError("moex_quote_timestamp_mismatch")
        points[quote_day.isoformat()] = price(current["CURRENTVALUE"])
        ordered = sorted(points.items())
        kind, as_of = "intraday", stamp.isoformat()
    write_local_json(
        CACHE_PATH,
        dict(
            schemaVersion="1.0",
            symbol="IMOEX",
            sourceUrl=SOURCE_URL,
            retrievedAt=now.isoformat(),
            observations=[
                dict(date=day, value=str(value))
                for day, value in ordered
                if day < today.isoformat()
            ],
        ),
    )
    return (
        "global-rsx",
        ordered,
        "Europe/Moscow",
        dict(
            currency="RUB",
            price_kind=kind,
            as_of=as_of,
            source="Moscow Exchange",
            source_url=SOURCE_URL,
            name="俄罗斯（MOEX 指数）",
            unit="index",
            quality_flags=["local_currency_price_index", "not_rsx_etf", "official_history_closes"],
        ),
    )
