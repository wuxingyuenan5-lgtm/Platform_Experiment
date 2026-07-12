<template>
  <section class="overview-card">
    <div class="overview-chart-shell">
      <div class="overview-chart-toolbar">
        <div class="overview-chart-title">
          <h3>策略损益总览</h3>
          <div class="overview-chart-meta">
            <span>{{ current.periodLabel }}</span>
            <strong>{{ current.dateLabel }}</strong>
            <em>总资金：{{ current.totalFund }}</em>
          </div>
        </div>

        <div class="overview-chart-actions">
          <div class="period-group">
            <button
              v-for="item in periods"
              :key="item.key"
              type="button"
              :class="{ 'is-active': item.key === activePeriod }"
              @click="$emit('update:activePeriod', item.key)"
            >
              {{ item.label }}
            </button>
          </div>

          <div class="legend-group">
            <button type="button" :class="{ 'is-active': showDaily }" @click="showDaily = !showDaily">
              <span class="dot dot-daily"></span>
              日度收益
            </button>
            <button type="button" :class="{ 'is-active': showNet }" @click="showNet = !showNet">
              <span class="dot dot-net"></span>
              净值曲线
            </button>
          </div>
        </div>
      </div>

      <div ref="chartRef" class="overview-chart"></div>
    </div>

    <div class="stat-card-grid">
      <article v-for="item in current.statCards" :key="item.label" class="stat-card">
        <label>{{ item.label }}</label>
        <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
        <p>{{ item.subValue || '--' }}</p>
      </article>
    </div>

    <div class="overview-bottom-grid">
      <article class="overview-table-card">
        <header class="green">盈利归因</header>
        <table>
          <thead>
            <tr>
              <th>类型</th>
              <th>策略数</th>
              <th>PnL</th>
              <th>占比</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in current.profitRows" :key="row.type">
              <td>{{ row.type }}</td>
              <td>{{ row.strategyCount }}</td>
              <td class="positive">{{ row.pnl }}</td>
              <td>{{ row.ratio }}</td>
            </tr>
          </tbody>
        </table>
      </article>

      <article class="overview-table-card">
        <header class="red">亏损归因</header>
        <table>
          <thead>
            <tr>
              <th>类型</th>
              <th>策略数</th>
              <th>PnL</th>
              <th>占比</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in current.lossRows" :key="row.type">
              <td>{{ row.type }}</td>
              <td>{{ row.strategyCount }}</td>
              <td class="negative">{{ row.pnl }}</td>
              <td>{{ row.ratio }}</td>
            </tr>
          </tbody>
        </table>
      </article>
    </div>

    <article class="sync-card">
      <div class="sync-card__header">
        <div>
          <h4>运行同步状态</h4>
          <p>按钮会直接改变前端状态，用来验收交互链路和页面反馈。</p>
        </div>
        <div class="sync-card__actions">
          <button type="button" @click="refreshPositions">刷新持仓</button>
          <button type="button" class="primary" @click="syncFees">同步费率</button>
        </div>
      </div>

      <div v-if="lastActionMessage" class="sync-banner">{{ lastActionMessage }}</div>

      <table>
        <thead>
          <tr>
            <th>类型</th>
            <th>状态</th>
            <th>信息</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in syncRows" :key="`${row.category}-${row.time}`">
            <td>{{ row.category }}</td>
            <td :class="row.tone ? row.tone : 'neutral'">{{ row.status }}</td>
            <td>{{ row.message }}</td>
            <td>{{ row.time }}</td>
          </tr>
        </tbody>
      </table>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { StrategyOverviewConfig, StrategyPeriodKey, StrategySyncRow } from '../types';

  const props = defineProps<{
    overview: StrategyOverviewConfig;
    activePeriod: StrategyPeriodKey;
  }>();

  defineEmits<{
    (e: 'update:activePeriod', value: StrategyPeriodKey): void;
  }>();

  const periods = computed(() => props.overview.periods);
  const current = computed(() => props.overview.datasets[props.activePeriod]);
  const syncRows = ref<StrategySyncRow[]>([]);
  const lastActionMessage = ref('');
  const showDaily = ref(true);
  const showNet = ref(true);
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);

  async function renderChart() {
    await setOptions({
      color: ['#69c645', '#5ca8e7'],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: { show: false },
      grid: {
        left: 20,
        right: 30,
        top: 42,
        bottom: 58,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: current.value.xLabels,
        axisTick: { show: false },
        axisLabel: {
          color: '#98a2b3',
          hideOverlap: true,
        },
      },
      yAxis: [
        {
          type: 'value',
          name: '日度收益',
          splitLine: {
            lineStyle: {
              color: 'rgba(148, 163, 184, 0.18)',
              type: 'dashed',
            },
          },
          axisLabel: { color: '#98a2b3' },
        },
        {
          type: 'value',
          name: '净值',
          scale: true,
          axisLabel: { color: '#98a2b3' },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 18,
          bottom: 8,
          borderColor: 'rgba(205, 214, 224, 0.8)',
          fillerColor: 'rgba(125, 167, 255, 0.12)',
          backgroundColor: 'rgba(240, 244, 248, 0.9)',
        },
      ],
      series: [
        ...(showDaily.value
          ? [{
              name: '日度收益',
              type: 'bar',
              barWidth: 14,
              itemStyle: {
                borderRadius: [4, 4, 0, 0],
                color: (params: { value: number }) => (params.value >= 0 ? '#69c645' : '#ef6b67'),
              },
              data: current.value.barValues,
            }]
          : []),
        ...(showNet.value
          ? [{
              name: '净值曲线',
              type: 'line',
              yAxisIndex: 1,
              smooth: true,
              symbol: 'none',
              lineStyle: {
                width: 3,
                color: '#5ca8e7',
              },
              areaStyle: {
                color: 'rgba(92, 168, 231, 0.08)',
              },
              data: current.value.lineValues,
            }]
          : []),
      ],
    });
    await nextTick();
    resize();
  }

  watch(
    () => current.value.syncRows,
    (rows) => {
      syncRows.value = rows.map((item) => ({ ...item }));
      lastActionMessage.value = '';
    },
    { immediate: true, deep: true },
  );

  watch([current, showDaily, showNet], renderChart, { deep: true });
  onMounted(renderChart);

  function stampRow(target: string, status: string, message: string, tone: StrategySyncRow['tone']) {
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    syncRows.value = syncRows.value.map((row, index) =>
      index === 0 || row.category === target ? { ...row, status, message, time, tone } : row,
    );
    lastActionMessage.value = message;
  }

  function refreshPositions() {
    stampRow('持仓同步', '已刷新', '持仓快照已经刷新，当前页卡片与图表重新对齐。', 'positive');
  }

  function syncFees() {
    stampRow('费率同步', '同步完成', '最新费率和借贷成本已经回写到前端状态。', 'positive');
  }
