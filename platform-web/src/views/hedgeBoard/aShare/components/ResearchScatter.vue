<template>
  <ChartExpand :title="title">
    <article class="scatter-card">
      <header
        ><h3>{{ title }}</h3
        ><p>{{ subtitle }}</p></header
      >
      <div class="scatter-tools">
        <label v-if="showNames"><input v-model="labels" type="checkbox" /> 行业名称</label>
        <button type="button" @click="resetZoom">重置缩放</button>
        <button type="button" :aria-pressed="table" @click="table = !table">{{
          table ? '图表' : '查看数据'
        }}</button>
      </div>
      <p v-if="!points.length" class="empty">所选区间没有同日有效数据。</p>
      <div
        v-show="!table && points.length"
        ref="element"
        class="scatter-plot"
        role="img"
        :aria-label="title + '，悬浮查看名称和数值，点击选中，可缩放'"
        @pointerdown="bindClick"
      ></div>
      <div
        v-if="table && points.length"
        class="scatter-data"
        tabindex="0"
        :aria-label="title + '数据表'"
      >
        <table
          ><thead
            ><tr
              ><th>{{ showNames ? '行业' : '日期' }}</th
              ><th>{{ xLabel }}</th
              ><th>{{ yLabel }}</th></tr
            ></thead
          >
          <tbody
            ><tr v-for="p in tablePoints" :key="p.id"
              ><th
                ><button v-if="showNames" type="button" @click="emit('select', p.id)">{{
                  p.name
                }}</button
                ><span v-else>{{ p.name }}</span></th
              ><td>{{ fmt(p.x) }}</td
              ><td>{{ fmt(p.y) }}</td></tr
            ></tbody
          ></table
        >
      </div>
      <div v-if="table && points.length" class="scatter-tools">
        <span>{{ points.length }}条 · 每页25条</span>
        <button :disabled="page === 1" @click="page--">上一页</button>
        <span>{{ page }} / {{ pages }}</span>
        <button :disabled="page === pages" @click="page++">下一页</button>
      </div>
      <p class="scatter-note"><slot></slot></p>
    </article>
  </ChartExpand>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { LabelLayout } from 'echarts/features';
  import { MarkLineComponent } from 'echarts/components';
  import echarts from '@/utils/lib/echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import ChartExpand from '../../components/ChartExpand.vue';
  import { formatResearch as fmt } from './researchFrameworkAnalysis';

  echarts.use([LabelLayout, MarkLineComponent]);
  export interface ScatterPoint {
    id: string;
    name: string;
    x: number;
    y: number;
    highlightLabel?: boolean;
  }
  const props = defineProps<{
    title: string;
    subtitle?: string;
    points: ScatterPoint[];
    xLabel: string;
    yLabel: string;
    selected?: string;
    showNames?: boolean;
    compactLabels?: boolean;
    xBounds?: [number, number];
    xMiddle?: number;
    xGuides?: number[];
    fit?: number[][] | null;
  }>();
  const emit = defineEmits<{ select: [id: string] }>();
  const labels = ref(!props.compactLabels),
    table = ref(false),
    element = ref<HTMLDivElement | null>(null);
  const page = ref(1);
  const pages = computed(() => Math.max(1, Math.ceil(props.points.length / 25)));
  const tablePoints = computed(() =>
    (props.showNames ? props.points : props.points.slice().reverse()).slice(
      (page.value - 1) * 25,
      page.value * 25,
    ),
  );
  watch(
    () => props.points,
    () => {
      page.value = 1;
    },
  );
  const chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  const escape = (v: unknown) =>
    String(v).replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!),
    );
  let bound: ReturnType<typeof chart.getInstance>;
  function bindClick() {
    const instance = chart.getInstance();
    if (!instance || instance === bound) return;
    instance.on('click', (event: unknown) => {
      const e = event as { data?: { id?: string } };
      if (e.data?.id) emit('select', e.data.id);
    });
    bound = instance;
  }
  function resetZoom() {
    chart.getInstance()?.dispatchAction({ type: 'dataZoom', start: 0, end: 100 });
  }
  watch(
    [() => props.points, () => props.selected, labels, table, element],
    async () => {
      await nextTick();
      if (!element.value || table.value) return;
      const option: EChartsOption = {
        animation: false,
        grid: { left: 68, right: 40, top: 35, bottom: 75 },
        tooltip: {
          trigger: 'item',
          confine: true,
          formatter: (event: unknown) => {
            const p = (event as { data?: { name?: string; value?: number[] } }).data;
            if (!p?.value || !p.name) return '';
            return `${escape(p.name)}<br/>${escape(props.xLabel)}：${fmt(p.value[0])}<br/>${escape(
              props.yLabel,
            )}：${fmt(p.value[1])}`;
          },
        },
        xAxis: {
          type: 'value',
          name: props.xLabel,
          nameLocation: 'middle',
          nameGap: 42,
          min: props.xBounds?.[0],
          max: props.xBounds?.[1],
          scale: true,
          axisLabel: { color: '#64748b' },
          splitLine: { lineStyle: { color: '#edf1f5' } },
        },
        yAxis: {
          type: 'value',
          name: props.yLabel,
          nameLocation: 'end',
          nameTextStyle: { align: 'left' },
          scale: true,
          axisLabel: { color: '#64748b' },
          splitLine: { lineStyle: { color: '#edf1f5' } },
        },
        dataZoom: [
          {
            type: 'inside',
            xAxisIndex: 0,
            filterMode: 'none',
            zoomOnMouseWheel: 'ctrl',
            moveOnMouseWheel: false,
          },
          { type: 'slider', xAxisIndex: 0, height: 16, bottom: 3, filterMode: 'none' },
        ],
        series: [
          {
            type: 'scatter',
            name: props.title,
            data: props.points.map((p) => ({
              id: p.id,
              name: p.name,
              value: [p.x, p.y],
              symbolSize: props.selected === p.id ? 12 : 8,
              itemStyle: {
                color: props.selected === p.id ? '#1e3a5f' : p.y >= 0 ? '#2563eb' : '#089184',
                opacity: props.selected === p.id ? 1 : 0.8,
              },
              label: {
                show:
                  props.showNames && (labels.value || props.selected === p.id || p.highlightLabel),
                formatter: p.name,
                color: props.selected === p.id ? '#102a43' : '#475569',
                fontSize: 12,
                fontWeight: props.selected === p.id ? 'bold' : 'normal',
              },
            })),
            label: { position: 'top', distance: 7 },
            labelLayout: { hideOverlap: true },
            emphasis: { label: { show: !!props.showNames }, scale: 1.3 },
            markLine: {
              silent: true,
              symbol: 'none',
              label: { show: false },
              lineStyle: { color: '#9aaabd', type: 'dashed' },
              data: [
                { yAxis: 0 },
                ...(props.xGuides || [props.xMiddle ?? 0]).map((xAxis) => ({ xAxis })),
              ],
            },
          },
          ...(props.fit?.length
            ? [
                {
                  type: 'line' as const,
                  name: '线性拟合',
                  data: props.fit,
                  showSymbol: false,
                  silent: true,
                  lineStyle: { color: '#8a98ac', type: 'dashed' as const, width: 1.5 },
                  tooltip: { show: false },
                },
              ]
            : []),
        ],
      };
      chart.setOptions(option, true);
      bindClick();
    },
    { immediate: true },
  );
