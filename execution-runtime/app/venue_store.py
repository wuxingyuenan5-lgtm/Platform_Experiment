from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from app.config import get_settings
from app.journal import connection
from app.models import (
    CancelOrderResponse,
    InternalCapitalTransferStepCommand,
    InternalCapitalTransferStepResponse,
    SubmitOrderCommand,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillSnapshot,
    VenueMarketQuoteSnapshot,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS fake_venue_orders (
    external_order_id TEXT PRIMARY KEY,
    platform_order_id TEXT NOT NULL UNIQUE,
    command_id TEXT NOT NULL UNIQUE,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT,
    status TEXT NOT NULL,
    filled_quantity TEXT NOT NULL,
    average_fill_price TEXT,
    occurred_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fake_venue_fills (
    external_fill_id TEXT PRIMARY KEY,
    external_order_id TEXT NOT NULL,
    platform_order_id TEXT NOT NULL,
    command_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT NOT NULL,
    fee TEXT NOT NULL,
    currency TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY(external_order_id) REFERENCES fake_venue_orders(external_order_id)
);

CREATE TABLE IF NOT EXISTS fake_venue_positions (
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    net_quantity TEXT NOT NULL,
    average_price TEXT,
    currency TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(account_id, instrument_id)
);

CREATE TABLE IF NOT EXISTS fake_venue_balances (
    account_id TEXT NOT NULL,
    currency TEXT NOT NULL,
    equity TEXT NOT NULL,
    available_balance TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(account_id, currency)
);

CREATE TABLE IF NOT EXISTS fake_venue_cancel_commands (
    idempotency_key TEXT PRIMARY KEY,
    external_order_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    response_status TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fake_venue_fills_order
ON fake_venue_fills(external_order_id, occurred_at);

CREATE TABLE IF NOT EXISTS fake_venue_economic_events (
    external_event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT,
    symbol TEXT,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fake_internal_capital_transfers (
    idempotency_key TEXT PRIMARY KEY,
    external_transfer_id TEXT NOT NULL UNIQUE,
    source_account_id TEXT NOT NULL,
    destination_account_id TEXT NOT NULL,
    source_currency TEXT NOT NULL,
    destination_currency TEXT NOT NULL,
    amount TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS fake_venue_quotes (
    symbol TEXT PRIMARY KEY,
    bid TEXT NOT NULL,
    ask TEXT NOT NULL,
    last TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fake_venue_order_scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    behavior TEXT NOT NULL CHECK (
        behavior IN ('filled', 'accepted_no_fill', 'partial_fill', 'result_unknown')
    ),
    partial_fill_quantity TEXT,
    partial_fill_price TEXT,
    cancel_terminal_after_queries INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    consumed_at TEXT
);


CREATE INDEX IF NOT EXISTS idx_fake_venue_positions_account
ON fake_venue_positions(account_id, instrument_id);
"""

LEGACY_FAKE_BALANCE = Decimal("100000")


def now() -> datetime:
    return datetime.now(UTC)


def now_iso() -> str:
    return now().isoformat()


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def ensure_store() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)
        _ensure_optional_order_columns(db)


def _ensure_optional_order_columns(db) -> None:
    columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(fake_venue_orders)").fetchall()
    }
    if "cancel_requested_at" not in columns:
        db.execute("ALTER TABLE fake_venue_orders ADD COLUMN cancel_requested_at TEXT")
    if "cancel_terminal_after_queries" not in columns:
        db.execute(
            """
            ALTER TABLE fake_venue_orders
            ADD COLUMN cancel_terminal_after_queries INTEGER NOT NULL DEFAULT 0
            """
        )
    if "cancel_query_count" not in columns:
        db.execute(
            """
            ALTER TABLE fake_venue_orders
            ADD COLUMN cancel_query_count INTEGER NOT NULL DEFAULT 0
            """
        )


def quote_currency(symbol: str) -> str:
    normalized = symbol.upper().replace("-PERP", "").replace("+", "")
    for currency in ("USDT", "USDC", "USD", "CNH", "CNY", "EUR", "JPY"):
        if normalized.endswith(currency):
            return currency
    return "USD"


def external_order_id(platform_order_id: str) -> str:
    return f"FAKE-{platform_order_id}"


def external_fill_id(platform_order_id: str) -> str:
    return f"FAKE-FILL-{platform_order_id}"


def persist_filled_order(command: SubmitOrderCommand, fill_price: Decimal) -> tuple[str, str]:
    return persist_order(
        command,
        status="filled",
        fill_price=fill_price,
        fill_quantity=command.quantity,
    )


def persist_order(
    command: SubmitOrderCommand,
    *,
    status: str,
    fill_price: Decimal | None,
    fill_quantity: Decimal,
    cancel_terminal_after_queries: int = 0,
) -> tuple[str, str]:
    ensure_store()
    order_id = external_order_id(command.platform_order_id)
    fill_id = external_fill_id(command.platform_order_id)
    occurred_at = command.received_at.astimezone(UTC).isoformat()
    currency = quote_currency(command.symbol)
    with connection() as db:
        existing = db.execute(
            "SELECT external_order_id FROM fake_venue_orders WHERE platform_order_id = ?",
            (command.platform_order_id,),
        ).fetchone()
        if existing is not None:
            return existing["external_order_id"], fill_id

        db.execute(
            """
            INSERT INTO fake_venue_orders (
                external_order_id, platform_order_id, command_id, account_id,
                instrument_id, symbol, side, order_type, quantity, price, status,
                filled_quantity, average_fill_price, occurred_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                command.platform_order_id,
                command.command_id,
                command.account_id,
                command.instrument_id,
                command.symbol,
                command.side,
                command.order_type,
                decimal_text(command.quantity),
                decimal_text(command.price) if command.price is not None else None,
                status,
                decimal_text(fill_quantity),
                decimal_text(fill_price) if fill_price is not None else None,
                occurred_at,
                occurred_at,
            ),
        )
        db.execute(
            """
            UPDATE fake_venue_orders
            SET cancel_terminal_after_queries = ?
            WHERE external_order_id = ?
            """,
            (cancel_terminal_after_queries, order_id),
        )
        if fill_quantity > 0 and fill_price is not None:
            db.execute(
                """
                INSERT INTO fake_venue_fills (
                    external_fill_id, external_order_id, platform_order_id, command_id,
                    account_id, instrument_id, symbol, side, quantity, price, fee,
                    currency, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fill_id,
                    order_id,
                    command.platform_order_id,
                    command.command_id,
                    command.account_id,
                    command.instrument_id,
                    command.symbol,
                    command.side,
                    decimal_text(fill_quantity),
                    decimal_text(fill_price),
                    "0",
                    currency,
                    occurred_at,
                ),
            )
            update_position(
                db,
                command,
                fill_price,
                currency,
                occurred_at,
                fill_quantity=fill_quantity,
            )
        ensure_balance(db, command.account_id, currency, occurred_at)
    return order_id, fill_id


def update_position(
    db,
    command: SubmitOrderCommand,
    fill_price: Decimal,
    currency: str,
    at: str,
    *,
    fill_quantity: Decimal | None = None,
) -> None:
    row = db.execute(
        """
        SELECT net_quantity, average_price
        FROM fake_venue_positions
        WHERE account_id = ? AND instrument_id = ?
        """,
        (command.account_id, command.instrument_id),
    ).fetchone()
    old_quantity = Decimal(row["net_quantity"]) if row is not None else Decimal("0")
    old_average = (
        Decimal(row["average_price"])
        if row is not None and row["average_price"] is not None
        else None
    )
    effective_quantity = fill_quantity if fill_quantity is not None else command.quantity
    signed_fill = effective_quantity if command.side == "buy" else -effective_quantity
    new_quantity, new_average = calculate_position(old_quantity, old_average, signed_fill, fill_price)
    db.execute(
        """
        INSERT INTO fake_venue_positions (
            account_id, instrument_id, symbol, net_quantity, average_price,
            currency, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(account_id, instrument_id) DO UPDATE SET
            symbol = excluded.symbol,
            net_quantity = excluded.net_quantity,
            average_price = excluded.average_price,
            currency = excluded.currency,
            updated_at = excluded.updated_at
        """,
        (
            command.account_id,
            command.instrument_id,
            command.symbol,
            decimal_text(new_quantity),
            decimal_text(new_average) if new_average is not None else None,
            currency,
            at,
        ),
    )


def calculate_position(
    old_quantity: Decimal,
    old_average: Decimal | None,
    signed_fill: Decimal,
    fill_price: Decimal,
) -> tuple[Decimal, Decimal | None]:
    if old_quantity == 0 or old_quantity * signed_fill > 0:
        new_quantity = old_quantity + signed_fill
        weighted = abs(old_quantity) * (old_average or Decimal("0"))
        weighted += abs(signed_fill) * fill_price
        return new_quantity, weighted / abs(new_quantity)
    new_quantity = old_quantity + signed_fill
    if new_quantity == 0:
        return new_quantity, None
    if old_quantity * new_quantity > 0:
        return new_quantity, old_average
    return new_quantity, fill_price


def ensure_balance(db, account_id: str, currency: str, at: str) -> None:
    target_balance = _fake_balance_seed(account_id, currency)
    db.execute(
        """
        INSERT OR IGNORE INTO fake_venue_balances (
            account_id, currency, equity, available_balance, updated_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            account_id,
            currency,
            decimal_text(target_balance),
            decimal_text(target_balance),
            at,
        ),
    )
    _backfill_legacy_balance_seed(
        db,
        account_id=account_id,
        currency=currency,
        target_balance=target_balance,
        at=at,
    )


def transfer_internal_capital(
    command: InternalCapitalTransferStepCommand,
) -> InternalCapitalTransferStepResponse:
    """Apply one deterministic FakeGateway transfer step exactly once."""
    from app.gateway_errors import GatewayRequestRejectedError

    ensure_store()
    source_currency = command.source_currency.upper()
    destination_currency = command.destination_currency.upper()
    at = now_iso()
    external_id = f"FAKE-TRANSFER-{command.idempotency_key}"
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM fake_internal_capital_transfers WHERE idempotency_key = ?",
            (command.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if (
                existing["source_account_id"] != command.source_account_id
                or existing["destination_account_id"] != command.destination_account_id
                or existing["source_currency"] != source_currency
                or existing["destination_currency"] != destination_currency
                or Decimal(existing["amount"]) != command.amount
            ):
                raise GatewayRequestRejectedError(
                    "Internal transfer idempotency key conflicts with another payload"
                )
            return _internal_transfer_response(existing)

        ensure_balance(db, command.source_account_id, source_currency, at)
        ensure_balance(db, command.destination_account_id, destination_currency, at)
        source = db.execute(
            """
            SELECT equity, available_balance FROM fake_venue_balances
            WHERE account_id = ? AND currency = ?
            """,
            (command.source_account_id, source_currency),
        ).fetchone()
        if source is None or Decimal(source["available_balance"]) < command.amount:
            raise GatewayRequestRejectedError("Insufficient transferable balance")
        db.execute(
            """
            UPDATE fake_venue_balances
            SET equity = ?, available_balance = ?, updated_at = ?
            WHERE account_id = ? AND currency = ?
            """,
            (
                decimal_text(Decimal(source["equity"]) - command.amount),
                decimal_text(Decimal(source["available_balance"]) - command.amount),
                at,
                command.source_account_id,
                source_currency,
            ),
        )
        destination = db.execute(
            """
            SELECT equity, available_balance FROM fake_venue_balances
            WHERE account_id = ? AND currency = ?
            """,
            (command.destination_account_id, destination_currency),
        ).fetchone()
        if destination is None:
            raise RuntimeError("Fake transfer destination balance is unavailable")
        db.execute(
            """
            UPDATE fake_venue_balances
            SET equity = ?, available_balance = ?, updated_at = ?
            WHERE account_id = ? AND currency = ?
            """,
            (
                decimal_text(Decimal(destination["equity"]) + command.amount),
                decimal_text(Decimal(destination["available_balance"]) + command.amount),
                at,
                command.destination_account_id,
                destination_currency,
            ),
        )
        db.execute(
            """
            INSERT INTO fake_internal_capital_transfers (
                idempotency_key, external_transfer_id, source_account_id,
                destination_account_id, source_currency, destination_currency,
                amount, status, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)
            """,
            (
                command.idempotency_key,
                external_id,
                command.source_account_id,
                command.destination_account_id,
                source_currency,
                destination_currency,
                decimal_text(command.amount),
                at,
                at,
            ),
        )
        row = db.execute(
            "SELECT * FROM fake_internal_capital_transfers WHERE idempotency_key = ?",
            (command.idempotency_key,),
        ).fetchone()
    return _internal_transfer_response(row)


def _internal_transfer_response(row) -> InternalCapitalTransferStepResponse:
    return InternalCapitalTransferStepResponse(
        externalTransferId=row["external_transfer_id"],
        status=row["status"],
        sourceAccountId=row["source_account_id"],
        destinationAccountId=row["destination_account_id"],
        sourceCurrency=row["source_currency"],
        destinationCurrency=row["destination_currency"],
        amount=Decimal(row["amount"]),
        completedAt=row["completed_at"],
    )


def _fake_balance_seed(account_id: str, currency: str) -> Decimal:
    return get_settings().fake_balance_seed_overrides.get(
        (account_id, currency.upper()),
        LEGACY_FAKE_BALANCE,
    )


def _backfill_legacy_balance_seed(
    db,
    *,
    account_id: str,
    currency: str,
    target_balance: Decimal,
    at: str,
) -> None:
    if target_balance == LEGACY_FAKE_BALANCE:
        return
    row = db.execute(
        """
        SELECT equity, available_balance
        FROM fake_venue_balances
        WHERE account_id = ? AND currency = ?
        """,
        (account_id, currency),
    ).fetchone()
    if row is None:
        return
    if (
        Decimal(row["equity"]) != LEGACY_FAKE_BALANCE
        or Decimal(row["available_balance"]) != LEGACY_FAKE_BALANCE
    ):
        return
    db.execute(
        """
        UPDATE fake_venue_balances
        SET equity = ?, available_balance = ?, updated_at = ?
        WHERE account_id = ? AND currency = ?
        """,
        (
            decimal_text(target_balance),
            decimal_text(target_balance),
            at,
            account_id,
            currency,
        ),
    )


def _seed_configured_balances(db, account_id: str | None) -> None:
    at = now_iso()
    overrides = get_settings().fake_balance_seed_overrides
    for (seed_account_id, currency), _ in overrides.items():
        if account_id is not None and seed_account_id != account_id:
            continue
        ensure_balance(db, seed_account_id, currency, at)


def get_order(*, platform_order_id: str | None = None, external_id: str | None = None) -> VenueOrderSnapshot | None:
    ensure_store()
    if platform_order_id is None and external_id is None:
        raise ValueError("platform_order_id or external_id is required")
    field = "platform_order_id" if platform_order_id is not None else "external_order_id"
    value = platform_order_id if platform_order_id is not None else external_id
    with connection() as db:
        _maybe_finalize_canceled_order(db, field, str(value))
        row = db.execute(f"SELECT * FROM fake_venue_orders WHERE {field} = ?", (value,)).fetchone()
    return order_from_row(row) if row is not None else None


def get_market_quote(*, account_id: str, symbol: str) -> VenueMarketQuoteSnapshot:
    ensure_store()
    normalized = symbol.upper()
    with connection() as db:
        row = db.execute("SELECT * FROM fake_venue_quotes WHERE symbol = ?", (normalized,)).fetchone()
        if row is None:
            at = now_iso()
            db.execute(
                """
                INSERT INTO fake_venue_quotes (symbol, bid, ask, last, updated_at)
                VALUES (?, '99', '101', '100', ?)
                """,
                (normalized, at),
            )
            row = db.execute(
                "SELECT * FROM fake_venue_quotes WHERE symbol = ?",
                (normalized,),
            ).fetchone()
    assert row is not None
    bid = Decimal(str(row["bid"]))
    ask = Decimal(str(row["ask"]))
    return VenueMarketQuoteSnapshot(
        source="fake",
        accountId=account_id,
        symbol=normalized,
        bid=bid,
        ask=ask,
        mid=(bid + ask) / Decimal("2"),
        last=Decimal(str(row["last"])) if row["last"] is not None else None,
        currency=quote_currency(normalized),
        asOf=row["updated_at"],
        dataQualityState="complete",
    )


def list_fills(
    *,
    account_id: str | None = None,
    external_id: str | None = None,
    platform_order_id: str | None = None,
) -> list[VenueFillSnapshot]:
    ensure_store()
    clauses: list[str] = []
    parameters: list[str] = []
    if account_id is not None:
        clauses.append("account_id = ?")
        parameters.append(account_id)
    if external_id is not None:
        clauses.append("external_order_id = ?")
        parameters.append(external_id)
    if platform_order_id is not None:
        clauses.append("platform_order_id = ?")
        parameters.append(platform_order_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection() as db:
        rows = db.execute(
            f"SELECT * FROM fake_venue_fills {where} ORDER BY occurred_at, external_fill_id",
            tuple(parameters),
        ).fetchall()
    return [fill_from_row(row) for row in rows]


def persist_economic_event(
    event_type: str,
    *,
    external_event_id: str,
    account_id: str,
    instrument_id: str | None,
    symbol: str | None,
    amount: Decimal,
    currency: str,
    occurred_at: str,
    payload: dict[str, object],
) -> None:
    ensure_store()
    with connection() as db:
        db.execute(
            """
            INSERT OR REPLACE INTO fake_venue_economic_events (
                external_event_id, event_type, account_id, instrument_id, symbol,
                amount, currency, occurred_at, data_quality_state, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'complete', ?)
            """,
            (
                external_event_id,
                event_type,
                account_id,
                instrument_id,
                symbol,
                decimal_text(amount),
                currency,
                occurred_at,
                json.dumps(payload, sort_keys=True, default=str),
            ),
        )


def list_economic_events(
    *,
    account_id: str | None = None,
    instrument_id: str | None = None,
    event_type: str | None = None,
) -> list[VenueEconomicEventSnapshot]:
    ensure_store()
    clauses: list[str] = []
    parameters: list[object] = []
    if account_id is not None:
        clauses.append("account_id = ?")
        parameters.append(account_id)
    if instrument_id is not None:
        clauses.append("instrument_id = ?")
        parameters.append(instrument_id)
    if event_type is not None:
        clauses.append("event_type = ?")
        parameters.append(event_type)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT * FROM fake_venue_economic_events
            {where}
            ORDER BY occurred_at
            """,
            parameters,
        ).fetchall()
    return [
        VenueEconomicEventSnapshot(
            source="fake",
            externalEventId=row["external_event_id"],
            eventType=row["event_type"],
            accountId=row["account_id"],
            instrumentId=row["instrument_id"],
            symbol=row["symbol"],
            amount=Decimal(row["amount"]),
            currency=row["currency"],
            occurredAt=row["occurred_at"],
            dataQualityState=row["data_quality_state"],
            payload=json.loads(row["payload_json"]),
        )
        for row in rows
    ]


def list_positions(account_id: str | None = None) -> list[VenuePositionSnapshot]:
    ensure_store()
    where = "WHERE account_id = ?" if account_id is not None else ""
    parameters = (account_id,) if account_id is not None else ()
    with connection() as db:
        rows = db.execute(
            f"SELECT * FROM fake_venue_positions {where} ORDER BY account_id, instrument_id",
            parameters,
        ).fetchall()
    return [position_from_row(row) for row in rows]


def list_balances(account_id: str | None = None) -> list[VenueBalanceSnapshot]:
    ensure_store()
    where = "WHERE account_id = ?" if account_id is not None else ""
    parameters = (account_id,) if account_id is not None else ()
    with connection() as db:
        _seed_configured_balances(db, account_id)
        rows = db.execute(
            f"SELECT * FROM fake_venue_balances {where} ORDER BY account_id, currency",
            parameters,
        ).fetchall()
    return [balance_from_row(row) for row in rows]


def cancel_order(external_id: str, idempotency_key: str, reason: str | None) -> CancelOrderResponse:
    ensure_store()
    payload_hash = f"{external_id}|{reason or ''}"
    at = now_iso()
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM fake_venue_cancel_commands WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise ValueError("Cancel idempotency key was reused with a different payload")
            order = db.execute(
                "SELECT platform_order_id FROM fake_venue_orders WHERE external_order_id = ?",
                (existing["external_order_id"],),
            ).fetchone()
            return CancelOrderResponse(
                source="fake",
                externalOrderId=existing["external_order_id"],
                platformOrderId=order["platform_order_id"] if order else "unknown",
                status=existing["response_status"],
                reason=existing["reason"],
                asOf=existing["created_at"],
            )

        order = db.execute(
            "SELECT * FROM fake_venue_orders WHERE external_order_id = ?",
            (external_id,),
        ).fetchone()
        if order is None:
            response_status = "not_found"
            platform_order_id = "unknown"
        elif order["status"] in {"filled", "rejected", "canceled"}:
            response_status = "already_final"
            platform_order_id = order["platform_order_id"]
        else:
            response_status = "canceled"
            platform_order_id = order["platform_order_id"]
            terminal_after = int(order["cancel_terminal_after_queries"] or 0)
            if terminal_after <= 0:
                db.execute(
                    """
                    UPDATE fake_venue_orders
                    SET status = 'canceled', cancel_requested_at = ?, updated_at = ?
                    WHERE external_order_id = ?
                    """,
                    (at, at, external_id),
                )
            else:
                db.execute(
                    """
                    UPDATE fake_venue_orders
                    SET cancel_requested_at = ?, cancel_query_count = 0, updated_at = ?
                    WHERE external_order_id = ?
                    """,
                    (at, at, external_id),
                )
        db.execute(
            """
            INSERT INTO fake_venue_cancel_commands (
                idempotency_key, external_order_id, payload_hash, response_status,
                reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (idempotency_key, external_id, payload_hash, response_status, reason, at),
        )
    return CancelOrderResponse(
        source="fake",
        externalOrderId=external_id,
        platformOrderId=platform_order_id,
        status=response_status,
        reason=reason,
        asOf=at,
    )


def order_from_row(row) -> VenueOrderSnapshot:
    return VenueOrderSnapshot(
        source="fake",
        externalOrderId=row["external_order_id"],
        platformOrderId=row["platform_order_id"],
        commandId=row["command_id"],
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        symbol=row["symbol"],
        side=row["side"],
        orderType=row["order_type"],
        quantity=Decimal(row["quantity"]),
        price=Decimal(row["price"]) if row["price"] is not None else None,
        status=row["status"],
        filledQuantity=Decimal(row["filled_quantity"]),
        remainingQuantity=Decimal(row["quantity"]) - Decimal(row["filled_quantity"]),
        averageFillPrice=(
            Decimal(row["average_fill_price"])
            if row["average_fill_price"] is not None
            else None
        ),
        occurredAt=row["occurred_at"],
        asOf=row["updated_at"],
        dataQualityState="complete",
    )


def claim_order_script(db, symbol: str):
    row = db.execute(
        """
        SELECT * FROM fake_venue_order_scripts
        WHERE upper(symbol) = upper(?) AND consumed_at IS NULL
        ORDER BY id
        LIMIT 1
        """,
        (symbol,),
    ).fetchone()
    if row is None:
        return None
    db.execute(
        "UPDATE fake_venue_order_scripts SET consumed_at = ? WHERE id = ?",
        (now_iso(), row["id"]),
    )
    return row


def _maybe_finalize_canceled_order(db, field: str, value: str) -> None:
    row = db.execute(f"SELECT * FROM fake_venue_orders WHERE {field} = ?", (value,)).fetchone()
    if row is None or row["cancel_requested_at"] is None:
        return
    if row["status"] in {"filled", "rejected", "canceled"}:
        return
    next_count = int(row["cancel_query_count"] or 0) + 1
    terminal_after = int(row["cancel_terminal_after_queries"] or 0)
    status = "canceled" if next_count > terminal_after else row["status"]
    db.execute(
        """
        UPDATE fake_venue_orders
        SET cancel_query_count = ?, status = ?, updated_at = ?
        WHERE external_order_id = ?
        """,
        (next_count, status, now_iso(), row["external_order_id"]),
    )


def fill_from_row(row) -> VenueFillSnapshot:
    return VenueFillSnapshot(
        source="fake",
        externalFillId=row["external_fill_id"],
        externalOrderId=row["external_order_id"],
        platformOrderId=row["platform_order_id"],
        commandId=row["command_id"],
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        symbol=row["symbol"],
        side=row["side"],
        quantity=Decimal(row["quantity"]),
        price=Decimal(row["price"]),
        fee=Decimal(row["fee"]),
        currency=row["currency"],
        occurredAt=row["occurred_at"],
        dataQualityState="complete",
    )


def position_from_row(row) -> VenuePositionSnapshot:
    return VenuePositionSnapshot(
        source="fake",
        externalPositionId=f"FAKE-POS-{row['account_id']}-{row['instrument_id']}",
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        symbol=row["symbol"],
        netQuantity=Decimal(row["net_quantity"]),
        averagePrice=Decimal(row["average_price"]) if row["average_price"] is not None else None,
        currency=row["currency"],
        asOf=row["updated_at"],
        dataQualityState="complete",
    )


def balance_from_row(row) -> VenueBalanceSnapshot:
    return VenueBalanceSnapshot(
        source="fake",
        externalBalanceId=f"FAKE-BAL-{row['account_id']}-{row['currency']}-{row['updated_at']}",
        accountId=row["account_id"],
        equity=Decimal(row["equity"]),
        availableBalance=Decimal(row["available_balance"]),
        currency=row["currency"],
        asOf=row["updated_at"],
        dataQualityState="complete",
    )
