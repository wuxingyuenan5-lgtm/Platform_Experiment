from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from uuid import uuid4


class MemberHoldingRepositoryError(RuntimeError):
    pass


class MemberHoldingNotFoundError(MemberHoldingRepositoryError):
    pass


class MemberHoldingVersionError(MemberHoldingRepositoryError):
    pass


class FundNotFoundError(MemberHoldingRepositoryError):
    pass


@dataclass(frozen=True, slots=True)
class FundRecord:
    id: str
    name: str
    fund_code: str | None
    base_currency: str


@dataclass(frozen=True, slots=True)
class MemberHoldingRecord:
    id: str
    member_user_id: str
    fund_id: str
    share_quantity: str
    cumulative_invested: str
    confirmed_at: str | None
    as_of: str
    source: str
    status: str
    row_version: int
    updated_by: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class FundNavRecord:
    id: str
    fund_id: str
    valuation_time: str
    unit_nav: str
    currency: str
    source: str
    status: str
    created_at: str


def _fund_from_row(row: sqlite3.Row | None) -> FundRecord | None:
    if row is None:
        return None
    return FundRecord(
        id=str(row["id"]),
        name=str(row["name"]),
        fund_code=str(row["fund_code"]) if row["fund_code"] is not None else None,
        base_currency=str(row["base_currency"]),
    )


def _holding_from_row(row: sqlite3.Row | None) -> MemberHoldingRecord | None:
    if row is None:
        return None
    return MemberHoldingRecord(
        id=str(row["id"]),
        member_user_id=str(row["member_user_id"]),
        fund_id=str(row["fund_id"]),
        share_quantity=str(row["share_quantity"]),
        cumulative_invested=str(row["cumulative_invested"]),
        confirmed_at=str(row["confirmed_at"]) if row["confirmed_at"] is not None else None,
        as_of=str(row["as_of"]),
        source=str(row["source"]),
        status=str(row["status"]),
        row_version=int(row["row_version"]),
        updated_by=str(row["updated_by"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _nav_from_row(row: sqlite3.Row | None) -> FundNavRecord | None:
    if row is None:
        return None
    return FundNavRecord(
        id=str(row["id"]),
        fund_id=str(row["fund_id"]),
        valuation_time=str(row["valuation_time"]),
        unit_nav=str(row["unit_nav"]),
        currency=str(row["currency"]),
        source=str(row["source"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
    )


def list_funds(db: sqlite3.Connection) -> list[FundRecord]:
    rows = db.execute(
        """
        SELECT id, name, fund_code, base_currency
        FROM funds
        ORDER BY name, id
        """
    ).fetchall()
    return [record for row in rows if (record := _fund_from_row(row)) is not None]


def get_fund(db: sqlite3.Connection, fund_id: str) -> FundRecord | None:
    row = db.execute(
        "SELECT id, name, fund_code, base_currency FROM funds WHERE id = ?",
        (fund_id,),
    ).fetchone()
    return _fund_from_row(row)


def update_fund_code(
    db: sqlite3.Connection,
    *,
    fund_id: str,
    fund_code: str,
) -> FundRecord:
    cursor = db.execute("UPDATE funds SET fund_code = ? WHERE id = ?", (fund_code, fund_id))
    if cursor.rowcount != 1:
        raise FundNotFoundError("Fund does not exist")
    updated = get_fund(db, fund_id)
    if updated is None:
        raise FundNotFoundError("Fund does not exist")
    return updated


def list_member_holdings(
    db: sqlite3.Connection,
    member_user_id: str,
) -> list[MemberHoldingRecord]:
    rows = db.execute(
        """
        SELECT * FROM member_fund_holdings
        WHERE member_user_id = ?
        ORDER BY status ASC, updated_at DESC, fund_id ASC
        """,
        (member_user_id,),
    ).fetchall()
    return [record for row in rows if (record := _holding_from_row(row)) is not None]


def get_member_holding(
    db: sqlite3.Connection,
    *,
    member_user_id: str,
    fund_id: str,
) -> MemberHoldingRecord | None:
    row = db.execute(
        """
        SELECT * FROM member_fund_holdings
        WHERE member_user_id = ? AND fund_id = ?
        """,
        (member_user_id, fund_id),
    ).fetchone()
    return _holding_from_row(row)


def get_latest_available_nav(
    db: sqlite3.Connection,
    fund_id: str,
) -> FundNavRecord | None:
    row = db.execute(
        """
        SELECT * FROM fund_nav_snapshots
        WHERE fund_id = ? AND status = 'available'
        ORDER BY valuation_time DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        (fund_id,),
    ).fetchone()
    return _nav_from_row(row)


def upsert_member_holding(
    db: sqlite3.Connection,
    *,
    member_user_id: str,
    fund_id: str,
    share_quantity: str,
    cumulative_invested: str,
    confirmed_at: str | None,
    as_of: str,
    source: str,
    status: str,
    expected_version: int | None,
    updated_by: str,
    now: str,
) -> MemberHoldingRecord:
    existing = get_member_holding(
        db,
        member_user_id=member_user_id,
        fund_id=fund_id,
    )
    if existing is None:
        if expected_version is not None:
            raise MemberHoldingVersionError("Holding does not exist at the expected version")
        holding_id = str(uuid4())
        db.execute(
            """
            INSERT INTO member_fund_holdings (
                id, member_user_id, fund_id, share_quantity,
                cumulative_invested, confirmed_at, as_of, source,
                status, row_version, updated_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                holding_id,
                member_user_id,
                fund_id,
                share_quantity,
                cumulative_invested,
                confirmed_at,
                as_of,
                source,
                status,
                updated_by,
                now,
                now,
            ),
        )
    else:
        if expected_version is None or existing.row_version != expected_version:
            raise MemberHoldingVersionError("Holding was changed by another request")
        cursor = db.execute(
            """
            UPDATE member_fund_holdings
            SET share_quantity = ?, cumulative_invested = ?,
                confirmed_at = ?, as_of = ?, source = ?, status = ?,
                row_version = row_version + 1,
                updated_by = ?, updated_at = ?
            WHERE id = ? AND row_version = ?
            """,
            (
                share_quantity,
                cumulative_invested,
                confirmed_at,
                as_of,
                source,
                status,
                updated_by,
                now,
                existing.id,
                expected_version,
            ),
        )
        if cursor.rowcount != 1:
            raise MemberHoldingVersionError("Holding was changed by another request")
    updated = get_member_holding(
        db,
        member_user_id=member_user_id,
        fund_id=fund_id,
    )
    if updated is None:
        raise MemberHoldingNotFoundError("Holding is unavailable after update")
    return updated


def insert_fund_nav(
    db: sqlite3.Connection,
    *,
    fund_id: str,
    valuation_time: str,
    unit_nav: str,
    currency: str,
    source: str,
    now: str,
) -> FundNavRecord:
    if get_fund(db, fund_id) is None:
        raise FundNotFoundError("Fund does not exist")
    db.execute(
        """
        UPDATE fund_nav_snapshots
        SET status = 'superseded'
        WHERE fund_id = ? AND status = 'available'
        """,
        (fund_id,),
    )
    nav_id = str(uuid4())
    db.execute(
        """
        INSERT INTO fund_nav_snapshots (
            id, fund_id, valuation_time, unit_nav,
            currency, source, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'available', ?)
        """,
        (nav_id, fund_id, valuation_time, unit_nav, currency, source, now),
    )
    created = get_latest_available_nav(db, fund_id)
    if created is None or created.id != nav_id:
        raise MemberHoldingRepositoryError("Fund NAV is unavailable after insert")
    return created
