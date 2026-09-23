<template>
  <div class="cftc-panel">
    <div class="cftc-toolbar">
      <div>
        <p class="cftc-eyebrow">COT REPORT · WEEKLY</p>
        <p class="cftc-note"
          >CFTC PRE Disaggregated Futures Only；报告日通常滞后一周，不代表实时资金流。</p
        >
      </div>
      <div class="cftc-tabs" role="tablist" aria-label="CFTC 合约市场">
        <button
          v-for="market in markets"
          :key="market.key"
          type="button"
          role="tab"
          :aria-selected="selectedKey === market.key"
          :class="{ active: selectedKey === market.key }"
          @click="selectedKey = market.key"
        >
          {{ market.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="cftc-empty">正在读取已落库的 CFTC 序列…</div>
    <div v-else-if="error" class="cftc-empty cftc-empty--error">{{ error }}</div>
    <div v-else-if="!selectedMarket" class="cftc-empty">当前没有可用的 CFTC 观测。</div>
    <template v-else>
      <div class="cftc-summary">
        <div class="cftc-summary__headline">
          <strong>{{ selectedMarket.label }}</strong>
          <span>{{ latestDate || '报告日未知' }}</span>
        </div>
        <div class="cftc-kpis">
          <article>
            <span>Managed Money 净头寸</span>
            <b :class="tone(managedMoneyNet)">{{ signed(managedMoneyNet) }}</b>
          </article>
          <article>
            <span>Producer / Merchant 净头寸</span>
            <b :class="tone(producerNet)">{{ signed(producerNet) }}</b>
          </article>
          <article>
            <span>Managed Money 历史分位</span>
            <b>{{ percentile == null ? '—' : `${percentile.toFixed(1)}%` }}</b>
          </article>
        </div>
      </div>

      <div class="cftc-chart-shell">
        <svg
          viewBox="0 0 960 220"
          role="img"
          :aria-label="`${selectedMarket.label} CFTC 净头寸历史`"
        >
          <line
            v-for="tick in ticks"
            :key="tick"
            x1="48"
            x2="936"
            :y1="y(tick)"
            :y2="y(tick)"
            class="grid"
          />
          <line x1="48" x2="936" :y1="y(0)" :y2="y(0)" class="zero" />
          <text
            v-for="tick in ticks"
            :key="`label-${tick}`"
            x="40"
            :y="y(tick) + 4"
            text-anchor="end"
            class="axis"
          >
            {{ compact(tick) }}
          </text>
          <path v-if="managedPath" :d="managedPath" class="line line--managed" />
          <path v-if="producerPath" :d="producerPath" class="line line--producer" />
          <text x="52" y="210" class="axis">{{ firstDate || '—' }}</text>
          <text x="932" y="210" text-anchor="end" class="axis">{{ latestDate || '—' }}</text>
        </svg>
        <div class="cftc-legend">
          <span><i class="dot dot--managed"></i>Managed Money 净头寸</span>
          <span><i class="dot dot--producer"></i>Producer / Merchant 净头寸</span>
        </div>
      </div>

      <div class="cftc-table-wrap">
        <table>
          <thead
            ><tr
              ><th>市场</th><th>报告日</th><th>Managed Money</th><th>Producer / Merchant</th
              ><th>历史分位</th></tr
            ></thead
          >
          <tbody>
            <tr v-for="row in rows" :key="row.key">
              <td>{{ row.label }}</td>
              <td>{{ row.date || '—' }}</td>
              <td :class="tone(row.managed)">{{ signed(row.managed) }}</td>
              <td :class="tone(row.producer)">{{ signed(row.producer) }}</td>
              <td>{{ row.percentile == null ? '—' : `${row.percentile.toFixed(1)}%` }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { getCommodityDashboardV1, type MacroDashboardSeries } from '@/api/hedgeResearch';

  type MarketKey = 'gold' | 'silver' | 'copper' | 'wti' | 'naturalGas';
  type MarketConfig = { key: MarketKey; label: string; net: string; percentile: string };
  type Row = {
    key: MarketKey;
    label: string;
    date: string | null;
    managed: number | null;
    producer: number | null;
    percentile: number | null;
  };

  const markets: MarketConfig[] = [
    { key: 'gold', label: '黄金', net: 'cftcGoldNet', percentile: 'cftcGoldPercentile' },
    { key: 'silver', label: '白银', net: 'cftcSilverNet', percentile: 'cftcSilverPercentile' },
    { key: 'copper', label: '铜', net: 'cftcCopperNet', percentile: 'cftcCopperPercentile' },
    { key: 'wti', label: 'WTI', net: 'cftcWtiNet', percentile: 'cftcWtiPercentile' },
    {
      key: 'naturalGas',
      label: '天然气',
      net: 'cftcNaturalGasNet',
      percentile: 'cftcNaturalGasPercentile',
    },
  ];
  const selectedKey = ref<MarketKey>('gold');
  const groups = ref<Record<string, MacroDashboardSeries[]>>({});
  const loading = ref(true);
  const error = ref('');

  const config = computed(() => markets.find((market) => market.key === selectedKey.value)!);
  const netSeries = computed(() => groups.value[config.value.net] ?? []);
  const percentileSeries = computed(() => groups.value[config.value.percentile]?.[0] ?? null);
  const managedSeries = computed(
    () =>
      netSeries.value.find((item) => item.seriesId.includes('managed_money')) ?? netSeries.value[0],
  );
  const producerSeries = computed(
    () => netSeries.value.find((item) => item.seriesId.includes('producer_merchant')) ?? null,
  );
  const latest = (series: MacroDashboardSeries | undefined) => {
    const points = (series?.observations ?? []).filter((point) =>
      Number.isFinite(Number(point.value)),
    );
    return points.length ? points[points.length - 1] : null;
  };
  const managedMoneyNet = computed(() => number(latest(managedSeries.value)?.value));
  const producerNet = computed(() => number(latest(producerSeries.value)?.value));
  const percentile = computed(() => number(latest(percentileSeries.value)?.value));
  const latestDate = computed(() => latest(managedSeries.value)?.date ?? null);
  const firstDate = computed(
    () =>
      managedSeries.value?.observations?.find((point) => Number.isFinite(Number(point.value)))
        ?.date ?? null,
  );
  const selectedMarket = computed(() => (managedSeries.value ? config.value : null));
  const rows = computed<Row[]>(() =>
    markets
      .map((market) => {
        const net = groups.value[market.net] ?? [];
        const managed = net.find((item) => item.seriesId.includes('managed_money')) ?? net[0];
        const producer = net.find((item) => item.seriesId.includes('producer_merchant'));
        const pct = groups.value[market.percentile]?.[0];
        return {
          key: market.key,
          label: market.label,
          date: latest(managed)?.date ?? null,
          managed: number(latest(managed)?.value),
          producer: number(latest(producer)?.value),
          percentile: number(latest(pct)?.value),
        };
      })
      .filter((row) => row.managed != null || row.producer != null || row.percentile != null),
  );

  const values = computed(() =>
    [...(managedSeries.value?.observations ?? []), ...(producerSeries.value?.observations ?? [])]
      .map((point) => Number(point.value))
      .filter(Number.isFinite),
  );
  const minValue = computed(() => (values.value.length ? Math.min(...values.value, 0) : -1));
  const maxValue = computed(() => (values.value.length ? Math.max(...values.value, 0) : 1));
  const ticks = computed(() =>
    Array.from(
      { length: 5 },
      (_, index) => minValue.value + ((maxValue.value - minValue.value) * index) / 4,
    ),
  );
  const y = (value: number) =>
    24 + ((maxValue.value - value) / Math.max(maxValue.value - minValue.value, 1)) * 156;
  const path = (series: MacroDashboardSeries | undefined) => {
    const points = (series?.observations ?? [])
      .filter((point) => Number.isFinite(Number(point.value)))
      .slice(-156);
    if (points.length < 2) return '';
    return points
      .map(
        (point, index) =>
          `${index ? 'L' : 'M'}${48 + (index / (points.length - 1)) * 888},${y(
            Number(point.value),
          )}`,
      )
      .join(' ');
  };
  const managedPath = computed(() => path(managedSeries.value));
  const producerPath = computed(() => path(producerSeries.value ?? undefined));
  const number = (value: string | number | null | undefined) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const signed = (value: number | null) =>
    value == null ? '—' : `${value > 0 ? '+' : ''}${Math.round(value).toLocaleString('en-US')}`;
  const compact = (value: number) =>
    Math.abs(value) >= 1000 ? `${(value / 1000).toFixed(0)}k` : Math.round(value).toString();
  const tone = (value: number | null) =>
    value == null ? '' : value > 0 ? 'positive' : value < 0 ? 'negative' : '';

  onMounted(async () => {
    try {
      const dashboard = await getCommodityDashboardV1();
      groups.value = dashboard.groups;
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : 'CFTC 数据暂不可用';
    } finally {
      loading.value = false;
    }
  });
</script>

<style scoped lang="less">
  .cftc-panel {
    padding: 4px 2px 0;
    color: var(--hedge-cool-text, #18313c);
  }

  .cftc-toolbar,
  .cftc-summary__headline,
  .cftc-legend {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .cftc-eyebrow {
    margin: 0 0 3px;
    color: #8a9baa;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  .cftc-note {
    margin: 0;
    color: #718596;
    font-size: 12px;
  }

  .cftc-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .cftc-tabs button {
    padding: 5px 11px;
    border: 1px solid #d9e3eb;
    border-radius: 999px;
    background: #fff;
    color: #5f7484;
    font-size: 12px;
    cursor: pointer;
  }

  .cftc-tabs button.active {
    border-color: #165dff;
    background: #eef4ff;
    color: #165dff;
    font-weight: 700;
  }

  .cftc-summary {
    margin-top: 16px;
    border: 1px solid #e0e8ef;
    border-radius: 12px;
    background: #f8fafc;
  }

  .cftc-summary__headline {
    padding: 10px 14px;
    border-bottom: 1px solid #e0e8ef;
  }

  .cftc-summary__headline strong {
    font-size: 15px;
  }

  .cftc-summary__headline span {
    color: #8193a1;
    font-size: 12px;
  }

  .cftc-kpis {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: #e0e8ef;
  }

  .cftc-kpis article {
    display: grid;
    gap: 4px;
    padding: 11px 14px;
    background: #f8fafc;
  }

  .cftc-kpis span {
    color: #8193a1;
    font-size: 11px;
  }

  .cftc-kpis b {
    font-size: 18px;
    font-variant-numeric: tabular-nums;
  }

  .cftc-chart-shell {
    margin-top: 14px;
    padding: 9px 12px 7px;
    border: 1px solid #e0e8ef;
    border-radius: 12px;
    background: #fff;
  }

  .cftc-chart-shell svg {
    display: block;
    width: 100%;
    height: 220px;
  }

  .grid {
    stroke-width: 1;
    stroke: #edf2f6;
  }

  .zero {
    stroke-dasharray: 4 4;
    stroke: #cbd7e1;
  }

  .axis {
    fill: #8a9baa;
    font-size: 11px;
  }

  .line {
    stroke-width: 2.2;
    stroke-linecap: round;
    fill: none;
    stroke-linejoin: round;
    vector-effect: non-scaling-stroke;
  }

  .line--managed {
    stroke: #165dff;
  }

  .line--producer {
    stroke: #d18b1f;
  }

  .cftc-legend {
    flex-wrap: wrap;
    justify-content: flex-start;
    padding: 3px 3px 0;
    color: #718596;
    font-size: 11px;
  }

  .cftc-legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .dot--managed {
    background: #165dff;
  }

  .dot--producer {
    background: #d18b1f;
  }

  .cftc-table-wrap {
    margin-top: 14px;
    overflow-x: auto;
    border: 1px solid #e0e8ef;
    border-radius: 12px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 9px 12px;
    border-bottom: 1px solid #edf2f6;
    text-align: right;
    white-space: nowrap;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  th {
    background: #f8fafc;
    color: #8193a1;
    font-size: 11px;
    font-weight: 700;
  }

  tbody tr:last-child td {
    border-bottom: 0;
  }

  td {
    font-variant-numeric: tabular-nums;
  }

  .positive {
    color: #d14343;
  }

  .negative {
    color: #148b6a;
  }

  .cftc-empty {
    padding: 56px 16px;
    color: #8193a1;
    text-align: center;
  }

  .cftc-empty--error {
    color: #c24141;
  }

  @media (max-width: 700px) {
    .cftc-toolbar {
      flex-direction: column;
      align-items: flex-start;
    }

    .cftc-kpis {
      grid-template-columns: 1fr;
    }
  }
</style>
