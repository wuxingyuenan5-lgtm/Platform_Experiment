import axios, { type AxiosInstance } from 'axios';

import type { ExecutionBatchResult } from './trading.types';

export type CrossSpreadDirection = 'LONG_SPREAD' | 'SHORT_SPREAD';
export type CrossSpreadExecutionMode = 'market' | 'limit';
export type CrossSpreadLimitStrategy = 'fok' | 'post_only_chase';
export type CrossSpreadSyntheticAction =
  | 'OPEN_LONG_SPREAD'
  | 'CLOSE_LONG_SPREAD'
  | 'OPEN_SHORT_SPREAD'
  | 'CLOSE_SHORT_SPREAD';
export type CrossSpreadSyntheticExecutionType = 'MARKET' | 'LIMIT';
export type CrossSpreadTriggerReason =
  | 'MANUAL'
  | 'STRATEGY'
  | 'TAKE_PROFIT'
  | 'STOP_LOSS'
  | 'KILL_SWITCH'
  | 'RISK_REDUCTION';
export type CrossSpreadExitPlanStatus =
  | 'active'
  | 'triggered'
  | 'closing'
  | 'closed'
  | 'manual_intervention';

export interface CrossSpreadOrderIntentResult {
  action: CrossSpreadSyntheticAction;
  executionType: CrossSpreadSyntheticExecutionType;
  triggerReason: CrossSpreadTriggerReason;
  direction: CrossSpreadDirection;
  isOpen: boolean;
}

export interface CrossSpreadLimitExecutionResult {
  direction: 'BUY_BYBIT_SELL_MT5' | 'SELL_BYBIT_BUY_MT5';
  limitStrategy: CrossSpreadLimitStrategy;
  limitSpread: string;
  executableSpread: string;
  mt5ReferencePrice: string;
  hedgeReserve: string;
  bybitTickSize: string;
  rawBybitLimitPrice: string;
  bybitLimitPrice: string;
  currentlyExecutable: boolean;
  timeInForce: 'FOK' | 'PostOnly';
}

export interface CrossSpreadExitPlanResult {
  planId: string;
  strategyInstanceId: string;
  openBatchId: string;
  closeBatchId?: string | null;
  direction: CrossSpreadDirection;
  quantityOz: string;
  mt5PositionId: string;
  entrySpread: string;
  takeProfitSpread: string | null;
  stopLossSpread: string | null;
  takeProfitExecutionMode: CrossSpreadExecutionMode;
  stopLossExecutionMode: CrossSpreadExecutionMode;
  takeProfitLimitStrategy: CrossSpreadLimitStrategy;
  stopLossLimitStrategy: CrossSpreadLimitStrategy;
  status: CrossSpreadExitPlanStatus;
  triggerReason?: string | null;
  triggerSpread?: string | null;
  createdAt: string;
  updatedAt: string;
  triggeredAt?: string | null;
  closedAt?: string | null;
}

export interface CrossSpreadMarketOpenInput {
  direction: CrossSpreadDirection;
  quantityOz: string;
  takeProfitSpread?: string;
  stopLossSpread?: string;
  executionMode: CrossSpreadExecutionMode;
  limitSpread?: string;
  limitStrategy: CrossSpreadLimitStrategy;
  takeProfitExecutionMode: CrossSpreadExecutionMode;
  stopLossExecutionMode: CrossSpreadExecutionMode;
  takeProfitLimitStrategy: CrossSpreadLimitStrategy;
  stopLossLimitStrategy: CrossSpreadLimitStrategy;
}

export interface CrossSpreadMarketOpenResult {
  executionBatch: ExecutionBatchResult;
  orderIntent: CrossSpreadOrderIntentResult;
  limitExecution?: CrossSpreadLimitExecutionResult | null;
  exitPlan?: CrossSpreadExitPlanResult | null;
}

export interface CrossSpreadMarketCloseResult {
  executionBatch: ExecutionBatchResult;
  orderIntent: CrossSpreadOrderIntentResult;
  limitExecution?: CrossSpreadLimitExecutionResult | null;
  exitPlan: CrossSpreadExitPlanResult;
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

export async function openCrossSpreadMarket(
  input: CrossSpreadMarketOpenInput,
): Promise<CrossSpreadMarketOpenResult> {
  const response = await client.post<CrossSpreadMarketOpenResult>(
    '/trading/cross-spread/lifecycle/open',
    input,
  );
  return response.data;
}

export async function getCrossSpreadExitPlans(
  status?: CrossSpreadExitPlanStatus,
): Promise<CrossSpreadExitPlanResult[]> {
  const response = await client.get<CrossSpreadExitPlanResult[]>(
    '/trading/cross-spread/exit-plans',
    { params: status ? { status } : undefined },
  );
  return response.data;
}

export async function closeCrossSpreadMarket(
  planId: string,
  executionMode: CrossSpreadExecutionMode,
  limitSpread?: string,
  limitStrategy: CrossSpreadLimitStrategy = 'fok',
): Promise<CrossSpreadMarketCloseResult> {
  const response = await client.post<CrossSpreadMarketCloseResult>(
    `/trading/cross-spread/exit-plans/${encodeURIComponent(planId)}/close`,
    {
      executionMode,
      limitStrategy,
      ...(limitSpread === undefined ? {} : { limitSpread }),
    },
  );
  return response.data;
}
