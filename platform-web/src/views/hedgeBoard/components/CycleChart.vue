<template><div ref="host" class="cycle-plot" role="img" :aria-label="label"></div></template>
<script setup lang="ts">
  import { nextTick, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';

  const props = defineProps<{ options: EChartsOption; label: string }>();
  const host = ref<HTMLDivElement | null>(null),
    chart = useECharts(host as Ref<HTMLDivElement>);
  watch(
    () => props.options,
    async (value) => {
      await nextTick();
      chart.setOptions(value, true);
    },
    { immediate: true },
  );
</script>
<style scoped>
  .cycle-plot {
    width: 100%;
    height: 380px;
  }
</style>
