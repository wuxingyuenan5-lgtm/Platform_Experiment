from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "platform-backend"
APP = BACKEND / "app"
TESTS = BACKEND / "tests"
sys.path.insert(0, str(BACKEND))

from app import venue_reconciliation as legacy  # noqa: E402

DDL_SHA256 = hashlib.sha256(legacy.SCHEMA_SQL.encode("utf-8")).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise SystemExit(f"expected exactly one match in {path}: {old[:100]!r}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


(APP / "venue_reconciliation_repository.py").write_text(
    '''from __future__ import annotations

import json
from datetime import UTC, datetime
from sqlite3 import Row
from uuid import uuid4

from app.database import connection
from app.venue_reconciliation_schemas import (
    DifferenceType,
    ReconciliationDifferenceResponse,
    VenueReconciliationRunResponse,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS venue_reconciliation_runs (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    run_type TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    order_count INTEGER NOT NULL,
    fill_count INTEGER NOT NULL,
    position_count INTEGER NOT NULL,
    balance_count INTEGER NOT NULL,
    fact_count INTEGER NOT NULL,
    difference_count INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS reconciliation_differences (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    difference_key TEXT NOT NULL,
    difference_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    local_reference TEXT,
    external_reference TEXT,
    local_value_json TEXT NOT NULL,
    external_value_json TEXT NOT NULL,
    status TEXT NOT NULL,
    resolution_actor TEXT,
    resolution_reason TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, difference_key),
    FOREIGN KEY(run_id) REFERENCES venue_reconciliation_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_runs_account
ON venue_reconciliation_runs(account_id, started_at);

CREATE INDEX IF NOT EXISTS idx_reconciliation_differences_run
ON reconciliation_differences(run_id, status, difference_type);
"""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def audit(event_type: str, subject_type: str, subject_id: str, details: dict[str, object]) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                event_type,
                subject_type,
                subject_id,
                json.dumps(details, ensure_ascii=False, sort_keys=True, default=str),
                now_iso(),
            ),
        )


def load_strategy_instance_id_for_command(command_id: str) -> str | None:
    with connection() as db:
        row = db.execute(
            "SELECT strategy_instance_id FROM trade_commands WHERE id = ?",
            (command_id,),
        ).fetchone()
    return row["strategy_instance_id"] if row is not None else None


def update_order_from_external(
    order_id: str,
    status: str,
    external_order_id: object,
    updated_at: object,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE orders
            SET status = ?, external_order_id = ?, updated_at = ?
            WHERE id = ? AND status != 'filled'
            """,
            (status, external_order_id, updated_at, order_id),
        )


def list_fill_quantities(order_id: str) -> list[object]:
    with connection() as db:
        rows = db.execute(
            "SELECT quantity FROM fills WHERE order_id = ?",
            (order_id,),
        ).fetchall()
    return [row["quantity"] for row in rows]


def ensure_standalone_order_run(
    *,
    order_id: str,
    run_id: str,
    payload_hash: str,
    started_at: str,
    completed_at: str,
) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            )
            SELECT ?, ?, ?, tc.strategy_instance_id, o.account_id, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            FROM orders o JOIN trade_commands tc ON tc.id = o.command_id
            WHERE o.id = ?
            """,
            (
                run_id,
                run_id,
                payload_hash,
                "order",
                "runtime",
                "completed_with_differences",
                1,
                0,
                0,
                0,
                0,
                1,
                started_at,
                completed_at,
                order_id,
            ),
        )


def load_run_by_idempotency_key(idempotency_key: str) -> Row | None:
    with connection() as db:
        return db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()


def create_account_snapshot_run(
    *,
    run_id: str,
    idempotency_key: str,
    payload_hash: str,
    strategy_instance_id: str,
    account_id: str,
    source: str,
    position_count: int,
    balance_count: int,
    started_at: str,
) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                idempotency_key,
                payload_hash,
                strategy_instance_id,
                account_id,
                "account_snapshot",
                source,
                "processing",
                0,
                0,
                position_count,
                balance_count,
                0,
                0,
                started_at,
                None,
            ),
        )


def complete_account_snapshot_run(
    *,
    run_id: str,
    status: str,
    fact_count: int,
    difference_count: int,
    completed_at: str,
) -> Row:
    with connection() as db:
        db.execute(
            """
            UPDATE venue_reconciliation_runs
            SET status = ?, fact_count = ?, difference_count = ?, completed_at = ?
            WHERE id = ?
            """,
            (status, fact_count, difference_count, completed_at, run_id),
        )
        row = db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    assert row is not None
    return row


def has_active_strategy_account(strategy_instance_id: str, account_id: str) -> bool:
    with connection() as db:
        row = db.execute(
            """
            SELECT sab.id
            FROM strategy_account_bindings sab
            JOIN strategy_instances si ON si.id = sab.strategy_instance_id
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.strategy_instance_id = ? AND sab.account_id = ?
              AND sab.status = 'active' AND si.status = 'active' AND a.status = 'active'
            """,
            (strategy_instance_id, account_id),
        ).fetchone()
    return row is not None


def load_comparison_position(
    strategy_instance_id: str,
    account_id: str,
    instrument_id: object,
) -> dict[str, object] | None:
    with connection() as db:
        row = db.execute(
            """
            SELECT net_quantity, average_price
            FROM formal_positions
            WHERE strategy_instance_id = ? AND account_id = ? AND instrument_id = ?
            """,
            (strategy_instance_id, account_id, instrument_id),
        ).fetchone()
        if row is None:
            row = db.execute(
                """
                SELECT net_quantity, average_price
                FROM positions
                WHERE account_id = ? AND instrument_id = ?
                """,
                (account_id, instrument_id),
            ).fetchone()
    return dict(row) if row is not None else None


def load_latest_balance(account_id: str) -> dict[str, object] | None:
    with connection() as db:
        row = db.execute(
            """
            SELECT equity, available_balance, currency
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC, created_at DESC
            LIMIT 1
            """,
            (account_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def store_difference(
    run_id: str,
    difference_key: str,
    difference_type: DifferenceType,
    entity_type: str,
    local_reference: str | None,
    external_reference: str | None,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> str:
    difference_id = str(uuid4())
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO reconciliation_differences (
                id, run_id, difference_key, difference_type, entity_type,
                local_reference, external_reference, local_value_json,
                external_value_json, status, resolution_actor, resolution_reason,
                resolved_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                difference_id,
                run_id,
                difference_key,
                difference_type,
                entity_type,
                local_reference,
                external_reference,
                json.dumps(local_value, sort_keys=True, default=str),
                json.dumps(external_value, sort_keys=True, default=str),
                "open",
                None,
                None,
                None,
                now_iso(),
            ),
        )
        row = db.execute(
            """
            SELECT id FROM reconciliation_differences
            WHERE run_id = ? AND difference_key = ?
            """,
            (run_id, difference_key),
        ).fetchone()
    assert row is not None
    return row["id"]


def load_run(run_id: str) -> Row | None:
    with connection() as db:
        return db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()


def list_difference_rows(run_id: str) -> list[Row]:
    with connection() as db:
        return db.execute(
            """
            SELECT * FROM reconciliation_differences
            WHERE run_id = ? ORDER BY created_at, difference_key
            """,
            (run_id,),
        ).fetchall()


def resolve_difference_row(
    *,
    difference_id: str,
    status: str,
    actor: str,
    reason: str,
    resolved_at: str,
) -> tuple[Row | None, bool]:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM reconciliation_differences WHERE id = ?",
            (difference_id,),
        ).fetchone()
        if row is None or row["status"] != "open":
            return row, False
        db.execute(
            """
            UPDATE reconciliation_differences
            SET status = ?, resolution_actor = ?, resolution_reason = ?, resolved_at = ?
            WHERE id = ?
            """,
            (status, actor, reason, resolved_at, difference_id),
        )
        row = db.execute(
            "SELECT * FROM reconciliation_differences WHERE id = ?",
            (difference_id,),
        ).fetchone()
    assert row is not None
    return row, True


def run_from_row(row: Row) -> VenueReconciliationRunResponse:
    return VenueReconciliationRunResponse(
        runId=row["id"],
        idempotencyKey=row["idempotency_key"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        runType=row["run_type"],
        source=row["source"],
        status=row["status"],
        orderCount=row["order_count"],
        fillCount=row["fill_count"],
        positionCount=row["position_count"],
        balanceCount=row["balance_count"],
        factCount=row["fact_count"],
        differenceCount=row["difference_count"],
        startedAt=row["started_at"],
        completedAt=row["completed_at"],
    )


def difference_from_row(row: Row) -> ReconciliationDifferenceResponse:
    return ReconciliationDifferenceResponse(
        differenceId=row["id"],
        runId=row["run_id"],
        differenceKey=row["difference_key"],
        differenceType=row["difference_type"],
        entityType=row["entity_type"],
        localReference=row["local_reference"],
        externalReference=row["external_reference"],
        localValue=json.loads(row["local_value_json"]),
        externalValue=json.loads(row["external_value_json"]),
        status=row["status"],
        resolutionActor=row["resolution_actor"],
        resolutionReason=row["resolution_reason"],
        resolvedAt=row["resolved_at"],
        createdAt=row["created_at"],
    )
''',
    encoding="utf-8",
)

venue = APP / "venue_reconciliation.py"
replace_once(venue, "from app.database import connection\n", "")
replace_once(
    venue,
    "from app.financial_facts import CreateFinancialFactRequest, record_financial_fact\n",
    "from app import venue_reconciliation_repository as repository\n"
    "from app.financial_facts import CreateFinancialFactRequest, record_financial_fact\n",
)
start = venue.read_text(encoding="utf-8").index('SCHEMA_SQL = """')
end = venue.read_text(encoding="utf-8").index("\n\ndef now_iso()", start)
content = venue.read_text(encoding="utf-8")
content = content[:start] + '''SCHEMA_SQL = repository.SCHEMA_SQL
ensure_schema = repository.ensure_schema
audit = repository.audit
create_difference = repository.store_difference
run_from_row = repository.run_from_row
difference_from_row = repository.difference_from_row
''' + content[end:]
venue.write_text(content, encoding="utf-8")
replace_once(
    venue,
    '''\n\ndef ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)
''',
    "",
)
replace_once(
    venue,
    '''\n\ndef audit(event_type: str, subject_type: str, subject_id: str, details: dict[str, object]) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                event_type,
                subject_type,
                subject_id,
                json.dumps(details, ensure_ascii=False, sort_keys=True, default=str),
                now_iso(),
            ),
        )
''',
    "",
)
replace_once(
    venue,
    '''def strategy_for_order(order_row) -> str:
    with connection() as db:
        row = db.execute(
            "SELECT strategy_instance_id FROM trade_commands WHERE id = ?",
            (order_row["command_id"],),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=422,
            detail="Order has no authoritative StrategyInstance and cannot enter formal reconciliation",
        )
    return row["strategy_instance_id"]
''',
    '''def strategy_for_order(order_row) -> str:
    strategy_instance_id = repository.load_strategy_instance_id_for_command(
        order_row["command_id"]
    )
    if strategy_instance_id is None:
        raise HTTPException(
            status_code=422,
            detail="Order has no authoritative StrategyInstance and cannot enter formal reconciliation",
        )
    return strategy_instance_id
''',
)
replace_once(
    venue,
    '''    with connection() as db:
        db.execute(
            """
            UPDATE orders
            SET status = ?, external_order_id = ?, updated_at = ?
            WHERE id = ? AND status != 'filled'
            """,
            (
                local_status,
                external_order["externalOrderId"],
                external_order["asOf"],
                row["id"],
            ),
        )
''',
    '''    repository.update_order_from_external(
        row["id"],
        local_status,
        external_order["externalOrderId"],
        external_order["asOf"],
    )
''',
)
replace_once(
    venue,
    '''    with connection() as db:
        local_fill_rows = db.execute(
            "SELECT quantity FROM fills WHERE order_id = ?",
            (order_id,),
        ).fetchall()
    drafts = order_difference_drafts(
        order_id=order_id,
        local_status=local_row["status"],
        local_fill_quantities=[row["quantity"] for row in local_fill_rows],
''',
    '''    drafts = order_difference_drafts(
        order_id=order_id,
        local_status=local_row["status"],
        local_fill_quantities=repository.list_fill_quantities(order_id),
''',
)
old_standalone_sql = '''    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            )
            SELECT ?, ?, ?, tc.strategy_instance_id, o.account_id, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            FROM orders o JOIN trade_commands tc ON tc.id = o.command_id
            WHERE o.id = ?
            """,
            (
                run_id,
                run_id,
                canonical_hash({"orderId": order_id}),
                "order",
                "runtime",
                "completed_with_differences",
                1,
                0,
                0,
                0,
                0,
                1,
                at,
                at,
                order_id,
            ),
        )
'''
replace_once(
    venue,
    old_standalone_sql,
    '''    repository.ensure_standalone_order_run(
        order_id=order_id,
        run_id=run_id,
        payload_hash=canonical_hash({"orderId": order_id}),
        started_at=at,
        completed_at=at,
    )
''',
)
replace_once(
    venue,
    '''    with connection() as db:
        existing = db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Reconciliation idempotency key was reused with a different payload",
                )
            return run_from_row(existing)
''',
    '''    existing = repository.load_run_by_idempotency_key(request.idempotency_key)
    if existing is not None:
        if existing["payload_hash"] != payload_hash:
            raise HTTPException(
                status_code=409,
                detail="Reconciliation idempotency key was reused with a different payload",
            )
        return run_from_row(existing)
''',
)
old_create_run = '''    with connection() as db:
        db.execute(
            """
            INSERT INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                request.idempotency_key,
                payload_hash,
                request.strategy_instance_id,
                request.account_id,
                "account_snapshot",
                source,
                "processing",
                0,
                0,
                len(positions),
                len(balances),
                0,
                0,
                started_at,
                None,
            ),
        )
'''
replace_once(
    venue,
    old_create_run,
    '''    repository.create_account_snapshot_run(
        run_id=run_id,
        idempotency_key=request.idempotency_key,
        payload_hash=payload_hash,
        strategy_instance_id=request.strategy_instance_id,
        account_id=request.account_id,
        source=source,
        position_count=len(positions),
        balance_count=len(balances),
        started_at=started_at,
    )
''',
)
old_complete = '''    with connection() as db:
        db.execute(
            """
            UPDATE venue_reconciliation_runs
            SET status = ?, fact_count = ?, difference_count = ?, completed_at = ?
            WHERE id = ?
            """,
            (status, fact_count, len(difference_ids), completed_at, run_id),
        )
        row = db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
'''
replace_once(
    venue,
    old_complete,
    '''    row = repository.complete_account_snapshot_run(
        run_id=run_id,
        status=status,
        fact_count=fact_count,
        difference_count=len(difference_ids),
        completed_at=completed_at,
    )
''',
)
replace_once(
    venue,
    '''def validate_strategy_account(strategy_instance_id: str, account_id: str) -> None:
    with connection() as db:
        row = db.execute(
            """
            SELECT sab.id
            FROM strategy_account_bindings sab
            JOIN strategy_instances si ON si.id = sab.strategy_instance_id
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.strategy_instance_id = ? AND sab.account_id = ?
              AND sab.status = 'active' AND si.status = 'active' AND a.status = 'active'
            """,
            (strategy_instance_id, account_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=403, detail="Account is not actively bound to strategy")
''',
    '''def validate_strategy_account(strategy_instance_id: str, account_id: str) -> None:
    if not repository.has_active_strategy_account(strategy_instance_id, account_id):
        raise HTTPException(status_code=403, detail="Account is not actively bound to strategy")
''',
)
start_marker = '''    with connection() as db:
        local_row = db.execute(
            """
            SELECT net_quantity, average_price
            FROM formal_positions
            WHERE strategy_instance_id = ? AND account_id = ? AND instrument_id = ?
            """,
            (
                request.strategy_instance_id,
                request.account_id,
                external["instrumentId"],
            ),
        ).fetchone()
        if local_row is None:
            local_row = db.execute(
                """
                SELECT net_quantity, average_price
                FROM positions
                WHERE account_id = ? AND instrument_id = ?
                """,
                (request.account_id, external["instrumentId"]),
            ).fetchone()
    local = dict(local_row) if local_row is not None else None
'''
replace_once(
    venue,
    start_marker,
    '''    local = repository.load_comparison_position(
        request.strategy_instance_id,
        request.account_id,
        external["instrumentId"],
    )
''',
)
old_balance = '''    with connection() as db:
        local_row = db.execute(
            """
            SELECT equity, available_balance, currency
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC, created_at DESC
            LIMIT 1
            """,
            (request.account_id,),
        ).fetchone()
    local = dict(local_row) if local_row is not None else None
'''
replace_once(
    venue,
    old_balance,
    '''    local = repository.load_latest_balance(request.account_id)
''',
)
replace_once(
    venue,
    '''def create_difference(
    run_id: str,
    difference_key: str,
    difference_type: DifferenceType,
    entity_type: str,
    local_reference: str | None,
    external_reference: str | None,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> str:
    difference_id = str(uuid4())
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO reconciliation_differences (
                id, run_id, difference_key, difference_type, entity_type,
                local_reference, external_reference, local_value_json,
                external_value_json, status, resolution_actor, resolution_reason,
                resolved_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                difference_id,
                run_id,
                difference_key,
                difference_type,
                entity_type,
                local_reference,
                external_reference,
                json.dumps(local_value, sort_keys=True, default=str),
                json.dumps(external_value, sort_keys=True, default=str),
                "open",
                None,
                None,
                None,
                now_iso(),
            ),
        )
        row = db.execute(
            """
            SELECT id FROM reconciliation_differences
            WHERE run_id = ? AND difference_key = ?
            """,
            (run_id, difference_key),
        ).fetchone()
    return row["id"]


''',
    "",
)
replace_once(
    venue,
    '''def get_run(run_id: str) -> VenueReconciliationRunResponse:
    ensure_schema()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Reconciliation run not found")
    return run_from_row(row)
''',
    '''def get_run(run_id: str) -> VenueReconciliationRunResponse:
    ensure_schema()
    row = repository.load_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Reconciliation run not found")
    return run_from_row(row)
''',
)
replace_once(
    venue,
    '''    with connection() as db:
        rows = db.execute(
            """
            SELECT * FROM reconciliation_differences
            WHERE run_id = ? ORDER BY created_at, difference_key
            """,
            (run_id,),
        ).fetchall()
    return [difference_from_row(row) for row in rows]
''',
    '''    return [
        difference_from_row(row)
        for row in repository.list_difference_rows(run_id)
    ]
''',
)
old_resolve = '''    at = now_iso()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM reconciliation_differences WHERE id = ?",
            (difference_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Reconciliation difference not found")
        if row["status"] != "open":
            return difference_from_row(row)
        db.execute(
            """
            UPDATE reconciliation_differences
            SET status = ?, resolution_actor = ?, resolution_reason = ?, resolved_at = ?
            WHERE id = ?
            """,
            (request.status, request.actor, request.reason, at, difference_id),
        )
        row = db.execute(
            "SELECT * FROM reconciliation_differences WHERE id = ?",
            (difference_id,),
        ).fetchone()
    audit(
'''
replace_once(
    venue,
    old_resolve,
    '''    row, changed = repository.resolve_difference_row(
        difference_id=difference_id,
        status=request.status,
        actor=request.actor,
        reason=request.reason,
        resolved_at=now_iso(),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Reconciliation difference not found")
    if not changed:
        return difference_from_row(row)
    audit(
''',
)
# Remove compatibility row mappers now aliased above.
content = venue.read_text(encoding="utf-8")
start = content.index("\ndef run_from_row(row)")
end = content.index("\n\nrouter = APIRouter", start)
venue.write_text(content[:start] + content[end:], encoding="utf-8")

(TESTS / "test_venue_reconciliation_repository.py").write_text(
    f'''from contextlib import contextmanager
from pathlib import Path

import pytest

from app import venue_reconciliation as compatibility
from app import venue_reconciliation_repository as repository
from app.config import get_settings
from app.database import connection as actual_connection
from app.database import initialize_database

DDL_SHA256 = "{DDL_SHA256}"
STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"


def setup_database(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "venue-repository.db")
    initialize_database()
    repository.ensure_schema()


def create_run(run_id: str = "repository-run-1") -> None:
    repository.create_account_snapshot_run(
        run_id=run_id,
        idempotency_key=f"idempotency:{{run_id}}",
        payload_hash=f"hash:{{run_id}}",
        strategy_instance_id=STRATEGY_ID,
        account_id=ACCOUNT_ID,
        source="runtime",
        position_count=0,
        balance_count=0,
        started_at="2026-07-24T00:00:00+00:00",
    )


def test_ddl_and_compatibility_aliases_are_exact() -> None:
    import hashlib

    assert hashlib.sha256(repository.SCHEMA_SQL.encode("utf-8")).hexdigest() == DDL_SHA256
    assert compatibility.SCHEMA_SQL is repository.SCHEMA_SQL
    assert compatibility.ensure_schema is repository.ensure_schema
    assert compatibility.audit is repository.audit
    assert compatibility.create_difference is repository.store_difference
    assert compatibility.run_from_row is repository.run_from_row
    assert compatibility.difference_from_row is repository.difference_from_row


def test_difference_storage_is_idempotent(tmp_path: Path) -> None:
    setup_database(tmp_path)
    create_run()

    first = repository.store_difference(
        "repository-run-1",
        "position:instrument-1:missing_local",
        "missing_local",
        "position",
        None,
        "external-position-1",
        {{}},
        {{"netQuantity": "1"}},
    )
    second = repository.store_difference(
        "repository-run-1",
        "position:instrument-1:missing_local",
        "missing_local",
        "position",
        None,
        "external-position-1",
        {{}},
        {{"netQuantity": "1"}},
    )

    assert second == first
    with actual_connection() as db:
        count = db.execute(
            "SELECT COUNT(*) AS count FROM reconciliation_differences WHERE run_id = ?",
            ("repository-run-1",),
        ).fetchone()["count"]
    assert count == 1


def test_difference_insert_rolls_back_when_identity_read_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    setup_database(tmp_path)
    create_run()

    class FailOnIdentityRead:
        def __init__(self, db):
            self.db = db

        def execute(self, sql, params=()):
            if "SELECT id FROM reconciliation_differences" in sql:
                raise RuntimeError("forced identity read failure")
            return self.db.execute(sql, params)

    @contextmanager
    def failing_connection():
        with actual_connection() as db:
            yield FailOnIdentityRead(db)

    monkeypatch.setattr(repository, "connection", failing_connection)
    with pytest.raises(RuntimeError, match="forced identity read failure"):
        repository.store_difference(
            "repository-run-1",
            "balance:USD:missing_local",
            "missing_local",
            "balance",
            ACCOUNT_ID,
            "external-balance-1",
            {{}},
            {{"currency": "USD"}},
        )

    with actual_connection() as db:
        count = db.execute(
            "SELECT COUNT(*) AS count FROM reconciliation_differences WHERE run_id = ?",
            ("repository-run-1",),
        ).fetchone()["count"]
    assert count == 0


def test_run_completion_rolls_back_when_result_read_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    setup_database(tmp_path)
    create_run()

    class FailAfterUpdate:
        def __init__(self, db):
            self.db = db
            self.updated = False

        def execute(self, sql, params=()):
            if "UPDATE venue_reconciliation_runs" in sql:
                self.updated = True
                return self.db.execute(sql, params)
            if self.updated and "SELECT * FROM venue_reconciliation_runs" in sql:
                raise RuntimeError("forced run read failure")
            return self.db.execute(sql, params)

    @contextmanager
    def failing_connection():
        with actual_connection() as db:
            yield FailAfterUpdate(db)

    monkeypatch.setattr(repository, "connection", failing_connection)
    with pytest.raises(RuntimeError, match="forced run read failure"):
        repository.complete_account_snapshot_run(
            run_id="repository-run-1",
            status="completed",
            fact_count=4,
            difference_count=2,
            completed_at="2026-07-24T01:00:00+00:00",
        )

    with actual_connection() as db:
        row = db.execute(
            "SELECT status, fact_count, difference_count, completed_at "
            "FROM venue_reconciliation_runs WHERE id = ?",
            ("repository-run-1",),
        ).fetchone()
    assert dict(row) == {{
        "status": "processing",
        "fact_count": 0,
        "difference_count": 0,
        "completed_at": None,
    }}
''',
    encoding="utf-8",
)

(TESTS / "test_architecture_venue_reconciliation_repository.py").write_text(
    '''import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
REPOSITORY_PATH = APP_ROOT / "venue_reconciliation_repository.py"
ORCHESTRATION_PATH = APP_ROOT / "venue_reconciliation.py"


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_repository_is_the_only_ddl_and_direct_sql_owner() -> None:
    repository_source = REPOSITORY_PATH.read_text(encoding="utf-8")
    orchestration_source = ORCHESTRATION_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS venue_reconciliation_runs" in repository_source
    assert "CREATE TABLE IF NOT EXISTS reconciliation_differences" in repository_source
    assert "db.execute(" in repository_source
    assert "connection()" in repository_source
    assert "CREATE TABLE" not in orchestration_source
    assert "db.execute(" not in orchestration_source
    assert "connection()" not in orchestration_source
    assert "SELECT " not in orchestration_source
    assert "INSERT " not in orchestration_source
    assert "UPDATE " not in orchestration_source


def test_orchestration_keeps_http_and_external_effect_mapping() -> None:
    source = ORCHESTRATION_PATH.read_text(encoding="utf-8")

    assert "httpx.get(" in source
    assert "record_financial_fact(" in source
    assert "HTTPException(" in source
    assert "from app import venue_reconciliation_repository as repository" in source


def test_repository_has_no_fastapi_httpx_config_or_financial_fact_dependency() -> None:
    imports = imported_modules(REPOSITORY_PATH)
    source = REPOSITORY_PATH.read_text(encoding="utf-8")

    assert "fastapi" not in imports
    assert "httpx" not in imports
    assert "app.config" not in imports
    assert "app.financial_facts" not in imports
    assert "HTTPException" not in source
''',
    encoding="utf-8",
)

pyproject = BACKEND / "pyproject.toml"
replace_once(
    pyproject,
    '  "app/venue_reconciliation_policy.py",\n',
    '  "app/venue_reconciliation_policy.py",\n  "app/venue_reconciliation_repository.py",\n',
)

ownership = ROOT / "docs/architecture/OWNERSHIP.md"
replace_once(
    ownership,
    "| Venue Reconciliation difference policy | `platform-backend/app/venue_reconciliation_policy.py` | Pure external-status mapping and immutable Order/Position/Balance difference-draft decisions | SQL, Runtime queries, persistence, audit or routes |\n"
    "| Venue Reconciliation orchestration | `platform-backend/app/venue_reconciliation.py` | Compatibility exports, Runtime/SQLite data retrieval, FinancialFact import, difference persistence, audit and routes pending staged extraction | Duplicate DTO or difference-policy definitions |\n",
    "| Venue Reconciliation difference policy | `platform-backend/app/venue_reconciliation_policy.py` | Pure external-status mapping and immutable Order/Position/Balance difference-draft decisions | SQL, Runtime queries, persistence, audit or routes |\n"
    "| Venue Reconciliation persistence | `platform-backend/app/venue_reconciliation_repository.py` | Reconciliation DDL, direct SQL, audit/run/difference persistence, comparison reads, row mapping and protected transactions | FastAPI, Runtime HTTP, FinancialFact import or difference rules |\n"
    "| Venue Reconciliation orchestration | `platform-backend/app/venue_reconciliation.py` | Compatibility exports, Runtime queries, FinancialFact import, repository/policy coordination, HTTP errors and routes pending staged extraction | Direct SQL, DDL, row mapping or duplicate DTO/policy definitions |\n",
)

architecture = ROOT / "docs/architecture/README.md"
replace_once(
    architecture,
    "- `platform-backend/app/venue_reconciliation_policy.py` 是外部订单状态映射与 Order/Position/Balance 差异草稿判定的纯 Policy Owner；它不得读取数据库、调用 Runtime 或写入 Difference。\n",
    "- `platform-backend/app/venue_reconciliation_policy.py` 是外部订单状态映射与 Order/Position/Balance 差异草稿判定的纯 Policy Owner；它不得读取数据库、调用 Runtime 或写入 Difference。\n"
    "- `platform-backend/app/venue_reconciliation_repository.py` 是 Reconciliation DDL、SQL、Row Mapping 与受保护事务的唯一 Owner；原模块不得直接访问数据库。\n",
)

checker = ROOT / "scripts/check-documentation-consistency.py"
replace_once(
    checker,
    '    "Venue Reconciliation difference policy": "platform-backend/app/venue_reconciliation_policy.py",\n',
    '    "Venue Reconciliation difference policy": "platform-backend/app/venue_reconciliation_policy.py",\n'
    '    "Venue Reconciliation persistence": "platform-backend/app/venue_reconciliation_repository.py",\n',
)

debt = ROOT / "docs/engineering/TECHNICAL_DEBT.md"
replace_once(
    debt,
    "Venue Reconciliation DTOs/Difference Policy",
    "Venue Reconciliation DTOs/Difference Policy/Repository",
)

state = ROOT / "docs/codex/current-state.md"
replace_once(
    state,
    "No engineering code workstream is active by default after PR #68 merges.",
    "Issue #69 / Draft PR #70 is the only active engineering workstream: Venue Reconciliation Repository extraction.",
)

changelog = ROOT / "CHANGELOG.md"
entry = '''### Venue Reconciliation Repository ownership — Issue #69 / PR #70

- Added `platform-backend/app/venue_reconciliation_repository.py` as the sole Reconciliation DDL, direct-SQL, row-mapping and persistence-transaction owner.
- Preserved compatibility identities for Schema, audit, Difference persistence and row mappers.
- Added exact pre-extraction DDL SHA-256, Difference idempotency and forced rollback evidence for Difference insertion and Run completion.
- Removed direct database access from the orchestration module while retaining HTTP errors, Runtime, FinancialFact and Policy sequencing.
- Preserved every DDL byte, query predicate/order, ID, API, transaction and both Live Write defaults.

'''
marker = "## Unreleased\n\n"
content = changelog.read_text(encoding="utf-8")
if entry not in content:
    changelog.write_text(content.replace(marker, marker + entry, 1), encoding="utf-8")

task = ROOT / "tasks/issue-69-venue-reconciliation-repository.md"
replace_once(task, "- PR:\n", "- PR: #70\n")
replace_once(
    task,
    "- Done: persistence inventory, Issue and branch.\n"
    "- Current: repository API and transaction design.\n"
    "- Next: implementation, direct verification and full CI.\n",
    "- Done: persistence inventory, Issue/branch/PR and repository API design.\n"
    "- Current: DDL/SQL/row-mapping extraction and transaction tests.\n"
    "- Next: full CI, final review and merge.\n",
)

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-69-apply.yml"
if workflow.exists():
    workflow.unlink()
