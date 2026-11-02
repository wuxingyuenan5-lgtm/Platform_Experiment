"""Local AI-industry research; independent bounded producers, never upstream GETs."""

import asyncio
import hashlib
import json
import logging
import os
import ssl
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import truststore

from app.research_ai_catalog import COMPANIES
from app.research_ai_financials import build_company, summary
from app.research_ai_sources import (
    financial_checks,
    issuer_disclosures,
    operating_kpis,
    reported_cds,
)
from app.research_equity_sources import archive, publish_artifact, read_artifact
from app.research_local_data import hedge_board_data_root, write_local_json

_LOCK = threading.Lock()


@contextmanager
def producer_lock():
    path = hedge_board_data_root() / "public/v1/equity/ai/producer.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if not path.stat().st_size:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def read_ai(ticker=None):
    if ticker and ticker not in {c[0] for c in COMPANIES}:
        raise ValueError("Unsupported AI company")
    result = read_artifact("ai/" + (ticker or "summary"))
    if not result:
        return {"status": "no_data", "companies": [], "cds": [], "capexHistory": []}
    checked = result.get("generatedAt")
    if checked and datetime.now(UTC) - datetime.fromisoformat(checked) > timedelta(hours=30):
        result["status"] = "stale"
    return result


def refresh(force=False):
    if not _LOCK.acquire(blocking=False):
        return "busy"
    try:
        with producer_lock() as acquired:
            return _produce(force) if acquired else "busy"
    finally:
        _LOCK.release()


