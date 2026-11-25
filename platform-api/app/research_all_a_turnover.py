"""Same-universe intraday turnover snapshots and historical-progress forecasts."""

import asyncio
import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx

from app.data_audit_calendar import cached_sessions
from app.research_equity_metrics import number
from app.research_local_data import read_local_json, write_local_json
from app.research_provider_a_share import (
    _EM_ALL_A_FILTER,
    _HTTP_SSL_CONTEXT,
    _eastmoney_clist,
)
from app.research_provider_errors import ResearchProviderError

PATH = "public/v1/a-share/intraday-turnover.json"
CHINA = ZoneInfo("Asia/Shanghai")
YI = Decimal(100000000)
SOURCE = "东方财富沪深北A股延迟行情汇总（约15分钟延迟）"
# f292 semantics are published by quote.eastmoney.com/newstatic/build/vendor.js:
# 6 suspended, 7 delisted, 8 listing suspended, 9 not listed, 14 intraday suspension.
STOCK = re.compile(r"(?:[036]\d{5}|(?:43|83|87|88|92)\d{4})\Z")


def read_archive():
    try:
        return read_local_json(PATH)
    except ResearchProviderError as exc:
        if str(exc).startswith("local_data_not_found:"):
            return {"days": {}}
        raise


def aggregate(rows, now, *, final=False):
    """Require complete pagination; only explicit non-trading statuses explain blanks."""
    seen, stamps, total, suspended, markets = set(), [], Decimal(0), 0, set()
    included = 0
    for row in rows:
        code = str(row["f12"])
        if code in seen:
            raise ValueError("duplicate_security")
        seen.add(code)
        if not STOCK.fullmatch(code) or row.get("f292") in {7, 9, 15}:
            continue
        included += 1
        stamp = datetime.fromtimestamp(int(row["f124"]), CHINA)
        if stamp.date() != now.date():
            raise ValueError("mixed_quote_dates")
        value = number(row.get("f6"))
        if value is None and row.get("f292") in {6, 8} and row.get("f5") in {"-", 0}:
            suspended += 1
            continue
        if value is None or value < 0:
            raise ValueError("missing_stock_amount:" + code)
        total += value
        if value > 0:
            if final and (stamp.strftime("%H:%M") < "15:00" or row.get("f292") not in {5, 13}):
                raise ValueError("close_not_confirmed")
            stamps.append(stamp)
            markets.add("sh" if code.startswith("6") else "sz" if code[0] in "03" else "bj")
    if markets != {"sh", "sz", "bj"} or not stamps:
        raise ValueError("incomplete_market_coverage")
    first, last = min(stamps), max(stamps)
    if last > now:
        raise ValueError("future_quote")
    if final and now.strftime("%H:%M") < "16:15":
        raise ValueError("close_window_not_open")
    if not final and (
        (last - first).total_seconds() > 90 or not 0 <= (now - last).total_seconds() <= 1200
    ):
        raise ValueError("unaligned_or_stale_quotes")
    slot = "close" if final else last.strftime("%H:%M")
    if not final and not ("09:35" <= slot <= "11:30" or "13:05" <= slot <= "15:00"):
        raise ValueError("outside_regular_session")
    return {
        "slot": slot,
        "amountYi": str(total / YI),
        "asOf": last.isoformat(),
        "retrievedAt": now.isoformat(),
        "firstQuoteAt": first.isoformat(),
        "securityCount": included,
        "suspendedCount": suspended,
        "source": SOURCE,
    }


async def collect():
    params = {
        "pz": "100",
        "po": "0",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": "f12",
        "fs": _EM_ALL_A_FILTER,
        "fields": "f12,f13,f6,f5,f124,f292",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html#hs_a_board",
    }
    async with httpx.AsyncClient(timeout=15, trust_env=False, verify=_HTTP_SSL_CONTEXT) as client:

        async def page(index):
            data = (await _eastmoney_clist(client, {**params, "pn": str(index)}, headers))["data"]
            rows = data.get("diff") or []
            return int(data["total"]), list(rows.values()) if isinstance(rows, dict) else rows

        total, rows = await page(1)
        pages = (total + 99) // 100
        if total < 4500 or pages > 100:
            raise ValueError("unexpected_universe_size")
        for start in range(2, pages + 1, 3):
            for count, part in await asyncio.gather(
                *(page(i) for i in range(start, min(start + 3, pages + 1)))
            ):
                if count != total:
                    raise ValueError("universe_changed_during_pagination")
                rows.extend(part)
        if len(rows) != total:
            raise ValueError("incomplete_pagination")
    return rows


def store(rows, now, *, final=False):
    point = aggregate(rows, now, final=final)
    archive = read_archive()
    day = now.date().isoformat()
    points = archive.setdefault("days", {}).setdefault(day, {})
    earlier = [p for s, p in points.items() if s < point["slot"]]
    if earlier and number(point["amountYi"]) < max(number(p["amountYi"]) for p in earlier):
        raise ValueError("cumulative_amount_regressed")
    old = points.get(point["slot"])
    if old and (point["asOf"] < old["asOf"] or number(point["amountYi"]) < number(old["amountYi"])):
        raise ValueError("quote_regressed")
    points[point["slot"]] = point
    archive.update(status="ready", attemptedAt=now.isoformat(), error=None)
    write_local_json(PATH, archive)


