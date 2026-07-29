<template>
  <section class="cross-replica">
    <header class="cross-head">
      <div class="cross-head__controls">
        <label class="select-chip">
          <span>标的</span>
          <select v-model="selectedPair">
            <option :value="`${leftLegSymbol}-${rightLegSymbol}`">BYBIT: {{ leftLegSymbol }} vs MT5: {{ rightLegSymbol }}</option>
          </select>
        </label>
      </div>
    </header>

    <div class="cross-top-grid">
      <CrossVenueMarketQuotes
        :left-leg-symbol="leftLegSymbol"
        :right-leg-symbol="rightLegSymbol"
        :bybit-quote="bybitQuote"
        :mt5-quote="mt5Quote"
        :bybit-status="snapshot?.bybit.status"
        :mt5-status="snapshot?.mt5.status"
      />

      <CrossVenueSpreadSummary
        :long-spread="longSpread"
        :short-spread="shortSpread"
        :funding-inventory-text="fundingInventoryText"
        :usdt-usd-text="usdtUsdText"
      />

      <CrossVenueSpreadChart
        v-model:selected-range="selectedRange"
        :ranges="ranges"
        :spread-history="spreadHistory"
      />
    </div>

    <div class="cross-mid-grid">
      <CrossVenueTradingRules
        :trading-rule-rows="tradingRuleRows"
        :execution-logs="executionLogs"
      />
      <SpreadExecutionCommand
        v-model:execution-stage="executionStage"
        v-model:execution-mode="executionMode"
        v-model:close-execution-mode="closeExecutionMode"
        v-model:qty-input="qtyInput"
        v-model:trigger-spread-input="triggerSpreadInput"
        v-model:acceptable-spread-input="acceptableSpreadInput"
        v-model:take-profit-execution="takeProfitExecution"
        v-model:take-profit-limit-strategy="takeProfitLimitStrategy"
        v-model:take-profit-spread-input="takeProfitSpreadInput"
        v-model:stop-loss-spread-input="stopLossSpreadInput"
        v-model:stop-loss-execution="stopLossExecution"
        v-model:stop-loss-limit-strategy="stopLossLimitStrategy"
        v-model:close-limit-spread-input="closeLimitSpreadInput"
        v-model:close-limit-strategy="closeLimitStrategy"
        :qty-error="qtyError"
        :bybit-qty="bybitQty"
        :mt5-lot="mt5Lot"
        :leverage="leverage"
        :long-spread="longSpread"
        :short-spread="shortSpread"
        :submit-loading="submitLoading"
        :execution-message="executionMessage"
        :execution-message-tone="executionMessageTone"
        :limit-evidence="limitEvidence"
        :close-orders="closeOrders"
        @commit-qty-input="commitQtyInput"
        @nudge-qty="nudgeQty"
        @handle-leverage-input="handleLeverageInput"
        @commit-spread-input="commitSpreadInput"
        @prepare-open-draft="prepareOpenDraft"
        @open-confirm="openConfirm"
      />

      <CrossVenueSpreadAnalysis />
    </div>

    <SpreadPositionOverview
      :overview-rows="overviewRows"
      :empty-text="observabilityError || snapshotError || '暂无真实持仓'"
      :long-spread="longSpread"
    />

    <SpreadExecutionConfirmModal
      :visible="confirmVisible"
      :submit-loading="submitLoading"
      :left-leg-symbol="leftLegSymbol"
      :right-leg-symbol="rightLegSymbol"
      :summary="confirmSummary"
      :guard-message="confirmGuardMessage"
      @close="confirmVisible = false"
      @confirm="confirmOrder"
    />
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
  import CrossVenueMarketQuotes from './CrossVenueMarketQuotes.vue';
  import CrossVenueSpreadAnalysis from './CrossVenueSpreadAnalysis.vue';
  import CrossVenueSpreadChart from './CrossVenueSpreadChart.vue';
  import CrossVenueSpreadSummary from './CrossVenueSpreadSummary.vue';
  import CrossVenueTradingRules from './CrossVenueTradingRules.vue';
  import SpreadExecutionCommand from './SpreadExecutionCommand.vue';
  import SpreadExecutionConfirmModal from './SpreadExecutionConfirmModal.vue';
  import SpreadPositionOverview from './SpreadPositionOverview.vue';
  import {
    CROSS_SPREAD_RANGES,
    CROSS_SPREAD_TRADING_RULE_ROWS,
  } from '../composables/crossSpreadFixtures';
  import { useCrossSpreadExecution } from '../composables/useCrossSpreadExecution';
  import { useCrossSpreadExitPlans } from '../composables/useCrossSpreadExitPlans';
  import {
    formatEditableNumber,
    formatNullableRate,
    formatNullableSigned,
    formatNumber,
    parseEditableNumber,
    parseOptionalNumber,
    spreadTone,
  } from '../composables/useCrossSpreadFormatting';
  import { useCrossSpreadObservability } from '../composables/useCrossSpreadObservability';
  import { useCrossSpreadPositions } from '../composables/useCrossSpreadPositions';
  import {
    getCrossSpreadHistory,
    getCrossSpreadSnapshot,
    getInstruments,
  } from '@/api/platform/trading';
  import {
    type CrossSpreadExitPlanResult,
    type CrossSpreadExecutionMode,
    type CrossSpreadLimitStrategy,
  } from '@/api/platform/crossSpreadLifecycle';
  import type {
    CrossSpreadSnapshotResult,
    InstrumentResult,
    MarketQuoteResult,
  } from '@/api/platform/trading.types';

  defineProps<{
    leftLegSymbol: string;
    rightLegSymbol: string;
  }>();

  const BYBIT_INSTRUMENT_ID = 'instrument_xau_usdt_perp';
  const MT5_INSTRUMENT_ID = 'instrument_xau_usd';

  const ranges = CROSS_SPREAD_RANGES;
  const selectedPair = ref('XAUTUSDT.P-XAUUSD.s');
  const selectedRange = ref('15m');
  const executionStage = ref<'open' | 'close'>('open');
  const executionMode = ref<CrossSpreadExecutionMode>('market');
  const closeExecutionMode = ref<CrossSpreadExecutionMode>('market');
  const qtyOz = ref(100);
  const qtyInput = ref('100');
  const instruments = ref<InstrumentResult[]>([]);
  const leverage = ref(10);
  const triggerSpread = ref(-1);
  const acceptableSpread = ref(-1.1);
  const takeProfitSpread = ref(-3);
  const stopLossSpread = ref(1);
  const takeProfitExecution = ref<CrossSpreadExecutionMode>('limit');
  const stopLossExecution = ref<CrossSpreadExecutionMode>('market');
  const openLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const takeProfitLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const stopLossLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const closeLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const closeLimitSpread = ref(-1.9);
  const triggerSpreadInput = ref(formatEditableNumber(triggerSpread.value));
  const acceptableSpreadInput = ref(formatEditableNumber(acceptableSpread.value));
  const takeProfitSpreadInput = ref(formatEditableNumber(takeProfitSpread.value));
  const stopLossSpreadInput = ref(formatEditableNumber(stopLossSpread.value));
  const closeLimitSpreadInput = ref(formatEditableNumber(closeLimitSpread.value));
  const { exitPlans, refreshExitPlans: loadExitPlans } = useCrossSpreadExitPlans();
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

  watch([triggerSpread, acceptableSpread, takeProfitSpread, stopLossSpread, closeLimitSpread], syncSpreadInputs);

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
  const { closeOrders, overviewRows } = useCrossSpreadPositions({
    exitPlans,
    leverage,
    snapshot,
    observability,
    quantityRules,
    longSpread,
    shortSpread,
    snapshotStatusText,
  });
  const {
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
    refreshExitPlans,
    refreshSnapshot,
  });
  const qtyError = computed(() => {
    if (qtyOz.value <= 0) return '数量必须大于 0';
    const rules = quantityRules.value;
    if (!rules) return '合约规格加载中';
    if (qtyOz.value < rules.minOz) return `当前合约最小下单数量为 ${formatNumber(rules.minOz, 2)} 盎司`;
    const steps = (qtyOz.value - rules.minOz) / rules.stepOz;
    if (Math.abs(steps - Math.round(steps)) > 1e-8) {
      return `当前合约下单步长为 ${formatNumber(rules.stepOz, 2)} 盎司`;
    }
    return '';
  });

  function venueStatusLabel(status: string | null | undefined) {
    if (status === 'available') return '可用';
    if (status === 'timeout') return '超时';
    if (status === 'unavailable') return '不可用';
    return '等待';
  }

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
    } catch (error: any) {
      snapshotError.value = error?.response?.data?.detail || error?.message || '跨所行情接口异常';
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

  function commitSpreadInput(field: 'trigger' | 'acceptable' | 'takeProfit' | 'stopLoss' | 'closeLimit') {
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

  function handleQtyInput(event: Event) {
    const parsed = parseEditableNumber((event.target as HTMLInputElement).value);
    if (parsed !== null) qtyOz.value = Math.max(0, parsed);
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

  function handleLeverageInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    leverage.value = Number.isFinite(value) ? Math.max(1, Math.min(20, value)) : 1;
  }

  function nudgeQty(delta: number) {
    const step = quantityRules.value?.stepOz || Math.abs(delta);
    const direction = delta >= 0 ? 1 : -1;
    qtyOz.value = Math.max(0, qtyOz.value + direction * step);
    qtyInput.value = formatEditableNumber(qtyOz.value);
  }

  async function refreshExitPlans() {
    const errorMessage = await loadExitPlans();
    if (errorMessage) {
      setExecutionMessage(errorMessage, 'is-error');
    }
  }

  onMounted(async () => {
    await refreshInstruments();
    await refreshExitPlans();
    await refreshHistory();
    await refreshObservability();
    await refreshSnapshot();
    snapshotTimer = window.setInterval(() => {
      refreshSnapshot();
      refreshObservability();
    }, 15_000);
  });

  onUnmounted(() => {
    if (snapshotTimer) window.clearInterval(snapshotTimer);
  });
</script>

<style scoped lang="less">
  .cross-replica {
    display: flex;
    flex-direction: column;
    gap: 14px;
    color: #10203f;
    background: #f8fafc;
    font-family: var(--strategy-font-sans);
  }

  .cross-head,
  .cross-card {
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
  }

  .cross-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
    padding: 16px 18px;
  }

  .cross-head__title,
  .cross-head__controls,
  .quote-card__head,
  .card-head--between,
  .submit-row,
  .overview-title,
  .overview-range {
    display: flex;
    align-items: center;
  }

  .cross-head__title {
    gap: 12px;
  }

  .cross-head__title h2 {
    margin: 0;
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 700;
    letter-spacing: -0.015em;
    color: #13233f;
  }

  .status-pill {
    padding: 6px 13px;
    border-radius: 999px;
    background: rgba(39, 184, 115, 0.12);
    color: #1a9b58;
    font-size: 12px;
    font-weight: 800;
  }

  .cross-head__controls {
    gap: 10px;
  }

  .select-chip,
  .meta-chip {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 38px;
    padding: 0 14px;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.88);
    color: #637491;
    font-size: 12px;
    font-weight: 600;
  }

  .select-chip select,
  .input-row input,
  .input-row select {
    border: none;
    background: transparent;
    outline: none;
    color: #1a2a48;
    font-size: 14px;
  }

  .select-chip select {
    min-width: 296px;
    font-weight: 700;
  }

  .meta-chip strong {
    color: #18294b;
    font-weight: 700;
  }

  .online-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #1db954;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.12);
  }

  .gear-btn {
    width: 38px;
    height: 38px;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
    background: #ffffff;
    color: #8a6c49;
    cursor: pointer;
  }

  .gear-btn--mini {
    width: 32px;
    height: 32px;
  }

  .cross-top-grid,
  .cross-mid-grid {
    display: grid;
    gap: 14px;
  }

  .cross-top-grid {
    grid-template-columns: 1.42fr 0.86fr 1.08fr;
  }

  .cross-mid-grid {
    grid-template-columns: 0.54fr 1.34fr 0.82fr;
  }

  .cross-card {
    padding: 16px 18px 18px;
  }

  .cross-card--status {
    padding: 14px;
  }

  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  .card-head h3 {
    margin: 0;
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.012em;
    color: #162845;
  }

  .card-head span {
    margin-top: 4px;
    display: inline-block;
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
  }

  .cross-top-grid > .cross-card:first-child .card-head span {
    display: none;
  }

  .quote-grid,
  .summary-grid,
  .mini-grid {
    display: grid;
    gap: 12px;
  }

  .rule-list {
    display: grid;
    gap: 10px;
  }

  .rule-list__row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    min-height: 40px;
    padding: 0 12px;
    border: 1px solid #e6ebf2;
    border-radius: 10px;
    background: #fff;
  }

  .rule-list__label {
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
  }

  .rule-list__value {
    color: #475467;
    font-size: 13px;
    font-weight: 800;
    text-align: right;
  }

  .status-mini-log {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #eef2f7;
  }

  .status-mini-log__head {
    margin-bottom: 10px;
  }

  .status-mini-log__head strong {
    color: #111827;
    font-size: 16px;
    font-weight: 800;
  }

  .status-mini-log__list {
    display: grid;
    gap: 10px;
  }

  .status-mini-log__list p {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin: 0;
    color: #475467;
    font-size: 13px;
    line-height: 1.55;
  }

  .status-mini-log__dot {
    width: 8px;
    height: 8px;
    margin-top: 5px;
    border-radius: 999px;
    flex: none;
  }

  .status-mini-log__dot.is-success {
    background: #22c55e;
  }

  .status-mini-log__dot.is-warn {
    background: #f59e0b;
  }

  .status-mini-log__dot.is-info {
    background: #60a5fa;
  }

  .quote-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .quote-card,
  .metric-card {
    border: 1px solid #e9edf2;
    border-radius: 16px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .quote-card {
    display: flex;
    flex-direction: column;
    padding: 18px 18px 14px;
    min-height: 208px;
  }

  .quote-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px 14px;
    flex-wrap: wrap;
    margin-bottom: 14px;
    color: #1a2b4a;
  }

  .quote-card__head strong {
    font-size: 18px;
    font-weight: 800;
  }

  .live-tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: #19a04d;
    font-size: 12px;
    font-weight: 700;
  }

  .quote-stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    flex: 1;
    align-items: stretch;
  }

  .quote-stat {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 8px;
    min-height: 92px;
    min-width: 0;
  }

  .quote-stat span,
  .summary-item small,
  .metric-card small,
  .field-block span {
    color: #2f3640;
    font-size: 13px;
    font-weight: 800;
  }

  .quote-stat strong {
    font-family: var(--strategy-font-data);
    font-size: clamp(14px, 0.82vw, 18px);
    line-height: 1.08;
    font-weight: 600;
    letter-spacing: -0.02em;
    white-space: nowrap;
  }

  .quote-stat small {
    color: #2f3640;
    font-size: 12px;
    font-weight: 600;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    overflow: hidden;
    border: 1px solid #e9edf2;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.9);
  }

  .summary-item {
    min-height: 106px;
    padding: 14px 16px;
    border-right: 1px solid #e9edf2;
    border-bottom: 1px solid #e9edf2;
  }

  .summary-item:nth-child(2n) {
    border-right: none;
  }

  .summary-item:nth-last-child(-n + 2) {
    border-bottom: none;
  }

  .summary-item label {
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 7px;
    color: #1d2e4d;
    font-family: var(--strategy-font-heading);
    font-size: 16px;
    font-weight: 800;
  }

  .summary-item label small {
    color: #2f3640;
    font-size: 13px;
    font-weight: 600;
  }

  .summary-item strong {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    margin-top: 18px;
    color: #10203f;
    font-family: var(--strategy-font-data);
    font-size: 16px;
    font-weight: 700;
    line-height: 1.2;
  }

  .summary-item--compact label {
    font-size: 14px;
  }

  .summary-item--compact strong {
    margin-top: 14px;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.01em;
    line-height: 1.3;
  }

  .summary-inline {
    white-space: nowrap;
  }

  .summary-item strong em {
    font-size: 14px;
    font-weight: 700;
    font-style: normal;
  }

  .spread-chart {
    height: 238px;
  }

  .range-tabs,
  .stage-tabs,
  .mode-tabs {
    display: flex;
    gap: 8px;
  }

  .range-tabs button,
  .stage-tabs button,
  .mode-tabs button,
  .row-btn {
    border: 1px solid #d7e2ef;
    border-radius: 10px;
    background: #fff;
    color: #47617f;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }

  .range-tabs button {
    height: 32px;
    min-width: 42px;
    padding: 0 12px;
  }

  .stage-tabs {
    margin-bottom: 14px;
  }

  .stage-tabs button {
    min-width: 118px;
    height: 44px;
    padding: 0 18px;
  }

  .mode-tabs {
    margin-bottom: 12px;
  }

  .mode-tabs button {
    flex: 1;
    height: 44px;
    padding: 0 18px;
  }

  .range-tabs button.active,
  .stage-tabs button.active,
  .mode-tabs button.active {
    border-color: rgba(220, 82, 82, 0.38);
    background: linear-gradient(180deg, #ff6868 0%, #ef4343 100%);
    color: #fff;
    box-shadow: 0 8px 20px rgba(239, 67, 67, 0.18);
  }

  .execution-grid {
    display: grid;
    grid-template-columns: 1.08fr 1fr 1fr;
    gap: 20px;
    align-items: start;
  }

  .execution-column {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .execution-column--pricing {
    gap: 14px;
    padding-top: 18px;
  }

  .execution-column--right {
    gap: 14px;
    padding-top: 18px;
  }

  .execution-column__spacer {
    height: 64px;
    flex: none;
  }

  .field-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .field-block--lower {
    margin-top: 0;
  }

  .field-block--compact {
    max-width: 360px;
    margin-bottom: 4px;
  }

  .input-row {
    display: grid;
    grid-template-columns: 1fr 62px;
    height: 48px;
    overflow: hidden;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
    background: #fff;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  }

  .input-row input,
  .input-row select {
    width: 100%;
    padding: 0 14px;
    font-family: var(--strategy-font-data);
    font-size: 15px;
    font-weight: 700;
    min-width: 0;
  }

  .input-row em {
    display: flex;
    align-items: center;
    justify-content: center;
    border-left: 1px solid #e7ebf0;
    background: #fff;
    color: #152646;
    font-size: 13px;
    font-style: normal;
    font-weight: 700;
  }

  .input-row--qty {
    grid-template-columns: 1fr 64px 40px 40px;
  }

  .input-row--select {
    grid-template-columns: minmax(0, 1fr) 60px 76px;
  }

  .input-row--select select {
    border-left: 1px solid #e7ebf0;
  }

  .input-row--condition {
    grid-template-columns: 58px minmax(0, 1fr) 64px;
  }

  .input-row--condition select {
    border-right: 1px solid #e7ebf0;
    border-left: none;
    padding: 0 18px 0 10px;
    text-align: center;
    text-align-last: center;
  }

  .input-row--condition input {
    padding-right: 8px;
  }

  .input-row--single-select {
    grid-template-columns: minmax(0, 1fr);
  }

  .input-row--single-select select {
    padding-right: 30px;
  }

  .input-row--qty button,
  .unit-btn {
    border: none;
    border-left: 1px solid #e7ebf0;
    background: #fff;
    color: #152646;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
  }

  .mini-panel {
    padding: 12px 14px 14px;
    border: 1px solid #e9edf2;
    border-radius: 16px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .mini-panel__title {
    display: block;
    margin-bottom: 10px;
    color: #2f3640;
    font-size: 15px;
    font-weight: 800;
  }

  .mini-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-card {
    min-height: 74px;
    padding: 12px 14px;
    border: 1px solid #e9edf2;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.94);
  }

  .metric-card strong {
    display: block;
    margin-top: 8px;
    color: #172947;
    font-family: var(--strategy-font-data);
    font-size: 16px;
    font-weight: 500;
  }

  .submit-row {
    justify-content: space-between;
    gap: 16px;
    margin-top: 16px;
  }

  .submit-row--compact {
    margin-top: 0;
  }

  .submit-btn {
    flex: 1;
    height: 52px;
    border: none;
    border-radius: 12px;
    color: #fff;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 0.01em;
    cursor: pointer;
  }

  .submit-btn--green {
    background: linear-gradient(90deg, #16a34a 0%, #0f8f3e 100%);
  }

  .submit-btn--red {
    background: linear-gradient(90deg, #ff4b4b 0%, #e92222 100%);
  }

  .submit-btn--full {
    width: 100%;
    margin-top: 16px;
    min-height: 58px;
    font-size: 18px;
  }

  .submit-btn--monitor {
    max-width: 156px;
  }

  .close-shell {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .basic-table,
  .overview-table {
    width: 100%;
    border-collapse: collapse;
  }

  .basic-table th,
  .basic-table td,
  .overview-table th,
  .overview-table td {
    padding: 13px 10px;
    border-bottom: 1px solid #d8e2ec;
    font-size: 13px;
    text-align: left;
    white-space: nowrap;
  }

  .basic-table th,
  .overview-table th {
    color: #2f3640;
    font-size: 14px;
    font-weight: 800;
  }

  .basic-table td,
  .overview-table td {
    color: #22324d;
    font-family: var(--strategy-font-data);
    font-size: 13px;
    font-weight: 700;
  }

  .overview-table td {
    font-weight: 500;
  }

  .row-btn {
    min-width: 104px;
    height: 40px;
    padding: 0 16px;
    font-size: 14px;
    font-weight: 600;
  }

  .cross-card--overview {
    padding-bottom: 14px;
  }

  .overview-range {
    display: grid;
    gap: 6px;
    max-width: 540px;
    margin-bottom: 12px;
  }

  .overview-range__meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    font-weight: 800;
    line-height: 1;
  }

  .overview-range__track {
    position: relative;
    display: flex;
    height: 6px;
    overflow: hidden;
    border-radius: 999px;
    background: #eef2f8;
  }

  .overview-range__green {
    height: 100%;
    background: linear-gradient(90deg, #19a34b 0%, #16b257 100%);
  }

  .overview-range__red {
    height: 100%;
    background: linear-gradient(90deg, #ff6868 0%, #ff3d3d 100%);
  }

  .overview-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #edf2f8;
  }

  .overview-summary--top {
    margin-bottom: 12px;
  }

  .overview-summary__item {
    display: flex;
    align-items: baseline;
    gap: 10px;
    min-width: 0;
  }

  .overview-summary__item span {
    color: #61728e;
    font-size: 24px;
    font-weight: 600;
    line-height: 1.1;
    white-space: nowrap;
  }

  .overview-summary__item strong {
    font-size: 24px;
    font-weight: 600;
    line-height: 1.1;
    white-space: nowrap;
  }

  .green {
    color: #179b4b !important;
  }

  .red,
  .red-text {
    color: #ef3232 !important;
  }

  .warning {
    color: #d07d1e !important;
  }

  .field-error {
    margin: 0;
    color: #d92b2b;
    font-size: 12px;
  }

  .execution-feedback {
    display: grid;
    gap: 6px;
    padding: 10px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface-muted);
    color: var(--strategy-text-2);
    font-size: 12px;
    font-weight: 700;
  }

  .execution-feedback span {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .execution-feedback strong {
    color: var(--strategy-text-1);
    font-weight: 800;
  }

  .execution-feedback {
    margin-top: 12px;
  }

  .execution-feedback .is-success {
    color: var(--strategy-success);
  }

  .execution-feedback .is-warn {
    color: #b7791f;
  }

  .execution-feedback .is-error {
    color: var(--strategy-danger);
  }

  .trade-modal {
    position: fixed;
    inset: 0;
    z-index: 1200;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(11, 21, 42, 0.3);
  }

  .trade-modal__dialog {
    width: min(620px, calc(100vw - 32px));
    border-radius: 20px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    box-shadow: 0 30px 60px rgba(23, 41, 72, 0.24);
  }

  .trade-modal__header,
  .trade-modal__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 20px;
  }

  .trade-modal__header {
    border-bottom: 1px solid #edf2f8;
  }

  .trade-modal__body {
    padding: 18px 20px 22px;
  }

  .trade-modal__eyebrow {
    display: none;
  }

  .trade-modal__header h3 {
    margin: 0;
    color: #172947;
    font-size: 20px;
    font-weight: 800;
  }

  .trade-modal__close {
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    color: #678;
    font-size: 20px;
    cursor: pointer;
  }

  .confirm-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .confirm-grid div {
    padding: 12px 14px;
    border: 1px solid #e3ebf6;
    border-radius: 12px;
    background: #fbfdff;
  }

  .confirm-grid span {
    display: block;
    margin-bottom: 8px;
    color: #7b8aa5;
    font-size: 12px;
    font-weight: 700;
  }

  .confirm-grid strong {
    color: #172947;
    font-size: 15px;
    font-weight: 800;
  }

  .modal-btn {
    height: 40px;
    padding: 0 18px;
    border-radius: 10px;
    border: 1px solid #dfe7f4;
    font-size: 14px;
    font-weight: 800;
    cursor: pointer;
  }

  .modal-btn--ghost {
    background: #fff;
    color: #526581;
  }

  .modal-btn--primary {
    border-color: #ff4b4b;
    background: #ff4b4b;
    color: #fff;
  }

  .cross-replica {
    color: var(--strategy-text-1);
    background: var(--strategy-bg);
  }

  .cross-head,
  .cross-card,
  .quote-card,
  .mini-panel,
  .metric-card,
  .summary-grid,
  .trade-modal__dialog {
    border-color: var(--strategy-border);
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
  }

  .cross-head__title h2,
  .card-head h3,
  .summary-item label,
  .summary-item strong,
  .metric-card strong,
  .quote-card__head strong,
  .overview-title h3 {
    color: var(--strategy-text-1);
  }

  .cross-card--summary .summary-item .red,
  .cross-card--summary .summary-item .green {
    color: var(--strategy-text-1) !important;
  }

  .card-head span,
  .summary-item label small,
  .quote-stat small,
  .mini-panel__title,
  .rule-list__label,
  .overview-summary__item span {
    color: #2f3640;
  }

  .status-pill {
    background: var(--strategy-success-soft);
    color: var(--strategy-success);
  }

  .select-chip,
  .meta-chip,
  .gear-btn,
  .input-row,
  .range-tabs button,
  .stage-tabs button,
  .mode-tabs button,
  .row-btn {
    border-color: var(--strategy-border-strong);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
  }

  .range-tabs button.active,
  .stage-tabs button.active,
  .mode-tabs button.active {
    border-color: rgba(201, 72, 72, 0.18);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px rgba(201, 72, 72, 0.08);
  }

  .select-chip select,
  .input-row input,
  .input-row select,
  .meta-chip strong {
    color: var(--strategy-text-1);
  }

  .cross-card--execution .input-row input,
  .cross-card--execution .input-row select,
  .cross-card--execution .metric-card strong {
    font-weight: 500;
  }

  .cross-card--execution .input-row--select {
    grid-template-columns: minmax(0, 1fr) 60px 90px;
  }

  .cross-card--execution .input-row--select select {
    padding-right: 26px;
  }

  .input-row em,
  .input-row--qty button,
  .unit-btn {
    border-left-color: var(--strategy-border);
    background: var(--strategy-surface-muted);
    color: var(--strategy-text-2);
  }

  .cross-card--execution .input-row em,
  .cross-card--execution .input-row--qty button,
  .cross-card--execution .unit-btn {
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
  }

  .cross-card--execution .input-row--select em {
    background: var(--strategy-surface);
  }

  @media (max-width: 1480px) {
    .cross-top-grid,
    .cross-mid-grid,
    .execution-grid {
      grid-template-columns: 1fr;
    }

    .cross-head,
    .cross-head__controls {
      flex-direction: column;
      align-items: flex-start;
    }

    .select-chip select {
      min-width: 0;
      width: 100%;
    }

    .field-block--lower {
      margin-top: 0;
    }

    .execution-column__spacer {
      display: none;
    }

    .mini-grid,
    .quote-grid {
      grid-template-columns: 1fr;
    }

    .quote-stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .overview-summary {
      grid-template-columns: 1fr;
      flex-direction: column;
    }
  }

  @media (max-width: 960px) {
    .stage-tabs,
    .mode-tabs,
    .submit-row {
      flex-direction: column;
      align-items: stretch;
    }

    .field-block--compact {
      max-width: none;
    }

    .basic-table,
    .overview-table {
      display: block;
      overflow-x: auto;
    }
  }
</style>




