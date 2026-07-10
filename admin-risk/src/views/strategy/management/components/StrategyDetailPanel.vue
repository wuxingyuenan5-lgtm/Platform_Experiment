<template>
  <article class="detail-card">
    <header class="detail-card__header">
      <div class="detail-title">
        <h3>{{ detail.title }}</h3>
        <span :class="statusClass">{{ detail.status }}</span>
      </div>
      <div class="detail-actions">
        <button
          v-for="item in detail.actions"
          :key="item"
          type="button"
          :class="{ primary: item.includes('加仓') || item.includes('平仓') }"
          @click="triggerAction(item)"
        >
          {{ item }}
        </button>
      </div>
    </header>

    <div class="detail-metrics">
      <article v-for="item in detail.metrics" :key="item.label" class="detail-metric">
        <label>{{ item.label }}</label>
        <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
      </article>
    </div>

    <div class="detail-main">
      <section class="detail-legs">
        <article v-for="leg in detail.legs" :key="`${leg.title}-${leg.symbol}`" class="leg-card">
          <header>
            <div>
              <h4>{{ leg.title }}</h4>
              <span>{{ leg.market }}</span>
            </div>
            <strong>{{ leg.symbol }}</strong>
          </header>

          <div class="leg-actions">
            <button
              v-for="action in leg.actions"
              :key="action"
              type="button"
              @click="triggerAction(`${leg.title} · ${action}`)"
            >
              {{ action }}
            </button>
          </div>

          <table>
            <tbody>
              <tr v-for="row in leg.rows" :key="row.label">
                <td>{{ row.label }}</td>
                <td :class="row.tone ? row.tone : 'neutral'">{{ row.value }}</td>
              </tr>
            </tbody>
          </table>
        </article>
      </section>

      <aside class="exposure-card">
        <h4>敞口分析</h4>
        <table>
          <tbody>
            <tr v-for="row in detail.exposureRows" :key="row.label">
              <td>{{ row.label }}</td>
              <td :class="row.tone ? row.tone : 'neutral'">{{ row.value }}</td>
            </tr>
          </tbody>
        </table>
      </aside>
    </div>

    <div class="detail-tabs">
      <button
        v-for="item in detail.tabs"
        :key="item.key"
        type="button"
        :class="{ 'is-active': item.key === activeTab }"
        @click="activeTab = item.key"
      >
        {{ item.label }}
      </button>
    </div>

    <div v-if="actionMessage" class="action-banner">{{ actionMessage }}</div>

    <div v-if="activeTab === 'curve'" class="detail-curve">
      <div ref="chartRef" class="detail-curve__chart"></div>
      <div class="curve-legend">
        <span class="net">净收益</span>
        <span class="position">合约盈亏</span>
        <span class="spot">现货盈亏</span>
        <span class="funding">费率累计</span>
        <span class="fee">手续费</span>
      </div>
    </div>

    <div v-else class="detail-table-wrap">
      <table>
        <thead>
          <tr>
            <th v-for="column in currentTable.columns" :key="column.key">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in currentTable.rows" :key="index">
            <td v-for="column in currentTable.columns" :key="column.key">{{ row[column.key] || '--' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </article>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { StrategyDetailSnapshot } from '../types';

  const props = defineProps<{ detail: StrategyDetailSnapshot }>();

  const activeTab = ref(props.detail.tabs[0]?.key || 'records');
  const currentTable = computed(() => props.detail.tabTables[activeTab.value] ?? { columns: [], rows: [] });
  const statusClass = computed(() =>
    props.detail.status.includes('运行') ? 'running' : props.detail.status.includes('结束') ? 'ended' : 'neutral',
  );
  const actionMessage = ref('');
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);

  const curveAxis = ['06-01', '06-03', '06-05', '06-07', '06-09', '06-11', '06-13', '06-15', '06-17', '06-19', '06-21', '06-23'];
  const curveSeries = {
    net: [0, 220, 350, 318, 402, 438, 466, 490, 521, 548, 572, 601],
    position: [0, -1180, -4410, -3950, -4620, -4720, -4310, -3880, 2620, 2740, 2810, 2900],
    spot: [0, 980, 3920, 3760, 4180, 4360, 4280, 4030, -2140, -2310, -2450, -2620],
    funding: [0, 42, 68, 86, 110, 138, 176, 214, 259, 302, 344, 392],
    fee: [0, -8, -14, -21, -28, -34, -41, -47, -53, -58, -63, -71],
  };

  async function renderCurveChart() {
    if (activeTab.value !== 'curve') return;
    await setOptions({
      color: ['#ffffff', '#90d27a', '#f3c14d', '#ea6a67', '#6bb6e8'],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: {
        top: 0,
        right: 0,
        itemWidth: 10,
        itemHeight: 10,
        data: ['净收益', '合约盈亏', '现货盈亏', '费率累计', '手续费'],
      },
      grid: {
        left: 24,
        right: 20,
        top: 42,
        bottom: 54,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: curveAxis,
        boundaryGap: false,
        axisTick: { show: false },
        axisLabel: { color: '#98a2b3' },
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.18)',
            type: 'dashed',
          },
        },
        axisLabel: { color: '#98a2b3' },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 16,
          bottom: 8,
          borderColor: 'rgba(205, 214, 224, 0.8)',
          fillerColor: 'rgba(125, 167, 255, 0.12)',
          backgroundColor: 'rgba(240, 244, 248, 0.9)',
        },
      ],
      series: [
        {
          name: '净收益',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 3, color: '#cbd5e1' },
          data: curveSeries.net,
        },
        { name: '合约盈亏', type: 'line', smooth: true, symbol: 'none', data: curveSeries.position },
        { name: '现货盈亏', type: 'line', smooth: true, symbol: 'none', data: curveSeries.spot },
        { name: '费率累计', type: 'line', smooth: true, symbol: 'none', data: curveSeries.funding },
        { name: '手续费', type: 'line', smooth: true, symbol: 'none', data: curveSeries.fee },
      ],
    });
    await nextTick();
    resize();
  }

  watch(activeTab, renderCurveChart);
  onMounted(renderCurveChart);

  function triggerAction(label: string) {
    actionMessage.value = `已触发「${label}」前端动作，程序员后续只需要把这里接入真实接口与状态机。`;
  }
