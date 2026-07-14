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
    if (props.item.tone === 'neutral') return '#4f647d';
    return '#2fa86e';
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
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 16,
          bottom: 4,
          borderColor: 'rgba(205, 214, 224, 0.8)',
          fillerColor: 'rgba(125, 167, 255, 0.12)',
          backgroundColor: 'rgba(240, 244, 248, 0.9)',
          brushSelect: false,
        },
      ],
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
    min-width: 0;
    padding: 18px 18px 14px;
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(255,255,255,.99), rgba(248,250,252,.98));
    box-shadow: 0 14px 34px rgba(28,35,40,.04);
    border: 1px solid rgba(223,230,240,.92);
  }

  .curve-card h3 {
    margin: 0;
    color: #17222d;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 0.01em;
  }

  .curve-card p {
    margin: 6px 0 0;
    color: #52606f;
    font-size: 13px;
    font-weight: 600;
  }

  .curve-stage {
    height: 210px;
    margin-top: 10px;
    min-width: 0;
  }
</style>
