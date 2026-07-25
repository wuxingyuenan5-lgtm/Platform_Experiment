import axios, { type AxiosInstance } from 'axios';

import type {
  AccountResult,
  CreateExecutionBatchInput,
  CredentialReferenceResult,
  CrossSpreadHistoryPointResult,
  CrossSpreadMarketCommandInput,
  CrossSpreadSnapshotResult,
  ExchangeConnectivityResult,
  ExecutionBatchResult,
  InstrumentResult,
  OrderDetailResult,
  OrderResult,
  PnlResult,
  PositionResult,
  ReconciliationSummaryResult,
  RuntimeReadinessResult,
  StrategyAccountBindingResult,
  StrategyDefinitionResult,
  StrategyInstanceResult,
  StrategyNavSnapshotResult,
  StrategyPnlResult,
  StrategyRunResult,
  StrategyV1ReadinessResult,
  TradingSafetyResult,
  TradingSnapshot,
} from './trading.types';

const apiBaseUrl = import.meta.env.VITE_PLATFORM_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

const client: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

function isNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

export async function reconcileTradingOrder(orderId: string): Promise<OrderResult> {
  const response = await client.post<OrderResult>(
    `/trading/orders/${encodeURIComponent(orderId)}/reconcile`,
  );
  return response.data;
}

export async function createExecutionBatch(
  input: CreateExecutionBatchInput,
): Promise<ExecutionBatchResult> {
  const response = await client.post<ExecutionBatchResult>('/trading/execution-batches', input);
  return response.data;
}

export async function getExecutionBatch(batchId: string): Promise<ExecutionBatchResult> {
  const response = await client.get<ExecutionBatchResult>(
    `/trading/execution-batches/${encodeURIComponent(batchId)}`,
  );
  return response.data;
}

export async function getExecutionBatches(
  strategyInstanceId?: string,
): Promise<ExecutionBatchResult[]> {
  const response = await client.get<ExecutionBatchResult[]>('/trading/execution-batches', {
    params: strategyInstanceId ? { strategyInstanceId } : undefined,
  });
  return response.data;
}

export async function getTradingPosition(
  accountId: string,
  instrumentId: string,
): Promise<PositionResult | null> {
  try {
    const response = await client.get<PositionResult>(
      `/accounts/${encodeURIComponent(accountId)}/positions/${encodeURIComponent(instrumentId)}`,
    );
    return response.data;
  } catch (error) {
    if (isNotFound(error)) return null;
    throw error;
  }
}

export async function getTradingPnl(
  accountId: string,
  instrumentId: string,
): Promise<PnlResult | null> {
  try {
    const response = await client.get<PnlResult>(
      `/accounts/${encodeURIComponent(accountId)}/pnl/${encodeURIComponent(instrumentId)}`,
    );
    return response.data;
  } catch (error) {
    if (isNotFound(error)) return null;
    throw error;
  }
}

export async function getTradingSnapshot(
  accountId: string,
  instrumentId: string,
): Promise<TradingSnapshot> {
  const [position, pnl] = await Promise.all([
    getTradingPosition(accountId, instrumentId),
    getTradingPnl(accountId, instrumentId),
  ]);
  return { position, pnl };
}

export async function getRuntimeReadiness(): Promise<RuntimeReadinessResult> {
  const response = await client.get<RuntimeReadinessResult>('/system/runtime-readiness');
  return response.data;
}

export async function getReconciliationSummary(): Promise<ReconciliationSummaryResult> {
  const response = await client.get<ReconciliationSummaryResult>('/ops/reconciliation-summary');
  return response.data;
}

export async function getTradingSafety(): Promise<TradingSafetyResult> {
  const response = await client.get<TradingSafetyResult>('/security/trading-safety');
  return response.data;
}

export async function getCredentialReferences(): Promise<CredentialReferenceResult[]> {
  const response = await client.get<CredentialReferenceResult[]>('/security/credential-references');
  return response.data;
}

export async function getExchangeConnectivity(): Promise<ExchangeConnectivityResult> {
  const response = await client.get<ExchangeConnectivityResult>('/security/exchange-connectivity');
  return response.data;
}

export async function getCrossSpreadSnapshot(): Promise<CrossSpreadSnapshotResult> {
  const response = await client.get<CrossSpreadSnapshotResult>('/trading/cross-spread/snapshot');
  return response.data;
}

export async function getCrossSpreadHistory(limit = 200): Promise<CrossSpreadHistoryPointResult[]> {
  const response = await client.get<CrossSpreadHistoryPointResult[]>(
    '/trading/cross-spread/history',
    { params: { limit } },
  );
  return response.data;
}

export async function submitCrossSpreadMarketCommand(
  input: CrossSpreadMarketCommandInput,
): Promise<ExecutionBatchResult> {
  const response = await client.post<ExecutionBatchResult>(
    '/trading/cross-spread/market-command',
    input,
  );
  return response.data;
}

export async function getStrategyDefinitions(): Promise<StrategyDefinitionResult[]> {
  const response = await client.get<StrategyDefinitionResult[]>('/strategies/definitions');
  return response.data;
}

export async function getStrategyInstances(): Promise<StrategyInstanceResult[]> {
  const response = await client.get<StrategyInstanceResult[]>('/strategies/instances');
  return response.data;
}

export async function getStrategyAccountBindings(
  strategyInstanceId: string,
): Promise<StrategyAccountBindingResult[]> {
  const response = await client.get<StrategyAccountBindingResult[]>(
    `/strategies/instances/${encodeURIComponent(strategyInstanceId)}/accounts`,
  );
  return response.data;
}

export async function getStrategyRuns(strategyInstanceId: string): Promise<StrategyRunResult[]> {
  const response = await client.get<StrategyRunResult[]>(
    `/strategies/instances/${encodeURIComponent(strategyInstanceId)}/runs`,
  );
  return response.data;
}

export async function getStrategyV1Readiness(
  strategyInstanceId: string,
): Promise<StrategyV1ReadinessResult> {
  const response = await client.get<StrategyV1ReadinessResult>(
    `/strategies/instances/${encodeURIComponent(strategyInstanceId)}/v1-readiness`,
  );
  return response.data;
}

export async function getAccounts(): Promise<AccountResult[]> {
  const response = await client.get<AccountResult[]>('/accounts');
  return response.data;
}

export async function getInstruments(): Promise<InstrumentResult[]> {
  const response = await client.get<InstrumentResult[]>('/instruments');
  return response.data;
}

export async function getOrders(): Promise<OrderDetailResult[]> {
  const response = await client.get<OrderDetailResult[]>('/trading/orders');
  return response.data;
}

export async function getStrategyPnl(strategyInstanceId: string): Promise<StrategyPnlResult> {
  const response = await client.get<StrategyPnlResult>(
    `/strategies/instances/${encodeURIComponent(strategyInstanceId)}/pnl`,
  );
  return response.data;
}

export async function getStrategyNavSnapshots(
  strategyInstanceId: string,
): Promise<StrategyNavSnapshotResult[]> {
  const response = await client.get<StrategyNavSnapshotResult[]>(
    `/strategies/instances/${encodeURIComponent(strategyInstanceId)}/nav-snapshots`,
  );
  return response.data;
}
