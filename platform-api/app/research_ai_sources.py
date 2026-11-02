"""Public secondary financial checks, issuer operating KPIs and reported CDS trades."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from bs4 import BeautifulSoup

from app.research_ai_financials import number


def table_data(content):
    """Read only the visible public HTML table cells, no embedded paid state."""
    soup = BeautifulSoup(content, "html.parser")
    result = []
    for table in soup.select("table"):
        headers = table.select("thead tr")
        if len(headers) < 2:
            continue
        titles = [cell.get_text(" ", strip=True) for cell in headers[0].find_all(["td", "th"])][1:]
        dates = []
        for cell in headers[1].find_all(["td", "th"])[1:]:
            match = re.search(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", cell.get_text(" ", strip=True))
            dates.append(
                datetime.strptime(match[0], "%b %d, %Y").date().isoformat() if match else None
            )
        if not dates or len(dates) != len(titles):
            continue
        for row in table.select("tbody tr"):
            cells = row.find_all(["td", "th"], recursive=False)
            if len(cells) < 2:
                continue
            label = cells[0].get_text(" ", strip=True)
            for title, day, cell in zip(titles, dates, cells[1:], strict=False):
                text = cell.get_text(" ", strip=True).replace("\u2212", "-")
                if day and text not in ("", "-", "—", "Upgrade"):
                    result.append({"label": label, "date": day, "period": title, "raw": text})
    return result


def parse_display(text, default_multiplier=1):
    match = re.fullmatch(r"\$?\s*([+-]?[\d,]+(?:\.\d+)?)\s*([BMKT%]?)", text)
    if not match:
        return None, None
    value = number(match[1].replace(",", ""))
    if value is None:
        return None, None
    suffix = match[2]
    multiplier = {"B": 10**9, "M": 10**6, "K": 1000, "T": 10**12, "%": 1}.get(
        suffix, default_multiplier
    )
    return value * multiplier, "percent" if suffix == "%" else None


def financial_checks(company, content, source_url, kind):
    metric_names = {
        "Revenue": "revenue",
        "Revenue Revenue Growth": "revenue",
        "Operating Cash Flow": "cfo",
        "Capital Expenditures": "capex",
    }
    annuals = {row["end"]: row for row in company["annual"]}
    checks = []
    # Stock Analysis financial statements identify USD millions in their page.
    text = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
    if "millions" not in text.lower() or "USD" not in text:
        raise ValueError("Secondary statement unit missing")
    for row in table_data(content):
        key = metric_names.get(row["label"])
        if not key or row["period"] == "TTM" or row["date"] not in annuals:
            continue
        value, _ = parse_display(row["raw"], 10**6)
        primary = annuals[row["date"]]["values"].get(key)
        if value is None or primary is None:
            continue
        if key == "capex":
            value = -value  # Secondary cash-flow tables show outflows as negatives.
        difference = (
            abs(value - primary) / abs(primary) * 100
            if primary
            else (Decimal(0) if not value else None)
        )
        checks.append(
            {
                "metric": key,
                "date": row["date"],
                "primary": primary,
                "secondary": value,
                "differencePct": difference,
                "status": "consistent"
                if difference is not None and difference <= 1
                else "difference",
                "sourceUrl": source_url,
                "source": "Stock Analysis · USD millions",
            }
        )
    # Keep the most recent matched annual period per metric.
    if not checks:
        raise ValueError("No comparable secondary annual values")
    return [
        max([row for row in checks if row["metric"] == metric], key=lambda row: row["date"])
        for metric in set(row["metric"] for row in checks)
    ]


KPI_PATTERN = re.compile(
    r"Annual Recurring|\bARR\b|\bRPO\b|Remaining Performance|Retention|Backlog|Bookings|"
    r"Cloud|Azure|AWS|Data Center|Subscription Revenue|Product Revenue|AI |"
    r"Artificial Intelligence|Customer",
    re.I,
)


def operating_kpis(content, source_url):
    output = {}
    for row in table_data(content):
        if not KPI_PATTERN.search(row["label"]) or row["period"] == "TTM":
            continue
        value, unit = parse_display(row["raw"])
        if value is None:
            continue
        name = row["label"]
        count_metric = bool(
            re.search(
                r"^(?:Total )?Customers(?:\s|$)|Customer Count|Number of|"
                r"Data Centers Operated|Buildings",
                name,
                re.I,
            )
        )
        stock = bool(
            re.search(
                r"ARR|Recurring Revenue|RPO|Remaining Performance|Retention|Backlog|Customer",
                name,
                re.I,
            )
        )
        unit = unit or (
            "count"
            if count_metric
            else (
                "USD"
                if re.search(
                    r"Revenue|ARR|Recurring|RPO|Performance|Backlog|Booking|Orders|Income|Profit|Earnings|ACV",
                    name,
                    re.I,
                )
                else "count"
            )
        )
        kind = (
            "ARR"
            if re.search(r"ARR|Annual Recurring", name, re.I) and unit == "USD"
            else "RPO"
            if re.search(r"RPO|Remaining Performance", name, re.I)
            else "留存率"
            if re.search(r"Retention", name, re.I)
            else "订单/积压"
            if re.search(r"Backlog|Booking|Orders", name, re.I)
            else "业务收入/增长"
            if re.search(r"Revenue|Cloud|Azure|AWS|Data Center", name, re.I)
            else "客户与用量"
        )
        if count_metric:
            kind = "客户与用量"
        item = output.setdefault(
            name,
            {
                "name": name,
                "kind": kind,
                "unit": unit,
                "basis": "财年至今累计披露"
                if "(YTD)" in name
                else ("期末存量/披露点" if stock else "单季业务披露"),
                "source": "Stock Analysis · issuer operating metrics",
                "sourceUrl": source_url,
                "history": [],
            },
        )
        item["history"].append({"date": row["date"], "value": value})
    for item in output.values():
        points = {row["date"]: row for row in item["history"]}
        item["history"] = [points[day] for day in sorted(points)]
        item["latest"] = item["history"][-1]
    return list(output.values())


def reported_cds(document, ticker):
    meta = document["meta"]
    if meta.get("ticker") != ticker or meta.get("units") != "basis points":
        raise ValueError("CDS identity/unit mismatch")
    points = []
    seen = set()
    for row in document["rows"]:
        day = datetime.strptime(row["date"], "%Y-%m-%d").date().isoformat()
        if day in seen:
            raise ValueError("Duplicate CDS trade date")
        seen.add(day)
        value = number(row.get("reported_bp"))
        if value is None:
            continue  # Never turn either upfront-model scenario into a quote.
        if value < 0 or not isinstance(row.get("reported_n"), int) or row["reported_n"] <= 0:
            raise ValueError("Invalid reported CDS observation")
        points.append({"date": day, "value": value, "trades": row["reported_n"]})
    if not points:
        raise ValueError("No explicitly reported CDS spreads")
    points.sort(key=lambda row: row["date"])
    expected = meta.get("field_coverage", {}).get("reported_bp", {})
    if expected.get("observations") != len(points) or expected.get("as_of") != points[-1]["date"]:
        raise ValueError("CDS coverage metadata disagrees")
    return {
        "ticker": ticker,
        "unit": "bp",
        "tenor": "约5年 · USD高级公司CDS",
        "method": "公开成交运行利差的日中位数；非连续交易商收盘报价",
        "history": points,
        "latest": points[-1],
        "tapeThrough": meta.get("tape_through"),
        "source": "DTCC public tape · third-party aggregation",
        "sourceUrl": "https://charts.allofthesewords.com/"
        + ("oracle" if ticker == "ORCL" else "nvda")
        + "-cds.html",
        "upstreamUrl": "https://pddata.dtcc.com/ppd/",
    }


def issuer_disclosures(content, ticker, period, url):
    """Extract a small set of explicit issuer statements, preserving bounds/scope."""
    text = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
    patterns = {
        "CRM": [
            (
                "Agentforce + Data 360 ARR",
                r"Agentforce and Data 360 annual recurring revenue.{0,25}"
                r"reached nearly \$([\d.]+) billion",
                "约",
                "ARR",
            ),
            ("Agentforce ARR", r"Agentforce ARR exceeded \$([\d.]+) billion", "超过", "ARR"),
        ],
        "MSFT": [
            (
                "公司披露季度资本开支",
                r"[Cc]apital expenditures.{0,40}\$([\d.]+) billion",
                "",
                "季度投入",
            ),
            ("公司披露季度融资租赁", r"\$([\d.]+) billion.{0,25}finance leases", "", "融资租赁"),
        ],
        "META": [],
    }
    rows = []
    for name, pattern, qualifier, kind in patterns.get(ticker, []):
        match = re.search(pattern, text)
        if match:
            rows.append(
                {
                    "name": name,
                    "kind": kind,
                    "unit": "USD",
                    "qualifier": qualifier,
                    "value": Decimal(match[1]) * 10**9,
                    "date": period,
                    "sourceUrl": url,
                    "source": "公司投资者关系披露",
                    "excerpt": match[0],
                    "basis": "Agentforce口径自Q2 FY27扩展；两项ARR存在包含关系，不相加。"
                    if ticker == "CRM"
                    else "公司披露口径；与现金流量表购建支出分别展示，不自动相加。",
                }
            )
    # Guidance belongs to a calendar year, never silently assigned to a fiscal quarter.
    match = (
        re.search(
            r"2026.{0,55}capital expenditures.{0,110}?\$([\d.]+)\s*"
            r"(?:billion\s*)?(?:to|[-–])\s*\$?([\d.]+) billion",
            text,
            re.I,
        )
        if ticker == "META"
        else None
    )
    if match:
        rows.append(
            {
                "name": "CY2026 资本开支指引",
                "kind": "年度指引",
                "unit": "USD",
                "value": Decimal(match[1]) * 10**9,
                "upper": Decimal(match[2]) * 10**9,
                "date": period,
                "sourceUrl": url,
                "source": "公司投资者关系披露",
                "basis": "全年指引，包含融资租赁本金偿付；非已实现开支。",
                "excerpt": match[0],
            }
        )
    if not rows:
        raise ValueError("No supported issuer disclosure matched")
    return rows
