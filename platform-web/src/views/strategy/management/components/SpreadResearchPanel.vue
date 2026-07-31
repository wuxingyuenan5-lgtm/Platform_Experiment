<template>
  <section class="spread-research">
    <div class="research-toolbar">
      <div class="toolbar-tabs">
        <button
          v-for="item in modeTabs"
          :key="item.key"
          type="button"
          :class="{ 'is-active': activeMode === item.key }"
          @click="activeMode = item.key"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="toolbar-controls">
        <label>
          <span>周期</span>
          <select v-model="selectedPeriod">
            <option v-for="item in periodOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label v-if="activeMode === 'matrix'">
          <span>基准腿</span>
          <select v-model="selectedMatrixBase">
            <option v-for="item in matrixBases" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
      </div>
    </div>

    <template v-if="activeMode === 'intraday'">
      <div class="intraday-layout">
        <article class="research-panel research-panel--chart">
          <header>
            <div>
              <p class="panel-eyebrow">Intraday Structure</p>
              <h3>XAUTUSDT.P - XAUUSD 价差联动</h3>
            </div>
          </header>
          <div class="legend-switches legend-switches--center">
            <button
              v-for="item in intradayLegends"
              :key="item.key"
              type="button"
              :class="{ 'is-active': intradayVisible.includes(item.key) }"
              @click="toggleIntradaySeries(item.key)"
            >
              {{ item.label }}
            </button>
          </div>
          <div ref="intradayChartRef" class="chart-block"></div>
        </article>

        <article class="research-panel research-panel--stats">
          <header>
            <div>
              <p class="panel-eyebrow">Distribution & Signal</p>
              <h3>日内统计</h3>
            </div>
            <span class="stats-badge">60</span>
          </header>

          <div class="stats-list">
            <div v-for="item in intradayStats" :key="item.label" class="stats-row">
              <span>{{ item.label }}</span>
              <strong :class="item.tone ? `is-${item.tone}` : ''">{{ item.value }}</strong>
            </div>
          </div>

          <div ref="histogramChartRef" class="mini-chart"></div>
        </article>
      </div>
    </template>

    <template v-else-if="activeMode === 'seasonal'">
      <div class="seasonal-layout">
        <article class="research-panel research-panel--chart">
          <header>
            <div>
              <p class="panel-eyebrow">Seasonality</p>
              <h3>季节图表</h3>
            </div>
          </header>
          <div class="legend-switches legend-switches--center">
            <button
              v-for="item in seasonalLegends"
              :key="item.key"
              type="button"
              :class="{ 'is-active': seasonalVisible.includes(item.key) }"
              @click="toggleSeasonalSeries(item.key)"
            >
              {{ item.label }}
            </button>
          </div>
          <div ref="seasonalChartRef" class="chart-block chart-block--tall"></div>
        </article>

        <article class="research-panel research-panel--stats">
          <header>
            <div>
              <p class="panel-eyebrow">Year Snapshot</p>
              <h3>振幅统计</h3>
            </div>
            <span class="stats-badge">5Y</span>
          </header>
          <div ref="seasonalSideChartRef" class="mini-chart mini-chart--tall"></div>
        </article>
      </div>

      <article class="research-panel">
        <header>
          <div>
            <p class="panel-eyebrow">Monthly Regime</p>
            <h3>月度热力分布</h3>
          </div>
        </header>
        <div class="heatmap-grid">
          <div class="heatmap-row heatmap-row--head">
            <span>年份</span>
            <span v-for="month in months" :key="month">{{ month }}</span>
          </div>
          <div v-for="row in seasonalHeatRows" :key="row.year" class="heatmap-row">
            <strong>{{ row.year }}</strong>
            <span
              v-for="(cell, index) in row.values"
              :key="`${row.year}-${index}`"
              :class="['heatmap-cell', cell > 0 ? 'is-positive' : 'is-negative']"
            >
              {{ cell > 0 ? '+' : '' }}{{ cell.toFixed(2) }}%
            </span>
          </div>
        </div>
      </article>
    </template>

    <template v-else>
      <div class="matrix-layout">
        <article class="research-panel research-panel--matrix">
          <header>
            <div>
              <p class="panel-eyebrow">Basis Matrix</p>
              <h3>价差矩阵</h3>
            </div>
            <div class="matrix-actions">
              <button
                v-for="item in matrixWindows"
                :key="item"
                type="button"
                :class="{ 'is-active': selectedMatrixWindow === item }"
                @click="selectedMatrixWindow = item"
              >
                {{ item }}
              </button>
            </div>
          </header>

          <div class="matrix-shell">
            <table>
              <thead>
                <tr>
                  <th>品种</th>
                  <th v-for="item in matrixColumns" :key="item">{{ item }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in matrixRows"
                  :key="row.symbol"
                  :class="{ 'is-selected': row.symbol === selectedMatrixPair }"
                  @click="selectedMatrixPair = row.symbol"
                >
                  <td>{{ row.symbol }}</td>
                  <td
                    v-for="item in row.values"
                    :key="`${row.symbol}-${item.label}`"
                    :class="item.value >= 0 ? 'is-positive' : 'is-negative'"
                  >
                    {{ item.value > 0 ? '+' : '' }}{{ item.value.toFixed(2) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

        <article class="research-panel research-panel--stats">
          <header>
            <div>
              <p class="panel-eyebrow">Pair Scatter</p>
              <h3>{{ selectedMatrixPair }} 线性关系</h3>
            </div>
            <span class="stats-badge">{{ selectedMatrixBase }}</span>
          </header>

          <div class="stats-list">
            <div v-for="item in scatterStats" :key="item.label" class="stats-row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>

          <div ref="scatterChartRef" class="mini-chart mini-chart--tall"></div>
        </article>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';

  type ModeKey = 'intraday' | 'seasonal' | 'matrix';
  type IntradaySeries = 'spread' | 'main' | 'hedge' | 'maFast' | 'maSlow';
  type SeasonalSeries = '2022' | '2023' | '2024' | '2025' | '2026';

  const modeTabs: Array<{ key: ModeKey; label: string }> = [
    { key: 'intraday', label: '日内结构' },
    { key: 'seasonal', label: '季节图表' },
    { key: 'matrix', label: '价差矩阵' },
  ];
  const intradayLegends: Array<{ key: IntradaySeries; label: string }> = [
    { key: 'spread', label: '价差' },
    { key: 'main', label: '主腿' },
    { key: 'hedge', label: '对冲腿' },
    { key: 'maFast', label: 'MA5' },
    { key: 'maSlow', label: 'MA20' },
  ];
  const seasonalLegends: Array<{ key: SeasonalSeries; label: string }> = [
    { key: '2022', label: '2022' },
    { key: '2023', label: '2023' },
    { key: '2024', label: '2024' },
    { key: '2025', label: '2025' },
    { key: '2026', label: '2026' },
  ];
  const periodOptions = ['1D', '5D', '20D'];
  const matrixWindows = ['1M', '3M', '6M', '1Y'];
  const matrixBases = ['SHFE黄金', 'XAUT', 'XAUUSD'];
  const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

  const activeMode = ref<ModeKey>('intraday');
  const selectedPeriod = ref('5D');
  const selectedMatrixBase = ref('SHFE黄金');
  const selectedMatrixWindow = ref('1M');
  const selectedMatrixPair = ref('SHFE白银');
  const intradayVisible = ref<IntradaySeries[]>(['spread', 'main', 'hedge', 'maFast', 'maSlow']);
  const seasonalVisible = ref<SeasonalSeries[]>(['2022', '2023', '2024', '2025', '2026']);

  const intradayChartRef = ref<HTMLDivElement | null>(null);
  const histogramChartRef = ref<HTMLDivElement | null>(null);
  const seasonalChartRef = ref<HTMLDivElement | null>(null);
  const seasonalSideChartRef = ref<HTMLDivElement | null>(null);
  const scatterChartRef = ref<HTMLDivElement | null>(null);

  const intradayChart = useECharts(intradayChartRef as Ref<HTMLDivElement>);
  const histogramChart = useECharts(histogramChartRef as Ref<HTMLDivElement>);
  const seasonalChart = useECharts(seasonalChartRef as Ref<HTMLDivElement>);
  const seasonalSideChart = useECharts(seasonalSideChartRef as Ref<HTMLDivElement>);
  const scatterChart = useECharts(scatterChartRef as Ref<HTMLDivElement>);

  const intradayData = computed(() => ({
    times: ['09:56', '10:24', '10:52', '11:20', '11:48', '12:16', '12:44', '13:12', '13:40', '14:08', '14:36', '15:04', '15:32', '16:00'],
    spread: [12, 15, 8, 11, 7, -4, -8, -6, 3, 10, 18, 26, 32, 28],
    main: [2350, 2352, 2349, 2351, 2348, 2342, 2339, 2340, 2344, 2348, 2355, 2362, 2358, 2354],
    hedge: [2338, 2339, 2337, 2338, 2336, 2330, 2328, 2329, 2334, 2339, 2346, 2350, 2349, 2346],
    maFast: [11, 12, 11, 10, 7, 3, -2, -3, 0, 5, 12, 18, 23, 24],
    maSlow: [8, 8, 8, 8, 7, 6, 5, 4, 5, 7, 9, 12, 14, 16],
  }));
  const intradayStats = computed(() => [
    { label: '最新值', value: '28' },
    { label: '均值', value: '10' },
    { label: '中值', value: '8' },
    { label: '距均值', value: '18', tone: 'positive' as const },
    { label: '标准差', value: '17' },
    { label: '百分位', value: '100.00%', tone: 'negative' as const },
    { label: '最高', value: '60 (06-24)' },
    { label: '最低', value: '-90 (06-23)' },
  ]);
  const seasonalHeatRows = [
    { year: '2026', values: [-2.65, 0.11, 0.44, -3.59, -2.23, 1.85, 0.17, 0.53, 2.04, 1.15, -0.85, 0.94] },
    { year: '2025', values: [-2.94, 6.97, -4.63, -10.32, 3.33, -1.55, 3.43, -4.37, 0.53, 2.04, 1.15, 0.66] },
    { year: '2024', values: [-4.77, -3.37, -2.49, 0.44, 0.59, -3.58, -3.94, 0.93, -0.35, -1.37, -4.84, -17.83] },
    { year: '2023', values: [2.10, 0.47, -2.01, -2.68, -2.56, -2.50, 0.85, -2.74, 3.50, 0.37, -0.15, -4.79] },
    { year: '2022', values: [-2.79, 3.24, -0.27, 2.07, -1.59, 0.81, -2.13, -4.17, 4.36, -3.99, 10.30, -2.72] },
  ];
  const matrixColumns = ['白银', '铜', '锌', '螺纹钢', 'PTA', '玻璃', '豆一'];
  const matrixRows = computed(() => [
    { symbol: 'SHFE白银', values: makeMatrixValues([13.94, 102.43, 23.45, 2.22, 4.88, 0.82, 3.88]) },
    { symbol: 'SHFE铜', values: makeMatrixValues([-102.43, -9.51, -11.72, 13.69, 9.07, 13.86, 10.06]) },
    { symbol: 'SHFE锌', values: makeMatrixValues([-23.45, 9.51, 21.23, 23.09, 18.58, 23.37, 19.57]) },
    { symbol: 'DCE豆一', values: makeMatrixValues([-3.88, -10.06, -19.57, 3.52, 0.99, -3.80, -3.63]) },
  ]);
  const scatterStats = computed(() => [
    { label: '最新值', value: '0' },
    { label: '均值', value: '0' },
    { label: '百分位', value: '0%' },
    { label: '标准差', value: '0' },
    { label: '斜率', value: '0' },
  ]);

  watch([activeMode, intradayVisible, seasonalVisible, selectedMatrixPair, selectedMatrixBase, selectedMatrixWindow], () => {
    nextTick(() => renderByMode());
  });
  onMounted(() => renderByMode());

  function renderByMode() {
    if (activeMode.value === 'intraday') {
      renderIntraday();
      renderHistogram();
      return;
    }
    if (activeMode.value === 'seasonal') {
      renderSeasonal();
      renderSeasonalBars();
      return;
    }
    renderScatter();
  }

  async function renderIntraday() {
    const mainSeries: any[] = [];
    if (intradayVisible.value.includes('spread')) {
      mainSeries.push({
        name: '价差',
        type: 'bar',
        xAxisIndex: 0,
        yAxisIndex: 0,
        barWidth: 10,
        itemStyle: {
          color: (params: any) => (Number(params?.data ?? params?.value ?? 0) >= 0 ? '#ef4444' : '#22d3ee'),
        },
        data: intradayData.value.spread,
      });
    }
    if (intradayVisible.value.includes('maFast')) {
      mainSeries.push({ name: 'MA5', type: 'line', xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: '#f97316', width: 1.5 }, data: intradayData.value.maFast });
    }
    if (intradayVisible.value.includes('maSlow')) {
      mainSeries.push({ name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: '#a855f7', width: 1.5 }, data: intradayData.value.maSlow });
    }
    if (intradayVisible.value.includes('main')) {
      mainSeries.push({ name: '主腿', type: 'line', xAxisIndex: 1, yAxisIndex: 1, smooth: true, symbol: 'none', lineStyle: { color: '#38bdf8', width: 1.6 }, data: intradayData.value.main });
    }
    if (intradayVisible.value.includes('hedge')) {
      mainSeries.push({ name: '对冲腿', type: 'line', xAxisIndex: 1, yAxisIndex: 1, smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', width: 1.6 }, data: intradayData.value.hedge });
    }
    await intradayChart.setOptions({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      grid: [
        { left: 16, right: 20, top: 20, height: '42%', containLabel: true },
        { left: 16, right: 20, top: '58%', height: '28%', containLabel: true },
      ],
      xAxis: [
        { type: 'category', data: intradayData.value.times, axisLabel: { color: '#94a3b8' }, axisLine: { lineStyle: { color: 'rgba(148,163,184,.18)' } } },
        { type: 'category', gridIndex: 1, data: intradayData.value.times, axisLabel: { color: '#94a3b8' }, axisLine: { lineStyle: { color: 'rgba(148,163,184,.18)' } } },
      ],
      yAxis: [
        { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,.1)' } } },
        { type: 'value', gridIndex: 1, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,.1)' } } },
      ],
      series: mainSeries,
    });
    await nextTick();
    intradayChart.resize();
  }

  async function renderHistogram() {
    await histogramChart.setOptions({
      backgroundColor: 'transparent',
      grid: { left: 24, right: 16, top: 12, bottom: 18, containLabel: true },
      xAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,.08)' } } },
      yAxis: { type: 'category', data: ['60', '53', '45', '38', '15', '8', '-8', '-15', '-30'], axisLabel: { color: '#94a3b8' } },
      series: [{ type: 'bar', data: [18, 10, 8, 7, 5, 4, 42, 6, 4], itemStyle: { color: (params) => (params.dataIndex < 6 ? '#f59e0b' : '#22d3ee') } }],
    });
    histogramChart.resize();
  }

  async function renderSeasonal() {
    const dates = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
    const seriesMap: Record<SeasonalSeries, number[]> = {
      '2022': [2.76, 2.72, 2.69, 2.65, 2.61, 2.57, 2.51, 2.48, 2.52, 2.56, 2.83, 2.75],
      '2023': [2.81, 2.79, 2.76, 2.72, 2.68, 2.64, 2.60, 2.54, 2.58, 2.63, 2.67, 2.62],
      '2024': [2.27, 2.18, 2.12, 2.14, 2.13, 2.12, 2.07, 2.13, 2.02, 2.02, 1.96, 1.66],
      '2025': [1.65, 1.72, 1.88, 1.76, 1.79, 1.78, 1.81, 1.84, 1.86, 1.84, 1.86, 1.88],
      '2026': [1.80, 1.78, 1.76, 1.74, 1.74, 1.77, 1.76, 1.75, 1.74, 1.75, 1.74, 1.73],
    };
    const colors: Record<SeasonalSeries, string> = { '2022': '#38bdf8', '2023': '#f59e0b', '2024': '#5eead4', '2025': '#fb7185', '2026': '#818cf8' };
    await seasonalChart.setOptions({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      grid: { left: 16, right: 20, top: 20, bottom: 26, containLabel: true },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#94a3b8' }, axisLine: { lineStyle: { color: 'rgba(148,163,184,.18)' } } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,.1)' } } },
      series: seasonalVisible.value.map((key) => ({ name: key, type: 'line', smooth: true, symbol: 'none', lineStyle: { width: 2, color: colors[key] }, data: seriesMap[key] })),
    });
    seasonalChart.resize();
  }

  async function renderSeasonalBars() {
    await seasonalSideChart.setOptions({
      backgroundColor: 'transparent',
      grid: { left: 18, right: 10, top: 16, bottom: 18, containLabel: true },
      xAxis: { type: 'category', data: ['2022', '2023', '2024', '2025', '2026'], axisLabel: { color: '#94a3b8' } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8', formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,.08)' } } },
      series: [{
        type: 'bar',
        data: [-2.79, 2.10, -4.77, -2.94, -2.65],
        itemStyle: {
          color: (params: any) => (Number(params?.data ?? params?.value ?? 0) >= 0 ? '#ef4444' : '#22c55e'),
        },
      }],
    });
    seasonalSideChart.resize();
  }

  async function renderScatter() {
    await scatterChart.setOptions({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item' },
      grid: { left: 28, right: 12, top: 20, bottom: 22, containLabel: true },
      xAxis: { type: 'value', name: `${selectedMatrixBase.value} 价差`, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,.08)' } } },
      yAxis: { type: 'value', name: `${selectedMatrixPair.value} 价差`, axisLabel: { color: '#94a3b8' } },
      series: [
        { type: 'scatter', symbolSize: 10, itemStyle: { color: '#38bdf8' }, data: [[895, 895], [912, 913], [929, 929], [941, 940], [952, 952], [964, 964], [975, 976], [987, 987], [998, 999]] },
        { type: 'line', symbol: 'none', lineStyle: { color: '#60a5fa', width: 2 }, data: [[895, 895], [998, 999]] },
      ],
    });
    scatterChart.resize();
  }

  function toggleIntradaySeries(key: IntradaySeries) {
    intradayVisible.value = intradayVisible.value.includes(key)
      ? intradayVisible.value.filter((item) => item !== key)
      : [...intradayVisible.value, key];
  }
  function toggleSeasonalSeries(key: SeasonalSeries) {
    seasonalVisible.value = seasonalVisible.value.includes(key)
      ? seasonalVisible.value.filter((item) => item !== key)
      : [...seasonalVisible.value, key];
  }
  function makeMatrixValues(values: number[]) {
    return values.map((value, index) => ({ label: matrixColumns[index], value }));
  }
