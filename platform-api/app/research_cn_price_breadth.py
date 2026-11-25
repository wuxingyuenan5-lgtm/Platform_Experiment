"""Reproducible price breadth for a dated public stock universe.

The current universe is not point-in-time membership. It must never be presented
as an unbiased historical all-A census or silently mixed into the report model.
"""

import asyncio
import json
import logging
import re
import ssl
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from threading import Lock

import httpx
import truststore

from app.data_audit_calendar import cached_sessions
from app.research_equity_sources import archive, publish_artifact, read_artifact
from app.research_local_data import hedge_board_data_root

ARTIFACT = "cn-crowding-price-breadth"
HISTORY_ARTIFACT = "cn-crowding-price-breadth-history"
LIST_URL = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center."
PRICE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
_LOCK = asyncio.Lock()
_DECODER_LOCK = Lock()


def sina_adjusted(rows, factors):
    factors = sorted((date.fromisoformat(r["d"]).isoformat(), Decimal(r["f"])) for r in factors)
    if not factors or any(not f.is_finite() or f <= 0 for _, f in factors):
        raise ValueError("sina_factor_invalid")
    result = {}
    for row in rows:
        day = str(row["date"])[:10]
        date.fromisoformat(day)
        applicable = [f for d, f in factors if d <= day]
        if not applicable:
            raise ValueError("sina_factor_missing")
        value = Decimal(str(row["close"])) / applicable[-1]
        if day in result or not value.is_finite() or value <= 0:
            raise ValueError("sina_price_invalid")
        result[day] = value
    if not result:
        raise ValueError("sina_prices_empty")
    return result


def decode_sina(content, factors):
    from akshare.stock.cons import hk_js_decode
    from py_mini_racer import MiniRacer

    # The installed public format decoder handles data, never source-page JS.
    encoded = content.decode().split("=", 1)[1].split(";", 1)[0].strip().strip('"')
    # V8's first initialization in this Windows runtime is not thread-safe.
    # Serialize decoder lifetimes; HTTP collection remains bounded/concurrent.
    with _DECODER_LOCK, MiniRacer() as decoder:
        decoder.eval(hk_js_decode)
        rows = decoder.call("d", encoded)
    raw_factors = json.loads(factors.decode().split("=", 1)[1].splitlines()[0].rstrip(";"))["data"]
    return sina_adjusted(rows, raw_factors)


