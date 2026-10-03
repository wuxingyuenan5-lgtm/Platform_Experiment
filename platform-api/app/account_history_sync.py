"""Historical evidence refresh must not delay or invalidate current observations."""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Lock

from app import monitor_health
from app.account_read_jobs import record_job
from app.database import connection
from app.live_venue_snapshot_sync import (
    _persist_fills,
    _persist_orders,
    _persist_pnl,
    _persist_venue_event,
    _persist_venue_snapshot,
    _sync_account_finance,
    _validate_snapshot,
    discover_live_accounts,
)
from app.venue_identity_repository import load_order_identities
from app.venue_reconciliation import runtime_get

logger = logging.getLogger(__name__)
_lock = Lock()
HISTORY_INTERVAL_SECONDS = 300


def _stamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("History evidence requires timezone-aware timestamps")
    return result


def _merge_history(previous: dict, incoming: dict, *, incremental: bool) -> dict:
    """Only contiguous, complete windows can extend persisted coverage."""
    result = dict(previous)
    start, end = incoming.get("historyStart"), incoming.get("historyEnd")
    if end and previous.get("historyEnd") and _stamp(end) < _stamp(previous["historyEnd"]):
        return result
    contiguous = bool(
        incremental
        and start
        and end
        and previous.get("historyEnd")
        and previous.get("economicEventsQuality") == "complete"
        and incoming.get("economicEventsQuality") == "complete"
        and _stamp(start) <= _stamp(previous["historyEnd"])
    )
    window_seconds = previous.get("historyWindowSeconds", 7 * 86400)
    if not incremental and start and end:
        window_seconds = (_stamp(end) - _stamp(start)).total_seconds()
    floor = None
    if contiguous and end is not None:
        floor = max(
            _stamp(previous["historyStart"]), _stamp(end) - timedelta(seconds=window_seconds)
        )
    for key, identity in (("fills", "externalFillId"), ("economicEvents", "externalEventId")):
        if floor is not None:
            rows = {(row.get("source"), row[identity]): row for row in previous.get(key, [])}
            rows.update({(row.get("source"), row[identity]): row for row in incoming.get(key, [])})
            result[key] = [row for row in rows.values() if _stamp(row["occurredAt"]) >= floor]
        else:
            result[key] = incoming.get(key, [])
    # Bybit refreshes the full order-status window, including older orders that
    # closed recently. Never infer a cancellation from absence in a time slice.
    result["orders"] = incoming["orders"]
    result["historyStart"] = floor.isoformat() if floor is not None else start
    result["historyEnd"] = end
    result["economicEventsQuality"] = incoming.get("economicEventsQuality", "unavailable")
    result["historyAuditAt"] = (
        previous.get("historyAuditAt") if incremental else incoming.get("asOf") or end
    )
    result["historyWindowSeconds"] = window_seconds
    result["historyObservedAt"] = incoming.get("asOf") or end
    return result


def sync_account_history(account_id: str) -> None:
    with connection() as db:
        prior = db.execute(
            "SELECT payload_json FROM account_venue_snapshots WHERE account_id=?", (account_id,)
        ).fetchone()
    if prior is None:
        return  # Let the first current observation establish the account identity.
    previous = json.loads(prior[0])
    now = datetime.now(UTC)
    is_mt5 = previous.get("venue") == "mt5"
    progress = previous.get("historyObservedAt") if is_mt5 else previous.get("historyEnd")
    incremental = bool(
        previous.get("economicEventsQuality") == "complete"
        and progress
        and previous.get("historyEnd")
        and previous.get("historyStart")
        and previous.get("historyAuditAt")
        and now - _stamp(previous["historyAuditAt"]) < timedelta(days=1)
        and now - _stamp(previous["historyEnd"]) < timedelta(days=7) - timedelta(minutes=10)
    )
    params = {"accountId": account_id}
    if incremental:
        # MT5's SDK query window is padded by one day on both sides because
        # broker-local epochs are retained unchanged. Its future historyEnd is
        # not a UTC progress watermark: use the actual read time with the same
        # padding, rather than treating tomorrow as already synchronized.
        params["historyStart"] = (
            _stamp(progress) - timedelta(minutes=10, days=1 if is_mt5 else 0)
        ).isoformat()
    record_job(account_id, "history", "syncing")
    try:
        if not incremental:
            backfill_missing_native_fills(account_id)
        response = runtime_get("/venue/account-snapshot", params=params)
        response.raise_for_status()
        snapshot = response.json()
        _validate_snapshot(account_id, snapshot)
        with connection() as db:
            _persist_orders(db, account_id, snapshot["orders"])
            _, realized, fees = _persist_fills(db, account_id, snapshot["fills"])
            _persist_pnl(
                db,
                account_id,
                unrealized_by_instrument={},
                realized_by_instrument=realized,
                fees_by_instrument=fees,
            )
            for fill in snapshot["fills"]:
                _persist_venue_event(db, account_id, "trade_fill", fill)
            for event in snapshot.get("economicEvents", []):
                _persist_venue_event(db, account_id, str(event["eventType"]), event)
            current = db.execute(
                "SELECT payload_json FROM account_venue_snapshots WHERE account_id=?", (account_id,)
            ).fetchone()
            # The current observation owns balances, risk and positions. A slow
            # history response must never replace a newer current observation.
            if current:
                merged = _merge_history(json.loads(current[0]), snapshot, incremental=incremental)
                _persist_venue_snapshot(db, account_id, merged)
        complete = snapshot.get("economicEventsQuality") == "complete"
        record_job(
            account_id,
            "history",
            "ready" if complete else "failed",
            None if complete else "economic_events_unavailable",
        )
    except Exception as exc:
        record_job(account_id, "history", "failed", type(exc).__name__)
        logger.warning("Account history sync failed: %s", type(exc).__name__)
        return
    _sync_account_finance(account_id)


