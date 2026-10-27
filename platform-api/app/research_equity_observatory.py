"""Additive equity read models, produced in background and read without fetching."""

import asyncio
import logging
import os
from calendar import monthrange
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.data_audit_calendar import calendar_snapshot
from app.database_connection import read_only_connection
from app.research_a_share_repository import read_dataset, read_dataset_metadata
from app.research_equity_catalog import CN_INDICES, CN_REFERENCE_CODES, CN_THEME_CODES, US_THEMES
from app.research_equity_metrics import (
    cn_structure,
    credit_impulse,
    distribution,
    hk_composite,
    monthly_yoy,
    number,
    percentage,
    percentile,
    rolling_rank,
    theme_observations,
    trend,
)
from app.research_equity_sources import (
    collect_sources,
    publish_artifact,
    read_artifact,
)
from app.research_local_data import hedge_board_data_root

_LOCK = asyncio.Lock()
_LOG = logging.getLogger(__name__)


@contextmanager
def production_lock():
    path = hedge_board_data_root() / "public/v1/equity/producer.lock"
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


def series(doc):
    return {p["date"]: v for p in doc.get("rows", []) if (v := number(p.get("value"))) is not None}


def source_state(doc, today, monthly=False):
    observed = doc.get("observationDate")
    if not observed:
        return "no_data"
    if len(observed) == 7:
        y, m = map(int, observed.split("-"))
        stamp = f"{observed}-{monthrange(y, m)[1]}"
    else:
        stamp = observed
    aged = (date.fromisoformat(today) - date.fromisoformat(stamp)).days > (110 if monthly else 7)
    return "stale" if aged or doc.get("status") != "ready" else "ready"


def valuations(sources, market, today):
    result = []
    for key, name in (
        [(f"csi_history_{code}", name + " · 历史TTM") for code, name in CN_INDICES.items()]
        + [(f"csi_{code}", name + " · PE1") for code, name in CN_INDICES.items()]
        if market == "cn"
        else [("us_pe", "标普500")]
    ):
        doc = sources.get(key, {})
        rows = doc.get("rows", [])
        latest = rows[-1] if rows else {}
        result.append(
            {
                "id": key,
                "name": name,
                "date": latest.get("date"),
                "pe": latest.get("pe"),
                "dividend": latest.get("dividend"),
                "pb": None,
                "peRank": rolling_rank(rows, "pe", 36 if market == "us" else 252),
                "source": doc.get("name"),
                "sourceUrl": doc.get("url"),
                "estimated": latest.get("estimated", False),
                "method": "月度TTM PE（含来源估计值）"
                if market == "us"
                else "中证历史行情滚动市盈率（独立口径，不与PE1拼接）"
                if key.startswith("csi_history_")
                else "中证官方PE1 / 股息率1（总股本）",
                "status": source_state(doc, today, market == "us"),
                "history": rows[-120:] if market == "us" else rows[-1500:],
            }
        )
    return result


def _isolated_themes(market, observations, latest, **kwargs):
    try:
        return theme_observations(market, observations, latest, **kwargs)
    except Exception:
        _LOG.exception("Equity %s themes failed; independent market sections continue", market)
        return None


