"""Resumable, bounded collection; browser reads never contact the provider."""

import asyncio
import hashlib
import json
import logging
import re
import ssl
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx
import truststore

from app import research_mutual_fund_sources as parse
from app.research_local_data import read_local_json, write_local_json
from app.research_provider_errors import ResearchProviderError

ROOT = "public/v1/mutual-funds/"
# Owner paused this workstream and all collection on 2026-11-02.
COLLECTION_PAUSED = True
_REFRESH = threading.Lock()
_IO = threading.RLock()


def refresh_interval():
    month = datetime.now(ZoneInfo("Asia/Shanghai")).month
    return 86400 if month in {1, 3, 4, 7, 8, 10} else 604800


def read(name):
    with _IO:
        try:
            return read_local_json(ROOT + name + ".json")
        except ResearchProviderError as exc:
            if str(exc).startswith("local_data_not_found:"):
                return {}
            raise


def write(name, value):
    with _IO:
        write_local_json(ROOT + name + ".json", value)


def fetch(client, url, params=None):
    response = client.get(url, params=params)
    response.raise_for_status()
    body = response.content.decode("utf-8-sig")
    digest = hashlib.sha256(response.content).hexdigest()
    stamp = datetime.now(UTC).isoformat()
    write_local_json(
        f"raw/research/mutual-funds/{digest}.json",
        {
            "sourceUrl": str(response.url),
            "retrievedAt": stamp,
            "sha256": digest,
            "body": body,
        },
    )
    return body, {"sourceUrl": str(response.url), "retrievedAt": stamp, "sha256": digest}


def merge_periods(previous, current):
    rows = {row["date"]: row for row in previous}
    if previous and (not current or max(r["date"] for r in current) < max(rows)):
        raise ValueError("source date regressed")
    for row in current:
        old = rows.get(row["date"])
        if old and old.get("coverage") == "full" and row.get("coverage") != "full":
            continue
        rows[row["date"]] = row
    return sorted(rows.values(), key=lambda r: r["date"], reverse=True)


def collect(client, fund, year):
    code = fund["code"]
    old = read("funds/" + code)
    data = dict(old.get("data", {}))
    sources = dict(old.get("sources", {}))
    base = "https://fundf10.eastmoney.com/"
    archive = base + "FundArchivesDatas.aspx"
    jobs = [
        ("profile", base + f"jbgk_{code}.html", None, lambda b: parse.profile(b, code)),
        ("allocations", base + f"zcpz_{code}.html", None, lambda b: parse.allocations(b, code)),
        ("sizes", archive, {"type": "gmbd", "code": code}, parse.sizes),
        (
            "industries",
            "https://api.fund.eastmoney.com/f10/HYPZ/",
            {"fundCode": code, "year": year},
            lambda b: parse.industries(b, code),
        ),
        (
            "reports",
            "https://api.fund.eastmoney.com/f10/JJGG",
            {"fundcode": code, "pageIndex": 1, "pageSize": 24, "type": 3},
            lambda b: parse.reports(b, code),
        ),
    ]
    for key, url, params, parser in jobs:
        prior_source = sources.get(key, {})
        if (
            prior_source.get("status") == "ready"
            and _age(prior_source.get("retrievedAt")) < refresh_interval()
        ):
            continue
        now = datetime.now(UTC).isoformat()
        try:
            body, provenance = fetch(client, url, params)
            parsed = parser(body)
            if key in {"allocations", "sizes", "industries"}:
                parsed = merge_periods(data.get(key, []), parsed)
            data[key] = parsed
            sources[key] = {**provenance, "status": "ready", "attemptedAt": now}
        except Exception as exc:
            logging.getLogger(__name__).warning("Fund %s %s: %s", code, key, type(exc).__name__)
            sources[key] = {
                **sources.get(key, {}),
                "status": "stale" if data.get(key) else "no_data",
                "attemptedAt": now,
                "error": type(exc).__name__,
            }
    # Preserve top-ten extracts for every quarter and full June/December lists.
    current = data.get("holdings", [])
    holding_sources = []
    failed = False
    previous_source = sources.get("holdings", {})
    skip_holdings = (
        previous_source.get("status") == "ready"
        and _age(previous_source.get("retrievedAt")) < refresh_interval()
    )
    years = [] if skip_holdings else [year, year - 1]
    for holding_year in years:
        months = [6] if holding_year == year else [6, 12]
        for month in months:
            try:
                body, provenance = fetch(
                    client,
                    archive,
                    {
                        "type": "jjcc",
                        "code": code,
                        "year": holding_year,
                        "month": month,
                        "topline": 10000,
                    },
                )
                available = re.search(r"arryear\s*:\s*(\[[\d,\s]*\])", body)
                if available and holding_year not in json.loads(available[1]):
                    holding_sources.append(provenance)
                    continue
                parsed = parse.holdings(body, code)
                existing_year = [
                    r["date"] for r in current if r["date"].startswith(str(holding_year))
                ]
                if existing_year and max(r["date"] for r in parsed) < max(existing_year):
                    raise ValueError("holding date regressed")
                # A historical-year request is allowed to predate current data.
                by_date = {r["date"]: r for r in current}
                for row in parsed:
                    old_row = by_date.get(row["date"])
                    allocation = next(
                        (a for a in data.get("allocations", []) if a["date"] == row["date"]), {}
                    )
                    if not row["rows"] and allocation.get("stockPct") not in (None, "0", "0.00"):
                        failed = True
                        if old_row and old_row["rows"]:
                            continue
                    if not old_row or row["coverage"] == "full" or old_row["coverage"] != "full":
                        by_date[row["date"]] = row
                current = sorted(by_date.values(), key=lambda r: r["date"], reverse=True)
                holding_sources.append(provenance)
            except Exception as exc:
                failed = True
                logging.getLogger(__name__).warning(
                    "Fund %s holdings: %s", code, type(exc).__name__
                )
    if current:
        data["holdings"] = current
    if not skip_holdings:
        sources["holdings"] = {
            "status": ("stale" if current else "no_data") if failed else "ready",
            "attemptedAt": datetime.now(UTC).isoformat(),
            "retrievedAt": holding_sources[0]["retrievedAt"]
            if holding_sources
            else sources.get("holdings", {}).get("retrievedAt"),
            "artifacts": holding_sources or sources.get("holdings", {}).get("artifacts", []),
        }
    # Multiple source names can be aliases of one legal portfolio. The overview
    # additionally deduplicates the verified legal name.
    status = (
        "ready"
        if all(s.get("status") == "ready" for s in sources.values()) and len(sources) == 6
        else "partial"
    )
    result = {
        "fund": fund,
        "data": data,
        "sources": sources,
        "status": status,
        "attemptedAt": datetime.now(UTC).isoformat(),
    }
    write("funds/" + code, result)
    return {
        "code": code,
        "status": status,
        "attemptedAt": result["attemptedAt"],
        "latestDate": max((r["date"] for r in data.get("allocations", [])), default=None),
    }


