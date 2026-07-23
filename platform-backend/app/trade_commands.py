from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.database import connection
from app.schemas import CreateOrderRequest, CreateTradeCommandRequest, TradeCommandResponse
from app.trading import decimal_text, submit_order


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def validate_trade_command_catalog(request: CreateTradeCommandRequest) -> None:
    with connection() as db:
        strategy = db.execute(
            """
            SELECT si.id, si.status AS instance_status, sd.strategy_key, sd.v1_scope
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ?
            """,
            (request.strategy_instance_id,),
        ).fetchone()
        if strategy is None:
            raise HTTPException(status_code=404, detail="Strategy instance not found")
        if strategy["instance_status"] != "active" or strategy["v1_scope"] != "closed_loop":
            raise HTTPException(status_code=422, detail="Strategy instance is not runnable")

        binding = db.execute(
            """
            SELECT sab.id
            FROM strategy_account_bindings sab
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.strategy_instance_id = ?
              AND sab.account_id = ?
              AND sab.status = 'active'
              AND a.status = 'active'
            """,
            (request.strategy_instance_id, request.account_id),
        ).fetchone()
        if binding is None:
            raise HTTPException(
                status_code=403,
                detail="Account is not actively bound to strategy instance",
            )

        instrument = db.execute(
            """
            SELECT i.id
            FROM instruments i
            JOIN contract_specifications cs ON cs.instrument_id = i.id
            WHERE i.id = ?
            LIMIT 1
            """,
            (request.instrument_id,),
        ).fetchone()
        if instrument is None:
            raise HTTPException(
                status_code=422,
                detail="Instrument or contract specification is unavailable",
            )


def create_trade_command(request: CreateTradeCommandRequest) -> TradeCommandResponse:
    validate_trade_command_catalog(request)
    existing = find_trade_command_by_idempotency_key(request.idempotency_key)
    if existing is not None:
        return trade_command_from_row(existing)

    trade_command_id = str(uuid4())
    created_at = now_iso()
    with connection() as db:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO trade_commands (
                id, idempotency_key, strategy_instance_id, account_id, instrument_id,
                command_type, side, order_type, quantity, price, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_command_id,
                request.idempotency_key,
                request.strategy_instance_id,
                request.account_id,
                request.instrument_id,
                "create_order",
                request.side,
                request.order_type,
                decimal_text(request.quantity),
                decimal_text(request.price) if request.price is not None else None,
                "accepted",
                created_at,
                created_at,
            ),
        )
        if cursor.rowcount == 0:
            row = find_trade_command_by_idempotency_key(
                request.idempotency_key,
                db=db,
            )
            if row is None:
                raise HTTPException(status_code=409, detail="Trade command claim failed")
            return trade_command_from_row(row)

        db.execute(
            """
            INSERT INTO risk_decisions (id, subject_type, subject_id, decision, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "trade_command",
                trade_command_id,
                "approved",
                "phase2_catalog_and_safety_check",
                created_at,
            ),
        )
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "trade_command_created",
                "trade_command",
                trade_command_id,
                "{}",
                created_at,
            ),
        )

    try:
        order = submit_order(
            CreateOrderRequest(
                accountId=request.account_id,
                instrumentId=request.instrument_id,
                symbol=request.symbol,
                side=request.side,
                orderType=request.order_type,
                quantity=request.quantity,
                price=request.price,
            ),
            command_id=trade_command_id,
        )
    except HTTPException:
        update_trade_command_status(trade_command_id, "rejected")
        raise
    except Exception:
        update_trade_command_status(trade_command_id, "failed")
        raise

    update_trade_command_status(trade_command_id, order.status)
    return get_trade_command(trade_command_id)


def get_trade_command(trade_command_id: str) -> TradeCommandResponse:
    row = find_trade_command(trade_command_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Trade command not found")
    return trade_command_from_row(row)


def find_trade_command(trade_command_id: str):
    with connection() as db:
        return db.execute(
            """
            SELECT tc.id, tc.idempotency_key, tc.strategy_instance_id, tc.account_id,
                   tc.instrument_id, tc.status, tc.created_at, tc.updated_at, o.id AS order_id
            FROM trade_commands tc
            LEFT JOIN orders o ON o.command_id = tc.id
            WHERE tc.id = ?
            """,
            (trade_command_id,),
        ).fetchone()


def find_trade_command_by_idempotency_key(idempotency_key: str, *, db=None):
    query = """
        SELECT tc.id, tc.idempotency_key, tc.strategy_instance_id, tc.account_id,
               tc.instrument_id, tc.status, tc.created_at, tc.updated_at, o.id AS order_id
        FROM trade_commands tc
        LEFT JOIN orders o ON o.command_id = tc.id
        WHERE tc.idempotency_key = ?
    """
    if db is not None:
        return db.execute(query, (idempotency_key,)).fetchone()
    with connection() as local_db:
        return local_db.execute(query, (idempotency_key,)).fetchone()


def update_trade_command_status(trade_command_id: str, status: str) -> None:
    with connection() as db:
        db.execute(
            "UPDATE trade_commands SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_iso(), trade_command_id),
        )


def trade_command_from_row(row) -> TradeCommandResponse:
    return TradeCommandResponse(
        tradeCommandId=row["id"],
        idempotencyKey=row["idempotency_key"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        platformOrderId=row["order_id"],
        status=row["status"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )
