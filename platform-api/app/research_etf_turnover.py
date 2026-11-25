"""Local copy of the supplied ETF turnover board; HTTP reads never collect."""

import copy
import hashlib
import html
import json
import logging
import re
import ssl
import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import truststore

from app.research_local_data import read_local_json, write_local_json
from app.research_provider_errors import ResearchProviderError

SOURCE = "https://etf-turnover-tracker.app.workbuddy.host/?sharecode=2V35TELSL4"
SNAPSHOT = "https://etf-turnover-tracker.app.workbuddy.host/data/snapshot.js"
QUOTE = "https://qt.gtimg.cn/q="
ROOT = "public/v1/etf-turnover/"
CHINA = ZoneInfo("Asia/Shanghai")
_LOCK = threading.Lock()
FIELDS = ("price", "prev_close", "pct", "amount_yi", "amount_wan", "mktcap_yi",
          "shares", "shares_yi", "outer_lots", "inner_lots", "turnover")


def read_doc(name):
    try:
        return read_local_json(ROOT + name + ".json")
    except ResearchProviderError:
        return {}


def numeric(value):
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("nonfinite ETF observation")
    return number


def validate(data):
    datetime.strptime(data["trade_date"], "%Y%m%d")
    datetime.strptime(data["generated_at"], "%Y-%m-%d %H:%M:%S")
    items = data["items"]
    codes = [item["code"] for item in items]
    if len(codes) != 24 or len(set(codes)) != 24:
        raise ValueError("expected 24 distinct reference ETFs")
    if sum(item["group"] == "core" for item in items) != 20 or sum(item["group"] == "watch" for item in items) != 4:
        raise ValueError("reference groups changed")
    for item in items:
        if not re.fullmatch(r"\d{6}", item["code"]) or item["tcode"] not in ("sh"+item["code"], "sz"+item["code"]):
            raise ValueError("invalid ETF identity")
        for key in (*FIELDS, "avg20_yi"):
            numeric(item[key])
        for key in ("huijin_yi", "tail_ratio", "tail_ratio_base", "subscr_net_yi", "prev_shares"):
            if item.get(key) is not None:
                numeric(item[key])
        if numeric(item["avg20_yi"]) <= 0 or numeric(item["amount_yi"]) < 0:
            raise ValueError("invalid turnover baseline")
        stamps = [entry[0] for entry in item["shape"]]
        ratios = [numeric(entry[1]) for entry in item["shape"]]
        for stamp in stamps:
            datetime.strptime(stamp, "%H:%M")
        if len(stamps) != 48 or stamps != sorted(set(stamps)) or ratios != sorted(ratios) or ratios[0] < 0 or ratios[-1] != 1:
            raise ValueError("invalid intraday distribution")
        dates = [entry["date"] for entry in item["hist"]]
        if len(dates) < 20 or dates != sorted(set(dates)):
            raise ValueError("invalid turnover history")
        for entry in item["hist"]:
            datetime.strptime(entry["date"], "%Y-%m-%d")
            if numeric(entry["amount_yi"]) < 0:
                raise ValueError("negative turnover")
    for day, values in data["shares_history"].items():
        datetime.strptime(day, "%Y%m%d")
        for code, value in values.items():
            if code not in codes or (value is not None and numeric(value) < 0):
                raise ValueError("invalid historical shares")
    return data


def parse_snapshot(text):
    match = re.fullmatch(r"\s*window\.SNAPSHOT\s*=\s*(\{.*\})\s*;?\s*", text, re.S)
    if not match:
        raise ValueError("expected a JSON assignment, not executable source")
    return validate(json.loads(match[1]))


def parse_quotes(text, symbols):
    rows = {}
    for symbol, body in re.findall(r'v_((?:sh|sz)\d{6})="([^"]*)"', text):
        parts = body.split("~")
        if symbol not in symbols or symbol in rows or len(parts) <= 72 or parts[2] != symbol[2:]:
            raise ValueError("quote identity mismatch")
        stamp = datetime.strptime(parts[30], "%Y%m%d%H%M%S")
        values = {key: str(numeric(parts[index])) for key, index in (
            ("price", 3), ("prev_close", 4), ("outer_lots", 7), ("inner_lots", 8),
            ("pct", 32), ("amount_wan", 37), ("turnover", 38), ("mktcap_yi", 45), ("shares", 72))}
        if any(numeric(values[key]) < 0 for key in ("price", "amount_wan", "shares", "outer_lots", "inner_lots")):
            raise ValueError("negative quote observation")
        values.update(amount_yi=str(numeric(values["amount_wan"])/10000),
                      shares_yi=str(numeric(values["shares"])/100000000), ts=parts[30], date=stamp.strftime("%Y%m%d"))
        rows[symbol] = values
    if set(rows) != set(symbols) or len({row["date"] for row in rows.values()}) != 1:
        raise ValueError("incomplete or mixed-day quote basket")
    return rows


