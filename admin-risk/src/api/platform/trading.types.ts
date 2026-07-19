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

export interface CreateOrderInput {
  accountId: string;
  instrumentId: string;
  symbol: string;
  side: TradingSide;
  orderType: TradingOrderType;
  quantity: string;
  price?: string;
}

export interface OrderResult {
  orderId: string;
  commandId: string;
  status: TradingOrderStatus;
  externalOrderId?: string | null;
}

export interface CreateExecutionBatchLegInput {
  role: string;
  instrumentId: string;
  symbol: string;
  side: TradingSide;
  orderType: TradingOrderType;
  quantity: string;
  price?: string;
}

export interface CreateExecutionBatchInput {
  accountId: string;
  strategyKey: string;
  direction: string;
  legs: [CreateExecutionBatchLegInput, CreateExecutionBatchLegInput];
}

export interface ExecutionBatchLegResult {
  role: string;
  orderId?: string | null;
  status: string;
  failureReason?: string | null;
}

export interface ExecutionBatchResult {
  batchId: string;
  accountId: string;
  strategyKey: string;
  direction: string;
  status: ExecutionBatchStatus;
  requiresManualIntervention: boolean;
  failureReason?: string | null;
  legs: ExecutionBatchLegResult[];
  createdAt: string;
  updatedAt: string;
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
