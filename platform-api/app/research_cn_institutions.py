"""Official AMAC / NFRA capital stocks. Local GETs never trigger collection."""

import asyncio
import calendar
import io
import json
import logging
import re
import ssl
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urljoin

import httpx
import pandas as pd
import truststore
from bs4 import BeautifulSoup
from pypdf import PdfReader

from app.research_equity_sources import archive, publish_artifact, read_artifact

ARTIFACT = "cn-institutional-capital"
AMAC = "https://www.amac.org.cn/sjtj/tjbg/"
NFRA = "https://www.nfra.gov.cn"
SOURCES = {
    "public": ("公募基金", "中国证券投资基金业协会", AMAC + "gmjj/"),
    "private": ("私募证券基金", "中国证券投资基金业协会", AMAC + "smjj/"),
    "insurance": (
        "保险资金",
        "国家金融监督管理总局",
        NFRA + "/cn/view/pages/ItemListRightList.html?itemId=954",
    ),
    "insurancePremium": ("原保险保费收入", "国家金融监督管理总局", NFRA + "/cn/view/pages/ItemListRightList.html?itemId=954"),
}
_LOCK = asyncio.Lock()


def month_end(year, month):
    year, month = int(year), int(month)
    return f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"


def decimal(value):
    result = Decimal(str(value).replace(",", ""))
    if not result.is_finite():
        raise ValueError("non_finite_official_value")
    return str(result)


def parse_public(text):
    """Read both dated column groups; preserve source units: CNY 100m / 100m shares."""
    if not all(t in text for t in ("份额", "亿份", "净值", "亿元")):
        raise ValueError("amac_public_units_changed")
    dates = list(dict.fromkeys(re.findall(r"(20\d{2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})", text)))
    if not 1 <= len(dates) <= 2:
        raise ValueError("amac_public_dates_changed")
    legacy = "开放式基金" in text
    rows = [{"date": month_end(y, m), "basis": "open" if legacy else "all"} for y, m, _ in dates]
    labels = {
        "股票基金": "stock",
        "混合基金": "mixed",
        "债券基金": "bond",
        ("货币基金" if legacy else "货币市场基金"): "money",
        ("合计" if legacy else "全部"): "total",
    }
    for label, key in labels.items():
        line = re.search(r"(?:^|\n)\s*(?:其中：)?" + label + r"\s+([^\n]+)", text)
        values = re.findall(r"[\d,]+(?:\.\d+)?", line[1]) if line else []
        if len(values) != 3 * len(rows):
            raise ValueError("amac_public_columns_changed:" + key)
        for i, row in enumerate(rows):
            row[key + "Shares"] = decimal(values[3 * i + 1])
            row[key + "Assets"] = decimal(values[3 * i + 2])
    return rows


def parse_private(text):
    compact = re.sub(r"\s+", "", text)
    period = re.search(r"（(20\d{2})年(\d{1,2})月）", compact)
    if not period:
        raise ValueError("amac_private_period_missing")
    # Search only the product stock section, not manager counts or new registrations.
    section = re.split(r"[（(]二[）)]私募基金存续情况", compact)
    if len(section) != 2:
        raise ValueError("amac_private_stock_section_changed")
    match = re.search(r"存续私募证券投资基金([\d,]+)只，存续规模([\d,.]+)(万亿元|亿元)", section[1])
    if not match:
        raise ValueError("amac_private_stock_missing")
    assets = Decimal(match[2].replace(",", "")) * (10000 if match[3] == "万亿元" else 1)
    flow = re.search(r"私募证券投资基金\d*([\d,]+)只，新备案规模([\d,.]+)亿元", compact)
    return [
        {
            "date": month_end(*period.groups()),
            "securitiesAssets": str(assets),
            "securitiesCount": int(match[1].replace(",", "")),
            "newRegistered": decimal(flow[2]) if flow else None,
        }
    ]


