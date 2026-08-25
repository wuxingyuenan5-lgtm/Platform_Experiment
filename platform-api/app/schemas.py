from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

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
    configured_credential_count: int = Field(
        default=0, alias="configuredCredentialCount"
    )
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
    capability: Literal["trade_and_read", "read_only"]
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


class AccountRiskSnapshotResponse(BaseModel):
    account_id: str = Field(alias="accountId")
    currency: str
    equity: Decimal | None = None
    margin: Decimal | None = None
    free_margin: Decimal | None = Field(default=None, alias="freeMargin")
    margin_level: Decimal | None = Field(default=None, alias="marginLevel")
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


class StrategyAccountSnapshotResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    account_id: str | None = Field(default=None, alias="accountId")
    account_code: str | None = Field(default=None, alias="accountCode")
    capability: Literal["trade_and_read", "read_only"] | None = None
    data_quality_state: str = Field(alias="dataQualityState")
    as_of: datetime | None = Field(default=None, alias="asOf")
    balance: BalanceSnapshotResponse | None = None
    account_risk: AccountRiskSnapshotResponse | None = Field(default=None, alias="accountRisk")
    positions: list[PositionResponse] = Field(default_factory=list)
    orders: list[OrderDetailResponse] = Field(default_factory=list)
    fills: list[FillResponse] = Field(default_factory=list)
    pnl: PnlResponse | None = None
    sync_status: str | None = Field(default=None, alias="syncStatus")
    sync_error_code: str | None = Field(default=None, alias="syncErrorCode")


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
