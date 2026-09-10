from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from sqlite3 import Connection
from typing import Any

from app.database import connection
from app.venue_identity_repository import (
    VenueIdentityConflict,
    load_order_execution_links,
    load_order_identities,
    order_execution_evidence,
)


def batch_order_ids(db: Connection, batch_id: str) -> set[str]:
    """Use persisted leg/action identities, including the existing rollback key."""
    batch = db.execute("SELECT * FROM execution_batches WHERE id=?", (batch_id,)).fetchone()
    if batch is None:
        raise VenueIdentityConflict("Execution batch not found")
    legs = db.execute("SELECT * FROM execution_batch_legs WHERE batch_id=?", (batch_id,)).fetchall()
    result = {
        order_id
        for order_id, link in load_order_execution_links(db).items()
        if link["batchId"] == batch_id
    }
    rollback = db.execute(
        "SELECT tc.*,o.id AS order_id FROM trade_commands tc "
        "LEFT JOIN orders o ON o.command_id=tc.id WHERE tc.idempotency_key=?",
        (f"cross-spread-rollback:{batch_id}:bybit",),
    ).fetchone()
    if rollback is not None:
        original = next((row for row in legs if row["role"] == "bybit_leg"), None)
        if (
            original is None
            or rollback["strategy_instance_id"] != batch["strategy_instance_id"]
            or any(rollback[key] != original[key] for key in ("account_id", "instrument_id"))
            or rollback["side"] == original["side"]
            or Decimal(rollback["quantity"]) > Decimal(original["quantity"])
        ):
            raise VenueIdentityConflict("Rollback command conflicts with its batch")
        if rollback["order_id"]:
            result.add(rollback["order_id"])
        elif rollback["status"] not in {"rejected", "failed"}:
            raise VenueIdentityConflict("Rollback command has an unresolved outcome")
    return result


def calculate_residual_exposure(batch_id: str) -> tuple[Decimal, str, str]:
    with connection() as db:
        return exposure_evidence(db, batch_id)[:3]


def exposure_evidence(
    db: Connection, batch_id: str
) -> tuple[Decimal, str, str, list[dict[str, Any]]]:
    """Net actual quantities before prices; never equate spread PnL with exposure.

    This read shares its caller's transaction for an atomic, auditable recheck.
    Missing identities, unresolved orders, ambiguous legacy fills and overfills
    stay incomplete even when the known directional quantities net to zero.
    """
    proof: list[dict[str, Any]] = []
    exposure: dict[str, Decimal] = {}
    prices: dict[str, Decimal] = {}
    currencies: set[str] = set()
    complete = True
    try:
        identities = load_order_identities(db)
        order_ids = batch_order_ids(db, batch_id)
        legs = db.execute(
            "SELECT * FROM execution_batch_legs WHERE batch_id=?", (batch_id,)
        ).fetchall()
        if not legs:
            complete = False
        for leg in legs:
            if not leg["order_id"] and leg["status"] not in {
                "pending",
                "blocked",
                "failed",
                "rejected",
                "canceled",
            }:
                complete = False
        batch = db.execute(
            "SELECT strategy_instance_id FROM execution_batches WHERE id=?", (batch_id,)
        ).fetchone()
        for order_id in sorted(order_ids):
            order = db.execute(
                "SELECT o.*,tc.strategy_instance_id,tc.status AS command_status,i.base_currency,"
                "i.settle_currency,i.instrument_type,a.environment,cs.contract_multiplier "
                "FROM orders o "
                "JOIN trade_commands tc ON tc.id=o.command_id "
                "JOIN accounts a ON a.id=o.account_id "
                "LEFT JOIN instruments i ON i.id=o.instrument_id "
                "LEFT JOIN contract_specifications cs ON cs.instrument_id=o.instrument_id "
                "AND cs.effective_from=(SELECT MAX(effective_from) FROM contract_specifications "
                "WHERE instrument_id=o.instrument_id) WHERE o.id=?",
                (order_id,),
            ).fetchone()
            if order is None or order["strategy_instance_id"] != batch["strategy_instance_id"]:
                raise VenueIdentityConflict("Risk order has no matching command owner")
            leg = next((leg for leg in legs if leg["order_id"] == order_id), None)
            if leg is not None and any(
                order[key] != leg[key] for key in ("account_id", "instrument_id", "side")
            ):
                raise VenueIdentityConflict("Risk leg identity conflicts with its order")
            quantity, price, trustworthy, fill_ids = order_execution_evidence(
                db, order_id, identities=identities
            )
            if order["status"] not in {"filled", "canceled", "rejected"} or order[
                "command_status"
            ] in {"processing", "result_unknown", "accepted", "acknowledged"}:
                trustworthy = False
            if quantity == 0 and order["status"] == "filled":
                trustworthy = False
            complete = complete and trustworthy
            proof.append(
                {
                    "orderId": order_id,
                    "externalOrderId": order["external_order_id"],
                    "quantity": str(quantity),
                    "complete": trustworthy,
                    "fillIds": fill_ids,
                }
            )
            if quantity == 0:
                continue
            if (
                not order["base_currency"]
                or not order["settle_currency"]
                or not order["contract_multiplier"]
                or price is None
            ):
                raise VenueIdentityConflict("Risk contract specification or fill price is missing")
            multiplier = Decimal(order["contract_multiplier"])
            if not multiplier.is_finite() or multiplier <= 0:
                raise VenueIdentityConflict("Risk contract multiplier is invalid")
            key = order["base_currency"]
            delta = quantity * multiplier * (-1 if order["side"] == "sell" else 1)
            if order["instrument_type"] == "crypto_spot" and order["environment"] == "live":
                from app.strategy_financial_readmodel import _native_fills_for_orders

                native = [
                    json.loads(row["payload_json"])
                    for row in _native_fills_for_orders(db, {order_id}) or []
                ]
                if (
                    not native
                    or sum((Decimal(str(fill["quantity"])) for fill in native), Decimal("0"))
                    != quantity
                    or any(
                        fill.get("fee") is None or fill.get("currency") in {None, "", "UNKNOWN"}
                        for fill in native
                    )
                ):
                    complete = False
                else:
                    delta -= sum(
                        (Decimal(str(fill["fee"])) for fill in native if fill["currency"] == key),
                        Decimal("0"),
                    )
            exposure[key] = exposure.get(key, Decimal(0)) + delta
            prices[key] = max(prices.get(key, Decimal(0)), price)
            currencies.add(order["settle_currency"])
    except (VenueIdentityConflict, InvalidOperation, ValueError, KeyError) as exc:
        return Decimal(0), "UNKNOWN", "incomplete", [*proof, {"error": str(exc)}]
    residual = sum((abs(q) * prices[key] for key, q in exposure.items()), Decimal(0))
    currency = (
        sorted(currencies)[0] if len(currencies) == 1 else "MIXED" if currencies else "UNKNOWN"
    )
    nonzero = sum(q != 0 for q in exposure.values())
    if residual and (len(currencies) != 1 or nonzero != 1):
        complete = False
    return residual, currency, "complete" if complete else "incomplete", proof
