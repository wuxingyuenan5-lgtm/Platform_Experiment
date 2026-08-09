<template>
  <section class="chart-panel">
    <div class="chart-panel__header">
      <div>
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

        <label class="toolbar-field">
          <span>交易所</span>
          <select v-model="selectedExchange">
            <option v-for="item in exchangeOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>

        <select v-model="selectedSymbol">
          <option v-for="item in symbolOptions" :key="item" :value="item">{{ item }}</option>
        </select>

        <label class="toolbar-field">
          <span>时间精度</span>
          <select v-model="selectedResolution">
            <option v-for="item in resolutionOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>

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
  import type { FundingChartPanelData, FundingExchange, FundingMarketRange } from '../types';

  const props = defineProps<{
    data: FundingChartPanelData;
    exchange: FundingExchange;
    symbol: string;
    range: FundingMarketRange;
    resolution: string;
    startDate: string;
    endDate: string;
  }>();

  const emit = defineEmits<{
    (e: 'update:exchange', value: FundingExchange): void;
    (e: 'update:symbol', value: string): void;
    (e: 'update:range', value: FundingMarketRange): void;
    (e: 'update:resolution', value: string): void;
    (e: 'update:start-date', value: string): void;
    (e: 'update:end-date', value: string): void;
  }>();

  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);
  type FundingRangeLabel = '当前' | '7日' | '30日';
  const rangeOptions: FundingRangeLabel[] = ['当前', '7日', '30日'];
  const exchangeOptions: FundingExchange[] = ['Binance', 'Bybit', 'OKX'];
  const rangeToLabelMap: Record<FundingMarketRange, FundingRangeLabel> = {
    current: '当前',
    '1d': '当前',
    '7d': '7日',
    '30d': '30日',
    '1y': '30日',
  };
  const labelToRangeMap: Record<FundingRangeLabel, FundingMarketRange> = {
    当前: 'current',
    '7日': '7d',
    '30日': '30d',
  };
  const symbolOptions = ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'XAUT'];
  const resolutionOptions = ['15分钟', '30分钟', '1小时', '4小时'];
  const selectedRange = ref<FundingRangeLabel>(rangeToLabelMap[props.range] ?? '当前');
  const selectedExchange = ref<FundingExchange>(props.exchange);
  const selectedSymbol = ref(props.symbol);
  const selectedResolution = ref(props.resolution);
  const startDate = ref(props.startDate || props.data.points[0]?.date || '2026-05-28');
  const endDate = ref(
    props.endDate || props.data.points[props.data.points.length - 1]?.date || '2026-06-24',
  );
  const showFunding = ref(true);
  const showPrice = ref(true);

  watch(
    () => props.range,
    (value) => {
      selectedRange.value = rangeToLabelMap[value] ?? '当前';
    },
    { immediate: true },
  );

  watch(
    () => props.exchange,
    (value) => {
      selectedExchange.value = value;
    },
    { immediate: true },
  );

  watch(
    () => props.symbol,
    (value) => {
      selectedSymbol.value = value;
    },
    { immediate: true },
  );

  watch(
    () => props.resolution,
    (value) => {
      selectedResolution.value = value;
    },
    { immediate: true },
  );

  watch(
    () => props.startDate,
    (value) => {
      startDate.value = value;
    },
    { immediate: true },
  );

  watch(
    () => props.endDate,
    (value) => {
      endDate.value = value;
    },
    { immediate: true },
  );

  watch(selectedRange, (value) => emit('update:range', labelToRangeMap[value] ?? 'current'));
  watch(selectedExchange, (value) => emit('update:exchange', value));
  watch(selectedSymbol, (value) => emit('update:symbol', value));
  watch(selectedResolution, (value) => emit('update:resolution', value));
  watch(startDate, (value) => emit('update:start-date', value));
  watch(endDate, (value) => emit('update:end-date', value));

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

  const panelTitle = computed(() => '持仓加权资金费率');

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
          ? [
              {
                name: props.data.legendFunding,
                type: 'bar' as const,
                barWidth: 16,
                itemStyle: {
                  borderRadius: [4, 4, 0, 0],
                  color: (params: { value: number }) => (params.value >= 0 ? '#cf3f4f' : '#2db87c'),
                },
                data: filteredPoints.value.map((point) => point.funding),
              },
            ]
          : []),
        ...(showPrice.value
          ? [
              {
                name: props.data.legendPrice,
                type: 'line' as const,
                yAxisIndex: 1,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 3, color: '#d79a1e' },
                data: filteredPoints.value.map((point) => point.price),
              },
            ]
          : []),
      ] as any,
    });
    await nextTick();
    resize();
  }

  watch([filteredPoints, selectedSymbol, showFunding, showPrice], renderChart, { deep: true });
  onMounted(renderChart);
</script>

<style scoped lang="less">
  .chart-panel {
    padding: var(--strategy-space-4);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
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
    margin: 0;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-sans);
    font-size: var(--strategy-font-section-title);
    font-weight: 800;
  }

  .toolbar {
    display: flex;
    flex-wrap: nowrap;
    align-items: end;
    justify-content: flex-end;
    gap: var(--strategy-space-2);
    width: 100%;
  }

  .toolbar-group {
    display: inline-flex;
    padding: 4px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
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
    height: var(--strategy-control-height);
    padding: 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
  }

  .toolbar-field {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    height: var(--strategy-control-height);
    padding: 0 10px 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  .toolbar-field span {
    white-space: nowrap;
  }

  .toolbar-field select {
    min-width: 88px;
    height: 100%;
    padding: 0;
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
  }

  .toolbar-group button {
    border: none;
    box-shadow: none;
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
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
  }

  .legend-pill.is-active {
    border-color: var(--strategy-accent-soft);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
  }

  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .dot-funding {
    background: var(--strategy-accent-strong);
  }

  .dot-price {
    background: #4aa3df;
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
