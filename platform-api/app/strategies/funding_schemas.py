"""Funding workspace HTTP read contract; financial values serialize as strings."""

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


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
    model_config = ConfigDict(allow_inf_nan=False)
    isAbnormal: bool = False
    abnormalReason: str | None = None
    abnormalAction: Literal["close_group", "flatten_open", "reconcile"] = "reconcile"
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
