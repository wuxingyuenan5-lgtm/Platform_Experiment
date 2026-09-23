<template>
  <div class="etf-flow-panel">
    <div v-if="loading" class="etf-flow-panel__state">加载中…</div>
    <div v-else-if="error" class="etf-flow-panel__state etf-flow-panel__state--error">
      {{ error }}
    </div>
    <div v-else-if="days.length === 0" class="etf-flow-panel__state">暂无 ETF 资金流数据</div>
    <div v-else class="etf-flow-panel__body">
      <div class="etf-flow-panel__header">
        <div class="etf-flow-panel__mode" role="group" aria-label="ETF 视图切换">
          <button
            type="button"
            :class="{ 'is-active': mode === 'chart' }"
            aria-label="图表视图"
            @click="mode = 'chart'"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <polyline points="1,12 5,8 8,10 11,4 15,6" />
            </svg>
          </button>
          <button
            type="button"
            :class="{ 'is-active': mode === 'table' }"
            aria-label="表格视图"
            @click="mode = 'table'"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <rect x="1.5" y="2" width="13" height="12" rx="1" />
              <path d="M1.5 6h13M1.5 10h13M6 2v12M10 2v12" />
            </svg>
          </button>
        </div>
      </div>

      <div v-if="mode === 'chart'" class="etf-flow-panel__chart-wrap">
        <svg
          class="etf-flow-panel__chart"
          :viewBox="`0 0 ${chart.width} ${chart.height}`"
          role="img"
          :aria-label="`${assetLabel} ETF 日资金流与价格双轴图`"
        >
          <g v-for="tick in chart.yTicks" :key="tick.value">
            <line
              :x1="chart.pad.left"
              :x2="chart.width - chart.pad.right"
              :y1="tick.y"
              :y2="tick.y"
              class="etf-flow-panel__grid"
            />
            <text
              :x="chart.pad.left - 8"
              :y="tick.y + 4"
              text-anchor="end"
              class="etf-flow-panel__axis"
            >
              {{ tick.label }}
            </text>
          </g>
          <g v-for="tick in chart.priceTicks" :key="`price-${tick.value}`">
            <text
              :x="chart.width - chart.pad.right + 8"
              :y="tick.y + 4"
              text-anchor="start"
              class="etf-flow-panel__axis etf-flow-panel__axis--price"
            >
              {{ tick.label }}
            </text>
          </g>
          <line
            :x1="chart.pad.left"
            :x2="chart.width - chart.pad.right"
            :y1="chart.zeroY"
            :y2="chart.zeroY"
            class="etf-flow-panel__zero"
          />
          <rect
            v-for="bar in chart.bars"
            :key="bar.date"
            :x="bar.x"
            :y="bar.y"
            :width="bar.width"
            :height="bar.height"
            :class="['etf-flow-panel__bar', { 'is-outflow': bar.value < 0 }]"
            rx="1.5"
          >
            <title>{{ bar.date }}：{{ formatFlow(bar.value) }} {{ flowUnit }}</title>
          </rect>
          <path v-if="chart.priceLine" :d="chart.priceLine" class="etf-flow-panel__price-line" />
          <g v-for="tick in chart.xTicks" :key="tick.label">
            <text
              :x="tick.x"
              :y="chart.height - chart.pad.bottom + 20"
              text-anchor="middle"
              class="etf-flow-panel__axis"
            >
              {{ tick.label }}
            </text>
          </g>
          <text
            v-if="chart.lastPrice != null"
            :x="chart.width - chart.pad.right + 8"
            :y="chart.priceLabelY"
            text-anchor="start"
            class="etf-flow-panel__price-label"
          >
            {{ assetLabel }} {{ formatPrice(chart.lastPrice) }}
          </text>
        </svg>
        <div class="etf-flow-panel__chart-legend">
          <span><i class="is-flow"></i>日净流入 / 流出（{{ flowUnit }}）</span>
          <span v-if="chart.hasPriceAxis"
            ><i class="is-price"></i>{{ assetLabel }} 价格（右轴）</span
          >
        </div>
        <div v-if="days.length > 1" class="etf-flow-panel__range">
          <div class="etf-flow-panel__range-labels" aria-hidden="true">
            <span>{{ formatDate(days[startIndex]?.date) }}</span>
            <span>{{ formatDate(days[endIndex]?.date) }}</span>
          </div>
          <div class="etf-flow-panel__range-viewport">
            <svg viewBox="0 0 100 20" preserveAspectRatio="none" aria-hidden="true">
              <polyline :points="overviewPoints" />
            </svg>
            <span class="etf-flow-panel__range-rail" aria-hidden="true"></span>
            <span
              class="etf-flow-panel__range-selection"
              :style="{
                '--range-start': `${rangeStartPercent}%`,
                '--range-end': `${rangeEndPercent}%`,
              }"
              aria-hidden="true"
            ></span>
            <input
              v-model.number="startIndex"
              class="etf-flow-panel__range-thumb etf-flow-panel__range-thumb--start"
              type="range"
              min="0"
              :max="maxIndex"
              :aria-label="`${assetLabel} ETF 起始日期`"
              @input="onStartInput"
            />
            <input
              v-model.number="endIndex"
              class="etf-flow-panel__range-thumb etf-flow-panel__range-thumb--end"
              type="range"
              min="0"
              :max="maxIndex"
              :aria-label="`${assetLabel} ETF 结束日期`"
              @input="onEndInput"
            />
          </div>
          <div
            class="etf-flow-panel__range-buttons"
            role="group"
            :aria-label="`${assetLabel} ETF 历史范围`"
          >
            <button type="button" :class="{ active: preset === 90 }" @click="setPreset(90)"
              >近90日</button
            >
            <button type="button" :class="{ active: preset === 365 }" @click="setPreset(365)"
              >近1年</button
            >
            <button type="button" :class="{ active: preset === null }" @click="setPreset(null)"
              >全部</button
            >
          </div>
        </div>
      </div>

      <div v-else class="etf-flow-panel__table-wrap">
        <table class="etf-flow-panel__table">
          <thead>
            <tr>
              <th class="etf-flow-panel__corner">日期</th>
              <th
                v-for="ticker in tickers"
                :key="ticker"
                :class="{ 'is-total': ticker === 'Total' }"
              >
                {{ ticker }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="day in displayDays" :key="day.date">
              <th class="etf-flow-panel__date">{{ formatDate(day.date) }}</th>
              <td
                v-for="ticker in tickers"
                :key="ticker"
                :class="[
                  'etf-flow-panel__cell',
                  flowClass(day.flows[ticker]),
                  { 'is-total': ticker === 'Total' },
                ]"
              >
                {{ formatFlow(day.flows[ticker]) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue';

  import {
    getCryptoEtfFlow,
    type CryptoEtfAsset,
    type CryptoEtfFlowData,
  } from '@/api/hedgeResearch';

  const props = withDefaults(defineProps<{ asset?: CryptoEtfAsset }>(), {
    asset: 'btc',
  });

  const loading = ref(true);
  const error = ref('');
  const data = ref<CryptoEtfFlowData | null>(null);
  const mode = ref<'chart' | 'table'>('chart');

  const tickers = computed(() => data.value?.tickers ?? []);
  const days = computed(() => data.value?.days ?? []);
  const displayDays = computed(() => days.value.slice(-14).reverse());
  const assetLabel = computed(() => (props.asset === 'eth' ? 'ETH' : 'BTC'));
  const flowUnit = computed(() => data.value?.flowUnit || assetLabel.value);
  const startIndex = ref(0);
  const endIndex = ref(0);
  const preset = ref<number | null>(null);
  const maxIndex = computed(() => Math.max(0, days.value.length - 1));
  const rangeStartPercent = computed(() =>
    maxIndex.value ? (startIndex.value / maxIndex.value) * 100 : 0,
  );
  const rangeEndPercent = computed(() =>
    maxIndex.value ? (endIndex.value / maxIndex.value) * 100 : 100,
  );
  const overviewPoints = computed(() => {
    const values = days.value.map((day) => Number(day.totalFlow ?? day.flows.Total ?? 0) || 0);
    const finite = values.filter(Number.isFinite);
    if (!finite.length) return '';
    const min = Math.min(...finite);
    const max = Math.max(...finite);
    return values
      .map((value, index) => {
        const x = (index / Math.max(values.length - 1, 1)) * 100;
        const y = max === min ? 10 : 18 - ((value - min) / (max - min)) * 16;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ');
  });

  watch(
    () => [days.value.length, days.value.at(-1)?.date],
    () => {
      const max = maxIndex.value;
      if (preset.value != null) {
        endIndex.value = max;
        startIndex.value = Math.max(0, max - preset.value + 1);
      } else {
        endIndex.value = max;
        startIndex.value = 0;
      }
    },
    { immediate: true },
  );

  const visibleDays = computed(() => days.value.slice(startIndex.value, endIndex.value + 1));

  const chart = computed(() => {
    const width = 920;
    const height = 310;
    const pad = { left: 54, right: 74, top: 18, bottom: 38 };
    const innerWidth = width - pad.left - pad.right;
    const innerHeight = height - pad.top - pad.bottom;
    const flowRows = visibleDays.value.map((day) => ({
      date: day.date,
      value: Number(day.totalFlow ?? day.flows.Total ?? 0) || 0,
      price: day.price == null ? null : Number(day.price),
    }));
    const maxAbs = Math.max(1, ...flowRows.map((row) => Math.abs(row.value)));
    const y = (value: number) =>
      pad.top + innerHeight / 2 - (value / maxAbs) * (innerHeight / 2 - 8);
    const priced = flowRows.filter(
      (row): row is typeof row & { price: number } =>
        row.price != null && Number.isFinite(row.price),
    );
    // A partial overlay creates detached, misleading price segments. Only
    // render the right-axis line when the shared strategy archive covers most
    // of the ETF window; unavailable history must remain unavailable.
    const hasPriceAxis = priced.length > 0;
    const hasPriceLine = priced.length >= 10 && priced.length / Math.max(flowRows.length, 1) >= 0.6;
    const visiblePrices = hasPriceAxis ? priced : [];
    const rawPriceMin = priced.length ? Math.min(...priced.map((row) => row.price)) : 0;
    const rawPriceMax = priced.length ? Math.max(...priced.map((row) => row.price)) : 1;
    const pricePadding = Math.max((rawPriceMax - rawPriceMin) * 0.08, rawPriceMax * 0.01, 0.01);
    const priceMin = Math.max(0, rawPriceMin - pricePadding);
    const priceMax = rawPriceMax + pricePadding;
    const priceSpan = Math.max(priceMax - priceMin, 0.01);
    const priceY = (value: number) =>
      pad.top + innerHeight - ((value - priceMin) / priceSpan) * innerHeight;
    const x = (index: number) =>
      pad.left +
      (flowRows.length <= 1 ? innerWidth / 2 : (index / (flowRows.length - 1)) * innerWidth);
    const barWidth = Math.max(1.5, Math.min(8, (innerWidth / Math.max(flowRows.length, 1)) * 0.7));
    // Scale daily bars against their own range so small net flows remain
    // visible beside the independent price axis.
    const flowMaxAbs = Math.max(1, ...flowRows.map((row) => Math.abs(row.value)));
    const flowBarHeight = Math.max(24, innerHeight * 0.34);
    const bars = flowRows.map((row, index) => {
      const zeroY = y(0);
      const yValue = zeroY - (row.value / flowMaxAbs) * flowBarHeight;
      return {
        date: row.date,
        value: row.value,
        x: x(index) - barWidth / 2,
        y: Math.min(yValue, zeroY),
        width: barWidth,
        height: Math.max(1, Math.abs(zeroY - yValue)),
      };
    });
    let previousPrice = false;
    const priceLine = hasPriceLine
      ? flowRows
          .map((row, index) => {
            if (!hasPriceLine || row.price == null || !Number.isFinite(row.price)) {
              previousPrice = false;
              return '';
            }
            const command = previousPrice ? 'L' : 'M';
            previousPrice = true;
            return `${command} ${x(index).toFixed(2)} ${priceY(row.price).toFixed(2)}`;
          })
          .filter(Boolean)
          .join(' ')
      : '';
    const tickValues = [-maxAbs, -maxAbs / 2, 0, maxAbs / 2, maxAbs];
    const yTicks = tickValues.map((value) => ({ value, y: y(value), label: formatCompact(value) }));
    const priceTicks = hasPriceAxis
      ? Array.from({ length: 5 }, (_, index) => {
          const value = priceMin + (priceSpan * index) / 4;
          return { value, y: priceY(value), label: formatPrice(value) };
        })
      : [];
    const xTicks = flowRows.length
      ? Array.from({ length: Math.min(7, flowRows.length) }, (_, index) => {
          const rowIndex = Math.round(
            (index * (flowRows.length - 1)) / Math.max(1, Math.min(6, flowRows.length - 1)),
          );
          return { x: x(rowIndex), label: flowRows[rowIndex].date.slice(5) };
        })
      : [];
    const lastPrice = visiblePrices.at(-1)?.price ?? null;
    return {
      width,
      height,
      pad,
      bars,
      yTicks,
      priceTicks,
      xTicks,
      zeroY: y(0),
      priceLine,
      hasPriceAxis,
      hasPriceLine,
      lastPrice,
      priceLabelY: lastPrice == null ? pad.top : priceY(lastPrice) - 8,
    };
  });

  function formatDate(iso?: string): string {
    if (!iso) return '—';
    const [, m, d] = iso.split('-');
    return `${Number(m)}/${Number(d)}`;
  }

  function setPreset(size: number | null) {
    preset.value = size;
    endIndex.value = maxIndex.value;
    startIndex.value = size == null ? 0 : Math.max(0, maxIndex.value - size + 1);
  }

  function onStartInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    if (!Number.isFinite(value)) return;
    preset.value = null;
    startIndex.value = Math.min(value, Math.max(0, endIndex.value - 1));
  }

  function onEndInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    if (!Number.isFinite(value)) return;
    preset.value = null;
    endIndex.value = Math.max(value, Math.min(maxIndex.value, startIndex.value + 1));
  }

  function formatFlow(value: number | null | undefined): string {
    if (value == null) return '—';
    if (Math.abs(value) < 0.05) return '0.0';
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}`;
  }

  function formatCompact(value: number): string {
    const absolute = Math.abs(value);
    const formatted = absolute >= 1000 ? `${(absolute / 1000).toFixed(1)}k` : absolute.toFixed(0);
    return `${value < 0 ? '-' : value > 0 ? '+' : ''}${formatted}`;
  }

  function formatPrice(value: number): string {
    if (!Number.isFinite(value)) return '—';
    return value >= 1000
      ? value.toLocaleString('en-US', { maximumFractionDigits: 0 })
      : value.toFixed(2);
  }

  function flowClass(value: number | null | undefined): string {
    if (value == null) return 'is-na';
    if (value > 0.05) return 'is-inflow';
    if (value < -0.05) return 'is-outflow';
    return 'is-flat';
  }

  onMounted(async () => {
    try {
      const response = await getCryptoEtfFlow(props.asset);
      data.value = response.data;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'ETF 资金流数据获取失败';
    } finally {
      loading.value = false;
    }
  });
</script>

<style scoped lang="less">
  .etf-flow-panel {
    min-height: 180px;
    padding: 6px 2px;
  }

  .etf-flow-panel__state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 160px;
    color: var(--strategy-text-faint, #667085);
    font-size: 13px;
  }

  .etf-flow-panel__state--error {
    color: var(--strategy-danger, #df4d4d);
  }

  .etf-flow-panel__body {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .etf-flow-panel__header {
    display: flex;
    align-items: flex-start;
    justify-content: flex-end;
    gap: 16px;
  }

  .etf-flow-panel__mode {
    display: inline-flex;
    flex: 0 0 auto;
    overflow: hidden;
    border: 1px solid var(--strategy-border, #dfe7f0);
    border-radius: 9px;
    background: var(--strategy-surface-muted, #f5f8fc);
  }

  .etf-flow-panel__mode button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 30px;
    padding: 0;
    border: 0;
    border-right: 1px solid var(--strategy-border, #dfe7f0);
    background: transparent;
    color: var(--strategy-text-faint, #667085);
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }

  .etf-flow-panel__mode button:last-child {
    border-right: 0;
  }

  .etf-flow-panel__mode button.is-active {
    background: var(--strategy-accent-soft, #eaf1ff);
    color: var(--strategy-accent-strong, #315bb8);
  }

  .etf-flow-panel__mode svg {
    width: 14px;
    height: 14px;
    stroke-width: 1.35;
    stroke-linecap: round;
    stroke: currentcolor;
    fill: none;
    stroke-linejoin: round;
  }

  .etf-flow-panel__chart-wrap {
    overflow: hidden;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 10px;
    background: var(--strategy-surface, #fff);
  }

  .etf-flow-panel__chart {
    display: block;
    width: 100%;
    min-height: 250px;
    padding: 6px 8px 0;
  }

  .etf-flow-panel__grid {
    stroke-width: 1;
    stroke: var(--strategy-border-soft, #edf2f7);
  }

  .etf-flow-panel__zero {
    stroke-width: 1;
    stroke-dasharray: 4 4;
    stroke: var(--strategy-border-strong, #c9d4e2);
  }

  .etf-flow-panel__axis {
    fill: var(--strategy-text-faint, #667085);
    font-size: 11px;
  }

  .etf-flow-panel__axis--price {
    fill: #7c3aed;
  }

  .etf-flow-panel__bar {
    opacity: 0.72;
    fill: var(--strategy-accent, #3b82c4);
  }

  .etf-flow-panel__bar.is-outflow {
    fill: var(--strategy-success, #189b50);
  }

  .etf-flow-panel__price-line {
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke: #7c3aed;
    fill: none;
    stroke-linejoin: round;
    vector-effect: non-scaling-stroke;
  }

  .etf-flow-panel__price-label {
    fill: #7c3aed;
    font-size: 11px;
    font-weight: 700;
  }

  .etf-flow-panel__chart-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 0 14px 10px;
    color: var(--strategy-text-faint, #667085);
    font-size: 11px;
  }

  .etf-flow-panel__chart-legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .etf-flow-panel__chart-legend i {
    width: 9px;
    height: 9px;
    border-radius: 2px;
  }

  .etf-flow-panel__chart-legend i.is-flow {
    background: var(--strategy-accent, #3b82c4);
  }

  .etf-flow-panel__chart-legend i.is-price {
    border-radius: 50%;
    background: #7c3aed;
  }

  .etf-flow-panel__range {
    display: grid;
    gap: 5px;
    margin: 0 14px 12px;
  }

  .etf-flow-panel__range-labels {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    min-height: 14px;
    overflow: hidden;
    color: var(--strategy-text-faint, #7b8da4);
    font-size: 10px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .etf-flow-panel__range-viewport {
    position: relative;
    height: 24px;
    overflow: hidden;
  }

  .etf-flow-panel__range-viewport svg {
    position: absolute;
    inset: 1px 0;
    width: 100%;
    height: calc(100% - 2px);
    pointer-events: none;
  }

  .etf-flow-panel__range-viewport polyline {
    stroke-width: 1.2;
    stroke-linecap: round;
    stroke: rgb(137 167 233 / 80%);
    fill: none;
    stroke-linejoin: round;
  }

  .etf-flow-panel__range-rail,
  .etf-flow-panel__range-selection {
    position: absolute;
    top: 50%;
    height: 12px;
    transform: translateY(-50%);
    border-radius: 999px;
  }

  .etf-flow-panel__range-rail {
    right: 0;
    left: 0;
    border: 1px solid rgb(192 205 227 / 92%);
    background: rgb(225 235 252 / 30%);
    box-shadow: inset 0 1px 1px rgb(255 255 255 / 72%);
  }

  .etf-flow-panel__range-selection {
    left: var(--range-start);
    width: max(4%, calc(var(--range-end) - var(--range-start)));
    border: 1px solid rgb(142 171 235 / 88%);
    background: rgb(202 218 251 / 45%);
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 35%);
    pointer-events: none;
  }

  .etf-flow-panel__range-thumb {
    position: absolute;
    z-index: 2;
    top: 0;
    left: 0;
    width: 100%;
    height: 24px;
    margin: 0;
    appearance: none;
    background: transparent;
    pointer-events: none;
  }

  .etf-flow-panel__range-thumb::-webkit-slider-runnable-track {
    height: 12px;
    background: transparent;
  }

  .etf-flow-panel__range-thumb::-moz-range-track {
    height: 12px;
    background: transparent;
  }

  .etf-flow-panel__range-thumb::-webkit-slider-thumb {
    width: 6px;
    height: 14px;
    margin-top: -1px;
    appearance: none;
    border: 1px solid rgb(146 171 230 / 90%);
    border-radius: 999px;
    background: #fff;
    box-shadow: 0 1px 2px rgb(124 145 186 / 20%);
    cursor: ew-resize;
    pointer-events: auto;
  }

  .etf-flow-panel__range-thumb::-moz-range-thumb {
    width: 6px;
    height: 14px;
    border: 1px solid rgb(146 171 230 / 90%);
    border-radius: 999px;
    background: #fff;
    box-shadow: 0 1px 2px rgb(124 145 186 / 20%);
    cursor: ew-resize;
    pointer-events: auto;
  }

  .etf-flow-panel__range-thumb--start {
    z-index: 3;
  }

  .etf-flow-panel__range-buttons {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
  }

  .etf-flow-panel__range-buttons button {
    padding: 4px 8px;
    border: 1px solid var(--strategy-border, #d9e3ee);
    border-radius: 5px;
    background: transparent;
    color: var(--strategy-text-2, #354d68);
    font-size: 12px;
    cursor: pointer;
  }

  .etf-flow-panel__range-buttons button.active {
    border-color: #c9dbf7;
    background: var(--strategy-accent-soft, #eaf2ff);
    color: var(--strategy-accent, #1d4ed8);
  }

  .etf-flow-panel__table-wrap {
    overflow-x: auto;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 10px;
  }

  .etf-flow-panel__table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  .etf-flow-panel__table th,
  .etf-flow-panel__table td {
    padding: 7px 9px;
    border-bottom: 1px solid var(--strategy-border-soft, #edf2f7);
    text-align: right;
  }

  .etf-flow-panel__table thead th {
    position: sticky;
    top: 0;
    background: var(--strategy-table-head-bg, #f7f9fc);
    color: var(--strategy-text-2, #2f3e52);
    font-weight: 700;
  }

  .etf-flow-panel__table thead th.is-total {
    color: var(--strategy-accent-strong, #c94848);
  }

  .etf-flow-panel__table tbody tr:last-child th,
  .etf-flow-panel__table tbody tr:last-child td {
    border-bottom: none;
  }

  .etf-flow-panel__corner,
  .etf-flow-panel__date {
    position: sticky;
    z-index: 1;
    left: 0;
    background: var(--strategy-surface-muted, #f5f8fc);
    color: var(--strategy-text-2, #2f3e52);
    font-weight: 700;
    text-align: left !important;
  }

  .etf-flow-panel__cell {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
  }

  .etf-flow-panel__cell.is-total {
    border-left: 1px solid var(--strategy-border-strong, #d7e0ec);
    font-weight: 800;
  }

  .etf-flow-panel__cell.is-inflow {
    color: var(--strategy-accent-strong, #c94848);
  }

  .etf-flow-panel__cell.is-outflow {
    color: var(--strategy-success, #189b50);
  }

  .etf-flow-panel__cell.is-flat {
    color: var(--strategy-text-faint, #667085);
  }

  .etf-flow-panel__cell.is-na {
    color: var(--strategy-border-strong, #d7e0ec);
  }

  @media (max-width: 640px) {
    .etf-flow-panel__header {
      flex-direction: column;
    }

    .etf-flow-panel__mode {
      align-self: flex-end;
    }
  }
</style>