def parse_insurance(content):
    frame = pd.read_excel(io.BytesIO(content), header=None)
    text = " ".join(str(v) for v in frame.values.ravel())
    title = re.search(r"(20\d{2})年([一二三四])季度保险公司资金运用情况表", text)
    if not title or "单位：亿元" not in text:
        raise ValueError("nfra_insurance_schema_changed")
    row = {"date": month_end(title[1], ("一二三四".index(title[2]) + 1) * 3)}
    group = None
    keys = {
        "资金运用余额": "Total",
        "股票": "Stock",
        "证券投资基金": "Funds",
        "长期股权投资": "Equity",
    }
    for cells in frame.itertuples(index=False, name=None):
        a, b = str(cells[0]).strip(), str(cells[1]).strip()
        if a == "保险公司":
            row["totalAssets"] = decimal(cells[2])
            group = None
        elif "财产险公司" in a:
            group = "property"
        elif a == "人身险公司":
            group = "life"
        if group and b in keys:
            row[group + keys[b]] = decimal(cells[2])
    required = [g + k for g in ("property", "life") for k in keys.values()]
    if not all(k in row for k in ["totalAssets", *required]):
        raise ValueError("nfra_insurance_fields_missing")
    for group in ("property", "life"):
        total = Decimal(row[group + "Total"])
        if total <= 0:
            raise ValueError("nfra_insurance_invalid_total")
        for key in ("Stock", "Funds", "Equity"):
            row[group + key + "Pct"] = str(Decimal(row[group + key]) / total * 100)
    return [row]


def parse_insurance_premium(content):
    frame = pd.read_excel(io.BytesIO(content), header=None)
    cells = [str(v).strip() for v in frame.values.ravel()]
    title = next((m for text in cells if (m := re.fullmatch(r"(20\d{2})年(\d{1,2})月保险业经营情况表", text))), None)
    if not title or not any(re.fullmatch(r"单位\s*[:：]\s*亿元(?:[、，,]\s*万件)?", text) for text in cells):
        raise ValueError("nfra_premium_schema_changed")
    for row in frame.itertuples(index=False, name=None):
        for i, item in enumerate(row[:-1]):
            if str(item).strip() == "原保险保费收入":
                total = decimal(row[i + 1])
                if Decimal(total) <= 0:
                    raise ValueError("nfra_invalid_premium")
                return [{"date": month_end(*title.groups()), "premiumYtd": total}]
    raise ValueError("nfra_premium_missing")


def monthly_premiums(rows):
    totals = {r["date"][:7]: Decimal(r["premiumYtd"]) for r in rows}
    result = []
    for row in rows:
        month = row["date"][:7]
        previous_month = (datetime.fromisoformat(row["date"]).replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        prior = Decimal(0) if month.endswith("-01") else totals.get(previous_month)
        value = totals[month] - prior if prior is not None else None
        result.append({**row, "premiumMonth": str(value) if value is not None and value >= 0 else None})
    return result


def pdf_text(content):
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(content)).pages)