def parse_prices(payload, symbol):
    if payload.get("code") != 0 or symbol not in payload.get("data", {}):
        raise ValueError("price_response_invalid")
    node = payload["data"][symbol]
    rows = node.get("qfqday", node.get("day"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("price_history_empty")
    result = {}
    for row in rows:
        day = date.fromisoformat(row[0]).isoformat()
        close = Decimal(row[2])
        if day in result or not close.is_finite() or close <= 0:
            raise ValueError("price_history_invalid")
        result[day] = close
    return result


def price_breadth(histories, sessions, as_of, universe_count, *, history_start=None):
    """Strict complete calendar windows; weekly highs count each stock once.

    MA30 uses the last session's close and 30-session arithmetic mean. A new
    closing high is strictly greater than the preceding 59 closes (60 including
    today). The weekly high denominator requires every day's 60-session window.
    Missing quotes, suspensions and short listings are excluded, never filled.
    """
    days = sorted(set(d for d in sessions if d <= as_of))
    if not days or not histories:
        raise ValueError("breadth_inputs_empty")
    # Do not rank a thin early tail created by source-window truncation. Stocks
    # with a full retained window determine the common history start; IPOs do
    # not move that start forward, and still need their own complete windows.
    full_starts = [min(h) for h in histories.values() if len(h) >= 640]
    start = history_start or (
        max(full_starts) if full_starts else min(d for h in histories.values() for d in h)
    )
    days = [d for d in days if d >= start]
    weeks = {}
    for i, day in enumerate(days):
        dt = date.fromisoformat(day)
        monday = (dt - timedelta(days=dt.weekday())).isoformat()
        weeks.setdefault(monday, []).append(i)
    result = {"ma30": [], "high60": []}
    for monday, indexes in weeks.items():
        end = indexes[-1]
        stamp = days[end]
        partial = date.fromisoformat(monday) + timedelta(days=4) >= date.fromisoformat(as_of)
        eligible30 = above = eligible60 = highs = 0
        w30 = days[max(0, end - 29) : end + 1]
        w60 = days[max(0, indexes[0] - 59) : end + 1]
        for history in histories.values():
            if len(w30) == 30 and all(d in history for d in w30):
                eligible30 += 1
                above += history[stamp] * 30 > sum(history[d] for d in w30)
            if indexes[0] >= 59 and all(d in history for d in w60):
                eligible60 += 1
                highs += any(
                    history[days[i]] > max(history[d] for d in days[i - 59 : i]) for i in indexes
                )
        for key, numerator, denominator in [
            ("ma30", above, eligible30),
            ("high60", highs, eligible60),
        ]:
            result[key].append(
                {
                    "date": stamp,
                    "value": str(Decimal(numerator) * 100 / denominator) if denominator else None,
                    "numerator": numerator,
                    "eligible": denominator,
                    "universe": universe_count,
                    "partial": partial,
                }
            )
    return result


async def collect_price_breadth(force=False):
    async with _LOCK:
        now = datetime.now(UTC)
        today = (now + timedelta(hours=8)).date().isoformat()
        old = read_artifact(ARTIFACT) or {}
        if (
            not force
            and old.get("attemptedAt")
            and now - datetime.fromisoformat(old["attemptedAt"]) < timedelta(hours=20)
        ):
            return old
        stamp = now.isoformat()
        cache = hedge_board_data_root() / "raw/equity/crowding_price_cache" / today
        cache.mkdir(parents=True, exist_ok=True)
        try:
            sessions = cached_sessions(today)
            if not sessions:
                raise ValueError("independent_calendar_missing")
            async with httpx.AsyncClient(
                verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
                timeout=httpx.Timeout(20, connect=8),
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            ) as client:
                universe_path = cache / "universe.json"
                if universe_path.exists():
                    universe = json.loads(universe_path.read_text(encoding="utf8"))
                else:
                    r = await client.get(LIST_URL + "getHQNodeStockCount", params={"node": "hs_a"})
                    r.raise_for_status()
                    total = int(r.json())
                    if not 4000 <= total <= 10000:
                        raise ValueError("universe_count_invalid")
                    universe = []
                    for page in range(1, (total + 99) // 100 + 1):
                        r = await client.get(
                            LIST_URL + "getHQNodeData",
                            params={
                                "page": page,
                                "num": 100,
                                "sort": "symbol",
                                "asc": 1,
                                "node": "hs_a",
                                "symbol": "",
                                "_s_r_a": "init",
                            },
                        )
                        r.raise_for_status()
                        rows = r.json()
                        if not isinstance(rows, list):
                            raise ValueError("universe_page_invalid")
                        universe.extend(rows)
                        await asyncio.sleep(0.15)
                    if len(universe) != total or len({r["symbol"] for r in universe}) != total:
                        raise ValueError("universe_incomplete")
                    universe_path.write_text(
                        json.dumps(universe, ensure_ascii=False), encoding="utf8"
                    )
                    archive("crowding_universe", universe_path.read_bytes(), stamp)
                universe = [
                    r for r in universe if re.fullmatch(r"(?:sh6|sz[03])\d{5}", r["symbol"])
                ]
                semaphore = asyncio.Semaphore(4)
                histories, failures, manifest = {}, [], []
                # A challenge disables further Tencent requests for this run;
                # the independent Sina source has separately archived provenance.
                tencent_blocked = (cache / "tencent-unavailable.json").exists()
                sina_blocked = False

                async def fetch(row):
                    nonlocal tencent_blocked, sina_blocked
                    symbol = row["symbol"]
                    async with semaphore:
                        network_requested = False
                        try:
                            path = cache / (symbol + ".json")
                            if path.exists():
                                content = path.read_bytes()
                            elif not tencent_blocked:
                                network_requested = True
                                r = await client.get(
                                    PRICE_URL, params={"param": f"{symbol},day,,{today},640,qfq"}
                                )
                                if r.status_code in (403, 429, 501, 503):
                                    tencent_blocked = True
                                    (cache / "tencent-unavailable.json").write_text(
                                        json.dumps({"status": r.status_code, "at": stamp}),
                                        encoding="utf8",
                                    )
                                    content = None
                                else:
                                    r.raise_for_status()
                                    content = r.content
                            else:
                                content = None
                            if content is not None:
                                prices = parse_prices(json.loads(content), symbol)
                                path.write_bytes(content)
                                manifest.append(
                                    {
                                        "symbol": symbol,
                                        "provider": "tencent",
                                        "sha256": archive("crowding_prices", content, stamp),
                                    }
                                )
                            else:
                                paths = [
                                    cache / (symbol + suffix)
                                    for suffix in ("-sina.txt", "-factor.txt")
                                ]
                                blobs = []
                                for path, suffix in zip(
                                    paths, ("hisdata_klc2/klc_kl.js", "qfq.js"), strict=True
                                ):
                                    if path.exists():
                                        blob = path.read_bytes()
                                    else:
                                        if sina_blocked:
                                            raise ValueError("sina_source_unavailable")
                                        network_requested = True
                                        r = await client.get(
                                            f"https://finance.sina.com.cn/realstock/company/{symbol}/{suffix}"
                                        )
                                        if r.status_code in (403, 429, 501, 503):
                                            sina_blocked = True
                                        r.raise_for_status()
                                        blob = r.content
                                        path.write_bytes(blob)
                                    blobs.append(blob)
                                prices = await asyncio.to_thread(decode_sina, *blobs)
                                # Align public-source history depth; no old unadjusted splice.
                                prices = {d: prices[d] for d in sorted(prices)[-640:]}
                                manifest.append(
                                    {
                                        "symbol": symbol,
                                        "provider": "sina",
                                        "sha256": [
                                            archive("crowding_sina_prices", b, stamp) for b in blobs
                                        ],
                                    }
                                )
                            histories[symbol] = prices
                        except (httpx.HTTPError, ValueError, KeyError, ArithmeticError) as exc:
                            failures.append({"symbol": symbol, "error": type(exc).__name__})
                        if network_requested:
                            await asyncio.sleep(0.25)

                await asyncio.gather(*(fetch(r) for r in universe))
            # A source outage cannot publish a tiny successful subset as a market.
            if len(histories) < len(universe) * Decimal("0.95"):
                raise ValueError(f"price_fetch_coverage:{len(histories)}/{len(universe)}")
            computed = await asyncio.to_thread(
                price_breadth, histories, sessions, today, len(universe)
            )
            doc = {
                "generatedAt": stamp,
                "attemptedAt": stamp,
                "universeDate": today,
                "universeCount": len(universe),
                "fetchedCount": len(histories),
                "failures": failures,
                "manifest": manifest,
                "sources": {},
            }
            for key, rows in computed.items():
                doc["sources"][key] = {
                    "status": "partial" if failures else "ready",
                    "data": rows,
                    "sourceUrl": "https://finance.sina.com.cn/",
                    "sourceName": "腾讯 / 新浪前复权日线 · 新浪沪深A股目录",
                    "fetchedAt": stamp,
                    "observationDate": rows[-1]["date"],
                    "frequency": "weekly",
                    "universeDate": today,
                    "universeCount": len(universe),
                    "fetchedCount": len(histories),
                    "modelEligible": False,
                    "sampleBasis": "current-universe",
                }
            publish_artifact(ARTIFACT, doc)
            return doc
        except Exception as exc:
            logging.getLogger(__name__).warning("Price breadth: %s", exc)
            doc = {**old, "attemptedAt": stamp, "error": str(exc)}
            doc["sources"] = {
                k: {**v, "status": "error"} for k, v in old.get("sources", {}).items()
            }
            publish_artifact(ARTIFACT, doc)
            return doc
