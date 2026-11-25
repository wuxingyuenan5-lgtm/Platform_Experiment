"""Choice CSS month-end backfill and daily close updates for the A-share valuation tables."""

import json
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.research_choice_index_catalog import CSS_INDEX_SPECS
from app.research_equity_metrics import number

FIELDS = {
    "CLOSE": "close",
    "PETTM": "pe",
    "PELYR": "peLyr",
    "PBMRQ": "pb",
    "PSTTM": "ps",
    "DIVIDENDRATETTM": "dividend",
}
OPTIONS = "DelType=1,AdjustFlag=1,Ispandas=1"
URL = "https://quantapi.eastmoney.com/"
SHANGHAI = ZoneInfo("Asia/Shanghai")

CSS_CHILD = r"""
import json,sys
from datetime import date,datetime,timedelta,timezone
import pandas as pd
from EmQuantAPI import c

cfg=json.loads(sys.argv[1])
result={"batches":[],"failures":{}}
def iso(day):
    return date(*map(int,str(day).replace('/','-').split('-'))).isoformat()
try:
    login=c.start()
    if login.ErrorCode: raise RuntimeError(str(login.ErrorCode))
    end=date.fromisoformat(cfg['end'])
    for market in sorted({p['market'] for p in cfg['requests']}):
        entries=[p for p in cfg['requests'] if p['market']==market]
        try:
            days=c.tradedates(str(end-timedelta(days=35)),str(end),"Market="+market)
            if days.ErrorCode: raise RuntimeError(str(days.ErrorCode))
            calendars=sorted(iso(d) for d in days.Dates)
            if not calendars: raise RuntimeError("empty exchange calendar")
            latest=calendars[-1]
            month_last={}
            for day in calendars: month_last[day[:7]]=day
            for day in sorted(set(month_last.values())):
                symbols=[p["symbol"] for p in entries if day not in p["dates"] and (day==latest or p["latest"])]
                for i in range(0,len(symbols),45):
                    codes=symbols[i:i+45]
                    opts="TradeDate="+day+","+cfg['options']
                    frame=c.css(",".join(codes),",".join(cfg['fields']),opts)
                    if not isinstance(frame,pd.DataFrame):
                        for code in codes: result['failures'][code]=str(frame.ErrorCode)
                        if frame.ErrorCode==10001029: raise RuntimeError(str(frame.ErrorCode))
                        continue
                    for f in cfg['fields']: frame[f]=pd.to_numeric(frame[f],errors="coerce")
                    available = frame[cfg['fields'][1:]].notna().any(axis=1)
                    for code in set(codes)-set(frame.index[available]):
                        result["failures"][code]="no valuation data"
                    result["batches"].append(dict(day=day,codes=codes,options=opts,fields=cfg['fields'],
                        fetchedAt=datetime.now(timezone.utc).isoformat(),
                        response=json.loads(frame.reset_index().to_json(orient="records",double_precision=12))))
        except Exception as exc:
            for p in entries: result["failures"].setdefault(p["symbol"],str(exc))
            if "10001029" in str(exc): break
except Exception as exc:
    for p in cfg['requests']: result["failures"][p["symbol"]]=str(exc)
finally:
    c.stop()
print(json.dumps(result,allow_nan=False))
"""


def source_key(code):
    return "choice_index_" + code


def parse_css_batch(batch):
    """Check identity and trade date before allowing dated CSS observations into the archive."""
    expected = date.fromisoformat(batch["day"]).isoformat()
    requested = set(batch["codes"])
    seen = set()
    for raw in batch["response"]:
        symbol = raw["CODES"]
        day = date(*(int(part) for part in str(raw["DATES"]).replace("/", "-").split("-"))).isoformat()
        if symbol not in requested or day != expected or symbol in seen:
            raise ValueError(f"Choice CSS unexpected response identity {symbol} {day}")
        seen.add(symbol)
        record = {field: number(raw.get(indicator)) for indicator, field in FIELDS.items()}
        close = record["close"]
        if close is not None and close > 0 and any(v is not None for k, v in record.items() if k != "close"):
            yield symbol, {"date": day, **{k: str(v) for k, v in record.items() if v is not None}}


