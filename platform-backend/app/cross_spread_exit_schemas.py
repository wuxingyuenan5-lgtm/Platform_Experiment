from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.execution_schemas import ExecutionBatchResponse

SpreadDirection = Literal["LONG_SPREAD", "SHORT_SPREAD"]
ExecutionMode = Literal["market", "limit"]
ExitPlanStatus = Literal[
    "active",
    "triggered",
    "closing",
    "closed",
    "manual_intervention",
]


class CrossSpreadMarketOpenRequest(BaseModel):
    direction: SpreadDirection
    quantity_oz: Decimal = Field(alias="quantityOz", gt=0)
    take_profit_spread: Decimal = Field(alias="takeProfitSpread")
    stop_loss_spread: Decimal = Field(alias="stopLossSpread")
    execution_mode: ExecutionMode = Field(default="market", alias="executionMode")

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "CrossSpreadMarketOpenRequest":
        if self.direction == "LONG_SPREAD":
            if self.take_profit_spread <= self.stop_loss_spread:
                raise ValueError(
                    "LONG_SPREAD take-profit exit spread must be above stop-loss exit spread"
                )
        elif self.take_profit_spread >= self.stop_loss_spread:
            raise ValueError(
                "SHORT_SPREAD take-profit exit spread must be below stop-loss exit spread"
            )
        return self


class CrossSpreadMarketCloseRequest(BaseModel):
    execution_mode: ExecutionMode = Field(default="market", alias="executionMode")


class CrossSpreadExitPlanResponse(BaseModel):
    plan_id: str = Field(alias="planId")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    open_batch_id: str = Field(alias="openBatchId")
    close_batch_id: str | None = Field(default=None, alias="closeBatchId")
    direction: SpreadDirection
    quantity_oz: Decimal = Field(alias="quantityOz")
    mt5_position_id: str = Field(alias="mt5PositionId")
    entry_spread: Decimal = Field(alias="entrySpread")
    take_profit_spread: Decimal = Field(alias="takeProfitSpread")
    stop_loss_spread: Decimal = Field(alias="stopLossSpread")
    status: ExitPlanStatus
    trigger_reason: str | None = Field(default=None, alias="triggerReason")
    trigger_spread: Decimal | None = Field(default=None, alias="triggerSpread")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    triggered_at: datetime | None = Field(default=None, alias="triggeredAt")
    closed_at: datetime | None = Field(default=None, alias="closedAt")


class CrossSpreadOpenResult(BaseModel):
    execution_batch: ExecutionBatchResponse = Field(alias="executionBatch")
    exit_plan: CrossSpreadExitPlanResponse = Field(alias="exitPlan")


class CrossSpreadCloseResult(BaseModel):
    execution_batch: ExecutionBatchResponse = Field(alias="executionBatch")
    exit_plan: CrossSpreadExitPlanResponse = Field(alias="exitPlan")


class CrossSpreadExitEvaluationResponse(BaseModel):
    evaluated_count: int = Field(alias="evaluatedCount")
    triggered_count: int = Field(alias="triggeredCount")
    skipped_reason: str | None = Field(default=None, alias="skippedReason")
