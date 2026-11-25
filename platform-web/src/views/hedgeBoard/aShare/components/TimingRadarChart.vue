<template>
  <div ref="plot" class="timing-plot" role="img" :aria-label="label"></div>
</template>

<script setup lang="ts">
  import { ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';

  const props = defineProps<{ option: EChartsOption; label: string }>();
  const plot = ref<HTMLDivElement>() as Ref<HTMLDivElement>;
  const chart = useECharts(plot);
  watch(
    () => props.option,
    (option) => chart.setOptions(option, false),
    { immediate: true },
  );
</script>

<style scoped>
  .timing-plot {
    width: 100%;
    min-width: 0;
    height: 100%;
  }
</style>
