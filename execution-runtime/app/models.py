from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SubmitOrderCommand(BaseModel):
    command_id: UUID
    platform_order_id: UUID
    account_id: UUID
    instrument_id: UUID
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = "market"
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)


class ExecutionEvent(BaseModel):
    event_id: UUID
    command_id: UUID
    platform_order_id: UUID
    event_type: Literal["order_acknowledged", "order_filled", "order_rejected"]
    external_order_id: str | None = None
    fill_price: Decimal | None = None
    fill_quantity: Decimal | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason: str | None = None
