from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from sqlite3 import Row
from threading import Lock

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import monitor_health
from app.account_read_jobs import record_job
from app.config import get_settings
from app.database import connection
from app.venue_identity_repository import (
    load_order_identities,
    resolve_snapshot_order,
    scoped_identity,
)
from app.venue_reconciliation import runtime_get
from app.venue_reconciliation_repository import effective_venue_event

SNAPSHOT_SYNC_INTERVAL_SECONDS = 30.0
_SNAPSHOT_SYNC_LOCK = Lock()
logger = logging.getLogger(__name__)


class AccountSyncStatusResponse(BaseModel):
    account_id: str = Field(alias="accountId")
    status: str
    error_code: str | None = Field(default=None, alias="errorCode")
    last_attempt_at: str | None = Field(default=None, alias="lastAttemptAt")
    last_success_at: str | None = Field(default=None, alias="lastSuccessAt")
    updated_at: str = Field(alias="updatedAt")


class VenueSnapshotSyncResponse(BaseModel):
    overall_status: str = Field(alias="overallStatus")
    synced_accounts: list[str] = Field(alias="syncedAccounts")
    failed_accounts: list[AccountSyncStatusResponse] = Field(
        default_factory=list,
        alias="failedAccounts",
    )
    skipped_accounts: list[AccountSyncStatusResponse] = Field(
        default_factory=list,
        alias="skippedAccounts",
    )
    balance_snapshots: int = Field(alias="balanceSnapshots")
    order_rows: int = Field(alias="orderRows")
    fill_rows: int = Field(alias="fillRows")
    position_rows: int = Field(alias="positionRows")
    pnl_rows: int = Field(alias="pnlRows")
    as_of: str = Field(alias="asOf")


class EquityHistoryPoint(BaseModel):
    asOf: str = Field(alias="asOf")
    equity: str


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _as_decimal(value: object, *, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValueError("Runtime financial value must be finite")
    return parsed


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _fill_fingerprint(account_id: str, fill: dict[str, object]) -> str | None:
    required = {
        "externalOrderId": fill.get("externalOrderId"),
        "symbol": fill.get("symbol"),
        "side": fill.get("side"),
        "quantity": fill.get("quantity"),
        "price": fill.get("price"),
        "occurredAt": fill.get("occurredAt"),
    }
    if any(value in {None, ""} for value in required.values()):
        return None
    payload = {
        "accountId": account_id,
        **required,
    }
    return f"fingerprint:{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"


def _status_row(account_id: str) -> Row | None:
    with connection() as db:
        return db.execute(
            """
            SELECT account_id, status, error_code, last_attempt_at, last_success_at, updated_at
            FROM account_sync_status
            WHERE account_id = ?
            """,
            (account_id,),
        ).fetchone()


def _write_status(
    account_id: str,
    *,
    status: str,
    error_code: str | None,
    last_attempt_at: str | None = None,
    last_success_at: str | None = None,
) -> None:
    now = _iso_now()
    with connection() as db:
        existing = db.execute(
            "SELECT last_attempt_at, last_success_at FROM account_sync_status WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        db.execute(
            """
            INSERT INTO account_sync_status (
                account_id, status, error_code, last_attempt_at, last_success_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET
                status = excluded.status,
                error_code = excluded.error_code,
                last_attempt_at = excluded.last_attempt_at,
                last_success_at = excluded.last_success_at,
                updated_at = excluded.updated_at
            """,
            (
                account_id,
                status,
                error_code,
                last_attempt_at or (existing["last_attempt_at"] if existing else None),
                last_success_at or (existing["last_success_at"] if existing else None),
                now,
            ),
        )


def discover_live_accounts() -> list[str]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT DISTINCT a.id
            FROM strategy_account_bindings sab
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.status = 'active'
              AND a.status = 'active'
              AND lower(a.environment) = 'live'
              AND sab.role != 'local_test'
            ORDER BY a.id
            """
        ).fetchall()
    return [str(row["id"]) for row in rows]


def load_sync_statuses() -> list[AccountSyncStatusResponse]:
    discovered = discover_live_accounts()
    with connection() as db:
        rows_by_account = {
            str(row["account_id"]): row
            for row in db.execute(
                """
                SELECT account_id, status, error_code, last_attempt_at, last_success_at, updated_at
                FROM account_sync_status
                ORDER BY account_id
                """
            ).fetchall()
        }
    results: list[AccountSyncStatusResponse] = []
    for account_id in discovered:
        row = rows_by_account.get(account_id)
        if row is None:
            results.append(
                AccountSyncStatusResponse(
                    accountId=account_id,
                    status="waiting_initial_sync",
                    errorCode=None,
                    lastAttemptAt=None,
                    lastSuccessAt=None,
                    updatedAt=_iso_now(),
                )
            )
            continue
        results.append(
            AccountSyncStatusResponse(
                accountId=account_id,
                status=str(row["status"]),
                errorCode=row["error_code"],
                lastAttemptAt=row["last_attempt_at"],
                lastSuccessAt=row["last_success_at"],
                updatedAt=str(row["updated_at"]),
            )
        )
    return results


def _persist_balances(db, account_id: str, balances: list[dict[str, object]]) -> int:
    written = 0
    for balance in balances:
        as_of = str(balance.get("asOf") or _iso_now())
        currency = str(balance.get("currency") or "USD").upper()
        snapshot_id = f"sync:{account_id}:{currency}:{as_of}"
        db.execute(
            """
            INSERT OR REPLACE INTO balance_snapshots (
                id, account_id, currency, equity, available_balance,
                source, data_quality_state, as_of, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                account_id,
                currency,
                str(_as_decimal(balance.get("equity"))),
                (
                    str(_as_decimal(balance["availableBalance"]))
                    if balance.get("availableBalance") is not None
                    else None
                ),
                str(balance.get("source") or "runtime"),
                str(balance.get("dataQualityState") or "complete"),
                as_of,
                _iso_now(),
            ),
        )
        written += 1
    return written


