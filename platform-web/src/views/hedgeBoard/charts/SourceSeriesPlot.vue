<template>
  <div
    ref="chartRef"
    class="source-series-plot"
    :class="{
      'source-series-plot--drivers': mode === 'gold-drivers',
      'source-series-plot--binance': mode === 'binance',
    }"
    role="img"
    :aria-label="description"
  ></div>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch, type Ref } from 'vue';
  import { useResearchViewState } from '../composables/researchWorkspace';
  import type { EChartsOption } from 'echarts';
  import type { MacroDashboardSeries } from '@/api/hedgeResearch';
  import { useECharts } from '@/hooks/web/useECharts';
  import {
    buildSourceSeriesOptions,
    buildRegionalStackOptions,
    buildGoldDriversOptions,
    buildSourceCurveOptions,
    buildDistributionOptions,
    buildBinanceOptions,
    buildStablecoinOptions,
    unitText,
  } from './sourceSeriesOptions';

  const props = defineProps<{
    stateKey?: string;
    series: MacroDashboardSeries[];
    colors: string[];
    unitLabel?: string;
    barSeriesIds?: string[];
    mode?:
      | 'time'
      | 'curve'
      | 'regional-stack'
      | 'gold-drivers'
      | 'distribution'
      | 'binance'
      | 'stablecoins';
  }>();
  const savedWindow = useResearchViewState<{
    startValue?: number | string;
    endValue?: number | string;
  } | null>(
    `source-window:${props.stateKey || props.series.map((series) => series.seriesId).join(',')}`,
    null,
  );
  onBeforeUnmount(() => {
    const option = chart.getInstance()?.getOption() as
      | { dataZoom?: Array<{ startValue?: number | string; endValue?: number | string }> }
      | undefined;
    const zoom = option?.dataZoom?.[0];
    if (zoom) savedWindow.value = { startValue: zoom.startValue, endValue: zoom.endValue };
  });
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
      const options = (
        props.mode === 'distribution'
          ? buildDistributionOptions(props.series)
          : props.mode === 'binance'
          ? buildBinanceOptions(props.series, props.colors)
          : props.mode === 'stablecoins'
          ? buildStablecoinOptions(props.series, props.colors)
          : props.mode === 'gold-drivers'
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
            )
      ) as EChartsOption;
      if (savedWindow.value && Array.isArray(options.dataZoom)) {
        options.dataZoom = options.dataZoom.map((zoom) => ({
          ...zoom,
          start: undefined,
          end: undefined,
          ...savedWindow.value,
        }));
      }
      chart.setOptions(options);
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

  .source-series-plot--drivers,
  .source-series-plot--binance {
    min-height: 580px;
    max-height: 700px;
  }
</style>