def backfill_missing_native_fills(account_id: str) -> int:
    """Daily audit repairs an evidenced fill gap beyond the rolling history window.

    Append original venue receipts only. Orders, positions and trading commands
    are never changed by this repair. One earliest missing window is read per audit.
    """
    with connection() as db:
        identities = load_order_identities(db)
        orders = [
            dict(row)
            for row in db.execute(
                "SELECT * FROM orders WHERE account_id=? AND status='filled' "
                "AND external_order_id IS NOT NULL ORDER BY julianday(created_at)",
                (account_id,),
            )
            if identities.canonical[row["id"]] == row["id"]
            and identities.rows[row["id"]]["strategy_instance_id"]
        ]
        quantities = {}
        for row in db.execute(
            "SELECT payload_json FROM venue_account_events "
            "WHERE account_id=? AND event_type='trade_fill'",
            (account_id,),
        ):
            fill = json.loads(row[0])
            order_id = identities.resolve(account_id, fill)
            quantities[order_id] = quantities.get(order_id, Decimal(0)) + Decimal(fill["quantity"])
        missing = next(
            (
                order
                for order in orders
                if quantities.get(order["id"], Decimal(0)) < Decimal(order["quantity"])
            ),
            None,
        )
    if missing is None:
        return 0
    start = (
        _stamp(missing["created_at"])
        .astimezone(UTC)
        .replace(hour=0, minute=0, second=0, microsecond=0)
    )
    params = {
        "accountId": account_id,
        "symbol": missing["symbol"],
        "startTime": start.isoformat(),
        "endTime": (start + timedelta(days=2)).isoformat(),
        "limit": 100,
    }
    cursors, count = set(), 0
    while True:
        response = runtime_get("/venue/fill-history", params=params)
        response.raise_for_status()
        page = response.json()
        if page.get("accountId") != account_id:
            raise ValueError("History fill account identity mismatch")
        with connection() as db:
            for fill in page.get("items", []):
                existed = db.execute(
                    "SELECT 1 FROM venue_account_events WHERE account_id=? AND source=? "
                    "AND event_type='trade_fill' AND external_id=?",
                    (account_id, fill["source"], fill["externalFillId"]),
                ).fetchone()
                _persist_venue_event(db, account_id, "trade_fill", fill)
                count += not bool(existed)
        cursor = page.get("nextCursor")
        if not cursor:
            return count
        if cursor in cursors:
            raise ValueError("History fill cursor did not advance")
        cursors.add(cursor)
        params["cursor"] = cursor


def sync_due_histories() -> None:
    if not _lock.acquire(blocking=False):
        return
    try:
        for account_id in discover_live_accounts():
            with connection() as db:
                row = db.execute(
                    "SELECT last_attempt_at,status FROM account_read_jobs "
                    "WHERE account_id=? AND job='history'",
                    (account_id,),
                ).fetchone()
            delay = 30 if row and row["status"] == "failed" else HISTORY_INTERVAL_SECONDS
            if row and datetime.now(UTC) - datetime.fromisoformat(
                row["last_attempt_at"]
            ) < timedelta(seconds=delay):
                continue
            try:
                sync_account_history(account_id)
            except Exception as exc:
                record_job(account_id, "history", "failed", type(exc).__name__)
                logger.warning("History preparation failed: %s", type(exc).__name__)
    finally:
        _lock.release()


def sync_and_check():
    sync_due_histories()
    with connection() as db:
        return bool(db.execute(
            "SELECT 1 FROM account_read_jobs j JOIN accounts a ON a.id=j.account_id "
            "WHERE j.job='history' AND j.status='failed' AND a.status='active' LIMIT 1"
        ).fetchone())


async def run_history_sync_monitor() -> None:
    while True:
        monitor_health.begin("account_history")
        try:
            failed = await asyncio.to_thread(sync_and_check)
            monitor_health.finish("account_history", "history_sync_failed" if failed else None)
        except Exception as exc:
            monitor_health.finish("account_history", type(exc).__name__)
            logger.warning("History monitor failed: %s", type(exc).__name__)
        await asyncio.sleep(30)
