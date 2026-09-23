import { createStrategyApi, strategyData } from './strategyApi';
import type { components } from './generated/strategy';

export type CrossSpreadLeverageResult = components['schemas']['CrossSpreadLeverageResponse'];
export type CrossSpreadTradingRulesResult =
  components['schemas']['CrossSpreadTradingRulesResponse'];
const api = createStrategyApi(30_000);
export async function closeAbnormalOpen(batchId: string, actor: string) {
  return strategyData(
    await api.POST('/api/v1/trading/execution-batches/{batch_id}/risk-actions', {
      params: { path: { batch_id: batchId } },
      body: {
        idempotencyKey: `cross-abnormal-close:${batchId}`,
        action: 'flatten_filled_legs',
        actor,
        reason: 'Owner confirmed closing the abnormal opening fill',
      },
    }),
  );
}
export async function getCrossSpreadLeverage(): Promise<CrossSpreadLeverageResult> {
  return strategyData(await api.GET('/api/v1/trading/cross-spread/leverage'));
}
export async function getCrossSpreadTradingRules(): Promise<CrossSpreadTradingRulesResult> {
  return strategyData(await api.GET('/api/v1/trading/cross-spread/trading-rules'));
}
export async function setCrossSpreadLeverage(leverage: string): Promise<CrossSpreadLeverageResult> {
  return strategyData(
    await api.POST('/api/v1/trading/cross-spread/leverage', { body: { leverage } }),
  );
}

export type CrossSpreadDirection = 'LONG_SPREAD' | 'SHORT_SPREAD';
export type CrossSpreadExecutionMode = 'market' | 'limit';
export type CrossSpreadLimitStrategy = 'fok' | 'post_only_chase' | 'market';
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

export type CrossSpreadOrderIntentResult = components['schemas']['CrossSpreadOrderIntentResponse'];

export type CrossSpreadLimitExecutionResult =
  components['schemas']['CrossSpreadLimitExecutionResponse'];

export type CrossSpreadExitPlanResult = components['schemas']['CrossSpreadExitPlanResponse'];

export type CrossSpreadMarketOpenInput = components['schemas']['CrossSpreadMarketOpenRequest'];

export type CrossSpreadMarketOpenResult = components['schemas']['CrossSpreadOpenResult'];

export type CrossSpreadMarketCloseResult = components['schemas']['CrossSpreadCloseResult'];

export type CrossSpreadMarketCloseInput = Omit<
  components['schemas']['CrossSpreadMarketCloseRequest'],
  'maxAdverseSpread'
> & { maxAdverseSpread?: string };

export type CrossSpreadExitPlanThresholdUpdateInput =
  components['schemas']['CrossSpreadExitPlanUpdateRequest'];

export type CrossSpreadPreflightInput = components['schemas']['CrossSpreadPreflightRequest'];

export type CrossSpreadPreflightResult = components['schemas']['CrossSpreadPreflightResponse'];

export async function getCrossSpreadInstruction(idempotencyKey: string) {
  const instructions = strategyData(
    await api.GET('/api/v1/strategies/{strategy_instance_id}/instructions', {
      params: { path: { strategy_instance_id: 'strategy_cross_venue_spread_instance_default' } },
    }),
  );
  const instruction = instructions.find((item) => item.idempotencyKey === idempotencyKey);
  if (!instruction) return null;
  if (
    typeof instruction.instructionId !== 'string' ||
    typeof instruction.status !== 'string' ||
    !(instruction.executionBatchId === null || typeof instruction.executionBatchId === 'string')
  ) {
    throw new Error('价差指令状态数据不完整');
  }
  return {
    instructionId: instruction.instructionId,
    status: instruction.status,
    executionBatchId:
      typeof instruction.executionBatchId === 'string' ? instruction.executionBatchId : null,
  };
}

export async function openCrossSpreadMarket(
  input: CrossSpreadMarketOpenInput,
): Promise<CrossSpreadMarketOpenResult> {
  const response = await api.POST('/api/v1/trading/cross-spread/lifecycle/open', { body: input });
  return strategyData(response);
}

export async function prepareCrossSpreadExecution(
  input: CrossSpreadPreflightInput,
): Promise<CrossSpreadPreflightResult> {
  const response = await api.POST('/api/v1/trading/cross-spread/preflight', { body: input });
  return strategyData(response);
}

export async function getCrossSpreadExitPlans(
  status?: CrossSpreadExitPlanStatus,
): Promise<CrossSpreadExitPlanResult[]> {
  const response = await api.GET('/api/v1/trading/cross-spread/exit-plans', {
    params: { query: status ? { status } : undefined },
  });
  return strategyData(response);
}

export async function updateCrossSpreadExitPlanThresholds(
  planId: string,
  input: CrossSpreadExitPlanThresholdUpdateInput,
): Promise<CrossSpreadExitPlanResult> {
  const response = await api.PATCH('/api/v1/trading/cross-spread/exit-plans/{plan_id}', {
    params: { path: { plan_id: planId } },
    body: input,
  });
  return strategyData(response);
}

export async function closeCrossSpreadMarket(
  planId: string,
  input: CrossSpreadMarketCloseInput,
): Promise<CrossSpreadMarketCloseResult> {
  const response = await api.POST('/api/v1/trading/cross-spread/exit-plans/{plan_id}/close', {
    params: { path: { plan_id: planId } },
    body: {
      executionMode: input.executionMode,
      limitStrategy: input.limitStrategy ?? 'fok',
      ...(input.idempotencyKey ? { idempotencyKey: input.idempotencyKey } : {}),
      ...(input.quantityOz === undefined ? {} : { quantityOz: input.quantityOz }),
      ...(input.limitSpread === undefined ? {} : { limitSpread: input.limitSpread }),
      maxAdverseSpread: input.maxAdverseSpread ?? '0',
    },
  });
  return strategyData(response);
}