def _persist_positions(
    db,
    account_id: str,
    positions: list[dict[str, object]],
) -> tuple[int, dict[str, Decimal]]:
    written = 0
    previously_observed = db.execute(
        """
        SELECT instrument_id FROM positions WHERE account_id = ?
        UNION
        SELECT instrument_id FROM pnl_results WHERE account_id = ?
        """,
        (account_id, account_id),
    ).fetchall()
    unrealized_by_instrument: dict[str, Decimal] = {
        str(row["instrument_id"]): Decimal("0") for row in previously_observed
    }
    db.execute("DELETE FROM positions WHERE account_id = ?", (account_id,))
    grouped: dict[str, list[dict[str, object]]] = {}
    for position in positions:
        grouped.setdefault(str(position["instrumentId"]), []).append(position)
    for instrument_id, rows in grouped.items():
        quantities = [_as_decimal(row["netQuantity"]) for row in rows]
        quantity = sum(quantities, Decimal("0"))
        known_prices = all(row.get("averagePrice") is not None for row in rows)
        same_direction = all(value >= 0 for value in quantities) or all(
            value <= 0 for value in quantities
        )
        average = None
        if quantity and known_prices and same_direction:
            average = sum(
                (
                    abs(value) * _as_decimal(row["averagePrice"])
                    for value, row in zip(quantities, rows, strict=True)
                ),
                Decimal("0"),
            ) / abs(quantity)
        unrealized_by_instrument[instrument_id] = sum(
            (_as_decimal(row.get("unrealizedPnl")) for row in rows), Decimal("0")
        )
        db.execute(
            "INSERT INTO positions "
            "(account_id,instrument_id,net_quantity,average_price,updated_at) "
            "VALUES (?,?,?,?,?)",
            (
                account_id,
                instrument_id,
                str(quantity),
                str(average) if average is not None else None,
                max(str(row.get("asOf") or _iso_now()) for row in rows),
            ),
        )
        written += len(rows)
    return written, unrealized_by_instrument


def _persist_orders(db, account_id: str, orders: list[dict[str, object]]) -> int:
    written = 0
    identities = load_order_identities(db)
    for order in orders:
        instrument_id = str(order.get("instrumentId") or "")
        if not instrument_id:
            continue
        order_id = resolve_snapshot_order(db, account_id, order, identities=identities)
        previous = db.execute(
            "SELECT o.account_id,o.instrument_id,o.external_order_id,tc.id AS owned_command "
            "FROM orders o LEFT JOIN trade_commands tc ON tc.id=o.command_id WHERE o.id=?",
            (order_id,),
        ).fetchone()
        if previous is not None and (
            previous["account_id"] != account_id or previous["instrument_id"] != instrument_id
        ):
            raise ValueError("Venue order identity conflicts with existing order ownership")
        if previous is not None and previous["owned_command"]:
            # Account monitoring records evidence; execution/reconciliation owns
            # command status and cumulative quantities, including unknown results.
            db.execute(
                "UPDATE orders SET external_order_id=COALESCE(NULLIF(external_order_id,''),?),"
                "venue_payload_json=? WHERE id=?",
                (order.get("externalOrderId"), _canonical_json(order), order_id),
            )
            if not previous["external_order_id"]:
                identities = load_order_identities(db)
            written += 1
            continue
        db.execute(
            """
            INSERT INTO orders (
                id, command_id, account_id, instrument_id, symbol, side, order_type,
                quantity, price, status, external_order_id, created_at, updated_at,
                venue_payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                external_order_id = excluded.external_order_id,
                updated_at = excluded.updated_at,
                venue_payload_json = excluded.venue_payload_json
            WHERE excluded.updated_at >= orders.updated_at
            """,
            (
                order_id,
                order_id,
                account_id,
                instrument_id,
                str(order.get("symbol") or ""),
                str(order.get("side") or "buy"),
                str(order.get("orderType") or "limit"),
                str(_as_decimal(order.get("quantity"))),
                (
                    str(_as_decimal(order.get("price")))
                    if order.get("price") not in {None, ""}
                    else None
                ),
                str(order.get("status") or "accepted"),
                str(order.get("externalOrderId") or ""),
                str(order.get("occurredAt") or _iso_now()),
                str(order.get("asOf") or _iso_now()),
                _canonical_json(order),
            ),
        )
        if previous is None:
            identities = load_order_identities(db)
        written += 1
    return written


