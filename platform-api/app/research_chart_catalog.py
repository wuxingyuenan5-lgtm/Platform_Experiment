"""Allowlisted shared research series for the personal chart editor. No SQL input."""

import hashlib
from functools import lru_cache

from fastapi import HTTPException

from app.research_local_data import hedge_board_data_root, read_local_json
from app.research_provider_errors import ResearchProviderError

EQUITY = {
    "ndx": ("^NDX", "纳斯达克100指数"),
    "spy": ("SPY", "标普500 ETF · SPY"),
    "dow": ("^DJI", "道琼斯工业指数"),
    "soxx": ("SOXX", "半导体 ETF · SOXX"),
    "xlk": ("XLK", "信息技术 ETF · XLK"),
}


def _id(path, key=""):
    return hashlib.sha256((path + "#" + key).encode()).hexdigest()[:24]


def _files():
    root = hedge_board_data_root()
    paths = sorted(root.glob("public/v1/*/series/*.json"))
    macro = root / "public/v1/macro/dashboard.json"
    if macro.is_file():
        paths.append(macro)
    for relative in ("equity/cn.json", "equity/us.json", "a-share/etf-market-cap-ratios.json"):
        path = root / "public/v1" / relative
        if path.is_file():
            paths.append(path)
    return tuple(
        (p.relative_to(root).as_posix(), p.stat().st_mtime_ns, p.stat().st_size) for p in paths
    )


@lru_cache(maxsize=2)
def _registry(revisions):
    result = {}
    for path, _, _ in revisions:
        try:
            data = read_local_json(path)
        except ResearchProviderError:
            continue  # An unrelated unavailable series must not break the catalog.
        if "valuationCharts" in data:
            series = []
            for index in data["valuationCharts"]:
                series.append(
                    {
                        "seriesId": index["id"] + "-close",
                        "label": index["name"] + " · 指数走势",
                        "unit": "点",
                        "frequency": "native_observation",
                        "source": "既有指数行情历史",
                        "observations": index.get("prices", []),
                    }
                )
                for metric in index.get("metrics", []):
                    series.append(
                        {
                            **metric,
                            "seriesId": index["id"] + "-" + metric["id"],
                            "label": index["name"] + " · " + metric["label"],
                            "frequency": "native_observation",
                            "observations": metric.get("history", []),
                        }
                    )
        elif path.endswith("etf-market-cap-ratios.json"):
            series = []
            for group, rows in data.get("groups", {}).items():
                for field, label, unit in (
                    ("ratioPct", "头部ETF / 指数流通市值", "%"),
                    ("etfCapYi", "头部ETF市值", "亿元"),
                    ("indexCapYi", "指数流通市值", "亿元"),
                ):
                    series.append(
                        {
                            "seriesId": group + "-" + field,
                            "label": group + " · " + label,
                            "unit": unit,
                            "source": data.get("source", ""),
                            "sourceUrl": data.get("sourceUrl", ""),
                            "frequency": "daily_business_day",
                            "observations": [
                                {"date": r["date"], "value": r.get(field)} for r in rows
                            ],
                        }
                    )
        else:
            series = (
                [s for group in data.get("groups", {}).values() for s in group]
                if "groups" in data
                else [data]
            )
        for item in series:
            points = item.get("observations")
            if not isinstance(points, list) or not points:
                continue
            key = item.get("seriesId", "")
            result[_id(path, key)] = {
                "id": _id(path, key),
                "name": item.get("label", key),
                "unit": item.get("unit", ""),
                "frequency": item.get("frequency", ""),
                "source": item.get("source", ""),
                "sourceUrl": item.get("sourceUrl", ""),
                "asOf": item.get("observationDate") or points[-1].get("date"),
                "group": path.split("/")[2],
                "observations": points,
            }
    return result


def series_catalog():
    out = [
        {k: v for k, v in s.items() if k != "observations"} for s in _registry(_files()).values()
    ]
    out += [
        {
            "id": "equity-" + key,
            "name": name,
            "unit": "点" if symbol.startswith("^") else "USD",
            "frequency": "daily_business_day",
            "group": "equity",
            "source": "Yahoo Finance",
            "sourceUrl": f"https://finance.yahoo.com/quote/{symbol}/history/",
            "asOf": None,
        }
        for key, (symbol, name) in EQUITY.items()
    ]
    return out


def series_data(series_id):
    if series_id.startswith("equity-") and series_id[7:] in EQUITY:
        import json

        from app.database_connection import read_only_connection

        symbol, _ = EQUITY[series_id[7:]]
        with read_only_connection() as db:
            records = db.execute(
                "SELECT observed_at,payload_json FROM research_a_share_history "
                "WHERE dataset='market_price' AND entity_code=? ORDER BY observed_at LIMIT 40000",
                ("Yahoo Finance:" + symbol,),
            ).fetchall()
        if len(records) == 40000:
            raise HTTPException(422, "Series history limit reached")
        meta = next(s for s in series_catalog() if s["id"] == series_id)
        return {
            **meta,
            "asOf": records[-1]["observed_at"] if records else None,
            "observations": [
                {"date": r["observed_at"], "value": json.loads(r["payload_json"]).get("close")}
                for r in records
            ],
        }
    item = _registry(_files()).get(series_id)
    if item is None:
        raise HTTPException(404, "Unknown shared research series")
    return item
