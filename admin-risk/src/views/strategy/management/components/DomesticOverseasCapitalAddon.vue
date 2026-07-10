<template>
  <section class="capital-stack">
    <article class="capital-card capital-card--table">
      <header class="capital-head capital-head--compact">
        <div>
          <p class="eyebrow">Account Overview</p>
          <h3>账户总览</h3>
        </div>
      </header>

      <div class="table-shell">
        <table class="capital-table">
          <thead>
            <tr>
              <th>产品名称</th>
              <th>账户净值（¥）</th>
              <th>账户净值（$）</th>
              <th>保证金余额（¥）</th>
              <th>保证金余额（$）</th>
              <th>累计收益（¥）</th>
              <th>累计收益（$）</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in overviewRows" :key="row.name">
              <td :class="row.emphasis ? 'is-name-emphasis' : ''">{{ row.name }}</td>
              <td>{{ row.navCny }}</td>
              <td>{{ row.navUsd }}</td>
              <td>{{ row.marginCny }}</td>
              <td>{{ row.marginUsd }}</td>
              <td>{{ row.pnlCny }}</td>
              <td>{{ row.pnlUsd }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>

    <article class="capital-card capital-card--table">
      <header class="capital-head capital-head--compact">
        <div>
          <p class="eyebrow">Account Detail</p>
          <h3>账户-返佣宝</h3>
        </div>
      </header>

      <div class="table-shell">
        <table class="capital-table">
          <thead>
            <tr>
              <th>账户名称</th>
              <th>交易所</th>
              <th>账户净值</th>
              <th>策略类型</th>
              <th>保证金余额</th>
              <th>未实现盈亏</th>
              <th>收益率（%）</th>
              <th>过去24h盈亏</th>
              <th>累计收益</th>
              <th>更新时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in accountRows" :key="row.account">
              <td class="is-name-emphasis">{{ row.account }}</td>
              <td>{{ row.exchange }}</td>
              <td>{{ row.nav }}</td>
              <td>{{ row.strategy }}</td>
              <td>{{ row.margin }}</td>
              <td class="is-positive">{{ row.unrealized }}</td>
              <td :class="row.roe.startsWith('-') ? 'is-negative' : 'is-positive'">{{ row.roe }}</td>
              <td :class="row.dayPnl.startsWith('-') ? 'is-negative' : 'is-positive'">{{ row.dayPnl }}</td>
              <td :class="row.totalPnl.startsWith('-') ? 'is-negative' : 'is-positive'">{{ row.totalPnl }}</td>
              <td>{{ row.updatedAt }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>

    <article class="capital-card">
      <header class="capital-head">
        <div>
          <p class="eyebrow">Account Capital</p>
          <h3>海内外价差账户资金增强看板</h3>
        </div>
      </header>

      <div class="kpi-grid">
        <article v-for="item in capitalKpis" :key="item.label" class="kpi-card">
          <label>{{ item.label }}</label>
          <div v-if="item.split" class="split-block">
            <div v-for="split in item.split" :key="split.name">
              <span>{{ split.name }}</span>
              <strong>{{ split.value }}</strong>
              <em>{{ split.note }}</em>
            </div>
          </div>
          <template v-else>
            <strong>{{ item.value }}</strong>
            <p>{{ item.note }}</p>
          </template>
        </article>
      </div>

      <div class="allocation-grid">
        <article v-for="item in allocationCards" :key="item.label" class="allocation-card">
          <label>{{ item.label }}</label>
          <strong>{{ item.value }}</strong>
          <p>{{ item.ratio }}</p>
        </article>
      </div>
    </article>

    <article class="capital-card">
      <div class="chart-head">
        <div>
          <h4>黄金一号</h4>
          <p>净值曲线</p>
        </div>

        <div class="chart-controls">
          <select v-model="chartMetric">
            <option value="nav">产品净值</option>
            <option value="aum">AUM</option>
          </select>
          <select v-model="chartPeriod">
            <option value="day">天</option>
            <option value="week">周</option>
          </select>
          <button
            type="button"
            class="pill-btn"
            :class="{ 'is-active': fxMode === 'realtime' }"
            @click="fxMode = 'realtime'"
          >
            实时汇率
          </button>
          <button
            type="button"
            class="pill-btn"
            :class="{ 'is-active': fxMode === 'fixed' }"
            @click="fxMode = 'fixed'"
          >
            固定汇率
          </button>
        </div>
      </div>

      <div ref="capitalCurveRef" class="capital-chart"></div>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';

  const chartMetric = ref<'nav' | 'aum'>('nav');
  const chartPeriod = ref<'day' | 'week'>('day');
  const fxMode = ref<'realtime' | 'fixed'>('realtime');

  const overviewRows = [
    {
      name: '返佣宝',
      navCny: '3,470,761.9950',
      navUsd: '487,610.3900',
      marginCny: '3,192,514.3154',
      marginUsd: '448,519.1300',
      pnlCny: '354,478.1108',
      pnlUsd: '49,800.9400',
      emphasis: true,
    },
    {
      name: '测试',
      navCny: '3,255.2292',
      navUsd: '457.3300',
      marginCny: '3,221.2056',
      marginUsd: '452.5500',
      pnlCny: '3,262.4183',
      pnlUsd: '458.3400',
      emphasis: true,
    },
    {
      name: '黄金测试产品1号',
      navCny: '--',
      navUsd: '--',
      marginCny: '--',
      marginUsd: '--',
      pnlCny: '--',
      pnlUsd: '--',
      emphasis: true,
    },
  ];

  const accountRows = [
    {
      account: 'FYBfund01',
      exchange: 'bybit',
      nav: '450,437.9100 $',
      strategy: '资费套利',
      margin: '413,734.7400 $',
      unrealized: '126,314.3600 $',
      roe: '11.3900',
      dayPnl: '12.7300 $',
      totalPnl: '51,288.7600 $',
      updatedAt: '2025-11-12 16:13:04',
    },
    {
      account: 'FYBfund02',
      exchange: 'bybit',
      nav: '37,172.4800 $',
      strategy: '价差套利',
      margin: '34,784.3900 $',
      unrealized: '22,976.0700 $',
      roe: '-4.0000',
      dayPnl: '2.3800 $',
      totalPnl: '-1,487.8200 $',
      updatedAt: '2025-11-12 16:13:04',
    },
  ];

  const capitalKpis = [
    { label: '总资产AUM', value: '21,770,490.97', note: 'CNY' },
    { label: '累计收益', value: '20,797,885.19', note: 'CNY' },
    { label: '收益率', value: '95.53%', note: '策略净收益率' },
    {
      label: '总CNYUSD资产占比',
      split: [
        { name: 'CNY', value: '55.16%', note: '12,007,815.82' },
        { name: 'USD', value: '44.84%', note: '9,765,941.3' },
      ],
    },
  ];

  const allocationCards = [
    { label: '期货', value: '12,007,815.82 CNY', ratio: '55.16%' },
    { label: '海外', value: '9,765,941.3 CNY', ratio: '44.84%' },
  ];

  const capitalDates = [
    '2025-11-19 15:00:05',
    '2025-11-26 15:00:05',
    '2025-12-03 15:00:05',
    '2025-12-10 15:00:05',
    '2025-12-17 15:00:05',
    '2025-12-24 15:00:09',
    '2025-12-31 15:00:05',
    '2026-01-09 15:00:12',
    '2026-01-22 15:00:08',
    '2026-01-30 15:00:12',
    '2026-02-06 15:00:12',
  ];

  const navSeries = [0.993, 0.991, 0.989, 0.986, 0.983, 0.982, 1.011, 1.012, 1.008, 1.058, 1.022];
  const aumSeries = [2100, 2105, 2110, 2098, 2085, 2072, 2140, 2156, 2148, 2177, 2169];
  const ddSeries = [-1, -2, -4, -5, -6, -5.5, -1.2, -1.5, -8, -58, -34];

  const capitalCurveRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(capitalCurveRef as Ref<HTMLDivElement>);

  async function renderCurve() {
    const isNav = chartMetric.value === 'nav';
    await setOptions({
      tooltip: { trigger: 'axis' },
      legend: {
        top: 4,
        data: isNav ? ['净值', '回撤'] : ['AUM', '回撤'],
        textStyle: { color: '#667788' },
      },
      grid: { left: 24, right: 36, top: 44, bottom: 48, containLabel: true },
      xAxis: {
        type: 'category',
        data: capitalDates,
        boundaryGap: false,
        axisTick: { show: false },
        axisLabel: { color: '#94a0b1', hideOverlap: true },
      },
      yAxis: [
        {
          type: 'value',
          axisLabel: { color: '#94a0b1' },
          splitLine: { lineStyle: { color: 'rgba(148,163,184,.15)', type: 'dashed' } },
        },
        {
          type: 'value',
          position: 'right',
          axisLabel: { color: '#94a0b1', formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 20,
          bottom: 10,
          backgroundColor: 'rgba(226, 236, 250, .55)',
          fillerColor: 'rgba(175, 198, 247, .35)',
          brushSelect: false,
        },
      ],
      series: [
        {
          name: isNav ? '净值' : 'AUM',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2, color: '#e14d4d' },
          data: isNav ? navSeries : aumSeries,
        },
        {
          name: '回撤',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 0 },
          areaStyle: { color: 'rgba(244, 184, 97, .35)' },
          data: ddSeries,
        },
      ],
    });
    await nextTick();
    resize();
  }

  watch([chartMetric, chartPeriod, fxMode], renderCurve);
  onMounted(renderCurve);
</script>

<style scoped lang="less">
  .capital-stack {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .capital-card {
    padding: 20px 22px;
    border-radius: 24px;
    border: 1px solid rgba(201, 164, 95, 0.14);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 251, 244, 0.94));
    box-shadow: 0 18px 40px rgba(28, 35, 40, 0.05);
  }

  .capital-card--table {
    padding-top: 18px;
  }

  .eyebrow {
    margin: 0 0 6px;
    color: #a38a60;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
  }

  .capital-head h3 {
    margin: 0;
    color: #172033;
    font-size: 28px;
    font-weight: 800;
  }

  .capital-head--compact h3 {
    font-size: 20px;
  }

  .table-shell {
    overflow-x: auto;
  }

  .capital-table {
    width: 100%;
    min-width: 1120px;
    border-collapse: collapse;
  }

  .capital-table th,
  .capital-table td {
    padding: 13px 14px;
    border-bottom: 1px solid #eef2f7;
    white-space: nowrap;
    text-align: center;
  }

  .capital-table th {
    color: #8a97ab;
    font-size: 12px;
    font-weight: 700;
    background: #fcfcfd;
  }

  .capital-table td {
    color: #31425a;
    font-size: 13px;
    font-weight: 600;
  }

  .capital-table tbody tr:last-child td {
    border-bottom: none;
  }

  .is-name-emphasis {
    color: #d8585f !important;
    font-weight: 700 !important;
  }

  .is-positive {
    color: #19a767 !important;
  }

  .is-negative {
    color: #d8585f !important;
  }

  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .kpi-card,
  .allocation-card {
    padding: 16px 18px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.85);
    box-shadow: inset 0 0 0 1px rgba(201, 164, 95, 0.08);
  }

  .kpi-card label,
  .allocation-card label {
    display: block;
    color: #8b95a4;
    font-size: 13px;
    font-weight: 600;
  }

  .kpi-card strong,
  .allocation-card strong {
    display: block;
    margin: 10px 0 6px;
    color: #df5858;
    font-size: 34px;
    font-weight: 800;
    line-height: 1.12;
  }

  .kpi-card p,
  .allocation-card p {
    margin: 0;
    color: #7d8899;
    font-size: 12px;
    font-weight: 600;
  }

  .split-block {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    margin-top: 12px;
  }

  .split-block span {
    display: block;
    color: #df5858;
    font-size: 13px;
    font-weight: 700;
  }

  .split-block strong {
    margin: 6px 0 4px;
    color: #1f2c40;
    font-size: 24px;
  }

  .split-block em {
    color: #7d8899;
    font-size: 12px;
    font-style: normal;
    font-weight: 600;
  }

  .allocation-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-top: 14px;
  }

  .chart-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 12px;
  }

  .chart-head h4 {
    margin: 0;
    color: #cf4d4d;
    font-size: 26px;
    font-weight: 800;
  }

  .chart-head p {
    margin: 8px 0 0;
    color: #1f2c40;
    font-size: 24px;
    font-weight: 800;
  }

  .chart-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .chart-controls select,
  .pill-btn {
    height: 36px;
    padding: 0 14px;
    border: 1px solid #e5dccb;
    border-radius: 10px;
    background: #fff;
    color: #4d5768;
    font-size: 13px;
    font-weight: 600;
  }

  .pill-btn {
    cursor: pointer;
  }

  .pill-btn.is-active {
    border-color: #d8585f;
    background: #d8585f;
    color: #fff;
  }

  .capital-chart {
    height: 420px;
  }

  .capital-stack,
  .capital-card,
  .kpi-card,
  .allocation-card {
    color: var(--strategy-text-1);
  }

  .capital-card,
  .kpi-card,
  .allocation-card {
    border-color: var(--strategy-border);
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
  }

  .chart-controls select,
  .pill-btn {
    border-color: var(--strategy-border);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
  }

  .pill-btn.is-active {
    border-color: rgba(201, 72, 72, 0.18);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  @media (max-width: 1320px) {
    .kpi-grid,
    .allocation-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