def project(archive, sessions, now):
    days = archive.get("days", {})
    day = max(days, default=None)
    rows = []
    past = sorted(set(d for d in sessions if day and d < day))
    for slot, point in sorted(days.get(day, {}).items()):
        current = number(point["amountYi"])
        result = {**point, "estimate5Yi": None, "estimate20Yi": None, "samples5": 0, "samples20": 0}
        for window in (5, 20):
            requested = past[-window:]
            ratios = []
            for historical in requested:
                history = days.get(historical, {})
                at = number(history.get(slot, {}).get("amountYi"))
                close = number(history.get("close", {}).get("amountYi"))
                if at is not None and close is not None and 0 < at <= close:
                    ratios.append(at / close)
            result[f"samples{window}"] = len(ratios)
            if len(ratios) == window and slot != "close":
                progress = sum(ratios, Decimal(0)) / window
                result[f"estimate{window}Yi"] = str(current / progress)
        rows.append(result)
    latest = rows[-1] if rows else None
    expected = max((d for d in sessions if d <= now.date().isoformat()), default=None)
    stale = not latest or day != expected
    if latest and not stale and latest["slot"] != "close":
        # Lunch-break snapshots remain valid until afternoon trading resumes.
        clock = now.strftime("%H:%M")
        lunch = latest["slot"] == "11:30" and "11:30" <= clock <= "13:20"
        stale = not lunch and (now - datetime.fromisoformat(latest["asOf"])).total_seconds() > 1200
    status = (
        ("failed" if archive.get("status") == "failed" else "no_data")
        if not latest
        else "stale"
        if stale or archive.get("status") == "failed"
        else "closed"
        if latest["slot"] == "close"
        else "ready"
        if latest["estimate5Yi"] is not None
        else "partial"
    )
    paths = {
        r["slot"]: {
            "slot": r["slot"],
            "amountYi": r["amountYi"],
            "forecast5Yi": None,
            "forecast20Yi": None,
        }
        for r in rows
    }
    if latest and status in {"ready", "partial"}:
        anchor = latest["slot"]
        for window in (5, 20):
            if latest[f"estimate{window}Yi"] is None:
                continue
            histories = [days[d] for d in past[-window:]]
            future_slots = sorted({s for h in histories for s in h if s > anchor})
            paths[anchor][f"forecast{window}Yi"] = latest["amountYi"]
            previous = number(latest["amountYi"])
            for slot in future_slots:
                ratios = []
                for history in histories:
                    at = number(history.get(slot, {}).get("amountYi"))
                    close = number(history.get("close", {}).get("amountYi"))
                    before = number(history.get(anchor, {}).get("amountYi"))
                    if at is not None and close is not None and before <= at <= close:
                        ratios.append(at / close)
                value = None
                if len(ratios) == window:
                    predicted = (
                        number(latest[f"estimate{window}Yi"]) * sum(ratios, Decimal(0)) / window
                    )
                    if predicted >= previous:
                        value, previous = str(predicted), predicted
                path = paths.setdefault(
                    slot,
                    {"slot": slot, "amountYi": None, "forecast5Yi": None, "forecast20Yi": None},
                )
                path[f"forecast{window}Yi"] = value
    return {
        "date": day,
        "rows": rows,
        "latest": latest,
        "paths": [paths[s] for s in sorted(paths)],
        "source": SOURCE,
        "status": status,
        "error": archive.get("error"),
        "baselineDays": len(past[-20:]),
    }


def read_forecast():
    now = datetime.now(CHINA)
    return project(read_archive(), cached_sessions(now.date().isoformat()), now)


async def refresh():
    now = datetime.now(CHINA)
    trading_day = now.date().isoformat() in cached_sessions(now.date().isoformat())
    clock = now.strftime("%H:%M")
    final = (
        "16:15" <= clock <= "16:30"
        and trading_day
        and "close" not in read_archive().get("days", {}).get(now.date().isoformat(), {})
    )
    intraday = trading_day and ("09:50" <= clock <= "11:50" or "13:20" <= clock <= "15:10")
    if not (final or intraday):
        return "outside_window"
    rows = await collect()
    store(rows, datetime.now(CHINA), final=final)
    return "ready"


async def run_periodic():
    while True:
        try:
            await refresh()
        except Exception as exc:
            logging.getLogger(__name__).exception("All-A turnover collection failed")
            try:
                archive = read_archive()
                archive.update(
                    status="failed", attemptedAt=datetime.now(UTC).isoformat(), error=str(exc)[:160]
                )
                write_local_json(PATH, archive)
            except Exception:
                # Preserve an unreadable archive for repair rather than replacing history.
                logging.getLogger(__name__).exception("All-A turnover archive unavailable")
        # Offset the five-minute boundary slightly so upstream quotes have arrived.
        clock = datetime.now(UTC).timestamp()
        await asyncio.sleep(300 - ((clock - 20) % 300))