</script>

<style scoped lang="less">
  .detail-card {
    padding: 22px;
    border-radius: 24px;
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
    border: 1px solid var(--strategy-border);
  }
  .detail-card__header,
  .detail-title,
  .detail-actions,
  .detail-tabs {
    display: flex;
    align-items: center;
  }
  .detail-card__header {
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }
  .detail-title {
    gap: 12px;
  }
  .detail-title h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 24px;
    font-weight: 900;
  }
  .detail-title span {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
  }
  .detail-title .running { color: #2e9e67; background: #e9f8f0; }
  .detail-title .ended { color: #9aa3af; background: #f3f4f6; }
  .detail-actions {
    gap: 10px;
    flex-wrap: wrap;
  }
  .detail-actions button,
  .leg-actions button,
  .detail-tabs button {
    height: 34px;
    padding: 0 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    cursor: pointer;
  }
  .detail-actions .primary {
    background: var(--strategy-accent-soft);
    border-color: rgba(201, 72, 72, 0.18);
    color: var(--strategy-accent-strong);
  }
  .detail-metrics {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }
  .detail-metric,
  .leg-card,
  .exposure-card {
    padding: 16px 18px;
    border-radius: 18px;
    background: rgba(255,255,255,.88);
    box-shadow: inset 0 0 0 1px rgba(229, 235, 243, 0.92);
  }
  .detail-metric label {
    color: #8a94a1;
    font-size: 12px;
  }
  .detail-metric strong {
    display: block;
    margin-top: 10px;
    font-size: 24px;
  }
  .detail-main {
    display: grid;
    grid-template-columns: 1.4fr .7fr;
    gap: 16px;
    margin-bottom: 16px;
  }
  .detail-legs {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
  .leg-card header {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }
  .leg-card h4,
  .exposure-card h4 {
    margin: 0;
    color: #334155;
    font-size: 16px;
  }
  .leg-card header span {
    color: #8a94a1;
    font-size: 12px;
  }
  .leg-card header strong {
    color: #60a5fa;
    font-size: 13px;
  }
  .leg-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  td, th {
    padding: 10px 8px;
    border-bottom: 1px solid #edf0f3;
    text-align: left;
    font-size: 13px;
  }
  td:last-child, th:last-child {
    text-align: right;
  }
  th {
    color: #8a94a1;
    font-weight: 700;
  }
  td {
    color: #314150;
    font-weight: 600;
  }
  .positive { color: #1d9f6e; }
  .negative { color: #d8585f; }
  .neutral { color: #1f2e3d; }
  .detail-tabs {
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 14px;
  }
  .detail-tabs .is-active {
    color: var(--strategy-accent-strong);
    border-color: rgba(201, 72, 72, 0.18);
    background: var(--strategy-accent-soft);
  }
  .action-banner {
    margin-bottom: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    font-size: 13px;
    font-weight: 700;
  }
  .detail-curve {
    padding: 16px;
    border-radius: 18px;
    background: rgba(255,255,255,.88);
    box-shadow: inset 0 0 0 1px rgba(229, 235, 243, 0.92);
  }
  .detail-curve__chart {
    width: 100%;
    height: 280px;
  }
  .curve-legend {
    display: flex;
    justify-content: center;
    gap: 18px;
    flex-wrap: wrap;
    margin-top: 8px;
    color: #6b7280;
    font-size: 12px;
    font-weight: 700;
  }
  .curve-legend span::before {
    display: inline-block;
    width: 12px;
    height: 12px;
    margin-right: 6px;
    border-radius: 50%;
    content: '';
  }
  .curve-legend .net::before { background: #ffffff; border: 1px solid #cbd5e1; }
  .curve-legend .position::before { background: #90d27a; }
  .curve-legend .spot::before { background: #f3c14d; }
  .curve-legend .funding::before { background: #ea6a67; }
  .curve-legend .fee::before { background: #6bb6e8; }
  .detail-table-wrap {
    overflow: auto;
  }
  @media (max-width: 1480px) {
    .detail-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  }
  @media (max-width: 1200px) {
    .detail-main,
    .detail-legs { grid-template-columns: 1fr; }
  }
  @media (max-width: 860px) {
    .detail-card__header,
    .detail-title { flex-direction: column; align-items: flex-start; }
    .detail-metrics { grid-template-columns: 1fr; }
  }
</style>
