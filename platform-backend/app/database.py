from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    command_id TEXT NOT NULL UNIQUE,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT,
    status TEXT NOT NULL,
    external_order_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fills (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    UNIQUE(order_id, id),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS positions (
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    net_quantity TEXT NOT NULL,
    average_price TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(account_id, instrument_id)
);

CREATE TABLE IF NOT EXISTS economic_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    order_id TEXT,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pnl_results (
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    realized_pnl TEXT NOT NULL,
    trading_pnl TEXT NOT NULL,
    fees TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(account_id, instrument_id)
);
"""


def database_path() -> Path:
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(database_path())
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_database() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)
