from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.journal import connection
from app.models import SubmitOrderCommand

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS demo_order_routes (
    platform_order_id TEXT PRIMARY KEY,
    external_order_id TEXT,
    command_id TEXT NOT NULL UNIQUE,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    adapter TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_demo_order_routes_external
ON demo_order_routes(external_order_id)
WHERE external_order_id IS NOT NULL;
"""


@dataclass(frozen=True)
class DemoOrderRoute:
    platform_order_id: str
    external_order_id: str | None
    command_id: str
    account_id: str
    instrument_id: str
    symbol: str
    adapter: str


def ensure_route_store() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def record_order_route(
    command: SubmitOrderCommand,
    adapter: str,
    external_order_id: str | None,
) -> None:
    ensure_route_store()
    at = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            """
            INSERT INTO demo_order_routes (
                platform_order_id, external_order_id, command_id, account_id,
                instrument_id, symbol, adapter, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(platform_order_id) DO UPDATE SET
                external_order_id = COALESCE(excluded.external_order_id, external_order_id),
                updated_at = excluded.updated_at
            """,
            (
                command.platform_order_id,
                external_order_id,
                command.command_id,
                command.account_id,
                command.instrument_id,
                command.symbol,
                adapter,
                at,
                at,
            ),
        )


def update_external_order_id(platform_order_id: str, external_order_id: str) -> None:
    ensure_route_store()
    with connection() as db:
        db.execute(
            """
            UPDATE demo_order_routes
            SET external_order_id = ?, updated_at = ?
            WHERE platform_order_id = ?
            """,
            (external_order_id, datetime.now(UTC).isoformat(), platform_order_id),
        )


def get_order_route(
    *,
    platform_order_id: str | None = None,
    external_order_id: str | None = None,
) -> DemoOrderRoute | None:
    ensure_route_store()
    if platform_order_id is None and external_order_id is None:
        raise ValueError("platform_order_id or external_order_id is required")
    field = "platform_order_id" if platform_order_id is not None else "external_order_id"
    value = platform_order_id if platform_order_id is not None else external_order_id
    with connection() as db:
        row = db.execute(
            f"SELECT * FROM demo_order_routes WHERE {field} = ?",
            (value,),
        ).fetchone()
    return route_from_row(row) if row is not None else None


def list_routed_accounts(adapter: str | None = None) -> list[str]:
    ensure_route_store()
    where = "WHERE adapter = ?" if adapter is not None else ""
    params = (adapter,) if adapter is not None else ()
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT DISTINCT account_id
            FROM demo_order_routes
            {where}
            ORDER BY account_id
            """,
            params,
        ).fetchall()
    return [row["account_id"] for row in rows]


def route_from_row(row) -> DemoOrderRoute:
    return DemoOrderRoute(
        platform_order_id=row["platform_order_id"],
        external_order_id=row["external_order_id"],
        command_id=row["command_id"],
        account_id=row["account_id"],
        instrument_id=row["instrument_id"],
        symbol=row["symbol"],
        adapter=row["adapter"],
    )
