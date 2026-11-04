"""Licensed public research datasets; background acquisition, local-only reads."""
import asyncio
import json
from datetime import UTC, datetime, timedelta, date
from decimal import Decimal
import httpx
from app.research_equity_sources import archive, read_artifact, publish_artifact

SOURCES = {
    "dli_regime": "https://dollarliquidity.com/api/regime",
    "dli_lens": "https://dollarliquidity.com/api/lens",
    "dli_history": "https://dollarliquidity.com/api/history",
    "sp_drivers": "https://historyofmarket.com/api/sp500/driver-decomp.json",
    "sp_drawdowns": "https://historyofmarket.com/api/sp500/intrayear-dd.json",
    "sp_monthly": "https://historyofmarket.com/api/sp500/monthly.json",
}
for key in ["fed-swap-lines", "tga", "sofr-iorb", "reserve-buffer", "ust-2y", "effr"]:
    SOURCES["dli_series_"+key] = "https://dollarliquidity.com/api/series/"+key+"?days=180"


def validate(key, payload):
    if not isinstance(payload, dict):
        raise ValueError("reference_schema")
    if key == "dli_regime":
        score = Decimal(str(payload["percentile5y"]))
        if not score.is_finite() or not 0 <= score <= 100:
            raise ValueError("invalid_score")
        date.fromisoformat(payload["dataAsOf"])
    elif key == "dli_lens":
        for axis in ["quantity", "price", "structure", "synthesis"]:
            if not isinstance(payload.get(axis), dict): raise ValueError("missing_lens_axis")
        date.fromisoformat(payload["dataAsOf"])
    elif key == "dli_snapshot":
        if not payload.get("indicators", {}).get("list"): raise ValueError("empty_indicators")
    else:
        field = {"dli_history":"dli", "sp_drivers":"series", "sp_drawdowns":"annual", "sp_monthly":"years"}.get(key)
        if field:
            rows = payload.get(field)
            if not isinstance(rows, list) or not rows: raise ValueError("empty_reference")
            ids = [r.get("date") if key == "dli_history" else r.get("year") for r in rows]
            if None in ids or len(set(ids)) != len(ids): raise ValueError("duplicate_reference_period")
        elif not any(isinstance(payload.get(k), list) and payload[k] for k in ["data", "series", "observations"]):
            raise ValueError("empty_series")
    def finite(value):
        if value is not None and not Decimal(str(value)).is_finite():
            raise ValueError("nonfinite_reference_value")
    field = {"dli_history":"dli", "sp_drivers":"series", "sp_drawdowns":"annual", "sp_monthly":"years"}.get(key, "data")
    for row in payload.get(field, []):
        if "date" in row:
            if date.fromisoformat(row["date"]) > datetime.now(UTC).date(): raise ValueError("future_observation")
        if key == "sp_drivers":
            for f in ["peChange","epsChange","priceReturn","endingPE","endingEPS"]:
                if row.get(f) is None: raise ValueError("incomplete_driver_row")
                finite(row[f])
        elif key == "sp_drawdowns":
            for f in ["dd","tr"]: finite(row.get(f))
            if row.get("dd") is not None and not -1 <= Decimal(str(row["dd"])) <= 0: raise ValueError("invalid_drawdown")
        elif key == "sp_monthly":
            for month,value in row["months"].items():
                if not 1 <= int(month) <= 12: raise ValueError("invalid_month")
                finite(value)
                if value is not None and Decimal(str(value)) < -1: raise ValueError("invalid_month_return")
            finite(row.get("annual"))
        else:
            finite(row.get("value"))
            finite(row.get("tightnessScore"))
    return payload


async def refresh_references(force=False):
    now = datetime.now(UTC)
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=True) as client:
        sem = asyncio.Semaphore(3)
        async def collect(key, url):
            old = await asyncio.to_thread(read_artifact, "references/"+key)
            interval = timedelta(hours=1 if old.get("error") else 6)
            if not force and old.get("attemptedAt") and now-datetime.fromisoformat(old["attemptedAt"]) < interval:
                return key, old.get("status")
            doc = {**old, "sourceUrl":url, "attemptedAt":now.isoformat()}
            try:
                async with sem:
                    response = await client.get(url)
                    response.raise_for_status()
                    payload = validate(key, json.loads(response.content, parse_float=str))
                old_date = (old.get("payload") or {}).get("dataAsOf") or (old.get("payload") or {}).get("updated")
                new_date = payload.get("dataAsOf") or payload.get("updated")
                if old_date and new_date and new_date < old_date: raise ValueError("source_date_regressed")
                digest = await asyncio.to_thread(archive, key, response.content, now.isoformat())
                doc.update(payload=payload, status="ready", error=None, fetchedAt=now.isoformat(), rawSha256=digest)
            except Exception as exc:
                doc.update(status="stale" if old.get("payload") else "error", error=type(exc).__name__)
            await asyncio.to_thread(publish_artifact,"references/"+key,doc)
            return key,doc["status"]
        return dict(await asyncio.gather(*(collect(k,u) for k,u in SOURCES.items())))


async def run_periodic():
    while True:
        try: await refresh_references()
        except asyncio.CancelledError: raise
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Reference boards refresh failed")
        await asyncio.sleep(300)


def read_references(board):
    keys = [k for k in SOURCES if k.startswith("dli_") == (board == "liquidity")]
    docs = {k:read_artifact("references/"+k) for k in keys}
    result = {k:d.get("payload") for k,d in docs.items()}
    if result.get("dli_history"):
        result["dli_history"] = {"updatedAt":result["dli_history"].get("updatedAt"),"dli":[{f:r.get(f) for f in ["date","tightnessScore","structuralFlow","tacticalFlow"]} for r in result["dli_history"]["dli"]]}
    result["sources"] = [{"id":k, **{f:d.get(f) for f in ["status","sourceUrl","fetchedAt","error"]}} for k,d in docs.items()]
    if board == "stocks" and result.get("sp_drivers"):
        doc = result["sp_drivers"]
        rows=[]
        for row in doc["series"]:
            p,e,r=[Decimal(str(row[k])) for k in ["peChange","epsChange","priceReturn"]]
            cross=p*e
            rows.append({**row,"date":str(row["year"])+"-12-31", "peContribution":(p+cross/2)*100,
                         "epsContribution":(e+cross/2)*100,"returnPct":r*100,
                         "residual":(r-p-e-cross)*100,"pePct":p*100,"epsPct":e*100})
        result["driverRows"]=rows
    return result
