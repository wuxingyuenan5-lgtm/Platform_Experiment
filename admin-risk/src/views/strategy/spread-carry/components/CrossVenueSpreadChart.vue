<template>
  <section class="cross-card cross-card--chart">
    <div class="card-head card-head--between">
      <div>
        <h3>做多价差走势</h3>
        <span>(BY Ask - MT5 Bid)</span>
      </div>
      <div class="range-tabs">
        <button
          v-for="range in ranges"
          :key="range"
          :class="{ active: selectedRange === range }"
          @click="$emit('update:selectedRange', range)"
        >
          {{ range }}
        </button>
        <button class="gear-btn gear-btn--mini" type="button">⤢</button>
      </div>
    </div>

    <div ref="chartRef" class="spread-chart"></div>
  </section>
</template>

<script setup lang="ts">
  import { nextTick, onMounted, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';

  const props = defineProps<{
    ranges: readonly string[];
    selectedRange: string;
    spreadHistory: Array<{ label: string; value: number }>;
  }>();

  defineEmits<{
    (event: 'update:selectedRange', value: string): void;
  }>();

  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>);

  function renderChart() {
    const chartSeries = props.spreadHistory.map((item) => item.value);
    const chartLabels = props.spreadHistory.map((item) => item.label);
    nextTick(() => {
      chart?.setOptions({
        grid: { left: 56, right: 20, top: 30, bottom: 76 },
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: chartLabels,
          boundaryGap: false,
          axisLine: { lineStyle: { color: '#d7deea' } },
          axisLabel: { color: '#70819c', fontSize: 12 },
        },
        yAxis: {
          type: 'value',
          min: chartSeries.length ? undefined : -4,
          max: chartSeries.length ? undefined : 2,
          splitNumber: 3,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: '#70819c', fontSize: 12 },
          splitLine: { lineStyle: { color: '#eef2f8' } },
        },
        dataZoom: [
          {
            type: 'inside',
            start: 0,
            end: 100,
          },
          {
            type: 'slider',
            bottom: 16,
            height: 22,
            borderColor: '#dbe7fb',
            fillerColor: 'rgba(84, 138, 255, 0.12)',
            backgroundColor: '#f4f8ff',
            handleStyle: { color: '#4f7bf5' },
          },
        ],
        series: [
          {
            data: chartSeries,
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: { color: '#ff3535', width: 3 },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(255, 53, 53, 0.22)' },
                  { offset: 1, color: 'rgba(255, 53, 53, 0.03)' },
                ],
              },
            },
          },
        ],
      });
    });
  }

  watch(() => props.spreadHistory, renderChart, { deep: true });
  onMounted(renderChart);
</script>

<style scoped lang="less">
  .cross-card {
    padding: 16px 18px 18px;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
  }

  .card-head,
  .card-head--between {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  .card-head--between {
    align-items: center;
  }

  .card-head h3 {
    margin: 0;
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.012em;
    color: #162845;
  }

  .card-head span {
    display: inline-block;
    margin-top: 4px;
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
  }

  .range-tabs {
    display: flex;
    gap: 8px;
  }

  .range-tabs button {
    height: 32px;
    min-width: 42px;
    padding: 0 12px;
    border: 1px solid #d7e2ef;
    border-radius: 10px;
    background: #fff;
    color: #47617f;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }

  .range-tabs button.active {
    border-color: rgba(201, 72, 72, 0.18);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px rgba(201, 72, 72, 0.08);
  }

  .gear-btn {
    width: 38px;
    height: 38px;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
    background: #ffffff;
    color: #8a6c49;
    cursor: pointer;
  }

  .gear-btn--mini {
    width: 32px;
    height: 32px;
  }

  .spread-chart {
    height: 238px;
  }
</style>
