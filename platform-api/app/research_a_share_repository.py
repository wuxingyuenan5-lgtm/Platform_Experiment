from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any


# Initial platform-owned theme baskets migrated from the approved historical
# stock-pool definition.  They are research configuration, not market facts.
DEFAULT_STOCK_POOL_BASKETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("ai_semiconductor", "AI算力/半导体", ("00981", "01347", "688012", "688041", "688256", "603986", "688008", "600584", "002156", "300373", "688234", "300666", "688037", "300604", "688372", "688820", "688825", "688521", "688141", "688048", "300661", "300395", "603650", "603893", "300857", "688702", "688146", "600330")),
    ("ai_pcb_optical", "AI PCB/光通信", ("300476", "002916", "002463", "600183", "688183", "002384", "01888", "300903", "301377", "688300", "301217", "300308", "300502", "000100", "000725", "000063", "002475", "000636", "003031", "600353", "603256", "300394", "002281", "300620", "688313", "688143", "300548", "601869", "600487", "688498", "688502", "002484", "300408")),
    ("robotics_datacenter", "机器人/自动化/数据中心", ("601689", "002050", "688017", "09880", "09660", "601100", "688777", "002851", "002008", "301200", "301396", "02513", "688025", "603308", "301018", "002837", "688630", "300757", "300776", "300870", "688808", "600875")),
    ("resources_cycle", "资源品/黄金/周期", ("601899", "600988", "000426", "603993", "601168", "000807", "600549", "000657", "600301", "002428", "000688", "001203", "603799", "600938", "601225", "600188", "600309", "002648", "600346", "600989", "600141", "000893", "600160", "605376", "600176", "002353")),
    ("innovative_drug", "创新药/CXO/AI医疗", ("600276", "06160", "01801", "09926", "06990", "603259", "02269", "02268", "02228")),
    ("new_energy", "新能源", ("300750", "300274", "600438", "600732", "605117", "002709", "301358", "688778", "300450", "300776", "002487", "301511", "688676", "688585")),
    ("consumer_internet", "消费/互联网/出海", ("600519", "000333", "600690", "00700", "09988", "01810", "02020", "09992", "605499", "300866", "689009", "02015", "01364", "301498", "002832", "688775", "300209")),
    ("core_assets", "金融/红利/核心资产", ("601398", "601318", "601336", "601628", "600030", "300059", "600941", "600900", "600031", "000338", "600066", "600233", "601058", "002714")),
)

from app.database import connection
from app.research_data_schemas import AShareDashboardResponse, ResearchModuleResult


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