def _ensure_fill_order_row(
    db,
    account_id: str,
    fill: dict[str, object],
    order_id: str,
    instrument_id: str,
) -> None:
    existing = db.execute("SELECT 1 FROM orders WHERE id = ?", (order_id,)).fetchone()
    if existing is not None:
        return
    occurred_at = str(fill.get("occurredAt") or _iso_now())
    symbol = str(fill.get("symbol") or "")
    side = str(fill.get("side") or "buy")
    quantity = str(_as_decimal(fill.get("quantity")))
    price = str(_as_decimal(fill.get("price")))
    external_order_id = str(fill.get("externalOrderId") or order_id)
    db.execute(
        """
        INSERT INTO orders (
            id, command_id, account_id, instrument_id, symbol, side, order_type,
            quantity, price, status, external_order_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            order_id,
            account_id,
            instrument_id,
            symbol,
            side,
            "market",
            quantity,
            price,
            "filled",
            external_order_id,
            occurred_at,
            occurred_at,
        ),
    )


def _persist_fills(
    db,
    account_id: str,
    fills: list[dict[str, object]],
) -> tuple[int, dict[str, Decimal], dict[str, Decimal]]:
    written = 0
    identities = load_order_identities(db)
    fees_by_instrument: dict[str, Decimal] = {}
    realized_by_instrument: dict[str, Decimal] = {}
    for fill in fills:
        native_id = str(fill.get("externalFillId") or "")
        if not native_id:
            fingerprint = _fill_fingerprint(account_id, fill)
            if fingerprint is None:
                raise ValueError("Runtime fill lacks authoritative identity")
            native_id = fingerprint
        fill_id = scoped_identity(
            "fill", account_id, str(fill.get("source") or "runtime"), native_id
        )
        instrument_id = str(fill.get("instrumentId") or "")
        if not instrument_id:
            continue
        order_id = resolve_snapshot_order(db, account_id, fill, identities=identities)
        _ensure_fill_order_row(
            db,
            account_id,
            fill,
            order_id,
            instrument_id,
        )
        if order_id not in identities.rows:
            identities = load_order_identities(db)
        requested = db.execute(
            """
            SELECT orders.quantity
            FROM orders
            JOIN trade_commands ON trade_commands.id = orders.command_id
            WHERE orders.id = ?
            """,
            (order_id,),
        ).fetchone()
        existing = db.execute(
            "SELECT * FROM fills WHERE id=? OR (id=? AND account_id=?)",
            (fill_id, native_id, account_id),
        ).fetchall()
        for row in existing:
            if requested is not None and row["origin"] != "venue_execution":
                # A Runtime/legacy confirmation can carry its own confirmation
                # time. It is not the native receipt identified by this ticket.
                # Native replay integrity is enforced in venue_account_events.
                continue
            canonical_order = identities.canonical.get(row["order_id"])
            if (
                canonical_order != order_id
                or row["account_id"] != account_id
                or row["instrument_id"] != instrument_id
                or row["side"] != fill.get("side")
                or _as_decimal(row["quantity"]) != _as_decimal(fill.get("quantity"))
                or _as_decimal(row["price"]) != _as_decimal(fill.get("price"))
                or datetime.fromisoformat(row["occurred_at"].replace("Z", "+00:00"))
                != datetime.fromisoformat(str(fill["occurredAt"]).replace("Z", "+00:00"))
            ):
                raise ValueError("Venue fill identity conflicts with existing financial data")
        if existing or requested is not None:
            # Native receipts are retained in venue_account_events for management.
            # They must not append deltas to the execution path's confirmations.
            continue
        incoming_quantity = _as_decimal(fill.get("quantity"))
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO fills (
                id, order_id, account_id, instrument_id, side, quantity, price, occurred_at,
                origin, source, external_fill_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'venue_execution', ?, ?)
            """,
            (
                fill_id,
                order_id,
                account_id,
                instrument_id,
                str(fill.get("side") or "buy"),
                str(incoming_quantity),
                str(_as_decimal(fill.get("price"))),
                str(fill.get("occurredAt") or _iso_now()),
                str(fill.get("source") or "runtime"),
                native_id,
            ),
        )
        if cursor.rowcount and cursor.rowcount > 0:
            written += 1
    return written, realized_by_instrument, fees_by_instrument


