from __future__ import annotations

import json
import sqlite3
from contextlib import nullcontext
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.database import connection
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
            "sage FROM research_a_share_refresh_runs ORDER BY started_at DESC LIMIT 1"
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
                "marketBreadthPct": round(
                    100 * (breadth.up - breadth.down) / (breadth.up + breadth.down + breadth.flat),
                    2,
                )
                if breadth.up + breadth.down + breadth.flat
                else None,
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
            """SELECT observed_at, payload_json FROM (
                SELECT observed_at, payload_json
                FROM research_a_share_history
                WHERE dataset='market'
                ORDER BY observed_at DESC
                LIMIT 2000
            ) ORDER BY observed_at"""
        ).fetchall()
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
            "marketHistory": [
                {"observedAt": row["observed_at"], **json.loads(row["payload_json"])}
                for row in history_rows
            ],
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
                "ready",
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


def read_hot_stock_history(*, days: int | None = 90, matrix_days: int | None = 10) -> dict[str, Any]:
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