</script>

<style scoped lang="less">
  .overview-card {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .overview-chart-shell,
  .sync-card {
    padding: 20px;
    border-radius: 20px;
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
    border: 1px solid var(--strategy-border);
  }

  .overview-chart-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .overview-chart-title h3,
  .sync-card h4 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 18px;
    font-weight: 900;
  }

  .overview-chart-meta {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-top: 10px;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .overview-chart-meta strong {
    color: var(--strategy-text-1);
  }

  .overview-chart-meta em {
    color: #c18d3f;
    font-style: normal;
    font-weight: 700;
  }

  .overview-chart-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .period-group {
    display: inline-flex;
    padding: 3px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface);
  }

  .period-group button,
  .legend-group button {
    min-width: 58px;
    height: 32px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface);
    color: var(--strategy-text-3);
    font-weight: 700;
    cursor: pointer;
  }

  .period-group button {
    border: none;
  }

  .period-group .is-active {
    color: var(--strategy-accent-strong);
    background: var(--strategy-accent-soft);
  }

  .legend-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .legend-group button {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-width: auto;
    padding: 0 12px;
  }

  .legend-group .is-active {
    border-color: rgba(201, 72, 72, 0.14);
    background: var(--strategy-surface-selected);
    color: var(--strategy-text-1);
  }

  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .dot-daily {
    background: #69c645;
  }

  .dot-net {
    background: #5ca8e7;
  }

  .overview-chart {
    height: 360px;
    margin-top: 14px;
  }

  .stat-card-grid,
  .overview-bottom-grid {
    display: grid;
    gap: 16px;
  }

  .stat-card-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .overview-bottom-grid {
    grid-template-columns: 1fr 1fr;
  }

  .stat-card,
  .overview-table-card {
    padding: 16px 18px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.88);
    box-shadow: inset 0 0 0 1px rgba(229, 235, 243, 0.9);
  }

  .stat-card label {
    color: #8a94a1;
    font-size: 12px;
  }

  .stat-card strong {
    display: block;
    margin: 10px 0 6px;
    font-size: 26px;
  }

  .stat-card p {
    margin: 0;
    color: #9aa3af;
    font-size: 12px;
  }

  .overview-table-card header {
    margin-bottom: 10px;
    font-size: 16px;
    font-weight: 700;
  }

  .overview-table-card header.green {
    color: #67b74a;
  }

  .overview-table-card header.red {
    color: #e76c68;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 12px 8px;
    border-bottom: 1px solid #edf0f3;
    text-align: left;
    font-size: 13px;
  }

  th {
    color: #8a94a1;
    font-weight: 700;
  }

  td {
    color: #314150;
    font-weight: 600;
  }

  .positive {
    color: #1d9f6e;
  }

  .negative {
    color: #d8585f;
  }

  .neutral {
    color: #1f2e3d;
  }

  .sync-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
  }

  .sync-card p {
    display: none;
  }

  .sync-card__actions {
    display: flex;
    gap: 10px;
  }

  .sync-card__actions button {
    height: 34px;
    padding: 0 14px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background: #fff;
    color: #667085;
    cursor: pointer;
  }

  .sync-card__actions .primary {
    border-color: #d15e66;
    color: #d15e66;
    background: #fff8f8;
  }

  .sync-banner {
    margin-bottom: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    background: #f4fbf7;
    color: #1d9f6e;
    font-size: 13px;
    font-weight: 600;
  }

  @media (max-width: 1480px) {
    .stat-card-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  @media (max-width: 1100px) {
    .overview-bottom-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 860px) {
    .overview-chart-toolbar,
    .sync-card__header {
      flex-direction: column;
      align-items: flex-start;
    }

    .stat-card-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
