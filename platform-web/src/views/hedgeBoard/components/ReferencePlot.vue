<template>
  <ChartExpand :title="title"
    ><article class="reference-plot"
      ><h3>{{ title }}</h3>
      <div
        ref="element"
        class="plot"
        role="img"
        :aria-label="title + '，拖动时间轴并悬浮查看数据'"
      ></div> </article
  ></ChartExpand>
</template>
<script setup lang="ts">
  import { ref, watch, nextTick, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import ChartExpand from './ChartExpand.vue';

  export interface ReferenceLine {
    key: string;
    name: string;
    color: string;
    type?: 'line' | 'bar' | 'scatter';
    stack?: string;
    signed?: boolean;
  }
  const props = defineProps<{
    title: string;
    rows: Record<string, unknown>[];
    lines: ReferenceLine[];
    unit?: string;
  }>();
  const element = ref<HTMLDivElement | null>(null);
  const chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  const num = (v: unknown) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  watch(
    [() => props.rows, () => props.lines],
    async () => {
      await nextTick();
      if (!element.value) return;
      chart.setOptions(
        {
          animation: false,
          legend: { type: 'scroll', top: 8, textStyle: { fontSize: 11, color: '#59718a' } },
          grid: { top: 60, left: 64, right: 25, bottom: 70 },
          tooltip: {
            trigger: 'axis',
            confine: true,
            valueFormatter: (v: unknown) =>
              num(v) == null ? '—' : Number(v).toFixed(2) + (props.unit || '%'),
          },
          xAxis: {
            type: 'category',
            data: props.rows.map((r) => r.date),
            axisLabel: { hideOverlap: true, color: '#6a7e91' },
          },
          yAxis: {
            type: 'value',
            scale: true,
            name: props.unit || '%',
            splitLine: { lineStyle: { color: '#e7edf4' } },
          },
          dataZoom: [
            {
              type: 'inside',
              filterMode: 'filter',
              zoomOnMouseWheel: 'ctrl',
              moveOnMouseWheel: false,
            },
            { type: 'slider', filterMode: 'filter', height: 20, bottom: 10 },
          ],
          series: props.lines.map((l) => ({
            name: l.name,
            type: l.type || 'line',
            stack: l.stack,
            showSymbol: l.type === 'scatter',
            symbolSize: 5,
            connectNulls: false,
            data: props.rows.map((r) => num(r[l.key])),
            lineStyle: { width: 1.7 },
            barMaxWidth: 20,
            itemStyle: l.signed
              ? { color: (p: { value: number }) => (p.value >= 0 ? '#087f80' : '#b44b53') }
              : { color: l.color },
          })),
        } as EChartsOption,
        true,
      );
    },
    { immediate: true },
  );
</script>
<style scoped>
  .reference-plot {
    padding: 16px;
    border: 1px solid #dce5ef;
    border-radius: 12px;
    background: #fff;
  }

  h3 {
    margin: 0;
    color: #17324d;
    font-size: 15px;
  }

  .plot {
    width: 100%;
    min-width: 0;
    height: 370px;
  }
</style>
