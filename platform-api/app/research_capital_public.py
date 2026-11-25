"""Incremental official public statistics for the capital research page."""

import asyncio
import base64
import hashlib
import io
import json
import re
import ssl
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from urllib.parse import urljoin

import httpx
import pandas as pd
import truststore
from bs4 import BeautifulSoup
from pypdf import PdfReader

from app.research_cn_institutions import month_end

SOCIAL = "https://www.ssf.gov.cn/portal/xxgk/fdzdgknr/cwbg/sbjjndbg/A0010030801index_1.htm"
BANK = "https://www.chinawealth.com.cn/lc_lcsj/lcbg/"
PENSION = "https://www.mohrss.gov.cn/xxgk2020/fdzdgknr/shbx_4216/shbxjjjg/qynjjd/"
SSE = "https://www.sse.com.cn/aboutus/publication/monthly/investor/"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def read(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def html(body):
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        text = body.decode("gb18030")
    return BeautifulSoup(text, "html.parser")


def numeric(value):
    parsed = Decimal(str(value).replace(",", ""))
    if not parsed.is_finite():
        raise ValueError("invalid_official_number")
    return str(parsed)


def parse_residents(payload):
    rows = []
    for item in payload.get("result", []):
        term = str(item.get("TERM", ""))
        if not re.fullmatch(r"20\d{2}\.\d{2}", term):
            continue
        # MDATE identifies publication coverage; TERM is the actual observation.
        if term.replace(".", "") > str(item.get("MDATE", "")):
            continue
        rows.append({"date": term.replace(".", "-") + "-01",
                     "personal": numeric(item["A_PERSON"]),
                     "institutional": numeric(item["A_ORG"])})
    if not rows:
        raise ValueError("sse_no_published_months")
    return rows


def parse_foreign_html(body):
    soup = html(body)
    if "100 Million Yuan" not in soup.get_text():
        raise ValueError("pbc_units_missing")
    for table in pd.read_html(io.StringIO(str(soup))):
        date_row = next((r for _, r in table.iterrows()
                         if sum(bool(re.fullmatch(r"20\d{2}\.\d{2}", str(v).strip())) for v in r) >= 6), None)
        equity_row = next((r for _, r in table.iterrows() if any("Equities" in str(v) for v in r)), None)
        if date_row is None or equity_row is None:
            continue
        dates = {i: str(v).strip() for i, v in date_row.items()
                 if re.fullmatch(r"20\d{2}\.\d{2}", str(v).strip())}
        rows = [{"date": month_end(*d.split(".")), "equities": numeric(equity_row[i])}
                for i, d in dates.items() if pd.notna(equity_row[i])]
        if rows:
            return rows
    raise ValueError("pbc_table_changed")


def parse_social(text):
    compact = re.sub(r"\s+", "", text)
    head = re.search(r"(20\d{2})年末，基金资产总额([\d,.]+)亿元", compact)
    if not head:
        raise ValueError("social_assets_missing")
    row = {"date": head[1] + "-12-31", "assets": numeric(head[2])}
    for key, pattern in {
        "direct": r"直接投资资产([\d,.]+)亿元",
        "entrusted": r"委托投资资产([\d,.]+)亿元",
        "domestic": r"境内投资资产([\d,.]+)亿元",
        "overseas": r"境外投资资产([\d,.]+)亿元",
        "returnPct": r"(?<!已实现)投资收益率([\-\d.]+)%",
    }.items():
        match = re.search(pattern, compact)
        row[key] = numeric(match[1]) if match else None
    return [row]


def parse_pension(text, title):
    compact = re.sub(r"\s+", "", text)
    year = re.search(r"(20\d{2})", title)
    amount = re.search(r"积累基金[（(]亿元[）)]([\d,]+\.\d{2})", compact)
    if not year or not amount:
        raise ValueError("pension_assets_missing")
    month = next((m for tokens, m in [("一1", 3), ("二2", 6), ("三3", 9)]
                  if any(token + "季度" in title for token in tokens)), 12)
    row = {"date": month_end(year[1], month), "assets": numeric(amount[1])}
    if not 1_000 < Decimal(row["assets"]) < 1_000_000:
        raise ValueError("pension_assets_outside_expected_units")
    for key, label in (("periodReturnPct", r"(?:本季度|本年度|当年)加权平均收益率"),
                       ("threeYearReturnPct", "近三年累计收益率")):
        match = re.search(label + r"[（(][%％][）)]([-−]?\d+\.\d{2})", compact)
        if match:
            row[key] = numeric(match[1].replace("−", "-"))
    return row


def parse_occupational_pension(text, title):
    year = re.match(r"(20\d{2})年全国职业年金基金市场化投资运营情况", title)
    match = re.search(r"(?:中央单位职业年金基金|中央单位职业年金)(?:累计)?投资运营规模(?:为|达)?([\d.]+)万亿元", re.sub(r"\s+", "", text))
    if not year or not match:
        raise ValueError("occupational_pension_assets_missing")
    return {"date": month_end(year[1], 12), "assets": str(Decimal(match[1]) * 10000)}


def pdf_pension(content, title):
    reader = PdfReader(io.BytesIO(content))
    for page in reader.pages[:6]:
        try:
            return parse_pension(page.extract_text() or "", title)
        except ValueError:
            continue
    # Some reports have vector outlines instead of text. Match the value to
    # the label on the same OCR row, then require the report's table heading.
    import unicodedata

    import pypdfium2

    script = Path(__file__).resolve().parents[1] / "scripts/read-mohrss-ocr.ps1"
    with pypdfium2.PdfDocument(content) as pdf, TemporaryDirectory() as work:
        for index in (3, 2, 4, 5):
            if index >= len(pdf):
                continue
            page = pdf[index]
            image = Path(work) / "table.png"
            page.render(scale=3.3).to_pil().save(image)
            page.close()
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                 "-ImagePath", str(image)], capture_output=True, check=True, encoding="utf-8", timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            words = json.loads(result.stdout)
            lines = []
            for word in sorted(words, key=lambda w: w["y"]):
                if not lines or abs(word["y"] - lines[-1][0]["y"]) > max(word["height"], lines[-1][0]["height"]) * 0.6:
                    lines.append([])
                lines[-1].append(word)
            text = "\n".join(
                "".join(w["text"] for w in sorted(line, key=lambda w: w["x"])) for line in lines
            )
            text = unicodedata.normalize("NFKC", text).replace("。", ".")
            if "全国企业年金基本情况一览表" not in re.sub(r"\s+", "", text):
                continue
            try:
                return parse_pension(text, title)
            except ValueError:
                continue
    raise ValueError("pension_pdf_table_unreadable")


