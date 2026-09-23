"""Background serving projection. HTTP reads never reconstruct financial history."""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from app import monitor_health
from app.database import connection
from app.schemas import StrategyAccountSnapshotResponse, StrategyPnlResponse

logger = logging.getLogger(__name__)


def request_projection(instance_id, account_id, kind):
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        if not db.execute("SELECT 1 FROM strategy_instances WHERE id=?", (instance_id,)).fetchone():
            raise HTTPException(404, "Strategy instance not found")
        db.execute(
            "INSERT INTO strategy_management_projection "
            "(strategy_instance_id,account_id,kind,requested_at) VALUES (?,?,?,?) "
            "ON CONFLICT(strategy_instance_id,account_id,kind) DO UPDATE "
            "SET requested_at=excluded.requested_at "
            "WHERE requested_at<?",
            (
                instance_id,
                account_id or "",
                kind,
                now,
                (datetime.now(UTC) - timedelta(seconds=30)).isoformat(),
            ),
        )


def read_projection(instance_id, *, account_id=None, kind="pnl"):
    request_projection(instance_id, account_id, kind)
    with connection() as db:
        row = db.execute(
            "SELECT * FROM strategy_management_projection "
            "WHERE strategy_instance_id=? AND account_id=? AND kind=?",
            (instance_id, account_id or "", kind),
        ).fetchone()
    if not row["payload_json"]:
        raise HTTPException(503, "后台正在准备策略数据，请稍后重试", headers={"Retry-After": "2"})
    payload = json.loads(row["payload_json"])
    stale = (
        bool(row["error_code"])
        or (datetime.now(UTC) - datetime.fromisoformat(row["updated_at"])).total_seconds() > 90
    )
    if stale:
        payload["dataQualityState"] = "stale"
        if kind == "pnl":
            payload["issues"] = list(
                set(payload.get("issues", [])) | {"management_projection_stale"}
            )
        else:
            payload["isStale"] = True
    model = StrategyPnlResponse if kind == "pnl" else StrategyAccountSnapshotResponse
    return model.model_validate(payload)


def prepare_keys():
    with connection() as db:
        rows = db.execute(
            "SELECT DISTINCT s.id,b.account_id FROM strategy_instances s "
            "JOIN strategy_account_bindings b ON b.strategy_instance_id=s.id "
            "WHERE b.status='active' AND b.role!='local_test'"
        ).fetchall()
    for row in rows:
        request_projection(row["id"], None, "pnl")
        request_projection(row["id"], None, "summary")
        request_projection(row["id"], row["account_id"], "summary")


def refresh_one(*, force=False):
    from app.catalog import get_strategy_account_snapshot, get_strategy_pnl

    now = datetime.now(UTC)
    with connection() as db:
        row = db.execute(
            "SELECT * FROM strategy_management_projection "
            "WHERE (updated_at IS NULL OR updated_at<?) "
            "AND (attempted_at IS NULL OR attempted_at<?) "
            "AND (kind!='detail' OR requested_at>?) "
            "ORDER BY payload_json IS NOT NULL,updated_at LIMIT 1",
            (
                (now if force else now - timedelta(seconds=30)).isoformat(),
                (now - timedelta(seconds=5)).isoformat(),
                (now - timedelta(minutes=10)).isoformat(),
            ),
        ).fetchone()
        if not row:
            return False
        key = (row["strategy_instance_id"], row["account_id"], row["kind"])
        db.execute(
            "UPDATE strategy_management_projection SET attempted_at=? "
            "WHERE strategy_instance_id=? AND account_id=? AND kind=?",
            (now.isoformat(), *key),
        )
    try:
        model = (
            get_strategy_pnl(key[0])
            if key[2] == "pnl"
            else get_strategy_account_snapshot(
                key[0], account_id=key[1] or None, include_details=key[2] == "detail"
            )
        )
        payload = model.model_dump_json(by_alias=True)
        with connection() as db:
            db.execute(
                "UPDATE strategy_management_projection "
                "SET payload_json=?,updated_at=?,error_code=NULL "
                "WHERE strategy_instance_id=? AND account_id=? AND kind=?",
                (payload, datetime.now(UTC).isoformat(), *key),
            )
    except Exception as exc:
        with connection() as db:
            db.execute(
                "UPDATE strategy_management_projection SET error_code=? "
                "WHERE strategy_instance_id=? AND account_id=? AND kind=?",
                (type(exc).__name__, *key),
            )
        logger.warning("Management projection failed for %s: %s", key, type(exc).__name__)
    return True


async def run_management_projection_monitor():
    await asyncio.to_thread(prepare_keys)
    while True:
        monitor_health.begin("management_projection")
        try:
            worked = await asyncio.to_thread(refresh_one)
            with connection() as db:
                failed = db.execute(
                    "SELECT 1 FROM strategy_management_projection "
                    "WHERE error_code IS NOT NULL LIMIT 1"
                ).fetchone()
            monitor_health.finish("management_projection", "projection_failed" if failed else None)
        except Exception as exc:
            worked = False
            monitor_health.finish("management_projection", type(exc).__name__)
        await asyncio.sleep(0.05 if worked else 1)
