from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.venue_reconciliation_schemas import DifferenceType


@dataclass(frozen=True)
class DifferenceDraft:
    difference_key: str
    difference_type: DifferenceType
    entity_type: str
    local_reference: str | None
    external_reference: str | None
    local_value: dict[str, object]
    external_value: dict[str, object]


_ORDER_UPDATE_STATUSES = {
    "accepted": "acknowledged",
    "filled": "filled",
    "rejected": "rejected",
    "canceled": "canceled",
    "unknown": "result_unknown",
}
_ORDER_EXPECTED_STATUSES = {
    **_ORDER_UPDATE_STATUSES,
    "filled": "filled",
}


def external_order_update_status(status: object) -> str | None:
    return _ORDER_UPDATE_STATUSES.get(str(status))


def expected_order_status(status: object) -> str:
    return _ORDER_EXPECTED_STATUSES.get(str(status), "result_unknown")


def order_difference_draft(
    order_id: str,
    difference_type: DifferenceType,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> DifferenceDraft:
    return DifferenceDraft(
        difference_key=f"order:{order_id}:{difference_type}",
        difference_type=difference_type,
        entity_type="order",
        local_reference=order_id,
        external_reference=None,
        local_value=local_value,
        external_value=external_value,
    )


def order_difference_drafts(
    *,
    order_id: str,
    local_status: object,
    local_fill_quantities: list[object],
    external_order: dict[str, object],
    fills: list[dict[str, object]],
) -> list[DifferenceDraft]:
    drafts: list[DifferenceDraft] = []
    if local_status != expected_order_status(external_order["status"]):
        drafts.append(
            order_difference_draft(
                order_id,
                "status_mismatch",
                {"status": local_status},
                {"status": external_order["status"]},
            )
        )

    external_quantity = sum(
        (Decimal(str(fill["quantity"])) for fill in fills),
        Decimal("0"),
    )
    local_quantity = sum(
        (Decimal(str(quantity)) for quantity in local_fill_quantities),
        Decimal("0"),
    )
    if local_quantity != external_quantity:
        drafts.append(
            order_difference_draft(
                order_id,
                "quantity_mismatch",
                {"filledQuantity": format(local_quantity, "f")},
                {"filledQuantity": format(external_quantity, "f")},
            )
        )
    return drafts


def position_difference_drafts(
    *,
    account_id: str,
    local: dict[str, object] | None,
    external: dict[str, object],
    fact_id: str,
) -> list[DifferenceDraft]:
    instrument_id = str(external["instrumentId"])
    external_reference = str(external["externalPositionId"])
    if local is None:
        return [
            DifferenceDraft(
                difference_key=f"position:{instrument_id}:missing_local",
                difference_type="missing_local",
                entity_type="position",
                local_reference=None,
                external_reference=external_reference,
                local_value={},
                external_value=external,
            )
        ]
    if Decimal(str(local["net_quantity"])) != Decimal(str(external["netQuantity"])):
        return [
            DifferenceDraft(
                difference_key=f"position:{instrument_id}:quantity_mismatch",
                difference_type="quantity_mismatch",
                entity_type="position",
                local_reference=f"{account_id}:{instrument_id}",
                external_reference=external_reference,
                local_value={"netQuantity": local["net_quantity"]},
                external_value={"netQuantity": external["netQuantity"], "factId": fact_id},
            )
        ]
    return []


def balance_difference_drafts(
    *,
    account_id: str,
    local: dict[str, object] | None,
    external: dict[str, object],
) -> list[DifferenceDraft]:
    currency = str(external["currency"])
    external_reference = str(external["externalBalanceId"])
    if local is None:
        return [
            DifferenceDraft(
                difference_key=f"balance:{currency}:missing_local",
                difference_type="missing_local",
                entity_type="balance",
                local_reference=account_id,
                external_reference=external_reference,
                local_value={},
                external_value=external,
            )
        ]
    if local["currency"] != external["currency"]:
        return [
            DifferenceDraft(
                difference_key=f"balance:{currency}:currency_mismatch",
                difference_type="currency_mismatch",
                entity_type="balance",
                local_reference=account_id,
                external_reference=external_reference,
                local_value={"currency": local["currency"]},
                external_value={"currency": external["currency"]},
            )
        ]
    if Decimal(str(local["equity"])) != Decimal(str(external["equity"])):
        return [
            DifferenceDraft(
                difference_key=f"balance:{currency}:quantity_mismatch",
                difference_type="quantity_mismatch",
                entity_type="balance",
                local_reference=account_id,
                external_reference=external_reference,
                local_value={"equity": local["equity"]},
                external_value={"equity": external["equity"]},
            )
        ]
    return []


__all__ = [
    "DifferenceDraft",
    "balance_difference_drafts",
    "expected_order_status",
    "external_order_update_status",
    "order_difference_draft",
    "order_difference_drafts",
    "position_difference_drafts",
]
