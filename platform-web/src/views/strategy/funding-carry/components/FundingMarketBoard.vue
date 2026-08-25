<template>
  <section class="market-board">
    <div class="market-board__context">
      <div class="context-chip">
        <span>交易所</span>
        <strong>{{ exchange }}</strong>
      </div>
      <div class="context-chip">
        <span>币种</span>
        <strong>{{ selectedSymbol }}</strong>
      </div>
      <div class="context-chip">
        <span>时间精度</span>
        <strong>{{ selectedResolution }}</strong>
      </div>
    </div>

    <div class="market-board__top">
      <div class="summary-grid">
        <article v-for="item in data.summaryCards" :key="item.title" class="summary-card">
          <div class="summary-card__title">{{ item.title }}</div>
          <div class="summary-card__value" :class="`is-${item.tone}`">{{ item.value }}</div>
          <div class="summary-card__subtitle">{{ item.subtitle }}</div>
        </article>
      </div>

      <div class="extrema-grid">
        <article class="extrema-card">
          <h3>最高资金费率</h3>
          <div class="extrema-list">
            <div v-for="item in data.highest" :key="item.market" class="extrema-row">
              <span>{{ item.market }}</span>
              <strong class="is-negative">{{ formatRate(item.value) }}</strong>
            </div>
          </div>
        </article>

        <article class="extrema-card">
          <h3>最低资金费率</h3>
          <div class="extrema-list">
            <div v-for="item in data.lowest" :key="item.market" class="extrema-row">
              <span>{{ item.market }}</span>
              <strong class="is-positive">{{ formatRate(item.value) }}</strong>
            </div>
          </div>
        </article>
      </div>
    </div>

    <div class="market-board__toolbar">
      <div class="range-tabs">
        <button
          v-for="item in rangeOptions"
          :key="item.value"
          type="button"
          :class="{ 'is-active': item.value === selectedRange }"
          @click="$emit('update:selectedRange', item.value)"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="board-actions">
        <button type="button">预测费率</button>
        <button type="button">显示自选</button>
        <button type="button">添加自选</button>
      </div>
    </div>

    <div class="heatmap-shell">
      <div class="heatmap-table">
        <div class="heatmap-table__header">
          <div class="symbol-cell">币种</div>
          <div
            class="group-header"
            :style="{
              gridTemplateColumns: `repeat(${data.usdtExchanges.length}, minmax(74px, 1fr))`,
            }"
          >
            <span v-for="venue in data.usdtExchanges" :key="venue">{{ venue }}</span>
          </div>
          <div
            class="group-header group-header--inverse"
            :style="{
              gridTemplateColumns: `repeat(${data.inverseExchanges.length}, minmax(74px, 1fr))`,
            }"
          >
            <span v-for="venue in data.inverseExchanges" :key="venue">{{ venue }}</span>
          </div>
        </div>

        <div
          v-for="row in data.rows"
          :key="row.symbol"
          class="heatmap-table__row"
          @click="selectRow(row.symbol)"
        >
          <div class="symbol-cell symbol-cell--row">{{ row.symbol }}</div>
          <div
            class="group-row"
            :style="{
              gridTemplateColumns: `repeat(${data.usdtExchanges.length}, minmax(74px, 1fr))`,
            }"
          >
            <span
              v-for="venue in data.usdtExchanges"
              :key="`${row.symbol}-${venue}`"
              :class="rateClass(row.usdtPerps[venue])"
            >
              {{ displayRate(row.usdtPerps[venue]) }}
            </span>
          </div>
          <div
            class="group-row group-row--inverse"
            :style="{
              gridTemplateColumns: `repeat(${data.inverseExchanges.length}, minmax(74px, 1fr))`,
            }"
          >
            <span
              v-for="venue in data.inverseExchanges"
              :key="`${row.symbol}-inverse-${venue}`"
              :class="rateClass(row.inversePerps[venue])"
            >
              {{ displayRate(row.inversePerps[venue]) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { FundingMarketBoardData, FundingMarketRange } from '../types';

  const props = defineProps<{
    context: Record<string, any> | null;
    loading: boolean;
    error: string | null;
  }>();

  const emit = defineEmits<{
    (e: 'refresh'): void;
    (e: 'select-symbol', perpetualSymbol: string, spotSymbol: string): void;
    (e: 'update:selectedRange', value: FundingMarketRange): void;
  }>();

  const exchange = computed(() => props.context?.venue ?? 'Bybit');
  const selectedSymbol = computed(() => {
    const option = props.context?.symbolOptions?.find(
      (item: Record<string, any>) => item.perpetualSymbol === props.context?.perpetualSymbol,
    );
    return option?.baseAsset ?? props.context?.perpetualSymbol?.replace(/USDT$/i, '') ?? '--';
  });
  const selectedResolution = computed(() => '实时');
  const selectedRange = computed<FundingMarketRange>(() => 'current');
  const rangeOptions = computed(() => [{ value: 'current' as FundingMarketRange, label: '实时' }]);

  const fundingRatePercent = computed(() => {
    const raw = Number(props.context?.fundingRate);
    return Number.isFinite(raw) ? raw * 100 : null;
  });

  function displayQuote(quote: Record<string, any> | null | undefined) {
    const value = quote?.mid;
    return value === null || value === undefined || value === '' ? '--' : String(value);
  }

  const data = computed<FundingMarketBoardData>(() => {
    const rate = fundingRatePercent.value;
    const selected = selectedSymbol.value;
    const options = props.context?.symbolOptions ?? [];
    return {
      updatedAt: props.context?.asOf ?? '',
      symbolOptions: options.map((item: Record<string, any>) => item.baseAsset),
      resolutionOptions: ['实时'],
      summaryCards: [
        {
          title: '当前资金费率',
          value: rate === null ? '--' : formatRate(rate),
          subtitle: props.context?.nextFundingTime
            ? `下次结算 ${props.context.nextFundingTime}`
            : '结算时间待同步',
          tone: rate !== null && rate < 0 ? 'negative' : 'positive',
        },
        {
          title: '现货 / 永续基差',
          value: props.context?.basis ?? '--',
          subtitle: `${displayQuote(props.context?.spotQuote)} / ${displayQuote(
            props.context?.perpetualQuote,
          )}`,
          tone: Number(props.context?.basis) < 0 ? 'negative' : 'positive',
        },
        {
          title: '账户可用资金',
          value: props.context?.activeReservation?.fundingAvailable ?? '--',
          subtitle: props.context?.activeReservation?.currency ?? 'USDT',
          tone: 'positive',
        },
        {
          title: '数据状态',
          value: props.loading ? '同步中' : props.error ? '不可用' : '实时',
          subtitle: props.error ?? props.context?.dataQualityState ?? 'authoritative',
          tone: props.error ? 'negative' : 'positive',
        },
      ],
      highest: rate !== null && rate >= 0 ? [{ market: `${selected} · Bybit`, value: rate }] : [],
      lowest: rate !== null && rate < 0 ? [{ market: `${selected} · Bybit`, value: rate }] : [],
      usdtExchanges: ['Bybit'],
      inverseExchanges: ['交割合约'],
      rows: options.map((item: Record<string, any>) => ({
        symbol: item.baseAsset,
        usdtPerps: {
          Bybit: item.perpetualSymbol === props.context?.perpetualSymbol ? rate : null,
        },
        inversePerps: { 交割合约: null },
      })),
    };
  });

  function selectRow(symbol: string) {
    const option = props.context?.symbolOptions?.find(
      (item: Record<string, any>) => item.baseAsset === symbol,
    );
    if (option) emit('select-symbol', option.perpetualSymbol, option.spotSymbol);
  }

  function formatRate(value: number) {
    return `${value.toFixed(4)}%`;
  }

  function displayRate(value: number | null) {
    if (value === null || Number.isNaN(value)) return '-';
    return `${value.toFixed(4)}%`;
  }

  function rateClass(value: number | null) {
    if (value === null || Number.isNaN(value)) return 'is-empty';
    if (value > 0.01) return 'is-hot';
    if (value > 0) return 'is-positive';
    return 'is-negative';
  }
</script>

<style scoped lang="less">
  .market-board {
    padding: var(--strategy-space-5);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .market-board__context {
    display: none;
  }

  .context-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 36px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
  }

  .context-chip span {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  .context-chip strong {
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-sm);
    font-weight: 800;
  }

  .market-board__top {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(420px, 0.9fr);
    gap: 18px;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .summary-card,
  .extrema-card {
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .summary-card {
    display: grid;
    gap: 14px;
    min-height: 140px;
    padding: 18px 18px 16px;
  }

  .summary-card__title {
    padding: 8px 14px;
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface-muted);
    color: var(--strategy-text-1);
    font-size: 16px;
    font-weight: 800;
    text-align: center;
  }

  .summary-card__value {
    font-size: 24px;
    font-weight: 800;
    text-align: center;
  }

  .summary-card__subtitle {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 600;
    text-align: center;
  }

  .extrema-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .extrema-card {
    padding: 18px;
  }

  .extrema-card h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 16px;
    font-weight: 800;
  }

  .extrema-list {
    display: grid;
    gap: 12px;
    margin-top: 16px;
  }

  .extrema-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 12px;
    align-items: center;
  }

  .extrema-row span {
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
  }

  .extrema-row strong {
    font-size: 15px;
    font-weight: 700;
  }

  .is-positive {
    color: var(--strategy-success);
  }

  .is-negative {
    color: var(--strategy-danger);
  }

  .is-hot {
    color: var(--strategy-danger);
  }

  .market-board__toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-top: 24px;
  }

  .range-tabs,
  .board-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .range-tabs button,
  .board-actions button {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    cursor: pointer;
  }

  .range-tabs .is-active {
    border-color: var(--strategy-accent-soft);
    background: var(--strategy-accent-soft);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
    color: var(--strategy-accent-strong);
  }

  .heatmap-shell {
    margin-top: 14px;
    padding-top: 16px;
    border-top: 1px solid var(--strategy-border);
  }

  .heatmap-caption {
    display: grid;
    grid-template-columns: minmax(120px, 140px) minmax(0, 1fr) minmax(240px, 280px);
    align-items: center;
    margin-bottom: 10px;
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 600;
  }

  .heatmap-table {
    overflow-x: auto;
  }

  .heatmap-table__header,
  .heatmap-table__row {
    display: grid;
    grid-template-columns: minmax(120px, 140px) minmax(0, 1fr) minmax(240px, 280px);
    gap: 12px;
    align-items: center;
  }

  .heatmap-table__header {
    padding: 12px 0;
    border-bottom: 1px solid var(--strategy-border);
    background: var(--strategy-table-head-bg);
  }

  .heatmap-table__row {
    min-height: 58px;
    border-bottom: 1px solid var(--strategy-border-soft);
  }

  .group-header,
  .group-row {
    display: grid;
    gap: 0;
    align-items: center;
  }

  .group-header span {
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
    text-align: center;
  }

  .group-row span {
    padding: 12px 8px;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
    text-align: center;
  }

  .group-row .is-positive {
    color: var(--strategy-success);
  }

  .group-row .is-negative {
    color: var(--strategy-success);
  }

  .group-row .is-hot {
    color: var(--strategy-danger);
  }

  .group-row .is-empty {
    color: var(--strategy-text-faint);
  }

  .symbol-cell {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
  }

  .symbol-cell--row {
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
  }

  @media (max-width: 1200px) {
    .market-board__top {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 900px) {
    .summary-grid,
    .extrema-grid {
      grid-template-columns: 1fr;
    }

    .market-board__toolbar {
      flex-direction: column;
      align-items: flex-start;
    }

    .heatmap-caption,
    .heatmap-table__header,
    .heatmap-table__row {
      min-width: 1080px;
    }
  }
</style>