def ensure_schema() -> None:
    """Compatibility guard for CLI/tests that initialize the DB without app lifespan."""
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS research_a_share_refresh_runs (
                run_id TEXT PRIMARY KEY, target_trade_date TEXT, started_at TEXT NOT NULL,
                finished_at TEXT, status TEXT NOT NULL, error_code TEXT, message TEXT
            );
            CREATE TABLE IF NOT EXISTS research_a_share_dataset_snapshots (
                dataset TEXT PRIMARY KEY, observed_at TEXT, fetched_at TEXT NOT NULL,
                status TEXT NOT NULL, source TEXT NOT NULL, payload_json TEXT,
                error_code TEXT, message TEXT, refresh_run_id TEXT
            );
            CREATE TABLE IF NOT EXISTS research_a_share_history (
                dataset TEXT NOT NULL, observed_at TEXT NOT NULL, entity_code TEXT NOT NULL,
                payload_json TEXT NOT NULL, source TEXT NOT NULL, fetched_at TEXT NOT NULL,
                refresh_run_id TEXT, PRIMARY KEY(dataset, observed_at, entity_code)
            );
            CREATE INDEX IF NOT EXISTS idx_research_a_share_history_lookup
              ON research_a_share_history(dataset, observed_at DESC);
            """
        )


def start_refresh(run_id: str, target_trade_date: str | None) -> None:
    ensure_schema()
    with connection() as db:
        db.execute(
            "INSERT INTO research_a_share_refresh_runs(run_id,target_trade_date,started_at,status) VALUES (?,?,?,?)",
            (run_id, target_trade_date, _now(), "running"),
        )


def finish_refresh(run_id: str, status: str, *, error_code: str | None = None, message: str | None = None) -> None:
    with connection() as db:
        db.execute(
            "UPDATE research_a_share_refresh_runs SET finished_at=?,status=?,error_code=?,message=? WHERE run_id=?",
            (_now(), status, error_code, message, run_id),
        )


def read_refresh_status() -> dict[str, Any] | None:
    ensure_schema()
    with connection() as db:
        row = db.execute(
            "SELECT run_id,target_trade_date,started_at,finished_at,status,error_code,message FROM research_a_share_refresh_runs ORDER BY started_at DESC LIMIT 1"
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


def write_dashboard(run_id: str, dashboard: AShareDashboardResponse) -> None:
    """Atomically replace latest datasets and append normalized history rows."""
    ensure_schema()
    fetched = dashboard.generated_at.isoformat()
    modules: dict[str, ResearchModuleResult] = {
        "market_detail": dashboard.market_detail,
        "breadth": dashboard.breadth,
        "shenwan": dashboard.shenwan,
        "emotion": dashboard.emotion,
    }
    if dashboard.crowding is not None:
        modules["crowding"] = dashboard.crowding
    with connection() as db:
        for dataset, module in modules.items():
            meta = module.meta
            existing = db.execute(
                "SELECT status FROM research_a_share_dataset_snapshots WHERE dataset=?",
                (dataset,),
            ).fetchone()
            # A failed collection must not erase the last meaningful snapshot.
            # The refresh run records the failure while the API continues serving LKG data.
            if existing is not None and str(existing["status"]) == "ready" and meta.status in {"error", "no_data"}:
                continue
            payload = module.data
            payload_json = json.dumps(_jsonable(payload), ensure_ascii=False, separators=(",", ":")) if payload is not None else None
            observed = meta.source_timestamp.isoformat() if meta.source_timestamp else fetched
            db.execute(
                """INSERT INTO research_a_share_dataset_snapshots
                (dataset,observed_at,fetched_at,status,source,payload_json,error_code,message,refresh_run_id)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(dataset) DO UPDATE SET observed_at=excluded.observed_at,
                fetched_at=excluded.fetched_at,status=excluded.status,source=excluded.source,
                payload_json=excluded.payload_json,error_code=excluded.error_code,
                message=excluded.message,refresh_run_id=excluded.refresh_run_id""",
                (dataset, observed, fetched, meta.status, meta.source, payload_json, meta.error_code, meta.message, run_id),
            )
        # Keep index history in a queryable table; this is the long-lived chart source.
        if dashboard.market_detail.data:
            for item in dashboard.market_detail.data:
                history = item.get("history", []) if isinstance(item, dict) else getattr(item, "history", [])
                code = str(item.get("code") if isinstance(item, dict) else item.code)
                for point in history:
                    row = point if isinstance(point, dict) else point.model_dump(mode="json")
                    db.execute(
                        """INSERT INTO research_a_share_history
                        (dataset,observed_at,entity_code,payload_json,source,fetched_at,refresh_run_id)
                        VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset,observed_at,entity_code)
                        DO UPDATE SET payload_json=excluded.payload_json,source=excluded.source,
                        fetched_at=excluded.fetched_at,refresh_run_id=excluded.refresh_run_id""",
                        ("index", row.get("observedAt", row.get("observed_at")), code, json.dumps(row, ensure_ascii=False), dashboard.market_detail.meta.source, fetched, run_id),
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
                "marketBreadthPct": None,
            }
            db.execute(
                """INSERT INTO research_a_share_history
                (dataset,observed_at,entity_code,payload_json,source,fetched_at,refresh_run_id)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset,observed_at,entity_code)
                DO UPDATE SET payload_json=excluded.payload_json,fetched_at=excluded.fetched_at,
                refresh_run_id=excluded.refresh_run_id""",
                ("market", observed, "market", json.dumps(payload, ensure_ascii=False), dashboard.breadth.meta.source, fetched, run_id),
            )


def read_dashboard() -> AShareDashboardResponse | None:
    ensure_schema()
    with connection() as db:
        rows = db.execute("SELECT dataset, fetched_at, payload_json, status, source, error_code, message, observed_at FROM research_a_share_dataset_snapshots").fetchall()
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
                "sourceTimestamp": row["observed_at"],
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
        crowding_payload = json.loads(crowding_row["payload_json"]) if crowding_row["payload_json"] else None
        if isinstance(crowding_payload, dict):
            # The navigator's initial window is a three-month view. Keep the
            # complete history in SQLite and avoid decoding/rendering unused rows.
            for key in ("history", "innovationHistory"):
                if isinstance(crowding_payload.get(key), list):
                    crowding_payload[key] = crowding_payload[key][-90:]
        values["crowding"] = {
            "meta": {
                "source": crowding_row["source"],
                "sourceTimestamp": crowding_row["observed_at"],
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
                LIMIT 90
            ) ORDER BY observed_at"""
        ).fetchall()
    return AShareDashboardResponse.model_validate({
        "generatedAt": max(str(row["fetched_at"]) for row in rows),
        **values,
        "marketHistory": [
            {"observedAt": row["observed_at"], **json.loads(row["payload_json"])}
            for row in history_rows
        ],
    })


