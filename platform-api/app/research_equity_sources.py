"""Bounded public-source collection with original responses and per-source LKG.

No access-control bypass, implicit credentials, zero filling, or requests from GET.
"""

import asyncio
import hashlib
import io
import json
import re
import ssl
import threading
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import truststore
from bs4 import BeautifulSoup

from app.research_equity_catalog import CN_INDICES
from app.research_equity_metrics import number
from app.research_local_data import hedge_board_data_root, read_local_json, write_local_json
from app.research_provider_errors import ResearchProviderError

HKMA_URL = "https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T020303.xls"
EASTMONEY_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
TSF_URL = "https://data.mofcom.gov.cn/datamofcom/front/gnmy/shrzgmQuery"
PBC_URL = "https://www.pbc.gov.cn/diaochatongjisi/116219/index.html"
MULTPL_URL = "https://www.multpl.com/s-p-500-pe-ratio/table/by-month"
_ARTIFACT_IO_LOCK = threading.RLock()


def read_artifact(name):
    try:
        with _ARTIFACT_IO_LOCK:
            return read_local_json(f"public/v1/equity/{name}.json")
    except ResearchProviderError as exc:
        if "local_data_not_found:" in str(exc):
            return {}
        raise


def publish_artifact(name, payload):
    # Decimal is serialized as text throughout the public research boundary.
    normalized = json.loads(json.dumps(payload, default=str))
    # Windows cannot replace a file while our GET reader holds its handle.
    # Serialize only local artifact I/O; no network request holds this lock.
    # The producer's OS file lock separately prevents concurrent producers.
    with _ARTIFACT_IO_LOCK:
        write_local_json(f"public/v1/equity/{name}.json", normalized)


def archive(source_id, content, now):
    digest = hashlib.sha256(content).hexdigest()
    path = hedge_board_data_root() / "raw" / "equity" / source_id / now[:10] / f"{digest}.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)
    return digest


def parse_csi(content):
    frame = pd.read_excel(io.BytesIO(content))
    columns = frame.columns.tolist()
    if len(columns) != 10 or not str(columns[6]).startswith("市盈率1"):
        raise ValueError("csi_schema_changed")
    rows = []
    for raw in frame.itertuples(index=False, name=None):
        day = datetime.strptime(str(int(raw[0])), "%Y%m%d").date().isoformat()
        rows.append(
            {
                "date": day,
                "pe": number(raw[6]),
                "peIndexWeight": number(raw[7]),
                "dividend": number(raw[8]),
                "dividendIndexWeight": number(raw[9]),
            }
        )
    return rows


def parse_pbc_tsf(content):
    frame = pd.read_excel(io.BytesIO(content), header=None)
    header = " ".join(str(v) for v in frame.iloc[:11, :2].values.ravel())
    if "社会融资规模增量" not in header or not re.search(r"(?<!万)亿元人民币", header):
        raise ValueError("pbc_tsf_schema_changed")
    rows = []
    for raw in frame.itertuples(index=False, name=None):
        # PBC numeric year.month cells use .01 through .12; .1 is October.
        label = f"{raw[0]:.2f}" if isinstance(raw[0], (float, int)) else str(raw[0]).strip()
        match = re.fullmatch(r"(20\d{2})\.(\d{2})", label)
        value = number(raw[1])
        if match and 1 <= int(match[2]) <= 12 and value is not None:
            rows.append({"date": f"{match[1]}-{match[2]}", "value": value})
    if not rows or len({r["date"] for r in rows}) != len(rows):
        raise ValueError("pbc_tsf_dates_invalid")
    return rows


async def collect_pbc_tsf(client, response, stamp):
    manifest = []

    async def follow(text):
        nonlocal response
        soup = BeautifulSoup(response.content, "html.parser")
        link = next((a for a in soup.select("a[href]") if text in a.get_text(strip=True)), None)
        if link is None:
            raise ValueError("pbc_tsf_link_missing")
        url = urljoin(str(response.url), link["href"])
        if urlparse(url).scheme != "https" or urlparse(url).hostname != "www.pbc.gov.cn":
            raise ValueError("pbc_tsf_link_invalid")
        response = await client.get(url)
        response.raise_for_status()
        digest = await asyncio.to_thread(archive, "cn_tsf_pbc", response.content, stamp)
        manifest.append({"url": url, "sha256": digest})

    await follow(f"{stamp[:4]}年统计数据")
    await follow("社会融资规模")
    # The national flow table precedes the stock and provincial tables.
    await follow("xls")
    rows = await asyncio.to_thread(parse_pbc_tsf, response.content)
    for row in rows:
        row.update(sourceUrl=str(response.url), rawSha256=manifest[-1]["sha256"])
    return rows, manifest