def build_cn(today, sources):
    stocks = read_dataset("stocks") or []
    metadata = read_dataset_metadata("stocks") or {}
    memberships = read_dataset("memberships") or []
    structure, aligned = cn_structure(stocks, memberships)
    previous = read_artifact("cn")
    history = previous.get("structureHistory", [])
    complete = (
        structure["closed"]
        and len(aligned) == len(stocks)
        and metadata.get("status") == "ready"
        and len(aligned) >= 1000
        and len(aligned) >= max((r.get("count", 0) for r in history[-20:]), default=0) * 0.95
    )
    state = "ready" if complete else "partial"
    local_now = datetime.now(ZoneInfo("Asia/Shanghai"))
    with read_only_connection() as db:
        calendar = calendar_snapshot(db, local_now.date().isoformat())
    if calendar:
        expected = max(
            (
                d
                for d in calendar["days"]
                if d < local_now.date().isoformat()
                or (
                    d == local_now.date().isoformat()
                    and (local_now.hour, local_now.minute) >= (16, 15)
                )
            ),
            default=None,
        )
        if expected and (structure["date"] or "") < expected:
            state = "stale"
    else:
        state = "partial"
    if complete:
        row = {
            "date": structure["date"],
            **structure["market"],
            "industries": structure["industries"],
        }
        history = sorted(
            [r for r in history if r["date"] != row["date"]] + [row], key=lambda r: r["date"]
        )[-1500:]
    for industry in structure["industries"]:
        samples = [
            i
            for h in history
            if h["date"] <= structure["date"]
            for i in h.get("industries", [])
            if i["code"] == industry["code"]
        ][-1250:]
        industry["shareRank"] = percentile(
            [s.get("amountSharePct") for s in samples], industry["amountSharePct"]
        )
        industry["turnoverRank"] = percentile(
            [s.get("medianTurnover") for s in samples], industry["medianTurnover"]
        )
        industry["sampleCount"] = len(samples)
    from app.research_a_share_repository import read_index_history, read_stored_stock_histories

    histories = read_stored_stock_histories(list(CN_THEME_CODES + CN_REFERENCE_CODES))
    history_points = {
        code: [{"date": str(p.observed_at), "value": p.close} for p in points]
        for code, points in histories.items()
    }
    industries = {
        m["securityCode"]: m.get("swL2Name") or m.get("swL1Name")
        for m in memberships
        if not m.get("effectiveTo") and m.get("effectiveFrom", "") <= (structure["date"] or "")
    }
    benchmark_points = [
        {"date": p["observedAt"], "value": p.get("close")} for p in read_index_history("000300")
    ]
    observations = {
        r["securityCode"]: {
            "name": r["securityName"],
            "date": structure["date"],
            "returnPct": r.get("returnPct") if structure["closed"] else None,
            "status": "ready" if structure["closed"] else "partial",
            "industry": industries.get(r["securityCode"]),
            "region": "A股上市",
            "history": history_points.get(r["securityCode"], []),
            "source": "腾讯复权日线 / 全市场收盘快照",
            "sourceUrl": "https://gu.qq.com/"
            + ("sh" if r["securityCode"].startswith("6") else "sz")
            + r["securityCode"],
        }
        for r in aligned
    }
    themes = _isolated_themes(
        "cn",
        observations,
        structure["date"],
        benchmark={"code": "000300", "name": "沪深300", "history": benchmark_points},
        references={
            code: {"history": points, "date": points[-1]["date"] if points else None}
            for code, points in history_points.items()
            if code in CN_REFERENCE_CODES
        },
    )
    indices = []
    for row in read_dataset("market_detail") or []:
        points = [{"date": p["observedAt"], "value": p["close"]} for p in row.get("history", [])]
        indices.append({"code": row["code"], "name": row["name"], **trend(points)})
    index_crowding = []
    index_history = previous.get("indexCrowdingHistory", [])
    by_code = {r["securityCode"]: r for r in aligned}
    for code, name in CN_INDICES.items():
        doc = sources.get(f"members_{code}", {})
        usable = [
            r for r in doc.get("rows", []) if structure["date"] and r["date"] <= structure["date"]
        ]
        member = usable[-1] if usable else {}
        codes = member.get("codes", [])
        sample = [by_code[c] for c in codes if c in by_code]
        stats = distribution(sample)
        observation = {
            "code": code,
            "name": name,
            "date": structure["date"],
            "membershipDate": member.get("date"),
            "expected": len(codes),
            **stats,
        }
        if complete and codes and len(sample) == len(codes):
            index_history = [
                r for r in index_history if (r["code"], r["date"]) != (code, structure["date"])
            ] + [observation.copy()]
        samples = sorted(
            [
                r
                for r in index_history
                if r["code"] == code and r["date"] <= (structure["date"] or "")
            ],
            key=lambda r: r["date"],
        )[-1250:]
        observation["turnoverRank"] = percentile(
            [r["medianTurnover"] for r in samples], stats["medianTurnover"]
        )
        observation["sampleCount"] = len(samples)
        index_crowding.append(observation)
    index_history = sorted(index_history, key=lambda r: (r["date"], r["code"]))[
        -1250 * len(CN_INDICES) :
    ]
    old_crowding = read_dataset("crowding") or {}
    crowding = []
    for name in ("通信设备", "计算机设备", "元件", "半导体"):
        points = [
            {"date": h["date"], **h.get("targets", {}).get(name, {})}
            for h in old_crowding.get("history", [])
            if h.get("targets", {}).get(name)
        ]
        if points:
            latest = points[-1]
            crowding.append(
                {
                    "name": name,
                    "date": latest["date"],
                    "sharePct": number(latest.get("amountShareOfA")) * 100
                    if number(latest.get("amountShareOfA")) is not None
                    else None,
                    "turnover": latest.get("turnoverPct"),
                    "shareRank": percentile(
                        [p.get("amountShareOfA") for p in points[-1250:]],
                        latest.get("amountShareOfA"),
                    ),
                    "turnoverRank": percentile(
                        [p.get("turnoverPct") for p in points[-1250:]], latest.get("turnoverPct")
                    ),
                    "count": len(points[-1250:]),
                }
            )
    reference = read_artifact("reference-hs300")
    ref_rows = reference.get("rows", [])
    reference["ranks"] = {k: rolling_rank(ref_rows, k) for k in ("pe", "pb", "ps", "pcf", "erp")}
    return {
        "market": "cn",
        "status": state,
        "date": structure["date"],
        "structure": structure,
        "structureHistory": history,
        "themes": themes,
        "breadth": market_breadth(
            observations, sorted(p["date"] for p in benchmark_points), structure["date"]
        ),
        "indices": indices,
        "crowding": crowding,
        "valuations": valuations(sources, "cn", today),
        "reference": reference,
        "indexCrowding": index_crowding,
        "indexCrowdingHistory": index_history,
        "source": metadata.get("source"),
        "sourceFetchedAt": metadata.get("fetched_at"),
    }


