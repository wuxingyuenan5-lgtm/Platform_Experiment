<template>
  <div class="spread-page">
    <SpreadAnalysisWorkspaceHeader
      v-if="activeSection === 'analysis'"
      v-model:domestic-metal="domesticMetal"
      v-model:selected-venue="selectedVenue"
      v-model:left-leg-symbol="leftLegSymbol"
      v-model:right-leg-symbol="rightLegSymbol"
      v-model:selected-resolution="selectedResolution"
      :variant="variant"
    />

    <template v-if="activeSection === 'analysis'">
      <SpreadAnalysisOverview v-if="variant !== 'domesticOverseas'" @refresh="touchRefresh" />

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

      <DomesticOverseasSupplement v-if="variant === 'domesticOverseas'" @refresh="touchRefresh" />

      <SpreadStatisticsSection
        v-model:progress-level="progressLevel"
        v-model:start-date="startDate"
        v-model:end-date="endDate"
      />
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
  import { nextTick, onMounted, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import SpreadExecutionWorkspace from './components/SpreadExecutionWorkspace.vue';
  import SpreadAnalysisWorkspaceHeader from './components/SpreadAnalysisWorkspaceHeader.vue';
  import DomesticOverseasSupplement from './components/DomesticOverseasSupplement.vue';
  import DomesticOverseasMarketInsight from './components/DomesticOverseasMarketInsight.vue';
  import SpreadAnalysisOverview from './components/SpreadAnalysisOverview.vue';
  import SpreadStatisticsSection from './components/SpreadStatisticsSection.vue';
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
      rightLegSymbol: 'XAUUSD.s',
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

  const mainChartRef = ref<HTMLDivElement | null>(null);

  const mainChart = useECharts(mainChartRef as Ref<HTMLDivElement>);

  const chartDates = ['03-17', '03-18', '03-19', '03-20', '03-21', '03-22', '03-24', '03-26', '03-28', '03-30', '04-01', '04-03', '04-05', '04-07', '04-09', '04-11', '04-13', '04-15'];
  const spreadSeries = [18.2, 17.9, 16.8, 14.4, 12.2, 10.9, 8.1, 7.4, 8.6, 10.3, 12.5, 14.8, 16.7, 18.1, 19.4, 18.8, 18.1, 17.3];
  const goldPriceSeries = [2331, 2334, 2338, 2329, 2321, 2318, 2306, 2301, 2305, 2316, 2328, 2340, 2352, 2359, 2362, 2361, 2358, 2354];


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

  watch(
    () => [props.activeSection, showSpread.value, showGoldPrice.value, progressLevel.value, startDate.value, endDate.value],
    () => {
      renderMainChart();
    },
  );

  onMounted(() => {
    renderMainChart();
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

  .spread-chart-card {
    border: 1px solid var(--strategy-border);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
    border-radius: var(--strategy-radius-panel);
  }

  .spread-chart-card {
    padding: var(--strategy-space-4) var(--strategy-space-4) var(--strategy-space-2);
  }

  .spread-chart-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
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
  .spread-chart-toolbar__left input,
  .spread-chart-toolbar__left select {
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
    padding: 0 12px;
    line-height: 1;
  }

  .spread-chart-toolbar__left input {
    min-width: 122px;
  }

  .chart-select span {
    color: var(--strategy-text-faint);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .spread-chart {
    height: 420px;
    margin-top: 8px;
  }

  @media (max-width: 980px) {
    .spread-chart-toolbar {
      flex-direction: column;
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
</style>
