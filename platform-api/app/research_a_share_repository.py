from __future__ import annotations

import json
import sqlite3
from contextlib import nullcontext
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.database import connection
from app.a_share_research_policy import market_breadth_pct
from app.research_data_schemas import (
    AShareDashboardResponse,
    AShareIndexHistoryPoint,
    ResearchModuleResult,
)

# Initial platform-owned theme baskets migrated from the approved historical
# stock-pool definition.  They are research configuration, not market facts.
DEFAULT_STOCK_POOL_BASKETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "ai_semiconductor",
        "AI算力/半导体",
        (
            "00981",
            "01347",
            "688012",
            "688041",
            "688256",
            "603986",
            "688008",
            "600584",
            "002156",
            "300373",
            "688234",
            "300666",
            "688037",
            "300604",
            "688372",
            "688820",
            "688825",
            "688521",
            "688141",
            "688048",
            "300661",
            "300395",
            "603650",
            "603893",
            "300857",
            "688702",
            "688146",
            "600330",
        ),
    ),
    (
        "ai_pcb_optical",
        "AI PCB/光通信",
        (
            "300476",
            "002916",
            "002463",
            "600183",
            "688183",
            "002384",
            "01888",
            "300903",
            "301377",
            "688300",
            "301217",
            "300308",
            "300502",
            "000100",
            "000725",
            "000063",
            "002475",
            "000636",
            "003031",
            "600353",
            "603256",
            "300394",
            "002281",
            "300620",
            "688313",
            "688143",
            "300548",
            "601869",
            "600487",
            "688498",
            "688502",
            "002484",
            "300408",
        ),
    ),
    (
        "robotics_datacenter",
        "机器人/自动化/数据中心",
        (
            "601689",
            "002050",
            "688017",
            "09880",
            "09660",
            "601100",
            "688777",
            "002851",
            "002008",
            "301200",
            "301396",
            "02513",
            "688025",
            "603308",
            "301018",
            "002837",
            "688630",
            "300757",
            "300776",
            "300870",
            "688808",
            "600875",
        ),
    ),
    (
        "resources_cycle",
        "资源品/黄金/周期",
        (
            "601899",
            "600988",
            "000426",
            "603993",
            "601168",
            "000807",
            "600549",
            "000657",
            "600301",
            "002428",
            "000688",
            "001203",
            "603799",
            "600938",
            "601225",
            "600188",
            "600309",
            "002648",
            "600346",
            "600989",
            "600141",
            "000893",
            "600160",
            "605376",
            "600176",
            "002353",
        ),
    ),
    (
        "innovative_drug",
        "创新药/CXO/AI医疗",
        ("600276", "06160", "01801", "09926", "06990", "603259", "02269", "02268", "02228"),
    ),
    (
        "new_energy",
        "新能源",
        (
            "300750",
            "300274",
            "600438",
            "600732",
            "605117",
            "002709",
            "301358",
            "688778",
            "300450",
            "300776",
            "002487",
            "301511",
            "688676",
            "688585",
        ),
    ),
    (
        "consumer_internet",
        "消费/互联网/出海",
        (
            "600519",
            "000333",
            "600690",
            "00700",
            "09988",
            "01810",
            "02020",
            "09992",
            "605499",
            "300866",
            "689009",
            "02015",
            "01364",
            "301498",
            "002832",
            "688775",
            "300209",
        ),
    ),
    (
        "core_assets",
        "金融/红利/核心资产",
        (
            "601398",
            "601318",
            "601336",
            "601628",
            "600030",
            "300059",
            "600941",
            "600900",
            "600031",
            "000338",
            "600066",
            "600233",
            "601058",
            "002714",
        ),
    ),
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _conflict_evidence(record: Any, fields: tuple[str, ...]) -> str:
    evidence: dict[str, Any] = {}
    for field in fields:
        value = record[field]
        if field == "payload_json":
            try:
                value = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                pass
            evidence["payload"] = value
        else:
            evidence[field] = _jsonable(value)
    return json.dumps(evidence, ensure_ascii=False, sort_keys=True)


