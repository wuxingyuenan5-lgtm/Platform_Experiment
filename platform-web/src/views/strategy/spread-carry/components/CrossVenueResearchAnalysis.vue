<template>
  <div class="spread-page">
    <section class="spread-overview">
      <article class="spread-card"
        ><header>实时三价差</header
        ><table
          ><thead
            ><tr><th>口径</th><th>当前观测</th><th>可用性</th></tr></thead
          ><tbody
            ><tr v-for="(name, key) in spreadNames" :key="key"
              ><td>{{ name }}</td
              ><td>{{ latest?.data?.[key] ?? '未知' }}</td
              ><td>{{ latest?.stale ? '时间或行情覆盖不足' : '可观察；不代表成交' }}</td></tr
            ></tbody
          ></table
        ></article
      >
      <article class="spread-card"
        ><header>机会分析</header
        ><div class="analysis-grid"
          ><div class="analysis-head"
            ><span>窗口</span><span>样本数</span><span>10%</span><span>50%</span
            ><span>90%</span></div
          ><div class="analysis-row"
            ><strong>所选窗口</strong><span>{{ distribution?.sampleCount ?? '未知' }}</span
            ><span>{{ distribution?.p10 ?? '未知' }}</span
            ><span>{{ distribution?.p50 ?? '未知' }}</span
            ><span>{{ distribution?.p90 ?? '未知' }}</span></div
          ></div
        ><p>等权 1 秒有效样本；开市、时钟或覆盖不足时不计算机会排名。</p></article
      >
    </section>
    <section class="spread-chart-card">
      <div class="spread-chart-toolbar"
        ><h3>跨所价差走势</h3
        ><div class="spread-series-inline"
          ><button
            class="series-switch"
            :class="{ 'is-active': showSpread }"
            @click="showSpread = !showSpread"
            >价差</button
          ><button
            class="series-switch"
            :class="{ 'is-active': showGoldPrice }"
            @click="showGoldPrice = !showGoldPrice"
            >黄金价格</button
          ></div
        ></div
      >
      <p v-if="!rows.length" role="status">{{
        history?.data?.emptyReason || '正在读取跨所观测；缺失报价不填零。'
      }}</p>
      <p v-if="showGoldPrice" role="status">黄金价格历史尚未随研究序列发布，未用最新价填充历史。</p>
      <div ref="mainChartRef" class="spread-chart"></div>
    </section>
    <section class="statistics-section">
      <div class="section-head"><h3>统计分析</h3><p>所选窗口 · 等权 1 秒收盘</p></div>
      <div class="statistics-grid">
        <article class="stats-card stats-card--summary"
          ><header class="stats-card__header"><span>统计分布</span></header
          ><div class="stats-kpi-grid"
            ><div v-for="item in stats" :key="item.label" class="stats-kpi"
              ><span>{{ item.label }}</span
              ><strong>{{ item.value }}</strong></div
            ></div
          ><div ref="distributionRef" class="mini-chart"></div
        ></article>
        <article class="stats-card"
          ><header>季节图表</header
          ><div class="seasonal-chart research-empty">{{ seasonalMessage }}</div></article
        >
        <article class="stats-card"
          ><header>月度热力矩阵</header
          ><div class="heatmap-table"
            ><div class="heatmap-row heatmap-head"
              ><span>年份</span><span v-for="month in 12" :key="month">{{ month }}月</span></div
            ><div class="heatmap-row"
              ><span class="heatmap-year">{{ year }}</span
              ><span v-for="month in 12" :key="month" class="heatmap-cell">—</span></div
            ></div
          ><p>完整月度覆盖尚未验证，未生成月度收益或季节规律。</p></article
        >
      </div>
    </section>
  </div>
