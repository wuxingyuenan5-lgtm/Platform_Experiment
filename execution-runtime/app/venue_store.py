from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.journal import connection
from app.models import (
    CancelOrderResponse,
    SubmitOrderCommand,
    VenueBalanceSnapshot,
    VenueFillSnapshot,
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

CREATE INDEX IF NOT EXISTS idx_fake_venue_positions_account
ON fake_venue_positions(account_id, instrument_id);
"""


def now() -> datetime:
    return datetime.now(UTC)


def now_iso() -> str:
    return now().isoformat()


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def ensure_store() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


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
                "filled",
                decimal_text(command.quantity),
                decimal_text(fill_price),
                occurred_at,
                occurred_at,
            ),
        )
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
                decimal_text(command.quantity),
                decimal_text(fill_price),
                "0",
                currency,
                occurred_at,
            ),
        )
        update_position(db, command, fill_price, currency, occurred_at)
        ensure_balance(db, command.account_id, currency, occurred_at)
    return order_id, fill_id


def update_position(db, command: SubmitOrderCommand, fill_price: Decimal, currency: str, at: str) -> None:
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
    signed_fill = command.quantity if command.side == "buy" else -command.quantity
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
    db.execute(
        """
        INSERT OR IGNORE INTO fake_venue_balances (
            account_id, currency, equity, available_balance, updated_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (account_id, currency, "100000", "100000", at),
    )


def get_order(*, platform_order_id: str | None = None, external_id: str | None = None) -> VenueOrderSnapshot | None:
    ensure_store()
    if platform_order_id is None and external_id is None:
        raise ValueError("platform_order_id or external_id is required")
    field = "platform_order_id" if platform_order_id is not None else "external_order_id"
    value = platform_order_id if platform_order_id is not None else external_id
    with connection() as db:
        row = db.execute(f"SELECT * FROM fake_venue_orders WHERE {field} = ?", (value,)).fetchone()
    return order_from_row(row) if row is not None else None


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
            db.execute(
                "UPDATE fake_venue_orders SET status = 'canceled', updated_at = ? WHERE external_order_id = ?",
                (at, external_id),
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
        averageFillPrice=(
            Decimal(row["average_fill_price"])
            if row["average_fill_price"] is not None
            else None
        ),
        occurredAt=row["occurred_at"],
        asOf=row["updated_at"],
        dataQualityState="complete",
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
