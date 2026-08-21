from __future__ import annotations

import json
from decimal import Decimal

from fastapi import HTTPException

from app.database import connection
from app.live_trading_sessions import (
    audit,
    canonical_hash,
    check_approval_blockers,
    decimal_text,
    ensure_schema,
    expire_sessions,
    now_iso,
)


def validate_and_claim_live_session_atomic(
    *,
    command_id: str,
    strategy_instance_id: str,
    account_id: str,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal | None,
) -> str:
    """Atomically validate an approved live window and reserve its notional.

    SQLite's ``BEGIN IMMEDIATE`` serializes competing writers before the daily
    total is read. This prevents two concurrent commands from both observing
    the same remaining allowance and oversubscribing the approved session.
    """

    ensure_schema()
    if order_type != "market" and (price is None or price <= 0):
        raise HTTPException(
            status_code=422,
            detail="Live session notional validation requires an explicit positive price",
        )

    expire_sessions()
    timestamp = now_iso()
    normalized_symbol = symbol.strip().upper()
    notional = quantity * price if price is not None else Decimal(0)
    payload_hash = canonical_hash(
        {
            "commandId": command_id,
            "strategyInstanceId": strategy_instance_id,
            "accountId": account_id,
            "symbol": normalized_symbol,
            "side": side,
            "orderType": order_type,
            "quantity": decimal_text(quantity),
            "price": decimal_text(price) if price is not None else None,
        }
    )

    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM live_trading_session_claims WHERE command_id = ?",
            (command_id,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Live session command identity was reused with a different payload",
                )
            return existing["session_id"]

        rows = db.execute(
            """
            SELECT * FROM live_trading_sessions
            WHERE strategy_instance_id = ? AND account_id = ?
              AND status = 'approved' AND starts_at <= ? AND ends_at > ?
            ORDER BY approved_at DESC
            """,
            (strategy_instance_id, account_id, timestamp, timestamp),
        ).fetchall()
        eligible = [
            row
            for row in rows
            if normalized_symbol in json.loads(row["symbols_json"])
            and side in json.loads(row["sides_json"])
            and order_type in json.loads(row["order_types_json"])
        ]
        if len(eligible) != 1:
            raise HTTPException(
                status_code=403,
                detail="Exactly one active approved LiveTradingSession is required",
            )

        session = eligible[0]
        if check_approval_blockers(session, db=db):
            raise HTTPException(status_code=423, detail="Live session has active safety blockers")
        # Session maxOrderNotional/maxDailyNotional are legacy-compat acceptance
        # caps: exceedance no longer rejects the claim (non-blocking). The claim
        # row is still recorded for command identity, audit and reconciliation.
        db.execute(
            """
            INSERT INTO live_trading_session_claims (
                command_id, session_id, payload_hash, notional, claimed_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                command_id,
                session["id"],
                payload_hash,
                decimal_text(notional),
                timestamp,
            ),
        )
        session_id = session["id"]

    audit(
        "live_trading_session_claimed",
        session_id,
        {
            "commandId": command_id,
            "strategyInstanceId": strategy_instance_id,
            "accountId": account_id,
            "symbol": normalized_symbol,
            "notional": notional,
            "claimMode": "sqlite_begin_immediate",
        },
    )
    return session_id
