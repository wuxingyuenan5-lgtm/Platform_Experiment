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
    time_in_force: Literal["GTC", "IOC", "FOK"] = Field(default="GTC", alias="timeInForce")
    reduce_only: bool = Field(default=False, alias="reduceOnly")
    position_idx: int = Field(default=0, alias="positionIdx", ge=0, le=2)
    max_deviation: int | None = Field(default=None, alias="maxDeviation", ge=0)
    allow_partial_fill: bool = Field(default=True, alias="allowPartialFill")
    max_slippage_bps: Decimal | None = Field(default=None, alias="maxSlippageBps", ge=0)


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
    time_in_force: Literal["GTC", "IOC", "FOK"] = Field(default="GTC", alias="timeInForce")
    reduce_only: bool = Field(default=False, alias="reduceOnly")
    position_idx: int = Field(default=0, alias="positionIdx", ge=0, le=2)
    max_deviation: int | None = Field(default=None, alias="maxDeviation", ge=0)
    allow_partial_fill: bool = Field(default=True, alias="allowPartialFill")
    max_slippage_bps: Decimal | None = Field(default=None, alias="maxSlippageBps", ge=0)

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
    max_leg_delay_ms: int = Field(default=3000, alias="maxLegDelayMs", ge=1, le=60000)
    max_residual_notional: Decimal = Field(default=Decimal("0"), alias="maxResidualNotional", ge=0)
    allow_partial_fill: bool = Field(default=False, alias="allowPartialFill")
    emergency_flatten: bool = Field(default=True, alias="emergencyFlatten")
    disposition_policy: Literal["flatten_filled_legs", "hold_and_escalate"] = Field(
        default="flatten_filled_legs", alias="dispositionPolicy"
    )
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
    filled_quantity: Decimal | None = Field(default=None, alias="filledQuantity")
    average_fill_price: Decimal | None = Field(default=None, alias="averageFillPrice")
    repair_order_id: str | None = Field(default=None, alias="repairOrderId")
    repair_status: str | None = Field(default=None, alias="repairStatus")


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
        "compensating",
        "compensated",
        "risk_unresolved",
        "kill_switch_blocked",
    ]
    requires_manual_intervention: bool = Field(alias="requiresManualIntervention")
    risk_state: str = Field(default="none", alias="riskState")
    residual_notional: Decimal = Field(default=Decimal("0"), alias="residualNotional")
    disposition_status: str | None = Field(default=None, alias="dispositionStatus")
    kill_switch_engaged: bool = Field(default=False, alias="killSwitchEngaged")
    max_leg_delay_ms: int = Field(default=3000, alias="maxLegDelayMs")
    max_residual_notional: Decimal = Field(default=Decimal("0"), alias="maxResidualNotional")
    allow_partial_fill: bool = Field(default=False, alias="allowPartialFill")
    emergency_flatten: bool = Field(default=True, alias="emergencyFlatten")
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


class StrategyV1ReadinessResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    strategy_key: str = Field(alias="strategyKey")
    runnable: bool
    blockers: list[str]
    warnings: list[str]
    latest_run_status: str | None = Field(default=None, alias="latestRunStatus")
    manual_intervention_count: int = Field(alias="manualInterventionCount")
    result_unknown_order_count: int = Field(alias="resultUnknownOrderCount")


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


class RuntimeReadinessResponse(BaseModel):
    backend_status: str = Field(alias="backendStatus")
    database_status: str = Field(alias="databaseStatus")
    runtime_status: str = Field(alias="runtimeStatus")
    default_trading_mode: str = Field(alias="defaultTradingMode")


class TradingSafetyResponse(BaseModel):
    live_trading_enabled: bool = Field(alias="liveTradingEnabled")
    default_trading_environment: str = Field(alias="defaultTradingEnvironment")
    secret_storage_policy: str = Field(alias="secretStoragePolicy")
    live_guard_policy: str = Field(alias="liveGuardPolicy")


class CredentialReferenceResponse(BaseModel):
    credential_id: str = Field(alias="credentialId")
    credential_ref: str = Field(alias="credentialRef")
    venue_id: str = Field(alias="venueId")
    venue_code: str = Field(alias="venueCode")
    environment: str
    purpose: str
    status: str
    created_at: datetime = Field(alias="createdAt")


class ExchangeCredentialInspectionResponse(BaseModel):
    credential_ref: str = Field(alias="credentialRef")
    env_prefix: str = Field(alias="envPrefix")
    configured: bool
    available_fields: list[str] = Field(alias="availableFields")
    missing_fields: list[str] = Field(alias="missingFields")


class ExchangeConnectivityResponse(BaseModel):
    status: str
    gateway: str | None = None
    credential_count: int = Field(default=0, alias="credentialCount")
    configured_credential_count: int = Field(default=0, alias="configuredCredentialCount")
    credentials: list[ExchangeCredentialInspectionResponse] = []


