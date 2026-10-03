from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings


def database_path() -> Path:
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    # The platform API and its read-only account workers can legitimately
    # overlap a short writer transaction.  The previous default five-second
    # SQLite wait turned ordinary contention into failed sync jobs and made
    # the service look unavailable.  Keep the existing rollback/commit
    # boundary, but wait long enough for the bounded writer to finish.
    db = sqlite3.connect(database_path(), timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 30000")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def read_only_connection() -> Iterator[sqlite3.Connection]:
    """Open a query-only handle without a commit boundary.

    The local database uses rollback journaling for SQLite-version safety. A
    normal connection can therefore participate in writer lock hand-off even
    for a SELECT followed by the shared connection context's commit. Research
    projections are read-only consumers and should not do that.
    """
    path = database_path()
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only = ON")
    db.execute("PRAGMA busy_timeout = 30000")
    try:
        yield db
    finally:
        db.close()


__all__ = ["connection", "database_path", "read_only_connection"]
