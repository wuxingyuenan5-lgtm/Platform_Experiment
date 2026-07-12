<template>
  <section class="chart-panel">
    <div class="chart-panel__header">
      <div>
        <p class="eyebrow">Funding Trend</p>
        <h2>{{ panelTitle }}</h2>
      </div>

      <div class="toolbar">
        <div class="toolbar-group">
          <button
            v-for="item in rangeOptions"
            :key="item"
            type="button"
            :class="{ 'is-active': item === selectedRange }"
            @click="selectedRange = item"
          >
            {{ item }}
          </button>
        </div>

        <select v-model="selectedSymbol">
          <option v-for="item in symbolOptions" :key="item" :value="item">{{ item }}</option>
        </select>

        <input v-model="startDate" type="date" />
        <input v-model="endDate" type="date" />
      </div>
    </div>

    <div class="toolbar-legend toolbar-legend--center">
      <button
        type="button"
        class="legend-pill"
        :class="{ 'is-active': showFunding }"
        @click="showFunding = !showFunding"
      >
        <span class="dot dot-funding"></span>
        {{ props.data.legendFunding }}
      </button>
      <button
        type="button"
        class="legend-pill"
        :class="{ 'is-active': showPrice }"
        @click="showPrice = !showPrice"
      >
        <span class="dot dot-price"></span>
        {{ props.data.legendPrice }}
      </button>
    </div>

    <div ref="chartRef" class="chart-wrap"></div>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { FundingChartPanelData } from '../types';

  const props = defineProps<{
    data: FundingChartPanelData;
    symbol: string;
  }>();

  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);
  const rangeOptions = ['当前', '7日', '30日'];
  const symbolOptions = ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'XAUT'];
  const selectedRange = ref('当前');
  const selectedSymbol = ref(props.symbol);
  const startDate = ref(props.data.points[0]?.date || '2026-05-28');
  const endDate = ref(props.data.points[props.data.points.length - 1]?.date || '2026-06-24');
  const showFunding = ref(true);
  const showPrice = ref(true);

  watch(
    () => props.symbol,
    (value) => {
      selectedSymbol.value = value;
    },
    { immediate: true },
  );

  const filteredPoints = computed(() => {
    const start = new Date(startDate.value).getTime();
    const end = new Date(endDate.value).getTime();
    const base = props.data.points.filter((point) => {
      const time = new Date(point.date).getTime();
      return time >= start && time <= end;
    });
    if (selectedRange.value === '7日') return base.slice(-7);
    if (selectedRange.value === '30日') return base.slice(-30);
    return base;
  });

  const panelTitle = computed(() => `${selectedSymbol.value} 持仓加权资金费率`);

  async function renderChart() {
    await setOptions({
      color: ['#cf3f4f', '#111827'],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: { show: false },
      grid: {
        left: 20,
        right: 28,
        top: 38,
        bottom: 58,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: filteredPoints.value.map((point) => point.date),
        axisTick: { show: false },
        axisLabel: { color: 'rgba(36,29,21,.55)' },
      },
      yAxis: [
        {
          type: 'value',
          name: '资金费率',
          axisLabel: {
            color: 'rgba(36,29,21,.55)',
            formatter: (value: number) => `${value.toFixed(3)}%`,
          },
          splitLine: {
            lineStyle: {
              color: 'rgba(134,115,87,.12)',
              type: 'dashed',
            },
          },
        },
        {
          type: 'value',
          name: '价格',
          scale: true,
          axisLabel: { color: 'rgba(36,29,21,.55)' },
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
      series: [
        ...(showFunding.value
          ? [{
              name: props.data.legendFunding,
              type: 'bar',
              barWidth: 16,
              itemStyle: {
                borderRadius: [4, 4, 0, 0],
                color: (params: { value: number }) => (params.value >= 0 ? '#cf3f4f' : '#2db87c'),
              },
              data: filteredPoints.value.map((point) => point.funding),
            }]
          : []),
        ...(showPrice.value
          ? [{
              name: props.data.legendPrice,
              type: 'line',
              yAxisIndex: 1,
              smooth: true,
              symbol: 'none',
              lineStyle: { width: 3, color: '#d79a1e' },
              data: filteredPoints.value.map((point) => point.price),
            }]
          : []),
      ],
    });
    await nextTick();
    resize();
  }

  watch([filteredPoints, selectedSymbol, showFunding, showPrice], renderChart, { deep: true });
  onMounted(renderChart);
</script>

<style scoped lang="less">
  .chart-panel {
    padding: 20px;
    border: 1px solid rgba(134, 115, 87, 0.12);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 16px 36px rgba(94, 76, 52, 0.06);
  }

  .eyebrow {
    display: none;
  }

  .chart-panel__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
  }

  .chart-panel__header h2 {
    margin: 10px 0 0;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-sans);
    font-size: 27px;
    font-weight: 900;
  }

  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
  }

  .toolbar-group {
    display: inline-flex;
    padding: 3px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: #fff;
  }

  .toolbar-legend {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .toolbar-legend--center {
    justify-content: center;
    margin-top: 4px;
  }

  .toolbar-group button,
  .legend-pill,
  .toolbar select,
  .toolbar input {
    height: 32px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 8px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: 12px;
    font-weight: 700;
  }

  .toolbar-group button {
    border: none;
    cursor: pointer;
  }

  .legend-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }

  .toolbar-group .is-active {
    color: var(--strategy-accent-strong);
    background: var(--strategy-accent-soft);
  }

  .legend-pill.is-active {
    border-color: rgba(201, 72, 72, 0.14);
    background: var(--strategy-surface-selected);
    color: var(--strategy-text-1);
  }

  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .dot-funding {
    background: #cf3f4f;
  }

  .dot-price {
    background: #d79a1e;
  }

  .chart-wrap {
    height: 380px;
    margin-top: 12px;
  }

  @media (max-width: 960px) {
    .chart-panel__header {
      align-items: flex-start;
      flex-direction: column;
    }

    .toolbar {
      justify-content: flex-start;
    }
  }
</style>
