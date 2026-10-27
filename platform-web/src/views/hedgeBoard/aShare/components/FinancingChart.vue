<template>
  <ChartExpand :title="title">
    <article class="financing-chart">
      <header
        ><h3>{{ title }}</h3
        ><div class="ranges"
          ><button
            v-for="p in [90, 365, 1095, 0]"
            :key="p"
            :class="{ active: range === p }"
            :aria-pressed="range === p"
            @click="range = p"
            >{{ p === 90 ? '3个月' : p === 365 ? '1年' : p ? '3年' : '全部' }}</button
          ></div
        ></header
      >
      <p v-if="note" class="definition">{{ note }}</p>
      <p v-if="!rows.length" class="empty">暂无有效历史</p>
      <div
        v-else
        ref="element"
        class="plot"
        role="img"
        :aria-label="`${title}，可拖动下方时间范围并悬浮查看数值`"
      ></div>
    </article>
  </ChartExpand>
</template>

<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import ChartExpand from '../../components/ChartExpand.vue';

  export interface FinanceLine {
    key: string;
    name: string;
    color: string;
    unit: string;
    bar?: boolean;
    right?: boolean;
    stack?: string;
  }
  export interface FinanceRow {
    date: string;
    [key: string]: string | number | null | boolean | undefined;
  }
  const props = defineProps<{
    title: string;
    rows: FinanceRow[];
    lines: FinanceLine[];
    note?: string;
  }>();
  const element = ref<HTMLDivElement | null>(null);
  const chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  const range = ref(365);
  const numeric = (value: unknown) =>
    value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
  const filtered = computed(() => {
    const last = props.rows.at(-1)?.date;
    if (!last || !range.value) return props.rows;
    const start = new Date(last + 'T00:00:00Z');
    start.setUTCDate(start.getUTCDate() - range.value);
    return props.rows.filter((r) => r.date >= start.toISOString().slice(0, 10));
  });
  const escape = (value: unknown) =>
    String(value).replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c),
    );
  const format = (v: unknown) =>
    numeric(v) == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 4 });
  watch(
    [filtered, () => props.lines],
    async () => {
      await nextTick();
      const rows = filtered.value;
      if (!element.value || !rows.length) return;
      const left = props.lines.find((l) => !l.right)?.unit || '';
      const right = props.lines.find((l) => l.right)?.unit || '';
      const option = {
        animation: false,
        color: props.lines.map((l) => l.color),
        legend: {
          top: 0,
          type: 'scroll',
          textStyle: { fontSize: 11, color: '#65809b', fontFamily: 'inherit' },
        },
        grid: { left: 65, right: right ? 70 : 28, top: 65, bottom: 65 },
        tooltip: {
          trigger: 'axis',
          confine: true,
          axisPointer: { type: 'cross' },
          formatter: (items: Array<{ dataIndex: number; seriesIndex: number; marker: string }>) => {
            if (!items.length) return '';
            const row = rows[items[0].dataIndex];
            const texts = [
              escape(row.date) + (row.contract ? ` · ${escape(row.contract)}` : ''),
              ...items.map((item) => {
                const l = props.lines[item.seriesIndex];
                return `${item.marker}${escape(l.name)}：${format(row[l.key])} ${escape(l.unit)}`;
              }),
            ];
            if (row.total !== undefined) texts.push(`合计：${format(row.total)} 亿元`);
            if (row.partialWeek) texts.push('本周截至当前交易日');
            return texts.join('<br/>');
          },
        },
        xAxis: {
          type: 'category',
          data: rows.map((r) => r.date),
          boundaryGap: props.lines.some((l) => l.bar),
          axisLabel: {
            color: '#71869e',
            hideOverlap: true,
            formatter: (value: string) => value.slice(2),
            fontSize: 11,
          },
        },
        yAxis: [left, right].map((unit, i) => ({
          type: 'value',
          name: unit,
          position: i ? 'right' : 'left',
          show: !i || !!right,
          scale: !props.lines.some((l) => !!l.right === !!i && l.bar),
          splitLine: { show: !i, lineStyle: { color: '#e8eef5' } },
          axisLabel: { color: '#71869e' },
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
          type: l.bar ? 'bar' : 'line',
          yAxisIndex: l.right ? 1 : 0,
          stack: l.stack,
          data: rows.map((r) => numeric(r[l.key])),
          showSymbol: rows.filter((r) => numeric(r[l.key]) != null).length === 1,
          symbolSize: 7,
          connectNulls: false,
          lineStyle: { width: l.color === '#171717' ? 2.2 : 1.5 },
          itemStyle:
            l.bar && !l.stack
              ? { color: (p: { value: number }) => (p.value >= 0 ? '#e87478' : '#35a47b') }
              : { color: l.color },
        })),
      } as EChartsOption;
      chart.setOptions(option, true);
    },
    { immediate: true },
  );
</script>

<style scoped>
  .financing-chart {
    margin: 14px 0;
    padding: 18px;
    border: 1px solid #d7e3ee;
    border-radius: 14px;
    background: linear-gradient(#fff, #f4f9fc);
    color: #123247;
    font-family: inherit;
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    padding-right: 38px;
    gap: 12px;
  }

  h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
  }

  .ranges {
    display: flex;
    gap: 6px;
  }

  button {
    padding: 4px 10px;
    border: 1px solid #d7e3ee;
    border-radius: 6px;
    background: #fff;
    color: #42617e;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  button.active {
    background: #edf3ff;
    color: #2563eb;
  }

  .definition {
    margin: 10px 0;
    color: #71869e;
    font-size: 12px;
  }

  .plot {
    width: 100%;
    height: 380px;
  }

  .empty {
    padding: 35px;
    color: #71869e;
  }
</style>
