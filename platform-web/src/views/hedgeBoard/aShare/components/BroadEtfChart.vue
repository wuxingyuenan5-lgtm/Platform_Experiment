<template>
  <div ref="plot" class="plot" role="img" :aria-label="title"></div>
</template>
<script setup lang="ts">
  import { nextTick, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import { broadChartOption, type EtfPeriod } from './broadEtfAnalysis';

  const props = defineProps<{
    rows: EtfPeriod[];
    label: string;
    title: string;
    hasIndex?: boolean;
    showMarketCapRatio?: boolean;
  }>();
  const plot = ref<HTMLDivElement | null>(null);
  const chart = useECharts(plot as Ref<HTMLDivElement>, 'light');
  watch(
    [
      () => props.rows,
      () => props.label,
      () => props.hasIndex,
      () => props.showMarketCapRatio,
      plot,
    ],
    async () => {
      await nextTick();
      chart.setOptions(
        broadChartOption(
          props.rows,
          props.label,
          props.hasIndex !== false,
          props.showMarketCapRatio,
        ) as EChartsOption,
        true,
      );
    },
    { immediate: true },
  );
</script>
<style scoped>
  .plot {
    width: 100%;
    min-width: 0;
    height: 440px;
  }

  @media (max-width: 650px) {
    .plot {
      height: 400px;
    }
  }
</style>
