from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class SubmitOrderCommand(BaseModel):
    command_id: str
    platform_order_id: str
    strategy_instance_id: str | None = None
    account_id: str
    instrument_id: str
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = "market"
    execution_policy: Literal["default", "fok", "post_only_chase"] = "default"
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    reduce_only: bool = False
    position_id: str | None = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_execution_target(self) -> "SubmitOrderCommand":
        if self.position_id is not None and not self.reduce_only:
            raise ValueError("position_id requires reduce_only")
        if self.execution_policy != "default" and self.order_type != "limit":
            raise ValueError("FOK and PostOnly Chase policies require a limit order")
        return self


class ExecutionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    command_id: str
    platform_order_id: str
    event_type: Literal["order_acknowledged", "order_filled", "order_rejected"]
    external_order_id: str | None = None
    fill_price: Decimal | None = None
    fill_quantity: Decimal | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason: str | None = None


class VenueOrderSnapshot(BaseModel):
    source: str
    external_order_id: str = Field(alias="externalOrderId")
    platform_order_id: str = Field(alias="platformOrderId")
    command_id: str = Field(alias="commandId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = Field(alias="orderType")
    quantity: Decimal
    price: Decimal | None = None
    status: Literal[
        "accepted",
        "partially_filled",
        "filled",
        "canceled",
        "rejected",
        "unknown",
    ]
    filled_quantity: Decimal = Field(alias="filledQuantity")
    remaining_quantity: Decimal = Field(default=Decimal("0"), alias="remainingQuantity")
    average_fill_price: Decimal | None = Field(default=None, alias="averageFillPrice")
    external_client_id: str | None = Field(default=None, alias="externalClientId")
    reduce_only: bool | None = Field(default=None, alias="reduceOnly")
    position_index: int | None = Field(default=None, alias="positionIndex")
    position_id: str | None = Field(default=None, alias="positionId")
    time_in_force: str | None = Field(default=None, alias="timeInForce")
    reject_reason: str | None = Field(default=None, alias="rejectReason")
    cancel_reason: str | None = Field(default=None, alias="cancelReason")
    occurred_at: datetime = Field(alias="occurredAt")
    as_of: datetime = Field(alias="asOf")
    data_quality_state: str = Field(default="complete", alias="dataQualityState")


class VenueInstrumentSpecification(BaseModel):
    source: str
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    status: str
    min_quantity: Decimal = Field(alias="minQuantity")
    quantity_step: Decimal = Field(alias="quantityStep")
    max_market_quantity: Decimal | None = Field(default=None, alias="maxMarketQuantity")
    contract_size: Decimal = Field(alias="contractSize")
    trade_mode: str
    filling_mode: str
    access_checks: dict[str, object] = Field(default_factory=dict, alias="accessChecks")
    as_of: datetime = Field(alias="asOf")
    data_quality_state: str = Field(default="complete", alias="dataQualityState")


class VenueFillSnapshot(BaseModel):
    source: str
    external_fill_id: str = Field(alias="externalFillId")
    external_order_id: str = Field(alias="externalOrderId")
    platform_order_id: str = Field(alias="platformOrderId")
    command_id: str = Field(alias="commandId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    side: Literal["buy", "sell"]
    quantity: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")
    currency: str
    occurred_at: datetime = Field(alias="occurredAt")
    data_quality_state: str = Field(default="complete", alias="dataQualityState")


class VenueOrderHistoryPage(BaseModel):
    source: str
    account_id: str = Field(alias="accountId")
    items: list[VenueOrderSnapshot]
    next_cursor: str | None = Field(default=None, alias="nextCursor")
    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="asOf")
