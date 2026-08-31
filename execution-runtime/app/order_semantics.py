from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any, Literal

from app.models import VenueFillSnapshot

type OrderStatus = Literal[
    "accepted",
    "partially_filled",
    "filled",
    "canceled",
    "rejected",
    "unknown",
]

_BYBIT_ORDER_STATUS: dict[str, OrderStatus] = {
    "New": "accepted",
    "Created": "accepted",
    "PartiallyFilled": "partially_filled",
    "Filled": "filled",
    "Cancelled": "canceled",
    "Canceled": "canceled",
    "Deactivated": "canceled",
    "Rejected": "rejected",
}


class FillEvidenceConflictError(ValueError):
    """Raised when authoritative fill evidence cannot be merged safely."""


def normalize_bybit_order_status(raw_status: object) -> OrderStatus:
    return _BYBIT_ORDER_STATUS.get(str(raw_status), "unknown")


def normalize_mt5_order_status(mt5: Any, state: int) -> OrderStatus:
    if state in {
        int(getattr(mt5, "ORDER_STATE_STARTED", 0)),
        int(getattr(mt5, "ORDER_STATE_PLACED", 1)),
        int(getattr(mt5, "ORDER_STATE_REQUEST_ADD", 7)),
    }:
        return "accepted"
    if state == int(getattr(mt5, "ORDER_STATE_PARTIAL", 3)):
        return "partially_filled"
    if state == int(getattr(mt5, "ORDER_STATE_FILLED", 4)):
        return "filled"
    if state in {
        int(getattr(mt5, "ORDER_STATE_CANCELED", 2)),
        int(getattr(mt5, "ORDER_STATE_EXPIRED", 6)),
    }:
        return "canceled"
    if state == int(getattr(mt5, "ORDER_STATE_REJECTED", 5)):
        return "rejected"
    return "unknown"


def canonical_fills(
    fills: Iterable[VenueFillSnapshot],
    *,
    requested_quantity: Decimal,
) -> tuple[VenueFillSnapshot, ...]:
    """Deduplicate and order Fill/Deal facts while enforcing the fill ceiling.

    Replayed events with the same immutable identity and payload are harmless.
    Conflicting duplicates and cumulative overfills fail closed.
    """

    by_identity: dict[str, VenueFillSnapshot] = {}
    for fill in fills:
        existing = by_identity.get(fill.external_fill_id)
        if existing is not None and existing != fill:
            raise FillEvidenceConflictError(
                f"Conflicting duplicate fill identity: {fill.external_fill_id}"
            )
        by_identity[fill.external_fill_id] = fill

    ordered = tuple(
        sorted(by_identity.values(), key=lambda item: (item.occurred_at, item.external_fill_id))
    )
    cumulative = sum((fill.quantity for fill in ordered), start=Decimal("0"))
    if cumulative > requested_quantity:
        raise FillEvidenceConflictError("Cumulative fill exceeds requested quantity")
    return ordered
