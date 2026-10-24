<template>
  <div class="linked-chart-shell">
    <div
      ref="chartRef"
      class="linked-chart"
      role="img"
      tabindex="0"
      aria-label="ETF联动历史图：价格、成交额、份额、申赎、指数及融资。Ctrl加滚轮缩放，拖动平移。"
      @pointerenter="bindEvents"
      @wheel.capture="allowPageScroll"
      @focus="bindEvents"
      @keydown.left.prevent="moveCursor(-1)"
      @keydown.right.prevent="moveCursor(1)"
    ></div>
    <p class="chart-help"
      >各图共享日期轴与十字线 · Ctrl + 滚轮缩放 · 拖动平移 · 左右方向键查看数据</p
    >
  </div>
</template>

<script setup lang="ts">
  import { ref, watch, nextTick, onMounted, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { EtfDetail } from '@/api/etfTracking';
  import { numeric } from './etfTrackingModel';

  const props = defineProps<{ detail: EtfDetail; start: string; end: string; tooltip: boolean }>();
  const emit = defineEmits<{ (event: 'range', start: string, end: string): void }>();
  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>, 'light');
  const blue = '#2864ec',
    red = '#ed6b70',
    green = '#36a795',
    ink = '#27364c';
  let cursor = 0;
  let bound: ReturnType<typeof chart.getInstance> = null;
  const plots = [
    ['日线价格走势', 'etf_qfq_close', '元', false],
    ['日度 ETF 成交额（估算）', 'etf_qfq_turnover_est_yi', '亿元', true],
    ['日线 ETF 份额走势 · 圆点为持仓披露', 'qfq_total_units_yi', '亿份', false],
    ['日度 ETF 申购赎回份额', 'qfq_delta_units_yi', '亿份', true],
    ['净申赎金额 / 指数成交额', 'flow_to_index_pct', '%', true],
    ['对应指数与本组 ETF 总份额', 'index_close', '点', false],
    ['ETF 融资余额与融资净买入', 'financing_balance_yi', '亿元', false],
    ['指数成分股融资余额与融资净买入', 'index_financing_balance_yi', '亿元', false],
  ] as const;
  const numberFormat = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 4 });
  const showNumber = (value: unknown) => {
    const n = numeric(value as number | null);
    return n == null ? '—' : numberFormat.format(n);
  };
  async function render() {
    const rows = props.detail.series;
    const dates = rows.map((r) => r.date);
    const group = new Map(props.detail.group.map((r) => [r.date, r]));
    const margin = new Map(props.detail.margin.map((r) => [r.date, r]));
    const groupMargin = new Map(props.detail.groupMargin.map((r) => [r.date, r]));
    const values = plots.map((plot, i) =>
      rows.map((r) =>
        numeric(
          i === 6
            ? margin.get(r.date)?.[plot[1]]
            : i === 7
            ? groupMargin.get(r.date)?.[plot[1]]
            : r[plot[1]],
        ),
      ),
    );
    const xAxis = plots.map((_, i) => ({
      type: 'category',
      gridIndex: i,
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#d8e0ed' } },
      axisTick: { show: false },
      axisLabel: {
        show: true,
        color: '#71809a',
        fontSize: 10,
        hideOverlap: true,
        formatter: (v: string) => v.slice(2),
      },
      axisPointer: { show: true, label: { show: i === plots.length - 1, backgroundColor: blue } },
    }));
    const yAxis: any[] = plots.map((plot, i) => ({
      type: 'value',
      gridIndex: i,
      scale: !plot[3],
      splitNumber: 3,
      name: plot[2],
      nameTextStyle: { color: '#8290a5', fontSize: 10 },
      axisLabel: { color: '#71809a', fontSize: 10, formatter: (v: number) => showNumber(v) },
      splitLine: { lineStyle: { color: '#e2e7f0' } },
      axisPointer: { show: false },
    }));
    const series: any[] = plots.map((plot, i) => ({
      id: plot[1],
      name: plot[0],
      type: plot[3] ? 'bar' : 'line',
      xAxisIndex: i,
      yAxisIndex: i,
      showSymbol: false,
      connectNulls: false,
      lineStyle: { color: blue, width: 1.6 },
      itemStyle: { color: plot[3] ? (p: any) => (p.value < 0 ? green : red) : blue },
      barMaxWidth: 12,
      data: values[i],
      emphasis: { disabled: true },
    }));
    for (const [gridIndex, field, name, unit, map, bar] of [
      [5, 'qfq_total_units_yi', '本组 ETF 总份额', '亿份', group, false],
      [6, 'financing_net_buy_yi', 'ETF 融资净买入', '亿元', margin, true],
      [7, 'index_financing_net_buy_yi', '成分股融资净买入', '亿元', groupMargin, true],
    ] as const) {
      const axisIndex = yAxis.length;
      yAxis.push({
        type: 'value',
        gridIndex,
        position: 'right',
        scale: !bar,
        splitNumber: 3,
        name: unit,
        nameTextStyle: { color: '#9b8b72', fontSize: 10 },
        axisLabel: { color: '#9b8b72', fontSize: 10 },
        splitLine: { show: false },
        axisPointer: { show: false },
      });
      series.push({
        id: name,
        name,
        type: bar ? 'bar' : 'line',
        xAxisIndex: gridIndex,
        yAxisIndex: axisIndex,
        showSymbol: false,
        connectNulls: false,
        lineStyle: { color: '#bb965b', width: 1.5 },
        itemStyle: { color: bar ? (p: any) => (p.value < 0 ? green : red) : '#bb965b' },
        data: rows.map((r) => numeric(map.get(r.date)?.[field])),
        barMaxWidth: 10,
      });
    }
    const disclosures = props.detail.disclosures.flatMap((d) => {
      const day = dates.filter((day) => day <= d.report_date).at(-1);
      const value = numeric(d.total_shares_yi_qfq);
      return day && value != null
        ? [{ value: [day, value], ratio: d.combined_ratio_pct, report: d.report_date }]
        : [];
    });
    series.push({
      id: 'disclosures',
      name: '持仓披露',
      type: 'scatter',
      xAxisIndex: 2,
      yAxisIndex: 2,
      symbolSize: 8,
      itemStyle: { color: '#fff', borderColor: blue, borderWidth: 2 },
      label: {
        show: true,
        position: 'top',
        color: '#667b9c',
        fontSize: 10,
        formatter: (p: any) => `${showNumber(p.data.ratio)}%`,
      },
      data: disclosures,
      tooltip: {
        trigger: 'item',
        formatter: (p: any) =>
          `报告期 ${p.data.report}\n披露占比 ${showNumber(p.data.ratio)}%\n份额 ${showNumber(
            p.value[1],
          )} 亿份`,
      },
    });
    const start = Math.max(
      0,
      dates.findIndex((d) => !props.start || d >= props.start),
    );
    const last =
      dates.length - 1 - [...dates].reverse().findIndex((d) => !props.end || d <= props.end);
    const end = Math.max(start, last < 0 ? dates.length - 1 : last);
    const option = {
      textStyle: {
        fontFamily: chartRef.value
          ? getComputedStyle(chartRef.value).fontFamily
          : 'Aptos, Microsoft YaHei UI, sans-serif',
      },
      animation: false,
      backgroundColor: '#fff',
      title: plots.map((plot, i) => ({
        text: plot[0],
        left: 18,
        top: i * 186 + 12,
        textStyle: { fontSize: 12, fontWeight: 600, color: ink },
        subtext: values[i].some((v) => v != null) ? '' : '暂无数据',
        subtextStyle: { fontSize: 11, color: '#8b97a9' },
      })),
      grid: plots.map((_, i) => ({ top: i * 186 + 47, height: 126, left: 64, right: 64 })),
      xAxis,
      yAxis,
      axisPointer: {
        link: [{ xAxisIndex: 'all' }],
        lineStyle: { color: '#8a9bb4', type: 'dashed' },
      },
      tooltip: {
        show: props.tooltip,
        trigger: 'axis',
        renderMode: 'richText',
        confine: true,
        backgroundColor: 'rgba(255,255,255,.97)',
        borderColor: '#d9e2f1',
        textStyle: { color: ink, fontSize: 11 },
        formatter: (params: any[]) => {
          const day = params[0]?.axisValue;
          const index = dates.indexOf(day);
          return [
            day,
            ...plots.map(
              (plot, i) => `${plot[0].split(' · ')[0]}  ${showNumber(values[i][index])} ${plot[2]}`,
            ),
            `估算净申赎金额  ${showNumber(rows[index]?.flow_yi)} 亿元`,
          ].join('\n');
        },
      },
      dataZoom: [
        {
          id: 'linked-window',
          type: 'inside',
          xAxisIndex: plots.map((_, i) => i),
          filterMode: 'filter',
          startValue: start,
          endValue: end,
          zoomOnMouseWheel: 'ctrl',
          moveOnMouseWheel: false,
          moveOnMouseMove: true,
        },
      ],
      series,
    } as EChartsOption;
    chart.getInstance()?.dispatchAction({ type: 'hideTip' });
    await chart.setOptions(option, false);
    await nextTick();
    bindEvents();
  }
  function allowPageScroll(event: WheelEvent) {
    // ECharts' shared roam controller captures wheel events even with ctrl-only zoom.
    // Let ordinary wheel events use the browser's native scrolling behavior.
    if (!event.ctrlKey) event.stopPropagation();
  }
  function bindEvents() {
    const instance = chart.getInstance();
    if (instance && bound !== instance) {
      bound = instance;
      instance.on('datazoom', (event: any) => {
        const payload = event.batch?.[0] || event;
        const currentDates = props.detail.series.map((r) => r.date);
        if (payload.start == null || payload.end == null || !currentDates.length) return;
        const a = Math.round((payload.start / 100) * (currentDates.length - 1));
        const b = Math.round((payload.end / 100) * (currentDates.length - 1));
        emit('range', currentDates[a], currentDates[b]);
      });
    }
  }
  function moveCursor(direction: number) {
    const rows = props.detail.series;
    const first = Math.max(
      0,
      rows.findIndex((row) => row.date >= props.start),
    );
    const last = rows.findIndex((row) => row.date === props.end);
    cursor = Math.max(first, Math.min(last < 0 ? rows.length - 1 : last, cursor + direction));
    chart.getInstance()?.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: cursor });
  }
  watch(() => [props.detail, props.tooltip], render, { deep: false });
  watch(
    () => [props.start, props.end],
    () => {
      const instance = chart.getInstance();
      if (!instance) {
        void render();
        return;
      }
      // Moving the window must not rebuild all eleven historical data series.
      instance.dispatchAction(
        {
          type: 'dataZoom',
          dataZoomId: 'linked-window',
          startValue: props.start,
          endValue: props.end,
        },
        { silent: true },
      );
    },
  );
  onMounted(render);
</script>

<style scoped>
  .linked-chart-shell {
    overflow: hidden;
    border: 1px solid #d8e0ed;
    border-radius: 9px;
    background: #fff;
  }

  .linked-chart {
    width: 100%;
    height: 1510px;
  }

  .linked-chart:focus-visible {
    outline: 2px solid #2864ec;
    outline-offset: -2px;
  }

  .chart-help {
    margin: 0;
    padding: 8px 16px 12px;
    color: #8290a5;
    font-size: 11px;
  }
</style>