class ExchangeVenueReadinessResult(BaseModel):
    venue: str
    status: str
    credential_ref: str = Field(alias="credentialRef")
    symbol: str
    market_type: str | None = Field(default=None, alias="marketType")
    checks: list[str] = []
    reason: str | None = None


class ExchangeVenueReadinessResponse(BaseModel):
    status: str
    venues: list[ExchangeVenueReadinessResult] = []


class MarketQuoteResponse(BaseModel):
    bid: Decimal
    ask: Decimal
    mid: Decimal
    last: Decimal | None = None
    currency: str


class VenuePositionResponse(BaseModel):
    symbol: str
    side: str
    quantity: Decimal
    average_price: Decimal | None = Field(default=None, alias="averagePrice")
    unrealized_pnl: Decimal | None = Field(default=None, alias="unrealizedPnl")
    external_id: str | None = Field(default=None, alias="externalId")


class CrossSpreadVenueSnapshotResponse(BaseModel):
    venue: str
    symbol: str
    status: str
    quote: MarketQuoteResponse | None = None
    positions: list[VenuePositionResponse] = []
    reason: str | None = None


class CrossSpreadMetricsResponse(BaseModel):
    funding_rate: Decimal | None = Field(default=None, alias="fundingRate")
    usdt_usd: Decimal | None = Field(default=None, alias="usdtUsd")
    buyer_inventory_fee: Decimal | None = Field(default=None, alias="buyerInventoryFee")
    seller_inventory_fee: Decimal | None = Field(default=None, alias="sellerInventoryFee")


class CrossSpreadSnapshotResponse(BaseModel):
    status: str
    bybit: CrossSpreadVenueSnapshotResponse
    mt5: CrossSpreadVenueSnapshotResponse
    long_spread: Decimal | None = Field(default=None, alias="longSpread")
    short_spread: Decimal | None = Field(default=None, alias="shortSpread")
    metrics: CrossSpreadMetricsResponse = Field(default_factory=CrossSpreadMetricsResponse)
    as_of: datetime = Field(alias="asOf")


class CrossSpreadHistoryPointResponse(BaseModel):
    as_of: datetime = Field(alias="asOf")
    long_spread: Decimal | None = Field(default=None, alias="longSpread")
    short_spread: Decimal | None = Field(default=None, alias="shortSpread")
    bybit_mid: Decimal | None = Field(default=None, alias="bybitMid")
    mt5_mid: Decimal | None = Field(default=None, alias="mt5Mid")


class CrossSpreadMarketCommandRequest(BaseModel):
    action: Literal["OPEN_LONG", "CLOSE_LONG", "OPEN_SHORT", "CLOSE_SHORT"]
    quantity_oz: Decimal = Field(alias="quantityOz", gt=0)


class StrategyDefinitionResponse(BaseModel):
    strategy_id: str = Field(alias="strategyId")
    strategy_key: str = Field(alias="strategyKey")
    name: str
    v1_scope: str = Field(alias="v1Scope")
    status: str
    description: str


class StrategyInstanceResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    strategy_id: str = Field(alias="strategyId")
    strategy_key: str = Field(alias="strategyKey")
    strategy_name: str = Field(alias="strategyName")
    version: str
    name: str
    trading_mode: str = Field(alias="tradingMode")
    status: str
    capital_base: Decimal | None = Field(alias="capitalBase")
    base_currency: str = Field(alias="baseCurrency")
    data_quality_state: str = Field(alias="dataQualityState")


class AccountResponse(BaseModel):
    account_id: str = Field(alias="accountId")
    account_code: str = Field(alias="accountCode")
    name: str
    venue_id: str = Field(alias="venueId")
    venue_code: str = Field(alias="venueCode")
    account_type: str = Field(alias="accountType")
    environment: str
    base_currency: str = Field(alias="baseCurrency")
    credential_ref: str | None = Field(alias="credentialRef")
    status: str
    data_quality_state: str = Field(alias="dataQualityState")


class StrategyAccountBindingResponse(BaseModel):
    binding_id: str = Field(alias="bindingId")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    account_code: str = Field(alias="accountCode")
    role: str
    max_notional: Decimal | None = Field(alias="maxNotional")
    status: str


class BalanceSnapshotResponse(BaseModel):
    snapshot_id: str = Field(alias="snapshotId")
    account_id: str = Field(alias="accountId")
    currency: str
    equity: Decimal
    available_balance: Decimal = Field(alias="availableBalance")
    source: str
    data_quality_state: str = Field(alias="dataQualityState")
    as_of: datetime = Field(alias="asOf")


