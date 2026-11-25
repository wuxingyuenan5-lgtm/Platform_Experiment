<template>
  <article class="capital-bars">
    <header>
      <h3>{{ title }}</h3>
      <slot name="toolbar"></slot>
      <button type="button" :aria-pressed="table" @click="table = !table">{{
        table ? '图表' : '查看数据'
      }}</button>
    </header>
    <p v-if="note" class="note">{{ note }}</p>
    <p v-if="!rows.length" class="empty">暂无有效数据</p>
    <div
      v-show="!table && rows.length"
      ref="element"
      class="plot"
      role="img"
      :aria-label="title"
    ></div>
    <slot v-if="table && rows.length && $slots['data-table']" name="data-table"></slot>
    <div v-else-if="table && rows.length" class="scroll"
      ><table
        ><thead
          ><tr
            ><th>分类</th><th v-for="l in lines" :key="l.key">{{ l.name }}（{{ l.unit }}）</th></tr
          ></thead
        ><tbody
          ><tr v-for="r in rows" :key="String(r.date)"
            ><th>{{ r.date }}</th
            ><td v-for="l in lines" :key="l.key">{{ fmt(r[l.key]) }}</td></tr
          ></tbody
        ></table
      ></div
    >
  </article>
</template>
<script setup lang="ts">
  import { ref, watch, nextTick, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { FinanceLine, FinanceRow } from './FinancingChart.vue';

  const props = defineProps<{
    title: string;
    rows: FinanceRow[];
    lines: FinanceLine[];
    note?: string;
    zoomable?: boolean;
  }>();
  const element = ref<HTMLDivElement>();
  const table = ref(false);
  const chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  const num = (v: unknown) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  const fmt = (v: unknown) => num(v)?.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) ?? '—';
  watch(
    [() => props.rows, () => props.lines, table],
    async () => {
      await nextTick();
      if (!element.value || table.value || !props.rows.length) return;
      chart.setOptions(
        {
          animation: false,
          tooltip: { trigger: 'axis', confine: true },
          legend: { type: 'scroll', top: 5 },
          grid: { left: 65, right: 55, top: 65, bottom: props.rows.length > 15 ? 100 : 60 },
          dataZoom:
            props.zoomable && props.rows.length > 12
              ? [{ type: 'slider', bottom: 12, height: 20, start: 0, end: 100 }, { type: 'inside' }]
              : [],
          xAxis: {
            type: 'category',
            data: props.rows.map((r) => r.date),
            axisLabel: { rotate: props.rows.length > 15 ? 50 : 0 },
          },
          yAxis: [
            { type: 'value', name: props.lines.find((l) => !l.right)?.unit || '' },
            {
              type: 'value',
              name: props.lines.find((l) => l.right)?.unit || '',
              show: props.lines.some((l) => l.right),
            },
          ],
          series: props.lines.map((l) => ({
            name: l.name,
            type: l.bar === false ? 'line' : 'bar',
            yAxisIndex: l.right ? 1 : 0,
            itemStyle: { color: l.color },
            barMaxWidth: 28,
            connectNulls: false,
            data: props.rows.map((r) => num(r[l.key])),
          })),
        },
        true,
      );
    },
    { immediate: true },
  );
</script>
<style scoped>
  .capital-bars {
    min-width: 0;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface);
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 15px;
  }

  button {
    padding: 5px 9px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: transparent;
    color: inherit;
    cursor: pointer;
  }

  .note,
  .empty {
    color: var(--strategy-text-3);
    font-size: 12px;
    line-height: 1.7;
  }

  .plot {
    height: 370px;
  }

  .scroll {
    max-height: 400px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 10px;
    border-bottom: 1px solid var(--strategy-border);
    text-align: right;
    white-space: nowrap;
  }

  th:first-child {
    text-align: left;
  }
</style>
