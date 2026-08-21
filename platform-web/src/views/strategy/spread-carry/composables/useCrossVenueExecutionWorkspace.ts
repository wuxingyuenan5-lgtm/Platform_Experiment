import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  getCrossSpreadHistory,
  getCrossSpreadSnapshot,
  getInstruments,
} from '@/api/platform/trading';
import type {
  CrossSpreadSnapshotResult,
  InstrumentResult,
  MarketQuoteResult,
} from '@/api/platform/trading.types';
import type {
  CrossSpreadExecutionMode,
  CrossSpreadLimitStrategy,
} from '@/api/platform/crossSpreadLifecycle';

import { CROSS_SPREAD_RANGES, CROSS_SPREAD_TRADING_RULE_ROWS } from './crossSpreadFixtures';
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
  const executionStage = ref<'open' | 'close'>('open');
  const executionMode = ref<CrossSpreadExecutionMode>('market');
  const closeExecutionMode = ref<CrossSpreadExecutionMode>('market');
  // Start at the live contract minimum, never at a demo-sized default.
  const qtyOz = ref(1);
  const qtyInput = ref('1');
  const instruments = ref<InstrumentResult[]>([]);
  const triggerSpread = ref<number | null>(null);
  const acceptableSpread = ref<number | null>(null);
  const takeProfitSpread = ref<number | null>(null);
  const stopLossSpread = ref<number | null>(null);
  const takeProfitExecution = ref<CrossSpreadExecutionMode>('limit');
  const stopLossExecution = ref<CrossSpreadExecutionMode>('market');
  const openLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const takeProfitLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const stopLossLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const closeLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const closeLimitSpread = ref<number | null>(null);
  const triggerSpreadInput = ref(formatEditableNumber(triggerSpread.value));
  const acceptableSpreadInput = ref(formatEditableNumber(acceptableSpread.value));
  const takeProfitSpreadInput = ref(formatEditableNumber(takeProfitSpread.value));
  const stopLossSpreadInput = ref(formatEditableNumber(stopLossSpread.value));
  const closeLimitSpreadInput = ref(formatEditableNumber(closeLimitSpread.value));
  const { exitPlans, refreshExitPlans: loadExitPlans, upsertExitPlan } = useCrossSpreadExitPlans();
  const tradingRuleRows = CROSS_SPREAD_TRADING_RULE_ROWS;
  const openDirection = ref<'long' | 'short'>('long');
  const snapshot = ref<CrossSpreadSnapshotResult | null>(null);
  const snapshotLoading = ref(false);
  const snapshotError = ref('');
  const { observability, observabilityError, refreshObservability } = useCrossSpreadObservability();
  const spreadHistory = ref<{ label: string; value: number }[]>([]);
  let snapshotTimer: number | undefined;

  const bybitQuote = computed<MarketQuoteResult | null>(() => snapshot.value?.bybit.quote || null);
  const mt5Quote = computed<MarketQuoteResult | null>(() => snapshot.value?.mt5.quote || null);
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
  const bybitLatencyMs = computed(() => {
    const asOf =
      observability.value?.bybit?.accountRisk?.asOf ||
      observability.value?.bybit?.positions?.[0]?.asOf ||
      snapshot.value?.asOf;
    return latencyMs(asOf);
  });
  const mt5LatencyMs = computed(() => {
    const asOf =
      observability.value?.mt5?.accountRisk?.asOf ||
      observability.value?.mt5?.positions?.[0]?.asOf ||
      snapshot.value?.asOf;
    return latencyMs(asOf);
  });
  const { closeOrders, overviewRows } = useCrossSpreadPositions({
    exitPlans,
    snapshot,
    observability,
    quantityRules,
    longSpread,
    shortSpread,
    snapshotStatusText,
  });
  const {
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
    } finally {
      snapshotLoading.value = false;
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
    if (parsed === null) {
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

  onMounted(async () => {
    await Promise.all([
      refreshInstruments(),
      refreshExitPlans().then((errorMessage) => {
        if (errorMessage) setExecutionMessage(errorMessage, 'is-error');
      }),
      refreshHistory(),
      refreshObservability(),
      refreshSnapshot(),
    ]);
    snapshotTimer = window.setInterval(() => {
      void refreshSnapshot();
      void refreshObservability();
    }, 15_000);
  });

  onUnmounted(() => {
    if (snapshotTimer) window.clearInterval(snapshotTimer);
  });

  function latencyMs(value: string | null | undefined) {
    if (!value) return null;
    const parsed = new Date(value).getTime();
    if (!Number.isFinite(parsed)) return null;
    return Math.max(0, Date.now() - parsed);
  }

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
    observabilityError,
    openLimitStrategy,
    openConfirm,
    overviewRows,
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
  };
}
