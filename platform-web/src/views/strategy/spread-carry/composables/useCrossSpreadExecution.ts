import { useUserStore } from '@/store/modules/user';
import { computed, ref, watch, type Ref } from 'vue';
import { getExecutionBatch } from '@/api/platform/trading';

import {
  closeCrossSpreadMarket,
  getCrossSpreadInstruction,
  openCrossSpreadMarket,
  prepareCrossSpreadExecution,
  type CrossSpreadDirection,
  type CrossSpreadExecutionMode,
  type CrossSpreadExitPlanResult,
  type CrossSpreadLimitExecutionResult,
  type CrossSpreadLimitStrategy,
} from '@/api/platform/crossSpreadLifecycle';
import type { CloseOrder } from './mapCrossSpreadPositions';
import {
  clearExecutionDraft,
  canHandOffAbnormalBatch,
  createCloseAllExecutionDraft,
  isTerminalBatchStatus,
  persistExecutionDraft,
  readExecutionDraft,
  type PersistedExecutionDraft,
} from './crossSpreadExecutionRecovery';

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
  | { kind: 'CLOSE'; planId: string; quantityOz?: number }
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
  function captureInputs() {
    return {
      qtyOz: options.qtyOz.value,
      bybitQty: options.bybitQty.value,
      mt5Lot: options.mt5Lot.value,
      executionMode: options.executionMode.value,
      closeExecutionMode: options.closeExecutionMode.value,
      takeProfitExecution: options.takeProfitExecution.value,
      stopLossExecution: options.stopLossExecution.value,
      openLimitStrategy: options.openLimitStrategy.value,
      takeProfitLimitStrategy: options.takeProfitLimitStrategy.value,
      stopLossLimitStrategy: options.stopLossLimitStrategy.value,
      closeLimitStrategy: options.closeLimitStrategy.value,
      triggerSpread: options.triggerSpread.value,
      acceptableSpread: options.acceptableSpread.value,
      takeProfitSpread: options.takeProfitSpread.value,
      stopLossSpread: options.stopLossSpread.value,
      closeLimitSpread: options.closeLimitSpread.value,
      longSpread: options.longSpread.value,
      shortSpread: options.shortSpread.value,
      closeOrders: options.closeOrders.value.map((item) => ({ ...item })),
      exitPlans: options.exitPlans.value.map((item) => ({ ...item })),
    };
  }
  const inputs = ref(captureInputs());
  const userStore = useUserStore();
  const pendingDraftAbsent = ref(false);
  let pendingDraftRecoveryRunning = false;

  function draftKeys(draft: PersistedExecutionDraft): string[] {
    return draft.kind === 'CLOSE_ALL'
      ? draft.plans.filter((plan) => plan.submitted !== false).map((plan) => plan.idempotencyKey)
      : [draft.idempotencyKey];
  }

  function sameDraft(left: PersistedExecutionDraft | null, right: PersistedExecutionDraft) {
    return !!left && JSON.stringify(left) === JSON.stringify(right);
  }

  function canStartIntent(): boolean {
    if (userStore.authentication?.user.role !== 'ceo') {
      setExecutionMessage('仅 CEO 可下达交易指令', 'is-warn');
      return false;
    }
    if (submitLoading.value || confirmVisible.value) return false;
    if (readExecutionDraft()) {
      setExecutionMessage(
        pendingDraftAbsent.value
          ? '服务器未找到上一条指令；请先解除本地锁定，再重新核对持仓后操作。'
          : '上一条指令回执尚未确认，请先恢复原指令',
        'is-warn',
      );
      return false;
    }
    inputs.value = captureInputs();
    limitEvidence.value = null;
    return true;
  }

  async function canStartCloseIntent(): Promise<boolean> {
    const draft = readExecutionDraft();
    if (
      userStore.authentication?.user.role === 'ceo' &&
      !submitLoading.value &&
      !confirmVisible.value &&
      pendingDraftAbsent.value &&
      draft &&
      draft.kind !== 'OPEN'
    ) {
      await clearUnreceivedPendingExecution();
    }
    return canStartIntent();
  }

  const submitLoading = ref(false);
  const confirmVisible = ref(false);
  const executionLogs = ref<LogEntry[]>([]);
  const executionMessage = ref('');
  const executionMessageTone = ref<MessageTone>('is-warn');
  const limitEvidence = ref<CrossSpreadLimitExecutionResult | null>(null);
  const pendingAction = ref<PendingAction | null>(null);
  const preflightReady = ref(false);
  const preflightError = ref('');

  const confirmGuardMessage = computed(() => preflightError.value);
  function cancelConfirmation() {
    if (submitLoading.value && preflightReady.value) return;
    confirmVisible.value = false;
    pendingAction.value = null;
    preflightReady.value = false;
    preflightError.value = '';
    submitLoading.value = false;
    setExecutionMessage('', 'is-warn');
  }
  const confirmSummary = computed(() => {
    const action = pendingAction.value;
    const closeOrders =
      action?.kind === 'CLOSE'
        ? inputs.value.closeOrders.filter((order) => order.id === action.planId)
        : action?.kind === 'CLOSE_ALL'
        ? inputs.value.closeOrders.filter((order) => !order.isAbnormal)
        : [];
    const closeQuantityOz =
      action?.kind === 'CLOSE' && action.quantityOz !== undefined
        ? action.quantityOz
        : closeOrders.reduce((total, order) => total + order.qtyOz, 0);
    const mt5OnlyOrder =
      action?.kind === 'CLOSE' && closeOrders[0]?.mt5Only ? closeOrders[0] : null;
    const mt5LotPerOz =
      inputs.value.qtyOz > 0 && inputs.value.mt5Lot !== null
        ? inputs.value.mt5Lot / inputs.value.qtyOz
        : null;
    const closeMt5Lot = mt5LotPerOz === null ? null : closeQuantityOz * mt5LotPerOz;
    const mode =
      action?.kind === 'CLOSE' || action?.kind === 'CLOSE_ALL'
        ? inputs.value.closeExecutionMode === 'market'
          ? '市价平仓'
          : '限价平仓'
        : inputs.value.executionMode === 'market'
        ? '市价开仓'
        : '限价开仓';
    const directionLabel =
      action?.kind === 'OPEN'
        ? action.direction === 'LONG_SPREAD'
          ? '开多价差'
          : '开空价差'
        : action?.kind === 'CLOSE' && action.quantityOz !== undefined
        ? '部分平仓'
        : '全部平仓';
    const closeMarketSpread =
      action?.kind === 'CLOSE'
        ? inputs.value.closeOrders.find((order) => order.id === action.planId)?.direction ===
          'LONG_SPREAD'
          ? inputs.value.shortSpread
          : inputs.value.longSpread
        : null;
    return {
      action: mt5OnlyOrder ? '完成剩余 MT5 平仓' : directionLabel,
      qty: `${
        action?.kind === 'CLOSE' || action?.kind === 'CLOSE_ALL'
          ? closeQuantityOz
          : inputs.value.qtyOz
      }`,
      legs: mt5OnlyOrder
        ? `BYBIT 已成交，不再下单 / MT5 ${mt5OnlyOrder.remainingMt5Lots} 手 · Ticket ${mt5OnlyOrder.mt5PositionId}`
        : action?.kind === 'CLOSE' || action?.kind === 'CLOSE_ALL'
        ? `BYBIT ${closeQuantityOz.toLocaleString('en-US', { maximumFractionDigits: 2 })} / MT5 ${
            closeMt5Lot === null
              ? '--'
              : closeMt5Lot.toLocaleString('en-US', { maximumFractionDigits: 4 })
          }`
        : `BYBIT ${inputs.value.bybitQty.toLocaleString('en-US', {
            maximumFractionDigits: 2,
          })} / MT5 ${
            inputs.value.mt5Lot === null
              ? '--'
              : inputs.value.mt5Lot.toLocaleString('en-US', { maximumFractionDigits: 4 })
          }`,
      mode: `${mode}${
        mode.startsWith('限价')
          ? ` · ${
              (action?.kind === 'OPEN'
                ? inputs.value.openLimitStrategy
                : inputs.value.closeLimitStrategy) === 'market'
                ? '触发后市价'
                : '追逐限价'
            }`
          : ''
      }`,
      marketSpread:
        action?.kind === 'CLOSE' || action?.kind === 'CLOSE_ALL'
          ? closeMarketSpread === null || closeMarketSpread === undefined
            ? '--'
            : formatSigned(closeMarketSpread)
          : formatNullableSigned(
              action?.kind === 'OPEN' && action.direction === 'SHORT_SPREAD'
                ? inputs.value.shortSpread
                : inputs.value.longSpread,
            ),
      spreadRange:
        action?.kind === 'OPEN'
          ? `${formatNullableSigned(inputs.value.triggerSpread)} / ${formatNullableSigned(
              inputs.value.acceptableSpread,
            )}`
          : `${formatNullableSigned(inputs.value.closeLimitSpread)} / ${
              inputs.value.acceptableSpread ?? 0
            }`,
      takeProfit:
        action?.kind === 'OPEN' ? formatNullableSigned(inputs.value.takeProfitSpread) : '--',
      stopLoss: action?.kind === 'OPEN' ? formatNullableSigned(inputs.value.stopLossSpread) : '--',
    };
  });

  function setExecutionMessage(nextMessage: string, nextTone: MessageTone) {
    executionMessage.value = nextMessage;
    executionMessageTone.value = nextTone;
  }

  async function prepareAction(action: PendingAction) {
    preflightReady.value = false;
    preflightError.value = '';
    submitLoading.value = true;
    setExecutionMessage('正在完成账户、报价和保证金预检…', 'is-warn');
    try {
      const orders =
        action.kind === 'CLOSE'
          ? inputs.value.closeOrders.filter((order) => order.id === action.planId)
          : action.kind === 'CLOSE_ALL'
          ? inputs.value.closeOrders.filter((order) => !order.isAbnormal)
          : [];
      if (action.kind === 'OPEN') {
        await prepareCrossSpreadExecution({
          action: action.direction === 'LONG_SPREAD' ? 'OPEN_LONG' : 'OPEN_SHORT',
          quantityOz: String(inputs.value.qtyOz),
        });
      } else {
        await Promise.all(
          orders.map((order) =>
            prepareCrossSpreadExecution({
              exitPlanId: order.id,
              action: order.direction === 'LONG_SPREAD' ? 'CLOSE_LONG' : 'CLOSE_SHORT',
              quantityOz: String(
                action.kind === 'CLOSE' && action.quantityOz !== undefined
                  ? action.quantityOz
                  : order.qtyOz,
              ),
            }),
          ),
        );
      }
      if (pendingAction.value !== action || !confirmVisible.value) return;
      preflightReady.value = true;
      setExecutionMessage('预检完成，可以确认下单', 'is-success');
    } catch (error) {
      if (pendingAction.value !== action || !confirmVisible.value) return;
      preflightError.value = requestErrorMessage(error, '执行预检失败');
      setExecutionMessage(preflightError.value, 'is-error');
    } finally {
      if (pendingAction.value === action) submitLoading.value = false;
    }
  }

  async function openConfirm(action: string) {
    if (!(await canStartCloseIntent())) return;
    if (action.startsWith('CLOSE:')) {
      pendingAction.value = { kind: 'CLOSE', planId: action.slice('CLOSE:'.length) };
    } else if (action === 'CLOSE_ALL') {
      pendingAction.value = { kind: 'CLOSE_ALL' };
    }
    confirmVisible.value = true;
    setExecutionMessage('', 'is-warn');
    if (pendingAction.value) void prepareAction(pendingAction.value);
  }

  async function openPartialClose(planId: string, quantityOz: number) {
    if (!(await canStartCloseIntent())) return;
    const order = inputs.value.closeOrders.find((candidate) => candidate.id === planId);
    if (!order || !Number.isFinite(quantityOz) || quantityOz <= 0 || quantityOz >= order.qtyOz) {
      setExecutionMessage('部分平仓数量必须大于 0 且小于该笔剩余数量', 'is-warn');
      return;
    }
    pendingAction.value = { kind: 'CLOSE', planId, quantityOz };
    confirmVisible.value = true;
    setExecutionMessage('', 'is-warn');
    void prepareAction(pendingAction.value);
  }

  function prepareOpenDraft(direction: 'long' | 'short') {
    if (!canStartIntent()) return;
    pendingAction.value = {
      kind: 'OPEN',
      direction: direction === 'long' ? 'LONG_SPREAD' : 'SHORT_SPREAD',
    };
    confirmVisible.value = true;
    setExecutionMessage('', 'is-warn');
    void prepareAction(pendingAction.value);
  }

  async function refreshExecutionViews() {
    const jobs: Array<Promise<unknown>> = [options.refreshExitPlans(), options.refreshSnapshot()];
    if (options.refreshObservability) jobs.push(options.refreshObservability());
    await Promise.allSettled(jobs);
  }

  async function releaseRejectedDraft(error: unknown) {
    const response = (error as { response?: { status?: number; data?: { detail?: unknown } } })
      ?.response;
    if (!response?.data?.detail || ![400, 401, 403, 409, 422, 423].includes(response.status ?? 0)) {
      return;
    }
    const draft = readExecutionDraft();
    if (!draft) return;
    // Only a completed, explicit server rejection followed by an authoritative
    // absent instruction releases this intent. Timeouts and failed reads do not.
    try {
      const keys =
        draft.kind === 'CLOSE_ALL'
          ? draft.plans
              .filter((plan) => plan.submitted !== false)
              .map((plan) => plan.idempotencyKey)
          : [draft.idempotencyKey];
      const instructions = await Promise.all(keys.map(getCrossSpreadInstruction));
      if (
        instructions.every((item) => item === null || ['completed', 'failed'].includes(item.status))
      ) {
        clearExecutionDraft();
      }
    } catch {
      // Keep the unresolved identity when its existence cannot be established.
    }
  }

  async function confirmOrder() {
    if (submitLoading.value || !confirmVisible.value || readExecutionDraft()) return;
    const action = pendingAction.value;
    if (!action) return;
    if (!preflightReady.value) {
      setExecutionMessage(preflightError.value || '请等待执行预检完成', 'is-warn');
      return;
    }
    submitLoading.value = true;
    setExecutionMessage('', 'is-warn');
    try {
      if (action.kind === 'OPEN') {
        if (inputs.value.executionMode === 'limit' && inputs.value.triggerSpread === null) {
          setExecutionMessage('限价开仓必须填写开仓价差', 'is-warn');
          return;
        }
        const payload = {
          direction: action.direction as CrossSpreadDirection,
          quantityOz: String(inputs.value.qtyOz),
          takeProfitSpread: optionalNumericText(inputs.value.takeProfitSpread),
          stopLossSpread: optionalNumericText(inputs.value.stopLossSpread),
          executionMode: inputs.value.executionMode,
          limitSpread:
            inputs.value.executionMode === 'limit'
              ? numericText(inputs.value.triggerSpread)
              : undefined,
          limitStrategy: inputs.value.openLimitStrategy,
          maxAdverseSpread: numericText(inputs.value.acceptableSpread ?? 0),
          takeProfitMaxAdverseSpread: numericText(inputs.value.acceptableSpread ?? 0),
          stopLossMaxAdverseSpread: numericText(inputs.value.acceptableSpread ?? 0),
          takeProfitExecutionMode: inputs.value.takeProfitExecution,
          stopLossExecutionMode: inputs.value.stopLossExecution,
          takeProfitLimitStrategy: inputs.value.takeProfitLimitStrategy,
          stopLossLimitStrategy: inputs.value.stopLossLimitStrategy,
        };
        const draft: PersistedExecutionDraft = {
          kind: 'OPEN',
          idempotencyKey: crypto.randomUUID(),
          payload,
        };
        persistExecutionDraft(draft);
        const result = await openCrossSpreadMarket({
          idempotencyKey: draft.idempotencyKey,
          ...payload,
        });
        if (result.exitPlan) {
          options.upsertExitPlan?.(result.exitPlan);
        }
        limitEvidence.value = result.limitExecution ?? null;
        if (result.pendingTrigger?.status === 'pending') {
          setExecutionMessage('限价价差指令已挂起，达到目标价差后才会执行', 'is-warn');
        } else if (result.executionBatch?.status === 'hedged') {
          setExecutionMessage('开仓成功，双边已对冲', 'is-success');
        } else {
          setExecutionMessage(
            `开仓提交完成，批次状态：${result.executionBatch?.status ?? '未知'}`,
            'is-warn',
          );
        }
        if (
          isTerminalBatchStatus(result.executionBatch?.status) ||
          canHandOffAbnormalBatch(result.executionBatch)
        ) {
          clearExecutionDraft();
        }
      } else if (action.kind === 'CLOSE') {
        if (inputs.value.closeExecutionMode === 'limit' && inputs.value.closeLimitSpread === null) {
          setExecutionMessage('限价平仓必须填写平仓限制价差', 'is-warn');
          return;
        }
        const draft: PersistedExecutionDraft = {
          kind: 'CLOSE',
          idempotencyKey:
            inputs.value.closeOrders.find((order) => order.id === action.planId)
              ?.recoveryIdempotencyKey || crypto.randomUUID(),
          planId: action.planId,
          payload: {
            quantityOz: String(
              action.quantityOz ??
                inputs.value.closeOrders.find((order) => order.id === action.planId)?.qtyOz ??
                0,
            ),
            executionMode: inputs.value.closeExecutionMode,
            limitSpread:
              inputs.value.closeExecutionMode === 'limit'
                ? numericText(inputs.value.closeLimitSpread)
                : undefined,
            limitStrategy: inputs.value.closeLimitStrategy,
            maxAdverseSpread: numericText(inputs.value.acceptableSpread ?? 0),
          },
        };
        persistExecutionDraft(draft);
        const result = await closeCrossSpreadMarket(action.planId, {
          idempotencyKey: draft.idempotencyKey,
          ...draft.payload,
        });
        options.upsertExitPlan?.(result.exitPlan);
        setExecutionMessage(
          result.executionBatch.status === 'manual_intervention'
            ? `平仓未完成：${result.executionBatch.failureReason || '请在异常订单区处理剩余仓位'}`
            : `平仓提交完成，批次状态：${result.executionBatch.status}`,
          result.executionBatch.status === 'manual_intervention' ? 'is-error' : 'is-success',
        );
        if (
          isTerminalBatchStatus(result.executionBatch.status) ||
          canHandOffAbnormalBatch(result.executionBatch)
        ) {
          clearExecutionDraft();
        }
      } else {
        if (inputs.value.closeExecutionMode === 'limit' && inputs.value.closeLimitSpread === null) {
          setExecutionMessage('限价平仓必须填写平仓限制价差', 'is-warn');
          return;
        }
        const closablePlans = inputs.value.exitPlans.filter(
          (plan) =>
            (plan.status === 'active' || plan.status === 'manual_intervention') &&
            inputs.value.closeOrders.some(
              (order) => order.id === plan.planId && order.qtyOz > 0 && !order.isAbnormal,
            ),
        );
        if (!closablePlans.length) {
          setExecutionMessage('没有可平仓的退出计划', 'is-warn');
          return;
        }
        const draft = createCloseAllExecutionDraft(
          closablePlans.map((plan) => plan.planId),
          {
            executionMode: inputs.value.closeExecutionMode,
            limitSpread:
              inputs.value.closeExecutionMode === 'limit'
                ? numericText(inputs.value.closeLimitSpread)
                : undefined,
            limitStrategy: inputs.value.closeLimitStrategy,
            maxAdverseSpread: numericText(inputs.value.acceptableSpread ?? 0),
          },
        );
        draft.plans = draft.plans.map((plan) => ({
          ...plan,
          quantityOz: String(
            inputs.value.closeOrders.find((order) => order.id === plan.planId)!.qtyOz,
          ),
        }));
        persistExecutionDraft(draft);
        let allTerminal = true;
        for (const planDraft of draft.plans) {
          planDraft.submitted = true;
          persistExecutionDraft(draft);
          const result = await closeCrossSpreadMarket(planDraft.planId, {
            idempotencyKey: planDraft.idempotencyKey,
            ...draft.payload,
            quantityOz: planDraft.quantityOz ?? draft.payload.quantityOz,
          });
          options.upsertExitPlan?.(result.exitPlan);
          allTerminal = allTerminal && isTerminalBatchStatus(result.executionBatch.status);
          if (!isTerminalBatchStatus(result.executionBatch.status)) break;
        }
        if (allTerminal) {
          clearExecutionDraft();
        }
        setExecutionMessage(`已提交 ${closablePlans.length} 个退出计划平仓`, 'is-success');
      }
      void refreshExecutionViews();
    } catch (error: unknown) {
      await releaseRejectedDraft(error);
      setExecutionMessage(requestErrorMessage(error, '价差指令执行失败'), 'is-error');
    } finally {
      submitLoading.value = false;
      confirmVisible.value = false;
      pendingAction.value = null;
    }
  }

  async function resumePendingExecution() {
    if (userStore.authentication?.user.role !== 'ceo' || pendingDraftRecoveryRunning) return;
    if (submitLoading.value || confirmVisible.value) return;
    const draft = readExecutionDraft();
    if (!draft) {
      pendingDraftAbsent.value = false;
      return;
    }
    pendingDraftRecoveryRunning = true;
    pendingDraftAbsent.value = false;
    submitLoading.value = true;
    setExecutionMessage('检测到未确认回执的价差指令，正在恢复状态…', 'is-warn');
    try {
      const keys = draftKeys(draft);
      const statuses: string[] = [];
      let allTerminal = true;
      let allReceived = true;
      let allAbsent = keys.length > 0;
      for (const key of keys) {
        const instruction = await getCrossSpreadInstruction(key);
        if (instruction === null) {
          // Keep the draft until a second authoritative read confirms absence.
          // This read-only recovery never resubmits an order.
          allReceived = false;
          // Absence during recovery can race an in-flight original request.
          // Keep its identity and never turn this read into a new submission.
          allTerminal = false;
          statuses.push('原指令尚未查到，请稍后刷新核对');
          continue;
        }
        allAbsent = false;
        if (instruction.executionBatchId === null) {
          allReceived = allReceived && ['failed', 'rejected'].includes(instruction.status);
          allTerminal = allTerminal && instruction.status === 'failed';
          statuses.push(instruction.status);
          continue;
        }
        const batch = await getExecutionBatch(instruction.executionBatchId);
        if (
          batch.batchId !== instruction.executionBatchId ||
          batch.strategyInstanceId !== 'strategy_cross_venue_spread_instance_default'
        )
          throw new Error('原指令与执行批次身份不一致，请核对');
        allTerminal = allTerminal && isTerminalBatchStatus(batch.status);
        allReceived =
          allReceived && (isTerminalBatchStatus(batch.status) || canHandOffAbnormalBatch(batch));
        statuses.push(batch.status);
      }
      if (allReceived) clearExecutionDraft();
      if (allAbsent && sameDraft(readExecutionDraft(), draft)) {
        await new Promise((resolve) => setTimeout(resolve, 1200));
        if (sameDraft(readExecutionDraft(), draft)) {
          const rechecked = await Promise.all(keys.map(getCrossSpreadInstruction));
          if (rechecked.every((item) => item === null)) {
            pendingDraftAbsent.value = true;
            setExecutionMessage(
              '服务器连续两次未找到这条指令。可核验后解除本地锁定；此操作不会下单。',
              'is-warn',
            );
          }
        }
      } else {
        setExecutionMessage(
          `已恢复指令状态：${statuses.join('；') || '没有已提交指令'}`,
          allTerminal ? 'is-success' : 'is-warn',
        );
      }
      await refreshExecutionViews();
    } catch (error: unknown) {
      setExecutionMessage(
        requestErrorMessage(error, '未完成指令恢复失败，请刷新后核对状态'),
        'is-error',
      );
    } finally {
      submitLoading.value = false;
      pendingDraftRecoveryRunning = false;
    }
  }

  async function clearUnreceivedPendingExecution() {
    if (!pendingDraftAbsent.value || submitLoading.value || confirmVisible.value) return;
    const draft = readExecutionDraft();
    if (!draft) {
      pendingDraftAbsent.value = false;
      return;
    }
    submitLoading.value = true;
    try {
      const instructions = await Promise.all(draftKeys(draft).map(getCrossSpreadInstruction));
      if (!sameDraft(readExecutionDraft(), draft) || instructions.some((item) => item !== null)) {
        pendingDraftAbsent.value = false;
        setExecutionMessage('原指令状态已变化，已保留本地锁定并重新核对。', 'is-warn');
        submitLoading.value = false;
        await resumePendingExecution();
        return;
      }
      clearExecutionDraft();
      pendingDraftAbsent.value = false;
      setExecutionMessage(
        '已确认服务器没有收到原指令并解除本地锁定；未提交任何交易。请刷新持仓后再发起平仓。',
        'is-success',
      );
      await refreshExecutionViews();
    } catch (error) {
      setExecutionMessage(requestErrorMessage(error, '核对失败，本地锁定仍保留。'), 'is-error');
    } finally {
      submitLoading.value = false;
    }
  }

  watch(
    () => userStore.authentication?.user.role,
    (role) => {
      if (role === 'ceo') void resumePendingExecution();
    },
    { immediate: true },
  );

  return {
    cancelConfirmation,
    confirmGuardMessage,
    confirmOrder,
    confirmSummary,
    confirmVisible,
    clearUnreceivedPendingExecution,
    executionLogs,
    executionMessage,
    executionMessageTone,
    limitEvidence,
    openConfirm,
    openPartialClose,
    pendingDraftAbsent,
    prepareOpenDraft,
    resumePendingExecution,
    setExecutionMessage,
    submitLoading,
  };
}
