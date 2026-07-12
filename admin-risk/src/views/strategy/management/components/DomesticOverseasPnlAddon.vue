<template>
  <section class="addon-stack">
    <article class="addon-card risk-card">
      <header class="risk-card__header">
        <div>
          <p class="eyebrow">Offshore Spread Risk</p>
          <h3>海内外价差风险总览</h3>
        </div>

        <div class="risk-levels">
          <span
            v-for="level in riskLevels"
            :key="level.label"
            class="risk-level"
          >
            <i :style="{ background: level.color }"></i>
            {{ level.label }}
          </span>
        </div>
      </header>

      <div class="summary-table">
        <div class="summary-row summary-row--head">
          <span v-for="item in summaryHead" :key="item">{{ item }}</span>
        </div>
        <div class="summary-row summary-row--body">
          <span>{{ activeRisk.product }}</span>
          <span>{{ activeRisk.type }}</span>
          <span class="tone-link">{{ activeRisk.level }}</span>
          <span>{{ activeRisk.factor }}</span>
          <span>{{ activeRisk.firstTrigger }}</span>
          <span>{{ activeRisk.latestTrigger }}</span>
          <span>{{ activeRisk.latestTime }}</span>
          <span>{{ activeRisk.count }}</span>
          <span class="summary-actions">
            <button type="button" class="link-btn is-success">处理完成</button>
            <button type="button" class="link-btn">忽略</button>
          </span>
        </div>
      </div>

      <div class="tab-row">
        <button
          v-for="item in riskTabs"
          :key="item.key"
          type="button"
          class="tab-btn"
          :class="{ 'is-active': activeRiskTab === item.key }"
          @click="activeRiskTab = item.key"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="risk-body">
        <div class="risk-meta">
          <h4>{{ activeRisk.name }}</h4>
          <div class="risk-stats">
            <article v-for="item in riskMetrics" :key="item.label" class="metric-chip">
              <label>{{ item.label }}</label>
              <strong :class="item.tone ? `is-${item.tone}` : ''">{{ item.value }}</strong>
            </article>
          </div>
        </div>

        <div class="risk-split">
          <article class="account-panel">
            <header>
              <h5>境内账户</h5>
              <span>{{ activeRisk.updatedAt }}</span>
            </header>
            <div class="mini-bars">
              <span class="bar is-primary"></span>
              <span class="bar is-primary"></span>
              <span class="bar"></span>
              <span class="bar"></span>
            </div>
            <div class="account-grid">
              <div v-for="item in activeRisk.onshore" :key="item.label">
                <label>{{ item.label }}</label>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </article>

          <article class="account-panel">
            <header>
              <h5>海外账户</h5>
              <span>{{ activeRisk.updatedAt }}</span>
            </header>
            <div class="mini-bars">
              <span class="bar is-primary"></span>
              <span class="bar is-primary"></span>
              <span class="bar"></span>
              <span class="bar"></span>
            </div>
            <div class="account-grid">
              <div v-for="item in activeRisk.offshore" :key="item.label">
                <label>{{ item.label }}</label>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </article>
        </div>
      </div>
    </article>

    <article class="addon-card chart-card">
      <header class="section-head">
        <div>
          <p class="eyebrow">Pnl Curve</p>
          <h3>净值曲线</h3>
        </div>

        <div class="head-controls">
          <select v-model="curveMetric">
            <option value="nav">产品净值</option>
            <option value="pnl">累计收益</option>
          </select>
          <select v-model="curvePeriod">
            <option value="day">天</option>
            <option value="week">周</option>
          </select>
          <button
            type="button"
            class="ghost-btn"
            :class="{ 'is-active': fxMode === 'realtime' }"
            @click="fxMode = 'realtime'"
          >
            实时汇率
          </button>
          <button
            type="button"
            class="ghost-btn"
            :class="{ 'is-active': fxMode === 'fixed' }"
            @click="fxMode = 'fixed'"
          >
            固定汇率
          </button>
        </div>
      </header>

      <div ref="curveRef" class="chart-stage chart-stage--large"></div>

      <div class="curve-grid">
        <article class="mini-chart-card">
          <h4>波动率</h4>
          <div ref="volRef" class="chart-stage chart-stage--small"></div>
        </article>

        <article class="mini-chart-card">
          <h4>夏普比率</h4>
          <div ref="sharpeRef" class="chart-stage chart-stage--small"></div>
        </article>
      </div>
    </article>

    <article class="addon-card">
      <header class="section-head">
        <div>
          <p class="eyebrow">Position Scale</p>
          <h3>仓位规模</h3>
        </div>
      </header>

      <div class="position-table">
        <table>
          <thead>
            <tr>
              <th>平台</th>
              <th>账户</th>
              <th>标的名称</th>
              <th>标的类型</th>
              <th>持仓量</th>
              <th>持仓均价</th>
              <th>强平价</th>
              <th>克重</th>
              <th>仓位价值 (CNY)</th>
              <th>持仓方向</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in positionRows" :key="item.symbol">
              <td>{{ item.platform }}</td>
              <td>{{ item.account }}</td>
              <td>{{ item.symbol }}</td>
              <td>{{ item.kind }}</td>
              <td>{{ item.position }}</td>
              <td>{{ item.entry }}</td>
              <td>{{ item.liq }}</td>
              <td>{{ item.weight }}</td>
              <td>{{ item.value }}</td>
              <td :class="item.side === '买入' ? 'tone-positive' : 'tone-negative'">{{ item.side }}</td>
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

  const activeRiskTab = ref<'overview' | 'action' | 'config'>('overview');
  const curveMetric = ref<'nav' | 'pnl'>('nav');
  const curvePeriod = ref<'day' | 'week'>('day');
  const fxMode = ref<'realtime' | 'fixed'>('realtime');

  const riskLevels = [
    { label: '一级风险', color: '#36b37e' },
    { label: '二级风险', color: '#4f8ff7' },
    { label: '三级风险', color: '#f4b740' },
    { label: '四级风险', color: '#f0805a' },
    { label: '五级风险', color: '#e45858' },
  ];

  const summaryHead = [
    '产品/账户',
    '类型',
    '触发风险等级',
    '风险因子',
    '最初触发数据',
    '最新触发数据',
    '最新触发时间',
    '触发次数',
    '操作',
  ];

  const riskTabs = [
    { key: 'overview', label: '信息概览' },
    { key: 'action', label: '风险处理' },
    { key: 'config', label: '风险分级配置' },
  ] as const;

  const riskPanels = {
    overview: {
      product: '黄金测试产品1号/live_trading',
      type: '账户',
      level: '二级风险',
      factor: 'marginLevel',
      firstTrigger: '10633.14',
      latestTrigger: '10605.7',
      latestTime: '2025-12-12 17:54:00',
      count: '3',
      name: '黄金测试产品1号',
      updatedAt: '2025-12-15 16:27',
      onshore: [
        { label: '资金使用率', value: '42.88%' },
        { label: '权益 (CNY)', value: '1,071,429.68' },
        { label: '可用资金 (CNY)', value: '566,467.28' },
        { label: '杠杆率', value: '287.03%' },
      ],
      offshore: [
        { label: '预付款维持率', value: '10246.82%' },
        { label: '净值 (USD)', value: '81,396.61' },
        { label: '可用预付款 (USD)', value: '80,602.25' },
        { label: '杠杆率', value: '512.32%' },
      ],
    },
    action: {
      product: '黄金测试产品1号/live_trading',
      type: '账户',
      level: '三级风险',
      factor: 'drawdown',
      firstTrigger: '-3.65%',
      latestTrigger: '-4.12%',
      latestTime: '2025-12-12 17:58:00',
      count: '2',
      name: '风险处理状态',
      updatedAt: '2025-12-15 16:35',
      onshore: [
        { label: '待复核告警', value: '2 条' },
        { label: '已降杠杆', value: '是' },
        { label: '保护止损', value: '已启用' },
        { label: '处理人', value: 'Admin' },
      ],
      offshore: [
        { label: '对冲腿偏离', value: '34.88%' },
        { label: '期货腿偏离', value: '65.12%' },
        { label: '目标保证金', value: '9,000 USD' },
        { label: '当前风控', value: '二级' },
      ],
    },
    config: {
      product: '黄金测试产品1号/live_trading',
      type: '规则',
      level: '二级风险',
      factor: 'marginLevel',
      firstTrigger: '10500',
      latestTrigger: '10605.7',
      latestTime: '2025-12-12 18:05:00',
      count: '1',
      name: '风险分级配置',
      updatedAt: '2025-12-15 16:42',
      onshore: [
        { label: '一级阈值', value: '> 12000' },
        { label: '二级阈值', value: '10500 - 12000' },
        { label: '三级阈值', value: '9500 - 10500' },
        { label: '更新频率', value: '5 分钟' },
      ],
      offshore: [
        { label: '跨市场偏离阈值', value: '35%' },
        { label: '回撤警戒线', value: '-5%' },
        { label: '杠杆上限', value: '5.5x' },
        { label: '自动处理', value: '开启' },
      ],
    },
  };

  const activeRisk = computed(() => riskPanels[activeRiskTab.value]);

  const riskMetrics = computed(() => [
    { label: '产品净值回撤', value: '-4.12%', tone: 'negative' },
    { label: '总杠杆率', value: '367.55%' },
    { label: '中性平衡', value: '多50.12% / 空49.88%', tone: 'positive' },
    { label: '海外/期货', value: '海外34.88% / 期货65.12%' },
  ]);

  const curveDates = [
    '2025-11-17 15:00:05',
    '2025-11-20 15:00:06',
    '2025-11-25 15:00:06',
    '2025-11-28 15:00:06',
    '2025-12-03 15:00:06',
    '2025-12-08 15:00:06',
    '2025-12-11 15:05:05',
    '2025-12-15 15:05:05',
    '2025-12-22 15:00:09',
    '2025-12-31 15:00:05',
    '2026-01-09 15:00:12',
    '2026-01-22 15:00:08',
    '2026-01-30 15:00:12',
  ];

  const navData = [0.998, 1.008, 1.012, 0.985, 1.011, 0.982, 0.979, 0.986, 0.974, 0.983, 0.986, 0.962, 0.961];
  const pnlData = [2, 5, 8, 1, 11, -3, -5, 4, -7, 13, 13, 11, 26];
  const drawdownData = [-1, -0.5, -1.2, -2.8, -3.1, -2.2, -2.5, -3.9, -2.7, -1.5, -1.8, -5.6, -4.3];
  const volData = [0.4, 0.5, 0.2, 0.3, 0.6, 0.8, 0.7, 0.5, 0.4, 32.4, 30.8, 29.2, 27.6];
  const sharpeData = [-1, -0.5, 0.2, 0.1, 0, 0.3, 1.1, 0.8, 0.2, 0.1, 64, 0.2, 3.8];

  const positionRows = [
    {
      platform: '期货',
      account: 'live_trading',
      symbol: 'SHFE.au2606',
      kind: '期货',
      position: '3.0000',
      entry: '959.09',
      liq: '755.40',
      weight: '3,000.0000',
      value: '2,961,480.00',
      side: '买入',
    },
    {
      platform: '海外',
      account: 'live_trading',
      symbol: 'XAUUSD+',
      kind: '期货',
      position: '0.9600',
      entry: '4,137.68',
      liq: '4,981.37',
      weight: '2,985.9338',
      value: '2,940,395.83',
      side: '卖出',
    },
  ];

  const curveRef = ref<HTMLDivElement | null>(null);
  const volRef = ref<HTMLDivElement | null>(null);
  const sharpeRef = ref<HTMLDivElement | null>(null);

  const { setOptions: setCurveOptions, resize: resizeCurve } = useECharts(curveRef as Ref<HTMLDivElement>);
  const { setOptions: setVolOptions, resize: resizeVol } = useECharts(volRef as Ref<HTMLDivElement>);
  const { setOptions: setSharpeOptions, resize: resizeSharpe } = useECharts(sharpeRef as Ref<HTMLDivElement>);

  async function renderCurveChart() {
    const isNav = curveMetric.value === 'nav';
    await setCurveOptions({
      tooltip: { trigger: 'axis' },
      legend: {
        top: 6,
        itemWidth: 12,
        textStyle: { color: '#58677c' },
        data: isNav ? ['净值', '回撤'] : ['累计收益', '回撤'],
      },
      grid: { left: 28, right: 32, top: 44, bottom: 52, containLabel: true },
      xAxis: {
        type: 'category',
        data: curveDates,
        boundaryGap: false,
        axisLabel: { color: '#8d98a8', hideOverlap: true },
        axisTick: { show: false },
      },
      yAxis: [
        {
          type: 'value',
          axisLabel: { color: '#8d98a8' },
          splitLine: { lineStyle: { color: 'rgba(148,163,184,.15)', type: 'dashed' } },
        },
        {
          type: 'value',
          position: 'right',
          axisLabel: { color: '#8d98a8', formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 22,
          bottom: 10,
          borderColor: 'rgba(199, 212, 230, .8)',
          brushSelect: false,
          backgroundColor: 'rgba(226, 236, 250, .55)',
          fillerColor: 'rgba(175, 198, 247, .35)',
        },
      ],
      series: [
        {
          name: isNav ? '净值' : '累计收益',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2, color: '#e14d4d' },
          data: isNav ? navData : pnlData,
          markPoint: isNav
            ? {
                symbol: 'circle',
                symbolSize: 8,
                label: { color: '#11b36c' },
                data: [
                  { name: '最低点', coord: [curveDates[8], 0.974], value: 'min:0.9506' },
                  { name: '高点', coord: [curveDates[12], 0.961], value: 'max:58.0201' },
                ],
              }
            : undefined,
        },
        {
          name: '回撤',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 0 },
          areaStyle: { color: 'rgba(244, 184, 97, .35)' },
          data: drawdownData,
        },
      ],
    });
    await nextTick();
    resizeCurve();
  }

  async function renderMiniCharts() {
    await setVolOptions({
      tooltip: { trigger: 'axis' },
      grid: { left: 24, right: 14, top: 16, bottom: 28, containLabel: true },
      xAxis: {
        type: 'category',
        data: curveDates,
        boundaryGap: false,
        axisTick: { show: false },
        axisLabel: { color: '#9aa3b2', hideOverlap: true },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#9aa3b2' },
        splitLine: { lineStyle: { color: 'rgba(148,163,184,.15)', type: 'dashed' } },
      },
      series: [{ type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#d65050', width: 2.5 }, data: volData }],
    });

    await setSharpeOptions({
      tooltip: { trigger: 'axis' },
      grid: { left: 24, right: 14, top: 16, bottom: 28, containLabel: true },
      xAxis: {
        type: 'category',
        data: curveDates,
        boundaryGap: false,
        axisTick: { show: false },
        axisLabel: { color: '#9aa3b2', hideOverlap: true },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#9aa3b2' },
        splitLine: { lineStyle: { color: 'rgba(148,163,184,.15)', type: 'dashed' } },
      },
      series: [{ type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#d65050', width: 2.5 }, data: sharpeData }],
    });

    await nextTick();
    resizeVol();
    resizeSharpe();
  }

  watch([curveMetric, curvePeriod, fxMode], renderCurveChart);
  onMounted(async () => {
    await renderCurveChart();
    await renderMiniCharts();
  });
</script>

<style scoped lang="less">
  .addon-stack {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .addon-card {
    padding: 20px 22px;
    border-radius: 24px;
    border: 1px solid rgba(201, 164, 95, 0.14);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 251, 244, 0.94));
    box-shadow: 0 18px 40px rgba(28, 35, 40, 0.05);
  }

  .eyebrow {
    display: none;
  }

  .section-head,
  .risk-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;
  }

  .section-head h3,
  .risk-card__header h3 {
    margin: 0;
    color: #172033;
    font-size: 28px;
    font-weight: 800;
  }

  .risk-levels {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;
    padding-top: 10px;
  }

  .risk-level {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #7f8a99;
    font-size: 12px;
  }

  .risk-level i {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .summary-table {
    overflow: hidden;
    border-radius: 18px;
    border: 1px solid rgba(231, 201, 146, 0.55);
    background: #fbfbf9;
  }

  .summary-row {
    display: grid;
    grid-template-columns: 2.3fr 0.8fr 1fr 1fr 1fr 1fr 1.2fr 0.7fr 1fr;
  }

  .summary-row span {
    padding: 14px 12px;
    border-right: 1px solid rgba(240, 218, 177, 0.55);
    color: #5f6675;
    font-size: 13px;
  }

  .summary-row span:last-child {
    border-right: none;
  }

  .summary-row--head {
    background: rgba(255, 229, 180, 0.48);
  }

  .summary-row--head span {
    color: #92774d;
    font-size: 12px;
    font-weight: 700;
  }

  .summary-row--body span {
    color: #20293d;
    font-weight: 600;
  }

  .tone-link {
    color: #4f8ff7 !important;
  }

  .summary-actions {
    display: inline-flex;
    align-items: center;
    gap: 10px;
  }

  .link-btn {
    border: none;
    background: transparent;
    color: #98a2b3;
    font-size: 13px;
    cursor: pointer;
  }

  .link-btn.is-success {
    color: #23a36b;
  }

  .tab-row {
    display: flex;
    gap: 18px;
    padding: 16px 0 10px;
    border-bottom: 1px solid rgba(228, 233, 241, 0.9);
  }

  .tab-btn {
    border: none;
    background: transparent;
    color: #707987;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  .tab-btn.is-active {
    color: #d25a5a;
  }

  .risk-body {
    padding-top: 18px;
  }

  .risk-meta h4 {
    margin: 0 0 14px;
    color: #273145;
    font-size: 24px;
    font-weight: 800;
  }

  .risk-stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 18px;
  }

  .metric-chip {
    min-height: 96px;
    padding: 16px 18px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: inset 0 0 0 1px rgba(201, 164, 95, 0.1);
  }

  .metric-chip label,
  .account-grid label {
    display: block;
    margin-bottom: 8px;
    color: #8b95a4;
    font-size: 13px;
    font-weight: 600;
  }

  .metric-chip strong,
  .account-grid strong {
    color: #1f2c40;
    font-size: 28px;
    font-weight: 800;
    line-height: 1.15;
  }

  .metric-chip strong.is-negative {
    color: #d8585f;
  }

  .metric-chip strong.is-positive {
    color: #1b9a64;
  }

  .risk-split {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .account-panel {
    padding: 18px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.82);
    box-shadow: inset 0 0 0 1px rgba(201, 164, 95, 0.08);
  }

  .account-panel header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  .account-panel h5 {
    margin: 0;
    color: #243249;
    font-size: 20px;
    font-weight: 800;
  }

  .account-panel header span {
    color: #8b95a4;
    font-size: 12px;
  }

  .mini-bars {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 16px;
  }

  .bar {
    height: 3px;
    border-radius: 999px;
    background: rgba(220, 226, 236, 0.9);
  }

  .bar.is-primary {
    background: #53a5f7;
  }

  .account-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
  }

  .head-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .head-controls select,
  .ghost-btn {
    height: 36px;
    padding: 0 14px;
    border: 1px solid #e5dccb;
    border-radius: 10px;
    background: #fff;
    color: #4d5768;
    font-size: 13px;
    font-weight: 600;
  }

  .ghost-btn {
    cursor: pointer;
  }

  .ghost-btn.is-active {
    border-color: #d8585f;
    background: #d8585f;
    color: #fff;
  }

  .chart-stage--large {
    height: 420px;
  }

  .curve-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    margin-top: 12px;
  }

  .mini-chart-card {
    padding: 14px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.78);
    box-shadow: inset 0 0 0 1px rgba(201, 164, 95, 0.08);
  }

  .mini-chart-card h4 {
    margin: 0 0 10px;
    color: #1d2a3f;
    font-size: 18px;
    font-weight: 800;
  }

  .chart-stage--small {
    height: 260px;
  }

  .position-table {
    overflow-x: auto;
  }

  .position-table table {
    width: 100%;
    min-width: 1200px;
    border-collapse: collapse;
  }

  .position-table th,
  .position-table td {
    padding: 14px 12px;
    border-bottom: 1px solid #eef2f7;
    white-space: nowrap;
    text-align: left;
  }

  .position-table th {
    color: #8a97ab;
    font-size: 12px;
    font-weight: 700;
  }

  .position-table td {
    color: #33435a;
    font-size: 13px;
    font-weight: 600;
  }

  .tone-positive {
    color: #19a767 !important;
  }

  .tone-negative {
    color: #d8585f !important;
  }

  .addon-stack,
  .addon-card,
  .curve-card,
  .risk-card,
  .position-card {
    color: var(--strategy-text-1);
  }

  .addon-card,
  .curve-card,
  .position-card {
    border-color: var(--strategy-border);
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
  }

  .subtab,
  .curve-toolbar select,
  .curve-toolbar button {
    border-color: var(--strategy-border);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
  }

  .subtab.is-active,
  .curve-toolbar .is-active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  @media (max-width: 1320px) {
    .summary-row,
    .risk-stats,
    .risk-split,
    .curve-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
