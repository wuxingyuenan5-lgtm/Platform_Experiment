<template>
  <section class="statistics-section">
    <div class="section-head">
      <div>
        <h3>统计分析</h3>
      </div>
    </div>

    <div class="statistics-grid">
      <article class="stats-card stats-card--summary">
        <header class="stats-card__header">
          <span>区间统计</span>
          <div class="stats-card__controls">
            <label class="chart-select chart-select--plain">
              <select :value="progressLevel" @change="emitInput('progressLevel', $event)">
                <option value="15min">15min</option>
                <option value="1h">1h</option>
                <option value="4h">4h</option>
                <option value="日线">日线</option>
              </select>
            </label>
            <input :value="startDate" type="date" @input="emitInput('startDate', $event)" />
            <input :value="endDate" type="date" @input="emitInput('endDate', $event)" />
          </div>
        </header>
        <div class="stats-kpi-grid">
          <div v-for="item in statsRows" :key="item.label" class="stats-kpi">
            <span>{{ item.label }}</span>
            <strong :class="item.tone">{{ item.value }}</strong>
          </div>
        </div>
        <div ref="distributionRef" class="mini-chart"></div>
      </article>

      <article class="stats-card">
        <header>季节图表</header>
        <div ref="seasonalRef" class="seasonal-chart"></div>
      </article>

      <article class="stats-card">
        <header>月度热力矩阵</header>
        <div class="heatmap-table">
          <div class="heatmap-row heatmap-head">
            <span>年份</span>
            <span v-for="month in monthLabels" :key="month">{{ month }}</span>
          </div>
          <div v-for="row in heatmapRows" :key="row.year" class="heatmap-row">
            <span class="heatmap-year">{{ row.year }}</span>
            <span
              v-for="cell in row.cells"
              :key="`${row.year}-${cell.month}`"
              class="heatmap-cell"
              :class="cell.value > 0 ? 'is-warm' : 'is-cold'"
            >
              {{ cell.value > 0 ? '+' : '' }}{{ cell.value.toFixed(2) }}%
            </span>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { onMounted, ref, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';

  type ProgressLevel = '15min' | '1h' | '4h' | '日线';

  defineProps<{
    progressLevel: ProgressLevel;
    startDate: string;
    endDate: string;
  }>();

  const emit = defineEmits<{
    (event: 'update:progressLevel', value: ProgressLevel): void;
    (event: 'update:startDate', value: string): void;
    (event: 'update:endDate', value: string): void;
  }>();

  const distributionRef = ref<HTMLDivElement | null>(null);
  const seasonalRef = ref<HTMLDivElement | null>(null);
  const distributionChart = useECharts(distributionRef as Ref<HTMLDivElement>);
  const seasonalChart = useECharts(seasonalRef as Ref<HTMLDivElement>);

  const monthLabels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

  const statsRows = [
    { label: '最新值', value: '17.30', tone: 'is-positive' },
    { label: '均值', value: '13.57', tone: 'is-neutral' },
    { label: '中位数', value: '14.02', tone: 'is-neutral' },
    { label: '标准差', value: '4.86', tone: 'is-neutral' },
    { label: '百分位', value: '89%', tone: 'is-positive' },
    { label: '区间振幅', value: '12.00', tone: 'is-negative' },
  ] as const;

  const distributionBins = ['-8', '-4', '0', '8', '15', '23', '30', '38', '45', '60'];
  const distributionValues = [3, 7, 11, 18, 44, 22, 10, 6, 4, 2];

  const seasonalYears = ['2022', '2023', '2024', '2025', '2026'];
  const seasonalSeries = {
    '2022': [2.76, 2.74, 2.69, 2.67, 2.71, 2.72, 2.75, 2.77, 2.73, 2.69, 2.66, 2.61],
    '2023': [2.81, 2.82, 2.8, 2.77, 2.74, 2.71, 2.68, 2.64, 2.62, 2.65, 2.7, 2.73],
    '2024': [2.77, 2.68, 2.62, 2.58, 2.57, 2.55, 2.51, 2.47, 2.44, 2.42, 2.39, 2.35],
    '2025': [1.65, 1.71, 1.85, 1.78, 1.81, 1.79, 1.88, 1.92, 1.95, 1.97, 1.99, 2.02],
    '2026': [2.29, 2.24, 2.22, 2.18, 2.16, 2.14, 2.11, 2.07, 2.03, 1.99, 1.76, 1.73],
  };

  const heatmapRows = [
    { year: '2026', cells: [{ month: 1, value: -2.65 }, { month: 2, value: 0.11 }, { month: 3, value: 0.44 }, { month: 4, value: 3.59 }, { month: 5, value: -2.23 }, { month: 6, value: 1.85 }, { month: 7, value: 0 }, { month: 8, value: 0 }, { month: 9, value: 0 }, { month: 10, value: 0 }, { month: 11, value: 0 }, { month: 12, value: 0 }] },
    { year: '2025', cells: [{ month: 1, value: -2.94 }, { month: 2, value: -6.97 }, { month: 3, value: 4.63 }, { month: 4, value: -10.32 }, { month: 5, value: 3.33 }, { month: 6, value: -1.55 }, { month: 7, value: 3.43 }, { month: 8, value: 4.37 }, { month: 9, value: 0.17 }, { month: 10, value: 0.53 }, { month: 11, value: 2.04 }, { month: 12, value: 1.15 }] },
    { year: '2024', cells: [{ month: 1, value: -4.77 }, { month: 2, value: -3.37 }, { month: 3, value: -2.49 }, { month: 4, value: 0.44 }, { month: 5, value: 0.59 }, { month: 6, value: -3.58 }, { month: 7, value: -3.94 }, { month: 8, value: 0.93 }, { month: 9, value: -0.35 }, { month: 10, value: -1.37 }, { month: 11, value: -4.84 }, { month: 12, value: -17.83 }] },
    { year: '2023', cells: [{ month: 1, value: 2.1 }, { month: 2, value: 0.47 }, { month: 3, value: -2.01 }, { month: 4, value: -2.68 }, { month: 5, value: -2.56 }, { month: 6, value: -2.5 }, { month: 7, value: 0.85 }, { month: 8, value: -2.74 }, { month: 9, value: 3.5 }, { month: 10, value: 0.37 }, { month: 11, value: -0.15 }, { month: 12, value: -4.79 }] },
    { year: '均值', cells: [{ month: 1, value: -2.21 }, { month: 2, value: 1.48 }, { month: 3, value: 0.06 }, { month: 4, value: -2.82 }, { month: 5, value: -0.49 }, { month: 6, value: -0.99 }, { month: 7, value: -0.45 }, { month: 8, value: -0.4 }, { month: 9, value: 1.92 }, { month: 10, value: -1.11 }, { month: 11, value: 1.84 }, { month: 12, value: -6.05 }] },
  ] as const;

  function emitInput(field: 'progressLevel' | 'startDate' | 'endDate', event: Event) {
    const value = (event.target as HTMLInputElement | HTMLSelectElement).value;
    if (field === 'progressLevel') {
      emit('update:progressLevel', value as ProgressLevel);
      return;
    }
    emit(`update:${field}` as never, value as never);
  }

  async function renderDistribution() {
    await distributionChart.setOptions({
      color: ['#d27a41'],
      grid: { left: 10, right: 10, top: 20, bottom: 18, containLabel: true },
      xAxis: {
        type: 'category',
        data: distributionBins,
        axisTick: { show: false },
        axisLabel: { color: '#98a2b3', fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#98a2b3', fontSize: 11 },
        splitLine: {
          lineStyle: { color: 'rgba(148, 163, 184, 0.14)', type: 'dashed' },
        },
      },
      series: [
        {
          type: 'bar',
          barWidth: 14,
          itemStyle: { borderRadius: [6, 6, 0, 0] },
          data: distributionValues,
        },
      ],
    });
    distributionChart.resize();
  }

  async function renderSeasonal() {
    await seasonalChart.setOptions({
      color: ['#4ca7dd', '#f2a43a', '#65c1bb', '#de6f7b', '#7286ff'],
      tooltip: { trigger: 'axis' },
      legend: { top: 8, left: 'center', itemWidth: 10, itemHeight: 10 },
      grid: { left: 16, right: 16, top: 42, bottom: 18, containLabel: true },
      xAxis: {
        type: 'category',
        data: monthLabels,
        axisTick: { show: false },
        axisLabel: { color: '#98a2b3' },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#98a2b3' },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.14)', type: 'dashed' } },
      },
      series: seasonalYears.map((year) => ({
        name: year,
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: year === '2026' ? 3 : 2 },
        data: seasonalSeries[year as keyof typeof seasonalSeries],
      })),
    });
    seasonalChart.resize();
  }

  onMounted(() => {
    renderDistribution();
    renderSeasonal();
  });
</script>

<style scoped lang="less">
  .statistics-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .section-head h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-sans);
    font-size: var(--strategy-font-section-title);
    font-weight: 800;
  }

  .statistics-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
    gap: 12px;
  }

  .stats-card {
    padding: var(--strategy-space-3);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .stats-card header,
  .stats-card__header,
  .stats-card__controls,
  .section-head {
    display: flex;
    align-items: center;
  }

  .stats-card header {
    justify-content: space-between;
    margin-bottom: 16px;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .stats-card__header {
    justify-content: space-between;
    gap: 14px;
  }

  .stats-card__controls {
    gap: 8px;
    flex-wrap: wrap;
  }

  .stats-card__controls input,
  .stats-card__controls select {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border-radius: var(--strategy-radius-control);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  .chart-select select,
  .stats-card__controls input {
    border: 1px solid var(--strategy-border-strong);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    box-shadow: var(--strategy-shadow-soft);
  }

  .stats-card--summary {
    display: grid;
    grid-row: span 2;
    grid-template-rows: auto auto minmax(220px, 1fr);
    gap: 14px;
  }

  .stats-kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .stats-kpi {
    display: grid;
    gap: 8px;
    padding: 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface-muted);
  }

  .stats-kpi span {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
  }

  .stats-kpi strong {
    color: var(--strategy-text-2);
    font-size: 18px;
    font-weight: 800;
  }

  .stats-kpi strong.is-positive {
    color: #d9534f;
  }

  .stats-kpi strong.is-negative {
    color: #239b63;
  }

  .mini-chart,
  .seasonal-chart {
    min-height: 260px;
  }

  .heatmap-table {
    display: grid;
    gap: 4px;
    overflow-x: auto;
  }

  .heatmap-row {
    display: grid;
    grid-template-columns: 72px repeat(12, minmax(58px, 1fr));
    gap: 4px;
  }

  .heatmap-row span {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 34px;
    border-radius: 8px;
    font-size: var(--strategy-font-sm);
    font-weight: 700;
  }

  .heatmap-head span,
  .heatmap-year {
    background: var(--strategy-table-head-bg);
    color: var(--strategy-text-3);
  }

  .heatmap-year {
    color: var(--strategy-text-2);
  }

  .heatmap-cell.is-warm {
    background: rgba(217, 83, 79, 0.12);
    color: #cf4653;
  }

  .heatmap-cell.is-cold {
    background: rgba(46, 204, 113, 0.12);
    color: #239b63;
  }

  @media (max-width: 1320px) {
    .statistics-grid {
      grid-template-columns: 1fr;
    }

    .stats-card--summary {
      grid-row: auto;
    }
  }

  @media (max-width: 980px) {
    .section-head {
      flex-direction: column;
    }

    .stats-card__controls {
      justify-content: flex-start;
    }
  }

  @media (max-width: 900px) {
    .statistics-grid,
    .stats-kpi-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
