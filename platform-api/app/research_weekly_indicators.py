"""Separate weekly-report additions: public collection and local-only projection."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import re
import ssl
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import openpyxl
import truststore

from app.research_equity_metrics import number
from app.research_local_data import hedge_board_data_root, read_local_json, write_local_json
from app.research_provider_errors import ResearchProviderError
from app.research_weekly_catalog import BATCH_ID, COVERED, INDICATORS, REPORTS

ARTIFACT = "public/v1/macro/weekly-report-indicators.json"
_LOCK = asyncio.Lock()
_CHINA = ZoneInfo("Asia/Shanghai")
_LOG = logging.getLogger(__name__)
SECTIONS = {item["section"] for item in INDICATORS}
BY_ID = {item["id"]: item for item in INDICATORS}
INDUSTRY_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
CPCA_URL = "https://data.cpcadata.com/api/chartlist"
EXTRA_URLS = {
    "epu_mainland": "https://www.policyuncertainty.com/media/China_Mainland_Paper_EPU.xlsx",
    "boj": "https://www.stat-search.boj.or.jp/api/v1/getDataCode",
    "ecb": "https://data-api.ecb.europa.eu/service/data/BSI/M.U2.Y.V.M20.X.1.U2.2300.Z01.E",
    "cfets": "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-fx/RmbIdxHis",
}


def local(path):
    try:
        return read_local_json(path)
    except ResearchProviderError as exc:
        if "local_data_not_found:" in str(exc):
            return {}
        raise


def normalized_points(rows, *, today=None):
    """Reject conflicting dates/nonfinite numbers; preserve explicit missing values."""
    today = today or datetime.now(_CHINA).date()
    values = {}
    for row in rows:
        day = str(row["date"])
        if date.fromisoformat(day) > today:
            raise ValueError("future_observation")
        raw = row["value"]
        value = number(raw)
        if raw is not None and value is None:
            raise ValueError("invalid_observation")
        if day in values and values[day] != value:
            raise ValueError("conflicting_observation")
        values[day] = value
    if not values or not any(v is not None for v in values.values()):
        raise ValueError("empty_observations")
    return [
        {"date": day, "value": str(value) if value is not None else None}
        for day, value in sorted(values.items())
    ]


def parse_industry(payload, identity):
    if payload.get("success") is not True:
        raise ValueError("industry_source_failed")
    rows = payload["result"]["data"]
    if any(row["INDICATOR_ID"] != identity for row in rows):
        raise ValueError("industry_identity_mismatch")
    return normalized_points(
        [{"date": row["REPORT_DATE"][:10], "value": row["INDICATOR_VALUE"]} for row in rows]
    )


def parse_epu(content, field):
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    if not reader.fieldnames or field not in reader.fieldnames:
        raise ValueError("epu_columns_changed")
    names = {key.lower(): key for key in reader.fieldnames}
    rows = []
    for row in reader:
        day = date(int(row[names["year"]]), int(row[names["month"]]), 1).isoformat()
        rows.append({"date": day, "value": row[field] if row[field].strip() else None})
    return normalized_points(rows)


def parse_cpca(payload):
    # AKShare and the publisher identify block 0 as the narrow passenger-car market.
    # Require the publisher's category and all year arrays instead of positional columns.
    if not payload or payload[0].get("category") != "整体市场":
        raise ValueError("cpca_category_changed")
    result = {key: [] for key in ("passenger_car_retail", "passenger_car_wholesale")}
    for row in payload[0]["dataList"]:
        month = int(re.fullmatch(r"(\d{1,2})月", row["month"])[1])
        for year, values in row.items():
            if not re.fullmatch(r"\d{4}年", year):
                continue
            if not isinstance(values, list) or len(values) != 4:
                raise ValueError("cpca_columns_changed")
            # A source's blank future month is not a zero sale or a future observation.
            if all(value in (None, "") for value in values):
                continue
            day = date(int(year[:4]), month, 1)
            if day >= datetime.now(_CHINA).date().replace(day=1):
                continue  # Complete monthly statistics only.
            for key, index in [("passenger_car_retail", 2), ("passenger_car_wholesale", 1)]:
                result[key].append({"date": day.isoformat(), "value": values[index]})
    return {key: normalized_points(rows) for key, rows in result.items()}


def monthly_yoy(rows):
    values = {}
    for row in sorted(rows, key=lambda row: row["date"]):
        values[row["date"][:7]] = row
    output = []
    for month, row in sorted(values.items()):
        previous = f"{int(month[:4]) - 1:04d}{month[4:]}"
        current = number(row.get("value"))
        base = number(values.get(previous, {}).get("value"))
        output.append(
            {
                "date": row["date"],
                "value": str((current / base - 1) * 100)
                if current is not None and base is not None and base > 0
                else None,
            }
        )
    return output


def parse_extra(kind, content):
    if kind == "epu_mainland":
        workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        try:
            sheet = workbook["EPU 2000 onwards"]
            rows = list(sheet.values)
            if rows[0][:3] != ("year", "month", "EPU"):
                raise ValueError("epu_columns_changed")
            return normalized_points(
                [
                    {"date": date(int(r[0]), int(r[1]), 1).isoformat(), "value": r[2]}
                    for r in rows[1:]
                    if r[0] is not None
                ]
            )
        finally:
            workbook.close()
    if kind == "cfets":
        raw = json.loads(content)
        if raw.get("data", {}).get("message"):
            raise ValueError("cfets_source_limit")
        return normalized_points(
            [{"date": r["showDate"], "value": r["cfetsIndexRate"]} for r in raw["records"]]
        )
    if kind == "boj":
        raw = json.loads(content)["RESULTSET"][0]
        if raw["UNIT"] != "100 million yen" or raw["SERIES_CODE"] != "MAM1NAM2M2MO":
            raise ValueError("boj_identity_changed")
        points = [
            {"date": f"{str(d)[:4]}-{str(d)[4:6]}-01", "value": v}
            for d, v in zip(raw["VALUES"]["SURVEY_DATES"], raw["VALUES"]["VALUES"], strict=True)
        ]
    elif kind == "ecb":
        raw = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
        if any(
            r["KEY"] != "BSI.M.U2.Y.V.M20.X.1.U2.2300.Z01.E"
            or r["UNIT"] != "EUR"
            or r["UNIT_MULT"] != "6"
            for r in raw
        ):
            raise ValueError("ecb_identity_changed")
        points = [{"date": r["TIME_PERIOD"] + "-01", "value": r["OBS_VALUE"] or None} for r in raw]
    else:
        raise ValueError("unknown_source")
    return monthly_yoy(normalized_points(points))


def _source_url(item):
    if item.get("collector") in EXTRA_URLS:
        return {
            "epu_mainland": "https://www.policyuncertainty.com/china_monthly.html",
            "cfets": "https://www.chinamoney.com.cn/chinese/bkrmbidx/",
        }.get(item["collector"], EXTRA_URLS[item["collector"]])
    if item.get("collector") == "industry":
        return f"https://data.eastmoney.com/cjsj/hyzs_list_{item['sourceId']}.html"
    if item.get("collector") == "epu":
        return f"https://www.policyuncertainty.com/media/{item['sourceId']}_Policy_Uncertainty_Data.csv"
    if item.get("collector") == "cpca":
        return "https://data.cpcadata.com/TotalMarket"
    return None


def _archive(key, content, stamp):
    digest = hashlib.sha256(content).hexdigest()
    path = (
        hedge_board_data_root() / "raw" / "macro" / BATCH_ID / key / stamp[:10] / (digest + ".bin")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)
    return digest


async def collect(force=False):
    """Independent daily jobs; failure preserves observations and degrades metadata."""
    async with _LOCK:
        now = datetime.now(UTC)
        stamp = now.isoformat()
        document = await asyncio.to_thread(local, ARTIFACT)
        sources = document.setdefault("sources", {})
        document["batchId"] = BATCH_ID
        jobs = [
            item for item in INDICATORS if item.get("collector") in {"industry", "epu", *EXTRA_URLS}
        ]
        jobs.append(BY_ID["passenger_car_retail"])
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        async with httpx.AsyncClient(
            verify=context,
            timeout=httpx.Timeout(25, connect=10),
            follow_redirects=True,
            trust_env=True,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            for item in jobs:
                key = item["id"]
                ids = (
                    [key]
                    if item["collector"] != "cpca"
                    else ["passenger_car_retail", "passenger_car_wholesale"]
                )
                old = sources.get(key, {})
                if not force and old.get("attemptedAt"):
                    delay = timedelta(hours=4 if old.get("status") == "error" else 20)
                    if now - datetime.fromisoformat(old["attemptedAt"]) < delay:
                        continue
                try:
                    raw_hashes = []
                    if item["collector"] == "industry":
                        cutoff = (now.date() - timedelta(days=3653)).isoformat()
                        if old.get("observations"):
                            cutoff = (
                                date.fromisoformat(old["observations"][-1]["date"])
                                - timedelta(days=35)
                            ).isoformat()
                        params = {
                            "reportName": "RPT_INDUSTRY_INDEX",
                            "columns": "REPORT_DATE,INDICATOR_VALUE,INDICATOR_ID",
                            "filter": (
                                f"(INDICATOR_ID=\"{item['sourceId']}\")"
                                f"(REPORT_DATE>='{cutoff}')"
                            ),
                            "sortColumns": "REPORT_DATE",
                            "sortTypes": "-1",
                            "pageSize": 500,
                            "pageNumber": 1,
                        }
                        rows = []
                        for page in range(1, 31):
                            response = await client.get(
                                INDUSTRY_URL, params={**params, "pageNumber": page}
                            )
                            response.raise_for_status()
                            raw_hashes.append(
                                await asyncio.to_thread(_archive, key, response.content, stamp)
                            )
                            payload = response.json()
                            rows.extend(parse_industry(payload, item["sourceId"]))
                            if page >= payload["result"]["pages"]:
                                break
                        else:
                            raise ValueError("industry_pagination_limit")
                        collected = {key: normalized_points(rows)}
                    elif item["collector"] in EXTRA_URLS:
                        kind = item["collector"]
                        start = (now.date() - timedelta(days=3653)).replace(day=1).isoformat()
                        params = {
                            "epu_mainland": {},
                            "boj": {
                                "format": "json",
                                "lang": "en",
                                "db": "MD02",
                                "startDate": start[:7].replace("-", ""),
                                "code": "MAM1NAM2M2MO",
                            },
                            "ecb": {"startPeriod": start[:7], "format": "csvdata"},
                            "cfets": {
                                "lang": "cn",
                                "startDate": (now.date() - timedelta(days=364)).isoformat(),
                                "endDate": now.date().isoformat(),
                            },
                        }[kind]
                        response = await client.get(EXTRA_URLS[kind], params=params)
                        response.raise_for_status()
                        raw_hashes.append(
                            await asyncio.to_thread(_archive, key, response.content, stamp)
                        )
                        collected = {key: parse_extra(kind, response.content)}
                    else:
                        url = CPCA_URL if item["collector"] == "cpca" else _source_url(item)
                        response = await client.get(
                            url, params={"charttype": "1"} if item["collector"] == "cpca" else {}
                        )
                        response.raise_for_status()
                        raw_hashes.append(
                            await asyncio.to_thread(_archive, key, response.content, stamp)
                        )
                        collected = (
                            parse_cpca(response.json())
                            if item["collector"] == "cpca"
                            else {key: parse_epu(response.content, item["field"])}
                        )
                    for series_id, rows in collected.items():
                        # Publisher revisions replace the matching date; omitted historical
                        # dates stay retained, with no inferred observations between them.
                        merged = {
                            r["date"]: r for r in sources.get(series_id, {}).get("observations", [])
                        }
                        merged.update({r["date"]: r for r in rows})
                        sources[series_id] = {
                            "status": "ready",
                            "attemptedAt": stamp,
                            "retrievedAt": stamp,
                            "sourceUrl": _source_url(BY_ID[series_id]),
                            "rawSha256": raw_hashes,
                            "source": {
                                "industry": "东方财富公开行业数据",
                                "epu": "Economic Policy Uncertainty",
                                "epu_mainland": "Davis / Liu / Sheng · Economic Policy Uncertainty",
                                "cpca": "乘联分会",
                                "boj": "日本银行 · M2月均余额",
                                "ecb": "欧洲央行 · M2季调月末余额",
                                "cfets": "中国外汇交易中心",
                            }[item["collector"]],
                            "observations": normalized_points(merged.values()),
                        }
                except Exception as exc:
                    _LOG.warning("Weekly-report source %s: %s", key, type(exc).__name__)
                    for series_id in ids:
                        sources[series_id] = {
                            **sources.get(series_id, {}),
                            "status": "error",
                            "attemptedAt": stamp,
                            "error": type(exc).__name__,
                            "sourceUrl": _source_url(BY_ID[series_id]),
                        }
                document["updatedAt"] = stamp
                await asyncio.to_thread(write_local_json, ARTIFACT, document)
        return {key: value["status"] for key, value in sources.items()}


def read_supplement(section, indicator=None, *, today=None):
    if section not in SECTIONS or (
        indicator is not None and (indicator not in BY_ID or BY_ID[indicator]["section"] != section)
    ):
        raise ValueError("unknown_weekly_indicator")
    today = today or datetime.now(_CHINA).date()
    try:
        document = local(ARTIFACT)
        artifact_error = False
    except ResearchProviderError:
        document, artifact_error = {}, True
    output = []
    for definition in INDICATORS:
        if definition["section"] != section:
            continue
        key = definition["id"]
        source = document.get("sources", {}).get(key, {})
        if definition.get("localSeries"):
            try:
                source = local(f"public/v1/macro/series/{definition['localSeries']}.json")
                source = {**source, "observations": monthly_yoy(source.get("observations", []))}
            except ResearchProviderError:
                source = {"status": "error"}
        rows = source.get("observations", [])
        if definition.get("divisor"):
            rows = [
                {
                    **row,
                    "value": str(number(row["value"]) / Decimal(definition["divisor"]))
                    if number(row["value"]) is not None
                    else None,
                }
                for row in rows
            ]
        valid = [row for row in rows if number(row["value"]) is not None]
        last = valid[-1] if valid else None
        tolerance = {"daily": 7, "weekly": 14, "monthly": 75, "quarterly": 200}[
            definition["frequency"]
        ]
        stale = bool(last and (today - date.fromisoformat(last["date"])).days > tolerance)
        if last:
            status = (
                "degraded"
                if source.get("status") in {"error", "degraded"}
                else "stale"
                if stale or source.get("isStale")
                else "ready"
            )
        else:
            status = "error" if source.get("status") == "error" or artifact_error else "no_data"
        series = dict(
            seriesId=key,
            label=definition["label"],
            unit=definition["unit"],
            frequency=definition["frequency"],
            timezone="Asia/Shanghai",
            status=status,
            latestValue=last["value"] if last else None,
            observationDate=last["date"] if last else None,
            source=source.get("source", ""),
            sourceUrl=source.get("sourceUrl"),
            retrievedAt=source.get("retrievedAt"),
            isStale=stale or bool(source.get("isStale")),
            methodologyVersion=BATCH_ID,
            qualityFlags=[],
            observations=rows if indicator == key else [],
        )
        output.append(
            {
                **{
                    k: v
                    for k, v in definition.items()
                    if k not in {"collector", "field", "sourceId", "localSeries", "transform"}
                },
                "reportTitle": REPORTS[definition["report"]]["title"],
                "reportDate": REPORTS[definition["report"]]["date"],
                "series": series,
            }
        )
    return {
        "batchId": BATCH_ID,
        "section": section,
        "updatedAt": document.get("updatedAt"),
        "items": output,
        "covered": COVERED,
    }


async def run_periodic():
    while True:
        try:
            await collect()
        except Exception:
            _LOG.exception("Weekly-report collection failed")
        await asyncio.sleep(300)
