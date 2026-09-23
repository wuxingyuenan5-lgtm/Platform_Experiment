import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  getCrossSpreadHistory,
  getCrossSpreadSnapshot,
  getInstruments,
} from '@/api/platform/trading';
import { getCrossSpreadTradingRules } from '@/api/platform/crossSpreadLifecycle';
import type {
  CrossSpreadSnapshotResult,
  InstrumentResult,
  MarketQuoteResult,
} from '@/api/platform/trading.types';
import type {
  CrossSpreadExecutionMode,
  CrossSpreadExitPlanThresholdUpdateInput,
  CrossSpreadLimitStrategy,
  CrossSpreadTradingRulesResult,
} from '@/api/platform/crossSpreadLifecycle';

import { CROSS_SPREAD_RANGES } from './crossSpreadFixtures';
import { useCrossSpreadExecution } from './useCrossSpreadExecution';
import { useCrossSpreadExitPlans } from './useCrossSpreadExitPlans';
import {
  formatEditableNumber,
  formatNullableRate,
  formatNullableSigned,
  formatNumber,
  parseEditableNumber,
  parseOptionalNumber,
} from './useCrossSpreadFormatting';
import { useCrossSpreadObservability } from './useCrossSpreadObservability';
import { useCrossSpreadPositions } from './useCrossSpreadPositions';

const BYBIT_INSTRUMENT_ID = 'instrument_xau_usdt_perp';
const MT5_INSTRUMENT_ID = 'instrument_xau_usd';

function requestErrorMessage(error: unknown, fallback: string) {
  if (typeof error !== 'object' || error === null) return fallback;
  const candidate = error as {
    message?: unknown;
    response?: { data?: { detail?: unknown } };
  };
  const detail = candidate.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  return typeof candidate.message === 'string' && candidate.message ? candidate.message : fallback;
}

