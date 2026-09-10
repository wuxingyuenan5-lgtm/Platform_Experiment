import { createStrategyApi, strategyData } from './strategyApi';
import type { components } from './generated/strategy';

const api = createStrategyApi();
export type FundingSymbolOption = components['schemas']['FundingSymbolOption'];
export type FundingExecutionContext = components['schemas']['FundingExecutionContextResponse'];
export type FundingWorkspaceResponse = components['schemas']['FundingWorkspaceResponse'];
export type FundingPositionGroup = components['schemas']['FundingPositionGroupResponse'];

export async function getFundingExecutionContext(
  params?: {
    perpetualSymbol?: string;
    spotSymbol?: string;
    notional?: string;
    quantity?: string;
  },
  signal?: AbortSignal,
): Promise<FundingExecutionContext> {
  return strategyData(
    await api.GET('/api/v1/trading/funding/execution-context', {
      params: { query: params },
      signal,
    }),
  );
}

export async function getFundingPositionGroups(
  scope: 'active' | 'history' | 'all' = 'all',
  signal?: AbortSignal,
): Promise<FundingPositionGroup[]> {
  return strategyData(
    await api.GET('/api/v1/trading/funding/positions', {
      params: { query: { scope } },
      signal,
    }),
  );
}

export async function submitFundingInstruction(
  input: components['schemas']['FundingInstructionRequest'],
): Promise<FundingWorkspaceResponse> {
  return strategyData(await api.POST('/api/v1/trading/funding/instructions', { body: input }));
}

export async function getFundingInstructionWorkspace(
  instructionId: string,
  signal?: AbortSignal,
): Promise<FundingWorkspaceResponse> {
  return strategyData(
    await api.GET('/api/v1/trading/funding/instructions/{instruction_id}', {
      params: { path: { instruction_id: instructionId } },
      signal,
    }),
  );
}

export async function getFundingInstructionWorkspaceByIdempotency(
  idempotencyKey: string,
  signal?: AbortSignal,
): Promise<FundingWorkspaceResponse> {
  return strategyData(
    await api.GET('/api/v1/trading/funding/instructions', {
      params: { query: { idempotencyKey } },
      signal,
    }),
  );
}

export async function closeFundingAbnormalOpen(batchId: string, actor: string) {
  return strategyData(
    await api.POST('/api/v1/trading/execution-batches/{batch_id}/risk-actions', {
      params: { path: { batch_id: batchId } },
      body: {
        idempotencyKey: `funding-abnormal-close:${batchId}`,
        action: 'flatten_filled_legs',
        actor,
        reason: 'Owner confirmed closing the abnormal Funding opening fills',
      },
    }),
  );
}
