"""Parse public fund disclosures without executing upstream JavaScript."""

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

TYPES = {"股票型", "混合型-偏股", "混合型-灵活"}
HK_INDUSTRIES = {
    "10": "能源",
    "15": "原材料",
    "20": "工业",
    "25": "非必需消费品",
    "30": "必需消费品",
    "35": "医疗保健",
    "40": "金融",
    "45": "信息技术",
    "50": "通信服务",
    "55": "公用事业",
    "60": "房地产",
}


def number(value, multiplier=1):
    text = str(value).strip().replace(",", "").removesuffix("%")
    if text in {"", "--", "---", "None", "null", "—"}:
        return None
    try:
        result = Decimal(text) * Decimal(multiplier)
    except InvalidOperation as exc:
        raise ValueError("invalid financial number") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("invalid financial number")
    return str(result)


def report_date(value):
    stamp = str(value)[:10]
    date.fromisoformat(stamp)
    if stamp[5:] not in {"03-31", "06-30", "09-30", "12-31"}:
        raise ValueError("not a quarter end")
    return stamp


def catalog(body):
    match = re.fullmatch(r"\s*var r\s*=\s*(\[.*\]);?\s*", body, re.S)
    if not match:
        raise ValueError("invalid fund directory")
    records = json.loads(match[1])
    groups = {}
    for row in records:
        code, _, name, kind, *_ = row
        if kind not in TYPES or "后端" in name:
            continue
        if not re.fullmatch(r"\d{6}", code):
            raise ValueError("invalid fund code")
        # Share-class suffixes only, never remove meaningful words from names.
        key = re.sub(r"[A-Z]+$", "", name)
        group = groups.setdefault((key, kind), [])
        group.append({"code": code, "name": name, "type": kind})
    output = []
    for (name, _kind), rows in groups.items():
        rows.sort(key=lambda r: (not r["name"].endswith("A"), r["code"]))
        output.append({**rows[0], "groupName": name, "classes": rows})
    if not output or len({r["code"] for r in output}) != len(output):
        raise ValueError("empty or duplicate fund directory")
    return sorted(output, key=lambda r: r["code"])


def archive_html(body):
    # The content property is a JS quoted string; JSON's strict string grammar
    # plus the site's escaped single quote is sufficient. Never eval the object.
    match = re.search(r'\bcontent\s*:\s*("(?:\\.|[^"\\])*")', body, re.S)
    if not match:
        raise ValueError("missing fund archive content")
    return BeautifulSoup(json.loads(match[1].replace("\\'", "'")), "html.parser")


def table_rows(table):
    return [
        [cell.get_text("", strip=True) for cell in row.find_all(["th", "td"])]
        for row in table.find_all("tr")
    ]


def allocations(body, code):
    soup = BeautifulSoup(body, "html.parser")
    if f"({code})" not in soup.title.get_text():
        raise ValueError("allocation identity mismatch")
    table = next((t for t in soup.select("table") if "股票占净比" in t.get_text()), None)
    if table is None:
        raise ValueError("allocation table absent")
    output = []
    for cells in table_rows(table)[1:]:
        if len(cells) != 5:
            raise ValueError("allocation columns changed")
        if cells[0][5:] not in {"03-31", "06-30", "09-30", "12-31"}:
            continue
        output.append(
            {
                "date": report_date(cells[0]),
                "stockPct": number(cells[1]),
                "bondPct": number(cells[2]),
                "cashPct": number(cells[3]),
                "navYuan": number(cells[4], 100000000),
            }
        )
    if not output:
        raise ValueError("empty allocations")
    return output


def sizes(body):
    soup = archive_html(body)
    table = soup.select_one("table")
    if table is None or "期间申购" not in table.get_text() or "亿份" not in table.get_text():
        raise ValueError("size units changed")
    output = []
    for cells in table_rows(table)[1:]:
        if len(cells) != 6:
            raise ValueError("size columns changed")
        # Non-quarter rows (e.g. inception) do not belong to period comparisons.
        if cells[0][5:] not in {"03-31", "06-30", "09-30", "12-31"}:
            continue
        output.append(
            {
                "date": report_date(cells[0]),
                "subscriptions": number(cells[1], 100000000),
                "redemptions": number(cells[2], 100000000),
                "shares": number(cells[3], 100000000),
                "navYuan": number(cells[4], 100000000),
            }
        )
    if not output:
        raise ValueError("empty size history")
    return output