async def collect(force=False, backfill=False, only=None):
    async with _LOCK:
        now = datetime.now(UTC)
        stamp = now.isoformat()
        doc = read_artifact(ARTIFACT)
        sources = doc.setdefault("sources", {})
        async with httpx.AsyncClient(
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:

            async def fetch(url, key):
                response = await client.get(url)
                response.raise_for_status()
                digest = await asyncio.to_thread(
                    archive, "institutions_" + key, response.content, stamp
                )
                return response.content, digest

            for key, (label, provider, url) in SOURCES.items():
                if only and key != only:
                    continue
                old = sources.get(key, {})
                if (
                    not force
                    and old.get("attemptedAt")
                    and now - datetime.fromisoformat(old["attemptedAt"]) < timedelta(hours=20)
                ):
                    continue

                def row_id(row):
                    return row["date"] + ":" + row.get("basis", "")

                rows = {
                    row_id(r): r for r in old.get("rows", []) if key != "public" or r.get("basis")
                }
                errors = []
                manifest = []
                try:
                    targets = {}
                    if key in ("public", "private"):
                        for page in range(2 if backfill else 1):
                            page_url = url + (f"index_{page}.html" if page else "")
                            content, _ = await fetch(page_url, key)
                            soup = BeautifulSoup(content, "html.parser")
                            for a in soup.select("a[href]"):
                                href, title = a["href"], a.get_text(" ", strip=True)
                                if (
                                    href.startswith("./")
                                    and href.endswith(".pdf")
                                    and ("公募基金市场数据" in title or "备案月报" in title)
                                ):
                                    targets[urljoin(url, href)] = title
                    else:
                        for page in range(1, (24 if key == "insurancePremium" else 9) if backfill else 3):
                            list_url = (
                                NFRA
                                + "/cbircweb/DocInfo/SelectDocByItemIdAndChild"
                                + f"?itemId=954&pageIndex={page}&pageSize=18"
                            )
                            content, _ = await fetch(list_url, key)
                            for item in json.loads(content)["data"]["rows"]:
                                keyword = "保险业经营情况表" if key == "insurancePremium" else "保险公司资金运用情况表"
                                if keyword in item["docTitle"]:
                                    year = re.search(r"20\d{2}", item["docTitle"])
                                    if key == "insurancePremium" and (not year or int(year[0]) < now.year - 3):
                                        continue
                                    detail_url = (
                                        NFRA
                                        + "/cn/static/data/DocInfo/SelectByDocId/"
                                        + f"data_docId={item['docId']}.json"
                                    )
                                    detail, _ = await fetch(detail_url, key)
                                    attachments = json.loads(detail)["data"]["attachmentInfoVOList"]
                                    for attachment in attachments:
                                        if (
                                            attachment["urlOtherName"]
                                            .lower()
                                            .endswith((".xls", ".xlsx"))
                                            and (key != "insurancePremium" or not re.search(r"地区|地区表", attachment.get("attachmentName", "")))
                                        ):
                                            targets[urljoin(NFRA, attachment["urlOtherName"])] = (
                                                item["docTitle"]
                                            )
                    if not targets:
                        raise ValueError("official_documents_missing")
                    retained = {item["url"]: item for item in old.get("manifest", [])}
                    revision_targets = set(list(targets)[:2])
                    # Oldest first: subsequent official documents win revisions of the same month.
                    for target, title in reversed(list(targets.items())):
                        if not backfill and target in retained and target not in revision_targets:
                            manifest.append(retained[target])
                            continue
                        try:
                            content, digest = await fetch(target, key)
                            parsed = (
                                parse_insurance(content)
                                if key == "insurance"
                                else parse_insurance_premium(content)
                                if key == "insurancePremium"
                                else (parse_public if key == "public" else parse_private)(
                                    await asyncio.to_thread(pdf_text, content)
                                )
                            )
                            for row in parsed:
                                if row["date"] > now.date().isoformat():
                                    raise ValueError("official_period_in_future")
                                rows[row_id(row)] = {
                                    **row,
                                    "sourceUrl": target,
                                    "sourceTitle": title,
                                    "rawSha256": digest,
                                    "fetchedAt": stamp,
                                }
                            manifest.append({"url": target, "sha256": digest})
                        except Exception as exc:
                            errors.append({"url": target, "error": str(exc)[:160]})
                    if not manifest:
                        raise ValueError("no_official_documents_parsed")
                    sources[key] = {
                        "label": label,
                        "provider": provider,
                        "sourceUrl": url,
                        "status": "partial" if errors else "ready",
                        "fetchedAt": stamp,
                        "attemptedAt": stamp,
                        "rows": sorted(rows.values(), key=lambda r: r["date"]),
                        "observationDate": max(r["date"] for r in rows.values()),
                        "errors": errors,
                        "manifest": manifest,
                    }
                except Exception as exc:
                    sources[key] = {
                        **old,
                        "status": "error",
                        "attemptedAt": stamp,
                        "error": str(exc)[:160],
                        "errors": errors,
                    }
                    logging.getLogger(__name__).warning(
                        "Institutional source %s: %s", key, type(exc).__name__
                    )
                doc["generatedAt"] = stamp
                await asyncio.to_thread(publish_artifact, ARTIFACT, doc)
        return doc


def read_institutions():
    sources = read_artifact(ARTIFACT).get("sources", {})
    result = {}
    for key, (label, provider, url) in SOURCES.items():
        source = dict(sources.get(key, {}))
        stamp = source.get("fetchedAt")
        source.update(
            label=label,
            provider=provider,
            sourceUrl=url,
            isStale=not stamp
            or datetime.now(UTC) - datetime.fromisoformat(stamp) > timedelta(days=3),
        )
        source.setdefault("rows", [])
        if key == "insurancePremium":
            boundary = datetime.now(UTC).date()
            cutoff = f"{boundary.year - 3}-{boundary.month:02d}"
            source["rows"] = [row for row in monthly_premiums(source["rows"]) if row["date"][:7] >= cutoff]
        source.setdefault("status", "unavailable")
        result[key] = source
    return result
