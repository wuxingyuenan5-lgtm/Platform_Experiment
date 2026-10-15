<template>
  <div class="vibe-trend-charts">
    <VibeTimeChart
      title="市场涨跌结构"
      y-label="上涨/下跌家数（家）"
      right-label="涨停/跌停家数（家）"
      :dates="dates"
      :series="marketSeries"
    />
    <VibeTimeChart
      title="市场宽度"
      y-label="（上涨－下跌）/（上涨＋下跌）× 100%"
      :dates="dates"
      :series="breadthSeries"
    />
    <template v-if="crowdingRows.length">
      <VibeTimeChart
        title="通信设备 | 成交额占全A与换手率"
        y-label="成交额占全A（%）"
        right-label="换手率（%）"
        :dates="crowdingDates"
        :series="communicationSeries"
      />
      <VibeTimeChart
        title="四行业 | 成交额与成交额占比"
        y-label="成交额（亿元）"
        right-label="成交额占全A（%）"
        :dates="crowdingDates"
        :series="fourIndustrySeries"
      />
    </template>
    <VibeTimeChart
      v-if="innovationRows.length"
      title="创新药 | 成交额占全A与换手率"
      y-label="成交额占全A（%）"
      right-label="换手率（%）"
      :dates="innovationDates"
      :series="innovationSeries"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import VibeTimeChart, { type Series } from './VibeTimeChart.vue';

  interface HistoryRow {
    date: string;
    advance?: number | null;
    decline?: number | null;
    limit_up?: number | null;
    limit_down?: number | null;
    market_breadth?: number | null;
    csi300Close?: number | string | null;
  }
  type CrowdingRow = {
    date: string;
    targets?: Record<
      string,
      {
        amount100m?: number | null;
        amountShareOfA?: number | null;
        turnoverPct?: number | null;
        price?: number | null;
      }
    >;
    combined?: { amount100m?: number | null; amountShareOfA?: number | null };
  };
  type InnovationRow = {
    date: string;
    amountShareOfA?: number | null;
    turnoverPct?: number | null;
    price?: number | null;
  };
  const props = defineProps<{
    rows: HistoryRow[];
    crowdingRows?: CrowdingRow[];
    innovationRows?: InnovationRow[];
  }>();
  const dates = computed(() => props.rows.map((row) => row.date));
  const marketSeries = computed<Series[]>(() => [
    {
      name: '上涨家数',
      values: props.rows.map((row) => row.advance),
      type: 'bar',
      color: '#ef4444',
      unit: '家',
      domain: [-6000, 6000],
      ticks: [4000, 2000, 0, -2000, -4000],
    },
    {
      name: '下跌家数',
      values: props.rows.map((row) => row.decline),
      type: 'bar',
      color: '#10b981',
      sign: -1,
      unit: '家',
      domain: [-6000, 6000],
      ticks: [4000, 2000, 0, -2000, -4000],
    },
    {
      name: '涨停家数',
      values: props.rows.map((row) => row.limit_up),
      type: 'line',
      axis: 'right',
      color: '#ef4444',
      unit: '家',
      domain: [-300, 300],
      ticks: [200, 100, 0, -100, -200],
    },
    {
      name: '沪深300',
      values: props.rows.map((row) => row.csi300Close),
      type: 'line',
      axis: 'hidden-price',
      color: '#7c3aed',
      unit: '点',
      lineWidth: 3,
    },
    {
      name: '跌停家数',
      values: props.rows.map((row) => row.limit_down),
      type: 'line',
      axis: 'right',
      color: '#10b981',
      sign: -1,
      unit: '家',
      domain: [-300, 300],
      ticks: [200, 100, 0, -100, -200],
    },
  ]);
  const breadthSeries = computed<Series[]>(() => [
    {
      name: '市场宽度',
      values: props.rows.map((row) => row.market_breadth),
      type: 'line',
      color: '#123d68',
      percent: true,
      domain: [-1, 1],
      ticks: [1, 0.5, 0, -0.5, -1],
    },
  ]);
  const crowdingRows = computed(() => props.crowdingRows || []);
  const crowdingDates = computed(() => crowdingRows.value.map((row) => row.date));
  const communicationSeries = computed<Series[]>(() => [
    {
      name: '通信设备成交额占全A',
      type: 'area',
      color: '#2563eb',
      percent: true,
      values: crowdingRows.value.map((row) => row.targets?.['通信设备']?.amountShareOfA),
    },
    {
      name: '通信设备换手率',
      type: 'line',
      axis: 'right',
      color: '#ef4444',
      percent: true,
      values: crowdingRows.value.map((row) => {
        const value = row.targets?.['通信设备']?.turnoverPct;
        return value == null ? null : value / 100;
      }),
    },
    {
      name: '申万通信设备指数',
      values: crowdingRows.value.map((row) => row.targets?.['通信设备']?.price),
      type: 'line',
      axis: 'hidden-price',
      color: '#0f766e',
      unit: '点',
    },
  ]);
  const fourIndustrySeries = computed<Series[]>(() => [
    {
      name: '四行业合计成交额',
      type: 'bar',
      color: '#4f81bd',
      values: crowdingRows.value.map((row) => row.combined?.amount100m),
    },
    {
      name: '四行业成交额占全A',
      type: 'line',
      axis: 'right',
      color: '#f59e0b',
      percent: true,
      values: crowdingRows.value.map((row) => row.combined?.amountShareOfA),
    },
  ]);
  const innovationRows = computed(() => props.innovationRows || []);
  const innovationDates = computed(() => innovationRows.value.map((row) => row.date));
  const innovationSeries = computed<Series[]>(() => [
    {
      name: '创新药成交额占全A',
      type: 'area',
      color: '#2563eb',
      percent: true,
      values: innovationRows.value.map((row) => row.amountShareOfA),
    },
    {
      name: '创新药换手率',
      type: 'line',
      axis: 'right',
      color: '#f97316',
      percent: true,
      values: innovationRows.value.map((row) =>
        row.turnoverPct == null ? null : row.turnoverPct / 100,
      ),
    },
    {
      name: '创新药价格',
      type: 'line',
      axis: 'hidden-price',
      color: '#be185d',
      unit: '点',
      values: innovationRows.value.map((row) => row.price),
    },
  ]);
</script>

<style scoped>
  .vibe-trend-charts {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .vibe-trend-charts > :first-child {
    grid-column: 1 / -1;
  }

  @container ashare-overview (max-width: 1000px) {
    .vibe-trend-charts {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