def holdings(body, code):
    soup = archive_html(body)
    output = []
    for box in soup.select(".boxitem"):
        heading, table = box.select_one("h4"), box.select_one("table")
        if heading is None or table is None:
            continue
        if not heading.select_one(f'a[href*="/{code}.html"]'):
            raise ValueError("holding identity mismatch")
        stamp = report_date(heading.select_one("font").get_text(strip=True))
        headers = table_rows(table)[0]
        if (
            "股票代码" not in headers
            or not any("万股" in h for h in headers)
            or not any("万元" in h for h in headers)
        ):
            raise ValueError("holding columns or units changed")
        index = {
            key: next(i for i, h in enumerate(headers) if key in h)
            for key in ("股票代码", "股票名称", "占净值", "持股数", "持仓市值")
        }
        rows = []
        for tr in table.select("tbody tr"):
            cells = [c.get_text("", strip=True) for c in tr.select("td")]
            if not cells:
                continue
            security = cells[index["股票代码"]].replace("*", "")
            link = tr.select("td")[index["股票代码"]].select_one("a")
            market = "HK" if link and "/116." in link.get("href", "") else "CN"
            if not re.fullmatch(r"\d{5,6}", security):
                raise ValueError("unsupported security identity")
            rows.append(
                {
                    "code": security,
                    "market": market,
                    "name": cells[index["股票名称"]].replace("*", ""),
                    "weightPct": number(cells[index["占净值"]]),
                    "shares": number(cells[index["持股数"]], 10000),
                    "valueYuan": number(cells[index["持仓市值"]], 10000),
                }
            )
        if len({(r["market"], r["code"]) for r in rows}) != len(rows):
            raise ValueError("duplicate securities")
        # The endpoint's annual response may mix 10-name quarterly extracts
        # and fuller half/year-end tables. Preserve the actual completeness.
        footer = box.select_one(".tfoot")
        more = footer is not None and "显示全部" in footer.get_text()
        coverage = "full" if stamp[5:] in {"06-30", "12-31"} and not more else "top10"
        output.append({"date": stamp, "coverage": coverage, "rows": rows})
    if not output:
        raise ValueError("empty holding periods")
    return output


def industries(body, code):
    data = json.loads(body, parse_float=Decimal)["Data"]
    if not data or data["FundCode"] != code:
        raise ValueError("industry identity mismatch")
    output = []
    for quarter in data["QuarterInfos"]:
        stamp = report_date(quarter["JZRQ"])
        rows = []
        for row in quarter["HYPZInfo"]:
            if row["BZDM"] != code or report_date(row["FSRQ"]) != stamp:
                raise ValueError("industry row identity mismatch")
            key = row["HYDM"]
            if key in {"合计", "合计 ", "sum", "SUM"} or row["HYMC"] == "合计":
                continue
            # Mainland SZ is in CNY 10,000; HK SZ is CNY. Use disclosed
            # weights directly rather than mixing these incompatible units.
            market = "CN" if re.fullmatch(r"[A-S]", key) else "HK"
            rows.append(
                {
                    "code": key,
                    "name": HK_INDUSTRIES.get(key, row["HYMC"]) if market == "HK" else row["HYMC"],
                    "market": market,
                    "weightPct": number(row["ZJZBL"]),
                }
            )
        if len({(r["market"], r["code"]) for r in rows}) != len(rows):
            raise ValueError("duplicate industries")
        output.append({"date": stamp, "rows": rows})
    if not output:
        raise ValueError("empty industries")
    return output


def profile(body, code):
    soup = BeautifulSoup(body, "html.parser")
    if f"({code})" not in soup.title.get_text():
        raise ValueError("profile identity mismatch")
    values = {}
    for th in soup.select("table th"):
        cell = th.find_next("td")
        if cell:
            values[th.get_text(strip=True)] = cell.get_text(" ", strip=True)
    name = values.get("基金全称")
    if not name or values.get("基金类型") not in TYPES:
        raise ValueError("fund is not an active equity candidate")
    return {
        "legalName": name,
        "manager": values.get("基金经理人"),
        "company": values.get("基金管理人"),
        "benchmark": values.get("业绩比较基准"),
    }


def reports(body, code):
    data = json.loads(body)
    if data.get("ErrCode") not in (None, 0):
        raise ValueError("report index rejected")
    output = []
    for row in data["Data"]:
        if row["FUNDCODE"] != code:
            raise ValueError("report identity mismatch")
        title = row["TITLE"]
        numeric_title = title.translate(str.maketrans("〇零一二三四五六七八九", "00123456789"))
        year = re.search(r"(20\d{2})年", numeric_title)
        if not year:
            continue
        suffix = next(
            (
                s
                for text, s in (
                    ("第1季度", "03-31"),
                    ("第2季度", "06-30"),
                    ("第3季度", "09-30"),
                    ("第4季度", "12-31"),
                    ("中期报告", "06-30"),
                    ("半年度报告", "06-30"),
                    ("年度报告", "12-31"),
                )
                if text in numeric_title
            ),
            None,
        )
        if suffix is None:
            continue
        published = row["PUBLISHDATE"][:10]
        date.fromisoformat(published)
        if not re.fullmatch(r"AN\d+", row["ID"]):
            raise ValueError("invalid report link")
        output.append(
            {
                "date": f"{year[1]}-{suffix}",
                "publishedAt": published,
                "title": title,
                "url": f"https://pdf.dfcfw.com/pdf/H2_{row['ID']}_1.pdf",
            }
        )
    if not output:
        raise ValueError("empty report index")
    return output
