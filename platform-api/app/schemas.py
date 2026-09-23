from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.execution_schemas import (
    BatchLegRequest as BatchLegRequest,
)
from app.execution_schemas import (
    BatchLegResponse as BatchLegResponse,
)
from app.execution_schemas import (
    CreateExecutionBatchRequest as CreateExecutionBatchRequest,
)
from app.execution_schemas import (
    CreateOrderRequest as CreateOrderRequest,
)
from app.execution_schemas import (
    CreateStrategyRunRequest as CreateStrategyRunRequest,
)
from app.execution_schemas import (
    ExecutionBatchResponse as ExecutionBatchResponse,
)
from app.execution_schemas import (
    OrderResponse as OrderResponse,
)
from app.execution_schemas import (
    PnlResponse as PnlResponse,
)
from app.execution_schemas import (
    PositionResponse as PositionResponse,
)
from app.execution_schemas import (
    StrategyRunResponse as StrategyRunResponse,
)
from app.execution_schemas import (
    StrategyV1ReadinessResponse as StrategyV1ReadinessResponse,
)
from app.financial_read_schemas import (
    AssetBreakdownResponse,
    CoinBalanceResponse,
    EconomicEventResponse,
    FinancialAmountsResponse,
    FinancialCoverageResponse,
    FinancialTimelinePointResponse,
)


class RuntimeReadinessResponse(BaseModel):
    backend_status: str = Field(alias="backendStatus")
    database_status: str = Field(alias="databaseStatus")
    runtime_status: str = Field(alias="runtimeStatus")
    default_trading_mode: str = Field(alias="defaultTradingMode")


class TradingSafetyResponse(BaseModel):
    live_trading_enabled: bool = Field(alias="liveTradingEnabled")
    default_trading_environment: str = Field(alias="defaultTradingEnvironment")
    founder_demo_local_self_approval_enabled: bool = Field(
        alias="founderDemoLocalSelfApprovalEnabled"
    )
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
    account_id: str | None = Field(default=None, alias="accountId")
    currency: str | None = None
    as_of: datetime | None = Field(default=None, alias="asOf")


class CrossSpreadVenueSnapshotResponse(BaseModel):
    venue: str
    symbol: str
    status: str
    quote: MarketQuoteResponse | None = None
    positions: list[VenuePositionResponse] = []
    reason: str | None = None
    open_allowed: bool = Field(default=False, alias="openAllowed")
    close_allowed: bool = Field(default=False, alias="closeAllowed")
    execution_block_reason: str | None = Field(default=None, alias="executionBlockReason")
    market_status: Literal["open", "closed", "buffer", "unknown"] = Field(
        default="unknown", alias="marketStatus"
    )
    trading_hours: str | None = Field(default=None, alias="tradingHours")
    trading_timezone: str | None = Field(default=None, alias="tradingTimezone")
    automatic_exit_allowed: bool = Field(default=False, alias="automaticExitAllowed")
    automatic_exit_block_reason: str | None = Field(default=None, alias="automaticExitBlockReason")
    automatic_exit_guard_minutes: int | None = Field(
        default=None, alias="automaticExitGuardMinutes"
    )
    quote_source_as_of: datetime | None = Field(default=None, alias="quoteSourceAsOf")
    fetch_latency_ms: float | None = Field(default=None, alias="fetchLatencyMs")
    as_of: datetime | None = Field(default=None, alias="asOf")


class CrossSpreadMetricsResponse(BaseModel):
    funding_rate: Decimal | None = Field(default=None, alias="fundingRate")
    usdt_usd: Decimal | None = Field(default=None, alias="usdtUsd")
    buyer_inventory_fee: Decimal | None = Field(default=None, alias="buyerInventoryFee")
    seller_inventory_fee: Decimal | None = Field(default=None, alias="sellerInventoryFee")


class CrossSpreadPositionPnlResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, json_schema_serialization_defaults_required=True)

    planId: str
    planUpdatedAt: datetime
    quantityOz: Decimal
    direction: str = ""
    bybitQuantity: Decimal | None = None
    mt5Quantity: Decimal | None = None
    mt5PositionId: str | None = None
    bybitEntryPrice: Decimal | None = None
    mt5EntryPrice: Decimal | None = None
    bybitPnlUsdt: Decimal | None = None
    mt5PnlUsdt: Decimal | None = None
    totalPnlUsdt: Decimal | None = None
    openTime: datetime
    dataQualityState: Literal["complete", "partial", "unavailable"]
    reason: str | None = None


class CrossSpreadUnattributedPositionResponse(VenuePositionResponse):
    venue: Literal["bybit", "mt5"]


class CrossSpreadAbnormalOrderResponse(BaseModel):
    batchId: str
    planId: str | None = None
    label: str
    direction: str
    bybitRemainingQuantity: Decimal | None = None
    mt5RemainingQuantity: Decimal | None = None
    bybitCloseFilledQuantity: Decimal = Decimal("0")
    mt5CloseFilledQuantity: Decimal = Decimal("0")
    mt5PositionId: str | None = None
    closeQuantityOz: Decimal | None = None
    mt5PendingCloseQuantity: Decimal | None = None
    recoveryIdempotencyKey: str | None = None
    action: Literal["finish_mt5", "close_group", "flatten_open", "reconcile"] = "reconcile"
    reason: str | None = None


class CrossSpreadPositionOverviewResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, json_schema_serialization_defaults_required=True)

    groups: list[CrossSpreadPositionPnlResponse] = Field(default_factory=list)
    abnormalOrders: list[CrossSpreadAbnormalOrderResponse] = Field(default_factory=list)
    unattributedPositions: list[CrossSpreadUnattributedPositionResponse] = Field(
        default_factory=list
    )
    bybitPnlUsdt: Decimal | None = None
    mt5PnlUsdt: Decimal | None = None
    totalPnlUsdt: Decimal | None = None
    dataQualityState: Literal["complete", "partial", "unavailable"]
    asOf: datetime


class CrossSpreadSnapshotResponse(BaseModel):
    status: str
    bybit: CrossSpreadVenueSnapshotResponse
    mt5: CrossSpreadVenueSnapshotResponse
    long_spread: Decimal | None = Field(default=None, alias="longSpread")
    short_spread: Decimal | None = Field(default=None, alias="shortSpread")
    metrics: CrossSpreadMetricsResponse = Field(default_factory=CrossSpreadMetricsResponse)
    execution_state: Literal["executable", "monitor_only", "unavailable"] = Field(
        default="unavailable", alias="executionState"
    )
    position_overview: CrossSpreadPositionOverviewResponse | None = Field(
        default=None, alias="positionOverview"
    )
    as_of: datetime = Field(alias="asOf")


class CrossSpreadVenueTradingRuleResponse(BaseModel):
    venue: Literal["bybit", "mt5"]
    source: str
    account_id: str = Field(alias="accountId")
    symbol: str
    status: str
    price_tick: Decimal = Field(alias="priceTick")
    min_quantity: Decimal = Field(alias="minQuantity")
    quantity_step: Decimal = Field(alias="quantityStep")
    max_market_quantity: Decimal | None = Field(default=None, alias="maxMarketQuantity")
    contract_size: Decimal = Field(alias="contractSize")
    trade_mode: str = Field(alias="tradeMode")
    filling_mode: str = Field(alias="fillingMode")
    access_checks: dict[str, object] = Field(default_factory=dict, alias="accessChecks")
    open_allowed: bool = Field(alias="openAllowed")
    close_allowed: bool = Field(alias="closeAllowed")
    execution_block_reason: str | None = Field(default=None, alias="executionBlockReason")
    market_status: Literal["open", "closed", "buffer", "unknown"] = Field(
        default="unknown", alias="marketStatus"
    )
    trading_hours: str | None = Field(default=None, alias="tradingHours")
    trading_timezone: str | None = Field(default=None, alias="tradingTimezone")
    automatic_exit_allowed: bool = Field(default=False, alias="automaticExitAllowed")
    automatic_exit_block_reason: str | None = Field(default=None, alias="automaticExitBlockReason")
    automatic_exit_guard_minutes: int | None = Field(
        default=None, alias="automaticExitGuardMinutes"
    )
    quote_source_as_of: datetime | None = Field(default=None, alias="quoteSourceAsOf")
    as_of: datetime = Field(alias="asOf")


