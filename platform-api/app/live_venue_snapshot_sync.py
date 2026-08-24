from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from sqlite3 import Row
from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import connection
from app.venue_reconciliation import runtime_get

SNAPSHOT_SYNC_INTERVAL_SECONDS = 30.0
SYNC_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS account_sync_status (
    account_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    error_code TEXT,
    last_attempt_at TEXT,
    last_success_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);
"""


class AccountSyncStatusResponse(BaseModel):
    account_id: str = Field(alias="accountId")
    status: str
    error_code: str | None = Field(default=None, alias="errorCode")
    last_attempt_at: str | None = Field(default=None, alias="lastAttemptAt")
    last_success_at: str | None = Field(default=None, alias="lastSuccessAt")
    updated_at: str = Field(alias="updatedAt")


class VenueSnapshotSyncResponse(BaseModel):
    synced_accounts: list[str] = Field(alias="syncedAccounts")
    balance_snapshots: int = Field(alias="balanceSnapshots")
    order_rows: int = Field(alias="orderRows")
    fill_rows: int = Field(alias="fillRows")
    position_rows: int = Field(alias="positionRows")
    pnl_rows: int = Field(alias="pnlRows")
    as_of: str = Field(alias="asOf")


class EquityHistoryPoint(BaseModel):
    asOf: str = Field(alias="asOf")
    equity: str


def ensure_sync_schema() -> None:
    with connection() as db:
        db.executescript(SYNC_SCHEMA_SQL)


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _as_decimal(value: object, *, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return Decimal(str(value))


def _status_row(account_id: str) -> Row | None:
    ensure_sync_schema()
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
    ensure_sync_schema()
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
            ORDER BY a.id
            """
        ).fetchall()
    return [str(row["id"]) for row in rows]


def load_sync_statuses() -> list[AccountSyncStatusResponse]:
    ensure_sync_schema()
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


def _persist_balances(account_id: str, balances: list[dict[str, object]]) -> int:
    written = 0
    with connection() as db:
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
                    str(_as_decimal(balance.get("availableBalance"))),
                    str(balance.get("source") or "runtime"),
                    str(balance.get("dataQualityState") or "complete"),
                    as_of,
                    _iso_now(),
                ),
            )
            written += 1
    return written


def _persist_positions(
    account_id: str,
    positions: list[dict[str, object]],
) -> tuple[int, dict[str, Decimal]]:
    written = 0
    unrealized_by_instrument: dict[str, Decimal] = {}
    with connection() as db:
        db.execute("DELETE FROM positions WHERE account_id = ?", (account_id,))
        for position in positions:
            instrument_id = str(position.get("instrumentId") or "")
            if not instrument_id:
                continue
            unrealized_by_instrument[instrument_id] = _as_decimal(position.get("unrealizedPnl"))
            db.execute(
                """
                INSERT INTO positions (
                    account_id, instrument_id, net_quantity, average_price, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(account_id, instrument_id) DO UPDATE SET
                    net_quantity = excluded.net_quantity,
                    average_price = excluded.average_price,
                    updated_at = excluded.updated_at
                """,
                (
                    account_id,
                    instrument_id,
                    str(_as_decimal(position.get("netQuantity"))),
                    (
                        str(_as_decimal(position.get("averagePrice")))
                        if position.get("averagePrice") not in {None, ""}
                        else None
                    ),
                    str(position.get("asOf") or _iso_now()),
                ),
            )
            written += 1
    return written, unrealized_by_instrument


def _persist_orders(account_id: str, orders: list[dict[str, object]]) -> int:
    written = 0
    with connection() as db:
        for order in orders:
            order_id = str(
                order.get("platformOrderId") or f"external:{order.get('externalOrderId')}"
            )
            instrument_id = str(order.get("instrumentId") or "")
            if not instrument_id:
                continue
            db.execute(
                """
                INSERT OR REPLACE INTO orders (
                    id, command_id, account_id, instrument_id, symbol, side, order_type,
                    quantity, price, status, external_order_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    str(order.get("commandId") or order_id),
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
                ),
            )
            written += 1
    return written


def _persist_fills(
    account_id: str,
    fills: list[dict[str, object]],
) -> tuple[int, dict[str, Decimal], dict[str, Decimal]]:
    written = 0
    fees_by_instrument: dict[str, Decimal] = {}
    realized_by_instrument: dict[str, Decimal] = {}
    with connection() as db:
        for fill in fills:
            fill_id = str(fill.get("externalFillId") or uuid4())
            order_id = str(fill.get("platformOrderId") or f"external:{fill.get('externalOrderId')}")
            instrument_id = str(fill.get("instrumentId") or "")
            if not instrument_id:
                continue
            fee = _as_decimal(fill.get("fee"))
            fees_by_instrument[instrument_id] = (
                fees_by_instrument.get(instrument_id, Decimal("0")) + fee
            )
            db.execute(
                """
                INSERT OR IGNORE INTO fills (
                    id, order_id, account_id, instrument_id, side, quantity, price, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fill_id,
                    order_id,
                    account_id,
                    instrument_id,
                    str(fill.get("side") or "buy"),
                    str(_as_decimal(fill.get("quantity"))),
                    str(_as_decimal(fill.get("price"))),
                    str(fill.get("occurredAt") or _iso_now()),
                ),
            )
            written += 1
    return written, realized_by_instrument, fees_by_instrument


