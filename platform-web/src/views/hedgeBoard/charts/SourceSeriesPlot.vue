<template>
  <div
    ref="chartRef"
    class="source-series-plot"
    :class="{
      'source-series-plot--drivers': mode === 'gold-drivers',
      'source-series-plot--binance': mode === 'binance',
      'source-series-plot--independent': independentAxes,
    }"
    role="img"
    :aria-label="description"
    @click="selectObservation"
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
    buildIndependentSeriesOptions,
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
    independentAxes?: boolean;
    pickDate?: boolean;
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
  const emit = defineEmits<{ pick: [date: string] }>();
  function selectObservation(event: MouseEvent) {
    if (!props.pickDate || !chartRef.value) return;
    const instance = chart.getInstance();
    const bounds = chartRef.value.getBoundingClientRect();
    const pixel = [event.clientX - bounds.left, event.clientY - bounds.top];
    if (!instance?.containPixel({ gridIndex: 0 }, pixel)) return;
    const time = Number(instance.convertFromPixel({ xAxisIndex: 0 }, pixel[0]));
    let distance = Infinity,
      selected = '';
    for (const series of props.series)
      for (const row of series.observations) {
        const delta = Math.abs(Date.parse(row.date) - time);
        if (row.value != null && delta < distance) {
          distance = delta;
          selected = row.date;
        }
      }
    if (selected) emit('pick', selected);
  }
  let renderedIdentity = '';
  const description = computed(
    () =>
      props.series.map((s) => `${s.label}，${unitText(s.unit)}`).join('；') +
      (props.mode === 'curve'
        ? '。横轴为合约月份，详细数据可切换至表格。'
        : '。可拖动下方范围选择器查看区间，详细数据可切换至表格。'),
  );
  watch(
    () => [
      props.series,
      props.colors,
      props.unitLabel,
      props.mode,
      props.barSeriesIds,
      props.independentAxes,
    ],
    () => {
      const identity = `${props.stateKey || props.series.map((s) => s.seriesId).join(',')}:${
        props.mode || 'time'
      }`;
      const currentZoom =
        renderedIdentity === identity
          ? (
              chart.getInstance()?.getOption().dataZoom as
                | Array<{ start?: number; end?: number }>
                | undefined
            )?.[0]
          : undefined;
      const options = (
        props.independentAxes
          ? buildIndependentSeriesOptions(props.series, props.colors, props.unitLabel)
          : props.mode === 'distribution'
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
      if (currentZoom && Array.isArray(options.dataZoom)) {
        options.dataZoom = options.dataZoom.map((zoom) => ({
          ...zoom,
          start: currentZoom.start,
          end: currentZoom.end,
          startValue: undefined,
          endValue: undefined,
        }));
      } else if (savedWindow.value && Array.isArray(options.dataZoom)) {
        options.dataZoom = options.dataZoom.map((zoom) => ({
          ...zoom,
          start: undefined,
          end: undefined,
          ...savedWindow.value,
        }));
      }
      chart.setOptions(options);
      renderedIdentity = identity;
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
  .source-series-plot--binance,
  .source-series-plot--independent {
    min-height: 580px;
    max-height: 700px;
  }
</style>
