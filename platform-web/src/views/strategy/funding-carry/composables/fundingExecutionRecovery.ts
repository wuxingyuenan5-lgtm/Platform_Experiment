export const FUNDING_PENDING_DRAFT_STORAGE_KEY = 'vg.platform.funding.pendingDraft';

export type FundingExecutionPolicy = 'market' | 'fok' | 'post_only_chase';

export type FundingDraftState =
  | 'accepted'
  | 'submitting'
  | 'executing'
  | 'partially_hedged'
  | 'reconciling'
  | 'result_unknown'
  | 'manual_intervention';

export interface FundingPendingDraft {
  ownerUserId?: string;
  idempotencyKey: string;
  instructionId?: string;
  action: 'open' | 'close';
  perpetualSymbol: string;
  spotSymbol: string;
  quantity: string;
  expectedPerpetualQuantity?: string;
  executionPolicy?: FundingExecutionPolicy;
  perpetualLimitPrice?: string;
  targetOpenInstructionId?: string;
  state: FundingDraftState;
}

export function readFundingDraft(
  storage: Pick<Storage, 'getItem'> = localStorage,
  ownerUserId?: string,
): FundingPendingDraft | null {
  const raw = storage.getItem(FUNDING_PENDING_DRAFT_STORAGE_KEY);
  if (!raw) return null;
  try {
    const draft = JSON.parse(raw) as FundingPendingDraft;
    return ownerUserId && draft.ownerUserId && draft.ownerUserId !== ownerUserId ? null : draft;
  } catch {
    return null;
  }
}

export function writeFundingDraft(
  draft: FundingPendingDraft,
  storage: Pick<Storage, 'setItem'> = localStorage,
): void {
  storage.setItem(FUNDING_PENDING_DRAFT_STORAGE_KEY, JSON.stringify(draft));
}

export function clearFundingDraft(storage: Pick<Storage, 'removeItem'> = localStorage): void {
  storage.removeItem(FUNDING_PENDING_DRAFT_STORAGE_KEY);
}

export function isFundingTerminalState(state: string | null | undefined): boolean {
  return state === 'completed' || state === 'failed' || state === 'rejected';
}

export function isFundingAutoPollingState(state: string | null | undefined): boolean {
  return (
    state === 'accepted' ||
    state === 'submitting' ||
    state === 'executing' ||
    state === 'partially_hedged' ||
    state === 'reconciling'
  );
}
