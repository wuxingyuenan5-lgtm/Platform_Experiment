from __future__ import annotations

from sqlite3 import Row

from app.database import connection


def get_position_row(account_id: str, instrument_id: str) -> Row | None:
    with connection() as db:
        return db.execute(
            """
            SELECT account_id, instrument_id, net_quantity, average_price
            FROM positions
            WHERE account_id = ? AND instrument_id = ?
            """,
            (account_id, instrument_id),
        ).fetchone()


def get_pnl_row(account_id: str, instrument_id: str) -> Row | None:
    with connection() as db:
        return db.execute(
            """
            SELECT account_id, instrument_id, realized_pnl, trading_pnl, fees
            FROM pnl_results
            WHERE account_id = ? AND instrument_id = ?
            """,
            (account_id, instrument_id),
        ).fetchone()
