"""Dated exchange margin inputs for the ETF tracking read model."""

import io
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd

from app import research_etf_tracking as tracking
from app.research_etf_native import INDEX_SYMBOLS, SZSE, YI, get, number, xlsx_rows

SSE_MARGIN = "https://query.sse.com.cn/marketdata/tradedata/queryMargin.do"
CSI = "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/"
CNI = "https://www.cnindex.com.cn/sample-detail/download-history"


def collect_day(client, day):
    response = get(
        client,
        SSE_MARGIN,
        params={
            "isPagination": "true",
            "tabType": "mxtype",
            "detailsDate": day.replace("-", ""),
            "pageHelp.pageSize": 5000,
            "pageHelp.pageNo": 1,
        },
        headers={"Referer": "https://www.sse.com.cn/"},
    )
    result = {}
    for row in response.json()["result"]:
        if row["opDate"] != day.replace("-", ""):
            raise ValueError("SSE margin date mismatch")
        buy, repayment = number(row["rzmre"]), number(row["rzche"])
        result[row["stockCode"]] = {
            "date": day,
            "financing_balance_yi": str(number(row["rzye"]) / YI),
            "financing_buy_yi": str(buy / YI),
            "financing_repayment_yi": str(repayment / YI),
            "financing_net_buy_yi": str((buy - repayment) / YI),
        }
    if not result:
        raise ValueError("SSE margin unpublished: " + day)
    response = get(
        client,
        SZSE,
        params={"SHOWTYPE": "xlsx", "CATALOGID": "1837_xxpl", "txtDate": day, "TABKEY": "tab2"},
        headers={"Referer": "https://www.szse.cn/disclosure/margin/margin/index.html"},
    )
    rows = iter(xlsx_rows(response.content))
    header = next(rows)
    if header[:4] != ["证券代码", "证券简称", "融资买入额(元)", "融资余额(元)"]:
        raise ValueError("SZSE margin units changed")
    for row in rows:
        if len(row) != len(header) or not row[0].isdigit():
            continue
        result[row[0].zfill(6)] = {
            "date": day,
            "financing_buy_yi": str(number(row[2]) / YI),
            "financing_balance_yi": str(number(row[3]) / YI),
            "securities_lending_balance_yi": str(number(row[6]) / YI),
            "margin_balance_yi": str(number(row[7]) / YI),
            "financing_net_buy_yi": None,
            "financing_repayment_yi": None,
        }
    return result


def refresh(client, state, universe, *, pending_only=False):
    now = datetime.now(UTC).isoformat()
    day, prior_day = state["sessions"][-1], state["sessions"][-2]
    members = [m for m in universe if m.get("dashboard_eligible")]

    def pending(path):
        doc = tracking.read(path)
        return not (
            doc.get("status") == "ready"
            and (doc.get("data", {}).get("rows") or [{}])[-1].get("date") == day
        )

    fund_updates = [m for m in members if not pending_only or pending("margin/etfs/" + m["code"])]
    group_updates = [key for key in INDEX_SYMBOLS if not pending_only or pending("margin/" + key)]
    if not fund_updates and not group_updates:
        return []
    current, prior = collect_day(client, day), collect_day(client, prior_day)
    for code, row in current.items():
        if row["financing_net_buy_yi"] is None and code in prior:
            change = number(row["financing_balance_yi"]) - number(
                prior[code]["financing_balance_yi"]
            )
            row.update(
                {
                    "financing_net_buy_yi": str(change),
                    "financing_repayment_yi": str(number(row["financing_buy_yi"]) - change),
                    "net_buy_method": "financing_balance_change",
                }
            )
    for meta in fund_updates:
        path = "margin/etfs/" + meta["code"]
        old = tracking.read(path)
        data = old.get("data", {"meta": {"code": meta["code"]}, "rows": []})
        history = {r["date"]: r for r in data["rows"]}
        row = current.get(meta["code"])
        if row:
            history[day] = row
        tracking.write(
            path,
            {
                "data": {**data, "rows": [history[d] for d in sorted(history)]},
                "status": "ready" if row else ("stale" if history else "no_data"),
                "url": SSE_MARGIN if meta["exchange"] == "SH" else SZSE,
                "fetchedAt": now if row else old.get("fetchedAt"),
                "attemptedAt": now,
            },
        )

    def group(key):
        old = tracking.read("margin/" + key)
        doc = old.get("data", {"meta": {}, "rows": []})
        history = {r["date"]: r for r in doc["rows"]}
        etfs = [m for m in members if tracking.index_key(m) == key]
        row = {"date": day}
        for field in (
            "financing_balance_yi",
            "financing_buy_yi",
            "financing_repayment_yi",
            "financing_net_buy_yi",
        ):
            values = [current.get(m["code"], {}).get(field) for m in etfs]
            row["etf_group_" + field] = (
                str(sum((number(v) for v in values), Decimal(0)))
                if values and all(v is not None for v in values)
                else None
            )
        row["etf_group_coverage"] = f"{sum(m['code'] in current for m in etfs)}/{len(etfs)}"
        error = None
        source_url = (
            CNI if key in ("chinext", "sz100") else CSI + INDEX_SYMBOLS[key][2:] + "cons.xls"
        )
        try:
            symbol = INDEX_SYMBOLS[key][2:]
            response = (
                get(client, CNI, params={"indexcode": symbol})
                if key in ("chinext", "sz100")
                else get(client, CSI + symbol + "cons.xls")
            )
            frame = pd.read_excel(io.BytesIO(response.content), dtype=str)
            source_url = str(response.url)
            codes = set(frame.iloc[:, 1 if key in ("chinext", "sz100") else 4].str.zfill(6))
            as_of = max(str(v).replace("-", "")[:8] for v in frame.iloc[:, 0])
            if not codes or as_of > day.replace("-", ""):
                raise ValueError("constituents are newer than margin date")
            for field in ("financing_balance_yi", "financing_net_buy_yi"):
                values = [current.get(code, {}).get(field) for code in codes]
                covered = [number(v) for v in values if v is not None]
                row["index_" + field] = str(sum(covered)) if covered else None
            row["index_coverage_pct"] = str(
                Decimal(sum(code in current for code in codes)) / len(codes) * 100
            )
            row["index_total_constituents"] = len(codes)
        except Exception as exc:
            error = str(exc)[:160]
            row.update(
                {
                    "index_financing_balance_yi": None,
                    "index_financing_net_buy_yi": None,
                    "index_coverage_pct": None,
                }
            )
        history[day] = row
        tracking.write(
            "margin/" + key,
            {
                "data": {**doc, "rows": [history[d] for d in sorted(history)]},
                "status": "stale" if error else "ready",
                "url": source_url,
                "sourceUrls": [SSE_MARGIN, SZSE, source_url],
                "fetchedAt": now,
                "attemptedAt": now,
                "error": error,
            },
        )
        return {"source": "margin/" + key, "error": error} if error else None

    with ThreadPoolExecutor(max_workers=3) as pool:
        return [failure for failure in pool.map(group, group_updates) if failure]