export function useCrossVenueExecutionWorkspace() {
  const ranges = CROSS_SPREAD_RANGES;
  const selectedPair = ref('XAUTUSDT-XAUUSD');
  const selectedRange = ref('15m');
  const executionStage = ref<'open' | 'close' | 'funding'>('open');
  const executionMode = ref<CrossSpreadExecutionMode>('market');
  const closeExecutionMode = ref<CrossSpreadExecutionMode>('market');
  // Start at the live contract minimum, never at a demo-sized default.
  const qtyOz = ref(1);
  const qtyInput = ref('1');
  const instruments = ref<InstrumentResult[]>([]);
  const triggerSpread = ref<number | null>(null);
  const acceptableSpread = ref<number | null>(0);
  const takeProfitSpread = ref<number | null>(null);
  const stopLossSpread = ref<number | null>(null);
  const takeProfitExecution = ref<CrossSpreadExecutionMode>('limit');
  const stopLossExecution = ref<CrossSpreadExecutionMode>('market');
  const openLimitStrategy = ref<CrossSpreadLimitStrategy>('post_only_chase');
  const takeProfitLimitStrategy = ref<CrossSpreadLimitStrategy>('post_only_chase');
  const stopLossLimitStrategy = ref<CrossSpreadLimitStrategy>('post_only_chase');
  const closeLimitStrategy = ref<CrossSpreadLimitStrategy>('post_only_chase');
  const closeLimitSpread = ref<number | null>(null);
  const triggerSpreadInput = ref(formatEditableNumber(triggerSpread.value));
  const acceptableSpreadInput = ref(formatEditableNumber(acceptableSpread.value));
  const takeProfitSpreadInput = ref(formatEditableNumber(takeProfitSpread.value));
  const stopLossSpreadInput = ref(formatEditableNumber(stopLossSpread.value));
  const closeLimitSpreadInput = ref(formatEditableNumber(closeLimitSpread.value));
  const {
    exitPlans,
    refreshExitPlans: loadExitPlans,
    updateExitPlanThresholds: persistExitPlanThresholds,
    upsertExitPlan,
  } = useCrossSpreadExitPlans();
  const tradingRules = ref<CrossSpreadTradingRulesResult | null>(null);
  const tradingRulesError = ref('');
  const openDirection = ref<'long' | 'short'>('long');
  const snapshot = ref<CrossSpreadSnapshotResult | null>(null);
  const snapshotLoading = ref(false);
  const snapshotError = ref('');
  const { observability, observabilityError, refreshObservability } = useCrossSpreadObservability();
  const spreadHistory = ref<{ label: string; value: number }[]>([]);
  let snapshotTimer: number | undefined;
  let tradingRulePolls = 0;

  const bybitQuote = computed<MarketQuoteResult | null>(() => snapshot.value?.bybit.quote || null);
  const mt5Quote = computed<MarketQuoteResult | null>(() => snapshot.value?.mt5.quote || null);
  const tradingRuleRows = computed(() => {
    const rules = tradingRules.value;
    if (!rules) {
      return [
        { label: '手续费', value: '—' },
        { label: '交易时间', value: tradingRulesError.value || '读取中' },
        { label: '个人最高杠杆', value: '—' },
        { label: '每日最大回撤', value: '—' },
        { label: '其他限制', value: '读取中' },
      ];
    }
    const mt5Schedule = rules.mt5.tradingHours || '时段未配置';
    const mt5MarketStatus = rules.mt5.marketStatus;
    const guardMinutes = rules.mt5.automaticExitGuardMinutes;
    const beijingBreak =
      rules.mt5.tradingTimezone?.toLowerCase() === 'bybit/mt5' &&
      mt5Schedule.includes('00:00-23:00')
        ? '；北京时间休市：04:00-05:00（UTC+03:00，夏令时）或05:00-06:00（UTC+02:00，冬令时）'
        : '';
    const automaticExitRule =
      guardMinutes === null || guardMinutes === undefined
        ? ''
        : `；开收盘前后${guardMinutes}分钟不自动交易（仅暂停后台自动止盈止损，手动开平仓可用）`;
    const mt5StatusText =
      mt5MarketStatus === 'closed'
        ? '休市'
        : mt5MarketStatus === 'buffer'
        ? `开收盘前后${guardMinutes ?? '配置'}分钟：不自动执行`
        : mt5MarketStatus === 'unknown'
        ? '时段未知'
        : !rules.mt5.automaticExitAllowed
        ? '不自动执行'
        : '';
    const mt5TradingTime = `XAUTUSDT：24H；XAUUSD：${mt5Schedule}${beijingBreak}${automaticExitRule}${
      mt5StatusText ? `；状态：${mt5StatusText}` : ''
    }`;
    const bybitMin = parseOptionalNumber(rules.bybit.minQuantity);
    const bybitStep = parseOptionalNumber(rules.bybit.quantityStep);
    const bybitMax = parseOptionalNumber(rules.bybit.maxMarketQuantity);
    const mt5Min = parseOptionalNumber(rules.mt5.minQuantity);
    const mt5Step = parseOptionalNumber(rules.mt5.quantityStep);
    const mt5Max = parseOptionalNumber(rules.mt5.maxMarketQuantity);
    const mt5ContractSize = parseOptionalNumber(rules.mt5.contractSize);
    const minimum =
      bybitMin !== null && mt5Min !== null && mt5ContractSize !== null
        ? Math.max(bybitMin, mt5Min * mt5ContractSize)
        : null;
    const step =
      bybitStep !== null && mt5Step !== null && mt5ContractSize !== null
        ? Math.max(bybitStep, mt5Step * mt5ContractSize)
        : null;
    const maximum =
      bybitMax !== null && mt5Max !== null && mt5ContractSize !== null
        ? Math.min(bybitMax, mt5Max * mt5ContractSize)
        : null;
    const quantityLimits = [
      minimum === null ? null : `最小下单 ${formatNumber(minimum, 2)} 盎司`,
      step === null ? null : `数量步长 ${formatNumber(step, 2)} 盎司`,
      maximum === null ? null : `市价上限 ${formatNumber(maximum, 2)} 盎司`,
    ].filter(Boolean);
    return [
      { label: '手续费', value: '—' },
      { label: '交易时间', value: mt5TradingTime },
      { label: '个人最高杠杆', value: '—' },
      { label: '每日最大回撤', value: '—' },
      { label: '其他限制', value: quantityLimits.join('；') || '—' },
    ];
  });
  const bybitInstrument = computed(() =>
    instruments.value.find((instrument) => instrument.instrumentId === BYBIT_INSTRUMENT_ID),
  );
  const mt5Instrument = computed(() =>
    instruments.value.find((instrument) => instrument.instrumentId === MT5_INSTRUMENT_ID),
  );
  const quantityRules = computed(() => {
    const bybitContract = bybitInstrument.value?.contract;
    const mt5Contract = mt5Instrument.value?.contract;
    if (!bybitContract || !mt5Contract) return null;
    const bybitMinOz = parseOptionalNumber(bybitContract.minOrderQuantity);
    const bybitStepOz = parseOptionalNumber(bybitContract.quantityStep);
    const mt5MinLot = parseOptionalNumber(mt5Contract.minOrderQuantity);
    const mt5StepLot = parseOptionalNumber(mt5Contract.quantityStep);
    const mt5Multiplier = parseOptionalNumber(mt5Contract.contractMultiplier);
    if (
      bybitMinOz === null ||
      bybitStepOz === null ||
      mt5MinLot === null ||
      mt5StepLot === null ||
      mt5Multiplier === null ||
      mt5Multiplier <= 0
    ) {
      return null;
    }
    return {
      minOz: Math.max(bybitMinOz, mt5MinLot * mt5Multiplier),
      stepOz: Math.max(bybitStepOz, mt5StepLot * mt5Multiplier),
      mt5Multiplier,
    };
  });
  const longSpread = computed(() => parseOptionalNumber(snapshot.value?.longSpread));
  const shortSpread = computed(() => parseOptionalNumber(snapshot.value?.shortSpread));
  const snapshotStatusText = computed(() => {
    if (snapshotLoading.value && !snapshot.value) return '加载中';
    if (snapshotError.value) return '接口异常';
    if (!snapshot.value) return '等待行情';
    if (snapshot.value.status === 'available') return '双边真实行情';
    if (snapshot.value.status === 'partial') return '单边行情可用';
    return '行情不可用';
  });

  watch(
    [triggerSpread, acceptableSpread, takeProfitSpread, stopLossSpread, closeLimitSpread],
    syncSpreadInputs,
  );

  const bybitQty = computed(() => qtyOz.value);
  const mt5Lot = computed(() => {
    const rules = quantityRules.value;
    return rules ? qtyOz.value / rules.mt5Multiplier : null;
  });
  const fundingInventoryText = computed(() => {
    const metrics = snapshot.value?.metrics;
    return [
      formatNullableRate(metrics?.fundingRate),
      formatNullableSigned(metrics?.buyerInventoryFee),
      formatNullableSigned(metrics?.sellerInventoryFee),
    ].join(' | ');
  });
  const usdtUsdText = computed(() => {
    const parsed = parseOptionalNumber(snapshot.value?.metrics?.usdtUsd);
    return parsed === null ? '--' : formatNumber(parsed, 4);
  });
  const bybitLatencyMs = computed(() => snapshot.value?.bybit.fetchLatencyMs ?? null);
  const mt5LatencyMs = computed(() => snapshot.value?.mt5.fetchLatencyMs ?? null);
  const { closeOrders, overviewRows, overviewPnl } = useCrossSpreadPositions({
    exitPlans,
    snapshot,
    observability,
    quantityRules,
    longSpread,
    shortSpread,
    snapshotStatusText,
  });
  const {
    cancelConfirmation,
    confirmGuardMessage,
    confirmOrder,
    confirmSummary,
    confirmVisible,
    executionLogs,
    executionMessage,
    executionMessageTone,
    limitEvidence,
    openConfirm,
    openPartialClose,
    prepareOpenDraft,
    setExecutionMessage,
    submitLoading,
  } = useCrossSpreadExecution({
    qtyOz,
    qtyInput,
    bybitQty,
    mt5Lot,
    quantityRules,
    openDirection,
    executionMode,
    closeExecutionMode,
    takeProfitExecution,
    stopLossExecution,
    openLimitStrategy,
    takeProfitLimitStrategy,
    stopLossLimitStrategy,
    closeLimitStrategy,
    triggerSpread,
    acceptableSpread,
    takeProfitSpread,
    stopLossSpread,
    closeLimitSpread,
    longSpread,
    shortSpread,
    exitPlans,
    closeOrders,
    upsertExitPlan,
    refreshExitPlans,
    refreshSnapshot,
    refreshObservability,
  });
  const qtyError = computed(() => {
    if (qtyOz.value <= 0) return '数量必须大于 0';
    const rules = quantityRules.value;
    if (!rules) return '合约规格加载中';
    if (qtyOz.value < rules.minOz) {
      return `当前合约最小下单数量为 ${formatNumber(rules.minOz, 2)} 盎司`;
    }
    const steps = (qtyOz.value - rules.minOz) / rules.stepOz;
    if (Math.abs(steps - Math.round(steps)) > 1e-8) {
      return `当前合约下单步长为 ${formatNumber(rules.stepOz, 2)} 盎司`;
    }
    return '';
  });

  async function refreshSnapshot() {
    if (snapshotLoading.value) return;
    snapshotLoading.value = true;
    try {
      const nextSnapshot = await getCrossSpreadSnapshot();
      snapshot.value = nextSnapshot;
      snapshotError.value = '';
      const nextSpread = parseOptionalNumber(nextSnapshot.longSpread);
      if (nextSpread !== null) {
        spreadHistory.value = [
          ...spreadHistory.value.slice(-59),
          {
            label: new Date(nextSnapshot.asOf).toLocaleTimeString('zh-CN', { hour12: false }),
            value: nextSpread,
          },
        ];
      }
    } catch (error: unknown) {
      snapshotError.value = requestErrorMessage(error, '跨所行情接口异常');
      if (snapshot.value) snapshot.value = { ...snapshot.value, positionOverview: null };
    } finally {
      snapshotLoading.value = false;
    }
  }

  async function refreshTradingRules() {
    try {
      tradingRules.value = await getCrossSpreadTradingRules();
      tradingRulesError.value = '';
    } catch (error: unknown) {
      tradingRules.value = null;
      tradingRulesError.value = requestErrorMessage(error, '真实交易规则暂不可用；当前仅行情监控');
    }
  }

  async function refreshHistory() {
    try {
      const points = await getCrossSpreadHistory(200);
      spreadHistory.value = points
        .map((point) => {
          const value = parseOptionalNumber(point.longSpread);
          if (value === null) return null;
          return {
            label: new Date(point.asOf).toLocaleTimeString('zh-CN', { hour12: false }),
            value,
          };
        })
        .filter((item): item is { label: string; value: number } => item !== null);
    } catch {
      spreadHistory.value = [];
    }
  }

  function isPageVisible() {
    return typeof document === 'undefined' || document.visibilityState === 'visible';
  }

  function stopSnapshotPolling() {
    if (snapshotTimer) {
      window.clearInterval(snapshotTimer);
      snapshotTimer = undefined;
    }
  }

  function startSnapshotPolling() {
    stopSnapshotPolling();
    if (!isPageVisible()) return;
    snapshotTimer = window.setInterval(() => {
      void refreshSnapshot();
      void refreshObservability();
      void refreshExitPlans();
      tradingRulePolls += 1;
      if (tradingRulePolls >= 10) {
        tradingRulePolls = 0;
        void refreshTradingRules();
      }
    }, 3_000);
  }

  function handleVisibilityChange() {
    if (!isPageVisible()) {
      stopSnapshotPolling();
      return;
    }
    void refreshSnapshot();
    void refreshTradingRules();
    void refreshObservability();
    void refreshExitPlans();
    startSnapshotPolling();
  }

  async function refreshInstruments() {
    try {
      instruments.value = await getInstruments();
    } catch {
      instruments.value = [];
    }
  }

  function syncSpreadInputs() {
    triggerSpreadInput.value = formatEditableNumber(triggerSpread.value);
    acceptableSpreadInput.value = formatEditableNumber(acceptableSpread.value);
    takeProfitSpreadInput.value = formatEditableNumber(takeProfitSpread.value);
    stopLossSpreadInput.value = formatEditableNumber(stopLossSpread.value);
    closeLimitSpreadInput.value = formatEditableNumber(closeLimitSpread.value);
  }

  function commitSpreadInput(
    field: 'trigger' | 'acceptable' | 'takeProfit' | 'stopLoss' | 'closeLimit',
  ) {
    const inputMap = {
      trigger: triggerSpreadInput,
      acceptable: acceptableSpreadInput,
      takeProfit: takeProfitSpreadInput,
      stopLoss: stopLossSpreadInput,
      closeLimit: closeLimitSpreadInput,
    };
    const valueMap = {
      trigger: triggerSpread,
      acceptable: acceptableSpread,
      takeProfit: takeProfitSpread,
      stopLoss: stopLossSpread,
      closeLimit: closeLimitSpread,
    };
    const parsed = parseEditableNumber(inputMap[field].value);
    if (parsed === null || (field === 'acceptable' && parsed < 0)) {
      inputMap[field].value = formatEditableNumber(valueMap[field].value);
      return;
    }
    valueMap[field].value = parsed;
    inputMap[field].value = formatEditableNumber(parsed);
  }

  function commitQtyInput() {
    const parsed = parseEditableNumber(qtyInput.value);
    if (parsed === null) {
      qtyInput.value = formatEditableNumber(qtyOz.value);
      return;
    }
    qtyOz.value = Math.max(0, parsed);
    qtyInput.value = formatEditableNumber(qtyOz.value);
  }

  function nudgeQty(delta: number) {
    const step = quantityRules.value?.stepOz || Math.abs(delta);
    const direction = delta >= 0 ? 1 : -1;
    qtyOz.value = Math.max(0, qtyOz.value + direction * step);
    qtyInput.value = formatEditableNumber(qtyOz.value);
  }

  async function refreshExitPlans(): Promise<string> {
    const errorMessage = await loadExitPlans();
    if (errorMessage) setExecutionMessage(errorMessage, 'is-error');
    return errorMessage;
  }

  async function updateExitPlanThresholds(
    planId: string,
    input: CrossSpreadExitPlanThresholdUpdateInput,
  ): Promise<void> {
    const errorMessage = await persistExitPlanThresholds(planId, input);
    if (errorMessage) {
      setExecutionMessage(errorMessage, 'is-error');
      throw new Error(errorMessage);
    }
    setExecutionMessage('止盈止损已更新；本次操作未触发平仓。', 'is-success');
  }

  onMounted(async () => {
    await Promise.all([
      refreshInstruments(),
      refreshExitPlans().then((errorMessage) => {
        if (errorMessage) setExecutionMessage(errorMessage, 'is-error');
      }),
      refreshHistory(),
      refreshObservability(),
      refreshSnapshot(),
      refreshTradingRules(),
    ]);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    startSnapshotPolling();
  });

  onUnmounted(() => {
    stopSnapshotPolling();
    document.removeEventListener('visibilitychange', handleVisibilityChange);
  });

  return {
    acceptableSpreadInput,
    bybitQty,
    bybitLatencyMs,
    bybitQuote,
    closeExecutionMode,
    closeLimitSpreadInput,
    closeLimitStrategy,
    closeOrders,
    commitQtyInput,
    commitSpreadInput,
    cancelConfirmation,
    confirmGuardMessage,
    confirmOrder,
    confirmSummary,
    confirmVisible,
    executionLogs,
    executionMessage,
    executionMessageTone,
    executionMode,
    executionStage,
    fundingInventoryText,
    limitEvidence,
    longSpread,
    mt5Lot,
    mt5LatencyMs,
    mt5Quote,
    nudgeQty,
    observability,
    observabilityError,
    openLimitStrategy,
    openConfirm,
    openPartialClose,
    overviewRows,
    refreshAbnormalPositions: async () => {
      await Promise.allSettled([refreshExitPlans(), refreshSnapshot(), refreshObservability()]);
    },
    overviewPnl,
    prepareOpenDraft,
    qtyError,
    qtyInput,
    ranges,
    selectedPair,
    selectedRange,
    shortSpread,
    snapshot,
    snapshotError,
    spreadHistory,
    stopLossExecution,
    stopLossLimitStrategy,
    stopLossSpreadInput,
    submitLoading,
    takeProfitExecution,
    takeProfitLimitStrategy,
    takeProfitSpreadInput,
    tradingRuleRows,
    triggerSpreadInput,
    usdtUsdText,
    updateExitPlanThresholds,
  };
}
