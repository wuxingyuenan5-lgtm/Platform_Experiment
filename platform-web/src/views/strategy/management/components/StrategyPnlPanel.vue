<template>
  <section class="pnl-panel">
    <article class="pnl-overview-card">
      <header class="pnl-overview-header">
        <div>
          <h3>损益总览</h3>
          <div class="pnl-meta">
            <em>总资金：{{ profile.totalFund }}</em>
          </div>
        </div>

        <div class="pnl-actions">
          <div class="period-tabs">
            <button
              v-for="item in periodTabs"
              :key="item"
              type="button"
              :class="{ 'is-active': activePeriod === item }"
              @click="activePeriod = item"
            >
              {{ item }}
            </button>
          </div>
          <button type="button" class="legend-pill is-return">
            <span></span>
            日度收益
          </button>
          <button type="button" class="legend-pill is-net">
            <span></span>
            净值曲线
          </button>
        </div>
      </header>

      <div ref="overviewChartRef" class="overview-chart"></div>
    </article>

    <section class="metric-grid">
      <article v-for="item in profile.metrics" :key="item.label" class="metric-card">
        <label>{{ item.label }}</label>
        <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
        <span :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.ratio }}</span>
      </article>
    </section>

    <section class="attribution-board">
      <article v-for="item in profile.attributions" :key="item.label" class="attribution-card">
        <label>{{ item.label }}</label>
        <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
        <span :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.ratio }}</span>
      </article>
    </section>

    <section v-if="profile.legSnapshots?.length" class="leg-snapshot-grid">
      <article v-for="leg in profile.legSnapshots" :key="leg.title" class="leg-snapshot-card">
        <header>
          <div>
            <h3>{{ leg.title }}</h3>
            <span>{{ leg.venue }}</span>
          </div>
          <strong>{{ leg.symbol }}</strong>
        </header>

        <dl>
          <div v-for="row in leg.rows" :key="row.label">
            <dt>{{ row.label }}</dt>
            <dd :class="row.tone ? `is-${row.tone}` : 'is-neutral'">{{ row.value }}</dd>
          </div>
        </dl>
      </article>
    </section>

    <article class="breakdown-curve-card">
      <header class="breakdown-curve-header">
        <h3>损益细分总图</h3>
      </header>
      <div ref="breakdownChartRef" class="breakdown-chart"></div>
    </article>

    <section class="detail-curve-grid">
      <StrategyCurveCardChart v-for="item in detailCurveCards" :key="item.title" :item="item" />
    </section>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { StrategyDeskKey, StrategyPnlProfile } from '@/data/sample/strategy';
  import StrategyCurveCardChart from './StrategyCurveCardChart.vue';
  import { strategyPnlProfiles } from '@/data/sample/strategy';

  const props = defineProps<{
    activeDesk: StrategyDeskKey;
    liveProfile?: StrategyPnlProfile | null;
  }>();

  const periodTabs = ['日报', '周报', '月报', '自定义'];
  const activePeriod = ref('周报');
  const overviewChartRef = ref<HTMLDivElement | null>(null);
  const breakdownChartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(overviewChartRef as Ref<HTMLDivElement>);
  const { setOptions: setBreakdownOptions, resize: resizeBreakdown } = useECharts(
    breakdownChartRef as Ref<HTMLDivElement>,
  );

  const emptyCrossSpreadProfile: StrategyPnlProfile = {
    ...strategyPnlProfiles.crossSpread,
    totalFund: '--',
    period: '--',
    xLabels: [],
    dailyReturns: [],
    netValues: [],
    metrics: strategyPnlProfiles.crossSpread.metrics.map((item) => ({
      ...item,
      value: '--',
      ratio: '接口待接入',
      tone: 'neutral',
    })),
    attributions: strategyPnlProfiles.crossSpread.attributions.map((item) => ({
      ...item,
      value: '--',
      ratio: '接口待接入',
      tone: 'neutral',
    })),
    breakdownSeries: strategyPnlProfiles.crossSpread.breakdownSeries.map((item) => ({
      ...item,
      data: [],
    })),
    legSnapshots: [
      {
        title: 'Bybit 腿',
        venue: '--',
        symbol: 'XAUTUSDT',
        rows: [
          { label: '持仓数量', value: '--' },
          { label: '均价', value: '--' },
          { label: '最新价', value: '--' },
          { label: '未实现盈亏', value: '--' },
          { label: '已实现盈亏', value: '--' },
          { label: '最后同步', value: '--' },
        ],
      },
      {
        title: 'MT5 腿',
        venue: '--',
        symbol: 'XAUUSD.s',
        rows: [
          { label: '持仓数量', value: '--' },
          { label: '均价', value: '--' },
          { label: '最新价', value: '--' },
          { label: '未实现盈亏', value: '--' },
          { label: '已实现盈亏', value: '--' },
          { label: '最后同步', value: '--' },
        ],
      },
    ],
    detailCurves: strategyPnlProfiles.crossSpread.detailCurves.map((item) => ({
      ...item,
      value: '--',
      tone: 'neutral',
      data: [],
    })),
  };

  const profile = computed(() => {
    const base = strategyPnlProfiles[props.activeDesk];
    if (props.liveProfile) return props.liveProfile;
    if (props.activeDesk !== 'crossSpread') return base;
    if (!props.liveProfile) return emptyCrossSpreadProfile;
    return emptyCrossSpreadProfile;
  });
  const detailCurveCards = computed(() =>
    profile.value.detailCurves.map((item) => ({
      title: item.title,
      amount: item.value,
      unit: '',
      tone: item.tone,
      points: profile.value.xLabels.map((date, index) => ({
        date,
        value: item.data[index] ?? item.data[item.data.length - 1] ?? 0,
      })),
    })),
  );

  async function renderOverviewChart() {
    await setOptions({
      color: ['#57bf45', '#5aa7ef'],
      tooltip: { trigger: 'axis' },
      grid: { left: 44, right: 40, top: 42, bottom: 74, containLabel: true },
      xAxis: {
        type: 'category',
        data: profile.value.xLabels,
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#7f8da3' } },
        axisLabel: { color: '#8392aa' },
      },
      yAxis: [
        {
          type: 'value',
          name: '日度收益',
          splitLine: { lineStyle: { color: 'rgba(132, 148, 168, 0.18)', type: 'dashed' } },
          axisLabel: { color: '#8392aa' },
        },
        {
          type: 'value',
          name: '净值',
          position: 'right',
          scale: true,
          splitLine: { show: false },
          axisLabel: { color: '#8392aa' },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 20,
          bottom: 14,
          borderColor: 'rgba(190, 204, 224, 0.75)',
          fillerColor: 'rgba(98, 150, 230, 0.2)',
          backgroundColor: 'rgba(232, 239, 250, 0.82)',
          brushSelect: false,
        },
      ],
      series: [
        {
          name: '日度收益',
          type: 'bar',
          barWidth: 14,
          itemStyle: {
            borderRadius: [4, 4, 0, 0],
            color: (params: any) =>
              Number(params?.value ?? params?.data ?? 0) >= 0 ? '#5cc548' : '#ee6f70',
          },
          data: profile.value.dailyReturns,
        },
        {
          name: '净值曲线',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2.8, color: '#5aa7ef' },
          areaStyle: { color: 'rgba(90, 167, 239, 0.08)' },
          data: profile.value.netValues,
        },
      ] as any,
    });
    await nextTick();
    resize();
  }

  async function renderBreakdownChart() {
    const palette = [
      '#3498db',
      '#55d6d9',
      '#f4bf45',
      '#ee746f',
      '#d05caa',
      '#7aa7ff',
      '#2fa86e',
      '#d8585f',
      '#8b6bd8',
    ];
    const series = profile.value.breakdownSeries.map((item, index) => ({
      name: item.name,
      color: palette[index % palette.length],
      data: item.data,
    }));
    await setBreakdownOptions({
      color: series.map((item) => item.color),
      tooltip: { trigger: 'axis' },
      legend: {
        right: 20,
        top: 12,
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: '#42526b', fontWeight: 700 },
      },
      grid: { left: 48, right: 36, top: 56, bottom: 76, containLabel: true },
      xAxis: {
        type: 'category',
        data: profile.value.xLabels,
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#d8e1ef' } },
        axisLabel: { color: '#8392aa' },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: 'rgba(132, 148, 168, 0.18)', type: 'dashed' } },
        axisLabel: { color: '#8392aa' },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 20,
          bottom: 16,
          borderColor: 'rgba(190, 204, 224, 0.75)',
          fillerColor: 'rgba(98, 150, 230, 0.2)',
          backgroundColor: 'rgba(232, 239, 250, 0.82)',
          brushSelect: false,
        },
      ],
      series: series.map((item) => ({
        name: item.name,
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2.4 },
        data: item.data,
      })),
    });
    await nextTick();
    resizeBreakdown();
  }

  function renderCharts() {
    renderOverviewChart();
    renderBreakdownChart();
  }

  watch(() => [props.activeDesk, profile.value], renderCharts, { deep: true });
  onMounted(renderCharts);
