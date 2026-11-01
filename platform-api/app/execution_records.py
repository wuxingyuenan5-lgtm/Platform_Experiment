"""Durable execution records: one row per open/close batch.

The strategy lines (funding arbitrage and cross-venue spread) already persist
their evidence in `execution_batches`, `execution_batch_legs`, `orders`,
`venue_account_events` and `execution_steps`. This module projects that evidence
into a single durable row so a trade can be listed, filtered and reopened long
after the fact without joining six tables at query time.

Two rules matter:

* Projection is idempotent and fail-open. A projection failure must never block
  or fail a trade; the next sync retries it.
* Projection is a *cache of the durable evidence*, not the evidence itself. The
  detail view always re-reads batches, legs, orders, fills and steps so a late
  fill or fee still shows up.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from app.database import connection

logger = logging.getLogger(__name__)

OPEN_ACTION = "open"
CLOSE_ACTION = "close"
PRIMARY_LEG_ROLES = ("perpetual_leg", "bybit_leg")
TERMINAL_STATUSES = frozenset(
    {"completed", "hedged", "failed", "rejected", "manual_intervention", "canceled"}
)
SNAPSHOT_PHASES = ("pre_submit", "post_submit", "post_fill", "final")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _json_loads(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_list(value: Any) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return None


def _average_price(fills: list[dict[str, Any]]) -> Decimal | None:
    total_quantity = Decimal("0")
    total_notional = Decimal("0")
    for fill in fills:
        quantity = _decimal(fill.get("quantity"))
        price = _decimal(fill.get("price"))
        if quantity is None or price is None or quantity <= 0:
            continue
        total_quantity += quantity
        total_notional += quantity * price
    if total_quantity <= 0:
        return None
    return total_notional / total_quantity


def _fills_for_orders(
    db: Any, order_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    if not order_ids:
        return {}
    placeholders = ",".join("?" for _ in order_ids)
    rows = db.execute(
        f"""
        SELECT f.order_id, f.quantity, f.price, f.occurred_at,
               f.fee, f.fee_currency, f.fee_quality, f.source, f.external_fill_id
        FROM fills f
        WHERE f.order_id IN ({placeholders})
        ORDER BY f.occurred_at, f.id
        """,
        order_ids,
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["order_id"]), []).append(dict(row))
    return grouped


def _parse_ts(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _backfill_fill_fees(db: Any, order_ids: list[str]) -> None:
    """Copy the venue's native fee onto fills confirmed by the runtime.

    Runtime confirmations carry price and quantity only, while the account
    history sync stores the venue receipt (`execFee`) in `venue_account_events`.
    Matching here is by platform order id plus nearest occurrence time, so a
    multi-fill order keeps each receipt on its own row. Only rows without a fee
    are touched, which makes the backfill idempotent and never overwrites a
    native value written by the snapshot sync.
    """

    if not order_ids:
        return
    placeholders = ",".join("?" for _ in order_ids)
    receipts = db.execute(
        f"""
        SELECT platform_order_id, occurred_at, payload_json
        FROM venue_account_events
        WHERE event_type = 'trade_fill'
          AND platform_order_id IN ({placeholders})
        ORDER BY occurred_at
        """,
        order_ids,
    ).fetchall()
    if not receipts:
        return
    by_order: dict[str, list[tuple[datetime, Decimal, str | None]]] = {}
    for row in receipts:
        payload = _json_loads(row["payload_json"])
        fee = _decimal(payload.get("fee"))
        if fee is None:
            continue
        stamp = _parse_ts(row["occurred_at"])
        if stamp is None:
            continue
        currency = _text(payload.get("feeCurrency")) or _text(payload.get("currency"))
        by_order.setdefault(str(row["platform_order_id"]), []).append((stamp, fee, currency))
    if not by_order:
        return
    pending = db.execute(
        f"""
        SELECT id, order_id, occurred_at FROM fills
        WHERE order_id IN ({placeholders}) AND (fee IS NULL OR fee = '')
        """,
        order_ids,
    ).fetchall()
    for fill in pending:
        candidates = by_order.get(str(fill["order_id"])) or []
        if not candidates:
            continue
        fill_stamp = _parse_ts(fill["occurred_at"])
        if fill_stamp is None:
            stamp, fee, currency = candidates[0]
        else:
            stamp, fee, currency = min(
                candidates, key=lambda item: abs((item[0] - fill_stamp).total_seconds())
            )
        db.execute(
            "UPDATE fills SET fee = ?, fee_currency = ?, fee_quality = 'reported' "
            "WHERE id = ? AND (fee IS NULL OR fee = '')",
            (str(fee), currency, fill["id"]),
        )


def _derived_account_snapshots(
    db: Any,
    *,
    account_ids: list[str],
    batch_id: str,
    instruction_id: str | None,
    trace_id: str | None,
    started_at: Any,
    finished_at: Any,
) -> list[dict[str, Any]]:
    """Rebuild the account state around a batch from the balance time series.

    The batch runner writes `execution_account_snapshots` at submit and finish.
    When a batch pre-dates that hook, or the hook never fired, the append-only
    `balance_snapshots` series still holds every venue sync (roughly 30s each).
    Reading the last row before the batch and the first row after it answers the
    same question: what did the account look like on both sides of the trade.
    """

    start = _parse_ts(started_at)
    finish = _parse_ts(finished_at)
    if start is None:
        return []
    snapshots: list[dict[str, Any]] = []
    for account_id in sorted(set(account_ids)):
        rows = db.execute(
            """
            SELECT currency, equity, available_balance, as_of, data_quality_state
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of
            """,
            (account_id,),
        ).fetchall()
        if not rows:
            continue
        parsed: list[tuple[datetime, Any]] = []
        for row in rows:
            stamp = _parse_ts(row["as_of"])
            if stamp is None:
                continue
            # The series is append-only and long-lived; keep only the window
            # around this batch so a busy account cannot blow up the response.
            if stamp < start - timedelta(minutes=30):
                continue
            if finish is not None and stamp > finish + timedelta(minutes=30):
                continue
            parsed.append((stamp, row))
        if not parsed:
            continue
        # One snapshot timestamp carries one row per currency. Quote the
        # settlement currency so the numbers line up with fees and notional.
        currencies = {_text(row["currency"]) for _, row in parsed}
        primary_currency = "USDT" if "USDT" in currencies else sorted(currencies)[0]
        parsed = [
            (stamp, row)
            for stamp, row in parsed
            if _text(row["currency"]) == primary_currency
        ]
        if not parsed:
            continue
        before = [item for item in parsed if item[0] <= start]
        after = [item for item in parsed if finish is not None and item[0] >= finish]
        for phase, picked in (
            ("pre_submit", before[-1] if before else None),
            ("final", after[0] if after else None),
        ):
            if picked is None:
                continue
            stamp, row = picked
            equity = _decimal(row["equity"])
            available = _decimal(row["available_balance"])
            snapshots.append(
                {
                    "id": f"derived:{batch_id}:{account_id}:{phase}",
                    "traceId": trace_id,
                    "batchId": batch_id,
                    "instructionId": instruction_id,
                    "accountId": account_id,
                    "phase": phase,
                    "currency": _text(row["currency"]),
                    "balance": str(equity) if equity is not None else None,
                    "available": str(available) if available is not None else None,
                    "equity": str(equity) if equity is not None else None,
                    "positionCount": None,
                    "positions": [],
                    "payload": {
                        "derivedFrom": "balance_snapshots",
                        "snapshotAsOf": _text(row["as_of"]),
                    },
                    "qualityState": _text(row["data_quality_state"]),
                    "capturedAt": stamp.isoformat(),
                    "derivedFrom": "balance_snapshots",
                }
            )
    return snapshots


def _trace_for_batch(db: Any, batch_id: str) -> str | None:
    row = db.execute(
        """
        SELECT trace_id FROM execution_steps
        WHERE batch_id = ? AND trace_id IS NOT NULL
        ORDER BY occurred_at LIMIT 1
        """,
        (batch_id,),
    ).fetchone()
    return str(row["trace_id"]) if row is not None else None


def _related_open_instruction(
    requested_parameters: dict[str, Any],
) -> str | None:
    return _text(requested_parameters.get("targetOpenInstructionId"))


def sync_execution_record(
    batch_id: str, *, trace_id: str | None = None
) -> dict[str, Any] | None:
    """Project one batch into `execution_records`. Never raises for data gaps."""

    try:
        with connection() as db:
            batch = db.execute(
                "SELECT * FROM execution_batches WHERE id = ?", (batch_id,)
            ).fetchone()
            if batch is None:
                return None
            instruction = None
            if batch["strategy_instruction_id"]:
                instruction = db.execute(
                    "SELECT * FROM strategy_runs WHERE id = ?",
                    (batch["strategy_instruction_id"],),
                ).fetchone()
            legs = [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM execution_batch_legs WHERE batch_id = ? "
                    "ORDER BY sequence, id",
                    (batch_id,),
                )
            ]
            order_ids = [str(leg["order_id"]) for leg in legs if leg.get("order_id")]
            orders: dict[str, dict[str, Any]] = {}
            if order_ids:
                placeholders = ",".join("?" for _ in order_ids)
                orders = {
                    str(row["id"]): dict(row)
                    for row in db.execute(
                        f"SELECT * FROM orders WHERE id IN ({placeholders})", order_ids
                    )
                }
            fills_by_order = _fills_for_orders(db, order_ids)
            # Runtime confirmations never carry a fee; the venue receipt does.
            # Backfill before summing so `total_fees` reflects the real cost.
            _backfill_fill_fees(db, order_ids)
            if any(
                fill.get("fee") in (None, "")
                for group in fills_by_order.values()
                for fill in group
            ):
                fills_by_order = _fills_for_orders(db, order_ids)
            risk_row = db.execute(
                "SELECT * FROM execution_batch_risk WHERE batch_id = ?", (batch_id,)
            ).fetchone()

            requested_parameters = _json_loads(
                instruction["requested_parameters_json"] if instruction is not None else None
            )
            plan = _json_loads(
                instruction["execution_plan_json"] if instruction is not None else None
            )

            leg_details: list[dict[str, Any]] = []
            total_fees = Decimal("0")
            fee_currency: str | None = None
            fees_by_currency: dict[str, Decimal] = {}
            filled_legs = 0
            for leg in legs:
                order_id = _text(leg.get("order_id"))
                fills = fills_by_order.get(order_id or "", [])
                filled_quantity = sum(
                    (_decimal(fill.get("quantity")) or Decimal("0")) for fill in fills
                )
                average = _average_price(fills)
                order = orders.get(order_id or "")
                leg_status = _text(leg.get("status")) or _text(
                    order.get("status") if order else None
                )
                if leg_status in {"filled", "partially_filled", "hedged"} or filled_quantity > 0:
                    filled_legs += 1
                leg_fees: dict[str, Decimal] = {}
                for fill in fills:
                    fee = _decimal(fill.get("fee"))
                    if fee is None:
                        continue
                    currency = _text(fill.get("fee_currency")) or "USDT"
                    leg_fees[currency] = leg_fees.get(currency, Decimal("0")) + fee
                # A spot buy pays its fee in the base asset, so adding legs
                # together mixes units. Keep a per-currency breakdown and only
                # roll the quote currency into the single `total_fees` column.
                for currency, amount in leg_fees.items():
                    fees_by_currency[currency] = (
                        fees_by_currency.get(currency, Decimal("0")) + amount
                    )
                leg_fee_currency = "USDT" if "USDT" in leg_fees else next(iter(leg_fees), None)
                leg_fee = leg_fees.get(leg_fee_currency, Decimal("0")) if leg_fee_currency else Decimal("0")
                leg_details.append(
                    {
                        "role": _text(leg.get("role")),
                        "accountId": _text(leg.get("account_id")),
                        "symbol": _text(leg.get("symbol")),
                        "side": _text(leg.get("side")),
                        "requestedQuantity": _text(leg.get("quantity")),
                        "filledQuantity": str(filled_quantity),
                        "averagePrice": str(average) if average is not None else None,
                        "notional": (
                            str(filled_quantity * average) if average is not None else None
                        ),
                        "status": leg_status,
                        "orderId": order_id,
                        "externalOrderId": _text(order.get("external_order_id")) if order else None,
                        "fees": str(leg_fee) if leg_fee else None,
                        "feeCurrency": leg_fee_currency,
                        "feeBreakdown": [
                            {"currency": currency, "amount": str(amount)}
                            for currency, amount in leg_fees.items()
                        ],
                        "fillCount": len(fills),
                        "failureReason": _text(leg.get("failure_reason")),
                    }
                )

            primary = next(
                (leg for leg in leg_details if leg["role"] in PRIMARY_LEG_ROLES),
                leg_details[0] if leg_details else None,
            )
            primary_notional: Decimal | None = None
            if primary is not None:
                primary_quantity = _decimal(primary.get("filledQuantity"))
                primary_price = _decimal(primary.get("averagePrice"))
                if (
                    primary_quantity is not None
                    and primary_quantity > 0
                    and primary_price is not None
                ):
                    primary_notional = primary_quantity * primary_price
            if fees_by_currency:
                fee_currency = (
                    "USDT" if "USDT" in fees_by_currency else next(iter(fees_by_currency))
                )
                total_fees = fees_by_currency[fee_currency]
            action = _text(instruction["action"]) if instruction is not None else None
            if action is None:
                action = CLOSE_ACTION if requested_parameters.get("targetOpenInstructionId") else OPEN_ACTION
            started_at = _text(batch["created_at"]) or utc_now_iso()
            status = _text(batch["status"]) or "unknown"
            finished_at = _text(batch["updated_at"]) if status in TERMINAL_STATUSES else None
            duration_ms: int | None = None
            if finished_at:
                try:
                    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
                    duration_ms = max(0, int((finished - started).total_seconds() * 1000))
                except ValueError:
                    duration_ms = None

            related_instruction_id = (
                _related_open_instruction(requested_parameters)
                if action == CLOSE_ACTION
                else None
            )
            related_record_id = None
            if related_instruction_id:
                row = db.execute(
                    "SELECT id FROM execution_records WHERE instruction_id = ? "
                    "AND strategy_key = ? ORDER BY started_at LIMIT 1",
                    (related_instruction_id, str(batch["strategy_key"])),
                ).fetchone()
                related_record_id = str(row["id"]) if row is not None else None
            elif action == OPEN_ACTION and batch["strategy_instruction_id"]:
                row = db.execute(
                    "SELECT id FROM execution_records WHERE related_record_id IS NOT NULL "
                    "AND instruction_id != ? AND strategy_key = ? ORDER BY started_at LIMIT 1",
                    (str(batch["strategy_instruction_id"]), str(batch["strategy_key"])),
                ).fetchone()
                related_record_id = str(row["id"]) if row is not None else None

            existing = db.execute(
                "SELECT id, created_at FROM execution_records WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            record_id = str(existing["id"]) if existing is not None else str(uuid4())
            created_at = _text(existing["created_at"]) if existing is not None else started_at
            payload = {
                "id": record_id,
                "strategyKey": _text(batch["strategy_key"]) or "unknown",
                "strategyInstanceId": _text(batch["strategy_instance_id"]),
                "batchId": batch_id,
                "instructionId": _text(batch["strategy_instruction_id"]),
                "action": action,
                "direction": _text(batch["direction"]) or _text(plan.get("direction")),
                "status": status,
                "failureReason": _text(batch["failure_reason"])
                or (
                    _text(instruction["failure_reason"])
                    if instruction is not None
                    else None
                ),
                "traceId": trace_id or _trace_for_batch(db, batch_id),
                "primarySymbol": primary["symbol"] if primary else None,
                "primaryQuantity": primary["filledQuantity"] if primary else None,
                "primaryAveragePrice": primary["averagePrice"] if primary else None,
                "totalFees": str(total_fees) if total_fees else None,
                "feeCurrency": fee_currency,
                "notional": str(primary_notional) if primary_notional else None,
                "legCount": len(leg_details),
                "filledLegCount": filled_legs,
                "legDetails": leg_details,
                "risk": dict(risk_row) if risk_row is not None else None,
                "relatedRecordId": related_record_id,
                "startedAt": started_at,
                "finishedAt": finished_at,
                "durationMs": duration_ms,
            }
            _upsert_record(db, payload, created_at=created_at, leg_details=leg_details)
            if payload["traceId"] is None:
                stored = db.execute(
                    "SELECT trace_id FROM execution_records WHERE batch_id = ?",
                    (batch_id,),
                ).fetchone()
                if stored is not None:
                    payload["traceId"] = stored["trace_id"]
            return payload
    except Exception:  # noqa: BLE001 - projection must never gate trading
        logger.exception("execution record projection failed for batch %s", batch_id)
        return None


def _upsert_record(
    db: Any,
    payload: dict[str, Any],
    *,
    created_at: str,
    leg_details: list[dict[str, Any]],
) -> None:
    now = utc_now_iso()
    db.execute(
        """
        INSERT INTO execution_records (
            id, strategy_key, strategy_instance_id, batch_id, instruction_id,
            action, direction, status, failure_reason, trace_id, primary_symbol,
            primary_quantity, primary_average_price, total_fees, fee_currency,
            notional, leg_count, filled_leg_count, leg_details_json, risk_json,
            related_record_id, started_at, finished_at, duration_ms, projected_at,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(batch_id) DO UPDATE SET
            strategy_key=excluded.strategy_key,
            strategy_instance_id=excluded.strategy_instance_id,
            instruction_id=excluded.instruction_id,
            action=excluded.action,
            direction=excluded.direction,
            status=excluded.status,
            failure_reason=excluded.failure_reason,
            trace_id=COALESCE(excluded.trace_id, execution_records.trace_id),
            primary_symbol=excluded.primary_symbol,
            primary_quantity=excluded.primary_quantity,
            primary_average_price=excluded.primary_average_price,
            total_fees=excluded.total_fees,
            fee_currency=excluded.fee_currency,
            notional=excluded.notional,
            leg_count=excluded.leg_count,
            filled_leg_count=excluded.filled_leg_count,
            leg_details_json=excluded.leg_details_json,
            risk_json=excluded.risk_json,
            related_record_id=COALESCE(excluded.related_record_id, execution_records.related_record_id),
            started_at=excluded.started_at,
            finished_at=excluded.finished_at,
            duration_ms=excluded.duration_ms,
            projected_at=excluded.projected_at,
            updated_at=excluded.updated_at
        """,
        (
            payload["id"],
            payload["strategyKey"],
            payload["strategyInstanceId"],
            payload["batchId"],
            payload["instructionId"],
            payload["action"],
            payload["direction"],
            payload["status"],
            payload["failureReason"],
            payload["traceId"],
            payload["primarySymbol"],
            payload["primaryQuantity"],
            payload["primaryAveragePrice"],
            payload["totalFees"],
            payload["feeCurrency"],
            payload["notional"],
            payload["legCount"],
            payload["filledLegCount"],
            _json_dumps(leg_details),
            _json_dumps(payload["risk"]),
            payload["relatedRecordId"],
            payload["startedAt"],
            payload["finishedAt"],
            payload["durationMs"],
            now,
            created_at,
            now,
        ),
    )


def sync_pending_records(*, limit: int = 50) -> int:
    """Backfill projections for batches that are missing or not yet projected."""

    try:
        with connection() as db:
            rows = db.execute(
                """
                SELECT b.id FROM execution_batches b
                LEFT JOIN execution_records r ON r.batch_id = b.id
                WHERE r.id IS NULL
                   OR r.projected_at < b.updated_at
                ORDER BY b.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except Exception:  # noqa: BLE001
        logger.exception("execution record backfill query failed")
        return 0
    written = 0
    for row in rows:
        if sync_execution_record(str(row["id"])) is not None:
            written += 1
    return written


def record_account_snapshot(
    *,
    account_id: str,
    phase: str,
    batch_id: str | None = None,
    trace_id: str | None = None,
    instruction_id: str | None = None,
    currency: str | None = None,
    balance: Any = None,
    available: Any = None,
    equity: Any = None,
    positions: list[dict[str, Any]] | None = None,
    quality_state: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append one point-in-time account snapshot. Fail-open by design."""

    if phase not in SNAPSHOT_PHASES:
        phase = "post_submit"
    try:
        positions_list = positions or []
        with connection() as db:
            db.execute(
                """
                INSERT INTO execution_account_snapshots (
                    id, trace_id, batch_id, instruction_id, account_id, phase,
                    currency, balance, available, equity, position_count,
                    positions_json, payload_json, quality_state, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    trace_id,
                    batch_id,
                    instruction_id,
                    account_id,
                    phase,
                    currency,
                    _text(balance),
                    _text(available),
                    _text(equity),
                    len(positions_list),
                    _json_dumps(positions_list),
                    _json_dumps(payload),
                    quality_state,
                    utc_now_iso(),
                ),
            )
    except Exception:  # noqa: BLE001
        logger.exception(
            "execution account snapshot failed for %s phase %s", account_id, phase
        )


def capture_account_state(
    *,
    account_id: str,
    phase: str,
    batch_id: str | None = None,
    trace_id: str | None = None,
    instruction_id: str | None = None,
) -> None:
    """Snapshot the account from the last synced venue payload, without I/O.

    Reading the venue again here would put a network round-trip inside the order
    path. The platform already persists a full account snapshot per venue sync,
    so the historical row records what the platform knew at that moment and says
    so through `quality_state`.
    """

    try:
        with connection() as db:
            account = db.execute(
                "SELECT base_currency, environment FROM accounts WHERE id = ?", (account_id,)
            ).fetchone()
            snapshot = db.execute(
                "SELECT payload_json, as_of, data_quality_state, source, venue "
                "FROM account_venue_snapshots WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            position_rows = [
                dict(row)
                for row in db.execute(
                    "SELECT instrument_id, net_quantity, average_price, updated_at "
                    "FROM positions WHERE account_id = ?",
                    (account_id,),
                )
            ]
        payload = _json_loads(snapshot["payload_json"]) if snapshot is not None else {}
        balances = payload.get("balances") if isinstance(payload, dict) else None
        risk = payload.get("accountRisk") if isinstance(payload, dict) else None
        equity = None
        if isinstance(risk, dict):
            breakdown = risk.get("assetBreakdown")
            if isinstance(breakdown, list):
                for item in breakdown:
                    if not isinstance(item, dict):
                        continue
                    if item.get("accountType") == "UnifiedTradingAccount":
                        equity = item.get("totalEquity")
                        break
        available = None
        if isinstance(balances, list):
            for item in balances:
                if not isinstance(item, dict):
                    continue
                if str(item.get("coin") or item.get("currency") or "").upper() == "USDT":
                    available = item.get("available") or item.get("free") or item.get("walletBalance")
                    break
        elif isinstance(balances, dict):
            usdt = balances.get("USDT")
            if isinstance(usdt, dict):
                available = usdt.get("available") or usdt.get("free")
            elif usdt is not None:
                available = usdt
        record_account_snapshot(
            account_id=account_id,
            phase=phase,
            batch_id=batch_id,
            trace_id=trace_id,
            instruction_id=instruction_id,
            currency=(account["base_currency"] if account is not None else None) or "USDT",
            balance=available,
            available=available,
            equity=equity,
            positions=position_rows,
            quality_state=(
                str(snapshot["data_quality_state"])
                if snapshot is not None and snapshot["data_quality_state"]
                else "unavailable"
            ),
            payload={
                "venueSnapshotAsOf": str(snapshot["as_of"]) if snapshot is not None else None,
                "source": str(snapshot["source"]) if snapshot is not None else None,
                "venue": str(snapshot["venue"]) if snapshot is not None else None,
                "environment": str(account["environment"]) if account is not None else None,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("account state capture failed for %s phase %s", account_id, phase)
        print(
            f"[exec-diag] capture failed {account_id} {phase}: {exc!r}",
            file=sys.stderr,
            flush=True,
        )


def _record_row(row: Any) -> dict[str, Any]:
    raw = dict(row)
    # leg_details_json is a JSON array; parsing it with the dict helper silently
    # degraded every record to {} and crashed the detail page on .map().
    leg_details = _json_list(raw.pop("leg_details_json", None))
    risk = _json_loads(raw.pop("risk_json", None))
    record = {_camel(key): value for key, value in raw.items()}
    record["legDetails"] = leg_details
    record["risk"] = risk
    return record


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def _camel_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {_camel(key): value for key, value in row.items()}


def list_execution_records(
    *,
    strategy_key: str | None = None,
    action: str | None = None,
    status: str | None = None,
    symbol: str | None = None,
    started_from: str | None = None,
    started_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    sync_pending_records()
    clauses: list[str] = []
    params: list[Any] = []
    if strategy_key:
        clauses.append("strategy_key = ?")
        params.append(strategy_key)
    if action:
        clauses.append("action = ?")
        params.append(action)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if symbol:
        clauses.append("UPPER(primary_symbol) LIKE ?")
        params.append(f"%{symbol.upper()}%")
    if started_from:
        clauses.append("started_at >= ?")
        params.append(started_from)
    if started_to:
        clauses.append("started_at <= ?")
        params.append(started_to)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    with connection() as db:
        total = db.execute(
            f"SELECT COUNT(*) AS total FROM execution_records {where}", params
        ).fetchone()["total"]
        rows = db.execute(
            f"""
            SELECT * FROM execution_records {where}
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [_record_row(row) for row in rows],
    }


def get_execution_record_detail(record_id: str) -> dict[str, Any] | None:
    """Aggregate the full chain for one record, re-reading durable evidence."""

    with connection() as db:
        row = db.execute(
            "SELECT * FROM execution_records WHERE id = ? OR batch_id = ?",
            (record_id, record_id),
        ).fetchone()
    if row is None:
        return None
    record = _record_row(row)
    batch_id = record["batchId"]
    # Re-project so late fills and fees are reflected even if the writer missed
    # the terminal transition (crashed worker, manual recovery, replay).
    refreshed = sync_execution_record(batch_id, trace_id=record.get("traceId"))
    if refreshed is not None:
        with connection() as db:
            row = db.execute(
                "SELECT * FROM execution_records WHERE batch_id = ?", (batch_id,)
            ).fetchone()
        if row is not None:
            record = _record_row(row)
    with connection() as db:
        batch = db.execute(
            "SELECT * FROM execution_batches WHERE id = ?", (batch_id,)
        ).fetchone()
        instruction = None
        if record.get("instructionId"):
            instruction = db.execute(
                "SELECT * FROM strategy_runs WHERE id = ?", (record["instructionId"],)
            ).fetchone()
        legs = [
            dict(item)
            for item in db.execute(
                "SELECT * FROM execution_batch_legs WHERE batch_id = ? ORDER BY sequence, id",
                (batch_id,),
            )
        ]
        order_ids = [str(leg["order_id"]) for leg in legs if leg.get("order_id")]
        orders: list[dict[str, Any]] = []
        fills: list[dict[str, Any]] = []
        if order_ids:
            placeholders = ",".join("?" for _ in order_ids)
            orders = [
                dict(item)
                for item in db.execute(
                    f"SELECT * FROM orders WHERE id IN ({placeholders}) ORDER BY created_at",
                    order_ids,
                )
            ]
            fills = [
                dict(item)
                for item in db.execute(
                    f"""
                    SELECT f.*, o.symbol AS order_symbol, o.side AS order_side
                    FROM fills f LEFT JOIN orders o ON o.id = f.order_id
                    WHERE f.order_id IN ({placeholders})
                    ORDER BY f.occurred_at, f.id
                    """,
                    order_ids,
                )
            ]
        snapshots = [
            {
                **_camel_dict(dict(item)),
                "positions": _json_list(item["positions_json"]),
                "payload": _json_loads(item["payload_json"]),
            }
            for item in db.execute(
                "SELECT * FROM execution_account_snapshots WHERE batch_id = ? "
                "ORDER BY captured_at",
                (batch_id,),
            )
        ]
        if not snapshots:
            # No batch-time snapshots were captured for this trade (older batch,
            # or the record hook never ran). Fall back to the venue balance
            # series so the account still has evidence on both sides of it.
            snapshots = _derived_account_snapshots(
                db,
                account_ids=[
                    str(item["account_id"]) for item in legs if item.get("account_id")
                ],
                batch_id=batch_id,
                instruction_id=_text(record.get("instructionId")),
                trace_id=_text(record.get("traceId")),
                started_at=record.get("startedAt"),
                finished_at=record.get("finishedAt"),
            )
        related = None
        if record.get("relatedRecordId"):
            related_row = db.execute(
                "SELECT * FROM execution_records WHERE id = ?",
                (record["relatedRecordId"],),
            ).fetchone()
            related = _record_row(related_row) if related_row is not None else None
    from app.execution_steps import list_execution_steps

    # Each leg dispatches under its own trace, so a batch has no single trace to
    # match on. Command ids are present on every dispatched step and cover all
    # legs; trace and batch only remain as fallbacks for records with no orders.
    command_ids = [str(item["command_id"]) for item in orders if item.get("command_id")]
    if command_ids or order_ids:
        timeline = list_execution_steps(command_ids=command_ids, order_ids=order_ids)
    elif record.get("traceId"):
        timeline = list_execution_steps(trace_id=record["traceId"])
    else:
        timeline = list_execution_steps(batch_id=batch_id)
    return {
        "record": record,
        "batch": dict(batch) if batch is not None else None,
        "instruction": (
            {
                **_camel_dict(dict(instruction)),
                "requestedParameters": _json_loads(instruction["requested_parameters_json"]),
                "executionPlan": _json_loads(instruction["execution_plan_json"]),
            }
            if instruction is not None
            else None
        ),
        "legs": legs,
        "orders": orders,
        "fills": fills,
        "accountSnapshots": snapshots,
        "timeline": timeline,
        "relatedRecord": related,
    }
