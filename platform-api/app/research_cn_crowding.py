"""Public inputs for the report's crowding factors; no network work in GET."""

import asyncio
import hashlib
import json
import logging
import re
import ssl
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import truststore
from bs4 import BeautifulSoup

from app.research_cn_monitor import merge_history, series
from app.research_equity_sources import archive, publish_artifact, read_artifact
from app.research_local_data import hedge_board_data_root

ARTIFACT = "cn-crowding-research"
REPORT_URL = "https://reportapi.eastmoney.com/report/list"
_LOCK = asyncio.Lock()


def read_crowding():
    from app.research_cn_price_breadth import HISTORY_ARTIFACT

    doc = read_artifact(ARTIFACT) or {"sources": {}, "generatedAt": None}
    breadth = read_artifact("cn-crowding-price-breadth") or {}
    historical = (read_artifact(HISTORY_ARTIFACT) or {}).get("sources", {})
    breadth_sources = {}
    for key, live in breadth.get("sources", {}).items():
        prefix = historical.get(key)
        if prefix and live.get("sampleBasis") == prefix.get("sampleBasis") == "current-universe":
            first = next((row["date"] for row in live["data"] if row["value"] is not None), None)
            if first:
                older = [row for row in prefix["data"] if row["date"] < first]
                live = {
                    **live,
                    "data": older + [row for row in live["data"] if row["date"] >= first],
                }
        breadth_sources[key] = live
    industry = read_artifact("cn-crowding-industry") or {}
    return {
        **doc,
        "sources": {**doc.get("sources", {}), **breadth_sources},
        "industryHistory": industry.get("data", []),
        "industryHistoryStatus": industry.get("status", "no_data"),
    }


def parse_turnover(raw):
    rows = series(
        [{**r, "date": r["tradeDate"]} for r in raw["data"]],
        {"value": "turnover1d", "close": "hs300Close"},
    )
    if any(r["value"] is not None and r["value"] < 0 for r in rows):
        raise ValueError("negative_turnover")
    return rows


def parse_flow(raw):
    values = []
    for line in raw["data"]["klines"]:
        fields = line.split(",")
        if len(fields) != 15:
            raise ValueError("fundflow_schema_changed")
        values.append({"date": fields[0], "value": Decimal(fields[1]) / Decimal(100000000)})
    return series(values, {"value": "value"})


def report_count(raw, rating, start, end):
    hits = raw.get("hits")
    if not isinstance(hits, int) or hits < 0 or not isinstance(raw.get("data"), list):
        raise ValueError("report_count_schema_changed")
    rows = raw["data"]
    if bool(hits) != bool(rows):
        raise ValueError("report_count_empty")
    for row in rows:
        if row.get("emRatingCode") != rating or not start <= row["publishDate"][:10] <= end:
            raise ValueError("report_filter_mismatch")
    return hits


def seasonal_reports(rows):
    lookup = {date.fromisoformat(r["date"]).isocalendar()[:2]: r for r in rows}
    result = []
    for row in rows:
        year, week, _ = date.fromisoformat(row["date"]).isocalendar()
        previous = [lookup.get((year - offset, week)) for offset in (1, 2, 3)]
        complete = not row.get("partial") and all(r and not r.get("partial") for r in previous)
        baseline = sum(Decimal(r["count"]) for r in previous) / 3 if complete else None
        result.append(
            {
                **row,
                "baseline": str(baseline) if baseline is not None else None,
                "value": str(Decimal(row["count"]) - baseline) if baseline is not None else None,
            }
        )
    return result


def parse_industry_weekly(raw):
    rows = series(
        raw["data"],
        {"amount": "amountCongestion", "turnover": "turnoverRateF", "close": "indexClose"},
    )
    for row in rows:
        if row["amount"] is not None:
            if not 0 <= row["amount"] <= 1:
                raise ValueError("industry_share_invalid")
            row["amount"] *= 100
        if row["turnover"] is not None and row["turnover"] < 0:
            raise ValueError("industry_turnover_invalid")
    return rows