def _persist_pnl(
    account_id: str,
    *,
    unrealized_by_instrument: dict[str, Decimal],
    realized_by_instrument: dict[str, Decimal],
    fees_by_instrument: dict[str, Decimal],
) -> int:
    written = 0
    instrument_ids = (
        set(unrealized_by_instrument)
        | set(realized_by_instrument)
        | set(fees_by_instrument)
    )
    with connection() as db:
        for instrument_id in instrument_ids:
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
                    str(realized_by_instrument.get(instrument_id, Decimal("0"))),
                    str(unrealized_by_instrument.get(instrument_id, Decimal("0"))),
                    str(fees_by_instrument.get(instrument_id, Decimal("0"))),
                    _iso_now(),
                ),
            )
            written += 1
    return written


def _sync_one_account(account_id: str) -> dict[str, int]:
    last_attempt_at = _iso_now()
    _write_status(account_id, status="syncing", error_code=None, last_attempt_at=last_attempt_at)
    try:
        balances = runtime_get("/venue/balances", params={"accountId": account_id}).json()
        positions = runtime_get("/venue/positions", params={"accountId": account_id}).json()
        active_orders = runtime_get(
            "/venue/orders",
            params={"accountId": account_id, "limit": "100"},
        ).json()
        closed_orders = runtime_get(
            "/venue/order-history",
            params={
                "accountId": account_id,
                "scope": "closed",
                "limit": "100",
                "startTime": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
                "endTime": datetime.now(UTC).isoformat(),
            },
        ).json()["items"]
        fills = runtime_get(
            "/venue/fill-history",
            params={
                "accountId": account_id,
                "limit": "200",
                "startTime": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
                "endTime": datetime.now(UTC).isoformat(),
            },
        ).json()["items"]
        runtime_get("/venue/account-risk", params={"accountId": account_id}).json()
    except Exception as exc:
        error_code = getattr(getattr(exc, "response", None), "status_code", None)
        _write_status(
            account_id,
            status="unavailable",
            error_code=f"runtime_{error_code}" if error_code is not None else "runtime_unavailable",
            last_attempt_at=last_attempt_at,
        )
        raise

    balance_count = _persist_balances(account_id, balances)
    position_count, unrealized = _persist_positions(account_id, positions)
    order_count = _persist_orders(account_id, [*active_orders, *closed_orders])
    fill_count, realized, fees = _persist_fills(account_id, fills)
    pnl_count = _persist_pnl(
        account_id,
        unrealized_by_instrument=unrealized,
        realized_by_instrument=realized,
        fees_by_instrument=fees,
    )
    _write_status(
        account_id,
        status="ready",
        error_code=None,
        last_attempt_at=last_attempt_at,
        last_success_at=_iso_now(),
    )
    return {
        "balanceSnapshots": balance_count,
        "orderRows": order_count,
        "fillRows": fill_count,
        "positionRows": position_count,
        "pnlRows": pnl_count,
    }


def sync_venue_snapshots(account_id: str | None = None) -> VenueSnapshotSyncResponse:
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
    for current in account_ids:
        try:
            result = _sync_one_account(current)
        except Exception:
            continue
        synced.append(current)
        for key, value in result.items():
            totals[key] += value
    return VenueSnapshotSyncResponse(
        syncedAccounts=synced,
        balanceSnapshots=totals["balanceSnapshots"],
        orderRows=totals["orderRows"],
        fillRows=totals["fillRows"],
        positionRows=totals["positionRows"],
        pnlRows=totals["pnlRows"],
        asOf=_iso_now(),
    )


def load_equity_history(account_id: str, currency: str | None = None) -> list[EquityHistoryPoint]:
    with connection() as db:
        if currency:
            rows = db.execute(
                """
                SELECT as_of, equity FROM balance_snapshots
                WHERE account_id = ? AND currency = ?
                ORDER BY as_of ASC
                """,
                (account_id, currency),
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT as_of, equity FROM balance_snapshots
                WHERE account_id = ?
                ORDER BY as_of ASC
                """,
                (account_id,),
            ).fetchall()
    if currency:
        return [EquityHistoryPoint(asOf=row["as_of"], equity=str(row["equity"])) for row in rows]
    aggregated: dict[str, Decimal] = {}
    ordered_as_of: list[str] = []
    for row in rows:
        as_of = str(row["as_of"])
        if as_of not in aggregated:
            aggregated[as_of] = Decimal("0")
            ordered_as_of.append(as_of)
        aggregated[as_of] += _as_decimal(row["equity"])
    return [
        EquityHistoryPoint(asOf=as_of, equity=str(aggregated[as_of]))
        for as_of in ordered_as_of
    ]


async def run_snapshot_sync_monitor() -> None:
    while True:
        await asyncio.sleep(SNAPSHOT_SYNC_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(sync_venue_snapshots)
        except Exception:
            pass


@asynccontextmanager
async def snapshot_sync_lifespan(_: FastAPI) -> AsyncIterator[None]:
    ensure_sync_schema()
    task = asyncio.create_task(run_snapshot_sync_monitor())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


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
