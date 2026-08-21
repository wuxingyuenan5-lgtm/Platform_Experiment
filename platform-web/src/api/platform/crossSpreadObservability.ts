import axios, { type AxiosInstance } from 'axios';

export type NumericValue = string | number;
export type ObservabilityState = 'complete' | 'partial' | 'unavailable';
export type ObservabilitySectionState = 'complete' | 'unavailable';
export type CrossSpreadObservabilityMode = 'fast' | 'audit';

export interface VenueAccountRiskSnapshot {
  source: string;
  accountId: string;
  currency: string;
  equity?: NumericValue | null;
  walletBalance?: NumericValue | null;
  marginBalance?: NumericValue | null;
  availableBalance?: NumericValue | null;
  initialMargin?: NumericValue | null;
  maintenanceMargin?: NumericValue | null;
  unrealizedPnl?: NumericValue | null;
  accountImRate?: NumericValue | null;
  accountMmRate?: NumericValue | null;
  marginLevel?: NumericValue | null;
  marginCallLevel?: NumericValue | null;
  stopOutLevel?: NumericValue | null;
  marginThresholdMode?: string | null;
  leverage?: NumericValue | null;
  marginMode?: string | null;
  tradeAllowed?: boolean | null;
  expertTradingAllowed?: boolean | null;
  fieldAvailability?: Record<string, string>;
  asOf: string;
  dataQualityState: string;
}

export interface VenuePositionSnapshot {
  source: string;
  externalPositionId: string;
  accountId: string;
  instrumentId: string;
  symbol: string;
  netQuantity: NumericValue;
  averagePrice?: NumericValue | null;
  currentPrice?: NumericValue | null;
  markPrice?: NumericValue | null;
  breakEvenPrice?: NumericValue | null;
  liquidationPrice?: NumericValue | null;
  liquidationPriceSource: string;
  positionValue?: NumericValue | null;
  leverage?: NumericValue | null;
  initialMargin?: NumericValue | null;
  maintenanceMargin?: NumericValue | null;
  unrealizedPnl?: NumericValue | null;
  realizedPnl?: NumericValue | null;
  stopLossPrice?: NumericValue | null;
  takeProfitPrice?: NumericValue | null;
  swap?: NumericValue | null;
  positionStatus?: string | null;
  currency: string;
  fieldAvailability?: Record<string, string>;
  dataQualityState: string;
  asOf: string;
  openTime?: string | null;
}

export interface VenueOrderSnapshot {
  source: string;
  externalOrderId: string;
  platformOrderId: string;
  accountId: string;
  symbol: string;
  side: 'buy' | 'sell';
  orderType: 'market' | 'limit';
  quantity: NumericValue;
  filledQuantity: NumericValue;
  remainingQuantity: NumericValue;
  price?: NumericValue | null;
  averageFillPrice?: NumericValue | null;
  status: string;
  reduceOnly?: boolean | null;
  positionIndex?: number | null;
  positionId?: string | null;
  timeInForce?: string | null;
  rejectReason?: string | null;
  cancelReason?: string | null;
  dataQualityState: string;
  asOf: string;
}

export interface VenueFillSnapshot {
  source: string;
  externalFillId: string;
  externalOrderId: string;
  accountId: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: NumericValue;
  price: NumericValue;
  fee: NumericValue;
  currency: string;
  occurredAt: string;
  dataQualityState: string;
}

export interface CrossSpreadVenueObservability {
  venue: string;
  accountId: string;
  symbol: string;
  status: ObservabilityState;
  sectionStates: Record<string, ObservabilitySectionState>;
  accountRisk?: VenueAccountRiskSnapshot | null;
  positions: VenuePositionSnapshot[];
  activeOrders: VenueOrderSnapshot[];
  recentOrders: VenueOrderSnapshot[];
  recentFills: VenueFillSnapshot[];
  warnings: string[];
}

export interface CrossSpreadObservabilityResult {
  status: ObservabilityState;
  historyHours: number;
  bybit: CrossSpreadVenueObservability;
  mt5: CrossSpreadVenueObservability;
  warnings: string[];
  asOf: string;
}

const apiBaseUrl = import.meta.env.VITE_PLATFORM_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

const platformApiToken = import.meta.env.VITE_PLATFORM_API_TOKEN || '';

const client: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
    ...(platformApiToken ? { Authorization: `Bearer ${platformApiToken}` } : {}),
  },
});

export async function getCrossSpreadObservability(
  historyHours = 24,
  limit = 20,
  mode: CrossSpreadObservabilityMode = 'audit',
): Promise<CrossSpreadObservabilityResult> {
  const response = await client.get<CrossSpreadObservabilityResult>(
    '/trading/cross-spread/observability',
    { params: { historyHours, limit, mode } },
  );
  return response.data;
}
