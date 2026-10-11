"""One-time, resume-safe import of verified Vibe A-share history.

The source URL is read from Vibe's existing launcher and is never printed or
persisted. PostgreSQL is held in a repeatable-read, read-only transaction;
SQLite batches commit independently so reruns continue from natural keys.
"""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.database import initialize_database
from app.database_connection import connection
from app.research_a_share_repository import (
    archive_a_share_audit,
    write_market_archive,
    write_price_archive,
)

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CMD = Path(
    r"C:\Users\jiuxi\Desktop\codex\vibe_research-main\windows\vibe-backend.cmd"
)
DEFAULT_LOG = PLATFORM_ROOT / "platform-api" / "data" / "import-vibe-a-share-history.log"


def read_database_url(path: Path = DEFAULT_CMD) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(
        r'^\s*(?:set\s+)?"?VR_DATABASE_URL\s*=\s*(.*?)"?\s*$',
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not match or not match.group(1).strip():
        raise RuntimeError("VR_DATABASE_URL_not_found")
    return match.group(1).strip().strip('"')


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def _append_log(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"at": datetime.now(UTC).isoformat(), **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=_json_default) + "\n")


def _batches(rows: Iterable[Any], size: int) -> Iterable[list[Any]]:
    batch: list[Any] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _market_record(row: tuple[Any, ...]) -> dict[str, Any]:
    universe, trade_date, payload, source_name = row
    payload = dict(payload or {})
    amount_100m = payload.get("total_amount_100m")
    amount_yuan = (
        Decimal(str(amount_100m)) * Decimal("100000000")
        if amount_100m is not None
        else None
    )
    return {
        "universe_key": str(universe),
        "trade_date": trade_date,
        "amount_yuan": amount_yuan,
        "up": payload.get("advance"),
        "down": payload.get("decline"),
        "flat": payload.get("flat"),
        "limit_up": payload.get("limit_up"),
        "limit_down": payload.get("limit_down"),
        "market_breadth_pct": payload.get("market_breadth"),
        "source_name": str(source_name or payload.get("snapshot_source") or ""),
        "definition_version": str(payload.get("source_code") or "historical-archive-v1"),
        "payload": payload,
    }


def _price_record(kind: str, row: tuple[Any, ...]) -> dict[str, Any]:
    if kind in {"000300.SH", "801102.SWI"}:
        trade_date, close, source_name, ingested_at = row
        return {
            "instrument_code": kind,
            "trade_date": trade_date,
            "close": close,
            "source_name": str(source_name),
            "definition_version": (
                "choice-csd-daily-close-v1" if kind == "801102.SWI" else "daily-close-v1"
            ),
            "industry_level": "swi-l1" if kind == "801102.SWI" else "",
            "payload": {
                "symbol": kind,
                "trade_date": trade_date,
                "close": close,
                "source_name": source_name,
                "ingested_at": ingested_at,
            },
        }
    if kind == "BK0448":
        trade_date, code, level, definition, source_name, ingested_at, payload = row
        payload = dict(payload or {})
        conflicted = bool(payload.get("conflict"))
        return {
            "instrument_code": str(code),
            "trade_date": trade_date,
            "close": None if conflicted else payload.get("close"),
            "source_name": str(source_name),
            "definition_version": str(definition),
            "industry_level": str(level),
            "quality_status": "conflict" if conflicted else "ready",
            "payload": {**payload, "ingested_at": ingested_at},
        }
    trade_date, definition, source_name, ingested_at, payload = row
    payload = dict(payload or {})
    return {
        "instrument_code": "BK1106",
        "trade_date": trade_date,
        "close": payload.get("收盘价"),
        "source_name": str(source_name),
        "definition_version": str(definition),
        "industry_level": "eastmoney-board",
        "payload": {**payload, "ingested_at": ingested_at},
    }


def import_history(*, source_url: str, batch_size: int = 100) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch_size_must_be_positive")
    initialize_database()
    import psycopg
    from psycopg.types.json import set_json_loads

    counts: dict[str, Any] = {"inserted": 0, "skipped": 0, "conflict": 0}
    with psycopg.connect(source_url, autocommit=False) as source:
        set_json_loads(lambda value: json.loads(value, parse_float=Decimal), context=source)
        source.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        queries = (
            (
                "market",
                """SELECT universe_key,trade_date,payload,source_name
                FROM public.market_history_archive
                WHERE universe_key IN ('all_a','sh_sz_a')
                ORDER BY universe_key,trade_date""",
            ),
            (
                "000300.SH",
                """SELECT trade_date,close,source_name,ingested_at
                FROM public.market_benchmark_daily
                WHERE symbol='000300.SH' ORDER BY trade_date""",
            ),
            (
                "801102.SWI",
                """SELECT trade_date,close,source_name,ingested_at
                FROM public.market_benchmark_daily
                WHERE symbol='801102.SWI' ORDER BY trade_date""",
            ),
            (
                "BK0448",
                """SELECT trade_date,industry_code,industry_level,definition_version,
                source_name,ingested_at,payload FROM public.industry_daily_snapshots
                WHERE industry_code='BK0448' AND industry_level='eastmoney-board'
                  AND definition_version='exact-board-price-v1'
                ORDER BY trade_date,source_name""",
            ),
            (
                "BK1106",
                """SELECT trade_date,definition_version,source_name,ingested_at,payload
                FROM public.innovation_drug_daily ORDER BY trade_date,source_name""",
            ),
        )
        for kind, query in queries:
            with source.cursor() as cursor:
                cursor.execute(query)
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    with connection() as target:
                        for raw in rows:
                            result = (
                                write_market_archive(_market_record(raw), db=target)
                                if kind == "market"
                                else write_price_archive(_price_record(kind, raw), db=target)
                            )
                            counts[result] += 1
    counts["audit"] = archive_a_share_audit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd", type=Path, default=DEFAULT_CMD)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args()
    try:
        result = import_history(
            source_url=read_database_url(args.cmd),
            batch_size=args.batch_size,
        )
    except Exception as exc:
        _append_log(args.log, {"status": "error", "error": type(exc).__name__})
        raise
    _append_log(args.log, {"status": "complete", **result})
    print(json.dumps(result, ensure_ascii=False, default=_json_default))


if __name__ == "__main__":
    main()
