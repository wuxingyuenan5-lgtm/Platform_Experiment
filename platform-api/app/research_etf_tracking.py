"""Public ETF tracking cache. Read endpoints never contact the upstream site."""

import asyncio
import hashlib
import json
import logging
import re
import ssl
import threading
from bisect import bisect_right, insort
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx
import truststore

from app.research_local_data import read_local_json, write_local_json
from app.research_provider_errors import ResearchProviderError

BASE = "https://wangwang-etf.com/"
ROOT = "public/v1/etf-tracking/"
INDICES = dict(
    zip(
        [
            "宽基/" + s
            for s in [
                "沪深300",
                "上证50",
                "上证180",
                "中证500",
                "中证800",
                "中证1000",
                "创业板",
                "科创50",
                "深证100",
            ]
        ],
        ["hs300", "sse50", "sse180", "csi500", "csi800", "csi1000", "chinext", "star50", "sz100"],
        strict=True,
    )
)
_IO = threading.RLock()
_REFRESH = threading.Lock()


def number(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def read(name):
    with _IO:
        try:
            return read_local_json(ROOT + name + ".json")
        except ResearchProviderError:
            return {}


def write(name, value):
    with _IO:
        write_local_json(ROOT + name + ".json", value)


def validate(path, data):
    if path == "universe":
        if not isinstance(data, list) or not data:
            raise ValueError("Invalid ETF universe")
        if any(
            not isinstance(x, dict) or not re.fullmatch(r"\d{6}", str(x.get("code", "")))
            for x in data
        ):
            raise ValueError("Invalid ETF code")
        if len({x["code"] for x in data}) != len(data):
            raise ValueError("Duplicate ETF code")
        if any(not x.get("name") or not x.get("display_group") for x in data):
            raise ValueError("Incomplete ETF catalog")
        return
    field = "series" if path.startswith("etfs/") else "rows"
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("meta"), dict)
        or not isinstance(data.get(field), list)
        or not data[field]
    ):
        raise ValueError("Invalid ETF series")
    if path.startswith("etfs/") and str(data["meta"].get("code")) != path.split("/")[-1]:
        raise ValueError("ETF identity mismatch")
    if path.startswith("margin/etfs/") and str(data["meta"].get("code")) != path.split("/")[-1]:
        raise ValueError("Margin ETF identity mismatch")
    dates = [x.get("date", "") for x in data[field]]
    for day in dates:
        datetime.strptime(day, "%Y-%m-%d")
    if dates != sorted(set(dates)):
        raise ValueError("Unordered or duplicate dates")


def fetch(client, path):
    now = datetime.now(UTC).isoformat()
    old = read(path)
    try:
        response = client.get(BASE + "data/" + path + ".json")
        response.raise_for_status()
        data = json.loads(response.content, parse_float=str)
        validate(path, data)
        if path != "universe" and old.get("data"):
            field = "series" if path.startswith("etfs/") else "rows"
            old_rows = old["data"].get(field, [])
            if old_rows and data[field][-1]["date"] < old_rows[-1]["date"]:
                raise ValueError("Source observation date regressed")
        digest = hashlib.sha256(response.content).hexdigest()
        # Preserve the exact response for provenance, including decimal precision.
        write("raw/" + digest, {"url": str(response.url), "fetchedAt": now, "body": response.text})
        doc = {
            "status": "ready",
            "fetchedAt": now,
            "attemptedAt": now,
            "url": str(response.url),
            "sha256": digest,
            "data": data,
        }
    except Exception as exc:
        doc = {
            **old,
            "status": "stale" if old.get("data") else "no_data",
            "attemptedAt": now,
            "error": type(exc).__name__,
        }
    write(path, doc)
    return doc


def index_key(meta):
    key = meta.get("index_turnover_key") or INDICES.get(meta.get("display_group"))
    return key if key and re.fullmatch(r"[a-z0-9_]+", key) else None


def refresh(*, force=False):
    if not _REFRESH.acquire(blocking=False):
        return "busy"
    try:
        last = read("refresh")
        if not force and last.get("attemptedAt"):
            elapsed = (
                datetime.now(UTC) - datetime.fromisoformat(last["attemptedAt"])
            ).total_seconds()
            if elapsed < (21600 if last.get("status") == "ready" else 3600):
                return "up_to_date"
        with httpx.Client(
            timeout=25, follow_redirects=True, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ) as client:
            universe = fetch(client, "universe")
            if not universe.get("data"):
                write("refresh", {"attemptedAt": datetime.now(UTC).isoformat(), "status": "error"})
                return "error"
            paths = set()
            for item in universe["data"]:
                if item.get("dashboard_eligible"):
                    paths.update(["etfs/" + item["code"], "margin/etfs/" + item["code"]])
                    key = index_key(item)
                    if key:
                        paths.update(["index-turnover/" + key, "margin/" + key])
            with ThreadPoolExecutor(max_workers=4) as pool:
                docs = list(pool.map(lambda p: fetch(client, p), sorted(paths)))
            state = (
                "ready"
                if universe["status"] == "ready" and all(d["status"] == "ready" for d in docs)
                else "partial"
            )
            write("refresh", {"attemptedAt": datetime.now(UTC).isoformat(), "status": state})
            return state
    finally:
        _REFRESH.release()


async def run_periodic():
    while True:
        try:
            await asyncio.to_thread(refresh)
        except Exception:
            logging.getLogger(__name__).exception("ETF tracking refresh failed")
        await asyncio.sleep(300)


def provenance(doc):
    return {k: doc.get(k) for k in ("status", "fetchedAt", "attemptedAt", "url", "sha256")}


