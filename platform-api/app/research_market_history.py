"""Native daily price archive behind market-detail snapshots; no GET-side fetching."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

from app.database import connection
from app.research_a_share_repository import finish_refresh, start_refresh, write_history_points
from app.research_provider_market_detail import MARKET_SYMBOLS, MarketDetailProvider

DATASET = "market_price"


def archive_snapshot(market: str, snapshot, run_id: str) -> None:
    points = []
    for row in snapshot.rows:
        if row.unit == "ratio" or row.price_kind != "close" or row.close is None:
            continue
        if not row.observation_date:
            continue
        points.append(
            (
                row.observation_date,
                f"{row.source}:{row.symbol}",
                {
                    "close": str(row.close),
                    "symbol": row.symbol,
                    "currency": row.currency,
                    "timezone": row.timezone,
                    "source": row.source,
                    "sourceUrl": row.source_url,
                    "qualityFlags": row.quality_flags,
                },
            )
        )
    if points:
        write_history_points(run_id, DATASET, points, source="native market-detail source")


async def backfill_market_prices(root: Path) -> dict:
    provider = MarketDetailProvider(timeout_seconds=30, user_agent="VariableGlobalResearch/1.0")
    symbols = sorted(
        {
            s
            for mapping in MARKET_SYMBOLS.values()
            for s in mapping.values()
            if s not in {"AU0", "AG0", "LC0", "RSX"}
        }
    )
    semaphore = asyncio.Semaphore(4)
    results, failures = {}, []
    async with httpx.AsyncClient(timeout=30, trust_env=True) as client:

        async def fetch(symbol):
            async with semaphore:
                try:
                    _, rows, timezone, meta = await provider._fetch_yahoo_history(
                        client, symbol, symbol, full_history=True
                    )
                    today = datetime.now(ZoneInfo(timezone)).date().isoformat()
                    closed = [
                        (day, value)
                        for day, value in rows
                        if day < today or (day == today and meta["price_kind"] == "close")
                    ]
                    if not closed:
                        raise ValueError("empty daily prices")
                    path = (
                        root
                        / "raw/research/market_price_history"
                        / (
                            datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
                            + "-"
                            + unquote(symbol).replace("/", "_").replace("=", "_")
                            + ".json"
                        )
                    )
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(
                        json.dumps(
                            {
                                "symbol": symbol,
                                "timezone": timezone,
                                "sourceUrl": f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                                "retrievedAt": datetime.now(UTC).isoformat(),
                                "representation": "parsed_vendor_daily_closes",
                                "metadata": meta,
                                "rows": [[d, str(v)] for d, v in closed],
                            },
                            ensure_ascii=False,
                        ),
                        encoding="utf8",
                    )
                    results[symbol] = (closed, timezone, meta)
                    print(f"market {symbol}: {len(closed)}", flush=True)
                except Exception as exc:
                    failures.append({"symbol": symbol, "error": type(exc).__name__})
                    print(f"market {symbol}: failed {type(exc).__name__}", flush=True)

        await asyncio.gather(*(fetch(symbol) for symbol in symbols))
    run_id = "market-history-" + uuid4().hex
    start_refresh(run_id, None)
    counts = {}
    written = set()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        for market, mapping in MARKET_SYMBOLS.items():
            for row_id, symbol in mapping.items():
                if symbol not in results:
                    continue
                rows, timezone, meta = results[symbol]
                points = [
                    (
                        day,
                        f"Yahoo Finance:{unquote(symbol)}",
                        {
                            "close": str(value),
                            "symbol": unquote(symbol),
                            "currency": meta.get("currency"),
                            "timezone": timezone,
                            "source": "Yahoo Finance",
                            "sourceUrl": f"https://finance.yahoo.com/quote/{symbol}/history/",
                            "qualityFlags": ["price_return_excludes_distributions"],
                        },
                    )
                    for day, value in rows
                ]
                if symbol not in written:
                    write_history_points(run_id, DATASET, points, source="Yahoo Finance", db=db)
                    written.add(symbol)
                counts[f"{market}:{row_id}"] = {
                    "count": len(rows),
                    "first": rows[0][0],
                    "last": rows[-1][0],
                }
    finish_refresh(run_id, "partial" if failures else "ready")
    report = {"retrievedAt": datetime.now(UTC).isoformat(), "series": counts, "failures": failures}
    path = root / "history/market-price-backfill-latest.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    return report


async def backfill_stock_prices(root: Path, *, codes: set[str] | None = None) -> dict:
    """Page existing CN/HK securities backwards, checking adjustment overlaps."""
    from datetime import date, timedelta
    from decimal import Decimal

    from app.database_connection import read_only_connection

    with read_only_connection() as db:
        prior_rows = [
            dict(r)
            for r in db.execute("SELECT * FROM research_a_share_history WHERE dataset='stock'")
        ]
    backup = root / "history/stock-before-backfill-20261027.json"
    if not backup.exists():
        backup.write_text(json.dumps(prior_rows, ensure_ascii=False), encoding="utf8")
    stored = {}
    for row in prior_rows:
        stored.setdefault(row["entity_code"], {})[row["observed_at"]] = Decimal(
            str(json.loads(row["payload_json"])["close"])
        )
    if codes is not None:
        stored = {code: rows for code, rows in stored.items() if code in codes}
    previous_path = root / "history/stock-backfill-latest.json"
    previous_report = (
        json.loads(previous_path.read_text(encoding="utf8")) if previous_path.exists() else {}
    )
    results, failures = {}, []
    semaphore = asyncio.Semaphore(3)
    run_id = "stock-history-" + uuid4().hex
    start_refresh(run_id, None)
    async with httpx.AsyncClient(timeout=25, trust_env=False) as client:

        async def fetch(code, previous):
            async with semaphore:
                symbol = ("hk" if len(code) == 5 else "sh" if code[0] in "569" else "sz") + code
                values, end, source_field = {}, "", None
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
                try:
                    for page in range(80):
                        response = await client.get(
                            (
                                "https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get"
                                if len(code) == 5
                                else "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
                            ),
                            params={"param": f"{symbol},day,1900-01-01,{end},640,qfq"},
                        )
                        response.raise_for_status()
                        document = response.json()
                        path = root / f"raw/research/stock_history/{code}/{stamp}-{page}.json"
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(
                            json.dumps(
                                {
                                    "url": str(response.url),
                                    "retrievedAt": datetime.now(UTC).isoformat(),
                                    "response": document,
                                },
                                ensure_ascii=False,
                            ),
                            encoding="utf8",
                        )
                        if document.get("code") != 0:
                            raise ValueError("source response error")
                        node = (document.get("data") or {}).get(symbol) or {}
                        field = "qfqday" if node.get("qfqday") else "day"
                        if source_field is not None and source_field != field and node.get(field):
                            raise ValueError("source adjustment field changed during paging")
                        rows = node.get(field) or []
                        if not rows:
                            if page == 0:
                                raise ValueError("empty adjusted source history")
                            break
                        source_field = field
                        incoming = {}
                        for row in rows:
                            day = date.fromisoformat(row[0]).isoformat()
                            value = Decimal(str(row[2]))
                            if not value.is_finite() or day > datetime.now(UTC).date().isoformat():
                                raise ValueError("invalid adjusted close/date")
                            if day in incoming:
                                raise ValueError("duplicate source date")
                            incoming[day] = value
                        overlap = set(values) & set(incoming)
                        if values and (
                            not overlap or any(values[d] != incoming[d] for d in overlap)
                        ):
                            raise ValueError("pagination adjustment overlap mismatch")
                        oldest = min(incoming)
                        if values and oldest >= min(values):
                            break
                        values.update(incoming)
                        if len(rows) < 640:
                            break
                        end = (date.fromisoformat(oldest) + timedelta(days=30)).isoformat()
                    else:
                        raise ValueError("history page bound exceeded")
                    native_dataset = (
                        "stock_tencent_qfq_native"
                        if source_field == "qfqday"
                        else "stock_tencent_day_native"
                    )
                    native = [
                        (
                            d,
                            f"{symbol}:{stamp}",
                            {
                                "close": str(v),
                                "symbol": symbol,
                                "currency": "HKD" if len(code) == 5 else "CNY",
                                "sourceField": source_field,
                                "adjustmentAsOf": stamp,
                                "closed": d < datetime.now(UTC).date().isoformat(),
                                "qualityFlags": ["nonpositive_adjusted_price"] if v <= 0 else [],
                                "sourceArtifact": (
                                    f"raw/research/stock_history/{code}/{stamp}-0.json"
                                ),
                            },
                        )
                        for d, v in sorted(values.items())
                    ]
                    await asyncio.to_thread(
                        write_history_points,
                        run_id,
                        native_dataset,
                        native,
                        source="Tencent native daily history",
                    )
                    results[code] = {
                        "fetched": len(values),
                        "added": 0,
                        "nativeCount": len(values),
                        "nativeDataset": native_dataset,
                        "first": min(values),
                        "last": max(values),
                    }
                    if source_field != "qfqday":
                        results[code]["primaryStatus"] = "native_field_kept_separate"
                        return
                    # Preserve the full signed native series in its own vintage;
                    # only a positive suffix can enter close-ratio calculations.
                    nonpositive = [d for d, v in values.items() if v <= 0]
                    floor = max(nonpositive, default="")
                    values = {d: v for d, v in values.items() if d > floor}
                    if not values:
                        raise ValueError("no positive source suffix for returns")
                    overlap = set(values) & set(previous)
                    if not overlap:
                        raise ValueError("no stored overlap for identity validation")
                    # QFQ is a moving adjusted series: never splice incompatible
                    # adjustment vintages or vendor definitions into a long chart.
                    mismatches = [
                        d for d in overlap if abs(values[d] - previous[d]) > Decimal("0.002")
                    ]
                    if mismatches:
                        raise ValueError(
                            f"stored adjustment vintage mismatch on {len(mismatches)} dates"
                        )
                    points = [
                        (d, code, {"close": str(v), "turnoverYuan": None})
                        for d, v in sorted(values.items())
                        if d < min(previous)
                    ]
                    if points:
                        await asyncio.to_thread(
                            write_history_points, run_id, "stock", points, source="腾讯前复权日线"
                        )
                    results[code] = {
                        **results[code],
                        "fetched": len(values),
                        "added": len(points),
                        "first": min(values),
                        "last": max(values),
                        "overlap": len(overlap),
                    }
                    print(f"stock {code}: added {len(points)}", flush=True)
                except Exception as exc:
                    failures.append({"code": code, "error": str(exc)})
                    print(f"stock {code}: {type(exc).__name__}: {exc}", flush=True)

        await asyncio.gather(*(fetch(code, points) for code, points in stored.items()))
    finish_refresh(run_id, "partial" if failures else "ready")
    if codes is not None:
        results = {**previous_report.get("series", {}), **results}
        failures = [
            x for x in previous_report.get("failures", []) if x["code"] not in stored
        ] + failures
    report = {"retrievedAt": datetime.now(UTC).isoformat(), "series": results, "failures": failures}
    (root / "history/stock-backfill-latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    return report


def import_choice_stock_history(root: Path) -> dict:
    """Keep licensed forward-adjusted vintages separate from Tencent history."""
    from datetime import date
    from decimal import Decimal

    results, failures = {}, []
    run_id = "choice-history-" + uuid4().hex
    start_refresh(run_id, None)
    for path in sorted((root / "raw/choice").glob("stock-fallback-*-20261027.json")):
        document = json.loads(path.read_text(encoding="utf8"))
        if document.get("errorCode"):
            failures.append({"codes": document["codes"], "errorCode": document["errorCode"]})
            continue
        by_code = {}
        for row in document["records"]:
            if row["code"] not in document["codes"]:
                raise ValueError("Choice security identity mismatch")
            day = date.fromisoformat(row["date"]).isoformat()
            if not document["start"] <= day <= document["end"]:
                raise ValueError("Choice date outside requested window")
            value = None if row["close"] is None else Decimal(str(row["close"]))
            if value is not None and not value.is_finite():
                raise ValueError("Choice nonfinite close")
            values = by_code.setdefault(row["code"], {})
            if day in values:
                raise ValueError("duplicate Choice security/date")
            values[day] = value
        with connection() as db:
            db.execute("BEGIN IMMEDIATE")
            for code, values in by_code.items():
                available = [d for d, v in values.items() if v is not None]
                if not available:
                    failures.append({"code": code, "error": "no price history"})
                    continue
                lower, upper = min(available), max(available)
                # Pre-listing padding is not market history; internal NULLs
                # remain explicit, including suspended/missing observations.
                points = [
                    (
                        day,
                        code,
                        {
                            "close": None if value is None else str(value),
                            "currency": "HKD" if code.endswith(".HK") else "CNY",
                            "symbol": code,
                            "adjustment": "forward",
                            "adjustFlag": 3,
                            "fillData": 0,
                            "adjustmentAsOf": document["end"],
                            "sourceArtifact": str(path.relative_to(root)),
                            "qualityFlags": ["nonpositive_adjusted_price"]
                            if value is not None and value <= 0
                            else [],
                        },
                    )
                    for day, value in sorted(values.items())
                    if lower <= day <= upper
                ]
                write_history_points(run_id, "stock_choice_qfq", points, source="Choice CSD", db=db)
                results[code] = {
                    "count": len(points),
                    "valid": len(available),
                    "nulls": sum(p[2]["close"] is None for p in points),
                    "first": lower,
                    "last": upper,
                }
    finish_refresh(run_id, "partial" if failures else "ready")
    report = {"retrievedAt": datetime.now(UTC).isoformat(), "series": results, "failures": failures}
    (root / "history/choice-stock-backfill-latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    return report