def market_breadth(observations, sessions, latest, codes=None):
    """Current fixed sample; never label partial history as exchange-wide breadth."""
    from app.research_equity_themes import price_map

    universe = {k: v for k, v in observations.items() if codes is None or k in codes}
    counts = {"advancing": 0, "declining": 0, "unchanged": 0, "valid": 0}
    participation = []
    prices = {k: price_map(v.get("history", []), latest) for k, v in universe.items()}
    for key, observation in universe.items():
        if observation.get("date") != latest:
            continue
        value = number(observation.get("returnPct"))
        if value is None and len(sessions) >= 2:
            a, b = (prices[key].get(d) for d in sessions[-2:])
            value = b / a - 1 if a and b else None
        if value is not None:
            counts["valid"] += 1
            counts["advancing" if value > 0 else "declining" if value < 0 else "unchanged"] += 1
    for period in (20, 60, 200, 252):
        window = sessions[-period:]
        valid = [
            p for p in prices.values() if len(window) == period and all(d in p for d in window)
        ]
        above = sum(p[latest] > sum(p[d] for d in window) / period for p in valid)
        highs = sum(p[latest] >= max(p[d] for d in window) for p in valid)
        lows = sum(p[latest] <= min(p[d] for d in window) for p in valid)
        participation.append(
            {
                "period": period,
                "valid": len(valid),
                "abovePct": percentage(above, len(valid)),
                "highs": highs,
                "lows": lows,
            }
        )
    return {"date": latest, "expected": len(universe), **counts, "participation": participation}


