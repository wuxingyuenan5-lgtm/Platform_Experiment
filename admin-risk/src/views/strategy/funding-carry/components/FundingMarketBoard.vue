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
      <div class="heatmap-caption">
        <span>USDT / USD 合约</span>
        <span>币本位合约</span>
      </div>

      <div class="heatmap-table">
        <div class="heatmap-table__header">
          <div class="symbol-cell">币种</div>
          <div class="group-header" :style="{ gridTemplateColumns: `repeat(${data.usdtExchanges.length}, minmax(74px, 1fr))` }">
            <span v-for="exchange in data.usdtExchanges" :key="exchange">{{ exchange }}</span>
          </div>
          <div class="group-header group-header--inverse" :style="{ gridTemplateColumns: `repeat(${data.inverseExchanges.length}, minmax(74px, 1fr))` }">
            <span v-for="exchange in data.inverseExchanges" :key="exchange">{{ exchange }}</span>
          </div>
        </div>

        <div v-for="row in data.rows" :key="row.symbol" class="heatmap-table__row">
          <div class="symbol-cell symbol-cell--row">{{ row.symbol }}</div>
          <div class="group-row" :style="{ gridTemplateColumns: `repeat(${data.usdtExchanges.length}, minmax(74px, 1fr))` }">
            <span
              v-for="exchange in data.usdtExchanges"
              :key="`${row.symbol}-${exchange}`"
              :class="rateClass(row.usdtPerps[exchange])"
            >
              {{ displayRate(row.usdtPerps[exchange]) }}
            </span>
          </div>
          <div class="group-row group-row--inverse" :style="{ gridTemplateColumns: `repeat(${data.inverseExchanges.length}, minmax(74px, 1fr))` }">
            <span
              v-for="exchange in data.inverseExchanges"
              :key="`${row.symbol}-inverse-${exchange}`"
              :class="rateClass(row.inversePerps[exchange])"
            >
              {{ displayRate(row.inversePerps[exchange]) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import type { FundingMarketBoardData, FundingMarketRange } from '../types';

  defineProps<{
    data: FundingMarketBoardData;
    exchange: string;
    selectedRange: FundingMarketRange;
    selectedSymbol: string;
    selectedResolution: string;
    rangeOptions: Array<{ value: FundingMarketRange; label: string }>;
  }>();

  defineEmits<{
    (e: 'update:selectedRange', value: FundingMarketRange): void;
    (e: 'update:selectedSymbol', value: string): void;
    (e: 'update:selectedResolution', value: string): void;
  }>();

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
    padding: 26px;
    border: 1px solid rgba(134, 115, 87, 0.12);
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 16px 36px rgba(94, 76, 52, 0.06);
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
    border: 1px solid rgba(134, 115, 87, 0.1);
    border-radius: 10px;
    background: #fff;
  }

  .context-chip span {
    color: rgba(36, 29, 21, 0.58);
    font-size: 12px;
    font-weight: 700;
  }

  .context-chip strong {
    color: #1f2937;
    font-size: 13px;
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
    border: 1px solid rgba(134, 115, 87, 0.08);
    border-radius: 14px;
    background: #fff;
  }

  .summary-card {
    display: grid;
    gap: 14px;
    min-height: 140px;
    padding: 18px 18px 16px;
  }

  .summary-card__title {
    padding: 8px 14px;
    border-radius: 10px;
    background: #f3f6f8;
    color: rgba(36, 29, 21, 0.7);
    font-size: 14px;
    font-weight: 700;
    text-align: center;
  }

  .summary-card__value {
    font-size: 20px;
    font-weight: 700;
    text-align: center;
  }

  .summary-card__subtitle {
    color: rgba(36, 29, 21, 0.62);
    font-size: 13px;
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
    color: #241d15;
    font-size: 22px;
    font-weight: 600;
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
    color: rgba(36, 29, 21, 0.74);
    font-size: 14px;
  }

  .extrema-row strong {
    font-size: 15px;
    font-weight: 700;
  }

  .is-positive {
    color: #10b981;
  }

  .is-negative {
    color: #ff3040;
  }

  .is-hot {
    color: #ff6b6b;
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
    height: 36px;
    padding: 0 16px;
    border: 1px solid rgba(134, 115, 87, 0.08);
    border-radius: 10px;
    background: #f4f6f8;
    color: rgba(36, 29, 21, 0.72);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  .range-tabs .is-active {
    background: #111827;
    border-color: #111827;
    color: #fff;
  }

  .heatmap-shell {
    margin-top: 14px;
    border-top: 1px solid rgba(134, 115, 87, 0.08);
    padding-top: 16px;
  }

  .heatmap-caption {
    display: grid;
    grid-template-columns: minmax(120px, 140px) minmax(0, 1fr) minmax(240px, 280px);
    align-items: center;
    margin-bottom: 10px;
    color: rgba(36, 29, 21, 0.72);
    font-size: 14px;
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
    border-bottom: 1px solid rgba(134, 115, 87, 0.08);
  }

  .heatmap-table__row {
    min-height: 58px;
    border-bottom: 1px solid rgba(134, 115, 87, 0.06);
  }

  .group-header,
  .group-row {
    display: grid;
    gap: 0;
    align-items: center;
  }

  .group-header span {
    color: #334155;
    font-size: 13px;
    font-weight: 700;
    text-align: center;
  }

  .group-row span {
    padding: 12px 8px;
    color: #1f2937;
    font-size: 13px;
    font-weight: 700;
    text-align: center;
  }

  .group-row .is-positive {
    color: #0ea768;
  }

  .group-row .is-negative {
    color: #19a463;
  }

  .group-row .is-hot {
    color: #ff6472;
  }

  .group-row .is-empty {
    color: rgba(36, 29, 21, 0.34);
  }

  .symbol-cell {
    color: rgba(36, 29, 21, 0.62);
    font-size: 13px;
    font-weight: 700;
  }

  .symbol-cell--row {
    color: #1f2937;
    font-size: 16px;
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