def _age(stamp):
    return (
        (datetime.now(UTC) - datetime.fromisoformat(stamp)).total_seconds()
        if stamp
        else float("inf")
    )


def refresh_batch(limit=100):
    if COLLECTION_PAUSED:
        return "paused"
    if not _REFRESH.acquire(blocking=False):
        return "busy"
    try:
        with httpx.Client(
            timeout=20,
            follow_redirects=True,
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://fundf10.eastmoney.com/"},
        ) as client:
            universe = read("universe")
            if _age(universe.get("attemptedAt")) > 86400:
                now = datetime.now(UTC).isoformat()
                try:
                    body, provenance = fetch(
                        client, "https://fund.eastmoney.com/js/fundcode_search.js"
                    )
                    rows = parse.catalog(body)
                    universe = {"rows": rows, "status": "ready", "attemptedAt": now, **provenance}
                except Exception as exc:
                    universe = {
                        **universe,
                        "status": "stale" if universe.get("rows") else "no_data",
                        "attemptedAt": now,
                        "error": type(exc).__name__,
                    }
                write("universe", universe)
            progress = read("progress")
            states = progress.get("funds", {})
            pending = [
                f
                for f in universe.get("rows", [])
                if _age(states.get(f["code"], {}).get("attemptedAt"))
                > (
                    refresh_interval()
                    if states.get(f["code"], {}).get("status") == "ready"
                    else 3600
                )
            ]
            # Unknown funds first, then the oldest attempted record: a few
            # broken sources must not starve the rest of the universe.
            pending.sort(key=lambda f: states.get(f["code"], {}).get("attemptedAt", ""))
            with ThreadPoolExecutor(max_workers=4) as pool:
                tasks = [
                    pool.submit(collect, client, f, datetime.now(UTC).year) for f in pending[:limit]
                ]
                for i, future in enumerate(as_completed(tasks), 1):
                    result = future.result()
                    states[result["code"]] = result
                    if i % 20 == 0 or i == len(tasks):
                        write(
                            "progress",
                            {"funds": states, "attemptedAt": datetime.now(UTC).isoformat()},
                        )
            from app.research_mutual_funds import publish_overview

            publish_overview()
            return {
                "processed": min(limit, len(pending)),
                "remaining": max(0, len(pending) - limit),
            }
    finally:
        _REFRESH.release()


async def run_periodic():
    if COLLECTION_PAUSED:
        return
    while True:
        try:
            result = await asyncio.to_thread(refresh_batch)
            delay = 5 if isinstance(result, dict) and result["remaining"] else 3600
        except Exception:
            logging.getLogger(__name__).exception("Mutual fund collection failed")
            delay = 300
        await asyncio.sleep(delay)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(refresh_batch(args.limit), ensure_ascii=False))