def enriched(data, index_rows=()):
    index = {r["date"]: r for r in index_rows}
    rows = []
    history = {"etf_qfq_turnover_est_yi": [], "qfq_delta_units_yi": [], "flow_yi": []}
    previous = None
    for raw in data.get("series", []):
        row = dict(raw)
        price, delta = number(row.get("etf_qfq_close")), number(row.get("qfq_delta_units_yi"))
        average = number(row.get("etf_qfq_avg_price_est"))
        basis = average if average is not None else price
        row["flow_yi"] = str(delta * basis) if delta is not None and basis is not None else None
        row["flow_price_basis"] = "average" if average is not None else "close"
        row["return_pct"] = (
            str((price / previous - 1) * 100) if price is not None and previous else None
        )
        previous = price
        benchmark = index.get(row["date"], {})
        row["index_close"] = benchmark.get("close")
        row["index_turnover_yi"] = benchmark.get("turnover_yi")
        turnover = number(benchmark.get("turnover_yi"))
        flow = number(row["flow_yi"])
        row["flow_to_index_pct"] = (
            str(flow / turnover * 100) if flow is not None and turnover and turnover > 0 else None
        )
        for key, values in history.items():
            val = number(row.get(key))
            if val is not None:
                ranked = abs(val) if key != "etf_qfq_turnover_est_yi" else val
                insort(values, ranked)
            # Expanding, as-of rank: no future observations enter past ranks.
            row[key + "_percentile"] = (
                str(Decimal(bisect_right(values, ranked)) / len(values) * 100)
                if val is not None and len(values) >= 60
                else None
            )
        rows.append(row)
    return rows


def catalog():
    doc = read("universe")
    result = []
    for meta in doc.get("data", []):
        detail = read("etfs/" + meta["code"])
        data = detail.get("data", {})
        rows = enriched(data)
        result.append({**meta, "latest": rows[-1] if rows else None, "source": provenance(detail)})
    return {"items": result, "source": provenance(doc), "refresh": read("refresh")}


def detail(code):
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("Invalid code")
    meta = next((x for x in read("universe").get("data", []) if x["code"] == code), None)
    if meta is None:
        raise KeyError(code)
    doc = read("etfs/" + code)
    key = index_key(meta)
    index = read("index-turnover/" + key) if key else {}
    margin = read("margin/etfs/" + code)
    group_margin = read("margin/" + key) if key else {}
    data = doc.get("data", {})
    members = [
        x
        for x in read("universe").get("data", [])
        if x.get("dashboard_eligible")
        and (index_key(x) == key if key else x.get("display_group") == meta.get("display_group"))
    ]
    member_docs = [read("etfs/" + x["code"]) for x in members]
    index_rows = index.get("data", {}).get("rows", [])
    member_series = [enriched(d.get("data", {}), index_rows) for d in member_docs]
    member_rows = [{r["date"]: r for r in rows} for rows in member_series]
    index_by_date = {r["date"]: r for r in index_rows}
    group = []
    ranks = {"flow_yi": [], "etf_qfq_turnover_est_yi": [], "qfq_delta_units_yi": []}
    for day in sorted({day for rows in member_rows for day in rows}):
        row = {"date": day, "expected": len(members)}
        for field in (
            "flow_yi",
            "etf_qfq_turnover_est_yi",
            "qfq_total_units_yi",
            "qfq_delta_units_yi",
        ):
            values = [number(rows.get(day, {}).get(field)) for rows in member_rows]
            covered = sum(v is not None for v in values)
            row[field] = (
                str(sum(v for v in values if v is not None)) if covered == len(members) else None
            )
            row[field + "_covered"] = covered
        weighted = [
            (
                number(rows.get(day, {}).get("return_pct")),
                number(rows.get(day, {}).get("etf_qfq_turnover_est_yi")),
            )
            for rows in member_rows
        ]
        complete = all(ret is not None and amount is not None for ret, amount in weighted)
        weight = sum(amount for _, amount in weighted if amount is not None)
        row["return_pct"] = (
            str(sum(ret * amount for ret, amount in weighted) / weight)
            if complete and weight
            else None
        )
        benchmark = index_by_date.get(day, {})
        row["index_close"] = benchmark.get("close")
        row["index_turnover_yi"] = benchmark.get("turnover_yi")
        denominator = number(row["index_turnover_yi"])
        flow = number(row["flow_yi"])
        row["flow_to_index_pct"] = (
            str(flow / denominator * 100) if flow is not None and denominator else None
        )
        for field, values in ranks.items():
            val = number(row[field])
            if val is not None:
                val = val if field == "etf_qfq_turnover_est_yi" else abs(val)
                insort(values, val)
            row[field + "_percentile"] = (
                str(Decimal(bisect_right(values, val)) / len(values) * 100)
                if val is not None and len(values) >= 60
                else None
            )
        group.append(row)
    return {
        "meta": meta,
        "series": enriched(data, index.get("data", {}).get("rows", [])),
        "group": group,
        "groupLabel": meta.get("index_turnover_name") or meta.get("display_group"),
        "members": [
            {
                "meta": member,
                "series": rows,
                "margin": read("margin/etfs/" + member["code"]).get("data", {}).get("rows", []),
            }
            for member, rows in zip(members, member_series, strict=True)
        ],
        "disclosures": data.get("disclosures", []),
        "margin": margin.get("data", {}).get("rows", []),
        "groupMargin": group_margin.get("data", {}).get("rows", []),
        "sources": {
            "market": provenance(doc),
            "index": provenance(index),
            "margin": provenance(margin),
            "groupMargin": provenance(group_margin),
            "groupMarket": {
                "status": "ready"
                if all(d.get("status") == "ready" for d in member_docs)
                else "stale",
                "fetchedAt": None,
                "url": BASE,
            },
        },
    }
