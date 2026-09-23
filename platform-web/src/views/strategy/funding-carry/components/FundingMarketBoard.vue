<template>
  <section class="market-board" :class="{ 'single-venue': !data.inverseExchanges.length }">
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

    <div class="market-board__content">
      <div class="market-board__table-area">
        <div class="market-board__toolbar">
          <div class="symbol-controls">
            <label
              >筛选关注标的<input
                :value="search"
                placeholder="搜索币种"
                @input="$emit('update:search', ($event.target as HTMLInputElement).value)"
            /></label>
            <label
              >排序<select
                :value="sort"
                @change="$emit('update:sort', ($event.target as HTMLSelectElement).value as Sort)"
                ><option value="default">关注顺序</option
                ><option value="name">币种名称</option
                ><option value="rate_desc">资费从高到低</option
                ><option value="rate_asc">资费从低到高</option></select
              ></label
            >
            <label
              >添加标的<input
                v-model="adding"
                list="funding-symbol-catalog"
                placeholder="搜索全部标的"
                @keydown.enter.prevent="addSymbol" /><datalist id="funding-symbol-catalog"
                ><option
                  v-for="symbol in data.symbolOptions"
                  :key="symbol"
                  :value="symbol"
                ></option></datalist
            ></label>
            <button type="button" :disabled="!canAdd" @click="addSymbol">添加</button>
          </div>
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

            <div v-for="row in data.rows" :key="row.symbol" class="heatmap-table__row">
              <div class="symbol-cell symbol-cell--row"
                >{{ row.symbol
                }}<button
                  type="button"
                  :aria-label="`移除 ${row.symbol}`"
                  @click="removeSymbol(row.symbol)"
                  >×</button
                ></div
              >
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
      </div>

      <article class="extrema-card extrema-card--combined">
        <section>
          <h3>最高资金费率</h3>
          <div class="extrema-list">
            <div v-for="item in data.highest" :key="item.market" class="extrema-row">
              <span>{{ item.market }}</span>
              <strong :class="rateClass(item.value)">{{ formatRate(item.value) }}</strong>
            </div>
          </div>
        </section>

        <section>
          <h3>最低资金费率</h3>
          <div class="extrema-list">
            <div v-for="item in data.lowest" :key="item.market" class="extrema-row">
              <span>{{ item.market }}</span>
              <strong :class="rateClass(item.value)">{{ formatRate(item.value) }}</strong>
            </div>
          </div>
        </section>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type { FundingMarketBoardData, FundingMarketRange } from '../types';

  type Sort = 'default' | 'name' | 'rate_desc' | 'rate_asc';
  const props = defineProps<{
    symbols?: string;
    search?: string;
    sort?: Sort;
    data: FundingMarketBoardData;
    exchange: string;
    selectedRange: FundingMarketRange;
    selectedSymbol: string;
    selectedResolution: string;
    rangeOptions: Array<{ value: FundingMarketRange; label: string }>;
  }>();

  const emit = defineEmits<{
    (e: 'update:symbols', value: string): void;
    (e: 'update:search', value: string): void;
    (e: 'update:sort', value: Sort): void;
    (e: 'update:selectedRange', value: FundingMarketRange): void;
    (e: 'update:selectedSymbol', value: string): void;
    (e: 'update:selectedResolution', value: string): void;
  }>();
  const adding = ref('');
  const canAdd = computed(
    () =>
      props.data.symbolOptions.includes(adding.value.trim().toUpperCase()) &&
      !(props.symbols || '').split(',').includes(adding.value.trim().toUpperCase()),
  );
  function addSymbol() {
    if (!canAdd.value) return;
    emit(
      'update:symbols',
      [...(props.symbols || '').split(',').filter(Boolean), adding.value.trim().toUpperCase()].join(
        ',',
      ),
    );
    adding.value = '';
  }
  function removeSymbol(symbol: string) {
    emit(
      'update:symbols',
      (props.symbols || '')
        .split(',')
        .filter((s) => s !== symbol)
        .join(','),
    );
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
    if (value >= 0) return 'is-positive';
    return 'is-negative';
  }
</script>

<style scoped lang="less">
  .symbol-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 12px;
  }

  .symbol-controls label {
    display: grid;
    gap: 5px;
    font-size: 12px;
  }

  .symbol-controls input,
  .symbol-controls select,
  .symbol-controls button {
    max-width: 180px;
    padding: 7px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface);
  }

  .symbol-cell--row button {
    margin-left: 12px;
    border: 0;
    background: transparent;
    color: var(--strategy-text-3);
    cursor: pointer;
  }

  .single-venue .heatmap-table__header,
  .single-venue .heatmap-table__row {
    grid-template-columns: minmax(120px, 1fr) minmax(140px, 1fr);
    min-width: 0;
  }

  .single-venue .group-header--inverse,
  .single-venue .group-row--inverse {
    display: none;
  }

  .heatmap-shell {
    max-height: 400px;
    margin-top: 14px;
    padding-top: 16px;
    overflow: auto;
  }

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

  .market-board__content {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(220px, 260px);
    gap: 18px;
    align-items: stretch;
  }

  .market-board__table-area,
  .extrema-card {
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .market-board__table-area {
    min-width: 0;
    padding: 18px;
  }

  .extrema-card--combined {
    display: grid;
    align-content: start;
    gap: 22px;
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
    color: var(--strategy-danger);
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
    .market-board__content {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 900px) {
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