async def collect_industry_crowding(force=False):
    async with _LOCK:
        now = datetime.now(UTC)
        stamp = now.isoformat()
        old = read_artifact("cn-crowding-industry") or {}
        if (
            not force
            and old.get("attemptedAt")
            and now - datetime.fromisoformat(old["attemptedAt"]) < timedelta(hours=20)
        ):
            return old
        catalogue = (
            (read_artifact("cn-monitor") or {})
            .get("sources", {})
            .get("industry", {})
            .get("data", [])
        )
        try:
            if len(catalogue) != 31 or len({r["code"] for r in catalogue}) != 31:
                raise ValueError("industry_catalogue_incomplete")
            result = []
            previous = {r["code"]: r for r in old.get("data", [])}
            cache = (
                hedge_board_data_root()
                / "raw/equity/crowding_industry_cache"
                / now.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat()
            )
            cache.mkdir(parents=True, exist_ok=True)
            async with httpx.AsyncClient(
                verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
                timeout=httpx.Timeout(25, connect=10),
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            ) as client:
                csrf = None
                for item in catalogue:
                    code = item["code"]
                    if not re.fullmatch(r"\d{6}\.SI", code):
                        raise ValueError("industry_code_invalid")
                    page_url = "https://legulegu.com/stockdata/sw-industry-2021"
                    path = cache / (code + ".json")
                    if path.exists():
                        content = path.read_bytes()
                    else:
                        if csrf is None:
                            page = await client.get(page_url, params={"industryCode": code})
                            page.raise_for_status()
                            csrf = BeautifulSoup(page.content, "html.parser").select_one(
                                'meta[name="_csrf"]'
                            )["content"]
                        await asyncio.sleep(6)
                        response = await client.get(
                            "https://legulegu.com/api/stockdata/sw-industry-2021",
                            params={
                                "industryCode": code,
                                "freq": "week",
                                "token": hashlib.md5(
                                    now.astimezone(ZoneInfo("Asia/Shanghai"))
                                    .date()
                                    .isoformat()
                                    .encode()
                                ).hexdigest(),
                            },
                            headers={"X-CSRF-Token": csrf},
                        )
                        response.raise_for_status()
                        content = response.content
                    history = parse_industry_weekly(json.loads(content, parse_float=Decimal))
                    if len(history) < 104:
                        raise ValueError("industry_weekly_history_short")
                    path.write_bytes(content)
                    digest = archive("crowding_industry_weekly", content, stamp)
                    result.append(
                        {
                            "code": code,
                            "name": item["name"],
                            "history": merge_history(
                                previous.get(code, {}).get("history", []), history
                            ),
                            "sourceUrl": page_url + "?industryCode=" + code,
                            "rawSha256": digest,
                        }
                    )
            doc = {"status": "ready", "data": result, "fetchedAt": stamp, "attemptedAt": stamp}
        except Exception as exc:
            logging.getLogger(__name__).warning("Industry weekly history: %s", exc)
            doc = {**old, "status": "error", "attemptedAt": stamp, "error": type(exc).__name__}
        publish_artifact("cn-crowding-industry", doc)
        return doc


