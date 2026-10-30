"""Isolated research storage. Explicit offline cutover preserves the legacy source."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app import database_connection as business
from app.config import get_settings


def database_path():
    value = get_settings().strategy_research_database_path
    return Path(value).resolve() if value else business.database_path()


@contextmanager
def connection():
    path = database_path().resolve()
    # Never silently create an empty research history on a misspelled cutover path.
    db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA synchronous=FULL")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def read_only_connection():
    db = sqlite3.connect(database_path().resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    try:
        yield db
    finally:
        db.close()


def migrate(source, destination):
    """Run while API writers are stopped; atomic destination publication, no source deletion."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    pending = destination.with_suffix(".pending")
    if pending.exists():
        raise FileExistsError(pending)
    db = sqlite3.connect(pending.as_uri(), uri=True)
    try:
        db.execute("ATTACH DATABASE ? AS legacy", (source.as_uri() + "?mode=ro",))
        objects = db.execute(
            "SELECT type,name,tbl_name,sql FROM legacy.sqlite_master "
            "WHERE (tbl_name LIKE 'research_strategy_%' "
            "OR tbl_name='funding_basis_projection_cursor') "
            "AND sql IS NOT NULL ORDER BY type DESC"
        ).fetchall()
        counts = {}
        for kind, name, _table, sql in objects:
            if kind != "table":
                continue
            db.execute(sql)
            columns = "rowid,*" if name == "research_strategy_parts" else "*"
            db.execute(
                f'INSERT INTO main."{name}" SELECT {columns} FROM legacy."{name}"'
                if columns == "*"
                else f'INSERT INTO main."{name}"(rowid,'
                + ",".join(
                    '"' + row[1] + '"' for row in db.execute(f'PRAGMA legacy.table_info("{name}")')
                )
                + f') SELECT rowid,* FROM legacy."{name}"'
            )
            count = db.execute(f'SELECT COUNT(*) FROM main."{name}"').fetchone()[0]
            assert count == db.execute(f'SELECT COUNT(*) FROM legacy."{name}"').fetchone()[0]
            counts[name] = count
        for kind, _name, _table, sql in objects:
            if kind == "index":
                db.execute(sql)
        db.commit()
        if db.execute("PRAGMA main.quick_check").fetchone()[0] != "ok":
            raise ValueError("research copy integrity failed")
    finally:
        db.close()
    pending.replace(destination)
    return counts
