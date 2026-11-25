"""Internal history holes in published research, independent of fetch freshness.

Only 7x24 daily series have a complete calendar-day expectation. Other
frequencies report explicit source nulls and long observation gaps as candidates,
never invent exchange sessions or monthly releases.
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.research_local_data import read_local_json, local_json_revision


# Frequency alone does not specify a calendar (ETF and FRED daily feeds often
# omit weekends). Only sources with an established 7x24 contract use day counts.
CALENDAR_DAY_SERIES = {
    "binance_btc_spot", "binance_eth_spot", "btc_dvol", "fear_greed",
    "binance_btc_funding", "binance_eth_funding", "binance_btc_open_interest",
    "binance_eth_open_interest", "stablecoin_market_cap", "coinbase_premium",
    "bybit_usdt_borrow", "gld_borrow_fee", "gld_borrow_available",
}


def series_coverage(series, *, calendar_days=False):
    rows = series.get("observations", [])
    dates, invalid, nulls = [], [], []
    for row in rows:
        day = str(row.get("date", ""))
        try:
            parsed = date.fromisoformat(day)
            if len(day) != 10:
                raise ValueError("not a day")
            dates.append(parsed)
            if row.get("value") is None:
                nulls.append(day)
            elif not Decimal(str(row["value"])).is_finite():
                invalid.append(day)
        except (ValueError, InvalidOperation, TypeError):
            invalid.append(day)
    ordered = sorted(set(dates))
    frequency = series.get("frequency")
    missing, gaps = [], []
    if ordered and calendar_days and frequency in {"daily", "daily_last_collected_snapshot"}:
        have = set(ordered)
        missing = [(ordered[0] + timedelta(days=i)).isoformat()
                   for i in range((ordered[-1] - ordered[0]).days + 1)
                   if ordered[0] + timedelta(days=i) not in have]
    # These are inspection candidates, not calendar-certified missing dates.
    threshold = {"daily_business_day": 10, "weekly": 17, "monthly": 75,
                 "quarterly": 200}.get(frequency)
    if threshold:
        gaps = [{"after": a.isoformat(), "before": b.isoformat(), "days": (b-a).days}
                for a, b in zip(ordered, ordered[1:]) if (b-a).days > threshold]
    return dict(observations=len(rows), firstDate=ordered[0].isoformat() if ordered else None,
                lastDate=ordered[-1].isoformat() if ordered else None,
                duplicateDates=len(dates)-len(set(dates)), invalidDates=invalid,
                explicitNullDates=nulls, missingDates=missing, longGapCandidates=gaps)


def research_history_checks(now):
    from app.data_audit import check
    results = []
    for domain in ("macro", "crypto", "commodity"):
        records = []
        try:
            document = read_local_json(f"public/v1/{domain}/dashboard.json")
            seen = set()
            for group, series in document.get("groups", {}).items():
                for row in series:
                    sid = row.get("seriesId")
                    if sid in seen:
                        continue
                    seen.add(sid)
                    coverage = series_coverage(row, calendar_days=sid in CALENDAR_DAY_SERIES)
                    if (not coverage["observations"] or any(coverage[k] for k in (
                        "duplicateDates", "invalidDates", "explicitNullDates", "missingDates", "longGapCandidates"
                    ))):
                        records.append(dict(seriesId=sid, label=row.get("label"), group=group,
                            source=row.get("source"), sourceUrl=row.get("sourceUrl"),
                            frequency=row.get("frequency"), sourceStatus=row.get("status"),
                            qualityFlags=row.get("qualityFlags", []), **coverage))
            results.append(check(f"history.coverage.{domain}", f"{domain} 历史内部覆盖", "研究文件库",
                "warning" if records or not seen else "healthy",
                "发布文件没有已登记序列" if not seen else
                "按原生频率保留缺值；长间隔仅为待核对候选" if records else "登记序列未发现内部异常",
                seriesCount=len(seen), findings=records, checkedAt=now.isoformat()))
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            results.append(check(f"history.coverage.{domain}", f"{domain} 历史内部覆盖", "研究文件库",
                                 "error", "覆盖检查未完成", error=str(exc)))
    try:
        document = read_local_json("public/v1/crypto/us-session-prices.json")
        records = document.get("rows", [])
        missing = {key: [r["date"] for r in records if r.get(key) is None]
                   for key in ("btc", "ndx", "xau")}
        dates = [r["date"] for r in records]
        duplicates = len(dates)-len(set(dates))
        results.append(check("crypto.coverage.session_prices", "同步开收盘价格覆盖", "加密研究数据",
            "warning" if not records or any(missing.values()) or duplicates or document.get("status") != "ready" else "healthy",
            "缺失原始端点会重置相关性窗口，不能用相邻价格替代",
            rows=len(records), missingEndpoints=missing, duplicateEndpoints=duplicates,
            sourceStatus=document.get("status"), retrievedAt=document.get("retrievedAt"),
            repairAttemptAt=document.get("repairAttemptAt"), repairErrors=document.get("repairErrors", []),
            lastError=document.get("lastError"),
            storage="public/v1/crypto/us-session-prices.json",
            endpoint="/research/crypto/rolling-correlation"))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        results.append(check("crypto.coverage.session_prices", "同步开收盘价格覆盖", "加密研究数据",
                             "error", "覆盖检查未完成", error=str(exc)))
    for filename in ("research-refresh", "china-macro-refresh", "choice-edb-refresh"):
        relative = f"public/v1/{filename}.json"
        if not local_json_revision(relative):
            continue
        try:
            report = read_local_json(relative)
            failed = [s for s in report.get("sources", []) if s.get("status") != "ready"]
            results.append(check(f"research.producer.{filename}", filename, "研究文件库",
                "healthy" if report.get("status") == "ready" else "warning",
                "采集状态按来源保留，成功读取旧历史不代表上游恢复",
                sourceStatus=report.get("status"), failedSources=failed,
                checkedAt=report.get("checkedAt", report.get("retrievedAt")),
                errorCode=report.get("errorCode"), quotaStopDay=report.get("quotaStopDay")))
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            results.append(check(f"research.producer.{filename}", filename, "研究文件库",
                                 "error", "采集状态检查未完成", error=str(exc)))
    return results