async def collect_crowding(force=False, *, analyst_backfill_start: date | None = None):
    async with _LOCK:
        now = datetime.now(UTC)
        stamp = now.isoformat()
        today = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
        doc = read_artifact(ARTIFACT) or {"sources": {}, "generatedAt": None}
        sources = doc.setdefault("sources", {})
        urls = {
            "turnover": "https://legulegu.com/stockdata/market-turnover-rate",
            "fundflow": "https://data.eastmoney.com/zjlx/dpzjlx.html",
            "analyst": "https://data.eastmoney.com/report/stock.jshtml",
        }
        async with httpx.AsyncClient(
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
            timeout=httpx.Timeout(25, connect=10),
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            for key, url in urls.items():
                if analyst_backfill_start is not None and key != "analyst":
                    continue
                old = sources.get(key, {})
                if (
                    not force
                    and analyst_backfill_start is None
                    and old.get("attemptedAt")
                    and now - datetime.fromisoformat(old["attemptedAt"]) < timedelta(hours=20)
                ):
                    continue
                manifest = []

                async def get(target, _key=key, _manifest=manifest, **kwargs):
                    response = await client.get(target, **kwargs)
                    response.raise_for_status()
                    digest = await asyncio.to_thread(
                        archive, "crowding_" + _key, response.content, stamp
                    )
                    _manifest.append({"url": str(response.url), "sha256": digest})
                    return response

                try:
                    if key == "turnover":
                        page = await get(url)
                        csrf = BeautifulSoup(page.content, "html.parser").select_one(
                            'meta[name="_csrf"]'
                        )["content"]
                        response = await get(
                            "https://legulegu.com/api/stockdata/market-turnover-rate",
                            params={
                                "years": 3,
                                "token": hashlib.md5(today.isoformat().encode()).hexdigest(),
                            },
                            headers={"X-CSRF-Token": csrf},
                        )
                        rows = parse_turnover(json.loads(response.content, parse_float=Decimal))
                    elif key == "fundflow":
                        response = await get(
                            "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get",
                            params={
                                "lmt": 0,
                                "klt": 101,
                                "secid": "1.000001",
                                "secid2": "0.399001",
                                "fields1": "f1,f2,f3,f7",
                                "fields2": ",".join(f"f{i}" for i in range(51, 66)),
                            },
                        )
                        rows = parse_flow(response.json())
                    else:
                        # API pagination is capped at 100. Use the verified rating-filtered
                        # total counts for each week, rather than interpreting page 1 as a census.
                        previous = {r["date"]: r for r in old.get("data", [])}
                        start = analyst_backfill_start or today - timedelta(days=28)
                        cursor = start - timedelta(days=start.weekday())
                        rows = []
                        while cursor <= today:
                            sunday = cursor + timedelta(days=6)
                            end = min(sunday, today)
                            prior = previous.get(sunday.isoformat())
                            if (
                                analyst_backfill_start is not None
                                and prior
                                and not prior.get("partial")
                                and sunday < today - timedelta(days=28)
                            ):
                                rows.append(prior)
                                cursor += timedelta(days=7)
                                continue
                            count = 0
                            week_manifest = []
                            for rating in ("007", "006"):
                                response = await get(
                                    REPORT_URL,
                                    params={
                                        "industryCode": "*",
                                        "industry": "*",
                                        "rating": rating,
                                        "ratingChange": "*",
                                        "beginTime": cursor.isoformat(),
                                        "endTime": end.isoformat(),
                                        "pageSize": 1,
                                        "pageNo": 1,
                                        "qType": 0,
                                        "code": "",
                                    },
                                )
                                count += report_count(
                                    response.json(), rating, cursor.isoformat(), end.isoformat()
                                )
                                week_manifest.append(manifest[-1])
                                await asyncio.sleep(0.15)
                            rows.append(
                                {
                                    "date": sunday.isoformat(),
                                    "count": count,
                                    "partial": sunday >= today,
                                    "through": end.isoformat(),
                                    "manifest": week_manifest,
                                }
                            )
                            # Checkpoint completed weeks for resumable historical collection.
                            if len(rows) % 26 == 0:
                                sources[key] = {
                                    **old,
                                    "status": "partial",
                                    "sourceUrl": url,
                                    "data": seasonal_reports(
                                        merge_history(old.get("data", []), rows)
                                    ),
                                    "attemptedAt": stamp,
                                }
                                await asyncio.to_thread(publish_artifact, ARTIFACT, doc)
                            cursor += timedelta(days=7)
                    merged = merge_history(old.get("data", []), rows)
                    if key == "analyst":
                        merged = seasonal_reports(merged)
                    sources[key] = {
                        "status": "ready",
                        "sourceUrl": url,
                        "data": merged,
                        "fetchedAt": stamp,
                        "attemptedAt": stamp,
                        "manifest": manifest,
                        "observationDate": today.isoformat()
                        if key == "analyst"
                        else merged[-1]["date"],
                    }
                except Exception as exc:
                    sources[key] = {
                        **sources.get(key, old),
                        "status": "error",
                        "sourceUrl": url,
                        "attemptedAt": stamp,
                        "error": type(exc).__name__,
                    }
                    logging.getLogger(__name__).warning("Crowding %s: %s", key, type(exc).__name__)
                doc["generatedAt"] = stamp
                await asyncio.to_thread(publish_artifact, ARTIFACT, doc)
        return doc
