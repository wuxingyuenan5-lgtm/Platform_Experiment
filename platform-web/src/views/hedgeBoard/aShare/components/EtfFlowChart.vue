<template>
  <ChartExpand v-slot="{ expanded }" :title="title">
    <article class="flow-chart">
      <header
        ><h3>{{ title }}</h3
        ><button @click="table = !table">{{ table ? '查看图表' : '查看数据' }}</button></header
      >
      <p>{{ note }}<span v-if="demo" class="demo"> · Demo · 合成数据</span></p>
      <p v-if="items.some((r) => !r.current.complete || !r.previous.complete)"
        >* 表示至少一期输入不完整；金额为可得合计，覆盖数见数据表。</p
      >
      <div
        v-show="!table && hasValues"
        ref="element"
        class="plot"
        role="img"
        :aria-label="title"
        :style="{
          height: expanded ? 'calc(100vh - 220px)' : `${Math.max(310, items.length * 30 + 90)}px`,
          minHeight: '260px',
        }"
      ></div>
      <div v-if="table" class="table-scroll"
        ><table
          ><thead
            ><tr
              ><th>分类</th><th v-for="s in series" :key="s.key">{{ s.name }}（{{ unit }}）</th
              ><th>比较期覆盖</th><th>观察期覆盖</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in items" :key="row.name"
              ><td>{{ row.name }}</td
              ><td v-for="s in series" :key="s.key">{{ format(value(row, s.key)) }}</td
              ><td>{{ row.previous.covered }}/{{ row.previous.expected }}</td
              ><td>{{ row.current.covered }}/{{ row.current.expected }}</td></tr
            ></tbody
          ></table
        ></div
      >
      <p v-if="!hasValues">此区间暂无符合计算条件的有效数据；缺失值不绘制为零。</p>
    </article>
  </ChartExpand>
</template>
<script setup lang="ts">
  import { computed, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import ChartExpand from '../../components/ChartExpand.vue';
  import type { FlowGroup } from '@/api/etfFlows';

  const props = defineProps<{
    title: string;
    note: string;
    items: FlowGroup[];
    kind?: 'comparison' | 'ratio' | 'recovery';
    demo?: boolean;
  }>();
  const element = ref<HTMLDivElement>();
  const table = ref(false);
  const chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  const unit = computed(() => (props.kind === 'ratio' || props.kind === 'recovery' ? '%' : '亿元'));
  const series = computed(() =>
    props.kind === 'recovery'
      ? [{ key: 'recovery', name: '回补／前期净赎回', color: '#cc8b3c' }]
      : props.kind === 'comparison' || props.kind === 'ratio'
      ? [
          { key: 'previous', name: '比较期', color: '#34567e' },
          { key: 'current', name: '观察期', color: '#cc8b3c' },
        ]
      : [{ key: 'current', name: '净流入', color: '#c44235' }],
  );
  function value(row: FlowGroup, key: string): number | null {
    const raw =
      key === 'recovery'
        ? row.recovery
        : row[key as 'current' | 'previous'][props.kind === 'ratio' ? 'ratio' : 'flow'];
    return raw == null || !Number.isFinite(Number(raw)) ? null : Number(raw);
  }
  const hasValues = computed(() =>
    props.items.some((row) => series.value.some((s) => value(row, s.key) !== null)),
  );
  const format = (v: number | null) =>
    v == null ? '—' : v.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  watch(
    () => [props.items, props.kind, table.value],
    () => {
      chart.setOptions(
        {
          animation: false,
          grid: { left: 12, right: 62, top: 45, bottom: 35, containLabel: true },
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            valueFormatter: (v) => (v == null ? '缺失' : `${format(Number(v))} ${unit.value}`),
          },
          legend: { top: 3, type: 'scroll' },
          xAxis: {
            type: 'value',
            name: unit.value,
            splitLine: { lineStyle: { color: '#edf1f5' } },
          },
          yAxis: {
            type: 'category',
            inverse: true,
            data: props.items.map(
              (r) => r.name + (!r.current.complete || !r.previous.complete ? ' *' : ''),
            ),
            axisLabel: { width: 112, overflow: 'truncate', fontSize: 11 },
            axisTick: { show: false },
          },
          series: series.value.map((s) => ({
            name: s.name,
            type: 'bar',
            itemStyle: { color: s.color },
            barMaxWidth: 20,
            data: props.items.map((row) => {
              const v = value(row, s.key);
              return {
                value: v,
                itemStyle: { color: !props.kind && v != null && v < 0 ? '#2b7a50' : s.color },
              };
            }),
            label: {
              show: props.items.length <= 12,
              position: 'right',
              fontSize: 10,
              formatter: (p) => (p.value == null ? '' : format(Number(p.value))),
            },
          })),
        },
        true,
      );
    },
    { immediate: true },
  );
</script>
<style scoped>
  .flow-chart {
    min-width: 0;
    padding: 18px;
    border: 1px solid #dbe4ee;
    border-radius: 10px;
    background: #fff;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-right: 26px;
  }

  h3 {
    margin: 0;
    color: #243b53;
    font-size: 15px;
  }

  p {
    margin: 8px 0;
    color: #64748b;
    font-size: 12px;
    line-height: 1.7;
  }

  .plot {
    width: 100%;
    min-width: 0;
  }

  button {
    padding: 4px 8px;
    border: 1px solid #dbe4ee;
    border-radius: 5px;
    background: white;
    color: #365c85;
    white-space: nowrap;
    cursor: pointer;
  }

  .table-scroll {
    max-height: 540px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 9px;
    border-bottom: 1px solid #edf1f5;
    text-align: right;
    white-space: nowrap;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  .demo {
    color: #9c671a;
  }
</style>