</script>

<style scoped lang="less">
  .spread-research {
    display: grid;
    gap: 14px;
    padding: 18px;
    border-radius: 22px;
    background: linear-gradient(180deg, #12161f 0%, #0c1018 100%);
    border: 1px solid rgba(71, 85, 105, 0.5);
    box-shadow: 0 24px 60px rgba(2, 6, 23, 0.42);
    color: #dbe4f0;
  }
  .research-toolbar,
  .toolbar-tabs,
  .toolbar-controls,
  .research-panel header,
  .legend-switches,
  .matrix-actions {
    display: flex;
    align-items: center;
  }
  .research-toolbar,
  .research-panel header {
    justify-content: space-between;
    gap: 14px;
    flex-wrap: wrap;
  }
  .toolbar-tabs,
  .toolbar-controls,
  .legend-switches,
  .matrix-actions {
    gap: 8px;
    flex-wrap: wrap;
  }

  .legend-switches--center {
    justify-content: center;
    margin: 12px 0 4px;
  }
  .toolbar-tabs button,
  .legend-switches button,
  .matrix-actions button {
    height: 34px;
    padding: 0 14px;
    border: 1px solid rgba(71, 85, 105, 0.7);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.82);
    color: #94a3b8;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }
  .toolbar-tabs .is-active,
  .legend-switches .is-active,
  .matrix-actions .is-active {
    color: #f8fafc;
    border-color: rgba(96, 165, 250, 0.88);
    background: rgba(37, 99, 235, 0.3);
  }
  .toolbar-controls label {
    display: grid;
    gap: 6px;
  }
  .toolbar-controls span {
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
  }
  .toolbar-controls select {
    min-width: 110px;
    height: 36px;
    padding: 0 12px;
    border: 1px solid rgba(71, 85, 105, 0.7);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.9);
    color: #dbe4f0;
  }
  .intraday-layout,
  .seasonal-layout,
  .matrix-layout {
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(0, 1.35fr) 320px;
  }
  .research-panel {
    border: 1px solid rgba(51, 65, 85, 0.82);
    background: rgba(15, 23, 42, 0.76);
    border-radius: 18px;
    padding: 16px;
    min-width: 0;
  }
  .panel-eyebrow {
    display: none;
  }
  .research-panel h3 {
    margin: 0;
    color: #f8fafc;
    font-size: 18px;
    font-weight: 700;
  }
  .stats-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    height: 34px;
    padding: 0 10px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.16);
    color: #e2e8f0;
    font-size: 12px;
    font-weight: 700;
  }
  .chart-block {
    height: 520px;
  }
  .chart-block--tall {
    height: 600px;
  }
  .mini-chart {
    height: 260px;
    margin-top: 12px;
  }
  .mini-chart--tall {
    height: 360px;
  }
  .stats-list {
    display: grid;
    gap: 12px;
  }
  .stats-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    color: #cbd5e1;
    font-size: 13px;
  }
  .stats-row span {
    color: #94a3b8;
  }
  .stats-row strong {
    color: #f8fafc;
  }
  .heatmap-grid {
    overflow: auto;
    display: grid;
    gap: 8px;
  }
  .heatmap-row {
    display: grid;
    grid-template-columns: 72px repeat(12, minmax(74px, 1fr));
    gap: 6px;
    align-items: center;
  }
  .heatmap-row--head span {
    color: #64748b;
    font-size: 12px;
    font-weight: 700;
  }
  .heatmap-row strong {
    color: #f8fafc;
    font-size: 12px;
  }
  .heatmap-cell {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 34px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    background: rgba(30, 41, 59, 0.78);
  }
  .matrix-shell {
    overflow: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th,
  td {
    padding: 11px 10px;
    border-bottom: 1px solid rgba(51, 65, 85, 0.56);
    text-align: center;
    white-space: nowrap;
    font-size: 12px;
  }
  th {
    color: #64748b;
    font-weight: 700;
  }
  td {
    color: #dbe4f0;
    font-weight: 600;
  }
  tbody tr {
    cursor: pointer;
  }
  tbody tr:hover {
    background: rgba(30, 41, 59, 0.55);
  }
  tbody tr.is-selected {
    background: rgba(37, 99, 235, 0.16);
  }
  .is-positive {
    color: #4ade80 !important;
  }
  .is-negative {
    color: #fb7185 !important;
  }
  @media (max-width: 1380px) {
    .intraday-layout,
    .seasonal-layout,
    .matrix-layout {
      grid-template-columns: 1fr;
    }
  }
</style>
