<template>
  <div class="spread-page">
    <section v-if="activeSection === 'analysis'" class="spread-workspace-head">
      <div class="spread-workspace-head__main">
        <label v-if="variant === 'domesticOverseas'" class="workspace-control">
          <span>标的</span>
          <select v-model="domesticMetal">
            <option value="gold">金</option>
            <option value="silver">银</option>
            <option value="copper">铜</option>
          </select>
        </label>

        <label v-else class="workspace-control">
          <span>主交易所</span>
          <select v-model="selectedVenue">
            <option value="Bybit">Bybit</option>
            <option value="Binance">Binance</option>
            <option value="OKX">OKX</option>
          </select>
        </label>

        <label class="workspace-control">
          <span>主腿</span>
          <select v-model="leftLegSymbol">
            <option value="XAUTUSDT.P">XAUTUSDT.P</option>
            <option value="SHFE.au2604">SHFE.au2604</option>
            <option value="SHFE.ag2510">SHFE.ag2510</option>
          </select>
        </label>

        <label class="workspace-control">
          <span>对冲腿</span>
          <select v-model="rightLegSymbol">
            <option value="XAUUSD+">XAUUSD+</option>
            <option value="SHFE.au2606">SHFE.au2606</option>
            <option value="SHFE.ag2512">SHFE.ag2512</option>
          </select>
        </label>

        <label class="workspace-control">
          <span>时间精度</span>
          <select v-model="selectedResolution">
            <option value="15分钟">15分钟</option>
            <option value="30分钟">30分钟</option>
            <option value="1小时">1小时</option>
            <option value="4小时">4小时</option>
          </select>
        </label>
      </div>
    </section>

    <template v-if="activeSection === 'analysis'">
      <section v-if="variant !== 'domesticOverseas'" class="spread-overview">
        <article class="spread-card spread-card--table">
          <header>期限结构</header>
          <table>
            <thead>
              <tr>
                <th>合约</th>
                <th>价格</th>
                <th>升贴水</th>
                <th>当前年化</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in termRows" :key="item.contract">
                <td>{{ item.contract }}</td>
                <td>{{ item.price }}</td>
                <td>{{ item.premium }}</td>
                <td>{{ item.annualized }}</td>
              </tr>
            </tbody>
          </table>
        </article>

        <article class="spread-card">
          <header>
            <span>机会分析</span>
            <button type="button" @click="touchRefresh">刷新</button>
          </header>
          <div class="analysis-grid">
            <div class="analysis-head">
              <span></span>
              <span>当前</span>
              <span>10%</span>
              <span>50%</span>
              <span>90%</span>
            </div>
            <div v-for="item in premiumRows" :key="item.label" class="analysis-row">
              <strong>{{ item.label }}</strong>
              <span>{{ item.current }}</span>
              <span>{{ item.p10 }}</span>
              <span>{{ item.p50 }}</span>
              <span>{{ item.p90 }}</span>
            </div>
          </div>
        </article>
      </section>

      <DomesticOverseasMarketInsight v-if="variant === 'domesticOverseas'" :selected-metal="domesticMetal" />

      <section class="spread-chart-card">
        <div class="spread-chart-toolbar">
          <div class="spread-chart-toolbar__left">
            <label class="chart-select chart-select--plain">
              <select v-model="progressLevel">
                <option value="15min">15min</option>
                <option value="1h">1h</option>
                <option value="4h">4h</option>
                <option value="日线">日线</option>
              </select>
            </label>
            <input v-model="startDate" type="date" />
            <input v-model="endDate" type="date" />
          </div>
          <div class="spread-chart-toolbar__center">
            <div class="spread-series-inline">
              <button
                type="button"
                class="series-switch"
                :class="{ 'is-active': showSpread }"
                @click="showSpread = !showSpread"
              >
                价差
              </button>
              <button
                type="button"
                class="series-switch"
                :class="{ 'is-active': showGoldPrice }"
                @click="showGoldPrice = !showGoldPrice"
              >
                黄金价格
              </button>
            </div>
          </div>
          <div class="spread-chart-toolbar__right"></div>
        </div>

        <div ref="mainChartRef" class="spread-chart"></div>
      </section>

      <section v-if="variant === 'domesticOverseas'" class="domestic-supplement">
        <article class="spread-card domestic-analysis-card">
          <header>
            <span>价差分析</span>
          </header>

          <div class="domestic-analysis-scroll">
            <table class="domestic-analysis-table">
              <thead>
                <tr>
                  <th rowspan="2">标的</th>
                  <th rowspan="2">当前价差</th>
                  <th rowspan="2">近一月 (%)</th>
                  <th rowspan="2">近一季度 (%)</th>
                  <th rowspan="2">近半年 (%)</th>
                  <th rowspan="2">近一年 (%)</th>
                  <th colspan="4">10%</th>
                  <th colspan="4">50%</th>
                  <th colspan="4">90%</th>
                </tr>
                <tr>
                  <th>近一月</th>
                  <th>近一季度</th>
                  <th>近半年</th>
                  <th>近一年</th>
                  <th>近一月</th>
                  <th>近一季度</th>
                  <th>近半年</th>
                  <th>近一年</th>
                  <th>近一月</th>
                  <th>近一季度</th>
                  <th>近半年</th>
                  <th>近一年</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in domesticAnalysisRows" :key="row.name">
                  <td>{{ row.name }}</td>
                  <td>{{ row.current }}</td>
                  <td>{{ row.month }}</td>
                  <td>{{ row.quarter }}</td>
                  <td>{{ row.halfYear }}</td>
                  <td>{{ row.year }}</td>
                  <td>{{ row.p10Month }}</td>
                  <td>{{ row.p10Quarter }}</td>
                  <td>{{ row.p10HalfYear }}</td>
                  <td>{{ row.p10Year }}</td>
                  <td>{{ row.p50Month }}</td>
                  <td>{{ row.p50Quarter }}</td>
                  <td>{{ row.p50HalfYear }}</td>
                  <td>{{ row.p50Year }}</td>
                  <td>{{ row.p90Month }}</td>
                  <td>{{ row.p90Quarter }}</td>
                  <td>{{ row.p90HalfYear }}</td>
                  <td>{{ row.p90Year }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

        <article class="spread-card domestic-realtime-card">
          <header class="domestic-realtime-head">
            <span>实时价差</span>
            <div class="domestic-realtime-toolbar">
              <button type="button" @click="touchRefresh">刷新</button>
              <label class="chart-select chart-select--plain">
                <select v-model="domesticRealtimeSymbol">
                  <option value="金">金</option>
                  <option value="银">银</option>
                  <option value="铜">铜</option>
                </select>
              </label>
            </div>
          </header>

          <table class="domestic-realtime-table">
            <thead>
              <tr>
                <th>标的</th>
                <th>最新价</th>
                <th>海外价格</th>
                <th>价差</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in domesticRealtimeRows" :key="row.symbol">
                <td>{{ row.symbol }}</td>
                <td>{{ row.lastPrice }}</td>
                <td>{{ row.overseasPrice }}</td>
                <td>{{ row.spread }}</td>
              </tr>
            </tbody>
          </table>
        </article>
      </section>

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
                  <select v-model="progressLevel">
                    <option value="15min">15min</option>
                    <option value="1h">1h</option>
                    <option value="4h">4h</option>
                    <option value="日线">日线</option>
                  </select>
                </label>
                <input v-model="startDate" type="date" />
                <input v-model="endDate" type="date" />
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

    <SpreadExecutionWorkspace
      v-else
      :variant="variant"
      :selected-venue="selectedVenue"
      :left-leg-symbol="leftLegSymbol"
      :right-leg-symbol="rightLegSymbol"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import SpreadExecutionWorkspace from './components/SpreadExecutionWorkspace.vue';
  import DomesticOverseasMarketInsight from './components/DomesticOverseasMarketInsight.vue';
  import type { SpreadWorkspaceVariant } from './types';

  const props = withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedVenue?: string;
      leftLegSymbol?: string;
      rightLegSymbol?: string;
      selectedResolution?: string;
      variant?: SpreadWorkspaceVariant;
    }>(),
    {
      activeSection: 'analysis',
      selectedVenue: 'Bybit',
      leftLegSymbol: 'XAUTUSDT.P',
      rightLegSymbol: 'XAUUSD+',
      selectedResolution: '30分钟',
      variant: 'crossVenue',
    },
  );

  const variant = ref(props.variant);
  const selectedVenue = ref(props.selectedVenue);
  const leftLegSymbol = ref(props.leftLegSymbol);
  const rightLegSymbol = ref(props.rightLegSymbol);
  const selectedResolution = ref(props.selectedResolution);
  const domesticMetal = ref<'gold' | 'silver' | 'copper'>('gold');
  const startDate = ref('2026-03-16');
  const endDate = ref('2026-04-16');
  const progressLevel = ref<'15min' | '1h' | '4h' | '日线'>('日线');
  const showSpread = ref(true);
  const showGoldPrice = ref(true);
  const domesticRealtimeSymbol = ref<'金' | '银' | '铜'>('金');

  const mainChartRef = ref<HTMLDivElement | null>(null);
  const distributionRef = ref<HTMLDivElement | null>(null);
  const seasonalRef = ref<HTMLDivElement | null>(null);

  const mainChart = useECharts(mainChartRef as Ref<HTMLDivElement>);
  const distributionChart = useECharts(distributionRef as Ref<HTMLDivElement>);
  const seasonalChart = useECharts(seasonalRef as Ref<HTMLDivElement>);

  const monthLabels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

  const termRows = [
    { contract: 'COMEX GCQ6', price: '2,353.6', premium: '18.7', annualized: '8.42%' },
    { contract: 'COMEX GCV6', price: '2,360.1', premium: '21.4', annualized: '9.10%' },
    { contract: 'LBMA Spot', price: '2,334.9', premium: '--', annualized: '--' },
  ];

  const premiumRows = [
    { label: '近一月', current: '18.7', p10: '6.8', p50: '13.2', p90: '22.4' },
    { label: '近一季度', current: '16.4', p10: '4.5', p50: '11.8', p90: '21.1' },
    { label: '近一年', current: '14.9', p10: '-2.3', p50: '9.7', p90: '20.2' },
  ];

  const domesticAnalysisRows = [
    {
      name: '铜',
      current: '1,964.18',
      month: '100',
      quarter: '89.54',
      halfYear: '97.43',
      year: '99.17',
      p10Month: '496.54',
      p10Quarter: '-150.64',
      p10HalfYear: '-2,412.82',
      p10Year: '-8,790.24',
      p50Month: '1,148.83',
      p50Quarter: '908.28',
      p50HalfYear: '-1,772.2',
      p50Year: '-2,091.13',
      p90Month: '1,801.11',
      p90Quarter: '2,071.93',
      p90HalfYear: '9.3',
      p90Year: '13.4',
    },
    {
      name: '银',
      current: '2.08',
      month: '80',
      quarter: '50.32',
      halfYear: '87.05',
      year: '95.63',
      p10Month: '1.81',
      p10Quarter: '1.10',
      p10HalfYear: '0.15',
      p10Year: '-0.04',
      p50Month: '2.17',
      p50Quarter: '2.35',
      p50HalfYear: '0.43',
      p50Year: '0.43',
      p90Month: '2.87',
      p90Quarter: '4.8',
      p90HalfYear: '6.1',
      p90Year: '7.2',
    },
    {
      name: '金',
      current: '0.95',
      month: '36',
      quarter: '44.29',
      halfYear: '55.2',
      year: '48.27',
      p10Month: '-5.01',
      p10Quarter: '-23.71',
      p10HalfYear: '-7.49',
      p10Year: '-8.87',
      p50Month: '1.85',
      p50Quarter: '1.41',
      p50HalfYear: '-0.06',
      p50Year: '0.68',
      p90Month: '12.2',
      p90Quarter: '8.64',
      p90HalfYear: '11.8',
      p90Year: '16.2',
    },
  ];

  const domesticRealtimeRows = computed(() => {
    const maps = {
      金: [
        { symbol: 'SHFE.au2605', lastPrice: '1,059.4', overseasPrice: '4,820.48', spread: '2.84' },
        { symbol: 'SHFE.au2606', lastPrice: '1,060.9', overseasPrice: '4,820.48', spread: '4.34' },
        { symbol: 'SHFE.au2607', lastPrice: '1,062.96', overseasPrice: '4,820.48', spread: '6.4' },
        { symbol: 'SHFE.au2608', lastPrice: '1,063.7', overseasPrice: '4,820.48', spread: '7.14' },
        { symbol: 'SHFE.au2610', lastPrice: '1,066.04', overseasPrice: '4,820.48', spread: '9.48' },
        { symbol: 'SHFE.au2612', lastPrice: '1,068.76', overseasPrice: '4,820.48', spread: '12.2' },
        { symbol: 'SHFE.au2702', lastPrice: '1,071.7', overseasPrice: '4,820.48', spread: '15.14' },
        { symbol: 'SHFE.au2704', lastPrice: '1,075.18', overseasPrice: '4,820.48', spread: '18.62' },
      ],
      银: [
        { symbol: 'SHFE.ag2508', lastPrice: '8,742', overseasPrice: '36.18', spread: '1.84' },
        { symbol: 'SHFE.ag2510', lastPrice: '8,766', overseasPrice: '36.18', spread: '2.08' },
        { symbol: 'SHFE.ag2512', lastPrice: '8,792', overseasPrice: '36.18', spread: '2.34' },
        { symbol: 'SHFE.ag2602', lastPrice: '8,828', overseasPrice: '36.18', spread: '2.70' },
      ],
      铜: [
        { symbol: 'SHFE.cu2508', lastPrice: '80,420', overseasPrice: '9,842', spread: '1,402.16' },
        { symbol: 'SHFE.cu2509', lastPrice: '80,660', overseasPrice: '9,842', spread: '1,642.16' },
        { symbol: 'SHFE.cu2510', lastPrice: '80,918', overseasPrice: '9,842', spread: '1,900.16' },
        { symbol: 'SHFE.cu2511', lastPrice: '80,982', overseasPrice: '9,842', spread: '1,964.18' },
      ],
    } as const;

    return maps[domesticRealtimeSymbol.value];
  });

  const chartDates = ['03-17', '03-18', '03-19', '03-20', '03-21', '03-22', '03-24', '03-26', '03-28', '03-30', '04-01', '04-03', '04-05', '04-07', '04-09', '04-11', '04-13', '04-15'];
  const spreadSeries = [18.2, 17.9, 16.8, 14.4, 12.2, 10.9, 8.1, 7.4, 8.6, 10.3, 12.5, 14.8, 16.7, 18.1, 19.4, 18.8, 18.1, 17.3];
  const goldPriceSeries = [2331, 2334, 2338, 2329, 2321, 2318, 2306, 2301, 2305, 2316, 2328, 2340, 2352, 2359, 2362, 2361, 2358, 2354];

  const statsRows = [
    { label: '最新值', value: '17.30', tone: 'is-positive' },
    { label: '均值', value: '13.57', tone: 'is-neutral' },
    { label: '中位数', value: '14.02', tone: 'is-neutral' },
    { label: '标准差', value: '4.86', tone: 'is-neutral' },
    { label: '百分位', value: '89%', tone: 'is-positive' },
    { label: '区间振幅', value: '12.00', tone: 'is-negative' },
  ];

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
  ];

  watch(() => props.selectedVenue, (v) => (selectedVenue.value = v), { immediate: true });
  watch(() => props.leftLegSymbol, (v) => (leftLegSymbol.value = v), { immediate: true });
  watch(() => props.rightLegSymbol, (v) => (rightLegSymbol.value = v), { immediate: true });
  watch(() => props.selectedResolution, (v) => (selectedResolution.value = v), { immediate: true });
  watch(() => props.variant, (v) => (variant.value = v), { immediate: true });
  watch(
    () => variant.value,
    (value) => {
      if (value === 'domesticOverseas') {
        leftLegSymbol.value = 'XAUTUSDT.P';
      }
    },
    { immediate: true },
  );

  function touchRefresh() {}

  async function renderMainChart() {
    if (props.activeSection !== 'analysis') return;

    const series: any[] = [];

    if (showSpread.value) {
      series.push({
        name: '价差',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 3, color: '#3da6de' },
        data: spreadSeries,
      });
    }

    if (showGoldPrice.value) {
      series.push({
        name: '黄金价格',
        type: 'line',
        smooth: true,
        symbol: 'none',
        yAxisIndex: 1,
        lineStyle: { width: 3, color: '#f4c63d' },
        data: goldPriceSeries,
      });
    }

    await mainChart.setOptions({
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: { show: false },
      grid: { left: 22, right: 24, top: 30, bottom: 78, containLabel: true },
      xAxis: {
        type: 'category',
        data: chartDates,
        axisTick: { show: false },
        axisLabel: { color: '#98a2b3' },
      },
      yAxis: [
        {
          type: 'value',
          name: '价差',
          axisLabel: { color: '#98a2b3' },
          splitLine: {
            lineStyle: { color: 'rgba(148, 163, 184, 0.18)', type: 'dashed' },
          },
        },
        {
          type: 'value',
          name: '黄金价格',
          axisLabel: { color: '#98a2b3' },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 16,
          bottom: 8,
          borderColor: 'rgba(205, 214, 224, 0.8)',
          fillerColor: 'rgba(125, 167, 255, 0.12)',
          backgroundColor: 'rgba(240, 244, 248, 0.9)',
        },
      ],
      series,
    });

    await nextTick();
    mainChart.resize();
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

  watch(
    () => [props.activeSection, showSpread.value, showGoldPrice.value, progressLevel.value, startDate.value, endDate.value],
    () => {
      renderMainChart();
    },
  );

  onMounted(() => {
    renderMainChart();
    renderDistribution();
    renderSeasonal();
  });
