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
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

import httpx
import truststore

from app.research_local_data import local_json_revision, read_local_json, write_local_json
from app.research_provider_errors import ResearchProviderError

SOURCE = "https://etf-fund-flow-board.app.workbuddy.host/"
MINUTE_SOURCE = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
TRENDS_SOURCE = "https://push2his.eastmoney.com/api/qt/stock/trends2/get"
QUOTE_SOURCE = "https://qt.gtimg.cn/q="
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
    "sh510330",
    "sh510180",
    "sh512500",
    "sz159629",
    "sz159977",
)
INTRADAY_INDEX = "sh000300"
LIVE_SYMBOLS = (INTRADAY_INDEX, *SYMBOLS[1:])
_LOCK = threading.Lock()
_READ_LOCK = threading.Lock()
_READ_CACHE = None
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
    if len(initial["table"]) != len(SYMBOLS) - 1 or {row["code"] for row in initial["table"]} != {
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


def trends_request(symbol, datalen):
    return TRENDS_SOURCE, {
        "secid": ("1." if symbol.startswith("sh") else "0.") + symbol[2:],
        "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "ndays": 1 if datalen <= 260 else 5, "iscr": 0,
    }


def minute_request(symbol, datalen):
    # Sina omits no-trade minutes for this ETF; Eastmoney explicitly publishes
    # their original zero turnover. Never infer zero from an absent minute.
    if symbol == "sh510180":
        return trends_request(symbol, datalen)
    return MINUTE_SOURCE, {"symbol": symbol, "scale": 1, "ma": "no", "datalen": datalen}


def minute_response(symbol, payload):
    if symbol != "sh510180":
        return payload
    return trends_response(symbol, payload)


def trends_response(symbol, payload):
    data = payload.get("data") or {}
    if data.get("code") != symbol[2:] or data.get("market") != (1 if symbol.startswith("sh") else 0):
        raise ValueError("ETF minute identity mismatch")
    rows = [
        {"day": fields[0] + ":00", "close": fields[2], "amount": fields[6]}
        for fields in (row.split(",") for row in data.get("trends", []))
    ]
    # Sina's 09:31 interval includes opening-auction turnover. Eastmoney
    # publishes it at 09:30 separately; align the same observed cash interval.
    opening = {r["day"][:10]: r["amount"] for r in rows if r["day"][11:16] == "09:30"}
    for row in rows:
        if row["day"][11:16] == "09:31" and row["day"][:10] in opening:
            row["amount"] = str(_number(row["amount"]) + _number(opening.pop(row["day"][:10])))
    if opening:
        raise ValueError("opening-auction minute cannot be aligned")
    return [r for r in rows if r["day"][11:16] != "09:30"]


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


def minute_coverage(rows):
    from app.research_etf_cumulative import MINUTES

    through = rows[-1]["day"][11:16]
    required = [slot for slot in MINUTES if slot <= through and slot not in {"14:58", "14:59"}]
    observed = {r["day"][11:16] for r in rows}
    missing = sorted(set(required) - observed)
    return {"date": rows[-1]["day"][:10], "through": through,
            "expected": len(required), "covered": len(required) - len(missing), "missingTimes": missing}


def collect_minutes(client, symbol, observed):
    """Select one complete original feed per fund, never stitch or infer zero bars."""
    url, params = minute_request(symbol, 260)
    response = client.get(url, params=params)
    response.raise_for_status()
    parsed = parse_minutes(minute_response(symbol, response.json()))
    _archive(symbol, response, observed)
    coverage = {**minute_coverage(parsed), "sourceUrl": str(response.url), "recovered": False}
    if coverage["missingTimes"] and url != TRENDS_SOURCE:
        try:
            supplement_url, supplement_params = trends_request(symbol, 260)
            supplement = client.get(supplement_url, params=supplement_params)
            supplement.raise_for_status()
            _archive(symbol, supplement, observed)
            candidate = parse_minutes(trends_response(symbol, supplement.json()))
            checked = minute_coverage(candidate)
            if (checked["date"] != coverage["date"] or checked["through"] < coverage["through"]
                    or checked["missingTimes"]):
                raise ValueError("supplemental minute session incomplete or mismatched")
            parsed = candidate
            coverage = {**checked, "sourceUrl": str(supplement.url), "recovered": True,
                        "primaryMissingTimes": coverage["missingTimes"]}
        except Exception as exc:
            # Keep the actual bars visible and report the gap; do not certify them complete.
            coverage["recoveryError"] = type(exc).__name__ + ": " + str(exc)[:160]
    return symbol, parsed, coverage


def parse_quotes(text: str) -> dict:
    """Normalize Tencent native quotes; turnover is published in 10,000 CNY."""
    rows = []
    for symbol, body in re.findall(r'v_((?:sh|sz)\d{6})="([^"\r\n]*)";', text):
        values = body.split("~")
        if len(values) < 38 or values[2] != symbol[2:]:
            raise ValueError("invalid Tencent ETF quote")
        stamp = datetime.strptime(values[30], "%Y%m%d%H%M%S")
        if re.search(r"[<>&\"\x27]", values[1]):
            raise ValueError("unsafe quote name")
        price, previous = _number(values[3]), _number(values[4])
        amount = _number(values[37]) * Decimal(10000)
        if price <= 0 or previous <= 0 or amount < 0:
            raise ValueError("invalid Tencent ETF price or turnover")
        rows.append(
            {
                "f12": values[2],
                "f14": values[1],
                "f2": str(price),
                "f3": str(_number(values[32])),
                "f6": str(amount),
                "f18": str(previous),
                "observedAt": stamp.isoformat(),
            }
        )
    if len(rows) != len(LIVE_SYMBOLS) or {row["f12"] for row in rows} != {s[2:] for s in LIVE_SYMBOLS}:
        raise ValueError("incomplete ETF quote basket")
    return {"data": {"diff": rows}}


def _archive(name, response, now):
    digest = hashlib.sha256(response.content).hexdigest()
    encoding = "gbk" if response.url.host == "qt.gtimg.cn" else "utf-8"
    write_local_json(
        f"raw/research/etf-observation/{name}/{digest}.json",
        {
            "sourceUrl": str(response.url),
            "observedAt": now,
            "sha256": digest,
            "body": response.content.decode(encoding),
            "encoding": encoding,
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
            "errorDetail": str(exc)[:240],
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
            if force or not _recent(old, now, 300 if old.get("status") == "ready" else 60):
                try:
                    from app.research_etf_native import build_reference
                    from app.research_etf_native import read as read_native

                    data = build_reference(old.get("data", {}), SYMBOLS)
                    state = read_native("refresh")
                    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
                    write_local_json(
                        ROOT + "reference.json",
                        {
                            "data": data,
                            "sourceUrl": "https://query.sse.com.cn/commonQuery.do",
                            "sourceLabel": "沪深交易所份额 / 基金单位净值 / 东方财富日行情",
                            "inputRetrievedAt": state["retrievedAt"],
                            "nativeFrom": data.get("nativeFrom"),
                            "sha256": digest,
                            "status": "ready"
                            if data["dailyData"]["netflow"][-1] is not None
                            and data["dailyData"]["amount"][-1] is not None
                            and data["broadData"]["total"][-1] is not None
                            and data.get("nativeStatus", "ready") == "ready"
                            else "partial",
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
            if not force and set(old.get("data", {}).get("klines", {})) == set(LIVE_SYMBOLS) and _recent(
                old, now, 60 if trading else (21600 if old.get("status") == "ready" else 300)
            ) and set(old.get("minuteCoverage", {})) == set(LIVE_SYMBOLS):
                return "cached"
            try:
                minutes, minute_checks = {}, {}
                with ThreadPoolExecutor(max_workers=6) as pool:
                    for future in as_completed(
                        [pool.submit(collect_minutes, client, symbol, observed) for symbol in LIVE_SYMBOLS]
                    ):
                        symbol, rows, coverage = future.result()
                        minutes[symbol] = rows
                        minute_checks[symbol] = coverage
                days = {rows[-1]["day"][:10] for rows in minutes.values()}
                if len(days) != 1:
                    raise ValueError("ETF minute source dates disagree")
                latest = min(rows[-1]["day"] for rows in minutes.values())
                latest_time = datetime.strptime(latest, "%Y-%m-%d %H:%M:%S").replace(tzinfo=_CHINA)
                if (
                    trading
                    and local.time() >= time(9, 35)
                    and (local - latest_time).total_seconds() > 300
                ):
                    raise ValueError("minute_source_delayed")
                previous = old.get("data", {}).get("klines", {})
                for symbol, series in minutes.items():
                    retained = previous.get(symbol, [])
                    if retained and series[-1]["day"] < retained[-1]["day"]:
                        raise ValueError("ETF minute date regressed")
                response = client.get(QUOTE_SOURCE + ",".join(LIVE_SYMBOLS))
                response.raise_for_status()
                snapshot = parse_quotes(response.content.decode("gbk"))
                rows = snapshot.get("data", {}).get("diff", [])
                if {row.get("f12") for row in rows} != {symbol[2:] for symbol in LIVE_SYMBOLS}:
                    raise ValueError("incomplete ETF quote basket")
                for row in rows:
                    if row["observedAt"][:10] != next(iter(days)):
                        raise ValueError("quote and minute source dates disagree")
                    symbol = next(s for s in LIVE_SYMBOLS if s[2:] == row["f12"])
                    coverage = minute_checks[symbol]
                    if coverage["recovered"] and coverage["through"] == "15:00":
                        total = sum((_number(r["amount"]) for r in minutes[symbol]), Decimal(0))
                        quoted = _number(row["f6"])
                        if abs(total - quoted) > max(Decimal(10000), quoted * Decimal("0.001")):
                            raise ValueError("recovered minute total disagrees with quote: " + symbol)
                        coverage["sumAmountYuan"] = str(total)
                        coverage["quoteAmountYuan"] = str(quoted)
                    for field in ("f2", "f3", "f6", "f18"):
                        _number(row[field])
                    if re.search(r"[<>&\"\x27]", row.get("f14", "")):
                        raise ValueError("unsafe quote name")
                if next(iter(days)) < local.date().isoformat():
                    # Before the new session, quotes may have reset while minutes
                    # still belong to the previous day. Never move its close line.
                    for row in rows:
                        symbol = next(symbol for symbol in LIVE_SYMBOLS if symbol[2:] == row["f12"])
                        quote_close = _number(row["f2"])
                        minute_close = _number(minutes[symbol][-1]["close"])
                        if symbol == INTRADAY_INDEX:
                            # Tencent publishes this index to 2 decimals, Sina to 3.
                            # Compare at quote precision without altering either stored value.
                            minute_close = minute_close.quantize(
                                Decimal(1).scaleb(quote_close.as_tuple().exponent),
                                rounding=ROUND_HALF_UP,
                            )
                        if _number(row["f6"]) == 0 or quote_close != minute_close:
                            raise ValueError("quote and retained minute sessions disagree")
                _archive("quotes", response, observed)
                complete = all(not c["missingTimes"] for c in minute_checks.values())
                payload = {
                    "data": {"klines": minutes, "hq": snapshot},
                    "status": "ready" if complete else "partial",
                    "sourceUrl": MINUTE_SOURCE,
                    "minuteSourceUrls": {s: c["sourceUrl"] for s, c in minute_checks.items()},
                    "minuteCoverage": minute_checks,
                    "quoteSourceUrl": QUOTE_SOURCE,
                    "sourceLabel": "新浪／东方财富分钟行情 / 腾讯行情快照",
                    "observationTime": latest,
                    "observationDate": next(iter(days)),
                    "retrievedAt": observed,
                    "attemptedAt": observed,
                }
                write_local_json(ROOT + "live.json", payload)
                write_local_json(
                    f"history/research/etf-observation/{payload['observationDate']}.json", payload
                )
                return payload["status"]
            except Exception as exc:
                _failed("live", old, observed, exc)
                logging.getLogger(__name__).warning("ETF minutes refresh: %s", type(exc).__name__)
                return "partial"
    finally:
        _LOCK.release()


def _flow_windows(dates, flows):
    def value(raw):
        try:
            return _number(raw) if raw is not None else None
        except (ValueError, TypeError):
            return None

    parsed = [value(raw) for raw in flows] if len(dates) == len(flows) else []
    end = next((i for i in range(len(parsed) - 1, -1, -1) if parsed[i] is not None), None)
    selected = parsed[:end + 1] if end is not None else []
    return {
        "date": dates[end] if end is not None else None,
        **{key: str(sum(selected[-window:], Decimal(0)))
           if len(selected) >= window and all(v is not None for v in selected[-window:]) else None
           for key, window in (("flow1Yi", 1), ("flow5Yi", 5), ("flow20Yi", 20))},
    }


def overview_summary(reference, intraday=None):
    """Use exactly the category series shown in the broad daily chart and table."""
    if intraday is None:
        intraday = intraday_summary(reference)
    broad = reference.get("broadData", {})
    dates, cats, series = broad.get("dates", []), broad.get("cats", []), broad.get("series", {})
    aligned = bool(cats) and len(cats) == len(set(cats)) and all(
        len(series.get(cat, [])) == len(dates) for cat in cats)
    totals = []
    if aligned:
        for i in range(len(dates)):
            try:
                from app.research_etf_broad import cash_total
                totals.append(cash_total(broad, i))
            except (ValueError, TypeError):
                totals.append(None)
    result = _flow_windows(dates, totals)
    coverage = reference.get("nativeCoverage", {}).get("broad", {}).get(result["date"], {})
    count = sum(coverage[cat]["expected"] for cat in cats) if cats and all(cat in coverage for cat in cats) else 0
    return {
        **result, "basketCount": count,
        "coveredCount": sum(group.get("covered", 0) for group in coverage.values()),
        "partialDates": [day for day, groups in broad.get("coverage", {}).items()
                         if any(group.get("covered", 0) < group.get("expected", 0) for group in groups.values())],
        # A 25-fund scale/share value cannot represent the broad universe.
        "scaleYi": None, "sharesYi": None,
        **{key: intraday.get(key) for key in ("baseline", "baselineStatus", "futures")},
    }


def intraday_summary(reference):
    """Summarize the fixed daily basket and independent local futures snapshot."""
    from app.research_etf_native import read as read_native
    from app.research_national_etf import read as read_national

    def value(raw):
        try:
            return _number(raw) if raw is not None else None
        except (ValueError, TypeError):
            return None

    def complete_sum(values, count):
        parsed = [value(v) for v in values]
        if len(parsed) != count or any(v is None for v in parsed):
            return None
        return sum(parsed, Decimal(0))

    daily = reference.get("dailyData", {})
    dates, flows = daily.get("dates", []), daily.get("netflow", [])
    windows = _flow_windows(dates, flows)
    day = windows["date"]
    result = {
        **windows,
        "basketCount": len(SYMBOLS) - 1,
        "scaleYi": None,
        "sharesYi": None,
    }
    shares, scales = [], []
    for symbol in SYMBOLS[1:]:
        fund = next(
            (r for r in reversed(read_native("funds/" + symbol[2:]).get("rows", [])) if r.get("date") == day),
            {},
        )
        market = next(
            (r for r in reversed(read_native("market/" + symbol).get("rows", [])) if r.get("date") == day),
            {},
        )
        units, close = value(fund.get("shares")), value(market.get("close"))
        shares.append(units if units is not None and units >= 0 else None)
        scales.append(
            units * close
            if units is not None and units >= 0 and close is not None and close > 0
            else None
        )
    for key, values in (("sharesYi", shares), ("scaleYi", scales)):
        total = complete_sum(values, len(SYMBOLS) - 1)
        result[key] = str(total / Decimal(100000000)) if total is not None else None

    national = read_national()
    result["baseline"] = national.get("data", {}).get("baseline")
    result["baselineStatus"] = national.get("status", "no_data")
    futures = national.get("data", {}).get("futures", {})
    latest = futures.get("latest", {})
    changes = []
    for product in ("IH", "IF", "IC", "IM"):
        contracts = latest.get("contracts", {}).get(product, [])
        product_changes = []
        for contract in contracts:
            buy = value(contract[2]) if len(contract) >= 5 else None
            sell = value(contract[4]) if len(contract) >= 5 else None
            product_changes.append(sell - buy if sell is not None and buy is not None else None)
        changes.append(complete_sum(product_changes, len(contracts)) if contracts else None)
    change = complete_sum(changes, 4) if latest.get("date") else None
    result["futures"] = {
        "date": latest.get("date"),
        "member": futures.get("member", "中信期货"),
        "netShortChange": str(change) if change is not None else None,
        "status": national.get("status", "no_data"),
        "sourceUrl": national.get("sourceUrl"),
    }
    return result


def project_intraday_cases(reference, index_document):
    """Rebase the fixed case-study index from original HS300 15-minute candles."""
    typ = reference.get("typData", {})
    slots = typ.get("slots", [])
    span = typ.get("range", [])
    if not slots or len(span) != 2:
        return reference
    dates = [d for d in reference.get("dailyData", {}).get("dates", []) if span[0] <= d <= span[1]]
    special = set(typ.get("supDays", []))
    groups = {"sup": [d for d in dates if d in special], "nor": [d for d in dates if d not in special]}
    candles = {}
    if index_document.get("symbol") == INTRADAY_INDEX and index_document.get("scale") == 15:
        for row in index_document.get("rows", []):
            stamp = row.get("day", "")
            if stamp[:10] not in dates:
                continue
            try:
                datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
                opened, closed = _number(row["open"]), _number(row["close"])
                if opened <= 0 or closed <= 0:
                    continue
            except (KeyError, ValueError):
                continue
            candles.setdefault(stamp[:10], {})[stamp[11:16]] = (opened, closed)
    complete = {day: rows for day, rows in candles.items() if all(slot in rows for slot in slots)}
    paths = {}
    coverage = {}
    for name, days in groups.items():
        coverage[name] = {"expected": len(days), "available": sum(day in complete for day in days)}
        paths[name + "Idx"] = [
            float(sum(((complete[day][slot][1] / complete[day][slots[0]][0] - 1) * 100
                       for day in days), Decimal(0)) / len(days))
            if days and all(day in complete for day in days) else None
            for slot in slots
        ]
    ready = bool(dates) and all(day in complete for day in dates)
    return {**reference, "typData": {
        **typ, **paths,
        "indexSymbol": INTRADAY_INDEX,
        "indexLabel": "沪深300",
        "indexInterval": "15min",
        "indexDefinition": "15分钟收盘相对当日首区间开盘涨跌幅的跨日算术平均",
        "indexStatus": "ready" if ready else "partial" if complete else "no_data",
        "indexCoverage": coverage,
        "indexSourceUrl": index_document.get("sourceUrl"),
        "indexRetrievedAt": index_document.get("retrievedAt"),
        "indexSha256": index_document.get("sha256"),
    }}


def read_observation():
    global _READ_CACHE
    paths = [ROOT + "reference.json", ROOT + "live.json", "public/v1/national-etf/latest.json"]
    paths += ["public/v1/etf-native/" + name + ".json" for s in SYMBOLS[1:]
              for name in ("funds/" + s[2:], "market/" + s)]
    paths.append(ROOT + "case-index.json")
    revision = tuple(local_json_revision(path) for path in paths)
    with _READ_LOCK:
        if _READ_CACHE and _READ_CACHE[0] == revision:
            reference, live, summary, intraday = _READ_CACHE[1]
        else:
            reference, live = _read("reference"), _read("live")
            intraday = intraday_summary(reference.get("data", {}))
            summary = overview_summary(reference.get("data", {}), intraday)
            reference = {**reference, "data": project_intraday_cases(reference.get("data", {}), _read("case-index"))}
            if revision[0] is not None or revision[1] is not None:
                _READ_CACHE = (revision, (reference, live, summary, intraday))
    if live.get("status") == "ready" and live.get("observationTime"):
        now = datetime.now(UTC).astimezone(_CHINA)
        stamp = datetime.strptime(live["observationTime"], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=_CHINA
        )
        if (
            now.time() >= time(9, 35)
            and (now - stamp).total_seconds() > 300
            and _trading_window(now)
        ):
            live = {**live, "status": "stale", "errorDetail": "minute_source_delayed"}
    return {
        "reference": reference.get("data", {}),
        "summary": summary,
        "intradaySummary": intraday,
        "live": live.get("data", {}),
        "sources": {
            name: {
                k: doc.get(k)
                for k in (
                    "status",
                    "sha256",
                    "sourceUrl",
                    "minuteSourceUrls",
                    "quoteSourceUrl",
                    "sourceLabel",
                    "retrievedAt",
                    "attemptedAt",
                    "observationDate",
                    "observationTime",
                    "error",
                    "errorDetail",
                )
            }
            for name, doc in (("reference", reference), ("live", live))
        },
    }


async def run_periodic():
    while True:
        try:
            from app.research_national_etf import refresh as refresh_national
            await asyncio.to_thread(refresh_national)
            await asyncio.to_thread(refresh)
        except Exception:
            logging.getLogger(__name__).exception("ETF observation refresh failed")
        try:
            from app.research_etf_turnover import refresh as refresh_turnover
            await asyncio.to_thread(refresh_turnover)
        except Exception:
            logging.getLogger(__name__).exception("ETF turnover refresh failed")
        await asyncio.sleep(60)
