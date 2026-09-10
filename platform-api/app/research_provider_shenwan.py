"""Resolve current official SW2021 classifications to Shenwan index identities."""

from __future__ import annotations

import asyncio
import hashlib
import ssl
from datetime import date, datetime
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import truststore
from bs4 import BeautifulSoup

from app.research_data_schemas import ShenwanMembership
from app.research_provider_errors import ResearchProviderError
from app.research_provider_normalization import as_date

CLASSIFICATIONS_URL = (
    "https://www.swsresearch.com/swindex/pdf/SwClass2021/StockClassifyUse_stock.xls"
)
TAXONOMY_URL = "https://www.swsresearch.com/swindex/pdf/SwClass2021/2014to2021.xlsx"
INDEX_IDENTITIES_URL = "https://legulegu.com/stockdata/sw-industry-overview"


def _name(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().replace("Ⅱ", "II").replace("Ⅲ", "III")


def _code(value: Any) -> str:
    value = _name(value).removesuffix(".0")
    return value if len(value) == 6 and value.isdigit() else ""


def index_identities(html: str) -> tuple[dict[str, str], dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    mappings = []
    for level in (1, 2):
        section = soup.find(id=f"level{level}Items")
        if section is None:
            raise ResearchProviderError("shenwan_index_identity_missing")
        codes = section.select(".lg-industries-item-chinese-title")
        names = section.select(".lg-industries-item-number")
        if len(codes) != len(names):
            raise ResearchProviderError("shenwan_index_identity_misaligned")
        mappings.append(
            {
                _name(name.get_text().split("(")[0]): code.get_text().strip().removesuffix(".SI")
                for code, name in zip(codes, names, strict=True)
            }
        )
    return mappings[0], mappings[1]


def normalize_memberships(
    records: list[dict[str, Any]],
    taxonomy: list[list[Any]],
    l1_indices: dict[str, str],
    l2_indices: dict[str, str],
    *,
    version: str,
    as_of: date,
) -> list[ShenwanMembership]:
    l1_names, l2_names = {}, {}
    for row in taxonomy:
        # Sheet 2 explicitly places the 2021 hierarchy in columns E:H.
        l1, l2, _l3, raw_code = row[4:8]
        code = _code(raw_code)
        if code and _name(l1):
            l1_names[code[:2]] = _name(l1)
        if code and _name(l2):
            l2_names[code[:4]] = _name(l2)
    latest: dict[str, tuple[date, date, str]] = {}
    for row in records:
        security = _code(row.get("股票代码"))
        effective = as_date(row.get("计入日期"))
        industry = _code(row.get("行业代码"))
        updated = as_date(row.get("更新日期")) or date.min
        if not security or not industry or not effective or effective > as_of:
            continue
        candidate = (effective, updated, industry)
        if security not in latest or candidate[:2] > latest[security][:2]:
            latest[security] = candidate
    result = []
    for security, (effective, _, industry) in sorted(latest.items()):
        l1_name = l1_names.get(industry[:2], "")
        l2_name = l2_names.get(industry[:4], "")
        l1_code, l2_code = l1_indices.get(l1_name), l2_indices.get(l2_name)
        if not l1_code or not l2_code:
            continue
        result.append(
            ShenwanMembership(
                security_code=security,
                sw_l1_code=l1_code,
                sw_l1_name=l1_name,
                sw_l2_code=l2_code,
                sw_l2_name=l2_name,
                classification_version=version,
                effective_from=effective,
            )
        )
    if not result:
        raise ResearchProviderError("shenwan_membership_empty")
    return result


async def collect_shenwan_memberships(*, timeout: float) -> list[ShenwanMembership]:
    def load():
        # Native verification builds missing intermediate chains on Windows.
        # Scope this context to this client; never patch SSL or disable verification.
        with httpx.Client(
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
            trust_env=False,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
        ) as client:
            responses = []
            for url in (CLASSIFICATIONS_URL, TAXONOMY_URL, INDEX_IDENTITIES_URL):
                response = client.get(url, headers={"Referer": url})
                response.raise_for_status()
                responses.append(response)
        records = pd.read_excel(BytesIO(responses[0].content), dtype=str).to_dict("records")
        taxonomy = pd.read_excel(BytesIO(responses[1].content), sheet_name=1, dtype=str)
        l1, l2 = index_identities(responses[2].text)
        digest = hashlib.sha256(responses[0].content + responses[1].content).hexdigest()[:16]
        return normalize_memberships(
            records,
            taxonomy.values.tolist(),
            l1,
            l2,
            version=f"sw-2021-{digest}",
            as_of=datetime.now(ZoneInfo("Asia/Shanghai")).date(),
        )

    return await asyncio.to_thread(load)
