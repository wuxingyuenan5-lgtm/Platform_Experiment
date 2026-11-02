"""Local ETF observation artifacts. Reads never fetch remote data."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import ssl
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import httpx
import truststore

from app.research_local_data import read_local_json, write_local_json
from app.research_provider_errors import ResearchProviderError

SOURCE = "https://etf-fund-flow-board.app.workbuddy.host/"
ROOT = "public/v1/etf-observation/"
SYMBOLS = (
    "sh000001",
    "sh510310",
    "sh588000",
    "sz159915",
    "sh510300",
    "sh563360",
    "sz159352",
    "sh512100",
    "sz159338",
    "sh510500",
    "sz159949",
    "sh588080",
    "sh510050",
    "sh510210",
    "sz159845",
    "sz159952",
    "sz159361",
    "sh512050",
    "sz159633",
    "sh560010",
    "sz159919",
)
_LOCK = threading.Lock()
_CHINA = ZoneInfo("Asia/Shanghai")


def _read(name):
    try:
        return read_local_json(ROOT + name + ".json")
    except ResearchProviderError:
        return {}


def _number(value):
    try:
        result = Decimal(str(value))
        if result.is_finite():
            return result
    except (InvalidOperation, ValueError):
        pass
    raise ValueError("non-finite ETF observation")


def _dates(values):
    if not values or values != sorted(set(values)):
        raise ValueError("unordered or empty ETF dates")
    for value in values:
        datetime.strptime(value, "%Y-%m-%d")


def parse_reference(text: str) -> dict:
    """Parse the published data literal as JSON, never execute downloaded JS."""
    body = text[text.index("{") :].strip().removesuffix(";")
    body = re.sub(r"(?m)^\s*(\w+):", lambda match: json.dumps(match[1]) + ":", body)
    data = json.loads(body)
    for key in ("dailyData", "broadData"):
        _dates(data[key]["dates"])
    daily = data["dailyData"]
    for key in ("amount", "netflow", "idx"):
        if len(daily[key]) != len(daily["dates"]):
            raise ValueError("daily ETF array length mismatch")
        for value in daily[key]:
            if value is not None:
                _number(value)
    initial = data["initData"]
    if len(initial["table"]) != 20 or {row["code"] for row in initial["table"]} != {
        symbol[2:] for symbol in SYMBOLS[1:]
    }:
        raise ValueError("ETF basket identity changed")
    if len(initial["times"]) != len(initial["bars"]) or len(initial["times"]) != len(
        initial["closes"]
    ):
        raise ValueError("minute array length mismatch")
    for row in initial["table"]:
        if re.search(r"[<>&\"\x27]", row.get("name", "")):
            raise ValueError("unsafe ETF label")
    datetime.strptime(initial["date"], "%Y-%m-%d")
    for value in initial["times"]:
        datetime.strptime(value, "%H:%M")
    for field in ("bars", "closes"):
        for value in initial[field]:
            if value is not None:
                _number(value)
    for row in data["cmpData"]["support"]:
        datetime.strptime(row["date"], "%Y-%m-%d")
        for field in ("amount", "netflow"):
            _number(row[field])
    typ = data["typData"]
    for field in ("supAmt", "supIdx", "norAmt", "norIdx"):
        if len(typ[field]) != len(typ["slots"]):
            raise ValueError("case study length mismatch")
        for value in typ[field]:
            if value is not None:
                _number(value)
    cumulative = data["cumData"]
    for field in ("prev", "avg20"):
        if len(cumulative[field]) != len(cumulative["slots"]):
            raise ValueError("cumulative minute length mismatch")
        for value in cumulative[field]:
            if value is not None:
                _number(value)
    broad = data["broadData"]
    if len(broad["cats"]) != len(set(broad["cats"])) or not broad["cats"]:
        raise ValueError("invalid broad ETF categories")
    if not broad["colors"] or any(
        not re.fullmatch(r"#[0-9a-fA-F]{3,8}", color) for color in broad["colors"]
    ):
        raise ValueError("invalid broad ETF colors")
    for category in broad["cats"]:
        if re.search(r"[<>&\"\x27]", category) or len(broad["series"][category]) != len(
            broad["dates"]
        ):
            raise ValueError("invalid broad ETF array")
    for field in ("total", "totalCum"):
        if len(broad[field]) != len(broad["dates"]):
            raise ValueError("invalid broad total length")
    for i in range(len(broad["dates"])):
        values = [broad["series"][category][i] for category in broad["cats"]]
        if all(value is not None for value in values) and broad["total"][i] is not None:
            # Published categories round separately to two decimals.
            if abs(
                sum((_number(value) for value in values), Decimal(0)) - _number(broad["total"][i])
            ) > Decimal("0.1"):
                raise ValueError("broad ETF total does not reconcile")
    return data


def parse_minutes(rows) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty ETF minutes")
    parsed = []
    for row in rows:
        stamp = datetime.strptime(row["day"], "%Y-%m-%d %H:%M:%S")
        close, amount = _number(row["close"]), _number(row["amount"])
        if close <= 0 or amount < 0:
            raise ValueError("invalid minute price or turnover")
        parsed.append(
            {"day": stamp.strftime("%Y-%m-%d %H:%M:%S"), "close": str(close), "amount": str(amount)}
        )
    stamps = [row["day"] for row in parsed]
    if stamps != sorted(set(stamps)):
        raise ValueError("unordered ETF minutes")
    day = parsed[-1]["day"][:10]
    return [row for row in parsed if row["day"][:10] == day]


def _archive(name, response, now):
    digest = hashlib.sha256(response.content).hexdigest()
    write_local_json(
        f"raw/research/etf-observation/{name}/{digest}.json",
        {
            "sourceUrl": str(response.url),
            "observedAt": now,
            "sha256": digest,
            "body": response.content.decode("utf-8"),
        },
    )
    return digest


def _recent(document, now, seconds):
    try:
        return (
            0 <= (now - datetime.fromisoformat(document["attemptedAt"])).total_seconds() < seconds
        )
    except (KeyError, ValueError):
        return False


def _failed(name, old, now, exc):
    write_local_json(
        ROOT + name + ".json",
        {
            **old,
            "status": "stale" if old.get("data") else "no_data",
            "attemptedAt": now,
            "error": type(exc).__name__,
        },
    )


def _trading_window(local):
    if local.weekday() >= 5 or not (
        time(9, 15) <= local.time() <= time(11, 35) or time(12, 55) <= local.time() <= time(15, 10)
    ):
        return False
    from app.data_audit_calendar import calendar_snapshot
    from app.database_connection import read_only_connection

    with read_only_connection() as db:
        calendar = calendar_snapshot(db, local.date().isoformat())
    # A known exchange holiday must not trigger minute collection.
    return calendar is None or local.date().isoformat() in calendar["days"]


def refresh(*, force=False):
    if not _LOCK.acquire(blocking=False):
        return "busy"
    try:
        now = datetime.now(UTC)
        observed = now.isoformat()
        local = now.astimezone(_CHINA)
        trading = _trading_window(local)
        with httpx.Client(
            timeout=20, follow_redirects=True, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ) as client:
            old = _read("reference")
            if force or not _recent(old, now, 21600 if old.get("status") == "ready" else 300):
                try:
                    response = client.get(SOURCE + "data.js")
                    response.raise_for_status()
                    data = parse_reference(response.content.decode("utf-8"))
                    previous = old.get("data", {}).get("dailyData", {}).get("dates", [])
                    if previous and data["dailyData"]["dates"][-1] < previous[-1]:
                        raise ValueError("reference date regressed")
                    if previous and data["dailyData"]["dates"][0] > previous[0]:
                        raise ValueError("reference history truncated")
                    digest = _archive("reference", response, observed)
                    write_local_json(
                        ROOT + "reference.json",
                        {
                            "data": data,
                            "sourceUrl": SOURCE,
                            "sha256": digest,
                            "status": "ready",
                            "retrievedAt": observed,
                            "attemptedAt": observed,
                        },
                    )
                except Exception as exc:
                    _failed("reference", old, observed, exc)
                    logging.getLogger(__name__).warning(
                        "ETF reference refresh: %s", type(exc).__name__
                    )
            old = _read("live")
            if not force and _recent(
                old, now, 60 if trading else (21600 if old.get("status") == "ready" else 300)
            ):
                return "cached"
            try:

                def collect(symbol):
                    response = client.get(
                        SOURCE + "api/kline", params={"symbol": symbol, "scale": 1, "datalen": 260}
                    )
                    response.raise_for_status()
                    parsed = parse_minutes(response.json())
                    _archive(symbol, response, observed)
                    return symbol, parsed

                minutes = {}
                with ThreadPoolExecutor(max_workers=6) as pool:
                    for future in as_completed(
                        [pool.submit(collect, symbol) for symbol in SYMBOLS]
                    ):
                        symbol, rows = future.result()
                        minutes[symbol] = rows
                days = {rows[-1]["day"][:10] for rows in minutes.values()}
                if len(days) != 1:
                    raise ValueError("ETF minute source dates disagree")
                response = client.get(SOURCE + "api/hq", params={"codes": ",".join(SYMBOLS)})
                response.raise_for_status()
                snapshot = response.json()
                rows = snapshot.get("data", {}).get("diff", [])
                if {row.get("f12") for row in rows} != {symbol[2:] for symbol in SYMBOLS}:
                    raise ValueError("incomplete ETF quote basket")
                for row in rows:
                    for field in ("f2", "f3", "f6", "f18"):
                        _number(row[field])
                    if re.search(r"[<>&\"\x27]", row.get("f14", "")):
                        raise ValueError("unsafe quote name")
                if next(iter(days)) < local.date().isoformat():
                    # Before the new session, quotes may have reset while minutes
                    # still belong to the previous day. Never move its close line.
                    for row in rows:
                        symbol = next(symbol for symbol in SYMBOLS if symbol[2:] == row["f12"])
                        if _number(row["f6"]) == 0 or _number(row["f2"]) != _number(
                            minutes[symbol][-1]["close"]
                        ):
                            raise ValueError("quote and retained minute sessions disagree")
                _archive("quotes", response, observed)
                payload = {
                    "data": {"klines": minutes, "hq": snapshot},
                    "status": "ready",
                    "sourceUrl": SOURCE,
                    "observationDate": next(iter(days)),
                    "retrievedAt": observed,
                    "attemptedAt": observed,
                }
                write_local_json(ROOT + "live.json", payload)
                write_local_json(
                    f"history/research/etf-observation/{payload['observationDate']}.json", payload
                )
                return "ready"
            except Exception as exc:
                _failed("live", old, observed, exc)
                logging.getLogger(__name__).warning("ETF minutes refresh: %s", type(exc).__name__)
                return "partial"
    finally:
        _LOCK.release()


def read_observation():
    reference, live = _read("reference"), _read("live")
    return {
        "reference": reference.get("data", {}),
        "live": live.get("data", {}),
        "sources": {
            name: {k: doc.get(k) for k in ("status", "sourceUrl", "retrievedAt", "observationDate")}
            for name, doc in (("reference", reference), ("live", live))
        },
    }


async def run_periodic():
    while True:
        try:
            await asyncio.to_thread(refresh)
        except Exception:
            logging.getLogger(__name__).exception("ETF observation refresh failed")
        await asyncio.sleep(60)
