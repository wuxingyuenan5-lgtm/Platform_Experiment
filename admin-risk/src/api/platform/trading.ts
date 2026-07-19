import axios, { type AxiosInstance } from 'axios';

import type {
  CreateExecutionBatchInput,
  CreateOrderInput,
  ExecutionBatchResult,
  OrderResult,
  PnlResult,
  PositionResult,
  TradingSnapshot,
} from './trading.types';

const apiBaseUrl =
  import.meta.env.VITE_PLATFORM_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

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

export async function createTradingOrder(input: CreateOrderInput): Promise<OrderResult> {
  const response = await client.post<OrderResult>('/trading/orders', input);
  return response.data;
}

export async function createExecutionBatch(
  input: CreateExecutionBatchInput,
): Promise<ExecutionBatchResult> {
  const response = await client.post<ExecutionBatchResult>(
    '/trading/execution-batches',
    input,
  );
  return response.data;
}

export async function getExecutionBatch(batchId: string): Promise<ExecutionBatchResult> {
  const response = await client.get<ExecutionBatchResult>(
    `/trading/execution-batches/${encodeURIComponent(batchId)}`,
  );
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
