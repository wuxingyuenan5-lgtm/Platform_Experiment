"""Read-only local national ETF monitor with bounded public refresh."""
import hashlib
import html
import json
import logging
import math
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
import httpx
from app.research_local_data import read_local_json, write_local_json

SOURCE = "https://etf.maomaoci-a.com/data/data.json"
ROOT = "public/v1/national-etf/"
_LOCK = threading.Lock()

def validate(data):
    if data.get("sample") is not False:
        raise ValueError("sample data cannot be published")
    dates = data.get("dates", [])
    if not dates or dates != sorted(set(dates)):
        raise ValueError("invalid dates")
    for day in dates:
        datetime.strptime(day, "%Y-%m-%d")
    codes = [e["code"] for e in data["etfs"]]
    if len(codes) != len(set(codes)) or not codes:
        raise ValueError("duplicate or absent ETF")
    for code in codes:
        if len(code) != 6 or not code.isdigit():
            raise ValueError("invalid code")
        for key in ("shares", "flow", "close"):
            values = data["series"][code][key]
            if len(values) != len(dates) or any(v is not None and (not isinstance(v, (float,int)) or not math.isfinite(v)) for v in values):
                raise ValueError("invalid observations")
    return data

def read():
    try:
        return read_local_json(ROOT + "latest.json")
    except Exception:
        return {}

def refresh(force=False):
    if not _LOCK.acquire(False):
        return "busy"
    try:
        old = read()
        now = datetime.now(UTC)
        if not force and old.get("attemptedAt") and now - datetime.fromisoformat(old["attemptedAt"]) < timedelta(hours=6 if old.get("status")=="ready" else 1):
            return "cached"
        try:
            with httpx.Client(timeout=40, follow_redirects=True) as client:
                response = client.get(SOURCE)
                response.raise_for_status()
                data = validate(response.json())
            if old.get("data",{}).get("dates") and (data["dates"][-1] < old["data"]["dates"][-1] or not set(old["data"]["dates"]).issubset(data["dates"])):
                raise ValueError("history regressed")
            digest = hashlib.sha256(response.content).hexdigest()
            write_local_json("raw/research/national-etf/" + digest + ".json", {"sourceUrl":SOURCE,"observedAt":now.isoformat(),"rawText":response.text})
            write_local_json(ROOT+"latest.json", {"status":"ready","sourceUrl":SOURCE,"attemptedAt":now.isoformat(),"retrievedAt":now.isoformat(),"sha256":digest,"data":data})
            return "ready"
        except Exception as exc:
            write_local_json(ROOT+"latest.json", {**old,"status":"stale" if old.get("data") else "no_data","attemptedAt":now.isoformat(),"error":type(exc).__name__})
            logging.getLogger(__name__).warning("National ETF refresh failed: %s",type(exc).__name__)
            return "stale"
    finally:
        _LOCK.release()

def page(view="etf"):
    snapshot = read()
    if not snapshot.get("data"):
        return '<p role="status">暂无已采集的股指期货持仓数据</p>' if view == "futures" else '<p role="status">暂无已采集的ETF数据</p>'
    def escape(value):
        if isinstance(value,str): return html.escape(value)
        if isinstance(value,list): return [escape(x) for x in value]
        if isinstance(value,dict): return {k:escape(v) for k,v in value.items()}
        return value
    base = Path(__file__).parent / "research_templates"
    document = (base/("citic_futures.html" if view == "futures" else "national_etf.html")).read_text(encoding="utf-8")
    document = document.replace("__LOCAL_DATA__",json.dumps(escape(snapshot["data"]),ensure_ascii=False).replace("<","\\u003c"))
    document = document.replace("__ECHARTS__", (base/"echarts.min.js").read_text(encoding="utf-8"))
    if snapshot.get("status") != "ready":
        document = document.replace('<div class="wrap">','<div class="wrap"><p role="status">更新暂未成功，当前显示已保留数据。</p>')
    return document