</script>

<style lang="less">
  @import '../shared/strategy-theme.less';
</style>

<style scoped lang="less">
  .spread-page {
    display: flex;
    flex-direction: column;
    gap: 14px;
    color: var(--strategy-text-1);
    background: var(--strategy-bg);
  }

  .spread-workspace-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 2px 0;
  }

  .spread-workspace-head__main {
    display: flex;
    flex-wrap: nowrap;
    gap: var(--strategy-space-2);
    align-items: center;
    width: auto;
    max-width: 100%;
    flex: 0 0 auto;
    min-height: 46px;
    padding: 5px var(--strategy-space-2);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }


  .workspace-control {
    display: inline-flex;
    align-items: center;
    gap: var(--strategy-space-1);
    min-width: 0;
    flex: 0 0 auto;
  }

  .workspace-control span {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
    letter-spacing: 0;
    white-space: nowrap;
  }

  .workspace-control select {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    min-width: 88px;
    width: auto;
  }

  .spread-overview {
    display: grid;
    grid-template-columns: 1.1fr 1fr;
    gap: 12px;
  }

  .spread-card,
  .spread-chart-card,
  .stats-card {
    border: 1px solid var(--strategy-border);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
    border-radius: var(--strategy-radius-panel);
  }

  .spread-card,
  .stats-card {
    padding: var(--strategy-space-3);
  }

  .spread-card header,
  .stats-card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .spread-card header button {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
    cursor: pointer;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 10px 0;
    border-bottom: 1px solid var(--strategy-border-soft);
    text-align: left;
    font-size: var(--strategy-font-sm);
  }

  th {
    color: var(--strategy-text-3);
    font-weight: 700;
  }

  td {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .analysis-grid {
    display: grid;
    gap: 14px;
  }

  .analysis-head,
  .analysis-row {
    display: grid;
    grid-template-columns: 1.2fr repeat(4, 1fr);
    gap: 12px;
    align-items: center;
    font-size: var(--strategy-font-sm);
  }

  .analysis-head {
    color: var(--strategy-text-faint);
    font-weight: 700;
  }

  .analysis-row {
    color: var(--strategy-text-2);
  }

  .analysis-row strong {
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .spread-chart-card {
    padding: var(--strategy-space-4) var(--strategy-space-4) var(--strategy-space-2);
  }

  .spread-chart-toolbar,
  .section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .spread-chart-filters,
  .stats-card__controls {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;
  }

  .spread-chart-toolbar__left,
  .spread-chart-toolbar__center,
  .spread-chart-toolbar__right {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .spread-chart-toolbar__left {
    flex: 0 0 auto;
    flex-wrap: nowrap;
  }

  .spread-chart-toolbar__center {
    flex: 1;
    justify-content: center;
  }

  .spread-chart-toolbar__right {
    flex: 0 0 auto;
    justify-content: flex-end;
  }

  .spread-series-inline {
    display: inline-flex;
    align-items: center;
    gap: 10px;
  }

  .series-switch,
  .spread-chart-filters input,
  .spread-chart-filters select,
  .stats-card__controls input,
  .stats-card__controls select {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
  }

  .series-switch {
    cursor: pointer;
  }

  .series-switch.is-active {
    border-color: var(--strategy-accent-soft);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
  }

  .chart-select {
    display: grid;
    gap: 6px;
  }

  .spread-chart-toolbar__left .chart-select {
    gap: 0;
    flex: 0 0 auto;
  }

  .spread-chart-toolbar__left input,
  .spread-chart-toolbar__left select {
    height: var(--strategy-control-height);
    padding: 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    line-height: 1;
    box-shadow: var(--strategy-shadow-soft);
  }

  .spread-chart-toolbar__left input {
    min-width: 122px;
  }

  .chart-select span,
  .section-head p {
    color: var(--strategy-text-faint);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .stats-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 18px;
  }

  .stats-card__header > span {
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .stats-card__controls {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
  }

  .stats-card__controls .chart-select {
    gap: 0;
  }

  .stats-card__controls input,
  .stats-card__controls select {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border-radius: var(--strategy-radius-control);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  .spread-chart {
    height: 420px;
    margin-top: 8px;
  }

  .domestic-supplement {
    display: grid;
    gap: 12px;
  }

  .domestic-analysis-card,
  .domestic-realtime-card {
    padding: 0;
    overflow: hidden;
  }

  .domestic-analysis-card header,
  .domestic-realtime-card header {
    margin: 0;
    padding: 16px 18px;
  }

  .domestic-analysis-scroll {
    overflow-x: auto;
    border-top: 1px solid #f2f4f7;
  }

  .domestic-analysis-table {
    min-width: 1540px;
  }

  .domestic-analysis-table th,
  .domestic-analysis-table td,
  .domestic-realtime-table th,
  .domestic-realtime-table td {
    padding: 12px 16px;
    border-bottom: 1px solid var(--strategy-border-soft);
    text-align: center;
    white-space: nowrap;
    font-size: var(--strategy-font-sm);
  }

  .domestic-analysis-table th,
  .domestic-realtime-table th {
    color: var(--strategy-text-3);
    font-weight: 700;
    background: var(--strategy-table-head-bg);
  }

  .domestic-analysis-table td,
  .domestic-realtime-table td {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .domestic-realtime-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .domestic-realtime-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .domestic-realtime-toolbar button {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
    cursor: pointer;
  }

  .domestic-realtime-table {
    width: 100%;
  }

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
    grid-template-columns: 1.1fr 1fr;
    gap: 14px;
  }

  .stats-card--summary {
    grid-row: span 2;
  }

  .stats-kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .stats-kpi {
    padding: 14px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface-muted);
  }

  .stats-kpi span {
    display: block;
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .stats-kpi strong {
    display: block;
    margin-top: 8px;
    font-size: 24px;
    font-weight: 800;
  }

  .is-negative {
    color: #cb4e5d;
  }

  .is-positive {
    color: #22a06b;
  }

  .is-neutral {
    color: #314053;
  }

  .mini-chart {
    height: 220px;
    margin-top: 16px;
  }

  .seasonal-chart {
    height: 320px;
  }

  .heatmap-table {
    display: grid;
    gap: 8px;
    overflow-x: auto;
  }

  .heatmap-row {
    display: grid;
    grid-template-columns: 84px repeat(12, minmax(70px, 1fr));
    gap: 6px;
    min-width: 980px;
  }

  .heatmap-row span {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 38px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 700;
  }

  .heatmap-head span {
    background: var(--strategy-table-head-bg);
    color: var(--strategy-text-3);
  }

  .heatmap-year {
    background: var(--strategy-table-head-bg);
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
    .spread-overview,
    .statistics-grid,
    .domestic-supplement {
      grid-template-columns: 1fr;
    }

    .stats-card--summary {
      grid-row: auto;
    }
  }

  @media (max-width: 980px) {
    .spread-chart-toolbar,
    .section-head,
    .domestic-realtime-head {
      flex-direction: column;
    }

    .spread-chart-filters,
    .stats-card__controls,
    .domestic-realtime-toolbar {
      justify-content: flex-start;
    }

    .spread-chart-toolbar__left,
    .spread-chart-toolbar__center,
    .spread-chart-toolbar__right {
      width: 100%;
      justify-content: flex-start;
    }

    .spread-chart-toolbar__left {
      flex-wrap: wrap;
    }
  }

  @media (max-width: 900px) {
    .spread-overview,
    .statistics-grid,
    .stats-kpi-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
