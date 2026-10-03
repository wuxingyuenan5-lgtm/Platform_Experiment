"""Reconcile group lifecycle from venue facts, without creating execution fills."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.database import connection
from app.database_connection import read_only_connection


def _legs(db, batch_id):
    return {
        r["role"]: r
        for r in db.execute("SELECT * FROM execution_batch_legs WHERE batch_id=?", (batch_id,))
    }


def assert_close_positions(plan) -> Decimal:
    """A stale ticket must never release the first (Bybit) leg."""
    from app.cross_spread import get_bybit_account_id, get_mt5_account_id
    from app.cross_spread_live_read_client import CrossSpreadLiveReadError, list_positions

    with connection() as db:
        legs = _legs(db, plan.open_batch_id)
        if set(legs) != {"bybit_leg", "mt5_leg"}:
            raise HTTPException(409, "Position group has no complete opening leg identity")
        bybit, mt5 = legs["bybit_leg"], legs["mt5_leg"]
        if (bybit["account_id"], mt5["account_id"]) != (
            get_bybit_account_id(),
            get_mt5_account_id(),
        ):
            raise HTTPException(409, "Position group account bindings have changed")
        rows = db.execute(
            "SELECT p.quantity_oz,p.direction FROM cross_spread_exit_plans p "
            "JOIN execution_batch_legs l ON l.batch_id=p.open_batch_id AND l.role='bybit_leg' "
            "WHERE p.status!='closed' AND l.account_id=? AND l.instrument_id=?",
            (bybit["account_id"], bybit["instrument_id"]),
        ).fetchall()
    try:
        mt5_positions = list_positions(mt5["account_id"])
        bybit_positions = list_positions(bybit["account_id"])
    except CrossSpreadLiveReadError as exc:
        raise HTTPException(503, str(exc)) from exc
    target = [
        p
        for p in mt5_positions
        if p.account_id == mt5["account_id"]
        and p.instrument_id == mt5["instrument_id"]
        and p.external_position_id == plan.mt5_position_id
    ]
    lot = plan.quantity_oz * Decimal(mt5["quantity"]) / Decimal(bybit["quantity"])
    expected_mt5 = -lot if plan.direction == "LONG_SPREAD" else lot
    expected_bybit = sum(
        (Decimal(r["quantity_oz"]) * (1 if r["direction"] == "LONG_SPREAD" else -1) for r in rows),
        Decimal(0),
    )
    actual = [
        p
        for p in bybit_positions
        if p.account_id == bybit["account_id"]
        and p.instrument_id == bybit["instrument_id"]
        and p.net_quantity != 0
    ]
    if (
        len(target) != 1
        or target[0].net_quantity != expected_mt5
        or len(actual) > 1
        or sum((p.net_quantity for p in actual), Decimal(0)) != expected_bybit
    ):
        raise HTTPException(
            409, "Venue positions differ from the position group; reconcile before closing"
        )
    return expected_bybit


def reconcile_external_cross_spread_closes() -> list[str]:
    """Close only an entirely flat scope with exact native close evidence.

    Bybit is netted: evidence belongs to the whole account/instrument group.
    It must not be allocated into invented per-plan fills or PnL.
    """
    from app.venue_reconciliation_repository import ensure_schema

    with read_only_connection() as db:
        if db.execute(
            "SELECT 1 FROM cross_spread_exit_plans WHERE status!='closed' LIMIT 1"
        ).fetchone() is None:
            return []
    ensure_schema()
    now = datetime.now(UTC)
    closed = []
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        plans = db.execute(
            "SELECT * FROM cross_spread_exit_plans WHERE status!='closed'"
        ).fetchall()
        groups = {}
        for plan in plans:
            legs = _legs(db, plan["open_batch_id"])
            if set(legs) != {"bybit_leg", "mt5_leg"}:
                continue
            b, m = legs["bybit_leg"], legs["mt5_leg"]
            key = (b["account_id"], b["instrument_id"], m["account_id"], m["instrument_id"])
            groups.setdefault(key, []).append((plan, b, m))
        for (ba, bi, ma, mi), group in groups.items():
            if sum(key[:2] == (ba, bi) for key in groups) != 1:
                continue
            if any(p["status"] not in {"active", "manual_intervention"} for p, _, _ in group):
                continue
            # Unknown or live commands/orders must retain their existing recovery path.
            if db.execute(
                "SELECT 1 FROM trade_commands c LEFT JOIN orders o ON o.command_id=c.id "
                "WHERE ((c.account_id=? AND c.instrument_id=?) "
                "OR (c.account_id=? AND c.instrument_id=?)) "
                "AND NOT (c.status='result_unknown' AND o.status='rejected' AND EXISTS ("
                "SELECT 1 FROM reconciliation_differences d WHERE d.entity_type='order' "
                "AND d.local_reference=o.id AND d.difference_type='missing_external' "
                "AND d.status IN ('accepted','resolved'))) "
                "AND (c.status NOT IN ('accepted','rejected','completed','filled','canceled') "
                "OR (c.status='accepted' AND o.id IS NULL) "
                "OR (o.id IS NOT NULL AND o.status NOT IN ('filled','canceled','rejected'))) "
                "LIMIT 1",
                (ba, bi, ma, mi),
            ).fetchone():
                continue
            if db.execute(
                "SELECT 1 FROM execution_batches b JOIN execution_batch_legs l ON l.batch_id=b.id "
                "WHERE ((l.account_id=? AND l.instrument_id=?) "
                "OR (l.account_id=? AND l.instrument_id=?)) "
                "AND b.status NOT IN ('hedged','failed','canceled') LIMIT 1",
                (ba, bi, ma, mi),
            ).fetchone():
                continue
            snapshots = []
            for account, instrument, source in ((ba, bi, "bybit_live"), (ma, mi, "mt5_live")):
                sync = db.execute(
                    "SELECT status FROM account_sync_status WHERE account_id=?", (account,)
                ).fetchone()
                if sync is None or sync["status"] != "ready":
                    break
                row = db.execute(
                    "SELECT * FROM account_venue_snapshots WHERE account_id=?", (account,)
                ).fetchone()
                if (
                    row is None
                    or row["source"] != source
                    or row["data_quality_state"] != "complete"
                ):
                    break
                snap = json.loads(row["payload_json"])
                if not _fresh(snap.get("asOf"), now, 120) or not _fresh(
                    snap.get("historyObservedAt"), now, 600
                ):
                    break
                if any(
                    p.get("instrumentId") == instrument and Decimal(str(p["netQuantity"])) != 0
                    for p in snap.get("positions", [])
                ):
                    break
                if any(
                    o.get("instrumentId") == instrument
                    and o.get("status") not in {"filled", "canceled", "rejected"}
                    for o in snap.get("orders", [])
                ):
                    break
                snapshots.append(snap)
            if len(snapshots) != 2 or len({p["direction"] for p, _, _ in group}) != 1:
                continue
            bs, ms = snapshots
            side = "sell" if group[0][0]["direction"] == "LONG_SPREAD" else "buy"
            earliest = min(_stamp(p["created_at"]) for p, _, _ in group)
            orders = {o["externalOrderId"]: o for o in bs["orders"] if o.get("instrumentId") == bi}
            fills = {
                f["externalFillId"]: f
                for f in bs["fills"]
                if f.get("instrumentId") == bi and _stamp(f["occurredAt"]) > earliest
            }
            if not fills or any(
                f["side"] != side or not orders.get(f["externalOrderId"], {}).get("reduceOnly")
                for f in fills.values()
            ):
                continue
            if sum((Decimal(f["quantity"]) for f in fills.values()), Decimal(0)) != sum(
                (Decimal(p["quantity_oz"]) for p, _, _ in group), Decimal(0)
            ):
                continue
            mt5_evidence = {}
            for p, _, m in group:
                deals = {
                    f["externalFillId"]: f
                    for f in ms["fills"]
                    if f.get("instrumentId") == mi
                    and str(f.get("positionId")) == p["mt5_position_id"]
                    and f.get("entryType") in (1, 3)
                    and f["side"] != side
                }
                if sum((Decimal(f["quantity"]) for f in deals.values()), Decimal(0)) != Decimal(
                    m["quantity"]
                ):
                    break
                mt5_evidence[p["id"]] = list(deals.values())
            if len(mt5_evidence) != len(group):
                continue
            evidence = {
                "scope": [ba, bi, ma, mi],
                "planIds": [p["id"] for p, _, _ in group],
                "plansBefore": [dict(p) for p, _, _ in group],
                "snapshotAsOf": [bs["asOf"], ms["asOf"]],
                "bybitFills": list(fills.values()),
                "bybitOrders": list(orders.values()),
                "mt5Closes": mt5_evidence,
                "allocation": "aggregate_only_no_per_plan_pnl",
            }
            stamp = now.isoformat()
            for p, _, _ in group:
                db.execute(
                    "UPDATE cross_spread_exit_plans SET status='closed',quantity_oz='0',"
                    "closed_at=?,updated_at=? WHERE id=?",
                    (stamp, stamp, p["id"]),
                )
                db.execute(
                    "INSERT INTO audit_events(id,event_type,subject_type,subject_id,"
                    "details_json,created_at) VALUES "
                    "(?,'cross_spread_external_close_reconciled','cross_spread_exit_plan',?,?,?)",
                    (str(uuid4()), p["id"], json.dumps(evidence, ensure_ascii=False), stamp),
                )
                closed.append(p["id"])
    return closed


def _stamp(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _fresh(value, now, seconds):
    if not value:
        return False
    return -5 <= (now - _stamp(value)).total_seconds() <= seconds
