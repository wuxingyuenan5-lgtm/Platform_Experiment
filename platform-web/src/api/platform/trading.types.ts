import type { components } from './generated/strategy';

export type TradingSide = 'buy' | 'sell';
export type TradingOrderType = 'market' | 'limit';
export type TradingOrderStatus =
  | 'processing'
  | 'acknowledged'
  | 'filled'
  | 'rejected'
  | 'result_unknown';

export type ExecutionBatchStatus =
  | 'pending'
  | 'executing'
  | 'partially_executed'
  | 'hedged'
  | 'completed'
  | 'failed'
  | 'manual_intervention';

export type OrderResult = components['schemas']['OrderResponse'];
export type CrossSpreadPositionOverviewResult =
  components['schemas']['CrossSpreadPositionOverviewResponse'];
export type CrossSpreadPositionPnlResult = components['schemas']['CrossSpreadPositionPnlResponse'];

export interface CreateExecutionBatchLegInput {
  role: string;
  accountId?: string;
  instrumentId: string;
  symbol: string;
  side: TradingSide;
  orderType: TradingOrderType;
  quantity: string;
  price?: string;
}

export interface CreateExecutionBatchInput {
  idempotencyKey: string;
  strategyInstanceId: string;
  accountId?: string;
  strategyKey: string;
  direction: string;
  legs: [CreateExecutionBatchLegInput, CreateExecutionBatchLegInput];
}

export interface ExecutionBatchLegResult {
  role: string;
  accountId?: string | null;
  orderId?: string | null;
  status: string;
  failureReason?: string | null;
}

export type ExecutionBatchResult = components['schemas']['ExecutionBatchResponse'];

export type StrategyRunStatus =
  | 'pending'
  | 'executing'
  | 'completed'
  | 'failed'
  | 'manual_intervention';

export type StrategyRunResult = components['schemas']['StrategyRunResponse'];

export type StrategyV1ReadinessResult = components['schemas']['StrategyV1ReadinessResponse'];

export type ReconciliationIssueResult = components['schemas']['ReconciliationIssueResponse'];

export type ReconciliationSummaryResult = components['schemas']['ReconciliationSummaryResponse'];

export type TradingSafetyResult = components['schemas']['TradingSafetyResponse'];

export type CredentialReferenceResult = components['schemas']['CredentialReferenceResponse'];

export type ExchangeCredentialInspectionResult =
  components['schemas']['ExchangeCredentialInspectionResponse'];

export type ExchangeConnectivityResult = components['schemas']['ExchangeConnectivityResponse'];

export type MarketQuoteResult = components['schemas']['MarketQuoteResponse'];

export type VenuePositionResult = components['schemas']['VenuePositionResponse'];

export type CrossSpreadVenueSnapshotResult =
  components['schemas']['CrossSpreadVenueSnapshotResponse'];

export type CrossSpreadSnapshotResult = components['schemas']['CrossSpreadSnapshotResponse'];

export type CrossSpreadMetricsResult = components['schemas']['CrossSpreadMetricsResponse'];

export type CrossSpreadHistoryPointResult =
  components['schemas']['CrossSpreadHistoryPointResponse'];

export type CrossSpreadMarketAction = 'OPEN_LONG' | 'CLOSE_LONG' | 'OPEN_SHORT' | 'CLOSE_SHORT';

export interface CrossSpreadMarketCommandInput {
  action: CrossSpreadMarketAction;
  quantityOz: string;
  idempotencyKey: string;
}

export interface AuditEventResult {
  auditEventId: string;
  eventType: string;
  subjectType: string;
  subjectId: string;
  detailsJson: string;
  createdAt: string;
}

export type PositionResult = components['schemas']['PositionResponse'];

export type BalanceResult = components['schemas']['BalanceSnapshotResponse'];

export interface AssetBreakdownResult {
  totalEquity?: string;
  valuationCurrency?: string;
  categories?: Array<{ category: string; equity: string }>;
  accountType?: string;
  category?: string;
  equity?: string;
  usdValue?: string;
  currency?: string;
  [key: string]: unknown;
}

export interface AccountRiskResult {
  assetScope?: string;
  totalAssets?: string | null;
  assetBreakdown?: AssetBreakdownResult[];
  assetOverviewAsOf?: string | null;
  assetOverviewQuality?: string;
  walletBalance?: string | null;
  marginBalance?: string | null;
  maintenanceMargin?: string | null;
  unrealizedPnl?: string | null;
  accountId: string;
  currency: string;
  equity?: string | null;
  margin?: string | null;
  freeMargin?: string | null;
  marginLevel?: string | null;
  dataQualityState: string;
  asOf: string;
}

export type StrategyEquityHistoryPointResult =
  components['schemas']['StrategyEquityHistoryPointResponse'];

export interface EquityHistoryPointResult {
  asOf: string;
  equity: string;
}

export type PnlResult = components['schemas']['PnlResponse'];

export interface TradingSnapshot {
  position: PositionResult | null;
  pnl: PnlResult | null;
}

export type RuntimeReadinessResult = components['schemas']['RuntimeReadinessResponse'];

export type StrategyDefinitionResult = components['schemas']['StrategyDefinitionResponse'];

export type StrategyInstanceResult = components['schemas']['StrategyInstanceResponse'];

export type StrategyManagementOverviewResult =
  components['schemas']['StrategyManagementOverviewResponse'];

export type LiveTradingSessionResult = components['schemas']['LiveTradingSessionResponse'];

export type AccountResult = components['schemas']['AccountResponse'];

export type StrategyAccountBindingResult = components['schemas']['StrategyAccountBindingResponse'];

export type StrategyAccountSnapshotResult =
  components['schemas']['StrategyAccountSnapshotResponse'];

export type InstrumentResult = components['schemas']['InstrumentResponse'];

export type ContractSpecificationResult = components['schemas']['ContractSpecificationResponse'];

// The detail endpoint is a read model and deliberately preserves every venue
// terminal state (for example `canceled` and `result_unknown`).  A submit
// response remains constrained by TradingOrderStatus above.
export type OrderDetailResult = components['schemas']['OrderDetailResponse'];

export type FillResult = components['schemas']['FillResponse'];

export interface FinancialAmountsResult {
  realizedPnl: string | null;
  tradingPnl: string | null;
  fees: string | null;
  fundingPnl?: string | null;
  swapPnl?: string | null;
  netPnl?: string | null;
  currency: string;
  accountId?: string;
}

export type StrategyPnlResult = components['schemas']['StrategyPnlResponse'];

export type StrategyNavSnapshotResult = components['schemas']['StrategyNavSnapshotResponse'];
