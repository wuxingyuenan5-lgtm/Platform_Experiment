<script setup lang="ts">
  import { useDashboardRefresh } from '../useDashboardRefresh';

  import { computed, shallowRef, ref } from 'vue';
  import { useElementSize } from '@vueuse/core';
  import { getCryptoDashboardV1, type MacroDashboardSeries } from '@/api/hedgeResearch';

  const plotHost = ref<HTMLElement | null>(null);
  const { width } = useElementSize(plotHost);
  const chartWidth = computed(() => Math.max(300, width.value));
  const rightEdge = computed(() => chartWidth.value - 24);
  const series = shallowRef<MacroDashboardSeries[]>([]);
  const state = ref('loading');
  const showTable = ref(false);
  const selected = ref<number | null>(null);
  const rows = computed(() =>
    series.value
      .map((item) => ({
        ...item,
        lower: Number(item.priceLower),
        upper: Number(item.priceUpper),
        value: item.latestValue == null ? null : Number(item.latestValue),
      }))
      .sort((a, b) => a.lower - b.lower),
  );
  const maxPrice = computed(() => Math.max(1, ...rows.value.map((r) => r.upper)));
  const maxSupply = computed(() => Math.max(1, ...rows.value.map((r) => r.value ?? 0)));
  const active = computed(() => (selected.value === null ? null : rows.value[selected.value]));
  const x = (price: number) => 72 + (price / maxPrice.value) * (rightEdge.value - 72);
  const y = (supply: number) => 280 - (supply / maxSupply.value) * 240;
  const number = (value: number) => value.toLocaleString('en-US', { maximumFractionDigits: 8 });
  useDashboardRefresh(async () => {
    try {
      series.value = (await getCryptoDashboardV1()).groups.urpd ?? [];
      if (
        !series.value.length ||
        rows.value.some(
          (r, i) =>
            r.priceLower == null ||
            r.priceUpper == null ||
            !Number.isFinite(r.lower) ||
            !Number.isFinite(r.upper) ||
            r.lower < 0 ||
            r.upper <= r.lower ||
            (r.value !== null && (!Number.isFinite(r.value) || r.value < 0)) ||
            (i > 0 && r.lower < rows.value[i - 1].upper),
        ) ||
        new Set(rows.value.map((r) => r.observationDate)).size !== 1
      )
        throw new Error('invalid URPD snapshot');
      state.value = 'ready';
    } catch {
      state.value = 'error';
    }
  });
</script>

<template>
  <div v-if="state !== 'ready'" class="local-empty">{{
    state === 'loading' ? '正在加载数据…' : '价格分布暂不可用。'
  }}</div>
  <div v-else ref="plotHost" class="urpd-panel">
    <div class="urpd-controls">
      <span
        >{{ rows[0].observationDate }} · BTC{{
          rows.some((r) => r.isStale) ? ' · 待更新' : ''
        }}</span
      >
      <button type="button" :aria-pressed="showTable" @click="showTable = !showTable">{{
        showTable ? '查看图表' : '查看数据'
      }}</button>
    </div>
    <div v-if="showTable" class="urpd-table">
      <table>
        <thead
          ><tr><th>价格区间（USD）</th><th>BTC 数量</th></tr></thead
        >
        <tbody
          ><tr v-for="row in rows" :key="row.seriesId"
            ><td>{{ number(row.lower) }}–{{ number(row.upper) }}</td
            ><td>{{ row.value === null ? '—' : number(row.value) }}</td></tr
          ></tbody
        >
      </table>
    </div>
    <template v-else>
      <svg :viewBox="`0 0 ${chartWidth} 330`" role="group" aria-label="UTXO 最后移动价格分布">
        <text x="72" y="20">BTC 数量</text>
        <g v-for="fraction in [0, 0.25, 0.5, 0.75, 1]" :key="fraction">
          <line
            x1="72"
            :x2="rightEdge"
            :y1="y(maxSupply * fraction)"
            :y2="y(maxSupply * fraction)"
            stroke="#e2e8f0"
          />
          <text x="62" :y="y(maxSupply * fraction) + 4" text-anchor="end">
            {{ Math.round(maxSupply * fraction).toLocaleString('en-US') }}
          </text>
          <text :x="x(maxPrice * fraction)" y="305" text-anchor="middle">
            {{ Math.round(maxPrice * fraction).toLocaleString('en-US') }}
          </text>
        </g>
        <template v-for="(row, index) in rows" :key="row.seriesId">
          <rect
            v-if="row.value !== null"
            :x="x(row.lower)"
            :y="y(row.value)"
            :width="Math.max(0.2, x(row.upper) - x(row.lower) - 0.5)"
            :height="280 - y(row.value)"
            :fill="selected === index ? '#165dff' : '#5895c9'"
            tabindex="0"
            :aria-label="`${row.label}: ${number(row.value)} BTC`"
            @mouseenter="selected = index"
            @focus="selected = index"
            @mouseleave="selected = null"
            @blur="selected = null"
          >
            <title>{{ row.label }} · {{ number(row.value) }} BTC</title>
          </rect>
        </template>
        <text :x="rightEdge" y="326" text-anchor="end">最后移动时价格（USD）</text>
      </svg>
      <div class="urpd-detail" aria-live="polite">{{
        active
          ? `${active.label} · ${active.value === null ? '—' : number(active.value)} BTC`
          : '按价格区间查看 BTC 数量'
      }}</div>
    </template>
    <small
      ><a :href="rows[0].sourceUrl || undefined" target="_blank" rel="noopener noreferrer"
        >BGeometrics</a
      >
      · UTXO 最后移动时价格，不等同于投资者实际买入成本。</small
    >
  </div>
</template>

<style scoped>
  .urpd-panel {
    display: grid;
    box-sizing: border-box;
    width: 100%;
    padding: 12px 20px;
    gap: 10px;
  }

  .urpd-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #64748b;
    font-size: 12px;
  }

  button {
    padding: 5px 10px;
    border: 1px solid #dbe4ea;
    border-radius: 7px;
    background: white;
    cursor: pointer;
  }

  svg {
    width: 100%;
    overflow: visible;
  }

  svg text {
    fill: #64748b;
    font-size: 12px;
  }

  .urpd-detail {
    min-height: 20px;
    color: #334155;
    font-size: 12px;
  }

  .urpd-table {
    max-height: 330px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 6px;
    border-bottom: 1px solid #eef2f6;
    text-align: right;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  small {
    color: #64748b;
  }
</style>
