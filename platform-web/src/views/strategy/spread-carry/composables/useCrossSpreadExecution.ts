import { computed, ref, type ComputedRef, type Ref } from 'vue';
import {
  closeCrossSpreadMarket,
  openCrossSpreadMarket,
  type CrossSpreadExitPlanResult,
  type CrossSpreadExecutionMode,
  type CrossSpreadLimitExecutionResult,
  type CrossSpreadLimitStrategy,
} from '@/api/platform/crossSpreadLifecycle';
import { CROSS_SPREAD_DEFAULT_EXECUTION_LOGS } from './crossSpreadFixtures';
import type { CloseOrder } from './useCrossSpreadPositions';
import {
  formatNullablePrice,
  formatNumber,
  formatSigned,
} from './useCrossSpreadFormatting';

interface QuantityRules {
  minOz: number;
  stepOz: number;
  mt5Multiplier: number;
}

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
  qtyInput: Ref<string>;
  bybitQty: ComputedRef<number>;
  mt5Lot: ComputedRef<number | null>;
  quantityRules: ComputedRef<QuantityRules | null>;
  openDirection: Ref<'long' | 'short'>;
  executionMode: Ref<CrossSpreadExecutionMode>;
  closeExecutionMode: Ref<CrossSpreadExecutionMode>;
  takeProfitExecution: Ref<CrossSpreadExecutionMode>;
  stopLossExecution: Ref<CrossSpreadExecutionMode>;
  openLimitStrategy: Ref<CrossSpreadLimitStrategy>;
  takeProfitLimitStrategy: Ref<CrossSpreadLimitStrategy>;
  stopLossLimitStrategy: Ref<CrossSpreadLimitStrategy>;
  closeLimitStrategy: Ref<CrossSpreadLimitStrategy>;
  triggerSpread: Ref<number>;
  acceptableSpread: Ref<number>;
  takeProfitSpread: Ref<number>;
  stopLossSpread: Ref<number>;
  closeLimitSpread: Ref<number>;
  longSpread: ComputedRef<number | null>;
  shortSpread: ComputedRef<number | null>;
  exitPlans: Ref<CrossSpreadExitPlanResult[]>;
  closeOrders: ComputedRef<CloseOrder[]>;
  refreshExitPlans: () => Promise<void>;
  refreshSnapshot: () => Promise<void>;
}

