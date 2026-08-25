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
        {{ data.legendFunding }}
      </button>
      <button
        type="button"
        class="legend-pill"
        :class="{ 'is-active': showPrice }"
        @click="showPrice = !showPrice"
      >
        <span class="dot dot-price"></span>
        {{ data.legendPrice }}
      </button>
    </div>

    <div ref="chartRef" class="chart-wrap"></div>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { FundingChartPanelData, FundingExchange } from '../types';

  const props = defineProps<{
    context: Record<string, any> | null;
    positionGroups: Array<Record<string, any>>;
  }>();

  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);
  type FundingRangeLabel = '当前' | '7日' | '30日';
  const rangeOptions: FundingRangeLabel[] = ['当前'];
  const exchangeOptions: FundingExchange[] = ['Bybit'];
  const symbolOptions = computed(() =>
    (props.context?.symbolOptions ?? []).map((item: Record<string, any>) => item.baseAsset),
  );
  const resolutionOptions = ['实时'];
  const selectedRange = ref<FundingRangeLabel>('当前');
  const selectedExchange = ref<FundingExchange>('Bybit');
  const selectedSymbol = ref('BTC');
  const selectedResolution = ref('实时');
  const today = new Date().toISOString().slice(0, 10);
  const startDate = ref(today);
  const endDate = ref(today);
  const showFunding = ref(true);
  const showPrice = ref(true);

  watch(
    () => props.context?.perpetualSymbol,
    () => {
      const option = props.context?.symbolOptions?.find(
        (item: Record<string, any>) => item.perpetualSymbol === props.context?.perpetualSymbol,
      );
      selectedSymbol.value = option?.baseAsset ?? 'BTC';
    },
    { immediate: true },
  );

  const data = computed<FundingChartPanelData>(() => {
    const price = Number(props.context?.perpetualQuote?.mid);
    const funding = Number(props.context?.fundingRate);
    return {
      title: '持仓加权资金费率',
      legendPrice: '永续中间价',
      legendFunding: '实时资金费率',
      points:
        Number.isFinite(price) || Number.isFinite(funding)
          ? [
              {
                date: String(props.context?.asOf ?? new Date().toISOString()),
                price: Number.isFinite(price) ? price : 0,
                funding: Number.isFinite(funding) ? funding * 100 : 0,
              },
            ]
          : [],
    };
  });

  const filteredPoints = computed(() => {
    const start = new Date(startDate.value).getTime();
    const end = new Date(endDate.value).getTime();
    const base = data.value.points.filter((point) => {
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
                name: data.value.legendFunding,
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
                name: data.value.legendPrice,
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
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
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
    box-shadow: var(--strategy-shadow-soft);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
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
    background: var(--strategy-accent-soft);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
    color: var(--strategy-accent-strong);
  }

  .legend-pill.is-active {
    border-color: var(--strategy-accent-soft);
    background: var(--strategy-accent-soft);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
    color: var(--strategy-accent-strong);
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
      flex-direction: column;
      align-items: flex-start;
    }

    .toolbar {
      justify-content: flex-start;
    }
  }
</style>