def _produce(force):
    stamp = datetime.now(UTC).isoformat()
    health = read_artifact("ai/health")
    old_sources = health.get("sources", {})
    states = {}
    state_lock = threading.Lock()

    def obtain(key, url, parser, hours=24, bootstrap=None):
        old = old_sources.get(key, {})
        cached = read_artifact("ai/cache/" + key)
        last = old.get("attemptedAt")
        interval = hours if old.get("status") == "ready" else 1
        if (
            not force
            and last
            and timedelta(0)
            <= datetime.now(UTC) - datetime.fromisoformat(last)
            < timedelta(hours=interval)
        ):
            with state_lock:
                states[key] = old
            return cached.get("data")
        try:
            if bootstrap and bootstrap.exists() and not old:
                content = bootstrap.read_bytes()
                source_meta = json.loads(
                    bootstrap.with_suffix(".source.json").read_text(encoding="utf8")
                )
                observed = source_meta["retrievedAt"]
                if hashlib.sha256(content).hexdigest() != source_meta["sha256"]:
                    raise ValueError("Bootstrap integrity mismatch")
            else:
                with httpx.Client(
                    timeout=30,
                    verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
                    follow_redirects=True,
                    headers={"User-Agent": "VariableGlobal Financial Research personal dashboard"},
                ) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    content = response.content
                observed = stamp
            parsed = parser(content)
            digest = archive("ai/" + key, content, observed)
            publish_artifact(
                "ai/cache/" + key,
                {"data": parsed, "retrievedAt": observed, "sha256": digest, "sourceUrl": url},
            )
            state = {
                "status": "ready",
                "attemptedAt": stamp,
                "retrievedAt": observed,
                "sourceUrl": url,
            }
            with state_lock:
                states[key] = state
            return json.loads(json.dumps(parsed, default=str))
        except Exception as exc:
            with state_lock:
                states[key] = {
                    **old,
                    "status": "stale" if cached else "error",
                    "attemptedAt": stamp,
                    "sourceUrl": url,
                    "error": type(exc).__name__ + ": " + str(exc)[:180],
                }
            logging.getLogger(__name__).warning("AI source %s failed: %s", key, type(exc).__name__)
            return cached.get("data")

    def company_job(spec):
        ticker, cik, *_ = spec
        previous = read_artifact("ai/" + ticker)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        raw_path = hedge_board_data_root() / f"raw/equity/ai-sec/{ticker}.json"
        company = obtain(
            "sec-" + ticker, url, lambda b: build_company(json.loads(b), spec), bootstrap=raw_path
        )
        if not company:
            return previous or {
                "ticker": ticker,
                "name": spec[2],
                "sector": spec[3],
                "status": "no_data",
            }
        if company.get("methodology") != "sec-us-gaap-usd-latest-vintage-v2":
            cache = read_artifact("ai/cache/sec-" + ticker)
            archive_path = (
                hedge_board_data_root()
                / f"raw/equity/ai/sec-{ticker}/{cache['retrievedAt'][:10]}/{cache['sha256']}.bin"
            )
            company = build_company(json.loads(archive_path.read_bytes()), spec)
            cache["data"] = company
            publish_artifact("ai/cache/sec-" + ticker, cache)
            company = json.loads(json.dumps(company, default=str))

        # Reconstruct Decimal for comparisons after reading the persisted boundary.
        def checks(b, source_url, kind):
            clone = json.loads(json.dumps(company))
            for row in clone["annual"]:
                row["values"] = {
                    k: Decimal(v) if v is not None else None for k, v in row["values"].items()
                }
            return financial_checks(clone, b, source_url, kind)

        cross_checks = []
        for kind, suffix in [("income", ""), ("cash", "cash-flow-statement/")]:
            check_url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/{suffix}"
            rows = obtain(
                (kind + "-v2-" if kind == "income" else kind + "-") + ticker,
                check_url,
                lambda b, u=check_url, k=kind: checks(b, u, k),
            )
            cross_checks.extend(rows or [])
        kpi_url = (
            f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/metrics/?p=quarterly"
        )

        def parse_kpis(b):
            rows = operating_kpis(b, kpi_url)
            # Empty is a genuine coverage gap, not a made-up ARR.
            if b"<table" not in b:
                raise ValueError("Operating table missing")
            return rows

        kpis = obtain("kpi-" + ticker, kpi_url, parse_kpis)
        company["operatingKpis"] = kpis or []
        year, month, _ = map(int, company["periodEnd"].split("-"))
        primary_url = None
        if ticker == "CRM":
            fy = year + (month > 1)
            quarter = ((month - 2) % 12) // 3 + 1
            word = ["First", "Second", "Third", "Fourth"][quarter - 1]
            primary_url = f"https://investor.salesforce.com/news/news-details/{year}/Salesforce-Delivers-Record-{word}-Quarter-Fiscal-{fy}-Results/default.aspx"
        elif ticker == "MSFT":
            fy = year + (month >= 7)
            quarter = ((month - 7) % 12) // 3 + 1
            primary_url = f"https://www.microsoft.com/en-us/investor/events/fy-{fy}/earnings-fy-{fy}-q{quarter}"
        elif ticker == "META":
            word = ["First", "Second", "Third", "Fourth"][(month - 1) // 3]
            primary_url = f"https://investor.atmeta.com/investor-news/press-release-details/{year}/Meta-Reports-{word}-Quarter-{year}-Results/"
        if primary_url:
            disclosures = obtain(
                "issuer-" + ticker,
                primary_url,
                lambda b: issuer_disclosures(b, ticker, company["periodEnd"], primary_url),
            )
            company["disclosures"] = disclosures or []
        company["crossChecks"] = cross_checks
        annuals = {row["end"]: row["values"] for row in company["annual"]}
        for check in cross_checks:
            primary = annuals.get(check["date"], {}).get(check["metric"])
            if primary is not None:
                primary, secondary = Decimal(primary), Decimal(check["secondary"])
                difference = (
                    abs(primary - secondary) / abs(primary) * 100
                    if primary
                    else (Decimal(0) if not secondary else None)
                )
                check.update(
                    primary=str(primary),
                    differencePct=str(difference) if difference is not None else None,
                    status="consistent"
                    if difference is not None and difference <= 1
                    else "difference",
                )
        company["generatedAt"] = stamp
        company["sources"] = {key: states[key] for key in states if key.endswith("-" + ticker)}
        if states["sec-" + ticker]["status"] != "ready":
            company["status"] = "stale"
        publish_artifact("ai/" + ticker, company)
        return company

    def safe_company_job(spec):
        try:
            return company_job(spec)
        except Exception as exc:
            logging.getLogger(__name__).exception("AI company %s failed", spec[0])
            with state_lock:
                states["producer-" + spec[0]] = {
                    "status": "error",
                    "attemptedAt": stamp,
                    "error": type(exc).__name__,
                }
            previous = read_artifact("ai/" + spec[0])
            return {
                **previous,
                "ticker": spec[0],
                "name": spec[2],
                "sector": spec[3],
                "status": "stale" if previous else "no_data",
            }

    with ThreadPoolExecutor(max_workers=2) as pool:
        companies = list(pool.map(safe_company_job, COMPANIES))
    cds = []
    for ticker, slug in [("ORCL", "oracle"), ("NVDA", "nvda")]:
        url = f"https://charts.allofthesewords.com/{slug}-cds-data.json"
        item = obtain(
            "cds-" + ticker, url, lambda b, t=ticker: reported_cds(json.loads(b), t), hours=4
        )
        if item:
            cds.append({**item, "health": states["cds-" + ticker]})
    by_ticker = {c["ticker"]: c for c in companies}
    hyperscalers = ["MSFT", "AMZN", "GOOGL", "META"]
    series = {t: {r["end"]: r for r in by_ticker[t].get("quarters", [])} for t in hyperscalers}
    common = set.intersection(*(set(v) for v in series.values()))
    history = []
    for end in sorted(common):
        rows = [series[t][end] for t in hyperscalers]
        if len({r["start"] for r in rows}) != 1:
            continue
        point = {"date": end}
        for ticker, row in zip(hyperscalers, rows, strict=True):
            point[ticker] = row["values"].get("capex")
        for metric in ("capex", "cfo", "revenue"):
            values = [r["values"].get(metric) for r in rows]
            point[metric] = (
                str(sum((Decimal(v) for v in values), Decimal(0)))
                if all(v is not None for v in values)
                else None
            )
        point["fcf"] = (
            str(Decimal(point["cfo"]) - Decimal(point["capex"]))
            if point["cfo"] is not None and point["capex"] is not None
            else None
        )
        history.append(point)
    payload = {
        "status": "ready"
        if all(c.get("status") == "ready" for c in companies)
        and all(s["status"] == "ready" for s in states.values())
        else "partial",
        "generatedAt": stamp,
        "companies": [summary(c) for c in companies],
        "capexHistory": history,
        "cds": cds,
        "metricDefinitions": {
            "capex": (
                "报表现金购建资产支出；ProductiveAssets包含软件/无形资产。"
                "公司整体投入，不等同于纯AI开支。"
            ),
            "fcf": "经营现金流减现金资本开支；不含融资租赁非现金新增资产。",
            "arr": "ARR、收入年化运行率与RPO口径不同，分别展示，不相加。",
            "period": (
                "季度按真实财报起止日；累计现金流以相邻累计值相减。TTM仅合计四个连续完整季度。"
            ),
            "vintage": "历史采用最新已申报版本，可能包含重述，不作为时点回测数据。",
        },
    }
    publish_artifact("ai/summary", payload)
    publish_artifact("ai/health", {"generatedAt": stamp, "sources": states})
    write_local_json(f"history/research/ai/{stamp[:10]}/summary.json", payload)
    return payload["status"]


async def run_periodic():
    while True:
        try:
            await asyncio.to_thread(refresh)
        except Exception:
            logging.getLogger(__name__).exception("AI industry producer failed")
        await asyncio.sleep(300)
