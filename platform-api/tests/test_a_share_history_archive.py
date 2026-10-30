from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

from app.database_bootstrap import bootstrap_database
from app.research_a_share_repository import write_market_archive, write_price_archive
from app.research_provider_choice import choice_daily_close
from app.schema_migrations import apply_migrations
from scripts.import_vibe_a_share_history import _market_record, _price_record


def database() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    bootstrap_database(db)
    apply_migrations(db)
    return db


def test_market_archive_preserves_decimal_and_conflicting_evidence() -> None:
    db = database()
    source = (
        "all_a",
        datetime(2026, 10, 9).date(),
        {
            "total_amount_100m": Decimal("1234567890.123456789"),
            "advance": 3000,
            "decline": 2000,
            "flat": 100,
            "limit_up": 80,
            "limit_down": 10,
            "market_breadth": Decimal("19.6078431372549"),
            "raw_fields": {"AMT": "1234567890.123456789"},
            "source_code": "B_001071",
        },
        "choice-cses-market-history",
    )
    row = _market_record(source)
    assert write_market_archive(row, db=db) == "inserted"
    assert write_market_archive(row, db=db) == "skipped"
    stored = db.execute(
        "SELECT amount_yuan,payload_json FROM research_a_share_market_archive"
    ).fetchone()
    assert stored["amount_yuan"] == "123456789012345678.900000000"
    assert "raw_fields" in stored["payload_json"]

    changed = {**row, "amount_yuan": Decimal("1")}
    assert write_market_archive(changed, db=db) == "conflict"
    conflict = db.execute(
        "SELECT existing_payload_json,incoming_payload_json FROM research_a_share_archive_conflicts"
    ).fetchone()
    assert json.loads(conflict["existing_payload_json"])["amount_yuan"] == stored["amount_yuan"]
    assert json.loads(conflict["incoming_payload_json"])["amount_yuan"] == "1"
    current = db.execute("SELECT amount_yuan FROM research_a_share_market_archive").fetchone()[0]
    assert current == stored["amount_yuan"]


def test_price_archive_keeps_source_identity_and_null_conflict_prices() -> None:
    db = database()
    base = {
        "instrument_code": "BK0448",
        "trade_date": "2026-10-09",
        "close": Decimal("25281.0500000000"),
        "source_name": "东方财富行业板块每日15:05后写入",
        "definition_version": "exact-board-price-v1",
        "industry_level": "eastmoney-board",
        "payload": {"board_code": "BK0448", "conflict": False},
    }
    assert write_price_archive(base, db=db) == "inserted"
    assert write_price_archive(base, db=db) == "skipped"
    second_source = {**base, "source_name": "东方财富行业板块每日15:20写入"}
    assert write_price_archive(second_source, db=db) == "inserted"
    assert db.execute("SELECT COUNT(*) FROM research_a_share_price_history").fetchone()[0] == 2
    assert write_price_archive({**base, "close": Decimal("1")}, db=db) == "conflict"
    conflict = db.execute(
        "SELECT existing_payload_json,incoming_payload_json "
        "FROM research_a_share_archive_conflicts WHERE table_name='price'"
    ).fetchone()
    assert json.loads(conflict["existing_payload_json"])["close"] == "25281.0500000000"
    assert json.loads(conflict["incoming_payload_json"])["close"] == "1"

    innovation = _price_record(
        "BK1106",
        (
            datetime(2026, 10, 9).date(),
            "innovation-v1",
            "eastmoney",
            datetime(2026, 10, 9, 7, 10, tzinfo=UTC),
            {"收盘价": "1512.2600000000", "成交额": "60295035333.0000000000"},
        ),
    )
    assert innovation["close"] == "1512.2600000000"


def test_choice_reference_price_has_independent_instrument_identity() -> None:
    row = _price_record(
        "801102.SWI",
        (datetime(2026, 10, 9).date(), "123.4500", "Choice CSD", datetime.now(UTC)),
    )
    assert row["instrument_code"] == "801102.SWI"
    assert row["close"] == "123.4500"
    assert row["definition_version"] == "choice-csd-daily-close-v1"
    assert row["industry_level"] == "swi-l1"


def test_price_archive_treats_equal_decimal_representations_as_idempotent() -> None:
    db = database()
    base = {
        "instrument_code": "801102.SWI",
        "trade_date": "2026-10-09",
        "close": "8570.5100",
        "source_name": "choice-csd-close-801102.SWI",
        "definition_version": "choice-csd-daily-close-v1",
        "industry_level": "swi-l1",
        "payload": {"close": "8570.5100", "imported": True},
    }
    assert write_price_archive(base, db=db) == "inserted"
    assert (
        write_price_archive(
            {**base, "close": Decimal("8570.51"), "payload": {"close": "8570.51"}}, db=db
        )
        == "skipped"
    )
    assert db.execute("SELECT COUNT(*) FROM research_a_share_archive_conflicts").fetchone()[0] == 0


def test_choice_provider_is_timeout_safe_and_does_not_forward_child_output(
    monkeypatch, tmp_path
) -> None:
    (tmp_path / "EmQuantAPI.py").write_text("# fixture", encoding="utf-8")

    def timeout(*args, **kwargs):
        raise __import__("subprocess").TimeoutExpired(args[0], 1)

    monkeypatch.setattr("app.research_provider_choice.subprocess.run", timeout)
    assert choice_daily_close("2026-10-09", sdk_root=tmp_path, timeout_seconds=1) is None


def test_choice_provider_accepts_choice_slash_date_index(tmp_path) -> None:
    (tmp_path / "EmQuantAPI.py").write_text(
        """import pandas as pd
class Result:
    ErrorCode = 0
class c:
    @staticmethod
    def start(): return Result()
    @staticmethod
    def stop(): return Result()
    @staticmethod
    def css(*args, **kwargs):
        return pd.DataFrame({'DATES':['2026/10/09'],'CLOSE':['8570.51']}, index=['801102.SWI'])
""",
        encoding="utf-8",
    )
    assert choice_daily_close("2026-10-09", sdk_root=tmp_path, timeout_seconds=10) == Decimal(
        "8570.51"
    )
