from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models import VenueFillSnapshot
from app.order_semantics import (
    FillEvidenceConflictError,
    canonical_fills,
    normalize_bybit_order_status,
    normalize_mt5_order_status,
)


def _fill(fill_id: str, quantity: str, offset: int = 0) -> VenueFillSnapshot:
    return VenueFillSnapshot(
        source="fake",
        externalFillId=fill_id,
        externalOrderId="venue-order-1",
        platformOrderId="platform-order-1",
        commandId="command-1",
        accountId="account-1",
        instrumentId="instrument-1",
        symbol="XAUUSD",
        side="buy",
        quantity=quantity,
        price="2400",
        currency="USD",
        occurredAt=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=offset),
    )


def test_status_normalization_is_shared_across_venue_adapters() -> None:
    class Mt5:
        ORDER_STATE_PARTIAL = 3

    assert normalize_bybit_order_status("PartiallyFilled") == "partially_filled"
    assert normalize_mt5_order_status(Mt5(), 3) == "partially_filled"
    assert normalize_bybit_order_status("new-venue-state") == "unknown"


def test_canonical_fills_deduplicates_replay_and_orders_out_of_order_evidence() -> None:
    later = _fill("fill-2", "0.4", 2)
    earlier = _fill("fill-1", "0.6", 1)

    result = canonical_fills(
        [later, earlier, earlier.model_copy(deep=True)],
        requested_quantity=Decimal("1"),
    )

    assert [fill.external_fill_id for fill in result] == ["fill-1", "fill-2"]


def test_canonical_fills_rejects_conflicting_duplicate_and_overfill() -> None:
    original = _fill("fill-1", "0.6")
    with pytest.raises(FillEvidenceConflictError, match="Conflicting duplicate"):
        canonical_fills(
            [original, original.model_copy(update={"quantity": Decimal("0.5")})],
            requested_quantity=Decimal("1"),
        )

    with pytest.raises(FillEvidenceConflictError, match="exceeds requested"):
        canonical_fills(
            [original, _fill("fill-2", "0.5", 1)],
            requested_quantity=Decimal("1"),
        )
