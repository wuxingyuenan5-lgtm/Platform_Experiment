<template>
  <section class="capital-net-value-board">
    <header class="board-header">
      <div>
        <h3>{{ curve.title }}</h3>
      </div>

      <div class="board-controls">
        <select v-model="metricKey">
          <option v-for="item in curve.metricOptions" :key="item.key" :value="item.key">{{ item.label }}</option>
        </select>
        <select v-model="periodKey">
          <option v-for="item in curve.periodOptions" :key="item.key" :value="item.key">{{ item.label }}</option>
        </select>
        <template v-if="curve.modeOptions?.length">
          <button
            v-for="item in curve.modeOptions"
            :key="item.key"
            type="button"
            class="mode-button"
            :class="{ 'is-active': modeKey === item.key }"
            @click="modeKey = item.key"
          >
            {{ item.label }}
          </button>
        </template>
      </div>
    </header>

    <div class="curve-summary">
      <article v-for="item in curve.summaries" :key="item.label" class="summary-pill">
        <label>{{ item.label }}</label>
        <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
      </article>
    </div>

    <div ref="chartRef" class="curve-chart"></div>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { StrategyCapitalCurveConfig } from '../types';

  const props = defineProps<{
    curve: StrategyCapitalCurveConfig;
  }>();

  const metricKey = ref(props.curve.defaultMetric);
  const periodKey = ref(props.curve.defaultPeriod);
  const modeKey = ref(props.curve.defaultMode || props.curve.modeOptions?.[0]?.key || '');

  const activeMetricLabel = computed(
    () => props.curve.metricOptions.find((item) => item.key === metricKey.value)?.label || '净值',
  );
  const activeModeColor = computed(() => (modeKey.value === 'fixed' ? '#8a63d2' : '#4a7cff'));
  const activeZoomEnd = computed(() => {
    if (periodKey.value === 'day') return 40;
    if (periodKey.value === '7d') return 75;
    return 100;
  });

  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);

  async function renderChart() {
    await setOptions({
      tooltip: { trigger: 'axis' },
      legend: {
        top: 4,
        itemWidth: 12,
        itemHeight: 12,
        data: [activeMetricLabel.value, '回撤'],
        textStyle: { color: '#6b7c93', fontSize: 12 },
      },
      grid: { left: 26, right: 36, top: 52, bottom: 72, containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: props.curve.xLabels,
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#dbe5f1' } },
        axisLabel: { color: '#90a0b5', hideOverlap: true },
      },
      yAxis: [
        {
          type: 'value',
          min: (value: { min: number }) => Math.max(0, Number((value.min - 0.04).toFixed(2))),
          max: (value: { max: number }) => Number((value.max + 0.04).toFixed(2)),
          axisLabel: { color: '#90a0b5' },
          splitLine: { lineStyle: { color: 'rgba(148, 163, 184, .16)', type: 'dashed' } },
        },
        {
          type: 'value',
          position: 'right',
          axisLabel: { color: '#90a0b5', formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: 'inside', start: Math.max(0, activeZoomEnd.value - 40), end: activeZoomEnd.value },
        {
          type: 'slider',
          height: 20,
          bottom: 14,
          backgroundColor: 'rgba(227, 236, 248, .55)',
          fillerColor: 'rgba(159, 186, 245, .28)',
          brushSelect: false,
          start: Math.max(0, activeZoomEnd.value - 40),
          end: activeZoomEnd.value,
        },
      ],
      series: [
        {
          name: activeMetricLabel.value,
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2.5, color: activeModeColor.value },
          areaStyle: { color: modeKey.value === 'fixed' ? 'rgba(138, 99, 210, .08)' : 'rgba(74, 124, 255, .08)' },
          data: props.curve.netValueData,
        },
        {
          name: '回撤',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1.8, color: '#db6d6d' },
          areaStyle: { color: 'rgba(219, 109, 109, .14)' },
          data: props.curve.drawdownData,
        },
      ],
    });

    await nextTick();
    resize();
  }

  watch(() => props.curve, renderChart, { deep: true });
  watch([metricKey, periodKey, modeKey], renderChart);
  onMounted(renderChart);
  </script>

<style scoped lang="less">
  .capital-net-value-board {
    display: grid;
    gap: 12px;
    padding: 18px 20px 14px;
    border-radius: 22px;
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    border: 1px solid var(--strategy-border);
    box-shadow: var(--strategy-shadow);
  }

  .board-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  .board-header h3 {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: var(--strategy-text-1);
  }

  .board-controls {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;
  }

  .board-controls select,
  .mode-button {
    height: 36px;
    padding: 0 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: 13px;
    font-weight: 600;
  }

  .mode-button {
    cursor: pointer;
  }

  .mode-button.is-active {
    border-color: rgba(74, 124, 255, 0.22);
    background: rgba(74, 124, 255, 0.08);
    color: #355eea;
  }

  .curve-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .summary-pill {
    min-width: 180px;
    padding: 10px 12px;
    border-radius: 14px;
    background: var(--strategy-surface-muted);
    border: 1px solid rgba(221, 229, 241, 0.92);
  }

  .summary-pill label,
  .summary-pill strong {
    display: block;
  }

  .summary-pill label {
    color: var(--strategy-text-3);
    font-size: 11px;
    font-weight: 700;
  }

  .summary-pill strong {
    margin-top: 6px;
    font-size: 16px;
    color: var(--strategy-text-1);
    font-weight: 700;
  }

  .curve-chart {
    height: 420px;
  }

  .is-positive {
    color: var(--strategy-success) !important;
  }

  .is-negative {
    color: var(--strategy-danger) !important;
  }

  .is-neutral {
    color: var(--strategy-text-1) !important;
  }

  @media (max-width: 980px) {
    .board-header {
      flex-direction: column;
    }

    .board-controls {
      justify-content: flex-start;
    }
  }
</style>