def write_stock_pool(run_id: str, payload: dict[str, Any]) -> None:
    ensure_schema()
    now = _now()
    with connection() as db:
        db.execute(
            """INSERT INTO research_a_share_dataset_snapshots
            (dataset,observed_at,fetched_at,status,source,payload_json,refresh_run_id)
            VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset) DO UPDATE SET
            observed_at=excluded.observed_at,fetched_at=excluded.fetched_at,
            status=excluded.status,source=excluded.source,payload_json=excluded.payload_json,
            refresh_run_id=excluded.refresh_run_id""",
            ("stock_pool", now, now, "ready", "platform-research-derived", json.dumps(_jsonable(payload), ensure_ascii=False), run_id),
        )


def _attach_default_stock_pool_baskets(payload: dict[str, Any]) -> dict[str, Any]:
    definitions = payload.get("definitions")
    definitions = dict(definitions) if isinstance(definitions, dict) else {}
    existing = definitions.get("research_baskets")
    if isinstance(existing, list) and any(isinstance(item, dict) and item.get("name") for item in existing):
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


def read_stock_pool() -> dict[str, Any] | None:
    ensure_schema()
    with connection() as db:
        row = db.execute("SELECT payload_json FROM research_a_share_dataset_snapshots WHERE dataset='stock_pool'").fetchone()
    if not row or not row["payload_json"]:
        return None
    payload = json.loads(row["payload_json"])
    return _attach_default_stock_pool_baskets(payload) if isinstance(payload, dict) else None


def write_dataset(dataset: str, payload: Any, *, source: str, run_id: str) -> None:
    ensure_schema()
    now = _now()
    with connection() as db:
        db.execute(
            """INSERT INTO research_a_share_dataset_snapshots
            (dataset,observed_at,fetched_at,status,source,payload_json,refresh_run_id)
            VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset) DO UPDATE SET
            observed_at=excluded.observed_at,fetched_at=excluded.fetched_at,
            status=excluded.status,source=excluded.source,payload_json=excluded.payload_json,
            refresh_run_id=excluded.refresh_run_id""",
            (dataset, now, now, "ready", source, json.dumps(_jsonable(payload), ensure_ascii=False), run_id),
        )


def read_dataset(dataset: str) -> Any:
    ensure_schema()
    with connection() as db:
        row = db.execute("SELECT payload_json FROM research_a_share_dataset_snapshots WHERE dataset=?", (dataset,)).fetchone()
    return json.loads(row["payload_json"]) if row and row["payload_json"] else None


