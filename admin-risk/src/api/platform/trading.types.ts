export type TradingSide = 'buy' | 'sell';
export type TradingOrderType = 'market' | 'limit';

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
  platformOrderId: string;
  commandId: string;
  status: 'processing' | 'acknowledged' | 'filled' | 'rejected' | 'result_unknown';
  externalOrderId?: string | null;
  filledQuantity: string;
  averageFillPrice?: string | null;
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