def parse_multpl(content):
    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table", id="datatable")
    if table is None:
        raise ValueError("multpl_table_missing")
    rows = []
    for tr in table.select("tr"):
        cells = tr.select("td")
        if len(cells) != 2:
            continue
        text = cells[0].get_text(" ", strip=True)
        estimated = "†" in tr.get_text()
        day = datetime.strptime(text.replace("†", "").strip(), "%b %d, %Y").date().isoformat()
        pe = number(
            cells[1].get_text(strip=True).replace(",", "").replace("†", "").replace("%", "").strip()
        )
        if pe is not None and pe > 0:
            rows.append({"date": day, "pe": pe, "estimated": estimated})
    return rows


def parse_hkma_money(content):
    frame = pd.read_excel(io.BytesIO(content), header=None)
    # Table 2.3.3 is ALL currencies, in HK$ million. Never use the HKD-only table.
    if (
        frame.shape[1] != 15
        or "All currencies" not in str(frame.iloc[3, 0])
        or str(frame.iloc[12, 11]).strip() != "M2"
    ):
        raise ValueError("hkma_money_schema_changed")
    rows = []
    year = None
    for row in frame.itertuples(index=False, name=None):
        y = number(row[0])
        if y is not None and 1900 <= y <= 2200:
            year = int(y)
        month = str(row[2]).strip().removesuffix("月")
        # Excel numerics have 15 significant digits; discard binary-float noise.
        value = number(format(row[11], ".15g") if isinstance(row[11], float) else row[11])
        if year and month.isdigit() and 1 <= int(month) <= 12 and value is not None:
            rows.append({"date": f"{year}-{int(month):02d}", "value": value})
    return rows


def parse_sina_hk(content, now):
    from akshare.stock.cons import hk_js_decode
    from py_mini_racer import MiniRacer

    encoded = content.split("=", 1)[1].split(";", 1)[0].strip().strip('"')
    with MiniRacer() as decoder:
        decoder.eval(hk_js_decode)
        values = decoder.call("d", encoded)
    local = now.astimezone(ZoneInfo("Asia/Hong_Kong"))
    today = local.date().isoformat()
    return [
        {"date": r["date"][:10], "value": number(r.get("close"))}
        for r in values
        if r["date"][:10] < today
        or (r["date"][:10] == today and (local.hour, local.minute) >= (16, 15))
    ]


def source_specs():
    specs = [
        {
            "id": f"csi_{code}",
            "name": f"中证指数 · {name}",
            "url": f"https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/indicator/{code}indicator.xls",
            "kind": "csi",
            "code": code,
        }
        for code, name in CN_INDICES.items()
    ]
    specs.extend(
        [
            {
                "id": "hk_m2",
                "name": "香港金管局 · M2总额",
                "url": HKMA_URL,
                "kind": "hkma_money",
            },
            {
                "id": "cn_ppi",
                "name": "国家统计局 / 东方财富 · PPI同比",
                "url": EASTMONEY_URL,
                "report": "RPT_ECONOMY_PPI",
                "field": "BASE_SAME",
            },
            {
                "id": "cn_retail",
                "name": "国家统计局 / 东方财富 · 社零同比",
                "url": EASTMONEY_URL,
                "report": "RPT_ECONOMY_TOTAL_RETAIL",
                "field": "RETAIL_TOTAL_SAME",
            },
            {
                "id": "cn_gdp",
                "name": "国家统计局 / 东方财富 · 累计名义GDP",
                "url": EASTMONEY_URL,
                "report": "RPT_ECONOMY_GDP",
                "field": "DOMESTICL_PRODUCT_BASE",
            },
            {"id": "cn_tsf", "name": "商务部数据转载 · 新增社融", "url": TSF_URL, "kind": "tsf"},
            {"id": "cn_tsf_pbc", "name": "人民银行 · 新增社融", "url": PBC_URL, "kind": "pbc_tsf"},
            {
                "id": "us_pe",
                "name": "Multpl / Shiller · 标普500 PE",
                "url": MULTPL_URL,
                "kind": "multpl",
            },
        ]
    )
    for code, name in CN_INDICES.items():
        specs.append(
            {
                "id": f"csi_history_{code}",
                "name": f"中证历史行情 · {name}滚动市盈率",
                "url": "https://www.csindex.com.cn/csindex-home/perf/index-perf",
                "kind": "csi_history",
                "code": code,
            }
        )
    for code, name in CN_INDICES.items():
        specs.append(
            {
                "id": f"members_{code}",
                "name": f"中证指数成分 · {name}",
                "url": f"https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/{code}cons.xls",
                "kind": "members",
            }
        )
    for key, symbol, name in [
        ("hsi", "^HSI", "恒生指数"),
        ("hscei", "^HSCE", "恒生国企"),
    ]:
        specs.append(
            {
                "id": f"hk_{key}",
                "name": name,
                "url": f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                "kind": "yahoo",
                "params": {"range": "1y", "interval": "1d"},
            }
        )
    specs.append(
        {
            "id": "hk_hstech",
            "name": "恒生科技 · 新浪财经",
            "url": "https://finance.sina.com.cn/stock/hkstock/HSTECH/klc2_kl.js",
            "kind": "sina_hk",
        }
    )
    for key, series, name in [
        ("us_credit", "BAMLH0A0HYM2", "ICE BofA / FRED · 美国高收益债OAS"),
        ("us_real_yield", "DFII10", "美联储 / FRED · 10年实际利率"),
    ]:
        specs.append(
            {
                "id": key,
                "name": name,
                "url": "https://fred.stlouisfed.org/graph/fredgraph.csv",
                "params": {"id": series},
                "kind": "fred",
                "series": series,
            }
        )
    from app.research_equity_valuation import valuation_specs

    specs.extend(valuation_specs())
    return specs