</script>
<style scoped>
  .scatter-card {
    min-width: 0;
    padding: 18px;
    border: 1px solid #dce5ee;
    border-radius: 9px;
    background: #fff;
  }

  header {
    padding-right: 32px;
  }

  h3 {
    margin: 0 0 7px;
    color: #18324d;
    font-size: 15px;
  }

  header p,
  .scatter-note {
    margin: 0;
    color: #64748b;
    font-size: 12px;
    line-height: 1.7;
  }

  .scatter-tools {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 12px 0 0;
    font-size: 12px;
    gap: 10px;
  }

  .scatter-tools label {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  button {
    padding: 5px 9px;
    border: 1px solid #dce5ee;
    border-radius: 5px;
    background: #fff;
    color: #334155;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  button:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }

  .scatter-plot {
    width: 100%;
    height: 440px;
  }

  .scatter-note {
    margin-top: 10px;
  }

  .scatter-data {
    height: 440px;
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
    border-bottom: 1px solid #e5edf3;
    text-align: right;
    white-space: nowrap;
  }

  th:first-child {
    text-align: left;
  }

  thead {
    position: sticky;
    top: 0;
    background: #f5f8fb;
  }

  .empty {
    padding: 60px 0;
    color: #64748b;
    text-align: center;
  }

  @media (max-width: 650px) {
    .scatter-card {
      padding: 12px;
    }

    .scatter-plot,
    .scatter-data {
      height: 370px;
    }
  }
</style>
