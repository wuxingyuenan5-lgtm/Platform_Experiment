import { createStrategyClient } from './strategyClient';

/** The timeline endpoint is read-only diagnostics; it reuses the session client. */
const client = createStrategyClient(15_000);

export type ExecutionStepStatus = 'passed' | 'blocked' | 'failed' | 'info';
export type ExecutionOutcome = 'passed' | 'blocked' | 'failed' | 'in_progress' | 'not_found';

export interface ExecutionStep {
  id: string;
  traceId: string;
  batchId: string | null;
  orderId: string | null;
  commandId: string | null;
  sequence: number;
  stage: string;
  stageLabel: string;
  status: ExecutionStepStatus;
  reasonCode: string | null;
  reasonLabel: string | null;
  reasonDetail: string | null;
  statusCode: number | null;
  durationMs: number | null;
  payload: Record<string, unknown> | null;
  occurredAt: string;
}

export interface ExecutionStepSummary {
  outcome: ExecutionOutcome;
  stepCount: number;
  startedAt: string | null;
  finishedAt: string | null;
  blockedStage: string | null;
  blockedStageLabel: string | null;
  blockedReasonCode: string | null;
  blockedReasonLabel: string | null;
  blockedReasonDetail: string | null;
  totalDurationMs: number;
}

export interface ExecutionTimeline {
  traceId: string | null;
  matchedBy: string;
  summary: ExecutionStepSummary;
  steps: ExecutionStep[];
}

export interface ExecutionTimelineSelector {
  traceId?: string | null;
  batchId?: string | null;
  orderId?: string | null;
  limit?: number;
}

export function newExecutionTraceId(): string {
  return `trc_${crypto.randomUUID().replace(/-/g, '')}`;
}

export async function getExecutionTimeline(
  selector: ExecutionTimelineSelector,
  signal?: AbortSignal,
): Promise<ExecutionTimeline> {
  const params: Record<string, string | number> = {};
  if (selector.traceId) params.traceId = selector.traceId;
  if (selector.batchId) params.batchId = selector.batchId;
  if (selector.orderId) params.orderId = selector.orderId;
  if (selector.limit) params.limit = selector.limit;
  if (!params.traceId && !params.batchId && !params.orderId) {
    throw new Error('执行时间线需要 traceId、batchId 或 orderId');
  }
  const response = await client.get<ExecutionTimeline>('/trading/execution-steps', {
    params,
    signal,
  });
  return response.data;
}
