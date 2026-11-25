"""Normalize retained Choice reports; no network access on dashboard reads."""

import calendar
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from app.research_equity_metrics import number

TYPES = {
    "基金": "fund",
    "保险公司": "insurance",
    "保险产品": "insuranceProduct",
    "QFII": "qfii",
    "社保基金": "social",
    "企业年金": "pension",
    "基金管理公司": "fundManager",
    "基金资产管理计划": "fundAssetPlan",
    "券商": "broker",
    "券商集合理财": "brokerCollective",
    "银行": "bank",
    "信托公司": "trust",
    "信托计划": "trustPlan",
}
FIELDS = {
    "PCTBYFUND": "fund",
    "PCTBYINSUR": "insurance",
    "PCTYINSURPRO": "insuranceProduct",
    "PCTBYQFII": "qfii",
    "PCTBYSSFUND": "social",
    "PCTBYCORPPENSION": "pension",
}


def scaled(value, divisor=1):
    parsed = number(value)
    return str(parsed / Decimal(divisor)) if parsed is not None else None


def resident_market_rows(residents, closes, start_month):
    returns = {}
    previous = None
    for month, (day, close) in sorted(closes.items()):
        ordinal = int(month[:4]) * 12 + int(month[5:])
        if previous and previous[0] == ordinal - 1:
            returns[month] = (day, str((close / previous[1] - 1) * 100))
        previous = (ordinal, close)
    return [
        {**row, "indexDate": returns[row["date"][:7]][0],
         "marketReturnPct": returns[row["date"][:7]][1]}
        for row in residents
        if row["date"][:7] >= start_month and row["date"][:7] in returns
    ]


def report_day(raw):
    stamp = str(raw)[:10]
    return (datetime.strptime(stamp, "%m/%d/%Y").date() if "/" in stamp
            else date.fromisoformat(stamp)).isoformat()


def capital_event_months(job, records):
    dividends = job["key"].startswith("capital-events-cash-dividends-")
    totals, seen = {}, {}
    for row in records:
        if dividends:
            if row["SECURITYTYPE"] != "A股":
                continue
            cash, base = number(row["DIVCASHPSBFTAX"]), number(row["DIVRTISSBASESHARES"])
            if cash is None or cash <= 0 or base is None or base <= 0 or not row["DIVPAYDATE"]:
                continue
            day = report_day(row["DIVPAYDATE"])
            key = (row["SECUCODE"], row["REPORTDATE"], day, row["DIVIMPLANNCDATE"])
            amount = cash * base / Decimal(10000)
        else:
            amount = number(row["SUMFINA"])
            if amount is None or amount <= 0 or not row["ATTACHNAME"] or not row["DAT_SHANGSHIRIQI"]:
                continue
            day = report_day(row["DAT_SHANGSHIRIQI"])
            # One listing notice can cover different tranches (assets and cash).
            key = (row["MSECUCODE"], day, row["ATTACHNAME"], amount)
        if day > job["observationDate"]:
            continue
        if key in seen:
            if seen[key] != amount:
                raise ValueError("conflicting_capital_event")
            continue
        seen[key] = amount
        month = day[:7] + "-01"
        totals[month] = totals.get(month, Decimal(0)) + amount
    key = "dividends" if dividends else "seasonedIssuance"
    return [{"date": day, key: str(amount)} for day, amount in sorted(totals.items())]


def fund_stock_leaders(records, day):
    stocks = {}
    for item in records:
        code = item["MSECUCODE"]
        if not re.fullmatch(r"(?:\d{6}\.(?:SH|SZ|BJ))", str(code)):
            continue
        if report_day(item["REPORTDATE"]) != day or item["ORGTDYFPE"] != "基金" or code in stocks:
            raise ValueError("invalid_or_duplicate_fund_stock")
        value = number(item["DEC_BENQISHIZHI"])
        shares, prior = number(item["DEC_BENQICHIGU"]), number(item["DEC_SHANGQICHIGU"])
        if value is None or value <= 0:
            continue
        stocks[code] = {
            "code": code, "name": item["SECURITYSHORTNAME"], "valueYi": str(value / 10000),
            "fundCount": scaled(item["INT_CGJGJS"]),
            "shareChangeWan": str(shares - prior) if shares is not None and prior is not None else None,
        }
    return sorted(stocks.values(), key=lambda x: (-Decimal(x["valueYi"]), x["code"]))[:20]


