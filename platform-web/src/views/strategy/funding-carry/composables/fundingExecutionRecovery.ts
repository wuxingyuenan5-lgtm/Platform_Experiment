export const FUNDING_PENDING_DRAFT_STORAGE_KEY = 'vg.platform.funding.pendingDraft';

export type FundingDraftState =
  | 'submitting'
  | 'executing'
  | 'partially_hedged'
  | 'reconciling'
  | 'result_unknown'
  | 'manual_intervention';

export interface FundingPendingDraft {
  idempotencyKey: string;
  instructionId?: string;
  action: 'open' | 'close';
  perpetualSymbol: string;
  spotSymbol: string;
  quantity: string;
  targetOpenInstructionId?: string;
  state: FundingDraftState;
}

export function readFundingDraft(
  storage: Pick<Storage, 'getItem'> = localStorage,
): FundingPendingDraft | null {
  const raw = storage.getItem(FUNDING_PENDING_DRAFT_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as FundingPendingDraft;
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
  return state === 'completed' || state === 'failed';
}