def publish_css_batches(documents, batches, failures=None):
    from app.research_equity_sources import archive, publish_artifact

    failures = failures or {}
    updates = {}
    provenance = {}
    for batch in batches:
        rows = dict(parse_css_batch(batch))
        digest = archive(
            "choice_index_valuation_css",
            json.dumps(batch, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            batch["fetchedAt"],
        )
        for symbol, row in rows.items():
            updates.setdefault(symbol, {})[row["date"]] = row
            provenance[symbol] = (batch["fetchedAt"], digest)

    now = datetime.now(UTC).isoformat()
    for code, name, symbol, _ in CSS_INDEX_SPECS:
        if symbol not in updates and symbol not in failures:
            continue
        key = source_key(code)
        old = documents.get(key, {})
        merged = {row["date"]: dict(row) for row in old.get("rows", [])}
        for day, row in updates.get(symbol, {}).items():
            merged.setdefault(day, {}).update(row)
        doc = {
            **old,
            "id": key,
            "name": f"Choice / {name} · CSS",
            "url": URL,
            "choiceSymbol": symbol,
            "acquisitionMethod": "choice_css",
            "rankFrequency": "month",
            "rows": [merged[d] for d in sorted(merged)],
            "attemptedAt": now,
            "status": "stale" if symbol in failures and merged else "error" if symbol in failures else "ready",
            "error": failures.get(symbol),
        }
        if symbol in provenance:
            doc["observationDate"] = max(merged)
            doc["fetchedAt"], doc["rawSha256"] = provenance[symbol]
        publish_artifact("sources/" + key, doc)
        documents[key] = doc
    return documents


def collect_choice_css_indices():
    from app.research_equity_sources import read_artifact

    documents = {source_key(code): read_artifact("sources/" + source_key(code)) for code, *_ in CSS_INDEX_SPECS}
    now = datetime.now(SHANGHAI)
    end = now.date() - timedelta(days=(now.hour, now.minute) < (16, 15))
    while end.weekday() >= 5:
        end -= timedelta(days=1)
    # Avoid repeating identical calls while the completed session is unchanged.
    requests = []
    for code, _, symbol, market in CSS_INDEX_SPECS:
        old = documents[source_key(code)]
        latest = old.get("observationDate") or ""
        attempted = old.get("attemptedAt")
        if latest >= end.isoformat() and old.get("status") == "ready":
            continue
        if attempted:
            time = datetime.fromisoformat(attempted).astimezone(SHANGHAI)
            if "10001029" in (old.get("error") or "") and time.date() == now.date():
                continue
            if now - time < timedelta(minutes=30):
                continue
        floor = (end - timedelta(days=35)).isoformat()
        dates = [r["date"] for r in old.get("rows", []) if r["date"] >= floor]
        requests.append({"symbol": symbol, "market": market, "latest": latest, "dates": dates})
    if not requests:
        return documents
    try:
        data = {"end": end.isoformat(), "requests": requests, "fields": list(FIELDS), "options": OPTIONS}
        process = subprocess.run(
            [str(Path(sys.base_prefix) / "python.exe"), "-c", CSS_CHILD, json.dumps(data)],
            cwd=Path.home() / ".choice/EMQuantAPI_Python/python3",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=80,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        payloads = [line for line in process.stdout.splitlines() if line.startswith('{"batches"')]
        if not payloads:
            raise RuntimeError("Choice CSS returned no structured result")
        payload = json.loads(payloads[-1])
        return publish_css_batches(documents, payload["batches"], payload["failures"])
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return publish_css_batches(documents, [], {r["symbol"]: str(exc) for r in requests})
