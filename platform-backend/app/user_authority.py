from __future__ import annotations

import sqlite3

from app.user_repository import count_active_ceos, get_user_by_id


class UserAuthorityError(RuntimeError):
    pass


class LastActiveCeoError(UserAuthorityError):
    pass


def assert_active_ceo_remains(
    db: sqlite3.Connection,
    *,
    target_user_id: str,
    resulting_role: str | None,
    resulting_status: str,
) -> None:
    if not db.in_transaction:
        db.execute("BEGIN IMMEDIATE")
    target = get_user_by_id(db, target_user_id)
    if target is None:
        raise UserAuthorityError("Target user does not exist")
    removes_active_ceo = (
        target.role_code == "ceo"
        and target.lifecycle_status == "active"
        and (resulting_role != "ceo" or resulting_status != "active")
    )
    if removes_active_ceo and count_active_ceos(db) <= 1:
        raise LastActiveCeoError("The last active CEO cannot be disabled or downgraded")
