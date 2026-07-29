from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.user_repository import ConcurrentUserUpdateError, UserNotFoundError


@dataclass(frozen=True, slots=True)
class AvatarUpdateResult:
    previous_avatar_key: str | None
    avatar_key: str | None
    row_version: int


def update_user_avatar(
    db: sqlite3.Connection,
    *,
    user_id: str,
    avatar_key: str | None,
    expected_version: int,
    now: str,
) -> AvatarUpdateResult:
    row = db.execute(
        "SELECT avatar_key, row_version FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        raise UserNotFoundError("User does not exist")
    if int(row["row_version"]) != expected_version:
        raise ConcurrentUserUpdateError("User profile was changed by another request")
    previous_key = str(row["avatar_key"]) if row["avatar_key"] is not None else None
    cursor = db.execute(
        """
        UPDATE users
        SET avatar_key = ?, row_version = row_version + 1, updated_at = ?
        WHERE id = ? AND row_version = ?
        """,
        (avatar_key, now, user_id, expected_version),
    )
    if cursor.rowcount != 1:
        raise ConcurrentUserUpdateError("User profile was changed by another request")
    return AvatarUpdateResult(
        previous_avatar_key=previous_key,
        avatar_key=avatar_key,
        row_version=expected_version + 1,
    )