def read_hot_stock_history(*, days: int = 90, matrix_days: int = 10) -> dict[str, Any]:
    """Read the Platform-owned >100bn mother table without reprocessing quotes."""
    ensure_schema()
    with connection() as db:
        rows = db.execute(
            """SELECT observed_at,payload_json FROM research_a_share_history
            WHERE dataset='hot_stock' ORDER BY observed_at ASC"""
        ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item = json.loads(row["payload_json"])
        if isinstance(item, dict):
            grouped.setdefault(str(row["observed_at"]), []).append(item)
    all_dates = sorted(grouped)[-days:]
    matrix_dates = all_dates[-matrix_days:]
    total_by_industry: dict[str, int] = {}
    for values in grouped.values():
        for item in values:
            industry = str(item.get("industry") or "待申万映射")
            total_by_industry[industry] = total_by_industry.get(industry, 0) + 1
    named = sorted(total_by_industry, key=lambda key: (-total_by_industry[key], key))[:12]
    matrix = []
    for industry in named:
        matrix.append({
            "industry": industry,
            "counts": [sum(str(item.get("industry") or "待申万映射") == industry for item in grouped.get(day, [])) for day in matrix_dates],
            "historyTotal": total_by_industry[industry],
        })
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
) -> None:
    """Upsert a validated historical series in a single SQLite transaction."""
    ensure_schema()
    now = _now()
    with connection() as db:
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


def read_stock_pool_focus() -> list[str]:
    ensure_schema()
    with connection() as db:
        row = db.execute("SELECT payload_json FROM research_a_share_dataset_snapshots WHERE dataset='stock_pool_focus'").fetchone()
    if not row or not row["payload_json"]:
        return []
    payload = json.loads(row["payload_json"])
    return [str(code) for code in payload.get("codes", []) if str(code)]


def write_stock_pool_focus(codes: list[str]) -> None:
    ensure_schema()
    now = _now()
    with connection() as db:
        db.execute(
            """INSERT INTO research_a_share_dataset_snapshots
            (dataset,observed_at,fetched_at,status,source,payload_json)
            VALUES (?,?,?,?,?,?) ON CONFLICT(dataset) DO UPDATE SET
            observed_at=excluded.observed_at,fetched_at=excluded.fetched_at,
            status=excluded.status,payload_json=excluded.payload_json""",
            ("stock_pool_focus", now, now, "ready", "platform-research-user-config", json.dumps({"codes": codes})),
        )


def update_stock_pool_membership(*, add_codes: list[str] | None = None, remove_code: str | None = None) -> int:
    payload = read_stock_pool() or {"summary": {}, "stocks": [], "indices": [], "heatmap": [], "leaders": {}, "definitions": {}}
    rows = list(payload.get("stocks") or [])
    if remove_code:
        rows = [row for row in rows if str(row.get("instrument_id") or row.get("code")) != remove_code]
    for code in add_codes or []:
        if not any(str(row.get("instrument_id") or row.get("code")) == code for row in rows):
            rows.append({"instrument_id": code, "code": code, "name": code, "change": None, "amount_yi": None})
    payload["stocks"] = rows
    payload["heatmap"] = rows
    payload.setdefault("summary", {})["tracked_count"] = len(rows)
    now = _now()
    with connection() as db:
        db.execute(
            """INSERT INTO research_a_share_dataset_snapshots
            (dataset,observed_at,fetched_at,status,source,payload_json)
            VALUES (?,?,?,?,?,?) ON CONFLICT(dataset) DO UPDATE SET
            observed_at=excluded.observed_at,fetched_at=excluded.fetched_at,
            status=excluded.status,source=excluded.source,payload_json=excluded.payload_json""",
            ("stock_pool", now, now, "ready", "platform-research-user-config", json.dumps(payload, ensure_ascii=False)),
        )
    return len(rows)