def archive(kind, response, observed):
    digest = hashlib.sha256(response.content).hexdigest()
    write_local_json(f"raw/research/etf-turnover/{kind}/{digest}.json", {
        "sourceUrl": str(response.url), "retrievedAt": observed,
        "sha256": digest, "encoding": "gbk" if kind == "quotes" else "utf-8",
        "rawText": response.content.decode("gbk" if kind == "quotes" else "utf-8"),
    })
    return digest


def due(doc, now, seconds):
    return not doc.get("attemptedAt") or now - datetime.fromisoformat(doc["attemptedAt"]) >= timedelta(seconds=seconds)


def refresh(force=False):
    if not _LOCK.acquire(False):
        return "busy"
    try:
        from app.research_etf_observation import _trading_window
        now = datetime.now(UTC)
        observed = now.isoformat()
        baseline, live = read_doc("baseline"), read_doc("live")
        with httpx.Client(timeout=25, follow_redirects=True,
                          verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)) as client:
            if force or due(baseline, now, 21600 if baseline.get("status") == "ready" else 3600):
                try:
                    # The supplied share link grants normal site cookies for its data asset.
                    client.get(SOURCE).raise_for_status()
                    response = client.get(SNAPSHOT, headers={"Referer": SOURCE})
                    response.raise_for_status()
                    data = parse_snapshot(response.content.decode("utf-8"))
                    previous = baseline.get("data", {})
                    if previous and (data["trade_date"] < previous["trade_date"] or
                                     not set(previous["shares_history"]).issubset(data["shares_history"]) or
                                     {i["code"] for i in data["items"]} != {i["code"] for i in previous["items"]}):
                        raise ValueError("reference history or basket regressed")
                    baseline = {"data": data, "status": "ready", "sourceUrl": SOURCE,
                                "retrievedAt": observed, "attemptedAt": observed,
                                "sha256": archive("baseline", response, observed)}
                except Exception as exc:
                    baseline = {**baseline, "status": "stale" if baseline.get("data") else "no_data",
                                "attemptedAt": observed, "error": type(exc).__name__}
                    logging.getLogger(__name__).warning("ETF turnover baseline: %s", type(exc).__name__)
                write_local_json(ROOT+"baseline.json", baseline)
            if baseline.get("data") and (force or _trading_window(now.astimezone(CHINA))) and (force or due(live, now, 60)):
                try:
                    symbols = [item["tcode"] for item in baseline["data"]["items"]]
                    response = client.get(QUOTE + ",".join(symbols))
                    response.raise_for_status()
                    rows = parse_quotes(response.content.decode("gbk"), symbols)
                    stamp = min(row["ts"] for row in rows.values())
                    if live.get("observationTime") and stamp < live["observationTime"]:
                        raise ValueError("quote time regressed")
                    if _trading_window(now.astimezone(CHINA)) and stamp[:8] != now.astimezone(CHINA).strftime("%Y%m%d"):
                        raise ValueError("quote not from current session")
                    live = {"data": rows, "status": "ready", "sourceUrl": QUOTE,
                            "retrievedAt": observed, "attemptedAt": observed, "observationTime": stamp,
                            "sha256": archive("quotes", response, observed)}
                except Exception as exc:
                    live = {**live, "status": "stale" if live.get("data") else "no_data",
                            "attemptedAt": observed, "error": type(exc).__name__}
                    logging.getLogger(__name__).warning("ETF turnover quotes: %s", type(exc).__name__)
                write_local_json(ROOT+"live.json", live)
        return baseline.get("status", "no_data")
    finally:
        _LOCK.release()


def escape_strings(value):
    if isinstance(value, str):
        return html.escape(value)
    if isinstance(value, list):
        return [escape_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: escape_strings(item) for key, item in value.items()}
    return value


def read_turnover():
    baseline, live = read_doc("baseline"), read_doc("live")
    data = copy.deepcopy(baseline.get("data"))
    if data:
        for item in data["items"]:
            quote = live.get("data", {}).get(item["tcode"])
            if not quote or quote["date"] < item.get("date", ""):
                continue
            item.update({key: float(numeric(quote[key])) for key in FIELDS})
            item.update(ts=quote["ts"], date=quote["date"])
            if quote["date"] != data["trade_date"]:
                item["tail_ratio"] = None  # A retained close is not today's tail turnover.
            if item.get("prev_shares") and item["shares"] and item["price"]:
                item["subscr_net_yi"] = float((numeric(quote["shares"])-numeric(item["prev_shares"]))*numeric(quote["price"])/100000000)
    if live.get("status") == "ready" and live.get("observationTime"):
        from app.research_etf_observation import _trading_window
        now = datetime.now(UTC).astimezone(CHINA)
        observed = datetime.strptime(live["observationTime"], "%Y%m%d%H%M%S").replace(tzinfo=CHINA)
        if _trading_window(now) and (now-observed).total_seconds() > 300:
            live = {**live, "status": "stale"}
    return {"data": escape_strings(data), "sources": {
        name: {key: doc.get(key) for key in ("status", "sourceUrl", "retrievedAt", "attemptedAt", "sha256", "observationTime", "error")}
        for name, doc in (("baseline", baseline), ("live", live))}}
