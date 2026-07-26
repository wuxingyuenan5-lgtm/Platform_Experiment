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
    data_quality_state: str = Field(default="complete", alias="dataQualityState")


class VenueFillHistoryPage(BaseModel):
    source: str
    account_id: str = Field(alias="accountId")
    items: list[VenueFillSnapshot]
    next_cursor: str | None = Field(default=None, alias="nextCursor")
    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="asOf")
    data_quality_state: str = Field(default="complete", alias="dataQualityState")


class VenuePositionSnapshot(BaseModel):
    source: str
    external_position_id: str = Field(alias="externalPositionId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    net_quantity: Decimal = Field(alias="netQuantity")
    average_price: Decimal | None = Field(default=None, alias="averagePrice")
    current_price: Decimal | None = Field(default=None, alias="currentPrice")
    mark_price: Decimal | None = Field(default=None, alias="markPrice")
    break_even_price: Decimal | None = Field(default=None, alias="breakEvenPrice")
    liquidation_price: Decimal | None = Field(default=None, alias="liquidationPrice")
    liquidation_price_source: str = Field(
        default="unavailable", alias="liquidationPriceSource"
    )
    position_value: Decimal | None = Field(default=None, alias="positionValue")
    leverage: Decimal | None = None
    initial_margin: Decimal | None = Field(default=None, alias="initialMargin")
    maintenance_margin: Decimal | None = Field(default=None, alias="maintenanceMargin")
    unrealized_pnl: Decimal | None = Field(default=None, alias="unrealizedPnl")
    realized_pnl: Decimal | None = Field(default=None, alias="realizedPnl")
    stop_loss_price: Decimal | None = Field(default=None, alias="stopLossPrice")
    take_profit_price: Decimal | None = Field(default=None, alias="takeProfitPrice")
    swap: Decimal | None = None
    position_status: str | None = Field(default=None, alias="positionStatus")
    risk_limit_value: Decimal | None = Field(default=None, alias="riskLimitValue")
    reduce_only_restricted: bool | None = Field(default=None, alias="reduceOnlyRestricted")
    auto_add_margin: bool | None = Field(default=None, alias="autoAddMargin")
    currency: str
    as_of: datetime = Field(alias="asOf")
    field_availability: dict[str, str] = Field(default_factory=dict, alias="fieldAvailability")
    data_quality_state: str = Field(default="complete", alias="dataQualityState")


class VenueBalanceSnapshot(BaseModel):
    source: str
    external_balance_id: str = Field(alias="externalBalanceId")
    account_id: str = Field(alias="accountId")
    equity: Decimal
    available_balance: Decimal = Field(alias="availableBalance")
    currency: str
    as_of: datetime = Field(alias="asOf")
    data_quality_state: str = Field(default="complete", alias="dataQualityState")


class VenueAccountRiskSnapshot(BaseModel):
    source: str
    account_id: str = Field(alias="accountId")
    currency: str
    equity: Decimal | None = None
    wallet_balance: Decimal | None = Field(default=None, alias="walletBalance")
    margin_balance: Decimal | None = Field(default=None, alias="marginBalance")
    available_balance: Decimal | None = Field(default=None, alias="availableBalance")
    initial_margin: Decimal | None = Field(default=None, alias="initialMargin")
    maintenance_margin: Decimal | None = Field(default=None, alias="maintenanceMargin")
    unrealized_pnl: Decimal | None = Field(default=None, alias="unrealizedPnl")
    account_im_rate: Decimal | None = Field(default=None, alias="accountImRate")
    account_mm_rate: Decimal | None = Field(default=None, alias="accountMmRate")
    margin_level: Decimal | None = Field(default=None, alias="marginLevel")
    margin_call_level: Decimal | None = Field(default=None, alias="marginCallLevel")
    stop_out_level: Decimal | None = Field(default=None, alias="stopOutLevel")
    margin_threshold_mode: str | None = Field(default=None, alias="marginThresholdMode")
    leverage: Decimal | None = None
    margin_mode: str | None = Field(default=None, alias="marginMode")
    trade_allowed: bool | None = Field(default=None, alias="tradeAllowed")
    expert_trading_allowed: bool | None = Field(default=None, alias="expertTradingAllowed")
    field_availability: dict[str, str] = Field(default_factory=dict, alias="fieldAvailability")
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="asOf")
    data_quality_state: str = Field(default="complete", alias="dataQualityState")


