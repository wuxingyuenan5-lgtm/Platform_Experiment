"""Funding workspace HTTP read contract; financial values serialize as strings."""

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FundingExitPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    expectedRevision: int = Field(ge=0)
    enabled: bool
    takeProfitSpread: Decimal | None = None
    stopLossSpread: Decimal | None = None

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.enabled and self.takeProfitSpread is None and self.stopLossSpread is None:
            raise ValueError("启用自动平仓须设置至少一个可成交价差阈值")
        if (
            self.takeProfitSpread is not None
            and self.stopLossSpread is not None
            and self.stopLossSpread >= self.takeProfitSpread
        ):
            raise ValueError("止损价差须小于止盈价差")
        return self


class FundingExitPlanResponse(BaseModel):
    openInstructionId: str
    revision: int
    enabled: bool
    takeProfitSpread: Decimal | None
    stopLossSpread: Decimal | None
    triggeredAt: str | None
    triggerReason: Literal["take_profit", "stop_loss"] | None
    triggerSpread: Decimal | None
    closeInstructionId: str | None
    lastError: str | None
    updatedAt: str


class FundingSymbolOption(BaseModel):
    baseAsset: str
    quoteCurrency: str
    perpetualSymbol: str
    spotSymbol: str
    perpetualInstrumentId: str
    spotInstrumentId: str


class FundingActiveReservation(BaseModel):
    currency: str
    activeReserved: Decimal
    fundingReserved: Decimal
    crossReserved: Decimal
    fundingAvailable: Decimal | None


class FundingOpenSizingResponse(BaseModel):
    spotQuantity: Decimal | None
    spotBaseFeeRate: Decimal
    expectedSpotNetQuantity: Decimal | None
    perpetualQuantity: Decimal | None
    roundingResidualQuantity: Decimal | None
    estimatedNotional: Decimal | None
    valid: bool
    reason: str | None


class FundingExecutionContextResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    accountId: str
    venue: str
    spotSymbol: str
    perpetualSymbol: str
    symbolOptions: list[FundingSymbolOption]
    spotQuote: dict[str, Any]
    perpetualQuote: dict[str, Any]
    fundingRate: Decimal | None
    nextFundingTime: str | None
    basis: Decimal | None
    executableSpread: dict[str, Decimal | None]
    tickSize: dict[str, Decimal]
    quantityStep: dict[str, Decimal]
    minimumQuantity: dict[str, Decimal]
    contractMultiplier: dict[str, Decimal]
    suggestedQuantity: Decimal | None
    openSizing: FundingOpenSizingResponse | None = None
    requestedNotional: Decimal | None
    availableBalance: dict[str, Any] | None
    activeReservation: FundingActiveReservation
    sharedResourceClaims: list[dict[str, Any]]
    controlledLiveReadiness: dict[str, Any]
    runtime: dict[str, Any]
    dataQualityState: str
    asOf: str


class FundingWorkspaceResponse(BaseModel):
    instruction: dict[str, Any]
    executionBatch: dict[str, Any] | None
    workspaceState: dict[str, Any]


class FundingPositionGroupResponse(BaseModel):
    exitPlan: FundingExitPlanResponse | None = None
    roundingBalanced: bool = False
    model_config = ConfigDict(allow_inf_nan=False)
    isAbnormal: bool = False
    abnormalReason: str | None = None
    abnormalAction: Literal["close_group", "flatten_open", "finish_close", "reconcile"] = (
        "reconcile"
    )
    recoveryCloseInstructionId: str | None = None
    recoveryIdempotencyKey: str | None = None
    recoverySpotQuantity: Decimal | None = None
    instructionId: str
    openInstructionId: str
    batchId: str
    status: str
    perpetualSymbol: str
    spotSymbol: str
    perpetualSide: str
    spotSide: str
    perpetualRequestedQuantity: Decimal
    spotRequestedQuantity: Decimal
    cumulativePerpetualFill: Decimal
    cumulativeSpotFill: Decimal
    hedgedQuantity: Decimal
    spotFeeAdjusted: bool
    netSpotAcquired: Decimal | None
    remainingSpotQuantity: Decimal | None
    remainingPerpetualQuantity: Decimal
    remainingSpotHolding: Decimal | None
    netDeltaQuantity: Decimal | None
    spotFeeResidualQuantity: Decimal | None
    spotQuantityStep: Decimal | None
    residualQuantity: Decimal
    alreadyClosedQuantity: Decimal
    authoritativeClosedQuantity: Decimal
    pendingCloseQuantity: Decimal
    resultUnknownReservedQuantity: Decimal
    remainingClosableQuantity: Decimal
    lifecycleState: Literal["active", "history"]
    fundingFees: Decimal | None
    fees: Decimal | None
    pnl: Decimal | None
    asOf: str
    workspaceState: dict[str, Any]