def _persist_pnl(
    db,
    account_id: str,
    *,
    unrealized_by_instrument: dict[str, Decimal],
    realized_by_instrument: dict[str, Decimal],
    fees_by_instrument: dict[str, Decimal],
) -> int:
    written = 0
    instrument_ids = (
        set(unrealized_by_instrument) | set(realized_by_instrument) | set(fees_by_instrument)
    )
    for instrument_id in instrument_ids:
        existing = db.execute(
            """
            SELECT realized_pnl, trading_pnl, fees
            FROM pnl_results
            WHERE account_id = ? AND instrument_id = ?
            """,
            (account_id, instrument_id),
        ).fetchone()
        realized = Decimal(str(existing["realized_pnl"])) if existing is not None else Decimal("0")
        trading = Decimal(str(existing["trading_pnl"])) if existing is not None else Decimal("0")
        fees = Decimal(str(existing["fees"])) if existing is not None else Decimal("0")
        if instrument_id in realized_by_instrument:
            realized = realized_by_instrument[instrument_id]
        if instrument_id in unrealized_by_instrument:
            trading = unrealized_by_instrument[instrument_id]
        if instrument_id in fees_by_instrument:
            fees = fees_by_instrument[instrument_id]
        db.execute(
            """
            INSERT INTO pnl_results (
                account_id, instrument_id, realized_pnl, trading_pnl, fees, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, instrument_id) DO UPDATE SET
                realized_pnl = excluded.realized_pnl,
                trading_pnl = excluded.trading_pnl,
                fees = excluded.fees,
                updated_at = excluded.updated_at
            """,
            (
                account_id,
                instrument_id,
                str(realized),
                str(trading),
                str(fees),
                _iso_now(),
            ),
        )
        written += 1
    return written


