import { computed, ref, type Ref } from 'vue';

import {
  closeCrossSpreadMarket,
  openCrossSpreadMarket,
  type CrossSpreadDirection,
  type CrossSpreadExecutionMode,
  type CrossSpreadExitPlanResult,
  type CrossSpreadLimitExecutionResult,
  type CrossSpreadLimitStrategy,
} from '@/api/platform/crossSpreadLifecycle';
import type { CloseOrder } from './mapCrossSpreadPositions';

export interface LogEntry {
  id: string;
  time: string;
  direction: string;
  type: string;
  qty: string;
  trigger: string;
  fill: string;
  status: string;
  channel: string;
}

type MessageTone = 'is-success' | 'is-error' | 'is-warn';

interface UseCrossSpreadExecutionOptions {
  qtyOz: Ref<number>;
  qtyInput?: Ref<string>;
  bybitQty: Ref<number>;
  mt5Lot: Ref<number | null>;
  quantityRules?: unknown;
  openDirection?: Ref<'long' | 'short'>;
  executionMode: Ref<CrossSpreadExecutionMode>;
  closeExecutionMode: Ref<CrossSpreadExecutionMode>;
  takeProfitExecution: Ref<CrossSpreadExecutionMode>;
  stopLossExecution: Ref<CrossSpreadExecutionMode>;
  openLimitStrategy: Ref<CrossSpreadLimitStrategy>;
  takeProfitLimitStrategy: Ref<CrossSpreadLimitStrategy>;
  stopLossLimitStrategy: Ref<CrossSpreadLimitStrategy>;
  closeLimitStrategy: Ref<CrossSpreadLimitStrategy>;
  triggerSpread: Ref<number | null>;
  acceptableSpread: Ref<number | null>;
  takeProfitSpread: Ref<number | null>;
  stopLossSpread: Ref<number | null>;
  closeLimitSpread: Ref<number | null>;
  longSpread: Ref<number | null>;
  shortSpread: Ref<number | null>;
  exitPlans: Ref<CrossSpreadExitPlanResult[]>;
  closeOrders: Ref<CloseOrder[]>;
  upsertExitPlan?: (plan: CrossSpreadExitPlanResult) => void;
  refreshExitPlans: () => Promise<string>;
  refreshSnapshot: () => Promise<void>;
  refreshObservability?: () => Promise<void>;
}

type PendingAction =
  | { kind: 'OPEN'; direction: 'LONG_SPREAD' | 'SHORT_SPREAD' }
  | { kind: 'CLOSE'; planId: string }
  | { kind: 'CLOSE_ALL' };

function requestErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null) {
    const candidate = error as {
      message?: string;
      response?: { data?: { detail?: string | Array<{ msg?: string }> } };
    };
    const detail = candidate.response?.data?.detail;
    if (Array.isArray(detail)) {
      return (
        detail
          .map((item) => item.msg)
          .filter(Boolean)
          .join('；') || fallback
      );
    }
    return detail || candidate.message || fallback;
  }
  return fallback;
}

