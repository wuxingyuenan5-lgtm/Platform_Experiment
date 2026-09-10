from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ObservabilityState = Literal["complete", "partial", "unavailable"]
SectionState = Literal["complete", "unavailable"]


class VenueAccountRiskSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    source: str
    accountId: str
    currency: str
    equity: Decimal | None = None
    walletBalance: Decimal | None = None
    marginBalance: Decimal | None = None
    availableBalance: Decimal | None = None
    initialMargin: Decimal | None = None
    maintenanceMargin: Decimal | None = None
    unrealizedPnl: Decimal | None = None
    accountImRate: Decimal | None = None
    accountMmRate: Decimal | None = None
    marginLevel: Decimal | None = None
    marginCallLevel: Decimal | None = None
    stopOutLevel: Decimal | None = None
    marginThresholdMode: str | None = None
    leverage: Decimal | None = None
    marginMode: str | None = None
    tradeAllowed: bool | None = None
    expertTradingAllowed: bool | None = None
    fieldAvailability: dict[str, str] | None = None
    asOf: str
    dataQualityState: str


class VenuePositionSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    source: str
    externalPositionId: str
    accountId: str
    instrumentId: str
    symbol: str
    netQuantity: Decimal
    averagePrice: Decimal | None = None
    currentPrice: Decimal | None = None
    markPrice: Decimal | None = None
    breakEvenPrice: Decimal | None = None
    liquidationPrice: Decimal | None = None
    liquidationPriceSource: str
    positionValue: Decimal | None = None
    leverage: Decimal | None = None
    initialMargin: Decimal | None = None
    maintenanceMargin: Decimal | None = None
    unrealizedPnl: Decimal | None = None
    realizedPnl: Decimal | None = None
    stopLossPrice: Decimal | None = None
    takeProfitPrice: Decimal | None = None
    swap: Decimal | None = None
    positionStatus: str | None = None
    currency: str
    fieldAvailability: dict[str, str] | None = None
    dataQualityState: str
    asOf: str
    openTime: str | None = None


class VenueOrderSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    source: str
    externalOrderId: str
    platformOrderId: str
    accountId: str
    symbol: str
    side: Literal["buy"] | Literal["sell"]
    orderType: Literal["market"] | Literal["limit"]
    quantity: Decimal
    filledQuantity: Decimal
    remainingQuantity: Decimal
    price: Decimal | None = None
    averageFillPrice: Decimal | None = None
    status: str
    reduceOnly: bool | None = None
    positionIndex: int | None = None
    positionId: str | None = None
    timeInForce: str | None = None
    rejectReason: str | None = None
    cancelReason: str | None = None
    dataQualityState: str
    asOf: str


class VenueFillSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    source: str
    externalFillId: str
    externalOrderId: str
    accountId: str
    symbol: str
    side: Literal["buy"] | Literal["sell"]
    quantity: Decimal
    price: Decimal
    fee: Decimal | None
    currency: str
    occurredAt: str
    dataQualityState: str


class CrossSpreadVenueObservabilityResponse(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
    venue: str
    account_id: str = Field(alias="accountId")
    symbol: str
    status: ObservabilityState
    section_states: dict[str, SectionState] = Field(alias="sectionStates")
    account_risk: VenueAccountRiskSnapshotResponse | None = Field(default=None, alias="accountRisk")
    positions: list[VenuePositionSnapshotResponse] = Field(default_factory=list)
    active_orders: list[VenueOrderSnapshotResponse] = Field(
        default_factory=list, alias="activeOrders"
    )
    recent_orders: list[VenueOrderSnapshotResponse] = Field(
        default_factory=list, alias="recentOrders"
    )
    recent_fills: list[VenueFillSnapshotResponse] = Field(default_factory=list, alias="recentFills")
    warnings: list[str] = Field(default_factory=list)


class CrossSpreadObservabilityResponse(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
    status: ObservabilityState
    history_hours: int = Field(alias="historyHours")
    bybit: CrossSpreadVenueObservabilityResponse
    mt5: CrossSpreadVenueObservabilityResponse
    warnings: list[str] = Field(default_factory=list)
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="asOf")
