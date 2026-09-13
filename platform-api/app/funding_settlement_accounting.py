"""Attribute Bybit settlements only from a reconciled native position interval.

No account-binding allocation or current-position inference. Ambiguous history
remains an unassigned venue event; the existing FinancialFact service owns writes.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from sqlite3 import Connection
from typing import Any

from app.database import connection
from app.financial_fact_schemas import CreateFinancialFactRequest
from app.financial_facts import record_financial_fact
from app.venue_identity_repository import (
    VenueIdentityConflict,
    canonical_operational_rows,
    load_order_execution_links,
    load_order_identities,
)


def _time(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Settlement evidence requires timezone-aware timestamps")
    return stamp


def _number(value: Any) -> Decimal:
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("Settlement evidence requires finite quantities")
    return number


def _opening_run(db: Connection, run: Any) -> Any:
    if run is not None and run["action"] == "close":
        parameters = json.loads(run["requested_parameters_json"] or "{}")
        return db.execute(
            "SELECT * FROM strategy_runs WHERE id=?",
            (parameters.get("targetOpenInstructionId"),),
        ).fetchone()
    return run


def settlement_request(
    db: Connection, event: dict[str, Any], snapshot: dict[str, Any]
) -> CreateFinancialFactRequest | None:
    """Prove one group's ownership since the last native flat position.

    Every subsequent transaction must match a native fill, an owned command and
    a batch, and its reported position must reconcile after each execution.
    Multiple outstanding groups are deliberately not apportioned.
    """
    account = event["accountId"]
    native = event.get("payload") or {}
    if (
        event.get("source") != "bybit_live"
        or event.get("eventType") != "funding"
        or event.get("dataQualityState") != "complete"
        or native.get("type") != "SETTLEMENT"
        or native.get("category") != "linear"
        or snapshot.get("accountId") != account
        or snapshot.get("economicEventsQuality") != "complete"
        or not snapshot.get("historyStart")
        or not snapshot.get("historyEnd")
    ):
        return None
    settled_at = _time(event["occurredAt"])
    if not (_time(snapshot["historyStart"]) < settled_at <= _time(snapshot["historyEnd"])):
        return None
    size = _number(native.get("size"))
    if (
        size == 0
        or abs(size) != _number(native.get("qty"))
        or native.get("side") != ("Sell" if size < 0 else "Buy")
        or _number(event["amount"]) != _number(native.get("funding"))
        or _number(event["amount"]) != _number(native.get("change"))
        or event.get("currency") != native.get("currency")
    ):
        return None
    identities = load_order_identities(db)
    instrument = identities.instrument(account, event.get("instrumentId"))
    links = load_order_execution_links(db)
    rows = db.execute(
        "SELECT payload_json FROM venue_account_events "
        "WHERE account_id=? AND source='bybit_live'",
        (account,),
    ).fetchall()
    history = [
        receipt for row in rows
        if identities.instrument(account, (receipt := json.loads(row[0])).get("instrumentId"))
        == instrument
    ]
    transactions: dict[str, dict[str, Any]] = {}
    fills: dict[str, dict[str, Any]] = {}
    for receipt in history:
        if _time(receipt["occurredAt"]) > settled_at:
            continue
        raw = receipt.get("payload") or {}
        if raw.get("type") == "TRADE" and raw.get("category") == "linear":
            transaction_id = str(raw.get("id") or "")
            if not transaction_id:
                return None
            if transaction_id in transactions and transactions[transaction_id]["payload"] != raw:
                return None
            transactions[transaction_id] = receipt
        if receipt.get("externalFillId"):
            fills[receipt["externalFillId"]] = receipt
    ordered = sorted(transactions.values(), key=lambda row: _time(row["occurredAt"]))
    anchors = []
    for row in ordered:
        raw = row["payload"]
        quantity = _number(raw.get("qty"))
        if quantity <= 0 or raw.get("side") not in {"Buy", "Sell"}:
            return None
        after = _number(raw.get("size"))
        before = after - quantity * (1 if raw["side"] == "Buy" else -1)
        if before == 0:
            anchors.append((row, "before"))
        if after == 0:
            anchors.append((row, "after"))
    if not anchors:
        return None
    anchor, phase = anchors[-1]
    anchor_time = _time(anchor["occurredAt"])
    if anchor_time < _time(snapshot["historyStart"]) or sum(
        _time(row["occurredAt"]) == anchor_time for row in ordered
    ) != 1:
        return None
    def in_interval(stamp: datetime) -> bool:
        return (stamp >= anchor_time if phase == "before" else stamp > anchor_time) and (
            stamp <= settled_at
        )

    # Native net zero can also mean offsetting *logical* groups. Do not erase
    # those groups by treating a venue-level zero as a fresh strategy position.
    prior_groups: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    operational = db.execute(
        "SELECT f.*,f.id AS fill_id FROM fills f WHERE account_id=?", (account,)
    ).fetchall()
    for fill in canonical_operational_rows(operational, identities):
        if identities.instrument(account, fill["instrument_id"]) != instrument:
            continue
        at = _time(fill["occurred_at"])
        if at > anchor_time or (phase == "before" and at == anchor_time):
            continue
        link = links.get(fill["order_id"], {})
        run = db.execute(
            "SELECT * FROM strategy_runs WHERE id=?", (link.get("instructionId"),)
        ).fetchone()
        opening = _opening_run(db, run)
        if opening is None:
            if identities.rows[fill["order_id"]]["strategy_instance_id"]:
                return None
            continue
        prior_groups[opening["id"]] += _number(fill["quantity"]) * (
            1 if fill["side"] == "buy" else -1
        )
    if any(prior_groups.values()):
        return None

    interval = [row for row in ordered if in_interval(_time(row["occurredAt"]))]
    stamps = [_time(row["occurredAt"]) for row in interval]
    if len(stamps) != len(set(stamps)) or settled_at in stamps:
        return None  # Millisecond ties cannot establish the venue's execution order.
    native_ids = {row["payload"].get("tradeId") for row in interval}
    interval_fills = {
        identity for identity, fill in fills.items()
        if in_interval(_time(fill["occurredAt"]))
    }
    if not interval or native_ids != interval_fills:
        return None  # Includes zero-fee/missing transaction evidence and manual executions.
    quantities: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    owners: dict[str, str] = {}
    instructions: dict[str, str] = {}
    evidence = []
    for transaction in interval:
        raw = transaction["payload"]
        fill = fills[raw["tradeId"]]
        quantity = _number(raw.get("qty"))
        if (
            quantity <= 0
            or quantity != _number(fill.get("quantity"))
            or raw.get("side", "").lower() != fill.get("side")
            or raw.get("orderId") != fill.get("externalOrderId")
            or _time(transaction["occurredAt"]) != _time(fill["occurredAt"])
            or fill.get("dataQualityState") != "complete"
        ):
            return None
        order_id = identities.resolve(account, fill)
        link = links.get(str(order_id), {})
        run = db.execute(
            "SELECT * FROM strategy_runs WHERE id=?", (link.get("instructionId"),)
        ).fetchone()
        if run is None or not order_id or run["execution_batch_id"] != link.get("batchId"):
            return None
        opening = _opening_run(db, run)
        if (
            opening is None or opening["action"] != "open"
            or opening["strategy_key"] != "funding_arbitrage"
            or opening["strategy_instance_id"] != run["strategy_instance_id"]
            or identities.rows[order_id]["strategy_instance_id"] != run["strategy_instance_id"]
            or not opening["execution_batch_id"]
        ):
            return None
        batch = opening["execution_batch_id"]
        quantities[batch] += quantity if fill["side"] == "buy" else -quantity
        owners[batch] = opening["strategy_instance_id"]
        instructions[batch] = opening["id"]
        if sum(quantities.values()) != _number(raw.get("size")):
            return None
        evidence.append({"transactionId": raw["id"], "fillId": raw["tradeId"], "orderId": order_id})
    outstanding = {batch: quantity for batch, quantity in quantities.items() if quantity}
    if len(outstanding) != 1 or sum(outstanding.values()) != size:
        return None
    batch = next(iter(outstanding))
    identity = f"{account}:{event['source']}:{event['externalEventId']}"
    return CreateFinancialFactRequest(
        idempotencyKey="venue-funding:" + hashlib.sha256(identity.encode()).hexdigest(),
        factType="funding", source=event["source"], externalId=event["externalEventId"],
        strategyInstanceId=owners[batch], accountId=account, instrumentId=instrument,
        amount=_number(event["amount"]), currency=event["currency"], occurredAt=settled_at,
        payload={
            "batchId": batch, "instructionId": instructions[batch],
            "attributionMethod": "native_flat_to_settlement_single_group",
            "flatTransactionId": anchor["payload"]["id"],
            "flatPositionPhase": phase,
            "positionQuantity": str(size), "executions": evidence, "venueEvent": event,
        },
    )


def sync_funding_settlements(account_id: str) -> int:
    """Called after durable native snapshot ingestion; safe to retry after restart."""
    with connection() as db:
        row = db.execute(
            "SELECT payload_json FROM account_venue_snapshots WHERE account_id=?", (account_id,)
        ).fetchone()
        if row is None:
            return 0
        snapshot = json.loads(row[0])
        requests = []
        for event in snapshot.get("economicEvents", []):
            if event.get("eventType") != "funding" or event.get("source") != "bybit_live":
                continue
            try:
                request = settlement_request(db, event, snapshot)
            except (ValueError, ArithmeticError, VenueIdentityConflict):
                request = None
            if request is not None:
                requests.append(request)
    for request in requests:
        record_financial_fact(request)
    return len(requests)
