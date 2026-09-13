<template>
  <section class="pnl-panel">
    <template v-if="view === 'overview'">
      <article class="pnl-overview-card">
        <header class="pnl-overview-header">
          <div>
            <h3>损益总览</h3>
            <div class="pnl-meta">
              <em>{{ profile.totalFund }}</em>
              <span>{{ profile.period }}</span>
            </div>
          </div>

          <div class="pnl-actions">
            <label class="precision-control"
              >时间精度
              <select v-model="precision" aria-label="收益曲线时间精度">
                <option v-for="item in curvePrecisions" :key="item.key" :value="item.key">{{
                  item.label
                }}</option>
              </select>
            </label>
            <div v-if="profile.curveKind !== 'realized'" class="period-tabs">
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
            <button
              v-if="profile.curveKind !== 'realized'"
              type="button"
              class="legend-pill is-return"
            >
              <span></span>
              日度收益
            </button>
            <button type="button" class="legend-pill is-net">
              <span></span>
              {{
                profile.curveKind === 'realized'
                  ? `已实现损益 ${profile.curveCurrency || ''}`
                  : '净值曲线'
              }}
            </button>
          </div>
        </header>

        <div ref="overviewChartRef" class="overview-chart"></div>
      </article>

      <section class="metric-grid">
        <article v-for="item in profile.metrics" :key="item.label" class="metric-card">
          <label>{{ item.label }}</label>
          <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
          <span v-if="item.ratio" :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{
            item.ratio
          }}</span>
        </article>
      </section>

      <section class="attribution-board">
        <article v-for="item in profile.attributions" :key="item.label" class="attribution-card">
          <label>{{ item.label }}</label>
          <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
          <span v-if="item.ratio" :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{
            item.ratio
          }}</span>
        </article>
      </section>
    </template>

    <StrategyPnlCalendar
      v-if="view === 'daily-position' && !distributionOnly"
      :points="profile.dailyPnl ?? []"
      :currency="profile.dailyPnlCurrency || profile.curveCurrency || ''"
      :load-error="profile.totalFund"
    />

    <article
      v-if="view === 'daily-position' && !hideDistribution"
      :class="['position-distribution-card', { 'is-embedded': distributionOnly }]"
    >
      <header class="position-distribution-header">
        <h3>{{ positionDistribution.title }}</h3>
        <div class="position-distribution-meta">
          <span>
            <em>{{ positionDistribution.grossLabel }}</em>
            {{ positionDistribution.gross }}
          </span>
        </div>
      </header>

      <div v-if="positionDistribution.slices.length" class="position-distribution-body">
        <div ref="distributionChartRef" class="position-distribution-chart"></div>
        <div class="position-distribution-legend">
          <header class="legend-header">
            <span>仓位详情</span>
            <strong>总名义 {{ positionDistribution.gross }}</strong>
          </header>
          <ul>
            <li v-for="(leg, legIndex) in positionDistribution.slices" :key="leg.label">
              <i class="legend-dot" :style="{ background: sliceColor(legIndex) }"></i>
              <span class="legend-name">{{ leg.label }}</span>
              <span class="legend-amount">{{ leg.amount }}</span>
              <span class="legend-share">{{ leg.share }}</span>
            </li>
          </ul>
        </div>
      </div>

      <p v-else class="position-distribution-empty">{{ positionDistribution.emptyMessage }}</p>
    </article>

    <template v-if="view === 'overview'">
      <article class="breakdown-curve-card">
        <header class="breakdown-curve-header">
          <h3>损益细分总图</h3>
        </header>
        <div ref="breakdownChartRef" class="breakdown-chart"></div>
      </article>

      <section class="detail-curve-grid">
        <StrategyCurveCardChart v-for="item in detailCurveCards" :key="item.title" :item="item" />
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import {
    strategyPnlProfiles,
    type StrategyDeskKey,
    type StrategyPnlProfile,
    type StrategyPositionDistribution,
  } from '@/data/sample/strategy';
  import StrategyCurveCardChart from './StrategyCurveCardChart.vue';
  import StrategyPnlCalendar from './StrategyPnlCalendar.vue';
  import {
    curvePrecisions,
    samplePnlCurve,
    type CurvePrecision,
  } from '../composables/strategyCurvePrecision';

  const props = defineProps<{
    activeDesk: StrategyDeskKey;
    liveProfile?: StrategyPnlProfile | null;
    view?: 'overview' | 'daily-position';
    distributionOnly?: boolean;
    hideDistribution?: boolean;
  }>();

  const view = computed(() => props.view ?? 'overview');
  const distributionOnly = computed(() => props.distributionOnly ?? false);
  const hideDistribution = computed(() => props.hideDistribution ?? false);

  const periodTabs = ['日报', '周报', '月报', '自定义'];
  const activePeriod = ref('周报');
  const precision = ref<CurvePrecision>('day');
  const overviewChartRef = ref<HTMLDivElement | null>(null);
  const breakdownChartRef = ref<HTMLDivElement | null>(null);
  const distributionChartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(overviewChartRef as Ref<HTMLDivElement>);
  const { setOptions: setBreakdownOptions, resize: resizeBreakdown } = useECharts(
    breakdownChartRef as Ref<HTMLDivElement>,
  );
  const { setOptions: setDistributionOptions, resize: resizeDistribution } = useECharts(
    distributionChartRef as Ref<HTMLDivElement>,
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

  const sourceProfile = computed(() => {
    const base = strategyPnlProfiles[props.activeDesk];
    if (props.liveProfile) return props.liveProfile;
    if (props.activeDesk !== 'crossSpread') return base;
    if (!props.liveProfile) return emptyCrossSpreadProfile;
    return emptyCrossSpreadProfile;
  });
  const profile = computed(() => samplePnlCurve(sourceProfile.value, precision.value));
  const detailCurveCards = computed(() =>
    profile.value.detailCurves.map((item) => ({
      title: item.title,
      amount: item.value,
      unit: '',
      tone: item.tone,
      points: item.data.map((value, index) => ({
        date: profile.value.xLabels[index],
        value,
      })),
    })),
  );

  const emptyDistribution: StrategyPositionDistribution = {
    title: '仓位分布',
    currency: '',
    mixedCurrency: false,
    grossLabel: '持仓价值（双边）',
    gross: '--',
    netLabel: '净敞口（对冲后）',
    net: '--',
    groups: [],
    slices: [],
    emptyMessage: '接口待接入',
  };
  const positionDistribution = computed(
    () => profile.value.positionDistribution ?? emptyDistribution,
  );

  const distributionPalette = [
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
  function sliceColor(legIndex: number): string {
    return distributionPalette[legIndex % distributionPalette.length];
  }

  async function renderDistributionChart() {
      const distribution = positionDistribution.value;
    if (!distribution.slices.length) return;
    await setDistributionOptions({
      tooltip: {
        trigger: 'item',
        formatter: (params: any) =>
          `${params.name}<br/>${params.marker} ${Number(params.value).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}<br/>${params.percent ? `${params.percent.toFixed(2)}%` : ''}`,
        borderWidth: 0,
      },
      series: [
        {
          name: '净仓位',
          type: 'pie',
          radius: ['50%', '80%'],
          center: ['50%', '50%'],
          minAngle: 8,
          avoidLabelOverlap: true,
          silent: false,
          label: {
            show: true,
            formatter: (params: any) => `${params.name}`,
            position: 'outside',
            fontSize: 11,
            color: '#42526b',
            lineHeight: 14,
            distance: 8,
          },
          labelLine: {
            show: true,
            length: 8,
            length2: 8,
            lineStyle: { color: 'rgba(66, 82, 107, 0.35)', width: 1 },
          },
          itemStyle: {
            borderColor: 'var(--strategy-surface)',
            borderWidth: 2,
            borderRadius: 8,
            shadowColor: 'rgba(28, 58, 91, 0.18)',
            shadowBlur: 16,
          },
          emphasis: {
            scale: true,
            scaleSize: 6,
            focus: 'self',
            itemStyle: {
              shadowBlur: 20,
              shadowColor: 'rgba(52, 74, 102, 0.24)',
              shadowOffsetX: 0,
              shadowOffsetY: 6,
            },
          },
          data: distribution.slices.map((slice, index) => ({
            name: `${slice.label}${distribution.mixedCurrency ? ` · ${slice.currency}` : ''}`,
            value: slice.value,
            itemStyle: { color: sliceColor(index) },
          })),
        },
      ] as any,
    });
    await nextTick();
    resizeDistribution();
  }

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
          name: profile.value.curveKind === 'realized' ? '' : '日度收益',
          splitLine: { lineStyle: { color: 'rgba(132, 148, 168, 0.18)', type: 'dashed' } },
          axisLabel: { color: '#8392aa' },
        },
        {
          type: 'value',
          name: profile.value.curveKind === 'realized' ? '已实现损益' : '净值',
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
          name: profile.value.curveKind === 'realized' ? '' : '日度收益',
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
          name: profile.value.curveKind === 'realized' ? '已实现损益' : '净值曲线',
          type: 'line',
          yAxisIndex: 1,
          smooth: profile.value.curveKind !== 'realized',
          step: profile.value.curveKind === 'realized' ? 'end' : false,
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
    if (view.value === 'overview') {
      renderOverviewChart();
      renderBreakdownChart();
    } else {
      renderDistributionChart();
    }
  }

  watch(() => [props.activeDesk, props.view, profile.value], renderCharts, {
    deep: true,
    flush: 'post',
  });
  onMounted(renderCharts);
</script>

<style scoped lang="less">
  .precision-control {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--strategy-text-2);
    white-space: nowrap;
  }

  .precision-control select {
    padding: 6px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface);
    color: inherit;
  }

  .pnl-panel {
    display: grid;
    gap: var(--strategy-space-2);
  }

  .pnl-overview-card,
  .metric-card,
  .attribution-card,
  .detail-curve-card,
  .breakdown-curve-card,
  .position-distribution-card,
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

  .position-distribution-card {
    display: grid;
    gap: 14px;
    padding: 18px 20px;
    border-radius: var(--strategy-radius-panel);
  }

  .position-distribution-card.is-embedded {
    padding: 0;
    margin-top: 16px;
    border: none;
    background: transparent;
    box-shadow: none;
  }

  .position-distribution-header {
    display: grid;
    gap: 14px;
  }

  .position-distribution-header h3 {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 20px;
    line-height: 1.2;
    font-weight: 900;
    letter-spacing: 0.02em;
  }

  .position-distribution-header h3::before {
    width: 4px;
    height: 18px;
    border-radius: 999px;
    background: linear-gradient(180deg, var(--strategy-accent), var(--strategy-accent-strong));
    content: '';
  }

  .position-distribution-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 18px;
    margin-top: 4px;
    color: var(--strategy-text-1);
    font-size: 15px;
    font-weight: 800;
    line-height: 1.65;
  }

  .position-distribution-meta em {
    display: inline;
    margin-right: 8px;
    margin-bottom: 0;
    color: var(--strategy-text-3);
    font-style: normal;
    font-weight: 700;
  }

  .position-distribution-body {
    display: grid;
    grid-template-columns: minmax(0, 300px) minmax(0, 1fr);
    align-items: center;
    gap: 18px;
  }

  .position-distribution-chart {
    height: 260px;
  }

  .position-distribution-legend {
    display: grid;
    gap: 12px;
    padding: 12px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: var(--strategy-radius-card);
    background: linear-gradient(
      180deg,
      rgba(250, 253, 255, 0.9),
      rgba(243, 248, 255, 0.45)
    );
  }

  .position-distribution-legend ul {
    display: grid;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .legend-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--strategy-border-soft);
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  .legend-header strong {
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 800;
  }

  .position-distribution-legend li {
    display: grid;
    grid-template-columns: 12px minmax(0, 1fr) auto auto;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .legend-name {
    color: var(--strategy-text-2);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }

  .legend-amount {
    color: var(--strategy-text-1);
    font-weight: 800;
  }

  .legend-share {
    min-width: 64px;
    color: var(--strategy-accent-strong);
    font-weight: 800;
    text-align: right;
  }

  .position-distribution-empty {
    margin: 0;
    padding: 24px 0;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    text-align: center;
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

    .position-distribution-body {
      grid-template-columns: 1fr;
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
