from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DifferenceType = Literal[
    "missing_local",
    "missing_external",
    "quantity_mismatch",
    "price_mismatch",
    "currency_mismatch",
    "status_mismatch",
]
DifferenceStatus = Literal["open", "resolved", "accepted"]


class VenueReconciliationRunRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    actor: str = Field(min_length=1, max_length=128)


class VenueReconciliationRunResponse(BaseModel):
    run_id: str = Field(alias="runId")
    idempotency_key: str = Field(alias="idempotencyKey")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    run_type: str = Field(alias="runType")
    source: str
    status: str
    order_count: int = Field(alias="orderCount")
    fill_count: int = Field(alias="fillCount")
    position_count: int = Field(alias="positionCount")
    balance_count: int = Field(alias="balanceCount")
    fact_count: int = Field(alias="factCount")
    difference_count: int = Field(alias="differenceCount")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class ReconciliationDifferenceResponse(BaseModel):
    difference_id: str = Field(alias="differenceId")
    run_id: str = Field(alias="runId")
    difference_key: str = Field(alias="differenceKey")
    difference_type: DifferenceType = Field(alias="differenceType")
    entity_type: str = Field(alias="entityType")
    local_reference: str | None = Field(default=None, alias="localReference")
    external_reference: str | None = Field(default=None, alias="externalReference")
    local_value: dict[str, object] = Field(alias="localValue")
    external_value: dict[str, object] = Field(alias="externalValue")
    status: DifferenceStatus
    resolution_actor: str | None = Field(default=None, alias="resolutionActor")
    resolution_reason: str | None = Field(default=None, alias="resolutionReason")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")
    created_at: datetime = Field(alias="createdAt")


class ResolveDifferenceRequest(BaseModel):
    status: Literal["resolved", "accepted"]
    actor: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)


class OrderVenueReconciliationResponse(BaseModel):
    order_id: str = Field(alias="orderId")
    command_id: str = Field(alias="commandId")
    source: str
    external_order_id: str | None = Field(default=None, alias="externalOrderId")
    status_before: str = Field(alias="statusBefore")
    status_after: str = Field(alias="statusAfter")
    recovered: bool
    imported_fact_ids: list[str] = Field(alias="importedFactIds")
    difference_ids: list[str] = Field(alias="differenceIds")
    reconciled_at: datetime = Field(alias="reconciledAt")


__all__ = [
    "DifferenceStatus",
    "DifferenceType",
    "OrderVenueReconciliationResponse",
    "ReconciliationDifferenceResponse",
    "ResolveDifferenceRequest",
    "VenueReconciliationRunRequest",
    "VenueReconciliationRunResponse",
]