class VenueEconomicEventSnapshot(BaseModel):
    source: str
    external_event_id: str = Field(alias="externalEventId")
    event_type: Literal["funding", "swap", "fee"] = Field(alias="eventType")
    account_id: str = Field(alias="accountId")
    instrument_id: str | None = Field(default=None, alias="instrumentId")
    symbol: str | None = None
    amount: Decimal
    currency: str
    occurred_at: datetime = Field(alias="occurredAt")
    data_quality_state: str = Field(default="complete", alias="dataQualityState")
    payload: dict[str, object] = Field(default_factory=dict)


class GatewayAdapterCapability(BaseModel):
    adapter: str
    environment: str
    configured: bool
    operational: bool
    write_enabled: bool = Field(alias="writeEnabled")
    account_ids: list[str] = Field(default_factory=list, alias="accountIds")
    capabilities: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(
        default_factory=list,
        alias="missingRequirements",
    )
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="checkedAt")


class GatewayCapabilitiesResponse(BaseModel):
    gateway: str
    environment: str
    live_write_enabled: bool = Field(alias="liveWriteEnabled")
    adapters: list[GatewayAdapterCapability]


class CancelOrderRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=512)


class CancelOrderResponse(BaseModel):
    source: str
    external_order_id: str = Field(alias="externalOrderId")
    platform_order_id: str = Field(alias="platformOrderId")
    status: Literal[
        "canceled",
        "already_final",
        "not_found",
        "unsupported",
        "blocked",
        "unknown",
    ]
    reason: str | None = None
    as_of: datetime = Field(alias="asOf")


class RuntimeStatusResponse(BaseModel):
    status: str
    service: str
    environment: str
    gateway: str
    journal: dict[str, object]


class CredentialInspection(BaseModel):
    credential_ref: str = Field(alias="credentialRef")
    provider: str
    secret_name: str = Field(alias="secretName")
    version: str
    configured: bool
    available_fields: list[str] = Field(alias="availableFields")
    missing_fields: list[str] = Field(alias="missingFields")
    env_prefix: str | None = Field(default=None, alias="envPrefix")
    legacy_reference: bool = Field(default=False, alias="legacyReference")


class GatewayConnectivityResponse(BaseModel):
    gateway: str
    credential_count: int = Field(alias="credentialCount")
    configured_credential_count: int = Field(alias="configuredCredentialCount")
    credentials: list[CredentialInspection]


class VenueReadinessResult(BaseModel):
    venue: str
    status: str
    credential_ref: str = Field(alias="credentialRef")
    symbol: str
    market_type: str | None = Field(default=None, alias="marketType")
    checks: list[str] = Field(default_factory=list)
    reason: str | None = None


class VenueReadinessResponse(BaseModel):
    status: str
    venues: list[VenueReadinessResult]


class MarketQuote(BaseModel):
    bid: Decimal
    ask: Decimal
    mid: Decimal
    last: Decimal | None = None
    currency: str


class VenuePosition(BaseModel):
    symbol: str
    side: str
    quantity: Decimal
    average_price: Decimal | None = Field(default=None, alias="averagePrice")
    unrealized_pnl: Decimal | None = Field(default=None, alias="unrealizedPnl")
    external_id: str | None = Field(default=None, alias="externalId")


class CrossSpreadVenueSnapshot(BaseModel):
    venue: str
    symbol: str
    status: str
    quote: MarketQuote | None = None
    positions: list[VenuePosition] = Field(default_factory=list)
    reason: str | None = None


class CrossSpreadMetrics(BaseModel):
    funding_rate: Decimal | None = Field(default=None, alias="fundingRate")
    usdt_usd: Decimal | None = Field(default=None, alias="usdtUsd")
    buyer_inventory_fee: Decimal | None = Field(default=None, alias="buyerInventoryFee")
    seller_inventory_fee: Decimal | None = Field(default=None, alias="sellerInventoryFee")


class CrossSpreadHistoryPoint(BaseModel):
    as_of: datetime = Field(alias="asOf")
    long_spread: Decimal | None = Field(default=None, alias="longSpread")
    short_spread: Decimal | None = Field(default=None, alias="shortSpread")
    bybit_mid: Decimal | None = Field(default=None, alias="bybitMid")
    mt5_mid: Decimal | None = Field(default=None, alias="mt5Mid")


class CrossSpreadSnapshotResponse(BaseModel):
    status: str
    bybit: CrossSpreadVenueSnapshot
    mt5: CrossSpreadVenueSnapshot
    long_spread: Decimal | None = Field(default=None, alias="longSpread")
    short_spread: Decimal | None = Field(default=None, alias="shortSpread")
    metrics: CrossSpreadMetrics = Field(default_factory=CrossSpreadMetrics)
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="asOf")