def write_market_archive(row: dict[str, Any], *, db: sqlite3.Connection | None = None) -> str:
    """Idempotently persist one source market aggregate; never overwrite conflicts."""
    universe = str(row.get("universe_key") or row.get("dataset"))
    trade_date = str(row["trade_date"])
    payload = _jsonable(row.get("payload", row))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    values = (
        universe,
        trade_date,
        str(row["amount_yuan"]) if row.get("amount_yuan") is not None else None,
        row.get("up"),
        row.get("down"),
        row.get("flat"),
        row.get("limit_up"),
        row.get("limit_down"),
        str(row["market_breadth_pct"]) if row.get("market_breadth_pct") is not None else None,
        str(row.get("source_name") or row.get("source") or ""),
        row.get("definition_version"),
        encoded,
        row.get("quality_status", "ready"),
        _now(),
    )
    with nullcontext(db) if db is not None else connection() as target:
        existing = target.execute(
            "SELECT * FROM research_a_share_market_archive WHERE universe_key=? AND trade_date=?",
            (universe, trade_date),
        ).fetchone()
        if existing is None:
            target.execute(
                """INSERT INTO research_a_share_market_archive
                (universe_key,trade_date,amount_yuan,up,down,flat,limit_up,limit_down,
                 market_breadth_pct,source_name,definition_version,payload_json,
                 quality_status,imported_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                values,
            )
            return "inserted"
        incoming = dict(zip(existing.keys(), values, strict=True))
        if all(
            existing[key] == incoming[key]
            for key in (
                "amount_yuan",
                "up",
                "down",
                "flat",
                "limit_up",
                "limit_down",
                "market_breadth_pct",
                "source_name",
                "definition_version",
                "payload_json",
                "quality_status",
            )
        ):
            return "skipped"
        target.execute(
            """INSERT OR IGNORE INTO research_a_share_archive_conflicts
            (table_name,natural_key,existing_payload_json,incoming_payload_json,source_name,reason,observed_at)
            VALUES (?,?,?,?,?,?,?)""",
            (
                "market",
                f"{universe}:{trade_date}",
                _conflict_evidence(
                    existing,
                    (
                        "amount_yuan",
                        "up",
                        "down",
                        "flat",
                        "limit_up",
                        "limit_down",
                        "market_breadth_pct",
                        "source_name",
                        "definition_version",
                        "payload_json",
                        "quality_status",
                    ),
                ),
                _conflict_evidence(
                    incoming,
                    (
                        "amount_yuan",
                        "up",
                        "down",
                        "flat",
                        "limit_up",
                        "limit_down",
                        "market_breadth_pct",
                        "source_name",
                        "definition_version",
                        "payload_json",
                        "quality_status",
                    ),
                ),
                values[9],
                "natural_key_conflict",
                _now(),
            ),
        )
        return "conflict"


def write_price_archive(row: dict[str, Any], *, db: sqlite3.Connection | None = None) -> str:
    """Idempotently persist an index/industry close and record immutable conflicts."""
    code = str(row["instrument_code"])
    trade_date = str(row.get("trade_date") or row.get("observed_at"))[:10]
    source = str(row.get("source_name") or row.get("source") or "")
    definition = str(row.get("definition_version") or row.get("definition_level") or "")
    industry_level = str(row.get("industry_level") or "")
    close = row.get("close", row.get("price"))
    encoded = json.dumps(_jsonable(row.get("payload", row)), ensure_ascii=False, sort_keys=True)
    values = (
        code,
        trade_date,
        source,
        definition,
        industry_level,
        str(close) if close is not None else None,
        encoded,
        row.get("quality_status", "ready"),
        _now(),
    )
    with nullcontext(db) if db is not None else connection() as target:
        existing = target.execute(
            """SELECT * FROM research_a_share_price_history
            WHERE instrument_code=? AND trade_date=? AND source_name=?
              AND definition_version=? AND industry_level=?""",
            (code, trade_date, source, definition, industry_level),
        ).fetchone()
        if existing is None:
            target.execute(
                """INSERT INTO research_a_share_price_history
                (instrument_code,trade_date,source_name,definition_version,industry_level,
                 close,payload_json,quality_status,imported_at) VALUES (?,?,?,?,?,?,?,?,?)""",
                values,
            )
            return "inserted"
        try:
            same_close = (
                existing["close"] is None
                and values[5] is None
                or existing["close"] is not None
                and values[5] is not None
                and Decimal(str(existing["close"])) == Decimal(str(values[5]))
            )
        except InvalidOperation:
            same_close = existing["close"] == values[5]
        # The first accepted raw payload remains the evidence record. A later
        # observation with the same natural key and numeric close is idempotent;
        # only a changed value or quality state is a conflict.
        if same_close and existing["quality_status"] == values[7]:
            return "skipped"
        target.execute(
            """INSERT OR IGNORE INTO research_a_share_archive_conflicts
            (table_name,natural_key,existing_payload_json,incoming_payload_json,source_name,reason,observed_at)
            VALUES (?,?,?,?,?,?,?)""",
            (
                "price",
                f"{code}:{trade_date}:{source}:{definition}:{industry_level}",
                _conflict_evidence(
                    existing,
                    (
                        "close",
                        "source_name",
                        "definition_version",
                        "industry_level",
                        "payload_json",
                        "quality_status",
                    ),
                ),
                _conflict_evidence(
                    dict(zip(existing.keys(), values, strict=True)),
                    (
                        "close",
                        "source_name",
                        "definition_version",
                        "industry_level",
                        "payload_json",
                        "quality_status",
                    ),
                ),
                source,
                "natural_key_conflict",
                _now(),
            ),
        )
        return "conflict"


def archive_a_share_audit() -> dict[str, Any]:
    with connection() as db:
        result: dict[str, Any] = {"market": {}, "prices": {}}
        fields = ("amount_yuan", "up", "down", "flat", "limit_up", "limit_down")
        for universe_row in db.execute(
            "SELECT DISTINCT universe_key FROM research_a_share_market_archive"
        ).fetchall():
            universe = str(universe_row["universe_key"])
            coverage: dict[str, Any] = {}
            for field in fields:
                row = db.execute(
                    f"""SELECT MIN(CASE WHEN {field} IS NOT NULL THEN trade_date END) earliest,
                    MAX(CASE WHEN {field} IS NOT NULL THEN trade_date END) latest,
                    SUM(CASE WHEN {field} IS NOT NULL THEN 1 ELSE 0 END) non_empty,
                    SUM(CASE WHEN {field} IS NULL THEN 1 ELSE 0 END) missing
                    FROM research_a_share_market_archive WHERE universe_key=?""",
                    (universe,),
                ).fetchone()
                coverage[field] = dict(row)
            result["market"][universe] = coverage
        for row in db.execute(
            """SELECT instrument_code,MIN(trade_date) earliest,MAX(trade_date) latest,
            COUNT(*) total,SUM(CASE WHEN close IS NOT NULL THEN 1 ELSE 0 END) non_empty,
            SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) missing
            FROM research_a_share_price_history GROUP BY instrument_code"""
        ).fetchall():
            item = dict(row)
            result["prices"][item.pop("instrument_code")] = item
        result["conflicts"] = db.execute(
            "SELECT COUNT(*) AS count FROM research_a_share_archive_conflicts"
        ).fetchone()["count"]
    return result


def read_market_amount_page(page: int = 1, page_size: int = 100) -> dict[str, Any]:
    page = max(1, int(page))
    page_size = min(500, max(1, int(page_size)))
    with connection() as db:
        total = db.execute(
            "SELECT COUNT(*) AS n FROM research_a_share_market_archive "
            "WHERE universe_key='all_a' AND quality_status <> 'conflict'"
        ).fetchone()["n"]
        rows = db.execute(
            """SELECT trade_date,amount_yuan,source_name FROM research_a_share_market_archive
            WHERE universe_key='all_a' AND quality_status <> 'conflict'
            ORDER BY trade_date DESC LIMIT ? OFFSET ?""",
            (page_size, (page - 1) * page_size),
        ).fetchall()
        coverage = db.execute(
            "SELECT MIN(trade_date) AS start, MAX(trade_date) AS end "
            "FROM research_a_share_market_archive WHERE universe_key='all_a' "
            "AND quality_status <> 'conflict'"
        ).fetchone()
        all_rows = db.execute(
            "SELECT trade_date,amount_yuan FROM research_a_share_market_archive "
            "WHERE universe_key='all_a' AND quality_status <> 'conflict' ORDER BY trade_date"
        ).fetchall()
    previous = None
    changes: dict[str, Decimal | None] = {}
    for row in all_rows:
        current = Decimal(str(row["amount_yuan"])) if row["amount_yuan"] is not None else None
        changes[row["trade_date"]] = (
            (current / previous - Decimal("1")) * 100
            if current is not None and previous and previous > 0
            else None
        )
        previous = current
    return {
        "rows": [
            {
                "observedAt": row["trade_date"],
                "totalAmountYuan": row["amount_yuan"],
                "amountChangePct": changes.get(row["trade_date"]),
                "source": _display_source(row["source_name"]),
            }
            for row in rows
        ],
        "coverageStart": coverage["start"],
        "coverageEnd": coverage["end"],
        "tradingDays": total,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


def _display_source(value: str | None) -> str | None:
    source = str(value or "").strip()
    lowered = source.lower()
    if not source:
        return None
    if "choice" in lowered:
        return "Choice（历史聚合）"
    if "eastmoney" in lowered or "东方财富" in source:
        return "东方财富（延迟行情）"
    if "legu" in lowered or "乐咕" in source:
        return "乐咕"
    if "tencent" in lowered or "腾讯" in source:
        return "腾讯指数日线"
    return source


def start_refresh(run_id: str, target_trade_date: str | None) -> None:
    with connection() as db:
        db.execute(
            (
                "INSERT INTO research_a_share_refresh_runs(run_id,target_trade_date,started_a"
                "t,status) VALUES (?,?,?,?)"
            ),
            (run_id, target_trade_date, _now(), "running"),
        )


def finish_refresh(
    run_id: str, status: str, *, error_code: str | None = None, message: str | None = None
) -> None:
    with connection() as db:
        db.execute(
            (
                "UPDATE research_a_share_refresh_runs SET finished_at=?,status=?,error_code=?"
                ",message=? WHERE run_id=?"
            ),
            (_now(), status, error_code, message, run_id),
        )


def read_refresh_status() -> dict[str, Any] | None:
    with connection() as db:
        row = db.execute(
            "SELECT run_id,target_trade_date,started_at,finished_at,status,error_code,mes"
            "sage FROM research_a_share_refresh_runs "
            "WHERE run_id LIKE 'a-share-%' OR target_trade_date IS NOT NULL "
            "ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "runId": row["run_id"],
        "targetTradeDate": row["target_trade_date"],
        "startedAt": row["started_at"],
        "finishedAt": row["finished_at"],
        "status": row["status"],
        "errorCode": row["error_code"],
        "message": row["message"],
    }


def write_dashboard(
    run_id: str, dashboard: AShareDashboardResponse, *, db: sqlite3.Connection | None = None
) -> None:
    """Atomically replace latest datasets and append normalized history rows."""
    fetched = dashboard.generated_at.isoformat()
    modules: dict[str, ResearchModuleResult] = {
        "market_detail": dashboard.market_detail,
        "breadth": dashboard.breadth,
        "shenwan": dashboard.shenwan,
        "emotion": dashboard.emotion,
    }
    if dashboard.crowding is not None:
        modules["crowding"] = dashboard.crowding
    with nullcontext(db) if db is not None else connection() as db:
        for dataset, module in modules.items():
            meta = module.meta
            existing = db.execute(
                "SELECT payload_json FROM research_a_share_dataset_snapshots WHERE dataset=?",
                (dataset,),
            ).fetchone()
            # A failed collection must not erase the last meaningful snapshot.
            # The refresh run records the failure while the API continues serving LKG data.
            if (
                existing is not None
                and existing["payload_json"]
                and meta.status in {"error", "no_data"}
            ):
                db.execute(
                    (
                        "UPDATE research_a_share_dataset_snapshots "
                        "SET status='stale',error_code=?,me"
                        "ssage=?,refresh_run_id=? WHERE dataset=?"
                    ),
                    (meta.error_code, meta.message, run_id, dataset),
                )
                continue
            payload = module.data
            payload_json = (
                json.dumps(_jsonable(payload), ensure_ascii=False, separators=(",", ":"))
                if payload is not None
                else None
            )
            observed = meta.source_timestamp.isoformat() if meta.source_timestamp else None
            db.execute(
                """INSERT INTO research_a_share_dataset_snapshots
                (dataset,observed_at,fetched_at,status,source,payload_json,error_code,message,refresh_run_id)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(dataset) DO UPDATE SET observed_at=excluded.observed_at,
                fetched_at=excluded.fetched_at,status=excluded.status,source=excluded.source,
                payload_json=excluded.payload_json,error_code=excluded.error_code,
                message=excluded.message,refresh_run_id=excluded.refresh_run_id""",
                (
                    dataset,
                    observed,
                    fetched,
                    meta.status,
                    meta.source,
                    payload_json,
                    meta.error_code,
                    meta.message,
                    run_id,
                ),
            )
        # Keep index history in a queryable table; this is the long-lived chart source.
        if dashboard.market_detail.data:
            for item in dashboard.market_detail.data:
                history = (
                    item.get("history", [])
                    if isinstance(item, dict)
                    else getattr(item, "history", [])
                )
                code = str(item.get("code") if isinstance(item, dict) else item.code)
                for point in history:
                    row = point if isinstance(point, dict) else point.model_dump(mode="json")
                    db.execute(
                        """INSERT INTO research_a_share_history
                        (dataset,observed_at,entity_code,payload_json,source,fetched_at,refresh_run_id)
                        VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset,observed_at,entity_code)
                        DO UPDATE SET payload_json=excluded.payload_json,source=excluded.source,
                        fetched_at=excluded.fetched_at,refresh_run_id=excluded.refresh_run_id""",
                        (
                            "index",
                            row.get("observedAt", row.get("observed_at")),
                            code,
                            json.dumps(row, ensure_ascii=False),
                            dashboard.market_detail.meta.source,
                            fetched,
                            run_id,
                        ),
                    )
        breadth = dashboard.breadth.data
        if breadth is not None and getattr(breadth, "trade_date", None):
            observed = breadth.trade_date.isoformat()
            payload = {
                "up": breadth.up,
                "down": breadth.down,
                "flat": breadth.flat,
                "limitUp": breadth.limit_up,
                "limitDown": breadth.limit_down,
                "totalAmountYuan": breadth.total_amount_yuan,
                "marketBreadthPct": market_breadth_pct(breadth.up, breadth.down),
            }
            db.execute(
                """INSERT INTO research_a_share_history
                (dataset,observed_at,entity_code,payload_json,source,fetched_at,refresh_run_id)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset,observed_at,entity_code)
                DO UPDATE SET payload_json=excluded.payload_json,fetched_at=excluded.fetched_at,
                refresh_run_id=excluded.refresh_run_id""",
                (
                    "market",
                    observed,
                    "market",
                    json.dumps(_jsonable(payload), ensure_ascii=False),
                    dashboard.breadth.meta.source,
                    fetched,
                    run_id,
                ),
            )


def _source_timestamp(value: str | None) -> str | None:
    # Historical imports store daily observation dates; API metadata uses an
    # aware timestamp at the mainland session close, never the current clock.
    return f"{value}T15:00:00+08:00" if value and len(value) == 10 else value


def read_dashboard() -> AShareDashboardResponse | None:
    with connection() as db:
        rows = db.execute(
            "SELECT dataset, fetched_at, payload_json, status, source, error_code, messag"
            "e, observed_at FROM research_a_share_dataset_snapshots"
        ).fetchall()
    if not rows:
        return None
    by_name = {str(row["dataset"]): row for row in rows}
    required = {"market_detail", "breadth", "shenwan", "emotion"}
    if not required.issubset(by_name):
        return None
    values: dict[str, Any] = {}
    for name in required:
        row = by_name[name]
        payload = json.loads(row["payload_json"]) if row["payload_json"] else None
        # The overview cards only use the latest fields plus the persisted spark.
        # Full index histories remain in research_a_share_history for a dedicated
        # detail query; sending four multi-year series on every page open made the
        # first-screen payload needlessly large.
        if name == "market_detail" and isinstance(payload, list):
            payload = [
                {key: value for key, value in item.items() if key != "history"}
                if isinstance(item, dict)
                else item
                for item in payload
            ]
        values[name] = {
            "meta": {
                "source": row["source"],
                "sourceTimestamp": _source_timestamp(row["observed_at"]),
                "fetchedAt": row["fetched_at"],
                "status": row["status"],
                "isStale": row["status"] == "stale",
                "errorCode": row["error_code"],
                "message": row["message"],
            },
            "data": payload,
        }
    crowding_row = by_name.get("crowding")
    if crowding_row is not None:
        crowding_payload = (
            json.loads(crowding_row["payload_json"]) if crowding_row["payload_json"] else None
        )
        values["crowding"] = {
            "meta": {
                "source": crowding_row["source"],
                "sourceTimestamp": _source_timestamp(crowding_row["observed_at"]),
                "fetchedAt": crowding_row["fetched_at"],
                "status": crowding_row["status"],
                "isStale": crowding_row["status"] == "stale",
                "errorCode": crowding_row["error_code"],
                "message": crowding_row["message"],
            },
            "data": crowding_payload,
        }
    with connection() as db:
        history_rows = db.execute(
            """SELECT observed_at, payload_json, source FROM (
                SELECT observed_at, payload_json, source
                FROM research_a_share_history
                WHERE dataset='market'
                ORDER BY observed_at DESC
                LIMIT 2000
            ) ORDER BY observed_at"""
        ).fetchall()
    market_history = []
    previous_amount: Decimal | None = None
    for row in history_rows:
        payload = json.loads(row["payload_json"])
        raw_amount = payload.get("totalAmountYuan")
        try:
            amount = Decimal(str(raw_amount)) if raw_amount is not None else None
        except InvalidOperation:
            amount = None
        amount_change_pct = (
            (amount / previous_amount - Decimal("1")) * Decimal("100")
            if amount is not None and previous_amount is not None and previous_amount > 0
            else None
        )
        market_history.append(
            {
                "observedAt": row["observed_at"],
                "source": row["source"],
                **payload,
                "amountChangePct": amount_change_pct,
            }
        )
        previous_amount = amount
    # Imported archives own their explicit universes. The first-screen chart
    # receives only dates needed by SH/SZ structure or CSI 300, while the full
    # all-A amount history remains on the paginated endpoint.
    with connection() as db:
        archive_rows = db.execute(
            "SELECT * FROM research_a_share_market_archive ORDER BY trade_date"
        ).fetchall()
        price_rows = db.execute(
            """SELECT instrument_code,trade_date,close,source_name,quality_status
            FROM research_a_share_price_history
            WHERE instrument_code IN ('000300.SH','801102.SWI','BK0448','BK1106')
            ORDER BY trade_date,source_name"""
        ).fetchall()
    by_date = {str(item.get("observedAt")): item for item in market_history}
    for row in archive_rows:
        if row["quality_status"] == "conflict" or row["universe_key"] != "sh_sz_a":
            continue
        if row["up"] is None and row["down"] is None:
            continue
        item = by_date.setdefault(row["trade_date"], {"observedAt": row["trade_date"]})
        item.update(
            {
                "up": row["up"],
                "down": row["down"],
                "flat": row["flat"],
                "limitUp": row["limit_up"],
                "limitDown": row["limit_down"],
                "marketBreadthPct": row["market_breadth_pct"],
            }
        )

    price_candidates: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for row in price_rows:
        price_candidates.setdefault((row["instrument_code"], row["trade_date"]), []).append(row)

    def _valid_price(code: str, trade_date: str) -> str | None:
        candidates = price_candidates.get((code, trade_date), [])
        if any(row["quality_status"] == "conflict" for row in candidates):
            return None
        closes: set[Decimal] = set()
        for row in candidates:
            if row["close"] is None:
                continue
            try:
                closes.add(Decimal(str(row["close"])))
            except InvalidOperation:
                return None
        return str(next(iter(closes))) if len(closes) == 1 else None

    for (code, trade_date), _candidates in price_candidates.items():
        if code == "000300.SH":
            by_date.setdefault(trade_date, {"observedAt": trade_date})["csi300Close"] = (
                _valid_price(code, trade_date)
            )

    for row in archive_rows:
        if row["universe_key"] == "all_a" and row["trade_date"] in by_date:
            item = by_date[row["trade_date"]]
            item["totalAmountYuan"] = row["amount_yuan"]
            item["source"] = _display_source(row["source_name"])

    market_history = [by_date[key] for key in sorted(by_date)]
    for item in market_history:
        # Imported archives retain their native ratio, while platform-daily-v1
        # retained a percent using a different denominator. Neither raw field
        # defines the serving unit: derive the chart's consistent net advancing
        # percentage from the same up/down counts, without rewriting evidence.
        item["marketBreadthPct"] = market_breadth_pct(item.get("up"), item.get("down"))

    if crowding_row is not None and isinstance(values.get("crowding", {}).get("data"), dict):
        crowding_data = values["crowding"]["data"]
        communication_history = []
        for point in crowding_data.get("history", []):
            item = dict(point)
            targets = dict(item.get("targets") or {})
            communication = dict(targets.get("通信设备") or {})
            communication["price"] = _valid_price("801102.SWI", str(item.get("date")))
            communication["priceIndexCode"] = "801102.SWI"
            targets["通信设备"] = communication
            item["targets"] = targets
            communication_history.append(item)
        crowding_data["history"] = communication_history
        crowding_data["innovationHistory"] = [
            {
                **point,
                "price": _valid_price("BK1106", str(point.get("date"))),
                "priceBoardCode": "BK1106",
            }
            for point in crowding_data.get("innovationHistory", [])
        ]
    latest_run = read_refresh_status()
    if latest_run and latest_run["status"] == "error":
        for value in values.values():
            if value.get("data"):
                value["meta"].update(
                    status="stale", isStale=True, message="最近一次更新失败，保留上次有效数据"
                )
    return AShareDashboardResponse.model_validate(
        {
            "generatedAt": max(str(by_name[name]["fetched_at"]) for name in required),
            **values,
            "marketHistory": market_history,
        }
    )


def write_stock_pool(
    run_id: str, payload: dict[str, Any], *, db: sqlite3.Connection | None = None
) -> None:
    now = _now()
    with nullcontext(db) if db is not None else connection() as db:
        db.execute(
            """INSERT INTO research_a_share_dataset_snapshots
            (dataset,observed_at,fetched_at,status,source,payload_json,refresh_run_id)
            VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset) DO UPDATE SET
            observed_at=excluded.observed_at,fetched_at=excluded.fetched_at,
            status=excluded.status,source=excluded.source,payload_json=excluded.payload_json,
            refresh_run_id=excluded.refresh_run_id""",
            (
                "stock_pool",
                payload.get("meta", {}).get("report_date"),
                now,
                payload.get("meta", {}).get("status", "ready"),
                "platform-research-derived",
                json.dumps(_jsonable(payload), ensure_ascii=False),
                run_id,
            ),
        )


def _attach_default_stock_pool_baskets(payload: dict[str, Any]) -> dict[str, Any]:
    definitions = payload.get("definitions")
    definitions = dict(definitions) if isinstance(definitions, dict) else {}
    existing = definitions.get("research_baskets")
    if isinstance(existing, list) and any(
        isinstance(item, dict) and item.get("name") for item in existing
    ):
        return payload
    valid_codes = {
        str(row.get("code") or "").strip()
        for row in payload.get("stocks") or []
        if isinstance(row, dict) and str(row.get("code") or "").strip()
    }
    definitions["research_baskets"] = [
        {
            "key": key,
            "name": name,
            "codes": [code for code in codes if code in valid_codes],
            "count": sum(code in valid_codes for code in codes),
        }
        for key, name, codes in DEFAULT_STOCK_POOL_BASKETS
    ]
    definitions.setdefault("focus_codes", [])
    payload["definitions"] = definitions
    return payload


def read_pool_configuration(db: sqlite3.Connection | None = None) -> tuple[list[str], int]:
    with nullcontext(db) if db is not None else connection() as db:
        row = db.execute(
            "SELECT codes_json,row_version FROM research_a_share_pool_config WHERE id=1"
        ).fetchone()
    if row is not None:
        return json.loads(row["codes_json"]), int(row["row_version"])
    return list(
        dict.fromkeys(code for _, _, codes in DEFAULT_STOCK_POOL_BASKETS for code in codes)
    ), 0


def update_stock_pool_membership(
    *, add_codes: list[str] | None = None, remove_code: str | None = None
) -> int:
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        codes, version = read_pool_configuration(db)
        codes = [code for code in codes if code != remove_code]
        codes = list(dict.fromkeys([*codes, *(add_codes or [])]))
        if len(codes) > 300:
            raise ValueError("核心股票池最多包含300只证券")
        db.execute(
            """INSERT INTO research_a_share_pool_config VALUES(1,?,?,?)
            ON CONFLICT(id) DO UPDATE SET codes_json=excluded.codes_json,
            row_version=excluded.row_version,updated_at=excluded.updated_at""",
            (json.dumps(codes), version + 1, _now()),
        )
    return len(codes)


def summarize_stock_pool(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("stocks") or []
    valid = [
        row
        for row in rows
        if row.get("change") is not None and row.get("status") not in {"stale", "no_data"}
    ]
    changes = [row["change"] for row in valid]
    amounts = [
        row["amount_yi"]
        for row in rows
        if row.get("amount_yi") is not None
        and row.get("currency", "CNY") == "CNY"
        and row.get("status") not in {"stale", "no_data"}
    ]
    payload["summary"] = {
        "tracked_count": len(rows),
        "quoted_count": len(valid),
        "breadth": {
            "up": sum(x > 0 for x in changes),
            "down": sum(x < 0 for x in changes),
            "flat": sum(x == 0 for x in changes),
            "missing": len(rows) - len(valid),
        },
        "avg_change": sum(changes) / len(changes) if changes else None,
        "total_amount_yi": sum(amounts) if amounts else None,
    }
    payload["heatmap"] = rows
    payload["leaders"] = {}
    for period, field in (("today", "change"), ("5d", "change_5d"), ("20d", "change_20d")):
        ordered = sorted(
            (
                row
                for row in rows
                if row.get(field) is not None and row.get("status") not in {"stale", "no_data"}
            ),
            key=lambda row: row[field],
        )
        payload["leaders"][period] = {
            "up": sorted(ordered, key=lambda row: row[field], reverse=True)[:8],
            "down": ordered[:8],
        }
    return _attach_default_stock_pool_baskets(payload)


def read_stock_pool(extra_codes: list[str] | None = None) -> dict[str, Any]:
    # Configuration is independent of collection; edits never advance quote time.
    with connection() as db:
        codes, version = read_pool_configuration(db)
        row = db.execute(
            "SELECT payload_json FROM research_a_share_dataset_snapshots WHERE dataset='stock_pool'"
        ).fetchone()
    payload: dict[str, Any] = (
        json.loads(row["payload_json"])
        if row and row["payload_json"]
        else {"meta": {"status": "no_data"}}
    )
    by_code = {str(row.get("code")): row for row in payload.get("stocks") or []}
    latest_run = read_refresh_status()
    if latest_run and latest_run["status"] == "error" and by_code:
        payload.setdefault("meta", {})["status"] = "stale"
        for stock in by_code.values():
            if stock.get("status") != "no_data":
                stock["status"] = "stale"
    payload["stocks"] = [
        by_code.get(code, {"code": code, "instrument_id": code, "name": code, "status": "no_data"})
        for code in codes
    ]
    payload["focusStocks"] = [
        by_code.get(code, {"code": code, "instrument_id": code, "name": code, "status": "no_data"})
        for code in extra_codes or []
    ]
    payload["configVersion"] = version
    return summarize_stock_pool(payload)


def write_dataset(
    dataset: str,
    payload: Any,
    *,
    source: str,
    run_id: str,
    observed_at: str | None = None,
    status: str = "ready",
    db: sqlite3.Connection | None = None,
) -> None:
    now = _now()
    with nullcontext(db) if db is not None else connection() as db:
        db.execute(
            """INSERT INTO research_a_share_dataset_snapshots
            (dataset,observed_at,fetched_at,status,source,payload_json,refresh_run_id)
            VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset) DO UPDATE SET
            observed_at=excluded.observed_at,fetched_at=excluded.fetched_at,
            status=excluded.status,source=excluded.source,payload_json=excluded.payload_json,
            refresh_run_id=excluded.refresh_run_id""",
            (
                dataset,
                observed_at,
                now,
                status,
                source,
                json.dumps(_jsonable(payload), ensure_ascii=False),
                run_id,
            ),
        )


def read_dataset(dataset: str) -> Any:
    with connection() as db:
        row = db.execute(
            "SELECT payload_json FROM research_a_share_dataset_snapshots WHERE dataset=?",
            (dataset,),
        ).fetchone()
    return json.loads(row["payload_json"]) if row and row["payload_json"] else None


def read_dataset_metadata(dataset: str) -> dict[str, Any] | None:
    with connection() as db:
        row = db.execute(
            (
                "SELECT observed_at,fetched_at,status,source FROM research_a_share_dataset_sn"
                "apshots WHERE dataset=?"
            ),
            (dataset,),
        ).fetchone()
    return dict(row) if row else None


def read_hot_stock_history(
    *, days: int | None = 90, matrix_days: int | None = 10
) -> dict[str, Any]:
    """Read the Platform-owned >100bn mother table without reprocessing quotes."""
    with connection() as db:
        rows = db.execute(
            """SELECT observed_at,payload_json FROM research_a_share_history
            WHERE dataset='hot_stock' AND observed_at IN (
                SELECT DISTINCT observed_at FROM research_a_share_history
                WHERE dataset='hot_stock' ORDER BY observed_at DESC LIMIT ?)
            ORDER BY observed_at ASC""",
            (days if days is not None else -1,),
        ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item = json.loads(row["payload_json"])
        if isinstance(item, dict):
            values = grouped.setdefault(str(row["observed_at"]), [])
            if item.get("securityCode"):
                values.append(item)
    all_dates = sorted(grouped)
    if days is not None:
        all_dates = all_dates[-days:]
    matrix_dates = all_dates if matrix_days is None else all_dates[-matrix_days:]
    total_by_industry: dict[str, int] = {}
    for day in all_dates[-90:]:
        for item in grouped[day]:
            industry = str(item.get("industry") or "待申万映射")
            total_by_industry[industry] = total_by_industry.get(industry, 0) + 1
    named = sorted(total_by_industry, key=lambda key: (-total_by_industry[key], key))[:12]
    matrix = []
    for industry in named:
        matrix.append(
            {
                "industry": industry,
                "counts": [
                    sum(
                        str(item.get("industry") or "待申万映射") == industry
                        for item in grouped.get(day, [])
                    )
                    for day in matrix_dates
                ],
                "historyTotal": total_by_industry[industry],
            }
        )
    return {
        "dates": matrix_dates,
        "counts": [len(grouped[day]) for day in matrix_dates],
        "industries": matrix,
        "rows": [dict(item, observedAt=day) for day in all_dates for item in grouped[day]],
    }


def write_history_points(
    run_id: str,
    dataset: str,
    points: list[tuple[str, str, dict[str, Any]]],
    *,
    source: str,
    db: sqlite3.Connection | None = None,
) -> None:
    """Upsert a validated historical series in a single SQLite transaction."""
    now = _now()
    with nullcontext(db) if db is not None else connection() as db:
        for observed_at, entity_code, payload in points:
            db.execute(
                """INSERT INTO research_a_share_history
                (dataset,observed_at,entity_code,payload_json,source,fetched_at,refresh_run_id)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset,observed_at,entity_code)
                DO UPDATE SET payload_json=excluded.payload_json,source=excluded.source,
                fetched_at=excluded.fetched_at,refresh_run_id=excluded.refresh_run_id""",
                (
                    dataset,
                    observed_at,
                    entity_code,
                    json.dumps(_jsonable(payload), ensure_ascii=False, separators=(",", ":")),
                    source,
                    now,
                    run_id,
                ),
            )


def publish_refresh(
    run_id: str,
    dashboard: AShareDashboardResponse,
    *,
    pool: dict[str, Any],
    datasets: list[tuple[str, Any, str]],
    histories: list[tuple[str, list[tuple[str, str, dict[str, Any]]], str]],
    trade_date: str | None,
    status: str,
    message: str | None = None,
) -> None:
    """Publish one collection consistently; readers see either the old or new run."""
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        write_dashboard(run_id, dashboard, db=db)
        write_stock_pool(run_id, pool, db=db)
        for dataset, payload, source in datasets:
            write_dataset(
                dataset, payload, source=source, run_id=run_id, observed_at=trade_date, db=db
            )
        for dataset, points, source in histories:
            if dataset == "hot_stock" and trade_date:
                db.execute(
                    "DELETE FROM research_a_share_history "
                    "WHERE dataset='hot_stock' AND observed_at=?",
                    (trade_date,),
                )
                points = [(trade_date, "__day__", {}), *points]
            write_history_points(run_id, dataset, points, source=source, db=db)
        db.execute(
            (
                "UPDATE research_a_share_refresh_runs SET finished_at=?,target_trade_date=?,s"
                "tatus=?,message=? WHERE run_id=?"
            ),
            (_now(), trade_date, status, message, run_id),
        )


def read_tracked_codes() -> list[str]:
    """Collect shared and personal symbols, without publishing account ownership."""
    with connection() as db:
        codes, _ = read_pool_configuration(db)
        rows = db.execute("SELECT items_json FROM user_research_watchlists").fetchall()
    return list(
        dict.fromkeys(
            [*codes, *(item["code"] for row in rows for item in json.loads(row["items_json"]))]
        )
    )


def read_stored_stock_histories(codes: list[str]) -> dict[str, list[AShareIndexHistoryPoint]]:
    if not codes:
        return {}
    placeholders = ",".join("?" for _ in codes)
    with connection() as db:
        rows = db.execute(
            f"""SELECT entity_code,observed_at,payload_json FROM (
                SELECT entity_code,observed_at,payload_json,
                ROW_NUMBER() OVER(PARTITION BY entity_code ORDER BY observed_at DESC) AS rank
                FROM research_a_share_history WHERE dataset='stock'
                AND entity_code IN ({placeholders})) WHERE rank<=300
                ORDER BY entity_code,observed_at""",
            codes,
        ).fetchall()
    result: dict[str, list[AShareIndexHistoryPoint]] = {}
    for row in rows:
        payload = json.loads(row["payload_json"])
        result.setdefault(row["entity_code"], []).append(
            AShareIndexHistoryPoint(
                observed_at=row["observed_at"],
                close=payload["close"],
                turnover_yuan=payload.get("turnoverYuan"),
            )
        )
    return result


def read_stock_detail(code: str) -> dict[str, Any]:
    payload = read_stock_pool([code])
    stock = payload["focusStocks"][0]
    with connection() as db:
        rows = db.execute(
            (
                "SELECT observed_at,payload_json FROM research_a_share_history WHERE dataset="
                "'stock' AND entity_code=? ORDER BY observed_at DESC LIMIT 300"
            ),
            (code,),
        ).fetchall()
    return {
        "stock": stock,
        "history": [
            {"observedAt": row["observed_at"], **json.loads(row["payload_json"])}
            for row in reversed(rows)
        ],
    }


def read_index_history(code: str) -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute(
            (
                "SELECT observed_at,payload_json FROM research_a_share_history WHERE dataset="
                "'index' AND entity_code=? ORDER BY observed_at DESC LIMIT 2000"
            ),
            (code,),
        ).fetchall()
    return [
        {**json.loads(row["payload_json"]), "observedAt": row["observed_at"]}
        for row in reversed(rows)
    ]