</script>

<style scoped lang="less">
  .pnl-panel {
    display: grid;
    gap: var(--strategy-space-2);
  }

  .pnl-overview-card,
  .metric-card,
  .attribution-card,
  .detail-curve-card,
  .breakdown-curve-card,
  .leg-snapshot-card {
    border: 1px solid var(--strategy-border);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .pnl-overview-card {
    padding: 18px 20px 12px;
    border-radius: var(--strategy-radius-panel);
  }

  .pnl-overview-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  .pnl-overview-header h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-section-title);
    font-weight: 800;
  }

  .pnl-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 10px;
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  .pnl-meta em {
    color: var(--strategy-accent-strong);
    font-style: normal;
  }

  .pnl-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
  }

  .period-tabs {
    display: inline-flex;
    gap: 6px;
    padding: 5px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .period-tabs button,
  .legend-pill {
    height: var(--strategy-control-height);
    border: none;
    background: transparent;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  .period-tabs button {
    min-width: 58px;
    padding: 0 14px;
    border-radius: var(--strategy-radius-control);
  }

  .period-tabs button.is-active {
    background: var(--strategy-accent-soft);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
    color: var(--strategy-accent-strong);
  }

  .legend-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .legend-pill span {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .legend-pill.is-return span {
    background: #5cc548;
  }

  .legend-pill.is-net span {
    background: #5aa7ef;
  }

  .overview-chart {
    height: 380px;
    margin-top: 12px;
  }

  .metric-grid,
  .attribution-board,
  .detail-curve-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--strategy-space-2);
  }

  .metric-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .attribution-board {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .detail-curve-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .metric-card,
  .attribution-card,
  .detail-curve-card {
    border-radius: var(--strategy-radius-card);
  }

  .metric-card,
  .attribution-card {
    display: grid;
    gap: 10px;
    padding: 16px;
    box-shadow: var(--strategy-shadow-soft);
  }

  .metric-card label,
  .attribution-card label {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  .metric-card strong,
  .attribution-card strong {
    color: var(--strategy-text-1);
    font-size: 22px;
    line-height: 1.1;
  }

  .metric-card span,
  .attribution-card span {
    font-size: var(--strategy-font-base);
    font-weight: 800;
  }

  .is-positive {
    color: var(--strategy-success) !important;
  }

  .is-negative {
    color: var(--strategy-danger) !important;
  }

  .is-neutral {
    color: var(--strategy-text-1) !important;
  }

  .breakdown-curve-card {
    padding: 16px 16px 8px;
    border-radius: var(--strategy-radius-panel);
  }

  .breakdown-curve-header h3 {
    margin: 0 0 8px;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .breakdown-chart {
    height: 300px;
  }

  .leg-snapshot-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--strategy-space-2);
  }

  .leg-snapshot-card {
    display: grid;
    padding: 16px;
    border-radius: var(--strategy-radius-panel);
    gap: 12px;
  }

  .leg-snapshot-card header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .leg-snapshot-card h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .leg-snapshot-card span,
  .leg-snapshot-card strong {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  .leg-snapshot-card strong {
    color: var(--strategy-accent-strong);
  }

  .leg-snapshot-card dl {
    display: grid;
    margin: 0;
  }

  .leg-snapshot-card dl div {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 12px 0;
    border-bottom: 1px solid var(--strategy-border-soft);
  }

  .leg-snapshot-card dt {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .leg-snapshot-card dd {
    margin: 0;
    color: var(--strategy-text-1);
    font-weight: 800;
  }

  @media (max-width: 1180px) {
    .metric-grid,
    .attribution-board,
    .leg-snapshot-grid,
    .detail-curve-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 860px) {
    .pnl-overview-header {
      flex-direction: column;
    }

    .pnl-actions {
      justify-content: flex-start;
    }

    .metric-grid,
    .attribution-board,
    .leg-snapshot-grid,
    .detail-curve-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
