from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.cross_spread import get_bybit_account_id, get_mt5_account_id
from app.database import connection
from app.venue_reconciliation import runtime_get

SNAPSHOT_SYNC_INTERVAL_SECONDS = 30.0


class VenueSnapshotSyncResponse(BaseModel):
    synced_accounts: list[str] = Field(alias="syncedAccounts")
    balance_snapshots: int = Field(alias="balanceSnapshots")
    pnl_rows: int = Field(alias="pnlRows")
    as_of: str = Field(alias="asOf")


class EquityHistoryPoint(BaseModel):
    asOf: str = Field(alias="asOf")
    equity: str


def _optional_decimal(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def sync_venue_balances() -> int:
    now = datetime.now(UTC).isoformat()
    written = 0
    with connection() as db:
        for account_id in (get_bybit_account_id(), get_mt5_account_id()):
            response = runtime_get("/venue/balances", params={"accountId": account_id})
            response.raise_for_status()
            balances = response.json()
            for balance in balances:
                db.execute(
                    """
                    INSERT INTO balance_snapshots (
                        id, account_id, currency, equity, available_balance,
                        source, data_quality_state, as_of, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        str(balance.get("accountId") or account_id),
                        str(balance.get("currency") or "USD"),
                        str(_optional_decimal(balance.get("equity"))),
                        str(_optional_decimal(balance.get("availableBalance"))),
                        str(balance.get("source") or "runtime"),
                        str(balance.get("dataQualityState") or "complete"),
                        str(balance.get("asOf") or now),
                        now,
                    ),
                )
                written += 1
    return written


def sync_venue_pnl() -> int:
    now = datetime.now(UTC).isoformat()
    written = 0
    with connection() as db:
        for account_id in (get_bybit_account_id(), get_mt5_account_id()):
            response = runtime_get("/venue/positions", params={"accountId": account_id})
            response.raise_for_status()
            positions = response.json()
            for position in positions:
                instrument_id = position.get("instrumentId")
                if not instrument_id:
                    continue
                unrealized = _optional_decimal(position.get("unrealizedPnl"))
                existing = db.execute(
                    """
                    SELECT realized_pnl, fees FROM pnl_results
                    WHERE account_id = ? AND instrument_id = ?
                    """,
                    (account_id, instrument_id),
                ).fetchone()
                realized = (
                    Decimal(str(existing["realized_pnl"])) if existing else Decimal("0")
                )
                fees = Decimal(str(existing["fees"])) if existing else Decimal("0")
                db.execute(
                    """
                    INSERT INTO pnl_results (
                        account_id, instrument_id, realized_pnl, trading_pnl, fees, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(account_id, instrument_id) DO UPDATE SET
                        trading_pnl = excluded.trading_pnl,
                        updated_at = excluded.updated_at
                    """,
                    (
                        account_id,
                        instrument_id,
                        str(realized),
                        str(unrealized),
                        str(fees),
                        now,
                    ),
                )
                written += 1
    return written


def sync_venue_snapshots() -> VenueSnapshotSyncResponse:
    account_ids = (get_bybit_account_id(), get_mt5_account_id())
    balance_count = sync_venue_balances()
    pnl_count = sync_venue_pnl()
    return VenueSnapshotSyncResponse(
        syncedAccounts=list(account_ids),
        balanceSnapshots=balance_count,
        pnlRows=pnl_count,
        asOf=datetime.now(UTC).isoformat(),
    )


def load_equity_history(
    account_id: str,
    currency: str | None = None,
) -> list[EquityHistoryPoint]:
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
        return [
            EquityHistoryPoint(asOf=row["as_of"], equity=str(row["equity"]))
            for row in rows
        ]

    aggregated: dict[str, Decimal] = {}
    ordered_as_of: list[str] = []
    for row in rows:
        as_of = str(row["as_of"])
        if as_of not in aggregated:
            aggregated[as_of] = Decimal("0")
            ordered_as_of.append(as_of)
        aggregated[as_of] += _optional_decimal(row["equity"])
    return [
        EquityHistoryPoint(asOf=as_of, equity=str(aggregated[as_of]))
        for as_of in ordered_as_of
    ]


async def run_snapshot_sync_monitor() -> None:
    while True:
        try:
            await asyncio.to_thread(sync_venue_snapshots)
        except Exception:
            pass
        await asyncio.sleep(SNAPSHOT_SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def snapshot_sync_lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(run_snapshot_sync_monitor())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


router = APIRouter(
    prefix=get_settings().api_prefix,
    lifespan=snapshot_sync_lifespan,
)


@router.post(
    "/ops/venue-snapshots/sync",
    response_model=VenueSnapshotSyncResponse,
    tags=["live-accounting"],
)
def sync_snapshots() -> VenueSnapshotSyncResponse:
    return sync_venue_snapshots()


@router.get(
    "/accounts/{account_id}/equity-history",
    response_model=list[EquityHistoryPoint],
    tags=["live-accounting"],
)
def equity_history(
    account_id: str,
    currency: str | None = None,
) -> list[EquityHistoryPoint]:
    return load_equity_history(account_id, currency)
