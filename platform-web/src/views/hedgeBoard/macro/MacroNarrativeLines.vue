<template
  ><div ref="chartRef" class="narrative-lines" role="img" aria-label="宏观叙事强度历史曲线"></div
></template>
<script setup lang="ts">
  import { ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import type { NarrativeDriver } from '@/api/macroNarratives';
  import { useECharts } from '@/hooks/web/useECharts';
  import { narrativeLines } from './narrativeOptions';

  const props = defineProps<{
    drivers: NarrativeDriver[];
    end: string;
    years: number;
    selected: string;
  }>();
  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>, 'light');
  watch(
    () => [props.drivers, props.end, props.years, props.selected],
    () =>
      chart.setOptions(
        narrativeLines(props.drivers, props.end, props.years, props.selected) as EChartsOption,
      ),
    { immediate: true },
  );
</script>
<style scoped>
  .narrative-lines {
    width: 100%;
    min-width: 0;
    height: 390px;
  }
</style>
