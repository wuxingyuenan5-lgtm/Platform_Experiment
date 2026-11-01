import { createStrategyClient } from './strategyClient';
import type { ExecutionTimeline } from './executionSteps';

/**
 * Durable open/close records. The list is a projection; the detail re-reads the
 * underlying batch, legs, orders, fills and steps every time it is opened.
 */
const client = createStrategyClient(20_000);

export type ExecutionAction = 'open' | 'close' | 'risk_disposition' | string;

export interface ExecutionLegDetail {
  role: string | null;
  accountId: string | null;
  symbol: string | null;
  side: string | null;
  requestedQuantity: string | null;
  filledQuantity: string;
  averagePrice: string | null;
  notional: string | null;
  status: string | null;
  orderId: string | null;
  externalOrderId: string | null;
  fees: string | null;
  feeCurrency: string | null;
  feeBreakdown?: Array<{ currency: string; amount: string }>;
  fillCount: number;
  failureReason: string | null;
}

export interface ExecutionRecord {
  id: string;
  strategyKey: string;
  strategyInstanceId: string | null;
  batchId: string;
  instructionId: string | null;
  action: ExecutionAction;
  direction: string | null;
  status: string;
  failureReason: string | null;
  traceId: string | null;
  primarySymbol: string | null;
  primaryQuantity: string | null;
  primaryAveragePrice: string | null;
  totalFees: string | null;
  feeCurrency: string | null;
  notional: string | null;
  legCount: number;
  filledLegCount: number;
  legDetails: ExecutionLegDetail[];
  risk: Record<string, unknown> | null;
  relatedRecordId: string | null;
  startedAt: string;
  finishedAt: string | null;
  durationMs: number | null;
  projectedAt?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ExecutionRecordPage {
  total: number;
  limit: number;
  offset: number;
  items: ExecutionRecord[];
}

export interface ExecutionAccountSnapshot {
  id: string;
  traceId: string | null;
  batchId: string | null;
  instructionId: string | null;
  accountId: string;
  phase: string;
  currency: string | null;
  balance: string | null;
  available: string | null;
  equity: string | null;
  positionCount: number | null;
  positions: Array<Record<string, unknown>>;
  payload: Record<string, unknown>;
  qualityState: string | null;
  capturedAt: string;
  /** Set when the snapshot was rebuilt from the balance series instead of the
   *  batch-time hook (`balance_snapshots`). */
  derivedFrom?: string;
}

export interface ExecutionRecordDetail {
  record: ExecutionRecord;
  batch: Record<string, any> | null;
  instruction: Record<string, any> | null;
  legs: Array<Record<string, any>>;
  orders: Array<Record<string, any>>;
  fills: Array<Record<string, any>>;
  accountSnapshots: ExecutionAccountSnapshot[];
  timeline: ExecutionTimeline;
  relatedRecord: ExecutionRecord | null;
}

export interface ExecutionRecordQuery {
  strategyKey?: string;
  action?: string;
  status?: string;
  symbol?: string;
  startedFrom?: string;
  startedTo?: string;
  limit?: number;
  offset?: number;
}

export async function listExecutionRecords(
  query: ExecutionRecordQuery = {},
  signal?: AbortSignal,
): Promise<ExecutionRecordPage> {
  const params: Record<string, string | number> = {};
  if (query.strategyKey) params.strategyKey = query.strategyKey;
  if (query.action) params.action = query.action;
  if (query.status) params.status = query.status;
  if (query.symbol) params.symbol = query.symbol;
  if (query.startedFrom) params.startedFrom = query.startedFrom;
  if (query.startedTo) params.startedTo = query.startedTo;
  if (query.limit != null) params.limit = query.limit;
  if (query.offset != null) params.offset = query.offset;
  const response = await client.get<ExecutionRecordPage>('/trading/execution-records', {
    params,
    signal,
  });
  return response.data;
}

export async function getExecutionRecord(
  recordId: string,
  signal?: AbortSignal,
): Promise<ExecutionRecordDetail> {
  const response = await client.get<ExecutionRecordDetail>(
    `/trading/execution-records/${encodeURIComponent(recordId)}`,
    { signal },
  );
  return response.data;
}
