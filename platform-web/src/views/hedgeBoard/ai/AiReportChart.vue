<template>
  <ChartExpand v-slot="{ expanded }" :title="chart.title">
    <article class="report-chart" :class="{ expanded }" :data-chart-id="chart.id">
      <header
        ><span class="status" :class="chart.status">{{
          chart.status === 'demo' ? 'Demo · 模拟数据' : '报告快照'
        }}</span
        ><h4>{{ chart.title }}</h4></header
      >
      <p class="date">{{ chart.asOf }} · PDF p.{{ chart.page }}</p>
      <div
        ref="element"
        class="plot"
        role="img"
        :aria-label="chart.title + '；' + (chart.status === 'demo' ? '模拟数据' : '报告快照')"
      ></div>
      <p class="basis">{{ chart.basis }}</p>
      <footer
        ><span
          >来源：兴证策略《AI投资篇》{{
            chart.status === 'demo' ? '研究框架；数值为模拟构造' : '图表转录，未独立核验原始数据'
          }}</span
        ><button @click="download">导出CSV</button></footer
      >
      <details
        ><summary>查看数据与单位</summary
        ><div class="table-wrap"
          ><table
            ><thead
              ><tr
                ><th v-for="h in headers" :key="h">{{ h }}</th></tr
              ></thead
            ><tbody
              ><tr v-for="(row, i) in rows" :key="i"
                ><td v-for="(value, j) in row" :key="j">{{ value ?? '—' }}</td></tr
              ></tbody
            ></table
          ></div
        ></details
      >
    </article>
  </ChartExpand>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import ChartExpand from '../components/ChartExpand.vue';
  import { chartCsv, chartHeaders, chartRows, type ReportChart } from './investmentReport';

  const props = defineProps<{ chart: ReportChart }>();
  const element = ref<HTMLDivElement>();
  const instance = useECharts(element as Ref<HTMLDivElement>, 'light');
  const headers = computed(() => chartHeaders(props.chart));
  const rows = computed(() => chartRows(props.chart));
  const colors = ['#b33d49', '#39799e', '#5c8f7b', '#a47a35', '#746b9f'];
  watch(
    () => props.chart,
    async (chart) => {
      await nextTick();
      const groups = [...new Set(chart.scatter?.map((p) => p.group) || [])];
      const scatterSeries = groups.map((group) => ({
        name: group,
        type: 'scatter',
        symbolSize: 10,
        data: chart
          .scatter!.filter((p) => p.group === group)
          .map((p) => ({ name: p.name, value: [p.x, p.y] })),
        label: {
          show: !!chart.peg,
          formatter: '{b}',
          position: 'top',
          fontSize: 10,
          color: '#415365',
        },
        labelLayout: { hideOverlap: true },
      }));
      const maxX = Math.max(...(chart.scatter?.map((p) => p.x) || [0]));
      const option = {
        animation: false,
        color: colors,
        legend: {
          type: 'scroll',
          top: 5,
          left: 8,
          right: 8,
          textStyle: { fontSize: 11, color: '#56667a' },
        },
        grid: {
          left: 65,
          right: chart.rightUnit ? 65 : 24,
          top: 80,
          bottom: chart.scatter ? 60 : 92,
        },
        tooltip: chart.scatter
          ? {
              trigger: 'item',
              confine: true,
              formatter: (p: { name: string; value: number[] }) =>
                `${p.name}<br/>${chart.xUnit}：${p.value[0]}<br/>${chart.unit}：${p.value[1]}`,
            }
          : {
              trigger: 'axis',
              confine: true,
              valueFormatter: (v: unknown) =>
                v == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 }),
            },
        xAxis: chart.scatter
          ? {
              type: 'value',
              name: chart.xUnit,
              nameLocation: 'middle',
              nameGap: 30,
              min: 0,
              splitLine: { show: false },
            }
          : {
              type: 'category',
              data: chart.labels,
              boundaryGap: chart.series.some((s) => s.bar),
              axisLabel: {
                hideOverlap: true,
                fontSize: 10,
                rotate: chart.labels.length <= 15 ? 25 : 0,
              },
            },
        yAxis: [
          {
            type: 'value',
            name: chart.unit,
            nameTextStyle: { fontSize: 10 },
            splitLine: { lineStyle: { color: '#e8edf2' } },
          },
          {
            type: 'value',
            show: !!chart.rightUnit,
            name: chart.rightUnit,
            nameTextStyle: { fontSize: 10 },
            splitLine: { show: false },
          },
        ],
        dataZoom:
          !chart.scatter && chart.labels.length > 15
            ? [
                { type: 'inside', zoomOnMouseWheel: 'ctrl', moveOnMouseWheel: false },
                { type: 'slider', height: 18, bottom: 10 },
              ]
            : [],
        series: chart.scatter
          ? [
              ...scatterSeries,
              ...(chart.peg
                ? [
                    {
                      type: 'line',
                      name: 'PEG=1参照',
                      data: [
                        [0, 0],
                        [maxX, maxX],
                      ],
                      symbol: 'none',
                      silent: true,
                      lineStyle: { type: 'dashed', width: 1, color: '#8995a5' },
                    },
                  ]
                : []),
            ]
          : chart.series.map((s) => ({
              name: s.name,
              type: s.bar ? 'bar' : 'line',
              data: s.values,
              yAxisIndex: s.right ? 1 : 0,
              showSymbol: chart.labels.length <= 15,
              symbolSize: 5,
              connectNulls: false,
              barMaxWidth: 32,
              lineStyle: { width: 2 },
              ...(chart.status === 'snapshot'
                ? { label: { show: true, position: 'top', formatter: '{c}%' } }
                : {}),
            })),
      };
      instance.setOptions(option as EChartsOption, true);
    },
    { immediate: true },
  );
  function download() {
    const blob = new Blob(['\uFEFF' + chartCsv(props.chart)], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob),
      a = document.createElement('a');
    a.href = url;
    a.download = `AI投资-${props.chart.id}-${props.chart.status}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
</script>
<style scoped>
  .report-chart {
    min-width: 0;
    padding: 18px;
    border: 1px solid #dce4eb;
    border-radius: 10px;
    background: #fff;
  }

  header {
    padding-right: 38px;
  }

  h4 {
    margin: 8px 0 0;
    color: #243b50;
    font-size: 15px;
    line-height: 1.55;
  }

  .status {
    padding: 3px 7px;
    border-radius: 4px;
    font-size: 11px;
  }

  .demo {
    background: #fff3e1;
    color: #986329;
  }

  .snapshot {
    background: #eaf4ee;
    color: #347260;
  }

  .date,
  .basis,
  footer {
    color: #738296;
    font-size: 11px;
    line-height: 1.7;
  }

  .date {
    margin: 7px 0 0;
  }

  .basis {
    min-height: 38px;
    margin: 0 0 8px;
  }

  .plot {
    width: 100%;
    height: 355px;
  }

  .expanded .plot {
    height: clamp(330px, calc(100dvh - 300px), 800px);
  }

  footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 10px;
    border-top: 1px solid #edf0f4;
    gap: 12px;
  }

  button {
    flex-shrink: 0;
    padding: 3px 9px;
    border: 1px solid #d8e1e9;
    border-radius: 5px;
    background: white;
    color: #496476;
    cursor: pointer;
  }

  details {
    margin-top: 10px;
    color: #536a80;
    font-size: 12px;
  }

  summary {
    width: fit-content;
    cursor: pointer;
  }

  .table-wrap {
    max-height: 260px;
    margin-top: 10px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 7px;
    border-bottom: 1px solid #edf0f4;
    text-align: right;
    white-space: nowrap;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  th {
    position: sticky;
    top: 0;
    background: #f5f8fa;
  }

  button:focus-visible,
  summary:focus-visible {
    outline: 2px solid #39799e;
    outline-offset: 3px;
  }

  @media (max-width: 600px) {
    .report-chart {
      padding: 12px;
    }

    .plot {
      height: 330px;
    }

    footer {
      align-items: flex-start;
    }

    .basis {
      min-height: 0;
    }
  }
</style>