class ContractSpecificationResponse(BaseModel):
    version: str
    price_tick: Decimal = Field(alias="priceTick")
    min_order_quantity: Decimal = Field(alias="minOrderQuantity")
    quantity_step: Decimal = Field(alias="quantityStep")
    contract_multiplier: Decimal = Field(alias="contractMultiplier")
    data_quality_state: str = Field(alias="dataQualityState")


class InstrumentResponse(BaseModel):
    instrument_id: str = Field(alias="instrumentId")
    instrument_code: str = Field(alias="instrumentCode")
    name: str
    instrument_type: str = Field(alias="instrumentType")
    base_currency: str = Field(alias="baseCurrency")
    quote_currency: str = Field(alias="quoteCurrency")
    settle_currency: str = Field(alias="settleCurrency")
    quantity_unit: str = Field(alias="quantityUnit")
    data_quality_state: str = Field(alias="dataQualityState")
    contract: ContractSpecificationResponse | None = None


class CreateTradeCommandRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = Field(alias="orderType")
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    time_in_force: Literal["GTC", "IOC", "FOK"] = Field(default="GTC", alias="timeInForce")
    reduce_only: bool = Field(default=False, alias="reduceOnly")
    position_idx: int = Field(default=0, alias="positionIdx", ge=0, le=2)
    max_deviation: int | None = Field(default=None, alias="maxDeviation", ge=0)
    allow_partial_fill: bool = Field(default=True, alias="allowPartialFill")
    max_slippage_bps: Decimal | None = Field(default=None, alias="maxSlippageBps", ge=0)

    @model_validator(mode="after")
    def validate_limit_price(self) -> "CreateTradeCommandRequest":
        if self.order_type == "limit" and self.price is None:
            raise ValueError("Limit trade commands require price")
        return self


class TradeCommandResponse(BaseModel):
    trade_command_id: str = Field(alias="tradeCommandId")
    idempotency_key: str = Field(alias="idempotencyKey")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    platform_order_id: str | None = Field(alias="platformOrderId")
    status: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class OrderDetailResponse(OrderResponse):
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    side: str
    order_type: str = Field(alias="orderType")
    quantity: Decimal
    price: Decimal | None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class FillResponse(BaseModel):
    fill_id: str = Field(alias="fillId")
    order_id: str = Field(alias="orderId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    side: str
    quantity: Decimal
    price: Decimal
    occurred_at: datetime = Field(alias="occurredAt")


class StrategyPnlResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    realized_pnl: Decimal = Field(alias="realizedPnl")
    trading_pnl: Decimal = Field(alias="tradingPnl")
    fees: Decimal
    currency: str
    data_quality_state: str = Field(alias="dataQualityState")


class StrategyNavSnapshotResponse(BaseModel):
    snapshot_id: str = Field(alias="snapshotId")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    valuation_time: datetime = Field(alias="valuationTime")
    equity: Decimal
    capital_base: Decimal = Field(alias="capitalBase")
    nav: Decimal
    currency: str
    data_quality_state: str = Field(alias="dataQualityState")


class ReconciliationIssueResponse(BaseModel):
    issue_type: str = Field(alias="issueType")
    subject_type: str = Field(alias="subjectType")
    subject_id: str = Field(alias="subjectId")
    strategy_instance_id: str | None = Field(default=None, alias="strategyInstanceId")
    severity: Literal["warning", "action_required"] = "action_required"
    message: str
    detected_at: datetime = Field(alias="detectedAt")


class ReconciliationSummaryResponse(BaseModel):
    status: Literal["ok", "action_required"]
    manual_intervention_batch_count: int = Field(alias="manualInterventionBatchCount")
    result_unknown_order_count: int = Field(alias="resultUnknownOrderCount")
    issues: list[ReconciliationIssueResponse]


class AuditEventResponse(BaseModel):
    audit_event_id: str = Field(alias="auditEventId")
    event_type: str = Field(alias="eventType")
    subject_type: str = Field(alias="subjectType")
    subject_id: str = Field(alias="subjectId")
    details_json: str = Field(alias="detailsJson")
    created_at: datetime = Field(alias="createdAt")


class KillSwitchRequest(BaseModel):
    engaged: bool
    reason: str = Field(min_length=1, max_length=512)


class KillSwitchResponse(BaseModel):
    scope_type: Literal["global", "strategy", "account"] = Field(alias="scopeType")
    scope_id: str = Field(alias="scopeId")
    engaged: bool
    reason: str | None = None
    updated_at: datetime = Field(alias="updatedAt")


class ExecutionDispositionRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    action: Literal["flatten_filled_legs", "hold_and_escalate", "mark_resolved"]
    reason: str = Field(min_length=1, max_length=512)


class ExecutionDispositionResponse(BaseModel):
    disposition_id: str = Field(alias="dispositionId")
    idempotency_key: str = Field(alias="idempotencyKey")
    batch_id: str = Field(alias="batchId")
    action: str
    status: str
    details_json: str = Field(alias="detailsJson")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
