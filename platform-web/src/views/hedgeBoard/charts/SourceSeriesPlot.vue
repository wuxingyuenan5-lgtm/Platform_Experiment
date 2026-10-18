<template>
  <div
    ref="chartRef"
    class="source-series-plot"
    :class="{ 'source-series-plot--drivers': mode === 'gold-drivers' }"
    role="img"
    :aria-label="description"
  ></div>
</template>

<script setup lang="ts">
  import { computed, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import type { MacroDashboardSeries } from '@/api/hedgeResearch';
  import { useECharts } from '@/hooks/web/useECharts';
  import {
    buildSourceSeriesOptions,
    buildRegionalStackOptions,
    buildGoldDriversOptions,
    buildSourceCurveOptions,
    unitText,
  } from './sourceSeriesOptions';

  const props = defineProps<{
    series: MacroDashboardSeries[];
    colors: string[];
    unitLabel?: string;
    barSeriesIds?: string[];
    mode?: 'time' | 'curve' | 'regional-stack' | 'gold-drivers';
  }>();
  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>, 'light');
  const description = computed(
    () =>
      props.series.map((s) => `${s.label}，${unitText(s.unit)}`).join('；') +
      (props.mode === 'curve'
        ? '。横轴为合约月份，详细数据可切换至表格。'
        : '。可拖动下方范围选择器查看区间，详细数据可切换至表格。'),
  );
  watch(
    () => [props.series, props.colors, props.unitLabel, props.mode, props.barSeriesIds],
    () => {
      chart.setOptions(
        (props.mode === 'gold-drivers'
          ? buildGoldDriversOptions(props.series, props.colors)
          : props.mode === 'regional-stack'
          ? buildRegionalStackOptions(props.series)
          : props.mode === 'curve'
          ? buildSourceCurveOptions(props.series, props.colors[0], props.unitLabel)
          : buildSourceSeriesOptions(
              props.series,
              props.colors,
              props.unitLabel,
              props.barSeriesIds,
            )) as EChartsOption,
      );
    },
    { immediate: true },
  );
</script>

<style scoped>
  .source-series-plot {
    width: 100%;
    min-width: 0;
    height: auto;
    aspect-ratio: 1.8;
    min-height: 280px;
    max-height: 420px;
  }

  .source-series-plot--drivers {
    min-height: 580px;
    max-height: 700px;
  }
</style>