</template>
<script setup lang="ts">
  import { computed, onMounted, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { ResearchResponse } from '@/api/platform/strategyResearch';

  const props = defineProps<{ history?: ResearchResponse; latest?: ResearchResponse }>();
  const rows = computed(() => props.history?.data?.rows || []);
  const distribution = computed(() => props.history?.data?.distribution);
  const spreadNames = { midSpread: '中间价差', buySpread: '买价差', sellSpread: '卖价差' };
  const showSpread = ref(true),
    showGoldPrice = ref(false);
  const year = new Date().getFullYear();
  const seasonalMessage = '已恢复季节图表位置；尚无完整年度覆盖，无法计算可信的季节曲线。';
  const stats = computed(() => [
    { label: '有效秒样本', value: distribution.value?.sampleCount ?? '未知' },
    { label: '有效毫秒', value: distribution.value?.validDurationMs ?? '未知' },
    { label: '中位价差', value: distribution.value?.p50 ?? '未知' },
    {
      label: 'P10 / P90',
      value: `${distribution.value?.p10 ?? '未知'} / ${distribution.value?.p90 ?? '未知'}`,
    },
  ]);
  const mainChartRef = ref<HTMLDivElement>(),
    distributionRef = ref<HTMLDivElement>();
  const chart = useECharts(mainChartRef as Ref<HTMLDivElement>),
    histogram = useECharts(distributionRef as Ref<HTMLDivElement>);
  function render() {
    void chart.setOptions({
      color: ['#d79a1e', '#cf3f4f', '#2db87c'],
      tooltip: { trigger: 'axis' },
      legend: {
        data: Object.values(spreadNames),
        selected: (chart.getInstance()?.getOption()?.legend as any)?.[0]?.selected || {
          中间价差: true,
          买价差: false,
          卖价差: false,
        },
      },
      xAxis: { type: 'time' },
      yAxis: { type: 'value', scale: true },
      dataZoom: [{ type: 'inside' }, { type: 'slider' }],
      series: showSpread.value
        ? (props.history?.data?.chartSeries || []).map((s) => ({
            name: String(s.name),
            type: 'line' as const,
            showSymbol: false,
            connectNulls: false,
            data: s.data as any,
          }))
        : [],
    });
    const bins = (distribution.value?.histogram || []) as Array<{ label: string; count: number }>;
    void histogram.setOptions({
      tooltip: { trigger: 'axis' },
      grid: { left: 44, right: 16, top: 20, bottom: 35 },
      xAxis: {
        type: 'category',
        data: bins.map((b) => b.label),
      },
      yAxis: { type: 'value', name: '秒样本' },
      series: [{ type: 'bar', data: bins.map((b) => b.count), itemStyle: { color: '#d79a1e' } }],
    });
  }
  watch(() => [props.history, showSpread.value], render, { deep: true });
  onMounted(render);
</script>
<style scoped lang="less">
  .research-empty {
    display: grid;
    place-items: center;
    padding: 30px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  .spread-page {
    display: flex;
    flex-direction: column;
    background: var(--strategy-bg);
    color: var(--strategy-text-1);
    gap: 14px;
  }

  .spread-workspace-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 2px 0;
  }

  .spread-workspace-head__main {
    display: flex;
    flex: 0 0 auto;
    flex-wrap: nowrap;
    align-items: center;
    width: auto;
    max-width: 100%;
    min-height: 46px;
    padding: 5px var(--strategy-space-2);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    gap: var(--strategy-space-2);
  }

  .workspace-control {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    min-width: 0;
    gap: var(--strategy-space-1);
  }

  .workspace-control span {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
    letter-spacing: 0;
    white-space: nowrap;
  }

  .workspace-control select {
    width: auto;
    min-width: 88px;
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  .spread-overview {
    display: grid;
    grid-template-columns: 1.1fr 1fr;
    gap: 12px;
  }

  .spread-card,
  .spread-chart-card,
  .stats-card {
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .spread-card,
  .stats-card {
    padding: var(--strategy-space-3);
  }

  .spread-card header,
  .stats-card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .spread-card header button {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    cursor: pointer;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 10px 0;
    border-bottom: 1px solid var(--strategy-border-soft);
    font-size: var(--strategy-font-sm);
    text-align: left;
  }

  th {
    color: var(--strategy-text-3);
    font-weight: 700;
  }

  td {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .analysis-grid {
    display: grid;
    gap: 14px;
  }

  .analysis-head,
  .analysis-row {
    display: grid;
    grid-template-columns: 1.2fr repeat(4, 1fr);
    gap: 12px;
    align-items: center;
    font-size: var(--strategy-font-sm);
  }

  .analysis-head {
    color: var(--strategy-text-faint);
    font-weight: 700;
  }

  .analysis-row {
    color: var(--strategy-text-2);
  }

  .analysis-row strong {
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .spread-chart-card {
    padding: var(--strategy-space-4) var(--strategy-space-4) var(--strategy-space-2);
  }

  .spread-chart-toolbar,
  .section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .spread-chart-filters,
  .stats-card__controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
  }

  .spread-chart-toolbar__left,
  .spread-chart-toolbar__center,
  .spread-chart-toolbar__right {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .spread-chart-toolbar__left {
    flex: 0 0 auto;
    flex-wrap: nowrap;
  }

  .spread-chart-toolbar__center {
    flex: 1;
    justify-content: center;
  }

  .spread-chart-toolbar__right {
    flex: 0 0 auto;
    justify-content: flex-end;
  }

  .spread-series-inline {
    display: inline-flex;
    align-items: center;
    gap: 10px;
  }

  .series-switch,
  .spread-chart-filters input,
  .spread-chart-filters select,
  .stats-card__controls input,
  .stats-card__controls select {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  .series-switch {
    cursor: pointer;
  }

  .series-switch.is-active {
    border-color: var(--strategy-accent-soft);
    background: var(--strategy-accent-soft);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
    color: var(--strategy-accent-strong);
  }

  .chart-select {
    display: grid;
    gap: 6px;
  }

  .spread-chart-toolbar__left .chart-select {
    gap: 0;
    flex: 0 0 auto;
  }

  .spread-chart-toolbar__left input,
  .spread-chart-toolbar__left select {
    height: var(--strategy-control-height);
    padding: 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    line-height: 1;
  }

  .spread-chart-toolbar__left input {
    min-width: 122px;
  }

  .chart-select span,
  .section-head p {
    color: var(--strategy-text-faint);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .stats-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 18px;
  }

  .stats-card__header > span {
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .stats-card__controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
  }

  .stats-card__controls .chart-select {
    gap: 0;
  }

  .stats-card__controls input,
  .stats-card__controls select {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border-radius: var(--strategy-radius-control);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  .spread-chart {
    height: 420px;
    margin-top: 8px;
  }

  .domestic-supplement {
    display: grid;
    gap: 12px;
  }

  .domestic-analysis-card,
  .domestic-realtime-card {
    padding: 0;
    overflow: hidden;
  }

  .domestic-analysis-card header,
  .domestic-realtime-card header {
    margin: 0;
    padding: 16px 18px;
  }

  .domestic-analysis-scroll {
    overflow-x: auto;
    border-top: 1px solid #f2f4f7;
  }

  .domestic-analysis-table {
    min-width: 1540px;
  }

  .domestic-analysis-table th,
  .domestic-analysis-table td,
  .domestic-realtime-table th,
  .domestic-realtime-table td {
    padding: 12px 16px;
    border-bottom: 1px solid var(--strategy-border-soft);
    font-size: var(--strategy-font-sm);
    text-align: center;
    white-space: nowrap;
  }

  .domestic-analysis-table th,
  .domestic-realtime-table th {
    background: var(--strategy-table-head-bg);
    color: var(--strategy-text-3);
    font-weight: 700;
  }

  .domestic-analysis-table td,
  .domestic-realtime-table td {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .domestic-realtime-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .domestic-realtime-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .domestic-realtime-toolbar button {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    cursor: pointer;
  }

  .domestic-realtime-table {
    width: 100%;
  }

  .statistics-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .section-head h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-sans);
    font-size: var(--strategy-font-section-title);
    font-weight: 800;
  }

  .statistics-grid {
    display: grid;
    grid-template-columns: 1.1fr 1fr;
    gap: 14px;
  }

  .stats-card--summary {
    grid-row: span 2;
  }

  .stats-kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .stats-kpi {
    padding: 14px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface-muted);
  }

  .stats-kpi span {
    display: block;
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .stats-kpi strong {
    display: block;
    margin-top: 8px;
    font-size: 24px;
    font-weight: 800;
  }

  .is-negative {
    color: #cb4e5d;
  }

  .is-positive {
    color: #22a06b;
  }

  .is-neutral {
    color: #314053;
  }

  .mini-chart {
    height: 220px;
    margin-top: 16px;
  }

  .seasonal-chart {
    height: 320px;
  }

  .heatmap-table {
    display: grid;
    gap: 8px;
    overflow-x: auto;
  }

  .heatmap-row {
    display: grid;
    grid-template-columns: 84px repeat(12, minmax(70px, 1fr));
    gap: 6px;
    min-width: 980px;
  }

  .heatmap-row span {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 38px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 700;
  }

  .heatmap-head span {
    background: var(--strategy-table-head-bg);
    color: var(--strategy-text-3);
  }

  .heatmap-year {
    background: var(--strategy-table-head-bg);
    color: var(--strategy-text-2);
  }

  .heatmap-cell.is-warm {
    background: rgb(217 83 79 / 12%);
    color: #cf4653;
  }

  .heatmap-cell.is-cold {
    background: rgb(46 204 113 / 12%);
    color: #239b63;
  }

  @media (max-width: 1320px) {
    .spread-overview,
    .statistics-grid,
    .domestic-supplement {
      grid-template-columns: 1fr;
    }

    .stats-card--summary {
      grid-row: auto;
    }
  }

  @media (max-width: 980px) {
    .spread-chart-toolbar,
    .section-head,
    .domestic-realtime-head {
      flex-direction: column;
    }

    .spread-chart-filters,
    .stats-card__controls,
    .domestic-realtime-toolbar {
      justify-content: flex-start;
    }

    .spread-chart-toolbar__left,
    .spread-chart-toolbar__center,
    .spread-chart-toolbar__right {
      justify-content: flex-start;
      width: 100%;
    }

    .spread-chart-toolbar__left {
      flex-wrap: wrap;
    }
  }

  @media (max-width: 900px) {
    .spread-overview,
    .statistics-grid,
    .stats-kpi-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
