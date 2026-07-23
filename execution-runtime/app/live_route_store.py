from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.journal import connection
from app.models import SubmitOrderCommand

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS live_order_routes (
    platform_order_id TEXT PRIMARY KEY,
    external_order_id TEXT,
    external_client_id TEXT NOT NULL UNIQUE,
    command_id TEXT NOT NULL UNIQUE,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    adapter TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_live_order_routes_external
ON live_order_routes(external_order_id)
WHERE external_order_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS live_write_claims (
    command_id TEXT PRIMARY KEY,
    platform_order_id TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    adapter TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    notional TEXT NOT NULL,
    business_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_live_write_claims_daily
ON live_write_claims(business_date, account_id, adapter);
"""


@dataclass(frozen=True)
class LiveOrderRoute:
    platform_order_id: str
    external_order_id: str | None
    external_client_id: str
    command_id: str
    strategy_instance_id: str
    account_id: str
    instrument_id: str
    symbol: str
    adapter: str


@dataclass(frozen=True)
class LiveWriteClaim:
    command_id: str
    notional: Decimal
    already_claimed: bool


def ensure_live_store() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def stable_external_client_id(prefix: str, platform_order_id: str, length: int = 30) -> str:
    digest = hashlib.sha256(platform_order_id.encode("utf-8")).hexdigest()
    return f"{prefix}{digest}"[:length]


def record_order_route(
    command: SubmitOrderCommand,
    adapter: str,
    external_client_id: str,
    external_order_id: str | None = None,
) -> None:
    ensure_live_store()
    if command.strategy_instance_id is None:
        raise ValueError("Live order route requires strategy_instance_id")
    at = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            """
            INSERT INTO live_order_routes (
                platform_order_id, external_order_id, external_client_id, command_id,
                strategy_instance_id, account_id, instrument_id, symbol, adapter,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform_order_id) DO UPDATE SET
                external_order_id = COALESCE(excluded.external_order_id, external_order_id),
                updated_at = excluded.updated_at
            """,
            (
                command.platform_order_id,
                external_order_id,
                external_client_id,
                command.command_id,
                command.strategy_instance_id,
                command.account_id,
                command.instrument_id,
                command.symbol.upper(),
                adapter,
                at,
                at,
            ),
        )


def update_external_order_id(platform_order_id: str, external_order_id: str) -> None:
    ensure_live_store()
    with connection() as db:
        db.execute(
            """
            UPDATE live_order_routes
            SET external_order_id = ?, updated_at = ?
            WHERE platform_order_id = ?
            """,
            (external_order_id, datetime.now(UTC).isoformat(), platform_order_id),
        )


def get_order_route(
    *,
    platform_order_id: str | None = None,
    external_order_id: str | None = None,
    external_client_id: str | None = None,
) -> LiveOrderRoute | None:
    ensure_live_store()
    filters = {
        "platform_order_id": platform_order_id,
        "external_order_id": external_order_id,
        "external_client_id": external_client_id,
    }
    selected = [(field, value) for field, value in filters.items() if value is not None]
    if len(selected) != 1:
        raise ValueError("Exactly one live order identity is required")
    field, value = selected[0]
    with connection() as db:
        row = db.execute(
            f"SELECT * FROM live_order_routes WHERE {field} = ?",
            (value,),
        ).fetchone()
    return route_from_row(row) if row is not None else None


def claim_live_write(
    command: SubmitOrderCommand,
    adapter: str,
    notional: Decimal,
    max_daily_notional: Decimal,
) -> LiveWriteClaim:
    ensure_live_store()
    if command.strategy_instance_id is None:
        raise ValueError("Live write requires strategy_instance_id")
    normalized = {
        "commandId": command.command_id,
        "platformOrderId": command.platform_order_id,
        "strategyInstanceId": command.strategy_instance_id,
        "accountId": command.account_id,
        "instrumentId": command.instrument_id,
        "symbol": command.symbol.upper(),
        "side": command.side,
        "orderType": command.order_type,
        "quantity": format(command.quantity, "f"),
        "price": format(command.price, "f") if command.price is not None else None,
        "reduceOnly": command.reduce_only,
        "adapter": adapter,
        "notional": format(notional, "f"),
    }
    payload_hash = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    now = datetime.now(UTC)
    business_date = now.date().isoformat()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM live_write_claims WHERE command_id = ?",
            (command.command_id,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise ValueError("Live command identity was reused with a different payload")
            return LiveWriteClaim(
                command_id=command.command_id,
                notional=Decimal(existing["notional"]),
                already_claimed=True,
            )
        daily = db.execute(
            """
            SELECT COALESCE(SUM(CAST(notional AS REAL)), 0) AS total
            FROM live_write_claims
            WHERE business_date = ? AND account_id = ? AND adapter = ?
            """,
            (business_date, command.account_id, adapter),
        ).fetchone()
        daily_total = Decimal(str(daily["total"]))
        if daily_total + notional > max_daily_notional:
            raise ValueError("Live daily notional limit would be exceeded")
        db.execute(
            """
            INSERT INTO live_write_claims (
                command_id, platform_order_id, payload_hash, adapter,
                strategy_instance_id, account_id, symbol, notional,
                business_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command.command_id,
                command.platform_order_id,
                payload_hash,
                adapter,
                command.strategy_instance_id,
                command.account_id,
                command.symbol.upper(),
                format(notional, "f"),
                business_date,
                now.isoformat(),
            ),
        )
    return LiveWriteClaim(
        command_id=command.command_id,
        notional=notional,
        already_claimed=False,
    )


def route_from_row(row) -> LiveOrderRoute:
    return LiveOrderRoute(
        platform_order_id=row["platform_order_id"],
        external_order_id=row["external_order_id"],
        external_client_id=row["external_client_id"],
        command_id=row["command_id"],
        strategy_instance_id=row["strategy_instance_id"],
        account_id=row["account_id"],
        instrument_id=row["instrument_id"],
        symbol=row["symbol"],
        adapter=row["adapter"],
    )
