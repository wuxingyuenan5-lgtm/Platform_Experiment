<template>
  <section class="orders-stack">
    <article class="orders-card">
      <header class="orders-head">
        <div class="fund-tabs">
          <button
            v-for="item in fundTabs"
            :key="item"
            type="button"
            class="fund-tab"
            :class="{ 'is-active': activeFund === item }"
            @click="activeFund = item"
          >
            {{ item }}
          </button>
        </div>
        <span class="timestamp">2025-11-12 16:08:04</span>
      </header>

      <div class="stat-grid">
        <article v-for="item in orderStats" :key="item.label" class="stat-card">
          <label>{{ item.label }}</label>
          <span>{{ item.unit }}</span>
          <strong :class="item.tone ? `is-${item.tone}` : ''">{{ item.value }}</strong>
        </article>
      </div>

      <div class="chart-grid">
        <article class="chart-card">
          <h4>波动率</h4>
          <div ref="volRef" class="chart-stage"></div>
        </article>
        <article class="chart-card">
          <h4>夏普比率</h4>
          <div ref="sharpeRef" class="chart-stage"></div>
        </article>
      </div>

      <div class="queue-tabs">
        <button
          v-for="item in queueTabs"
          :key="item.key"
          type="button"
          class="queue-tab"
          :class="{ 'is-active': activeQueue === item.key }"
          @click="activeQueue = item.key"
        >
          {{ item.label }}
        </button>

        <button type="button" class="add-btn">新增指令</button>
      </div>

      <div class="orders-table">
        <table>
          <thead>
            <tr>
              <th v-for="column in orderColumns" :key="column.key">{{ column.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in activeRows" :key="row.title + row.createdAt">
              <td>{{ row.title }}</td>
              <td>{{ row.symbol }}</td>
              <td>{{ row.size }}</td>
              <td>{{ row.mode }}</td>
              <td :class="row.platform === '海外' ? 'tone-negative' : ''">{{ row.platform }}</td>
              <td>{{ row.start }}</td>
              <td>{{ row.end }}</td>
              <td>{{ row.requirement }}</td>
              <td :class="row.status === '执行中' ? 'tone-negative' : 'tone-warning'">{{ row.status }}</td>
              <td>{{ row.createdAt }}</td>
              <td>{{ row.creator }}</td>
              <td>{{ row.trader }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';

  const activeFund = ref('FYBfund01');
  const activeQueue = ref<'pending' | 'done'>('pending');

  const fundTabs = ['FYBfund01', 'FYBfund02'];
  const queueTabs = [
    { key: 'pending', label: '待执行/执行中' },
    { key: 'done', label: '已执行' },
  ] as const;

  const orderStats = computed(() => [
    { label: '账户净值', unit: 'USD', value: activeFund.value === 'FYBfund01' ? '450,391.25' : '398,562.10' },
    { label: '策略类型', unit: '', value: '资费套利' },
    { label: '保证金余额', unit: 'USD', value: activeFund.value === 'FYBfund01' ? '413,710.29' : '366,118.41' },
    { label: '收益率 (%)', unit: '', value: activeFund.value === 'FYBfund01' ? '11.38' : '9.64', tone: 'positive' },
    { label: '过去24h盈亏', unit: 'USD', value: activeFund.value === 'FYBfund01' ? '-5.39' : '+3.82', tone: activeFund.value === 'FYBfund01' ? 'negative' : 'positive' },
    { label: '累计收益', unit: 'USD', value: activeFund.value === 'FYBfund01' ? '51,251.08' : '42,518.77' },
  ]);

  const orderColumns = [
    { key: 'title', label: '指令标题' },
    { key: 'symbol', label: '交易标的' },
    { key: 'size', label: '仓位大小' },
    { key: 'mode', label: '执行方式' },
    { key: 'platform', label: '平台' },
    { key: 'start', label: '开始时间' },
    { key: 'end', label: '结束时间' },
    { key: 'requirement', label: '其他要求' },
    { key: 'status', label: '状态' },
    { key: 'createdAt', label: '创建时间' },
    { key: 'creator', label: '创建人' },
    { key: 'trader', label: '交易员' },
  ];

  const orderRows = {
    pending: [
      {
        title: '沪金-伦敦金 实盘测试1',
        symbol: 'AU2604-XAU',
        size: '1.0000',
        mode: '自动',
        platform: '海外',
        start: '2025-11-05',
        end: '2025-11-05',
        requirement: '无',
        status: '待执行',
        createdAt: '2025-11-05 10:42:14',
        creator: '77',
        trader: 'test',
      },
      {
        title: '测试2',
        symbol: '黄金AU2604',
        size: '1.0000',
        mode: '手动',
        platform: '海外',
        start: '2025-11-04',
        end: '2025-11-08',
        requirement: '--',
        status: '待执行',
        createdAt: '2025-11-04 19:31:50',
        creator: 'admin',
        trader: 'uri',
      },
      {
        title: '123',
        symbol: 'BTCUSDT',
        size: '0.1000',
        mode: '手动',
        platform: '另类',
        start: '2025-05-07',
        end: '2025-05-10',
        requirement: '没有其他要求',
        status: '执行中',
        createdAt: '2025-05-08 11:31:40',
        creator: 'admin',
        trader: 'test',
      },
    ],
    done: [
      {
        title: '海内外价差平仓',
        symbol: 'SHFE.au2612-XAUUSD',
        size: '0.8000',
        mode: '自动',
        platform: '海外',
        start: '2025-10-21',
        end: '2025-10-21',
        requirement: '价差回补',
        status: '已执行',
        createdAt: '2025-10-21 14:02:18',
        creator: 'admin',
        trader: 'hjk',
      },
    ],
  };

  const activeRows = computed(() => orderRows[activeQueue.value]);

  const chartDates = [
    '2024-08-10 00:00',
    '2024-11-10 00:00',
    '2025-02-11 00:00',
    '2025-05-18 00:00',
    '2025-08-27 00:00',
    '2025-11-12 00:00',
  ];
  const volSeries = [0.002, 0.004, 0.006, 0.026, 0.004, 0.003];
  const sharpeSeries = [-18, -6, -28, -58, -14, -23];

  const volRef = ref<HTMLDivElement | null>(null);
  const sharpeRef = ref<HTMLDivElement | null>(null);
  const { setOptions: setVolOptions, resize: resizeVol } = useECharts(volRef as Ref<HTMLDivElement>);
  const { setOptions: setSharpeOptions, resize: resizeSharpe } = useECharts(sharpeRef as Ref<HTMLDivElement>);

  async function renderCharts() {
    await setVolOptions({
      tooltip: { trigger: 'axis' },
      grid: { left: 24, right: 18, top: 18, bottom: 28, containLabel: true },
      xAxis: {
        type: 'category',
        data: chartDates,
        boundaryGap: false,
        axisTick: { show: false },
        axisLabel: { color: '#94a0b1', hideOverlap: true },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#94a0b1' },
        splitLine: { lineStyle: { color: 'rgba(148,163,184,.14)', type: 'dashed' } },
      },
      series: [{ type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#d24c4c', width: 2 }, data: volSeries }],
    });

    await setSharpeOptions({
      tooltip: { trigger: 'axis' },
      grid: { left: 24, right: 18, top: 18, bottom: 28, containLabel: true },
      xAxis: {
        type: 'category',
        data: chartDates,
        boundaryGap: false,
        axisTick: { show: false },
        axisLabel: { color: '#94a0b1', hideOverlap: true },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#94a0b1' },
        splitLine: { lineStyle: { color: 'rgba(148,163,184,.14)', type: 'dashed' } },
      },
      series: [{ type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#d24c4c', width: 2 }, data: sharpeSeries }],
    });

    await nextTick();
    resizeVol();
    resizeSharpe();
  }

  watch([activeFund, activeQueue], renderCharts);
  onMounted(renderCharts);
</script>

<style scoped lang="less">
  .orders-stack {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .orders-card {
    padding: 18px 20px 20px;
    border-radius: 24px;
    border: 1px solid rgba(201, 164, 95, 0.14);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 251, 244, 0.94));
    box-shadow: 0 18px 40px rgba(28, 35, 40, 0.05);
  }

  .orders-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 16px;
  }

  .fund-tabs,
  .queue-tabs {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .fund-tab,
  .queue-tab {
    border: none;
    background: transparent;
    color: #6e7786;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
  }

  .fund-tab.is-active,
  .queue-tab.is-active {
    color: #d14f4f;
  }

  .timestamp {
    color: #7a8698;
    font-size: 13px;
    font-weight: 600;
  }

  .stat-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
  }

  .stat-card {
    min-height: 120px;
    padding: 16px 18px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: inset 0 0 0 1px rgba(201, 164, 95, 0.08);
  }

  .stat-card label,
  .stat-card span {
    display: block;
  }

  .stat-card label {
    color: #394256;
    font-size: 16px;
    font-weight: 700;
  }

  .stat-card span {
    margin-top: 10px;
    color: #8c96a6;
    font-size: 12px;
    font-weight: 600;
  }

  .stat-card strong {
    display: block;
    margin-top: 8px;
    color: #172033;
    font-size: 40px;
    font-weight: 800;
    line-height: 1.1;
  }

  .stat-card strong.is-positive {
    color: #19a767;
  }

  .stat-card strong.is-negative {
    color: #d8585f;
  }

  .chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    margin-top: 18px;
  }

  .chart-card {
    padding: 14px 16px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.82);
    box-shadow: inset 0 0 0 1px rgba(201, 164, 95, 0.08);
  }

  .chart-card h4 {
    margin: 0 0 10px;
    color: #1f2c40;
    font-size: 24px;
    font-weight: 800;
  }

  .chart-stage {
    height: 260px;
  }

  .queue-tabs {
    justify-content: space-between;
    margin-top: 18px;
    padding-top: 10px;
    border-top: 1px solid rgba(229, 235, 242, 0.85);
  }

  .add-btn {
    height: 34px;
    padding: 0 14px;
    border: none;
    border-radius: 10px;
    background: #d63636;
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
  }

  .orders-table {
    margin-top: 14px;
    overflow-x: auto;
  }

  .orders-table table {
    width: 100%;
    min-width: 1280px;
    border-collapse: collapse;
  }

  .orders-table th,
  .orders-table td {
    padding: 13px 12px;
    border-bottom: 1px solid #eef2f7;
    white-space: nowrap;
    text-align: left;
  }

  .orders-table th {
    color: #8a97ab;
    font-size: 12px;
    font-weight: 700;
  }

  .orders-table td {
    color: #31425a;
    font-size: 13px;
    font-weight: 600;
  }

  .tone-negative {
    color: #d8585f !important;
  }

  .tone-warning {
    color: #e48b3a !important;
  }

  .orders-stack,
  .orders-card,
  .stat-card,
  .chart-card,
  .queue-card {
    color: var(--strategy-text-1);
  }

  .orders-card,
  .stat-card,
  .chart-card,
  .queue-card {
    border-color: var(--strategy-border);
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
  }

  .fund-tab,
  .queue-tabs button,
  .add-btn {
    border-color: var(--strategy-border);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
  }

  .fund-tab.is-active,
  .queue-tabs .is-active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  @media (max-width: 1320px) {
    .stat-grid,
    .chart-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