function formatSigned(value: number): string {
  return `${value > 0 ? '+' : ''}${value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatNullableSigned(value: number | null | undefined): string {
  return value === null || value === undefined ? '--' : formatSigned(value);
}

function numericText(value: number | null | undefined, fallback = 0): string {
  return String(value ?? fallback);
}

function optionalNumericText(value: number | null | undefined): string | undefined {
  return value === null || value === undefined ? undefined : String(value);
}

export function useCrossSpreadExecution(options: UseCrossSpreadExecutionOptions) {
  const submitLoading = ref(false);
  const confirmVisible = ref(false);
  const executionLogs = ref<LogEntry[]>([]);
  const executionMessage = ref('');
  const executionMessageTone = ref<MessageTone>('is-warn');
  const limitEvidence = ref<CrossSpreadLimitExecutionResult | null>(null);
  const pendingAction = ref<PendingAction | null>(null);

  const confirmGuardMessage = computed(() => '');
  const confirmSummary = computed(() => {
    const action = pendingAction.value;
    const closeOrders =
      action?.kind === 'CLOSE'
        ? options.closeOrders.value.filter((order) => order.id === action.planId)
        : action?.kind === 'CLOSE_ALL'
        ? options.closeOrders.value
        : [];
    const closeQuantityOz = closeOrders.reduce((total, order) => total + order.qtyOz, 0);
    const mt5LotPerOz =
      options.qtyOz.value > 0 && options.mt5Lot.value !== null
        ? options.mt5Lot.value / options.qtyOz.value
        : null;
    const closeMt5Lot = mt5LotPerOz === null ? null : closeQuantityOz * mt5LotPerOz;
    const mode =
      action?.kind === 'CLOSE' || action?.kind === 'CLOSE_ALL'
        ? options.closeExecutionMode.value === 'market'
          ? '市价平仓'
          : '限价平仓'
        : options.executionMode.value === 'market'
        ? '市价开仓'
        : '限价开仓';
    const directionLabel =
      action?.kind === 'OPEN'
        ? action.direction === 'LONG_SPREAD'
          ? '开多价差'
          : '开空价差'
        : '平仓价差';
    const closeMarketSpread =
      action?.kind === 'CLOSE'
        ? options.closeOrders.value.find((order) => order.id === action.planId)?.direction ===
          'LONG_SPREAD'
          ? options.longSpread.value
          : options.shortSpread.value
        : null;
    return {
      action: directionLabel,
      qty: `${
        action?.kind === 'CLOSE' || action?.kind === 'CLOSE_ALL'
          ? closeQuantityOz
          : options.qtyOz.value
      }`,
      legs:
        action?.kind === 'CLOSE' || action?.kind === 'CLOSE_ALL'
          ? `BYBIT ${closeQuantityOz.toLocaleString('en-US', { maximumFractionDigits: 2 })} / MT5 ${
              closeMt5Lot === null
                ? '--'
                : closeMt5Lot.toLocaleString('en-US', { maximumFractionDigits: 4 })
            }`
          : `BYBIT ${options.bybitQty.value.toLocaleString('en-US', {
              maximumFractionDigits: 2,
            })} / MT5 ${
              options.mt5Lot.value === null
                ? '--'
                : options.mt5Lot.value.toLocaleString('en-US', { maximumFractionDigits: 4 })
            }`,
      mode,
      marketSpread:
        action?.kind === 'CLOSE' || action?.kind === 'CLOSE_ALL'
          ? closeMarketSpread === null || closeMarketSpread === undefined
            ? '--'
            : formatSigned(closeMarketSpread)
          : formatNullableSigned(options.longSpread.value),
      spreadRange:
        action?.kind === 'OPEN'
          ? `${formatNullableSigned(options.triggerSpread.value)} / ${formatNullableSigned(
              options.acceptableSpread.value,
            )}`
          : '--',
      takeProfit:
        action?.kind === 'OPEN' ? formatNullableSigned(options.takeProfitSpread.value) : '--',
      stopLoss: action?.kind === 'OPEN' ? formatNullableSigned(options.stopLossSpread.value) : '--',
    };
  });

  function setExecutionMessage(nextMessage: string, nextTone: MessageTone) {
    executionMessage.value = nextMessage;
    executionMessageTone.value = nextTone;
  }

  function openConfirm(action: string) {
    if (action.startsWith('CLOSE:')) {
      pendingAction.value = { kind: 'CLOSE', planId: action.slice('CLOSE:'.length) };
    } else if (action === 'CLOSE_ALL') {
      pendingAction.value = { kind: 'CLOSE_ALL' };
    }
    confirmVisible.value = true;
    setExecutionMessage('', 'is-warn');
  }

  function prepareOpenDraft(direction: 'long' | 'short') {
    pendingAction.value = {
      kind: 'OPEN',
      direction: direction === 'long' ? 'LONG_SPREAD' : 'SHORT_SPREAD',
    };
    confirmVisible.value = true;
    setExecutionMessage('', 'is-warn');
  }

  async function refreshExecutionViews() {
    const jobs: Array<Promise<unknown>> = [options.refreshExitPlans(), options.refreshSnapshot()];
    if (options.refreshObservability) jobs.push(options.refreshObservability());
    await Promise.allSettled(jobs);
  }

  async function confirmOrder() {
    const action = pendingAction.value;
    if (!action) return;
    submitLoading.value = true;
    setExecutionMessage('', 'is-warn');
    try {
      if (action.kind === 'OPEN') {
        if (options.executionMode.value === 'limit' && options.triggerSpread.value === null) {
          setExecutionMessage('限价开仓必须填写开仓价差', 'is-warn');
          return;
        }
        const result = await openCrossSpreadMarket({
          direction: action.direction as CrossSpreadDirection,
          quantityOz: String(options.qtyOz.value),
          takeProfitSpread: optionalNumericText(options.takeProfitSpread.value),
          stopLossSpread: optionalNumericText(options.stopLossSpread.value),
          executionMode: options.executionMode.value,
          limitSpread:
            options.executionMode.value === 'limit'
              ? numericText(options.triggerSpread.value)
              : undefined,
          limitStrategy: options.openLimitStrategy.value,
          takeProfitExecutionMode: options.takeProfitExecution.value,
          stopLossExecutionMode: options.stopLossExecution.value,
          takeProfitLimitStrategy: options.takeProfitLimitStrategy.value,
          stopLossLimitStrategy: options.stopLossLimitStrategy.value,
        });
        if (result.exitPlan) {
          options.upsertExitPlan?.(result.exitPlan);
        }
        limitEvidence.value = result.limitExecution ?? null;
        if (result.executionBatch?.status === 'hedged') {
          setExecutionMessage('开仓成功，双边已对冲', 'is-success');
        } else {
          setExecutionMessage(
            `开仓提交完成，批次状态：${result.executionBatch?.status ?? '未知'}`,
            'is-warn',
          );
        }
      } else if (action.kind === 'CLOSE') {
        if (
          options.closeExecutionMode.value === 'limit' &&
          options.closeLimitSpread.value === null
        ) {
          setExecutionMessage('限价平仓必须填写平仓限制价差', 'is-warn');
          return;
        }
        const result = await closeCrossSpreadMarket(
          action.planId,
          options.closeExecutionMode.value,
          options.closeExecutionMode.value === 'limit'
            ? numericText(options.closeLimitSpread.value)
            : undefined,
          options.closeLimitStrategy.value,
        );
        options.upsertExitPlan?.(result.exitPlan);
        setExecutionMessage('平仓指令已提交', 'is-success');
      } else {
        const closablePlans = options.exitPlans.value.filter(
          (plan) => plan.status === 'active' || plan.status === 'manual_intervention',
        );
        if (!closablePlans.length) {
          setExecutionMessage('没有可平仓的退出计划', 'is-warn');
          return;
        }
        for (const plan of closablePlans) {
          const result = await closeCrossSpreadMarket(
            plan.planId,
            options.closeExecutionMode.value,
            options.closeExecutionMode.value === 'limit'
              ? numericText(options.closeLimitSpread.value)
              : undefined,
            options.closeLimitStrategy.value,
          );
          options.upsertExitPlan?.(result.exitPlan);
        }
        setExecutionMessage(`已提交 ${closablePlans.length} 个退出计划平仓`, 'is-success');
      }
      void refreshExecutionViews();
    } catch (error: unknown) {
      setExecutionMessage(requestErrorMessage(error, '价差指令执行失败'), 'is-error');
    } finally {
      submitLoading.value = false;
      confirmVisible.value = false;
      pendingAction.value = null;
    }
  }

  return {
    confirmGuardMessage,
    confirmOrder,
    confirmSummary,
    confirmVisible,
    executionLogs,
    executionMessage,
    executionMessageTone,
    limitEvidence,
    openConfirm,
    prepareOpenDraft,
    setExecutionMessage,
    submitLoading,
  };
}