def normalize(root: Path):
    plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
    names = plan["industryNames"]
    institutions, holdings, margins, issues, stamps = [], [], [], [], []
    previous_institutions = {}
    resident_closes = {}
    resident_market_fetched_at = None
    foreign_caps = {}
    capital_events = {}
    fund_stock_reports = []
    for job in sorted(plan["jobs"], key=lambda j: (j["observationDate"], j["key"])):
        path = root / (job["key"] + ".json")
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
        if doc["request"]["requestHash"] != job["requestHash"]:
            raise ValueError("capital_request_hash_mismatch")
        stamps.append(doc["fetchedAt"])
        if job["key"].startswith("public-fund-stocks-"):
            day = job["observationDate"]
            if rows := fund_stock_leaders(doc["data"], day):
                fund_stock_reports.append({"date": day, "rows": rows, "fetchedAt": doc["fetchedAt"]})
        elif job["key"].startswith("capital-events-"):
            kind = job["key"].removesuffix("-" + job["observationDate"])
            if rows := capital_event_months(job, doc["data"]):
                capital_events[kind] = {"rows": rows, "fetchedAt": doc["fetchedAt"],
                                        "through": job["observationDate"]}
        elif job["key"].startswith("foreign-market-cap-"):
            if not doc["data"]:
                continue
            row, = doc["data"]
            d = job["observationDate"]
            if row["CODES"] != "B_001071" or f"TradeDate={d}" not in job["options"].split(","):
                raise ValueError("capital_foreign_market_cap_identity_mismatch")
            value = number(row.get("SUMMV"))
            if value is not None and value > 0:
                foreign_caps[d[:7]] = (d, value / Decimal(100000000))
        elif job["key"].startswith("resident-market-"):
            _, start, end = job["args"]
            for item in doc["data"]:
                day = date.fromisoformat(str(item["DATES"]).replace("/", "-")[:10]).isoformat()
                close = number(item.get("CLOSE"))
                if item["CODES"] != "000300.SH" or not start <= day <= end:
                    raise ValueError("capital_resident_index_identity_or_date_mismatch")
                if close is not None and close > 0:
                    resident_closes[day[:7]] = (day, close)
            resident_market_fetched_at = doc["fetchedAt"]
        elif job["key"].startswith("institutions-"):
            row = {"date": job["observationDate"]}
            report_date = date.fromisoformat(row["date"])
            quarter_start = report_date.replace(month=(report_date.month - 1) // 3 * 3 + 1, day=1)
            previous_date = (quarter_start - timedelta(days=1)).isoformat()
            previous_row = {"date": previous_date, "sourceReportDate": row["date"]}
            for item in doc["data"]:
                if item["REPORTDATE"] != row["date"]:
                    raise ValueError("capital_report_date_mismatch")
                key = TYPES.get(item["ORGTDYFPE"])
                if key:
                    row[key] = scaled(item.get("DEC_BENQISHIZHI"), 10000)
                    prior_value = scaled(item.get("DEC_SHANGQISHIZHI"), 10000)
                    if prior_value is not None:
                        previous_row[key] = prior_value
            institutions.append(row)
            if len(previous_row) > 2:
                previous_institutions[previous_date] = previous_row
        elif job["key"].startswith("industry-holdings-"):
            for item in doc["data"]:
                holdings.append(
                    {
                        "date": job["observationDate"],
                        "code": item["CODES"],
                        "name": names[item["CODES"]],
                        **{v: scaled(item.get(k)) for k, v in FIELDS.items()},
                    }
                )
        elif job["key"].startswith("industry-margin-"):
            for item in doc["data"]:
                d = job["observationDate"]
                # cses DATES is the API processing date, not TradeDate.
                if f"TradeDate={d}," not in job["options"]:
                    raise ValueError("capital_trade_date_mismatch")
                balance, free = number(item.get("RZYE")), number(item.get("ALLFREEFLOATMV"))
                buy, turnover = number(item.get("SUMPURMONEY")), number(item.get("AMOUNTSUM"))
                margins.append(
                    {
                        "date": d,
                        "code": item["CODES"],
                        "name": names[item["CODES"]],
                        "balance": scaled(balance, 100000000),
                        "freeValue": scaled(free, 100000000),
                        "leverage": str(balance / free * 100)
                        if balance is not None and free and free > 0
                        else None,
                        "buyShare": str(buy / turnover * 100)
                        if buy is not None and turnover and turnover > 0
                        else None,
                    }
                )
        elif job["key"].startswith("fund-issues-"):
            for item in doc["data"]:
                match = re.fullmatch(r"(\d{4})年(\d{2})月", item["ENDDATE"])
                if not match:
                    raise ValueError("capital_issue_period_invalid")
                d = "-".join(match.groups()) + "-01"
                # First and last months may be partial; do not treat as complete months.
                start = re.search(r"StartDate=([\d-]+)", job["options"])[1]
                if d < start or d[:7] >= plan["asOf"][:7]:
                    continue
                issues.append(
                    {
                        "date": d,
                        "stock": scaled(item.get("FIRSTRAISES")),
                        "mixed": scaled(item.get("FIRSTRAISEM")),
                        "stockCount": scaled(item.get("TOTALNUMS")),
                        "mixedCount": scaled(item.get("TOTALNUMM")),
                    }
                )
    supplement_path = root / "public-supplement.json"
    supplement = (
        json.loads(supplement_path.read_text(encoding="utf-8")) if supplement_path.exists() else {}
    )
    as_of = date.fromisoformat(plan["asOf"])
    start_month = f"{as_of.year - 3}-{as_of.month:02d}"
    for series in capital_events.values():
        series["rows"] = [r for r in series["rows"] if r["date"][:7] > start_month]
    foreign_value_share = []
    for row in supplement.get("foreign", []):
        month = row["date"][:7]
        equities = number(row.get("equities"))
        if month >= start_month and month in foreign_caps and equities is not None:
            market_date, market_cap = foreign_caps[month]
            foreign_value_share.append({**row, "marketDate": market_date,
                                        "sharePct": str(equities / market_cap * 100)})
    fund_reports = {r["date"]: r for r in fund_stock_reports}
    for path in sorted(root.glob("fund-stocks-css-*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["date"] not in fund_reports:
            fund_reports[report["date"]] = report
    north_industries = [json.loads(path.read_text(encoding="utf-8"))
                        for path in sorted(root.glob("north-industry-*.json"))]
    benchmark_months = {}
    for row in margins:
        if row["date"][5:7] in {"03", "06", "09", "12"} and row["freeValue"] is not None:
            days = benchmark_months.setdefault(row["date"][:7], {})
            days.setdefault(row["date"], {})[row["name"]] = Decimal(row["freeValue"])
    fund_benchmarks = []
    for month, choices in sorted(benchmark_months.items()):
        trade_day = max(choices)
        industries = choices[trade_day]
        if month < start_month or month >= plan["asOf"][:7] or len(industries) != len(names) or min(industries.values()) <= 0:
            continue
        total = sum(industries.values())
        fund_benchmarks.append({"date": month + "-" + str(calendar.monthrange(int(month[:4]), int(month[5:]))[1]),
                                "tradeDate": trade_day,
                                "rows": [{"name": name, "weightPct": str(value / total * 100)}
                                         for name, value in sorted(industries.items(), key=lambda p: (-p[1], p[0]))]})
    institution_dates = {row["date"] for row in institutions}
    return {
        "source": "Choice EMQuantAPI · 机构类型统计 / 基金发行统计 / 申万一级行业",
        "fetchedAt": max(stamps, default=None),
        "asOf": plan["asOf"],
        "institutions": sorted(
            [*institutions, *(row for day, row in previous_institutions.items()
                              if day not in institution_dates)],
            key=lambda row: row["date"],
        ),
        "holdings": sorted(holdings, key=lambda x: (x["date"], x["code"])),
        "margins": sorted(margins, key=lambda x: (x["date"], x["code"])),
        "issues": sorted({r["date"]: r for r in issues}.values(), key=lambda x: x["date"]),
        "bank": supplement.get("bank", []),
        "residents": supplement.get("residents", []),
        "residentMarket": resident_market_rows(supplement.get("residents", []), resident_closes, start_month),
        "residentMarketFetchedAt": resident_market_fetched_at,
        "foreign": supplement.get("foreign", []),
        "foreignValueShare": foreign_value_share,
        "northIndustryReports": [r for r in north_industries if f"{start_month}-{as_of.day:02d}" <= r["date"] <= plan["asOf"]],
        "fundIndustryBenchmarks": fund_benchmarks,
        "capitalEvents": capital_events,
        "fundStockReports": [r for day, r in sorted(fund_reports.items())
                             if f"{start_month}-{as_of.day:02d}" <= day <= plan["asOf"]],
        "social": supplement.get("social", []),
        "pension": [r for r in supplement.get("pension", []) if r["date"][:7] >= start_month],
        "occupationalPension": [r for r in supplement.get("occupationalPension", []) if r["date"][:7] >= start_month],
        "publicSources": supplement.get("sources", {}),
        "publicFetchedAt": supplement.get("publicFetchedAt"),
    }


def publish(root: Path):
    output = normalize(root / "research/capital-handbook-choice")
    path = root / "public/v1/equity/cn-capital-handbook.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return output


async def refresh():
    """Run bounded collectors independently of dashboard reads, with durable daily cadence."""
    import asyncio
    import subprocess
    import sys
    from datetime import UTC, datetime, timedelta

    from app.research_capital_public import collect_public, read, save
    from app.research_local_data import hedge_board_data_root

    root = hedge_board_data_root()
    work = root / "research/capital-handbook-choice"
    await collect_public(root)
    path = work / "refresh-state.json"
    state = read(path)
    now = datetime.now(UTC)
    if not state.get("attemptedAt") or now - datetime.fromisoformat(state["attemptedAt"]) >= timedelta(hours=24):
        state.update(attemptedAt=now.isoformat(), status="running")
        save(path, state)
        try:
            command = [getattr(sys, "_base_executable", sys.executable),
                       str(Path(__file__).resolve().parents[1] / "scripts/collect_capital_handbook.py"),
                       "--collect", "--incremental", "--data-root", str(root)]
            codes = []
            for flags in (
                ["--max-cells", "3000", "--exclude-job-prefix", "capital-events-"],
                ["--max-cells", "180000", "--job-prefix", "capital-events-"],
                ["--max-cells", "96000", "--job-prefix", "public-fund-stocks-"],
                ["--north-quarters", "2"],
            ):
                result = await asyncio.to_thread(
                    subprocess.run, command + flags, capture_output=True, timeout=600,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                codes.append(result.returncode)
            state.update(status="ready" if not any(codes) else "partial", returnCodes=codes)
            if not any(codes):
                state["completedAt"] = datetime.now(UTC).isoformat()
        except Exception as exc:
            state.update(status="error", error=type(exc).__name__)
        save(path, state)
    if (work / "plan.json").exists():
        await asyncio.to_thread(publish, root)
