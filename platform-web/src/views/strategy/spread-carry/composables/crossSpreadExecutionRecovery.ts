import type {
  CrossSpreadDirection,
  CrossSpreadExecutionMode,
  CrossSpreadLimitStrategy,
} from '@/api/platform/crossSpreadLifecycle';

interface StorageLike {
  getItem(key: string): string | null;
  removeItem(key: string): void;
  setItem(key: string, value: string): void;
}

export interface CloseExecutionDraftPayload {
  executionMode: CrossSpreadExecutionMode;
  limitSpread?: string;
  limitStrategy: CrossSpreadLimitStrategy;
}

export type PersistedExecutionDraft =
  | {
      kind: 'OPEN';
      idempotencyKey: string;
      payload: {
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
      };
    }
  | {
      kind: 'CLOSE';
      idempotencyKey: string;
      planId: string;
      payload: CloseExecutionDraftPayload;
    }
  | {
      kind: 'CLOSE_ALL';
      payload: CloseExecutionDraftPayload;
      plans: Array<{
        planId: string;
        idempotencyKey: string;
      }>;
    };

export const PENDING_EXECUTION_STORAGE_KEY = 'vg.crossSpread.pendingExecution';

export function persistExecutionDraft(
  draft: PersistedExecutionDraft,
  storage: StorageLike = localStorage,
) {
  storage.setItem(PENDING_EXECUTION_STORAGE_KEY, JSON.stringify(draft));
}

export function readExecutionDraft(
  storage: StorageLike = localStorage,
): PersistedExecutionDraft | null {
  const raw = storage.getItem(PENDING_EXECUTION_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PersistedExecutionDraft;
  } catch {
    storage.removeItem(PENDING_EXECUTION_STORAGE_KEY);
    return null;
  }
}

export function clearExecutionDraft(storage: StorageLike = localStorage) {
  storage.removeItem(PENDING_EXECUTION_STORAGE_KEY);
}

export function isTerminalBatchStatus(status: string | null | undefined) {
  return status === 'hedged' || status === 'completed' || status === 'failed';
}

export function createCloseAllExecutionDraft(
  planIds: string[],
  payload: CloseExecutionDraftPayload,
  createId: () => string = () => crypto.randomUUID(),
): PersistedExecutionDraft & { kind: 'CLOSE_ALL' } {
  return {
    kind: 'CLOSE_ALL',
    payload,
    plans: planIds.map((planId) => ({
      planId,
      idempotencyKey: createId(),
    })),
  };
}