def _persist_account_risk(db, account_id: str, risk: dict[str, object] | None) -> int:
    if not risk:
        return 0
    as_of = str(risk.get("asOf") or _iso_now())
    db.execute(
        """
        INSERT OR REPLACE INTO account_risk_snapshots (
            account_id, as_of, currency, equity, margin, free_margin, margin_level,
            data_quality_state, created_at, payload_json, total_assets, asset_scope
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            account_id,
            as_of,
            str(risk.get("currency") or "USD"),
            (
                str(_as_decimal(risk.get("equity")))
                if risk.get("equity") not in {None, ""}
                else None
            ),
            (
                str(_as_decimal(risk.get("initialMargin")))
                if risk.get("initialMargin") not in {None, ""}
                else None
            ),
            (
                str(_as_decimal(risk.get("availableBalance")))
                if risk.get("availableBalance") not in {None, ""}
                else None
            ),
            (
                str(_as_decimal(risk.get("marginLevel")))
                if risk.get("marginLevel") not in {None, ""}
                else None
            ),
            str(risk.get("dataQualityState") or "complete"),
            _iso_now(),
            _canonical_json(risk),
            str(_as_decimal(risk["totalAssets"])) if risk.get("totalAssets") is not None else None,
            str(risk.get("assetScope") or "unspecified"),
        ),
    )
    return 1


def _classify_sync_failure(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, ValueError):
        return "query_failed", "query_failed"
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    detail = ""
    if response is not None:
        try:
            payload = response.json()
            detail = str(payload.get("detail") or "")
        except Exception:
            detail = str(getattr(response, "text", "") or "")
    lowered = detail.lower()
    if "identity mismatch" in lowered:
        return "identity_mismatch", "identity_mismatch"
    if "restore failed" in lowered:
        return "restore_failed", "restore_failed"
    if "missing required secret" in lowered or "credential" in lowered:
        return "credential_unavailable", "credential_unavailable"
    if "query failed" in lowered or "authoritative identity" in lowered:
        return "query_failed", "query_failed"
    if status_code is not None:
        return "runtime_unavailable", f"runtime_{status_code}"
    return "runtime_unavailable", "runtime_unavailable"


def _validate_snapshot(account_id: str, snapshot: object) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("accountId") != account_id:
        raise ValueError("Runtime snapshot account identity mismatch")
    for section in ("balances", "positions", "orders", "fills"):
        rows = snapshot.get(section)
        if not isinstance(rows, list):
            # An absent or malformed section is not an authoritative empty account.
            raise ValueError(f"Runtime snapshot is missing {section}")
        for row in rows:
            if not isinstance(row, dict) or row.get("accountId", account_id) != account_id:
                raise ValueError(f"Runtime {section} account identity mismatch")
    for section, required in (
        ("positions", ("instrumentId", "netQuantity")),
        ("orders", ("instrumentId", "quantity", "side")),
        ("fills", ("instrumentId", "quantity", "price", "side")),
        ("balances", ("currency", "equity", "asOf")),
    ):
        for row in snapshot[section]:
            if any(row.get(key) in (None, "") for key in required):
                raise ValueError(f"Runtime {section} lacks required financial fields")
            for key in (
                "netQuantity",
                "quantity",
                "price",
                "averagePrice",
                "equity",
                "availableBalance",
                "fee",
                "unrealizedPnl",
            ):
                if row.get(key) not in (None, ""):
                    _as_decimal(row[key])
            if section in {"orders", "fills"} and (
                row["side"] not in {"buy", "sell"} or _as_decimal(row["quantity"]) <= 0
            ):
                raise ValueError("Runtime trade has invalid side or quantity")
            for key in ("asOf", "occurredAt"):
                if (
                    row.get(key) is not None
                    and datetime.fromisoformat(str(row[key]).replace("Z", "+00:00")).tzinfo is None
                ):
                    raise ValueError("Runtime financial timestamps require timezone")
    if not snapshot.get("asOf"):
        raise ValueError("Runtime snapshot requires asOf")
    risk = snapshot.get("accountRisk")
    if risk is not None and (
        not isinstance(risk, dict)
        or risk.get("accountId") != account_id
        or not risk.get("currency")
    ):
        raise ValueError("Runtime account risk identity mismatch")
    for key in ("asOf", "historyStart", "historyEnd"):
        if snapshot.get(key) is not None:
            stamp = datetime.fromisoformat(str(snapshot[key]).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("Runtime snapshot timestamps must include timezone")
    events = snapshot.get("economicEvents", [])
    if not isinstance(events, list):
        raise ValueError("Runtime economic events must be a list")
    for event in events:
        if not isinstance(event, dict) or event.get("accountId") != account_id:
            raise ValueError("Runtime economic event account identity mismatch")


def _persist_venue_snapshot(db, account_id: str, snapshot: dict[str, object]) -> None:
    # Keep complete venue position tickets and coin-level fields for monitoring.
    # Operational positions remain a separate net-position projection.
    db.execute(
        """INSERT INTO account_venue_snapshots (
           account_id, source, venue, as_of, history_start, history_end,
           data_quality_state, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(account_id) DO UPDATE SET source=excluded.source,
           venue=excluded.venue, as_of=excluded.as_of, history_start=excluded.history_start,
           history_end=excluded.history_end, data_quality_state=excluded.data_quality_state,
           payload_json=excluded.payload_json""",
        (
            account_id,
            str(snapshot.get("source") or "runtime"),
            str(snapshot.get("venue") or ""),
            str(snapshot.get("asOf") or _iso_now()),
            snapshot.get("historyStart"),
            snapshot.get("historyEnd"),
            str(snapshot.get("dataQualityState") or "partial"),
            _canonical_json(snapshot),
        ),
    )


def _persist_venue_event(db, account_id: str, event_type: str, event: dict[str, object]) -> None:
    if event.get("accountId", account_id) != account_id:
        raise ValueError("Venue event account identity mismatch")
    if event_type not in {"trade_fill", "funding", "swap", "fee", "realized_pnl"}:
        raise ValueError("Unknown venue economic event type")
    external_id = event.get("externalFillId" if event_type == "trade_fill" else "externalEventId")
    if not external_id and event_type == "trade_fill":
        external_id = _fill_fingerprint(account_id, event)
    if not external_id:
        raise ValueError("Runtime event lacks authoritative identity")
    if event.get("occurredAt") is None:
        raise ValueError("Runtime event lacks authoritative occurrence time")
    identity = (account_id, str(event.get("source") or "runtime"), event_type, str(external_id))
    existing = db.execute(
        """SELECT payload_json FROM venue_account_events
           WHERE account_id=? AND source=? AND event_type=? AND external_id=?""",
        identity,
    ).fetchone()
    if existing is not None:
        previous = effective_venue_event(
            db, account_id, event_type, json.loads(existing["payload_json"])
        )
        identities = load_order_identities(db)
        if identities.instrument(account_id, previous.get("instrumentId")) != (
            identities.instrument(account_id, event.get("instrumentId"))
        ):
            raise ValueError("Venue event identity was reused with different instrument")
        for field in ("quantity", "price", "fee", "amount", "realizedPnl", "swap"):
            old = previous.get(field)
            new = event.get(field)
            if (old is None) != (new is None) or (
                old is not None and _as_decimal(old) != _as_decimal(new)
            ):
                raise ValueError("Venue event identity was reused with different financial data")
        for field in (
            "currency",
            "side",
            "symbol",
            "externalOrderId",
            "positionId",
        ):
            if previous.get(field) != event.get(field):
                raise ValueError("Venue event identity was reused with different financial data")
        if datetime.fromisoformat(str(previous["occurredAt"]).replace("Z", "+00:00")) != (
            datetime.fromisoformat(str(event["occurredAt"]).replace("Z", "+00:00"))
        ):
            raise ValueError("Venue event identity was reused with different occurrence time")
        if previous.get("platformOrderId") != event.get("platformOrderId"):
            old_order = identities.resolve(account_id, previous)
            new_order = identities.resolve(account_id, event)
            if old_order != new_order or (old_order is None and not event.get("externalOrderId")):
                raise ValueError("Venue event identity was reused with different order ownership")
        return
    for key in ("quantity", "price", "fee", "amount", "realizedPnl", "swap"):
        if event.get(key) is not None:
            _as_decimal(event[key])
    db.execute(
        """INSERT INTO venue_account_events (account_id, source, event_type, external_id,
           instrument_id, platform_order_id, occurred_at, amount, currency, payload_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            *identity,
            event.get("instrumentId"),
            event.get("platformOrderId"),
            event["occurredAt"],
            str(_as_decimal(event["amount"])) if event.get("amount") is not None else None,
            event.get("currency"),
            _canonical_json(event),
        ),
    )


def _sync_one_account(account_id: str, *, include_history: bool = True) -> dict[str, int]:
    last_attempt_at = _iso_now()
    _write_status(account_id, status="syncing", error_code=None, last_attempt_at=last_attempt_at)
    try:
        params = {"accountId": account_id}
        if not include_history:
            params["includeHistory"] = "false"
        snapshot_response = runtime_get("/venue/account-snapshot", params=params)
        snapshot_response.raise_for_status()
        snapshot = snapshot_response.json()
        _validate_snapshot(account_id, snapshot)
        with connection() as db:
            previous = db.execute(
                "SELECT as_of FROM account_venue_snapshots WHERE account_id=?", (account_id,)
            ).fetchone()
            stamp = datetime.fromisoformat(str(snapshot["asOf"]).replace("Z", "+00:00"))
            if (stamp - datetime.now(UTC)).total_seconds() > 5 or (
                previous
                and stamp < datetime.fromisoformat(previous["as_of"].replace("Z", "+00:00"))
            ):
                raise ValueError("Runtime snapshot clock or ordering is invalid")
            balance_count = _persist_balances(db, account_id, list(snapshot.get("balances") or []))
            position_count, unrealized = _persist_positions(
                db,
                account_id,
                list(snapshot.get("positions") or []),
            )
            order_count = (
                _persist_orders(db, account_id, list(snapshot.get("orders") or []))
                if include_history
                else 0
            )
            fill_count, realized, fees = (
                _persist_fills(
                    db,
                    account_id,
                    list(snapshot.get("fills") or []),
                )
                if include_history
                else (0, {}, {})
            )
            pnl_count = _persist_pnl(
                db,
                account_id,
                unrealized_by_instrument=unrealized,
                realized_by_instrument=realized,
                fees_by_instrument=fees,
            )
            _persist_account_risk(db, account_id, snapshot.get("accountRisk"))
            if not include_history:
                previous_payload = db.execute(
                    "SELECT payload_json FROM account_venue_snapshots WHERE account_id=?",
                    (account_id,),
                ).fetchone()
                if previous_payload:
                    historical = json.loads(previous_payload[0])
                    snapshot = dict(snapshot)
                    for key in (
                        "orders",
                        "fills",
                        "economicEvents",
                        "economicEventsQuality",
                        "historyStart",
                        "historyEnd",
                        "historyAuditAt",
                        "historyObservedAt",
                        "historyWindowSeconds",
                    ):
                        if key in historical:
                            snapshot[key] = historical[key]
            _persist_venue_snapshot(db, account_id, snapshot)
            from app.account_performance import persist_valuation_rates

            persist_valuation_rates(db, account_id, snapshot)
            for fill in snapshot["fills"] if include_history else []:
                _persist_venue_event(db, account_id, "trade_fill", fill)
            for event in snapshot.get("economicEvents", []) if include_history else []:
                _persist_venue_event(db, account_id, str(event["eventType"]), event)
            completed = _iso_now()
            db.execute(
                """UPDATE account_sync_status SET status='ready', error_code=NULL,
                   last_success_at=?, updated_at=? WHERE account_id=?""",
                (completed, completed, account_id),
            )
    except Exception as exc:
        status, error_code = _classify_sync_failure(exc)
        _write_status(
            account_id,
            status=status,
            error_code=error_code,
            last_attempt_at=last_attempt_at,
        )
        raise
    if include_history:
        complete = snapshot.get("economicEventsQuality") == "complete"
        record_job(
            account_id,
            "history",
            "ready" if complete else "failed",
            None if complete else "economic_events_unavailable",
        )
        _sync_account_finance(account_id)
    return {
        "balanceSnapshots": balance_count,
        "orderRows": order_count,
        "fillRows": fill_count,
        "positionRows": position_count,
        "pnlRows": pnl_count,
    }


def _sync_account_finance(account_id: str) -> None:
    from app.account_performance import sync_capital_history
    from app.funding_settlement_accounting import sync_funding_settlements

    record_job(account_id, "settlements", "syncing")
    try:
        sync_funding_settlements(account_id)
    except Exception as exc:
        record_job(account_id, "settlements", "failed", type(exc).__name__)
        logger.warning("Account settlement projection failed: %s", type(exc).__name__)
    else:
        record_job(account_id, "settlements", "ready")
    # Capital history owns its existing persisted coverage/error state.
    try:
        sync_capital_history(account_id)
    except Exception as exc:
        # Even a capital-history setup failure must not change observation health.
        with connection() as db:
            db.execute(
                "INSERT INTO account_capital_sync VALUES (?,?,'failed',?) ON CONFLICT(account_id) "
                "DO UPDATE SET attempted_at=excluded.attempted_at,status='failed',"
                "error_code=excluded.error_code",
                (account_id, _iso_now(), type(exc).__name__),
            )
        logger.warning("Capital history preparation failed: %s", type(exc).__name__)


def _sync_account_result(
    account_id: str,
    *,
    include_history: bool = True,
) -> tuple[str, dict[str, int] | None, AccountSyncStatusResponse | None]:
    try:
        return account_id, _sync_one_account(account_id, include_history=include_history), None
    except HTTPException as exc:
        status = _status_row(account_id)
        return (
            account_id,
            None,
            AccountSyncStatusResponse(
                accountId=account_id,
                status=(str(status["status"]) if status is not None else "failed"),
                errorCode=(str(status["error_code"]) if status is not None else str(exc.detail)),
                lastAttemptAt=(str(status["last_attempt_at"]) if status is not None else None),
                lastSuccessAt=(str(status["last_success_at"]) if status is not None else None),
                updatedAt=(str(status["updated_at"]) if status is not None else _iso_now()),
            ),
        )
    except Exception:
        status = _status_row(account_id)
        return (
            account_id,
            None,
            AccountSyncStatusResponse(
                accountId=account_id,
                status=(str(status["status"]) if status is not None else "failed"),
                errorCode=(
                    str(status["error_code"]) if status is not None else "runtime_unavailable"
                ),
                lastAttemptAt=(str(status["last_attempt_at"]) if status is not None else None),
                lastSuccessAt=(str(status["last_success_at"]) if status is not None else None),
                updatedAt=(str(status["updated_at"]) if status is not None else _iso_now()),
            ),
        )


def _sync_venue_snapshots(
    account_id: str | None = None, *, include_history: bool = True
) -> VenueSnapshotSyncResponse:
    account_ids = [account_id] if account_id is not None else discover_live_accounts()
    if account_id is not None and account_id not in discover_live_accounts():
        raise HTTPException(
            status_code=404,
            detail="Live account is not discoverable from active bindings",
        )
    totals = {
        "balanceSnapshots": 0,
        "orderRows": 0,
        "fillRows": 0,
        "positionRows": 0,
        "pnlRows": 0,
    }
    synced: list[str] = []
    failed: list[AccountSyncStatusResponse] = []
    skipped: list[AccountSyncStatusResponse] = []
    with ThreadPoolExecutor(max_workers=max(1, min(len(account_ids), 4))) as executor:
        results = executor.map(
            lambda current: _sync_account_result(current, include_history=include_history),
            account_ids,
        )
        for current, result, failure in results:
            if failure is not None:
                failed.append(failure)
                continue
            assert result is not None
            synced.append(current)
            for key, value in result.items():
                totals[key] += value
    if synced and failed:
        overall_status = "partial"
    elif failed:
        overall_status = "failed"
    elif skipped:
        overall_status = "skipped"
    else:
        overall_status = "synced"
    return VenueSnapshotSyncResponse(
        overallStatus=overall_status,
        syncedAccounts=synced,
        failedAccounts=failed,
        skippedAccounts=skipped,
        balanceSnapshots=totals["balanceSnapshots"],
        orderRows=totals["orderRows"],
        fillRows=totals["fillRows"],
        positionRows=totals["positionRows"],
        pnlRows=totals["pnlRows"],
        asOf=_iso_now(),
    )


def sync_venue_snapshots(
    account_id: str | None = None, *, include_history: bool = True
) -> VenueSnapshotSyncResponse:
    if not _SNAPSHOT_SYNC_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Venue snapshot sync already running")
    try:
        return _sync_venue_snapshots(account_id, include_history=include_history)
    finally:
        _SNAPSHOT_SYNC_LOCK.release()


def load_equity_history(account_id: str, currency: str | None = None) -> list[EquityHistoryPoint]:
    with connection() as db:
        latest_risk = db.execute(
            """
            SELECT currency
            FROM account_risk_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC
            LIMIT 1
            """,
            (account_id,),
        ).fetchone()
        risk_currency = currency or (str(latest_risk["currency"]) if latest_risk else None)
        if risk_currency:
            rows = db.execute(
                """
                SELECT as_of, equity
                FROM (
                    SELECT as_of, equity
                    FROM account_risk_snapshots
                    WHERE account_id = ?
                      AND currency = ?
                      AND equity IS NOT NULL
                    ORDER BY as_of DESC
                    LIMIT 1000
                )
                ORDER BY as_of ASC
                """,
                (account_id, risk_currency),
            ).fetchall()
            if rows:
                return [
                    EquityHistoryPoint(asOf=row["as_of"], equity=str(row["equity"])) for row in rows
                ]

        if currency:
            rows = db.execute(
                """
                SELECT as_of, equity FROM balance_snapshots
                WHERE account_id = ? AND currency = ?
                ORDER BY as_of DESC
                LIMIT 1000
                """,
                (account_id, currency),
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT as_of, equity FROM balance_snapshots
                WHERE account_id = ?
                ORDER BY as_of DESC
                LIMIT 1000
                """,
                (account_id,),
            ).fetchall()
    if currency:
        return [
            EquityHistoryPoint(asOf=row["as_of"], equity=str(row["equity"]))
            for row in reversed(rows)
        ]
    aggregated: dict[str, Decimal] = {}
    ordered_as_of: list[str] = []
    for row in reversed(rows):
        as_of = str(row["as_of"])
        if as_of not in aggregated:
            aggregated[as_of] = Decimal("0")
            ordered_as_of.append(as_of)
        aggregated[as_of] += _as_decimal(row["equity"])
    return [
        EquityHistoryPoint(asOf=as_of, equity=str(aggregated[as_of])) for as_of in ordered_as_of
    ]


async def run_snapshot_sync_monitor() -> None:
    while True:
        monitor_health.begin("account_sync")
        try:
            result = await asyncio.to_thread(sync_venue_snapshots, include_history=False)
            monitor_health.finish(
                "account_sync", None if not result.failed_accounts else "account_read_failed"
            )
        except HTTPException as exc:
            monitor_health.finish("account_sync", f"http_{exc.status_code}")
            if exc.status_code != 409:
                logger.warning("Account snapshot sync failed: http_%s", exc.status_code)
        except Exception as exc:
            monitor_health.finish("account_sync", type(exc).__name__)
            logger.warning("Account snapshot sync failed: %s", type(exc).__name__)
        # Run again after a bounded delay so a transient venue/runtime outage is
        # retried automatically and stale snapshots do not depend on a page visit.
        await asyncio.sleep(SNAPSHOT_SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def snapshot_sync_lifespan(_: FastAPI) -> AsyncIterator[None]:
    # The application owns the monitor lifecycle. Keep this router lifespan as
    # a compatibility no-op for isolated router tests and mounted applications.
    yield


router = APIRouter(prefix=get_settings().api_prefix, lifespan=snapshot_sync_lifespan)


@router.post(
    "/ops/venue-snapshots/sync",
    response_model=VenueSnapshotSyncResponse,
    tags=["live-accounting"],
)
def sync_snapshots() -> VenueSnapshotSyncResponse:
    return sync_venue_snapshots()


@router.post(
    "/ops/venue-snapshots/accounts/{account_id}/sync",
    response_model=VenueSnapshotSyncResponse,
    tags=["live-accounting"],
)
def sync_single_account(account_id: str) -> VenueSnapshotSyncResponse:
    return sync_venue_snapshots(account_id)


@router.get(
    "/ops/venue-snapshots/status",
    response_model=list[AccountSyncStatusResponse],
    tags=["live-accounting"],
)
def sync_statuses() -> list[AccountSyncStatusResponse]:
    return load_sync_statuses()


@router.get(
    "/accounts/{account_id}/equity-history",
    response_model=list[EquityHistoryPoint],
    tags=["live-accounting"],
)
def equity_history(account_id: str, currency: str | None = None) -> list[EquityHistoryPoint]:
    return load_equity_history(account_id, currency)