def build_us(today, sources):
    snapshot = read_dataset("market_detail_us") or {}
    rows = snapshot.get("rows", [])
    by_symbol = {r["symbol"]: r for r in rows}
    # A closed SPY session defines every stock/ETF comparison window. An open
    # quote or a different exchange's newer date cannot advance the whole board.
    baseline = by_symbol.get("SPY", {}).get("history", [])
    latest = max((p["date"] for p in baseline), default=None)
    observations = {}
    for r in rows:
        points = [p for p in r.get("history", []) if latest and p["date"] <= latest]
        day = points[-1]["date"] if points else None
        observations[r["symbol"]] = {
            "name": r.get("name") if r.get("name") != r.get("id") else r["symbol"],
            "date": day,
            "status": "ready"
            if day and day == latest and r.get("status") == "ready"
            else "no_data",
            "history": points,
            "source": r.get("source"),
            "sourceUrl": r.get("sourceUrl"),
            "region": "美股上市；经营地域未分类",
            "industry": None,
        }
    themes = _isolated_themes(
        "us",
        observations,
        latest,
        benchmark={"code": "SPY", "name": "SPY（标普500价格）", "history": baseline},
    )
    from app.research_equity_themes import window_metrics

    sector_names = {
        "XLB": "材料",
        "XLC": "通信服务",
        "XLE": "能源",
        "XLF": "金融",
        "XLI": "工业",
        "XLK": "信息技术",
        "XLP": "必选消费",
        "XLRE": "房地产",
        "XLU": "公用事业",
        "XLV": "医疗",
        "XLY": "可选消费",
    }
    sector_metrics = [
        {
            "code": code,
            "name": name,
            "date": observations.get(code, {}).get("date"),
            **window_metrics(
                observations.get(code, {}).get("history", []),
                sorted(p["date"] for p in baseline),
                latest,
            ),
        }
        for code, name in sector_names.items()
    ]
    if themes is not None:
        themes["sectors"] = sector_metrics
    trends = {symbol: trend(r.get("history", [])) for symbol, r in by_symbol.items()}
    ratios = []
    for numerator, denominator, name in [
        ("RSP", "SPY", "等权 / 市值加权"),
        ("IWM", "SPY", "小盘 / 大盘"),
        ("QQQ", "SPY", "纳指100 / 标普500"),
        ("^VIX", "^VIX3M", "VIX / VIX3M"),
    ]:
        a = {p["date"]: number(p["value"]) for p in by_symbol.get(numerator, {}).get("history", [])}
        b = {
            p["date"]: number(p["value"]) for p in by_symbol.get(denominator, {}).get("history", [])
        }
        points = [
            {"date": d, "value": a[d] / b[d]}
            for d in sorted(a.keys() & b.keys())
            if a[d] is not None and b[d] and b[d] > 0
        ]
        ratios.append(
            {
                "name": name,
                "symbols": f"{numerator} / {denominator}",
                **trend(points),
                "history": points[-260:],
            }
        )
    sectors = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
    eligible = [trends[s] for s in sectors if s in trends and trends[s].get("date")]
    same_date = max((r["date"] for r in eligible), default=None)
    participation = []
    for period in (20, 60, 200):
        valid = [
            t
            for t in eligible
            if t.get("date") == same_date and t.get(f"above{period}") is not None
        ]
        participation.append(
            {
                "period": period,
                "count": len(valid),
                "expected": 11,
                "value": percentage(sum(t[f"above{period}"] for t in valid), len(valid)),
                "date": same_date,
            }
        )
    risk = []
    for key, name in [("us_credit", "美国高收益债信用利差"), ("us_real_yield", "美国10年实际利率")]:
        doc = sources.get(key, {})
        ps = doc.get("rows", [])
        risk.append(
            {
                "name": name,
                "value": ps[-1].get("value") if ps else None,
                "date": doc.get("observationDate"),
                "source": doc.get("name"),
                "sourceUrl": doc.get("url"),
                "status": source_state(doc, today),
                "history": ps[-260:],
            }
        )
    return {
        "market": "us",
        "date": latest,
        "status": snapshot.get("status", "no_data"),
        "sourceFetchedAt": snapshot.get("retrievedAt"),
        "themes": themes,
        "breadth": market_breadth(
            observations,
            sorted(p["date"] for p in baseline),
            latest,
            {c for _, parts in US_THEMES for _, symbols in parts for c in symbols.split()},
        ),
        "ratios": ratios,
        "participation": participation,
        "risk": risk,
        "valuations": valuations(sources, "us", today),
    }


def build_hk(today, sources):
    # Both publishers report PBC monthly AFRE flow in CNY 100 million.
    # Keep their artifacts separate; newer official revisions win by month.
    tsf = series(sources.get("cn_tsf", {}))
    official_tsf = series(sources.get("cn_tsf_pbc", {}))
    tsf.update(official_tsf)
    credit_source = "cn_tsf_pbc" if official_tsf else "cn_tsf"
    components = {
        "m2": monthly_yoy(series(sources.get("hk_m2", {}))),
        "ppi": series(sources.get("cn_ppi", {})),
        "retail": series(sources.get("cn_retail", {})),
        "credit": credit_impulse(tsf, series(sources.get("cn_gdp", {}))),
    }
    result = hk_composite(components, today)
    result["indices"] = []
    for key in ("hk_hsi", "hk_hscei", "hk_hstech", "hk_hsiii"):
        doc = sources.get(key, {})
        points = doc.get("rows", [])
        latest = points[-1] if points else {}
        previous = number(points[-2].get("value")) if len(points) > 1 else None
        value = number(latest.get("value"))
        result["indices"].append(
            {
                "name": doc.get("name", key),
                "date": latest.get("date"),
                "value": value,
                "returnPct": (value / previous - 1) * 100 if value and previous else None,
                "status": source_state(doc, today),
                "history": points[-260:],
            }
        )
    for row, key in zip(
        result["components"], ["hk_m2", "cn_ppi", "cn_retail", credit_source], strict=True
    ):
        row["source"] = sources.get(key, {}).get("name")
        row["sourceUrl"] = sources.get(key, {}).get("url")
        row["status"] = source_state(sources.get(key, {}), today, True)
        if key == credit_source:
            row["source"] = (
                "人民银行当年表 / 商务部转载历史 · 新增社融" if official_tsf else row["source"]
            )
        if key == credit_source and source_state(sources.get("cn_gdp", {}), today, True) != "ready":
            row["status"] = "stale"
    if result["value"] is not None and any(r["status"] != "ready" for r in result["components"]):
        result["status"] = "stale"
    return result


