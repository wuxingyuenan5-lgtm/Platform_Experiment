<template>
  <ChartExpand :title="title">
    <article class="ai-chart">
      <header
        ><h3>{{ title }}</h3
        ><div class="ranges"
          ><button
            v-for="n in [365, 1826, 3653, 0]"
            :key="n"
            :aria-pressed="range === n"
            :class="{ active: range === n }"
            @click="range = n"
            >{{ n === 365 ? '1年' : n === 1826 ? '5年' : n ? '10年' : '全部' }}</button
          ></div
        ></header
      >
      <p v-if="note" class="note">{{ note }}</p>
      <div
        v-show="rows.length"
        ref="element"
        class="plot"
        role="img"
        :aria-label="title + '，可悬浮查看数值并拖动时间范围'"
      ></div
      ><p v-if="!rows.length" class="empty">暂无有效历史</p>
    </article>
  </ChartExpand>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import ChartExpand from '../components/ChartExpand.vue';
  import { numeric } from './model';

  export interface AiLine {
    key: string;
    name: string;
    color: string;
    bar?: boolean;
    scatter?: boolean;
    observedLine?: boolean;
    right?: boolean;
    unit?: string;
  }
  const props = defineProps<{
    title: string;
    rows: { date: string; [key: string]: unknown }[];
    lines: AiLine[];
    unit?: string;
    note?: string;
  }>();
  const range = ref(1826);
  const element = ref<HTMLDivElement | null>(null);
  const chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  const filtered = computed(() => {
    const end = props.rows.at(-1)?.date;
    if (!end || !range.value) return props.rows;
    const d = new Date(end + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() - range.value);
    return props.rows.filter((r) => r.date >= d.toISOString().slice(0, 10));
  });
  watch(
    [filtered, () => props.lines],
    async () => {
      await nextTick();
      if (!element.value || !filtered.value.length) return;
      const rows = filtered.value;
      const temporal = props.lines.every((line) => line.scatter || line.observedLine);
      chart.setOptions(
        {
          animation: false,
          color: props.lines.map((l) => l.color),
          legend: { type: 'scroll', top: 4, textStyle: { color: '#58748e', fontSize: 11 } },
          grid: {
            left: 66,
            right: props.lines.some((l) => l.right) ? 65 : 25,
            top: 68,
            bottom: 66,
          },
          tooltip: {
            trigger: 'axis',
            confine: true,
            valueFormatter: (v: unknown) =>
              numeric(Array.isArray(v) ? v[1] : v) == null
                ? '—'
                : Number(Array.isArray(v) ? v[1] : v).toLocaleString('zh-CN', {
                    maximumFractionDigits: 3,
                  }),
          },
          xAxis: {
            type: temporal ? 'time' : 'category',
            data: rows.map((r) => r.date),
            boundaryGap: props.lines.some((l) => l.bar),
            axisLabel: { hideOverlap: true, color: '#6c8197', fontSize: 11 },
          },
          yAxis: [0, 1].map((i) => ({
            type: 'value',
            scale: !props.lines.some((l) => !!l.right === !!i && l.bar),
            position: i ? 'right' : 'left',
            show: !i || props.lines.some((l) => l.right),
            name: i ? props.lines.find((l) => l.right)?.unit || '%' : props.unit || '十亿美元',
            splitLine: { show: !i, lineStyle: { color: '#e8eef5' } },
            axisLabel: { color: '#6c8197', fontSize: 11 },
          })),
          dataZoom: [
            {
              type: 'inside',
              filterMode: 'filter',
              zoomOnMouseWheel: 'ctrl',
              moveOnMouseWheel: false,
            },
            { type: 'slider', filterMode: 'filter', height: 20, bottom: 8 },
          ],
          series: props.lines.map((l) => ({
            name: l.name,
            type: l.scatter ? 'scatter' : l.bar ? 'bar' : 'line',
            symbolSize: l.scatter ? 7 : 4,
            showSymbol: !!(l.scatter || l.observedLine),
            connectNulls: false,
            yAxisIndex: l.right ? 1 : 0,
            data: rows.map((r) => (temporal ? [r.date, numeric(r[l.key])] : numeric(r[l.key]))),
            lineStyle: { width: 1.8 },
            barMaxWidth: 25,
          })),
        } as EChartsOption,
        true,
      );
    },
    { immediate: true, deep: true },
  );
</script>
<style scoped>
  .ai-chart {
    min-width: 0;
    padding: 16px;
    border: 1px solid #dce6ef;
    border-radius: 12px;
    background: linear-gradient(#fff, #f5f9fc);
  }

  header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 12px;
  }

  h3 {
    margin: 0;
    color: #16334a;
    font-size: 15px;
  }

  .ranges {
    display: flex;
    gap: 5px;
  }

  button {
    padding: 3px 9px;
    border: 1px solid #dbe5ef;
    border-radius: 5px;
    background: #fff;
    color: #58748e;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  button.active {
    background: #edf3ff;
    color: #2563eb;
  }

  .plot {
    width: 100%;
    height: 360px;
  }

  .note,
  .empty {
    margin: 10px 0;
    color: #71869d;
    font-size: 12px;
  }

  .empty {
    padding: 60px 0;
  }
</style>