class CrossSpreadTradingRulesResponse(BaseModel):
    bybit: CrossSpreadVenueTradingRuleResponse
    mt5: CrossSpreadVenueTradingRuleResponse
    execution_state: Literal["executable", "monitor_only", "unavailable"] = Field(
        alias="executionState"
    )
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
    idempotency_key: str | None = Field(
        default=None,
        alias="idempotencyKey",
        min_length=1,
        max_length=128,
    )


class CrossSpreadPreflightRequest(BaseModel):
    action: Literal["OPEN_LONG", "CLOSE_LONG", "OPEN_SHORT", "CLOSE_SHORT"]
    quantity_oz: Decimal = Field(alias="quantityOz", gt=0)
    exit_plan_id: str | None = Field(default=None, alias="exitPlanId")


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
    capability: Literal["trade_and_read", "read_only"]
    max_notional: Decimal | None = Field(alias="maxNotional")
    status: str


class BalanceSnapshotResponse(BaseModel):
    snapshot_id: str = Field(alias="snapshotId")
    account_id: str = Field(alias="accountId")
    currency: str
    equity: Decimal
    available_balance: Decimal | None = Field(default=None, alias="availableBalance")
    source: str
    data_quality_state: str = Field(alias="dataQualityState")
    as_of: datetime = Field(alias="asOf")


class AccountRiskSnapshotResponse(BaseModel):
    account_id: str = Field(alias="accountId")
    currency: str
    equity: Decimal | None = None
    margin: Decimal | None = None
    free_margin: Decimal | None = Field(default=None, alias="freeMargin")
    margin_level: Decimal | None = Field(default=None, alias="marginLevel")
    data_quality_state: str = Field(alias="dataQualityState")
    as_of: datetime = Field(alias="asOf")
    asset_scope: str = Field(default="unspecified", alias="assetScope")
    total_assets: Decimal | None = Field(default=None, alias="totalAssets")
    asset_breakdown: list[AssetBreakdownResponse] = Field(
        default_factory=list, alias="assetBreakdown"
    )
    asset_overview_as_of: datetime | None = Field(default=None, alias="assetOverviewAsOf")
    asset_overview_quality: str = Field(default="unavailable", alias="assetOverviewQuality")
    wallet_balance: Decimal | None = Field(default=None, alias="walletBalance")
    margin_balance: Decimal | None = Field(default=None, alias="marginBalance")
    maintenance_margin: Decimal | None = Field(default=None, alias="maintenanceMargin")
    unrealized_pnl: Decimal | None = Field(default=None, alias="unrealizedPnl")


class StrategyEquityHistoryPointResponse(BaseModel):
    equity_drawdown: Decimal | None = Field(default=None, alias="equityDrawdown")
    total_assets_drawdown: Decimal | None = Field(default=None, alias="totalAssetsDrawdown")
    equity_drawdown_quality: str = Field(default="unavailable", alias="equityDrawdownQuality")
    total_assets_drawdown_quality: str = Field(
        default="unavailable", alias="totalAssetsDrawdownQuality"
    )
    total_assets: Decimal | None = Field(default=None, alias="totalAssets")
    as_of: datetime = Field(alias="asOf")
    equity: Decimal
    currency: str | None = None
    asset_scope: str = Field(default="unspecified", alias="assetScope")


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
    instruction_id: str | None = Field(default=None, alias="instructionId")
    batch_id: str | None = Field(default=None, alias="batchId")
    action: str | None = None
    direction: str | None = None
    time_quality: str = Field(default="legacy", alias="timeQuality")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    symbol: str
    side: str
    order_type: str = Field(alias="orderType")
    quantity: Decimal
    price: Decimal | None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    filled_quantity: Decimal | None = Field(default=None, alias="filledQuantity")
    average_fill_price: Decimal | None = Field(default=None, alias="averageFillPrice")
    reduce_only: bool | None = Field(default=None, alias="reduceOnly")
    time_in_force: str | None = Field(default=None, alias="timeInForce")
    reject_reason: str | None = Field(default=None, alias="rejectReason")
    cancel_reason: str | None = Field(default=None, alias="cancelReason")


