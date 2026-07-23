from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CreateOrderRequest(BaseModel):
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = Field(alias="orderType")
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)


class OrderResponse(BaseModel):
    order_id: str = Field(alias="orderId")
    command_id: str = Field(alias="commandId")
    status: str
    external_order_id: str | None = Field(default=None, alias="externalOrderId")


class BatchLegRequest(BaseModel):
    role: str = Field(min_length=1, max_length=32)
    account_id: str | None = Field(default=None, alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = Field(alias="orderType")
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_limit_price(self) -> "BatchLegRequest":
        if self.order_type == "limit" and self.price is None:
            raise ValueError("Limit batch legs require price")
        return self


class CreateExecutionBatchRequest(BaseModel):
    idempotency_key: str | None = Field(
        default=None, alias="idempotencyKey", min_length=1, max_length=128
    )
    strategy_instance_id: str | None = Field(default=None, alias="strategyInstanceId")
    account_id: str | None = Field(default=None, alias="accountId")
    strategy_key: str = Field(alias="strategyKey", min_length=1, max_length=64)
    direction: str = Field(min_length=1, max_length=32)
    legs: list[BatchLegRequest] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_unique_legs(self) -> "CreateExecutionBatchRequest":
        roles = [leg.role for leg in self.legs]
        if len(set(roles)) != len(roles):
            raise ValueError("Execution batch leg roles must be unique")
        if self.account_id is None and any(leg.account_id is None for leg in self.legs):
            raise ValueError("Either batch accountId or every leg accountId must be provided")
        return self


class BatchLegResponse(BaseModel):
    role: str
    account_id: str | None = Field(default=None, alias="accountId")
    order_id: str | None = Field(default=None, alias="orderId")
    status: str
    failure_reason: str | None = Field(default=None, alias="failureReason")


class ExecutionBatchResponse(BaseModel):
    batch_id: str = Field(alias="batchId")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")
    strategy_instance_id: str | None = Field(default=None, alias="strategyInstanceId")
    account_id: str | None = Field(default=None, alias="accountId")
    strategy_key: str = Field(alias="strategyKey")
    direction: str
    status: Literal[
        "pending",
        "executing",
        "partially_executed",
        "hedged",
        "failed",
        "manual_intervention",
    ]
    requires_manual_intervention: bool = Field(alias="requiresManualIntervention")
    failure_reason: str | None = Field(default=None, alias="failureReason")
    legs: list[BatchLegResponse]
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class CreateStrategyRunRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    direction: str = Field(min_length=1, max_length=32)
    reason: str | None = Field(default=None, max_length=256)
    legs: list[BatchLegRequest] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_unique_legs(self) -> "CreateStrategyRunRequest":
        roles = [leg.role for leg in self.legs]
        if len(set(roles)) != len(roles):
            raise ValueError("Strategy run leg roles must be unique")
        if any(leg.account_id is None for leg in self.legs):
            raise ValueError("Every strategy run leg must provide accountId")
        return self


class StrategyRunResponse(BaseModel):
    strategy_run_id: str = Field(alias="strategyRunId")
    idempotency_key: str = Field(alias="idempotencyKey")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    strategy_key: str = Field(alias="strategyKey")
    direction: str
    status: Literal["pending", "executing", "completed", "failed", "manual_intervention"]
    execution_batch_id: str | None = Field(default=None, alias="executionBatchId")
    execution_batch: ExecutionBatchResponse | None = Field(default=None, alias="executionBatch")
    reason: str | None = None
    failure_reason: str | None = Field(default=None, alias="failureReason")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class PositionResponse(BaseModel):
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    net_quantity: Decimal = Field(alias="netQuantity")
    average_price: Decimal | None = Field(alias="averagePrice")


class PnlResponse(BaseModel):
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    realized_pnl: Decimal = Field(alias="realizedPnl")
    trading_pnl: Decimal = Field(alias="tradingPnl")
    fees: Decimal


__all__ = [
    "BatchLegRequest",
    "BatchLegResponse",
    "CreateExecutionBatchRequest",
    "CreateOrderRequest",
    "CreateStrategyRunRequest",
    "ExecutionBatchResponse",
    "OrderResponse",
    "PnlResponse",
    "PositionResponse",
    "StrategyRunResponse",
]