def archive_public(work, url, stamp, content):
    digest = hashlib.sha256(content).hexdigest()
    archive = work / "public-raw" / (digest + ".json")
    if not archive.exists():
        save(archive, {"url": url, "fetchedAt": stamp, "sha256": digest, "bodyHex": content.hex()})
    return {"sourceUrl": url, "fetchedAt": stamp, "sourceHash": digest}


def fetch_annuity(known, min_year):
    script = Path(__file__).resolve().parents[1] / "scripts/fetch-mohrss-annuity.cjs"
    result = subprocess.run(
        ["node", str(script), json.dumps(known), str(min_year)], check=True,
        capture_output=True, encoding="utf-8", timeout=240,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    messages = [json.loads(line) for line in result.stdout.splitlines()]
    return messages[:-1], messages[-1]


def collect_annuity(work, doc, now, force):
    stamp = now.isoformat()
    states = doc["sources"]
    keys = ("pension", "occupationalPension")
    due = []
    for key in keys:
        state = states.get(key, {})
        interval = timedelta(days=1 if state.get("status") in {"partial", "error"} else 7)
        if force or not state.get("attemptedAt") or now - datetime.fromisoformat(state["attemptedAt"]) >= interval:
            due.append(key)
    if not due:
        return
    try:
        documents, result = fetch_annuity(
            [url for key in keys for url in states.get(key, {}).get("documents", {})], now.year - 3,
        )
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        documents, result = [], {"discovered": [], "errors": [{"url": PENSION, "error": type(exc).__name__}]}
    for key in keys:
        rows = {r["date"]: r for r in doc.get(key, [])}
        state = states.get(key, {})
        known = dict(state.get("documents", {}))
        errors = [e for e in result["errors"] if e.get("key", key) == key]
        successful = False
        for item in documents:
            if item["key"] != key:
                continue
            try:
                content = base64.b64decode(item["body"], validate=True)
                meta = archive_public(work, item["source"], stamp, content)
                if known.get(item["url"]) == meta["sourceHash"]:
                    successful = True
                    continue
                row = (pdf_pension(content, item["title"]) if key == "pension" else
                       parse_occupational_pension(html(content).get_text(" ", strip=True), item["title"]))
                if row["date"] > now.date().isoformat():
                    raise ValueError("future_official_period")
                rows[row["date"]] = {**row, **meta, "sourceTitle": item["title"], "articleUrl": item["url"]}
                known[item["url"]] = meta["sourceHash"]
                successful = True
            except Exception as exc:
                errors.append({"url": item["url"], "error": str(exc)[:180]})
        if key not in result["discovered"]:
            errors.append({"url": PENSION, "error": "official_report_list_empty"})
        if rows:
            doc[key] = sorted(rows.values(), key=lambda r: r["date"])
        states[key] = {**state, "attemptedAt": stamp, "sourceUrl": PENSION, "documents": known,
                       "fetchedAt": stamp if successful else state.get("fetchedAt"),
                       "status": ("partial" if errors else "ready") if rows and (successful or known) else "error",
                       "errors": errors, "error": errors[0]["error"] if errors else None}


def parse_bank(text, title):
    compact = re.sub(r"\s+", "", text)
    year = re.search(r"20\d{2}", title)
    month = next((m for token, m in [("一季度", 3), ("半年", 6), ("三季度", 9)] if token in title), 12)
    if not year:
        raise ValueError("bank_period_missing")
    row = {"date": month_end(year[0], month)}
    patterns = {
        "assets": r"存续规模(?:为|达)?([\d.]+)万亿元",
        "investmentAssets": r"投资资产(?:合计|总额|余额)(?:为|达)?([\d.]+)万亿元",
        "equity": r"权益类资产(?:的?余额|投资余额|规模)(?:为|达)?([\d.]+)万亿元",
        "bonds": r"债券类资产(?:的?余额|投资余额|规模)(?:为|达)?([\d.]+)万亿元",
        "nonstandard": r"非标准化债权类资产(?:的?余额|投资余额|规模)(?:为|达)?([\d.]+)万亿元",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, compact)
        row[key] = numeric(match[1]) if match else None
    combined = re.search(r"投向债券类、非标准化债权类\d*资产、权益类资产余额分别为([\d.]+)万亿元、([\d.]+)万亿元、([\d.]+)万亿元[，,]分别占总投资资产的([\d.]+)%、([\d.]+)%、([\d.]+)%", compact)
    if combined:
        for i, key in enumerate(("bonds", "nonstandard", "equity")):
            row[key] = numeric(combined[i + 1])
            row[key + "Pct"] = numeric(combined[i + 4])
    if row["assets"] is None or row["investmentAssets"] is None:
        raise ValueError("bank_totals_missing")
    for key in ("equity", "bonds", "nonstandard"):
        row.setdefault(key + "Pct", str(Decimal(row[key]) / Decimal(row["investmentAssets"]) * 100) if row[key] else None)
    if any(row[k] is None for k in ("equity", "bonds", "nonstandard")):
        raise ValueError("bank_allocation_requires_table_review")
    return [row]


async def collect_public(root, *, force=False, now=None, annuity_only=False):
    now = now or datetime.now(UTC)
    stamp = now.isoformat()
    work = root / "research/capital-handbook-choice"
    path = work / "public-supplement.json"
    doc = read(path)
    states = doc.setdefault("sources", {})
    urls = {"residents": SSE, "foreign": f"https://www.pbc.gov.cn/diaochatongjisi/116219/116319/{now.year}ntjsj/hbtjgl/index.html",
            "social": SOCIAL, "bank": BANK}
    if annuity_only:
        urls.clear()
    async with httpx.AsyncClient(verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
                                timeout=25, follow_redirects=True,
                                headers={"User-Agent": "Mozilla/5.0"}) as client:
        async def fetch(url, params=None):
            response = await client.get(url, params=params, headers={"Referer": url if params is None else SSE})
            response.raise_for_status()
            return response.content, archive_public(work, str(response.url), stamp, response.content)

        for key, url in urls.items():
            state = states.get(key, {})
            interval = timedelta(days=1 if key in ("residents", "foreign") else 7)
            if not force and state.get("attemptedAt") and now - datetime.fromisoformat(state["attemptedAt"]) < interval:
                continue
            rows = {r["date"]: r for r in doc.get(key, [])}
            errors, updated = [], 0
            known = dict(state.get("documents", {}))
            try:
                if key == "residents":
                    coverage = (now.date().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
                    body, meta = await fetch("https://query.sse.com.cn/commonQuery.do", {
                        "sqlId": "COMMON_SSE_TZZ_M_STOCK_ACCT_C", "isPagination": "false", "MDATE": coverage})
                    for row in parse_residents(json.loads(body)):
                        rows[row["date"]] = {**row, **meta}
                    updated += 1
                else:
                    body, _ = await fetch(url)
                    soup = html(body)
                    if key == "foreign":
                        node = soup.find(string=lambda s: s and "Domestic RMB Financial Assets" in s)
                        if node is None:
                            raise ValueError("pbc_report_link_missing")
                        parent = node.find_parent("tr")
                        targets = [(urljoin(url, a["href"]), "境外持有境内人民币资产")
                                   for a in parent.select("a[href]") if a.get_text(strip=True) == "htm"]
                    else:
                        keyword = {"social": "全国社会保障基金", "bank": "理财市场"}[key]
                        targets = [(urljoin(url, a["href"]), a.get_text(" ", strip=True))
                                   for a in soup.select("a[href]") if keyword in a.get_text()
                                   and re.search(r"20\d{2}", a.get_text())
                                   and int(re.search(r"20\d{2}", a.get_text())[0]) >= now.year - 3]
                        targets = list(dict.fromkeys(targets))[:12]
                    if not targets:
                        raise ValueError("official_report_list_empty")
                    for idx, (target, title) in enumerate(targets):
                        # Published old documents are immutable; check the newest report for revision.
                        if target in known and idx > 0:
                            continue
                        try:
                            content, meta = await fetch(target)
                            if key == "bank" and not content.startswith(b"%PDF"):
                                page = html(content)
                                pdf = next((urljoin(target, a["href"]) for a in page.select("a[href]")
                                            if ".pdf" in a["href"].lower()), None)
                                if not pdf:
                                    pdf = next((urljoin(target, a["data-recurl"]) for a in page.select("[data-recurl]")
                                                if ".pdf" in a["data-recurl"].lower()), None)
                                if not pdf:
                                    raise ValueError("official_pdf_link_missing")
                                content, meta = await fetch(pdf)
                            if known.get(target) == meta["sourceHash"]:
                                updated += 1
                                continue
                            if key == "foreign":
                                parsed = parse_foreign_html(content)
                            elif key == "social":
                                parsed = parse_social(html(content).get_text(" ", strip=True))
                            else:
                                text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)
                                parsed = parse_bank(text, title)
                            for row in parsed:
                                if row["date"] > now.date().isoformat():
                                    raise ValueError("future_official_period")
                                rows[row["date"]] = {**row, **meta, "sourceTitle": title}
                            known[target] = meta["sourceHash"]
                            updated += 1
                        except Exception as exc:
                            errors.append({"url": target, "error": str(exc)[:180]})
                if not updated and not known:
                    raise ValueError("no_public_reports_parsed")
                doc[key] = sorted(rows.values(), key=lambda r: r["date"])
                states[key] = {**state, "error": None, "attemptedAt": stamp,
                               "fetchedAt": stamp if updated else state.get("fetchedAt"),
                               "status": "partial" if errors else "ready", "errors": errors,
                               "sourceUrl": url, "documents": known}
            except Exception as exc:
                states[key] = {**state, "attemptedAt": stamp, "sourceUrl": url,
                               "status": "error", "error": str(exc)[:180], "errors": errors}
            save(path, doc)
    await asyncio.to_thread(collect_annuity, work, doc, now, force)
    doc["publicFetchedAt"] = max((s.get("fetchedAt") or "" for s in states.values()), default="") or doc.get("publicFetchedAt")
    save(path, doc)
    return doc