def produce_local(sources):
    stamp = datetime.now(UTC).isoformat()
    results = {}
    for market, build in [("cn", build_cn), ("us", build_us)]:
        try:
            previous = read_artifact(market) or {}
            section_status = {}
            try:
                payload = build(stamp[:10], sources)
                section_status["market"] = "ready"
                if "themes" in payload and payload["themes"] is None:
                    payload["themes"] = previous.get("themes")
                    section_status["themes"] = "stale" if payload["themes"] else "error"
            except Exception:
                _LOG.exception("Equity %s market section failed; other sections continue", market)
                payload = {**previous, "market": market, "status": "partial"}
                payload.setdefault("date", None)
                payload.setdefault("themes", None)
                section_status["market"] = "stale" if previous else "error"
            from app.research_equity_valuation import build_valuation_charts

            try:
                payload["valuationCharts"] = build_valuation_charts(sources, market)
                section_status["valuation"] = "ready"
            except Exception:
                _LOG.exception(
                    "Equity %s valuation section failed; market section retained", market
                )
                payload["valuationCharts"] = previous.get("valuationCharts", [])
                section_status["valuation"] = "stale" if payload["valuationCharts"] else "error"
            payload["generatedAt"] = stamp
            payload["schemaVersion"] = "1.0"
            if market == "cn":
                try:
                    payload["hongKong"] = build_hk(stamp[:10], sources)
                    section_status["hongKong"] = "ready"
                except Exception:
                    _LOG.exception("Hong Kong section failed; mainland sections retained")
                    payload["hongKong"] = previous.get("hongKong")
                    section_status["hongKong"] = "stale" if payload["hongKong"] else "error"
            payload["sectionStatus"] = section_status
            incomplete = (
                any(v["status"] != "ready" for v in payload.get("valuations", []))
                or any(r["count"] != r["expected"] for r in payload.get("indexCrowding", []))
                or (market == "cn" and (payload.get("hongKong") or {}).get("status") != "ready")
                or (market == "us" and any(not r.get("date") for r in payload.get("ratios", [])))
            )
            if incomplete or any(state != "ready" for state in section_status.values()):
                payload["status"] = "partial"
            payload["sources"] = [
                {
                    "name": s.get("name", k),
                    "status": s.get("status"),
                    "date": s.get("observationDate"),
                    "fetchedAt": s.get("fetchedAt"),
                    "error": s.get("error"),
                }
                for k, s in sources.items()
                if k.startswith(("us_",)) == (market == "us")
            ]
            publish_artifact(market, payload)
            results[market] = {"status": payload["status"], "date": payload.get("date")}
        except Exception as exc:
            _LOG.exception("Equity %s projection failed; previous artifact retained", market)
            results[market] = {"status": "error", "error": type(exc).__name__}
    publish_artifact("health", {"attemptedAt": stamp, "markets": results})
    return results


async def refresh_equity_observatory(*, force=False):
    if _LOCK.locked():
        return "busy"
    async with _LOCK:
        with production_lock() as acquired:
            if not acquired:
                return "busy"
            sources = await collect_sources(force=force)
            results = await asyncio.to_thread(produce_local, sources)
    return (
        "ready"
        if all(v.get("status") == "ready" for v in sources.values())
        and all(v["status"] == "ready" for v in results.values())
        else "partial"
    )


async def run_periodic():
    while True:
        try:
            await refresh_equity_observatory()
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOG.exception("Equity observation refresh failed; retrying next cycle")
        await asyncio.sleep(300)


def read_equity_observatory(market):
    result = read_artifact(market)
    if not result:
        return {"market": market, "status": "no_data", "generatedAt": None}
    generated = datetime.fromisoformat(result["generatedAt"])
    if datetime.now(UTC) - generated > timedelta(minutes=30):
        result["status"] = "stale"
    fetched = result.get("sourceFetchedAt")
    if (
        market == "us"
        and fetched
        and datetime.now(UTC) - datetime.fromisoformat(fetched.replace("Z", "+00:00"))
        > timedelta(hours=2)
    ):
        result["status"] = "stale"
    # Source histories are stored on disk for audit but omitted from the normal
    # page response except chart-ready series, preventing multi-MB GET payloads.
    result["structureHistory"] = [
        {k: v for k, v in r.items() if k != "industries"}
        for r in result.get("structureHistory", [])
    ]
    result.pop("indexCrowdingHistory", None)
    result.get("reference", {}).pop("sourceFile", None)
    health = read_artifact("health")
    if health.get("markets", {}).get(market, {}).get("status") == "error":
        result["status"] = "stale"
    return result
