<template><div ref="root" class="demo-chart" role="img" :aria-label="label"></div></template>
<script setup lang="ts">
  import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
  import type { EChartsType } from 'echarts/core';
  import { MarkAreaComponent, MarkLineComponent } from 'echarts/components';
  import echarts from '@/utils/lib/echarts';

  echarts.use([MarkAreaComponent, MarkLineComponent]);
  const props = defineProps<{ option: any; label: string }>();
  const root = ref<HTMLDivElement>();
  let chart: EChartsType | undefined;
  let observer: ResizeObserver | undefined;
  const render = () => {
    chart?.setOption({ ...props.option, animation: false }, { notMerge: true });
  };
  onMounted(() => {
    if (!root.value) return;
    chart = echarts.init(root.value, undefined, { renderer: 'svg' });
    observer = new ResizeObserver(() => chart?.resize());
    observer.observe(root.value);
    render();
  });
  watch(() => props.option, render, { deep: true });
  onBeforeUnmount(() => {
    observer?.disconnect();
    chart?.dispose();
    chart = undefined;
  });
</script>
<style scoped>
  .demo-chart {
    width: 100%;
    min-width: 0;
    height: 330px;
  }
</style>