class FillResponse(BaseModel):
    fill_id: str = Field(alias="fillId")
    order_id: str = Field(alias="orderId")
    account_id: str = Field(alias="accountId")
    instrument_id: str = Field(alias="instrumentId")
    side: str
    quantity: Decimal
    price: Decimal
    occurred_at: datetime = Field(alias="occurredAt")
    symbol: str | None = None
    fee: Decimal | None = None
    currency: str | None = None
    realized_pnl: Decimal | None = Field(default=None, alias="realizedPnl")
    swap: Decimal | None = None
    origin: str = "legacy"
    source: str | None = None
    external_fill_id: str | None = Field(default=None, alias="externalFillId")
    external_order_id: str | None = Field(default=None, alias="externalOrderId")
    instruction_id: str | None = Field(default=None, alias="instructionId")
    batch_id: str | None = Field(default=None, alias="batchId")
    action: str | None = None
    direction: str | None = None
    order_confirmed_at: datetime | None = Field(default=None, alias="orderConfirmedAt")
    time_quality: str = Field(default="legacy", alias="timeQuality")


class StrategyPnlResponse(BaseModel):
    valuation_policy: str = Field(default="continuous", alias="valuationPolicy")
    valuation_as_of: datetime | None = Field(default=None, alias="valuationAsOf")
    valuation_market_status: str | None = Field(default=None, alias="valuationMarketStatus")
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    realized_pnl: Decimal | None = Field(alias="realizedPnl")
    trading_pnl: Decimal | None = Field(alias="tradingPnl")
    fees: Decimal | None
    currency: str
    data_quality_state: str = Field(alias="dataQualityState")
    funding_pnl: Decimal | None = Field(default=None, alias="fundingPnl")
    swap_pnl: Decimal | None = Field(default=None, alias="swapPnl")
    net_pnl: Decimal | None = Field(default=None, alias="netPnl")
    by_currency: list[FinancialAmountsResponse] = Field(default_factory=list, alias="byCurrency")
    by_account: list[FinancialAmountsResponse] = Field(default_factory=list, alias="byAccount")
    positions: list[dict[str, object]] = Field(default_factory=list)
    timeline: list[FinancialTimelinePointResponse] = Field(default_factory=list)
    coverage: list[FinancialCoverageResponse] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    unattributed_events: list[EconomicEventResponse] = Field(
        default_factory=list, alias="unattributedEvents"
    )
    economic_events: list[EconomicEventResponse] = Field(
        default_factory=list, alias="economicEvents"
    )
    strategy_daily_pnl: list[dict[str, object]] = Field(
        default_factory=list, alias="strategyDailyPnl"
    )
    scope: str = "strategy"


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


class StrategyDailyPnlPointResponse(BaseModel):
    """One cash-flow-adjusted daily result of the account behind a strategy.

    ``pnl`` is the account's equity move between two same-scope daily closings
    with deposits and withdrawals removed, so trading result, funding, fees,
    swap and the day's unrealised mark are all inside it. A day that cannot be
    valued carries no amount and names the reason in ``quality`` instead of
    reporting a zero.
    """

    date: str
    currency: str
    pnl: Decimal | None = None
    return_rate: Decimal | None = Field(default=None, alias="returnRate")
    equity_open: Decimal | None = Field(default=None, alias="equityOpen")
    equity_close: Decimal | None = Field(default=None, alias="equityClose")
    quality: str = "unavailable"


