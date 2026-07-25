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
  | 'failed'
  | 'manual_intervention';

export interface OrderResult {
  orderId: string;
  commandId: string;
  status: TradingOrderStatus;
  externalOrderId?: string | null;
}

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

export interface ExecutionBatchResult {
  batchId: string;
  idempotencyKey?: string | null;
  strategyInstanceId?: string | null;
  accountId?: string | null;
  strategyKey: string;
  direction: string;
  status: ExecutionBatchStatus;
  requiresManualIntervention: boolean;
  failureReason?: string | null;
  legs: ExecutionBatchLegResult[];
  createdAt: string;
  updatedAt: string;
}

export type StrategyRunStatus =
  | 'pending'
  | 'executing'
  | 'completed'
  | 'failed'
  | 'manual_intervention';

export interface StrategyRunResult {
  strategyRunId: string;
  idempotencyKey: string;
  strategyInstanceId: string;
  strategyKey: string;
  direction: string;
  status: StrategyRunStatus;
  executionBatchId?: string | null;
  executionBatch?: ExecutionBatchResult | null;
  reason?: string | null;
  failureReason?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StrategyV1ReadinessResult {
  strategyInstanceId: string;
  strategyKey: string;
  runnable: boolean;
  blockers: string[];
  warnings: string[];
  latestRunStatus?: string | null;
  manualInterventionCount: number;
  resultUnknownOrderCount: number;
}

export interface ReconciliationIssueResult {
  issueType: string;
  subjectType: string;
  subjectId: string;
  strategyInstanceId?: string | null;
  severity: 'warning' | 'action_required';
  message: string;
  detectedAt: string;
}

export interface ReconciliationSummaryResult {
  status: 'ok' | 'action_required';
  manualInterventionBatchCount: number;
  resultUnknownOrderCount: number;
  issues: ReconciliationIssueResult[];
}

export interface TradingSafetyResult {
  liveTradingEnabled: boolean;
  defaultTradingEnvironment: string;
  secretStoragePolicy: string;
  liveGuardPolicy: string;
}

export interface CredentialReferenceResult {
  credentialId: string;
  credentialRef: string;
  venueId: string;
  venueCode: string;
  environment: string;
  purpose: string;
  status: string;
  createdAt: string;
}

export interface ExchangeCredentialInspectionResult {
  credentialRef: string;
  envPrefix: string;
  configured: boolean;
  availableFields: string[];
  missingFields: string[];
}

export interface ExchangeConnectivityResult {
  status: string;
  gateway?: string | null;
  credentialCount: number;
  configuredCredentialCount: number;
  credentials: ExchangeCredentialInspectionResult[];
}

export interface MarketQuoteResult {
  bid: string;
  ask: string;
  mid: string;
  last?: string | null;
  currency: string;
}

export interface VenuePositionResult {
  symbol: string;
  side: string;
  quantity: string;
  averagePrice?: string | null;
  unrealizedPnl?: string | null;
  externalId?: string | null;
}

export interface CrossSpreadVenueSnapshotResult {
  venue: string;
  symbol: string;
  status: string;
  quote?: MarketQuoteResult | null;
  positions: VenuePositionResult[];
  reason?: string | null;
}

export interface CrossSpreadSnapshotResult {
  status: string;
  bybit: CrossSpreadVenueSnapshotResult;
  mt5: CrossSpreadVenueSnapshotResult;
  longSpread?: string | null;
  shortSpread?: string | null;
  metrics: CrossSpreadMetricsResult;
  asOf: string;
}

export interface CrossSpreadMetricsResult {
  fundingRate?: string | null;
  usdtUsd?: string | null;
  buyerInventoryFee?: string | null;
  sellerInventoryFee?: string | null;
}

export interface CrossSpreadHistoryPointResult {
  asOf: string;
  longSpread?: string | null;
  shortSpread?: string | null;
  bybitMid?: string | null;
  mt5Mid?: string | null;
}

export type CrossSpreadMarketAction = 'OPEN_LONG' | 'CLOSE_LONG' | 'OPEN_SHORT' | 'CLOSE_SHORT';

export interface CrossSpreadMarketCommandInput {
  action: CrossSpreadMarketAction;
  quantityOz: string;
}

export interface AuditEventResult {
  auditEventId: string;
  eventType: string;
  subjectType: string;
  subjectId: string;
  detailsJson: string;
  createdAt: string;
}

export interface PositionResult {
  accountId: string;
  instrumentId: string;
  netQuantity: string;
  averagePrice?: string | null;
}

export interface PnlResult {
  accountId: string;
  instrumentId: string;
  realizedPnl: string;
  tradingPnl: string;
  fees: string;
}

export interface TradingSnapshot {
  position: PositionResult | null;
  pnl: PnlResult | null;
}

export interface RuntimeReadinessResult {
  backendStatus: string;
  databaseStatus: string;
  runtimeStatus: string;
  defaultTradingMode: string;
}

export interface StrategyDefinitionResult {
  strategyId: string;
  strategyKey: string;
  name: string;
  v1Scope: 'closed_loop' | 'reserved' | 'placeholder' | string;
  status: string;
  description: string;
}

export interface StrategyInstanceResult {
  strategyInstanceId: string;
  strategyId: string;
  strategyKey: string;
  strategyName: string;
  version: string;
  name: string;
  tradingMode: string;
  status: string;
  capitalBase?: string | null;
  baseCurrency: string;
  dataQualityState: string;
}

export interface AccountResult {
  accountId: string;
  accountCode: string;
  name: string;
  venueId: string;
  venueCode: string;
  accountType: string;
  environment: string;
  baseCurrency: string;
  credentialRef?: string | null;
  status: string;
  dataQualityState: string;
}

export interface StrategyAccountBindingResult {
  bindingId: string;
  strategyInstanceId: string;
  accountId: string;
  accountCode: string;
  role: string;
  maxNotional?: string | null;
  status: string;
}

export interface InstrumentResult {
  instrumentId: string;
  instrumentCode: string;
  name: string;
  instrumentType: string;
  baseCurrency: string;
  quoteCurrency: string;
  settleCurrency: string;
  quantityUnit: string;
  dataQualityState: string;
  contract?: ContractSpecificationResult | null;
}

export interface ContractSpecificationResult {
  version: string;
  priceTick: string;
  minOrderQuantity: string;
  quantityStep: string;
  contractMultiplier: string;
  dataQualityState: string;
}

export interface OrderDetailResult extends OrderResult {
  accountId: string;
  instrumentId: string;
  symbol: string;
  side: TradingSide;
  orderType: TradingOrderType;
  quantity: string;
  price?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StrategyPnlResult {
  strategyInstanceId: string;
  realizedPnl: string;
  tradingPnl: string;
  fees: string;
  currency: string;
  dataQualityState: string;
}

export interface StrategyNavSnapshotResult {
  snapshotId: string;
  strategyInstanceId: string;
  valuationTime: string;
  equity: string;
  capitalBase: string;
  nav: string;
  currency: string;
  dataQualityState: string;
}