export function useCrossSpreadExecution(options: UseCrossSpreadExecutionOptions) {
  const submitLoading = ref(false);
  const confirmVisible = ref(false);
  const confirmAction = ref('OPEN_LONG');
  const limitEvidence = ref<CrossSpreadLimitExecutionResult | null>(null);
  const executionMessage = ref('');
  const executionMessageTone = ref<MessageTone>('is-success');
  const executionLogs = ref<LogEntry[]>(
    CROSS_SPREAD_DEFAULT_EXECUTION_LOGS.map((entry) => ({ ...entry })),
  );
  let localLogSequence = executionLogs.value.length;

  const openValidationError = computed(() => {
    if (options.qtyOz.value <= 0) return '数量必须大于 0';
    const rules = options.quantityRules.value;
    if (!rules) return '合约规格加载中';
    if (options.qtyOz.value < rules.minOz) {
      return `当前合约最小下单数量为 ${formatNumber(rules.minOz, 2)} 盎司`;
    }
    const steps = (options.qtyOz.value - rules.minOz) / rules.stepOz;
    if (Math.abs(steps - Math.round(steps)) > 1e-8) {
      return `当前合约下单步长为 ${formatNumber(rules.stepOz, 2)} 盎司`;
    }
    if (!Number.isFinite(options.takeProfitSpread.value) || !Number.isFinite(options.stopLossSpread.value)) {
      return '止盈止损价差必须有效';
    }
    if (options.executionMode.value === 'limit' && !Number.isFinite(options.acceptableSpread.value)) {
      return '可接受价差必须有效';
    }
    if (options.openDirection.value === 'long' && options.takeProfitSpread.value <= options.stopLossSpread.value) {
      return '开多价差的止盈价差必须高于止损价差';
    }
    if (options.openDirection.value === 'short' && options.takeProfitSpread.value >= options.stopLossSpread.value) {
      return '开空价差的止盈价差必须低于止损价差';
    }
    return '';
  });

  const closeValidationError = computed(() =>
    options.closeExecutionMode.value === 'limit' && !Number.isFinite(options.closeLimitSpread.value)
      ? '限价平仓价差必须有效'
      : '',
  );

  const confirmSummary = computed(() => {
    if (confirmAction.value === 'CLOSE_ALL') {
      return {
        action: '手动全平',
        qty: `${formatNumber(options.closeOrders.value.reduce((sum, item) => sum + item.qtyOz, 0), 2)} 盎司`,
        legs: '逐笔平结全部持仓',
        mode: options.closeExecutionMode.value === 'market' ? '市价平仓' : '限价平仓',
        marketSpread: `平多 ${formatExecutionSpread(options.longSpread.value)} / 平空 ${formatExecutionSpread(options.shortSpread.value)}`,
        spreadRange: options.closeExecutionMode.value === 'market' ? '市价执行' : `${options.closeLimitSpread.value.toFixed(2)} USDT`,
        takeProfit: '--',
        stopLoss: '--',
      };
    }

    if (confirmAction.value.startsWith('CLOSE:')) {
      const target = options.closeOrders.value.find((item) => `CLOSE:${item.id}` === confirmAction.value);
      const marketSpread = target?.direction === 'SHORT_SPREAD' ? options.shortSpread.value : options.longSpread.value;
      return {
        action: target?.direction === 'LONG_SPREAD' ? '平多价差' : '平空价差',
        qty: `${formatNumber(target?.qtyOz ?? 0, 2)} 盎司`,
        legs: `${formatNumber(target?.qtyOz ?? 0, 2)} / ${formatNullablePrice(convertOzToMt5Lot(target?.qtyOz ?? 0), 2)}`,
        mode: options.closeExecutionMode.value === 'market' ? '市价平仓' : '限价平仓',
        marketSpread: formatExecutionSpread(marketSpread),
        spreadRange: options.closeExecutionMode.value === 'market' ? '市价执行' : `${options.closeLimitSpread.value.toFixed(2)} USDT`,
        takeProfit: `${formatSigned(target?.takeProfit ?? 0)} USDT`,
        stopLoss: `${formatSigned(target?.stopLoss ?? 0)} USDT`,
      };
    }

    const marketSpread = options.openDirection.value === 'long' ? options.longSpread.value : options.shortSpread.value;
    return {
      action: options.openDirection.value === 'long' ? '开多价差' : '开空价差',
      qty: `${formatNumber(options.qtyOz.value, 2)} 盎司`,
      legs: `${formatNumber(options.bybitQty.value, 2)} / ${formatNullablePrice(options.mt5Lot.value, 2)}`,
      mode: options.executionMode.value === 'market' ? '市价开仓' : '限价开仓',
      marketSpread: formatExecutionSpread(marketSpread),
      spreadRange: `${options.triggerSpread.value.toFixed(2)} / ${options.acceptableSpread.value.toFixed(2)} USDT`,
      takeProfit: `${options.takeProfitSpread.value.toFixed(2)} USDT / ${options.takeProfitExecution.value === 'limit' ? '限价' : '市价'}`,
      stopLoss: `${options.stopLossSpread.value.toFixed(2)} USDT / ${options.stopLossExecution.value === 'limit' ? '限价' : '市价'}`,
    };
  });

  const confirmGuardMessage = computed(() => {
    if ((confirmAction.value === 'OPEN_LONG' || confirmAction.value === 'OPEN_SHORT') && openValidationError.value) {
      return openValidationError.value;
    }
    if (confirmAction.value.startsWith('CLOSE') && closeValidationError.value) {
      return closeValidationError.value;
    }
    return '';
  });

  function prepareOpenDraft(direction: 'long' | 'short') {
    options.openDirection.value = direction;
    openConfirm(direction === 'long' ? 'OPEN_LONG' : 'OPEN_SHORT');
  }

  function openConfirm(action: string) {
    confirmAction.value = action;
    confirmVisible.value = true;
  }

  async function confirmOrder() {
    confirmVisible.value = false;
    if (confirmAction.value.startsWith('CLOSE') && closeValidationError.value) {
      setExecutionMessage(closeValidationError.value, 'is-error');
      return;
    }
    if ((confirmAction.value === 'OPEN_LONG' || confirmAction.value === 'OPEN_SHORT') && openValidationError.value) {
      setExecutionMessage(openValidationError.value, 'is-error');
      return;
    }
    submitLoading.value = true;
    limitEvidence.value = null;
    try {
      if (confirmAction.value === 'OPEN_LONG' || confirmAction.value === 'OPEN_SHORT') {
        const result = await openCrossSpreadMarket({
          direction: resolveOpenDirection(),
          quantityOz: String(options.qtyOz.value),
          takeProfitSpread: String(options.takeProfitSpread.value),
          stopLossSpread: String(options.stopLossSpread.value),
          executionMode: options.executionMode.value,
          limitStrategy: options.openLimitStrategy.value,
          takeProfitExecutionMode: options.takeProfitExecution.value,
          stopLossExecutionMode: options.stopLossExecution.value,
          takeProfitLimitStrategy: options.takeProfitLimitStrategy.value,
          stopLossLimitStrategy: options.stopLossLimitStrategy.value,
          ...(options.executionMode.value === 'limit' ? { limitSpread: String(options.acceptableSpread.value) } : {}),
        });
        limitEvidence.value = result.limitExecution || null;
        setExecutionMessage(
          result.executionBatch.status === 'hedged'
            ? '开仓已提交并生成退出计划'
            : result.executionBatch.failureReason || '开仓未形成完整退出计划',
          result.executionBatch.status === 'hedged' ? 'is-success' : 'is-warn',
        );
      } else if (confirmAction.value === 'CLOSE_ALL') {
        const targets = [...options.exitPlans.value.filter((plan) => plan.status === 'active')];
        for (const plan of targets) {
          const result = await closePlan(plan);
          limitEvidence.value = result.limitExecution || limitEvidence.value;
        }
        setExecutionMessage('已逐笔提交全部活动退出计划的平仓请求', 'is-success');
      } else {
        const plan = resolveClosePlan();
        if (!plan) throw new Error('未找到对应退出计划');
        const result = await closePlan(plan);
        limitEvidence.value = result.limitExecution || null;
        setExecutionMessage(
          result.exitPlan.status === 'closed' ? '平仓完成' : '平仓请求已提交，退出计划仍需跟踪',
          result.exitPlan.status === 'closed' ? 'is-success' : 'is-warn',
        );
      }
      await options.refreshExitPlans();
      appendLog({
        time: nowTime(),
        direction: confirmSummary.value.action,
        type: confirmSummary.value.mode,
        qty: confirmSummary.value.qty,
        trigger: confirmSummary.value.spreadRange,
        fill: executionMessage.value,
        status: executionMessageTone.value === 'is-success' ? '成功' : '待确认',
        channel: 'LIFECYCLE',
      });
      await options.refreshSnapshot();
    } catch (error) {
      const message = resolveError(error, '执行失败');
      setExecutionMessage(message, 'is-error');
      appendLog({
        time: nowTime(),
        direction: confirmSummary.value.action,
        type: confirmSummary.value.mode,
        qty: confirmSummary.value.qty,
        trigger: confirmSummary.value.spreadRange,
        fill: message,
        status: '拒绝',
        channel: 'RISK_GATE',
      });
    } finally {
      submitLoading.value = false;
    }
  }

  function setExecutionMessage(nextMessage: string, nextTone: MessageTone) {
    executionMessage.value = nextMessage;
    executionMessageTone.value = nextTone;
  }

  function appendLog(entry: Omit<LogEntry, 'id'>) {
    localLogSequence += 1;
    executionLogs.value.unshift({
      id: `local-log-${localLogSequence}`,
      ...entry,
    });
  }

  function closePlan(plan: CrossSpreadExitPlanResult) {
    return closeCrossSpreadMarket(
      plan.planId,
      options.closeExecutionMode.value,
      options.closeExecutionMode.value === 'limit' ? String(options.closeLimitSpread.value) : undefined,
      options.closeLimitStrategy.value,
    );
  }

  function resolveOpenDirection() {
    return confirmAction.value === 'OPEN_SHORT' ? 'SHORT_SPREAD' : 'LONG_SPREAD';
  }

  function resolveClosePlan() {
    const planId = confirmAction.value.replace('CLOSE:', '');
    return options.exitPlans.value.find((plan) => plan.planId === planId && plan.status === 'active');
  }

  function convertOzToMt5Lot(value: number) {
    const multiplier = options.quantityRules.value?.mt5Multiplier;
    return multiplier ? value / multiplier : null;
  }

  return {
    closeValidationError,
    confirmGuardMessage,
    confirmOrder,
    confirmSummary,
    confirmVisible,
    executionLogs,
    executionMessage,
    executionMessageTone,
    limitEvidence,
    openConfirm,
    openValidationError,
    prepareOpenDraft,
    setExecutionMessage,
    submitLoading,
  };
}

function formatExecutionSpread(value: number | null | undefined) {
  return value === null || value === undefined ? '--' : `${formatSigned(value)} USDT`;
}

function nowTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false });
}

function resolveError(error: unknown, fallback: string) {
  let message = fallback;
  if (typeof error === 'object' && error !== null) {
    const candidate = error as {
      message?: string;
      response?: { data?: { detail?: string | Array<{ msg?: string }> } };
    };
    const detail = candidate.response?.data?.detail;
    if (Array.isArray(detail)) {
      message = detail.map((item) => item.msg).filter(Boolean).join('; ') || fallback;
    } else {
      message = detail || candidate.message || fallback;
    }
  }
  if (message.includes('A non-closed cross-spread lifecycle already exists')) {
    return '已有未关闭的价差生命周期，请先平仓或关闭现有退出计划后再开新仓';
  }
  return message;
}