class StrategyAccountSnapshotResponse(BaseModel):
    session_equity_history: list[StrategyEquityHistoryPointResponse] = Field(
        default_factory=list, alias="sessionEquityHistory"
    )
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str | None = Field(default=None, alias="accountId")
    account_code: str | None = Field(default=None, alias="accountCode")
    capability: Literal["trade_and_read", "read_only"] | None = None
    data_quality_state: str = Field(alias="dataQualityState")
    as_of: datetime | None = Field(default=None, alias="asOf")
    balance: BalanceSnapshotResponse | None = None
    equity_history: list[StrategyEquityHistoryPointResponse] = Field(
        default_factory=list, alias="equityHistory"
    )
    daily_pnl: list[StrategyDailyPnlPointResponse] = Field(default_factory=list, alias="dailyPnl")
    strategy_daily_pnl: list[dict[str, object]] = Field(
        default_factory=list, alias="strategyDailyPnl"
    )
    account_risk: AccountRiskSnapshotResponse | None = Field(default=None, alias="accountRisk")
    positions: list[PositionResponse] = Field(default_factory=list)
    position_value: Decimal | None = Field(default=None, alias="positionValue")
    position_value_net: Decimal | None = Field(default=None, alias="positionValueNet")
    position_value_currency: str | None = Field(default=None, alias="positionValueCurrency")
    leverage: Decimal | None = None
    venue_leverage: Decimal | None = Field(default=None, alias="venueLeverage")
    orders: list[OrderDetailResponse] = Field(default_factory=list)
    fills: list[FillResponse] = Field(default_factory=list)
    pnl: PnlResponse | None = None
    finance: StrategyPnlResponse | None = None
    sync_status: str | None = Field(default=None, alias="syncStatus")
    sync_error_code: str | None = Field(default=None, alias="syncErrorCode")
    financial_sync_status: str = Field(default="waiting_initial_sync", alias="financialSyncStatus")
    financial_sync_error_code: str | None = Field(default=None, alias="financialSyncErrorCode")
    last_successful_financial_sync_at: datetime | None = Field(
        default=None, alias="lastSuccessfulFinancialSyncAt"
    )
    snapshot_scope: Literal["account", "strategy"] = Field(
        default="strategy", alias="snapshotScope"
    )
    is_stale: bool = Field(default=True, alias="isStale")
    last_successful_sync_at: datetime | None = Field(default=None, alias="lastSuccessfulSyncAt")
    history_start: datetime | None = Field(default=None, alias="historyStart")
    history_end: datetime | None = Field(default=None, alias="historyEnd")
    coin_balances: list[CoinBalanceResponse] = Field(default_factory=list, alias="coinBalances")
    economic_events: list[EconomicEventResponse] = Field(
        default_factory=list, alias="economicEvents"
    )
    economic_events_quality: str = Field(default="unavailable", alias="economicEventsQuality")
    orders_total: int = Field(default=0, alias="ordersTotal")
    fills_total: int = Field(default=0, alias="fillsTotal")


class StrategyManagementOverviewResponse(BaseModel):
    desk_key: str = Field(alias="deskKey")
    sort_order: int = Field(alias="sortOrder")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    strategy_id: str = Field(alias="strategyId")
    strategy_key: str = Field(alias="strategyKey")
    strategy_name: str = Field(alias="strategyName")
    instance_name: str = Field(alias="instanceName")
    category: str
    v1_scope: str = Field(alias="v1Scope")
    operating_status: str = Field(alias="operatingStatus")
    trading_mode: str = Field(alias="tradingMode")
    data_quality_state: str = Field(alias="dataQualityState")
    active_capability: str = Field(alias="activeCapability")
    binding_count: int = Field(alias="bindingCount")
    latest_run_status: str | None = Field(default=None, alias="latestRunStatus")
    latest_run_at: datetime | None = Field(default=None, alias="latestRunAt")
    primary_account_code: str | None = Field(default=None, alias="primaryAccountCode")
    primary_account_status: str | None = Field(default=None, alias="primaryAccountStatus")
    primary_account_data_quality_state: str | None = Field(
        default=None, alias="primaryAccountDataQualityState"
    )
    execution_readiness: StrategyV1ReadinessResponse | None = Field(
        default=None, alias="executionReadiness"
    )