async def collect_one(client, spec, *, force=False):
    key = "sources/" + spec["id"]
    old = await asyncio.to_thread(read_artifact, key)
    now = datetime.now(UTC)
    stamp = now.isoformat()
    if not force and old.get("attemptedAt"):
        elapsed = now - datetime.fromisoformat(old["attemptedAt"])
        if elapsed < timedelta(hours=6 if old.get("status") == "ready" else 1):
            return old
    params = spec.get("params", {})
    if spec.get("kind") == "csi_history":
        local = now.astimezone(ZoneInfo("Asia/Shanghai"))
        start = now - timedelta(days=365 * 5 + 7)
        if old.get("observationDate"):
            start = datetime.fromisoformat(old["observationDate"]) - timedelta(days=7)
        params = {
            "indexCode": spec["code"],
            "startDate": start.strftime("%Y%m%d"),
            "endDate": local.strftime("%Y%m%d"),
        }
    if spec.get("report"):
        params = {
            "reportName": spec["report"],
            "columns": "ALL",
            "pageNumber": 1,
            "pageSize": 1000,
            "sortColumns": "REPORT_DATE",
            "sortTypes": -1,
        }
    doc = {**old, "id": spec["id"], "name": spec["name"], "url": spec["url"], "attemptedAt": stamp}
    try:
        response = await (
            client.post(spec["url"])
            if spec.get("kind") == "tsf"
            else client.get(spec["url"], params=params)
        )
        response.raise_for_status()
        digest = await asyncio.to_thread(archive, spec["id"], response.content, stamp)
        kind = spec.get("kind")
        if kind == "index_metric":
            from app.research_equity_valuation import parse_index_metric

            rows = parse_index_metric(response.content, spec["ticker"])
        elif kind == "ssga_index":
            from app.research_equity_valuation import parse_ssga

            rows = parse_ssga(response.content)
        elif kind == "siblis_table":
            from app.research_equity_valuation import parse_russell

            rows = parse_russell(response.content, spec.get("ticker", "Russell 2000"))
        elif kind == "pbc_tsf":
            rows, manifest = await collect_pbc_tsf(client, response, stamp)
            doc["rawDocuments"] = [{"url": spec["url"], "sha256": digest}, *manifest]
        elif kind == "csi_history":
            payload = json.loads(response.content, parse_float=str)
            if not payload.get("success"):
                raise ValueError("csi_history_error")
            local = now.astimezone(ZoneInfo("Asia/Shanghai"))
            rows = []
            for raw in payload["data"]:
                day = datetime.strptime(raw["tradeDate"], "%Y%m%d").date().isoformat()
                if raw["indexCode"] != spec["code"]:
                    raise ValueError("csi_history_index_mismatch")
                if day < local.date().isoformat() or (local.hour, local.minute) >= (16, 15):
                    rows.append(
                        {
                            "date": day,
                            "pe": number(raw.get("peg")),
                            "close": number(raw.get("close")),
                        }
                    )
        elif kind == "csi":
            rows = await asyncio.to_thread(parse_csi, response.content)
        elif kind == "hkma_money":
            rows = await asyncio.to_thread(parse_hkma_money, response.content)
        elif kind == "sina_hk":
            rows = await asyncio.to_thread(parse_sina_hk, response.text, now)
        elif kind == "members":
            frame = pd.read_excel(io.BytesIO(response.content), dtype=str)
            code_col = next(
                (c for c in frame.columns if "成份券代码" in c or "成分券代码" in c), None
            )
            date_col = next((c for c in frame.columns if "日期" in c), None)
            if code_col is None or date_col is None:
                raise ValueError("constituent_schema_changed")
            grouped = {}
            for _, row in frame.iterrows():
                day = datetime.strptime(row[date_col], "%Y%m%d").date().isoformat()
                code = str(row[code_col]).zfill(6)
                if len(code) == 6 and code.isdigit():
                    grouped.setdefault(day, set()).add(code)
            rows = [
                {"date": d, "value": len(codes), "codes": sorted(codes)}
                for d, codes in grouped.items()
            ]
        elif kind == "yahoo":
            result = response.json()["chart"]["result"][0]
            zone = ZoneInfo(result.get("meta", {}).get("exchangeTimezoneName", "Asia/Hong_Kong"))
            local_today = now.astimezone(zone).date().isoformat()
            end = (
                result.get("meta", {}).get("currentTradingPeriod", {}).get("regular", {}).get("end")
            )
            rows = []
            for ts, value in zip(
                result.get("timestamp", []), result["indicators"]["quote"][0]["close"], strict=True
            ):
                day = datetime.fromtimestamp(ts, zone).date().isoformat()
                if day < local_today or (end and now.timestamp() >= end):
                    rows.append({"date": day, "value": number(value)})
        elif kind == "multpl":
            rows = parse_multpl(response.text)
        elif kind == "fred":
            frame = pd.read_csv(io.BytesIO(response.content), dtype=str)
            if spec["series"] not in frame.columns:
                raise ValueError("fred_schema_changed")
            rows = [
                {"date": str(row.iloc[0]), "value": number(row[spec["series"]])}
                for _, row in frame.iterrows()
            ]
        else:
            payload = json.loads(response.content, parse_float=str)
            if kind == "hkma":
                if not payload.get("header", {}).get("success"):
                    raise ValueError("hkma_error")
                rows = [
                    {"date": r["end_of_month"], "value": number(r.get("m2_total"))}
                    for r in payload["result"]["records"]
                ]
            elif kind == "tsf":
                rows = [
                    {
                        "date": str(r["date"])[:4] + "-" + str(r["date"])[4:6],
                        "value": number(r.get("tiosfs")),
                    }
                    for r in payload
                ]
            else:
                if not payload.get("success"):
                    raise ValueError("eastmoney_error")
                rows = [
                    {
                        "date": r["REPORT_DATE"][:7],
                        "value": number(r.get(spec["field"])),
                        "period": "1—2月合计"
                        if spec["id"] == "cn_retail" and r["REPORT_DATE"][5:7] == "02"
                        else r.get("TIME"),
                    }
                    for r in payload["result"]["data"]
                ]
        field = "pe" if kind in {"csi", "csi_history", "multpl", "ssga_index"} else "value"

        def valid_date(value):
            try:
                datetime.strptime(value, "%Y-%m" if len(value) == 7 else "%Y-%m-%d")
                return value <= stamp[: len(value)]
            except ValueError:
                return False

        rows = [r for r in rows if number(r.get(field)) is not None and valid_date(r["date"])]
        if kind in {"csi", "csi_history", "multpl", "yahoo", "sina_hk"}:
            rows = [r for r in rows if number(r[field]) > 0]
        if not rows:
            raise ValueError("empty_valid_observations")
        if old.get("observationDate", "") > max(r["date"] for r in rows):
            raise ValueError("source_date_regressed")

        # Per-source identity is fixed. Never stitch Choice and CSI histories.
        def identity(row):
            # The current monthly estimate changes date as it updates; it is
            # still one monthly observation, not extra daily rank samples.
            return row["date"][:7] if kind == "multpl" else row["date"]

        merged = {identity(r): r for r in old.get("rows", []) if valid_date(r["date"])}
        merged.update({identity(r): r for r in sorted(rows, key=lambda r: r["date"])})
        doc.update(
            rows=[merged[d] for d in sorted(merged)][-(1 if kind == "members" else 6000) :],
            fetchedAt=stamp,
            acquisitionMethod="http",
            status="ready",
            error=None,
            rawSha256=digest,
            observationDate=max(r["date"] for r in rows),
        )
    except Exception as exc:
        # Parser libraries (Excel/JS) also raise their own exception classes.
        # This per-source failure boundary must retain LKG for all of them.
        doc.update(status="stale" if old.get("rows") else "error", error=type(exc).__name__)
    await asyncio.to_thread(publish_artifact, key, doc)
    return doc


async def collect_sources(*, force=False):
    semaphore = asyncio.Semaphore(3)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(25, connect=10),
        follow_redirects=True,
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        trust_env=True,
        headers={"User-Agent": "VariableGlobalResearch/1.0"},
    ) as client:

        async def bounded(spec):
            async with semaphore:
                return await collect_one(client, spec, force=force)

        results = await asyncio.gather(
            *(bounded(s) for s in source_specs()), return_exceptions=True
        )
    documents = {
        s["id"]: (
            r
            if isinstance(r, dict)
            else {"id": s["id"], "status": "error", "error": type(r).__name__}
        )
        for s, r in zip(source_specs(), results, strict=True)
    }

    from app.research_equity_valuation import collect_choice_indices

    return {**documents, **(await asyncio.to_thread(collect_choice_indices))}
