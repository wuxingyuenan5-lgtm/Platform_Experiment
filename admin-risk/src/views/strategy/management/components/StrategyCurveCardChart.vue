<template>
  <article class="curve-card">
    <header>
      <div>
        <h3>{{ item.title }}</h3>
        <p>{{ item.amount }} {{ item.unit }}</p>
      </div>
    </header>

    <div ref="chartRef" class="curve-stage"></div>
  </article>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { StrategyCurveCard } from '../types';

  const props = defineProps<{ item: StrategyCurveCard }>();

  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);

  const lineColor = computed(() => {
    if (props.item.tone === 'negative') return '#d8585f';
    if (props.item.tone === 'neutral') return '#45556c';
    return '#cf3f4f';
  });

  async function renderChart() {
    await setOptions({
      color: [lineColor.value],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line' },
      },
      grid: {
        left: 18,
        right: 10,
        top: 26,
        bottom: 28,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: props.item.points.map((point) => point.date),
        boundaryGap: false,
        axisTick: { show: false },
        axisLabel: {
          color: '#98a2b3',
          hideOverlap: true,
        },
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.18)',
            type: 'dashed',
          },
        },
        axisLabel: {
          color: '#98a2b3',
        },
      },
      series: [
        {
          name: props.item.title,
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 3, color: lineColor.value },
          areaStyle: { opacity: 0.06, color: lineColor.value },
          data: props.item.points.map((point) => point.value),
        },
      ],
    });
    await nextTick();
    resize();
  }

  watch(() => props.item, renderChart, { deep: true });
  onMounted(renderChart);
</script>

<style scoped lang="less">
  .curve-card {
    padding: 18px 18px 14px;
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,.97), rgba(255,251,245,.94));
    box-shadow: 0 18px 40px rgba(28,35,40,.05);
    border: 1px solid rgba(201,164,95,.14);
  }

  .curve-card h3 {
    margin: 0;
    color: #15252a;
    font-size: 16px;
  }

  .curve-card p {
    margin: 8px 0 0;
    color: #8a94a1;
    font-size: 13px;
  }

  .curve-stage {
    height: 210px;
    margin-top: 10px;
  }
</style>
