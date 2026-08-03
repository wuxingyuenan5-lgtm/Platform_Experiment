<template>
  <section class="funding-exec-shell">
    <header class="funding-exec-topbar">
      <div class="topbar-title">
        <div class="selector-chip">
          <span>标的</span>
          <strong>{{ data.strategyLabel }}</strong>
        </div>
      </div>
    </header>

    <div class="funding-upper-grid">
      <section class="panel quote-panel">
        <div class="panel-title">
          <h3>资金费率行情</h3>
        </div>

        <div class="exchange-grid">
          <article v-for="item in exchangeCards" :key="item.name" class="exchange-card">
            <div class="exchange-card__head">
              <div class="exchange-brand">
                <span class="exchange-logo">{{ item.mark }}</span>
                <strong>{{ item.name }}</strong>
              </div>
              <span class="status-pill"><i></i>在线</span>
            </div>

            <div class="exchange-stats">
              <div
                ><span>最新价格</span><strong>{{ item.price }}</strong></div
              >
              <div
                ><span>资金费率</span><strong class="green">{{ item.rate }}</strong></div
              >
              <div
                ><span>预期年化</span><strong class="green">{{ item.apr }}</strong></div
              >
              <div
                ><span>下次结算</span><strong>{{ item.window }}</strong></div
              >
              <div
                ><span>标记价格</span><strong>{{ item.markPrice }}</strong></div
              >
              <div
                ><span>24H成交量</span><strong>{{ item.volume }}</strong></div
              >
              <div
                ><span>持仓量</span><strong>{{ item.oi }}</strong></div
              >
            </div>
          </article>
        </div>
      </section>

      <section class="panel opportunity-panel">
        <div class="panel-title">
          <h3>资金费率机会</h3>
        </div>

        <div class="opportunity-value">+0.0810%</div>
        <div class="opportunity-meta">
          <div><span>交易所</span><strong>Binance</strong></div>
          <div><span>套利方向</span><strong class="red">现货买入 + 永续卖出</strong></div>
          <div><span>现货-永续价差</span><strong class="green">+10.5 USDT (+0.0102%)</strong></div>
          <div><span>预估年化收益率</span><strong class="green">+29.57%</strong></div>
          <div><span>预估综合净收益率</span><strong class="green">+22.31%</strong></div>
          <div><span>机会质量</span><strong class="green">高质量</strong></div>
        </div>
      </section>

      <section class="panel trend-panel">
        <div class="panel-title panel-title--between">
          <h3>资金费率走势 (Binance)</h3>
          <div class="range-tabs">
            <button
              v-for="item in chartRanges"
              :key="item"
              type="button"
              :class="{ active: item === activeChartRange }"
              @click="activeChartRange = item"
            >
              {{ item }}
            </button>
          </div>
        </div>

        <div class="trend-chart-shell">
          <div ref="chartRef" class="trend-chart"></div>
        </div>
      </section>
    </div>

    <div class="funding-lower-grid">
      <FundingStatusPanel
        :trading-rules="tradingRuleRows"
        :feedback-rows="executionFeedback"
        @clear="executionFeedback = []"
      />

      <FundingExecutionPanel
        v-model:funding-execution-stage="fundingExecutionStage"
        v-model:funding-open-direction="fundingOpenDirection"
        v-model:funding-open-mode="fundingOpenMode"
        v-model:funding-close-mode="fundingCloseMode"
        v-model:selected-symbol="selectedSymbol"
        v-model:selected-venue="selectedVenue"
        v-model:notional-value="notionalValue"
        v-model:selected-leverage="selectedLeverage"
        v-model:funding-hedge-leverage="fundingHedgeLeverage"
        v-model:order-qty="orderQty"
        v-model:stop-spread="stopSpread"
        v-model:funding-threshold="fundingThreshold"
        v-model:funding-entry-basis="fundingEntryBasis"
        v-model:funding-take-profit="fundingTakeProfit"
        v-model:funding-close-basis="fundingCloseBasis"
        :funding-legs="fundingLegs"
        :funding-close-rows="fundingCloseRows"
        @submit-order="submitFundingOrder"
        @submit-close="submitFundingClose"
      />

      <section class="panel history-panel">
        <div class="panel-title panel-title--between">
          <h3>资金费率历史分析</h3>
          <div class="range-tabs">
            <button
              v-for="item in historyRanges"
              :key="item"
              type="button"
              :class="{ active: item === activeHistoryRange }"
              @click="activeHistoryRange = item"
            >
              {{ item }}
            </button>
          </div>
        </div>

        <table class="analysis-table">
          <thead>
            <tr>
              <th>指标</th>
              <th>资金费率</th>
              <th>现货-永续基差</th>
              <th>说明 / 状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in historyRows" :key="row.label">
              <td>{{ row.label }}</td>
              <td :class="row.rate.startsWith('-') ? 'red' : 'green'">{{ row.rate }}</td>
              <td :class="row.basis.startsWith('-') ? 'red' : 'green'">{{ row.basis }}</td>
              <td
                :class="row.state.includes('高') ? 'green' : row.state.includes('低') ? 'red' : ''"
                >{{ row.state }}</td
              >
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <FundingPositionsPanel />
  </section>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, ref, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import FundingExecutionPanel from './FundingExecutionPanel.vue';
  import FundingPositionsPanel from './FundingPositionsPanel.vue';
  import FundingStatusPanel from './FundingStatusPanel.vue';
  import type { FundingOrderPanelData } from '../types';

  defineProps<{ data: FundingOrderPanelData }>();

  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>);

  const chartRanges = ['1h', '4h', '1D', '7D', '30D'];
  const historyRanges = ['1D', '7D', '30D', '90D'];

  const activeChartRange = ref('1D');
  const activeHistoryRange = ref('30D');
  const fundingExecutionStage = ref<'open' | 'close'>('open');
  const fundingOpenDirection = ref<'collect' | 'pay'>('collect');
  const fundingOpenMode = ref<'market' | 'limit'>('market');
  const fundingCloseMode = ref<'market' | 'limit'>('market');

  const selectedSymbol = ref('BTCUSDT');
  const selectedVenue = ref('Binance');
  const notionalValue = ref('100,000.00');
  const selectedLeverage = ref('2x');
  const fundingHedgeLeverage = ref('2x');
  const orderQty = ref('0.9791');
  const stopSpread = ref('-25.0');
  const fundingThreshold = ref('0.0500');
  const fundingEntryBasis = ref('20.0');
  const fundingTakeProfit = ref('2.0');
  const fundingCloseBasis = ref('4.0');
  const tradingRuleRows = [
    { label: '手续费', value: '—' },
    { label: '交易时间', value: '24H' },
    { label: '个人最高杠杆', value: '—' },
    { label: '每日最大回撤', value: '—' },
    { label: '其他限制', value: '—' },
  ] as const;

  const exchangeCards = [
    {
      name: 'Binance',
      mark: '◆',
      price: '102,350.0 USDT',
      rate: '+0.0810%',
      apr: '+29.57%',
      window: '03:21:45',
      markPrice: '102,360.5 USDT',
      volume: '28,765.32 BTC',
      oi: '136,245.67 BTC',
    },
    {
      name: 'Bybit',
      mark: '●',
      price: '102,348.5 USDT',
      rate: '+0.0750%',
      apr: '+27.38%',
      window: '03:21:45',
      markPrice: '102,359.0 USDT',
      volume: '19,842.11 BTC',
      oi: '98,732.45 BTC',
    },
    {
      name: 'OKX',
      mark: '✦',
      price: '102,341.2 USDT',
      rate: '+0.0680%',
      apr: '+24.82%',
      window: '03:21:45',
      markPrice: '102,351.3 USDT',
      volume: '15,673.88 BTC',
      oi: '87,654.21 BTC',
    },
  ];

  const historyRows = [
    { label: '90%分位', rate: '+0.1200%', basis: '+0.0280%', state: '极端高位' },
    { label: '75%分位', rate: '+0.0800%', basis: '+0.0150%', state: '偏高' },
    { label: '50%分位 (中位数)', rate: '+0.0300%', basis: '+0.0030%', state: '中性' },
    { label: '25%分位', rate: '+0.0100%', basis: '-0.0080%', state: '偏低' },
    { label: '10%分位', rate: '-0.0200%', basis: '-0.0200%', state: '极端低位' },
    { label: '当前值', rate: '+0.0810%', basis: '+0.0102%', state: '处于偏高区间' },
  ];

  interface FundingCloseRow {
    id: string;
    name: string;
    spot: string;
    perp: string;
    rate: string;
    basis: string;
    pnl: string;
    status: string;
  }

  const fundingCloseRows = ref<FundingCloseRow[]>([
    {
      id: 'carry-1',
      name: '资金费组合 #1',
      spot: '买入 0.5000 BTC',
      perp: '卖出 0.5000 BTC',
      rate: '+0.0810%',
      basis: '+10.5 USDT',
      pnl: '+349.80 USDT',
      status: '正常',
    },
    {
      id: 'carry-2',
      name: '资金费组合 #2',
      spot: '买入 0.4791 BTC',
      perp: '卖出 0.4791 BTC',
      rate: '+0.0680%',
      basis: '+8.4 USDT',
      pnl: '+221.70 USDT',
      status: '正常',
    },
  ]);

  type ExecutionFeedbackRow = {
    id: string;
    tone: 'is-success' | 'is-info';
    time: string;
    text: string;
  };

  const executionFeedback = ref<ExecutionFeedbackRow[]>([
    {
      id: 'feedback-1',
      tone: 'is-success',
      time: '2026-03-18 15:44:45',
      text: '正套开仓成功，现货腿与永续腿已同步成交。',
    },
    {
      id: 'feedback-2',
      tone: 'is-success',
      time: '2026-03-18 15:44:45',
      text: '对冲腿下单完成，成交均价与预估偏差可控。',
    },
    {
      id: 'feedback-3',
      tone: 'is-success',
      time: '2026-03-18 15:44:43',
      text: '执行引擎已完成风控校验，保证金占用正常。',
    },
    {
      id: 'feedback-4',
      tone: 'is-info',
      time: '2026-03-18 15:44:42',
      text: '已发起套利执行请求，等待交易所返回最终回报。',
    },
  ]);

  const fundingLegs = computed(() => {
    const qty = Number(orderQty.value || 0).toFixed(4);
    return {
      spot: `${qty} BTC`,
      perp: `${qty} BTC`,
    };
  });

  function createFeedbackId() {
    return `feedback-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  }

  function pushExecutionFeedback(text: string, tone: 'is-success' | 'is-info' = 'is-success') {
    executionFeedback.value.unshift({
      id: createFeedbackId(),
      tone,
      time: new Date().toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-'),
      text,
    });
    executionFeedback.value = executionFeedback.value.slice(0, 8);
  }

  function submitFundingOrder(direction: 'collect' | 'pay') {
    fundingOpenDirection.value = direction;
    const sideLabel = direction === 'collect' ? '正套' : '反套';
    pushExecutionFeedback(
      `${sideLabel}开仓已提交，${selectedVenue.value} ${selectedSymbol.value} 名义本金 ${notionalValue.value} USDT。`,
    );
  }

  function submitFundingClose(row: (typeof fundingCloseRows.value)[number]) {
    pushExecutionFeedback(
      `${row.name} 已发起${fundingCloseMode.value === 'market' ? '市价' : '限价'}平仓。`,
      'is-info',
    );
  }

  async function renderChart() {
    await chart.setOptions({
      animation: false,
      grid: { left: 46, right: 18, top: 18, bottom: 26 },
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { color: '#8b95a7', fontSize: 11 },
        data: ['05-19 00:00', '05-19 06:00', '05-19 12:00', '05-19 18:00', '05-20 00:00'],
      },
      yAxis: {
        type: 'value',
        min: -0.1,
        max: 0.15,
        axisLabel: {
          color: '#8b95a7',
          fontSize: 11,
          formatter: (value: number) => `${value.toFixed(2)}%`,
        },
        splitLine: { lineStyle: { color: '#edf2f7' } },
      },
      series: [
        {
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { color: '#ff4d4f', width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(255,77,79,0.24)' },
                { offset: 1, color: 'rgba(255,77,79,0.02)' },
              ],
            },
          },
          data: [0.0, 0.05, -0.03, 0.09, 0.081],
        },
      ],
    });
    await nextTick();
    chart.resize();
  }

  onMounted(renderChart);
</script>

<style scoped lang="less">
  .funding-exec-shell {
    display: flex;
    flex-direction: column;
    gap: 12px;
    color: #1f2937;
    background: #f8fafc;
    font-family: var(--strategy-font-sans);
  }

  .funding-exec-topbar,
  .topbar-title,
  .topbar-controls,
  .panel-title,
  .panel-title--between,
  .exchange-card__head,
  .exchange-brand,
  .yield-item {
    display: flex;
    align-items: center;
  }

  .funding-exec-topbar,
  .panel-title--between,
  .exchange-card__head {
    justify-content: space-between;
  }

  .funding-exec-topbar {
    gap: 16px;
    padding: 4px 2px 0;
  }

  .topbar-title,
  .topbar-controls {
    gap: 12px;
  }

  .topbar-title h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 800;
    color: #111827;
  }

  .run-pill {
    padding: 8px 14px;
    border: 1px solid rgba(34, 197, 94, 0.18);
    border-radius: 12px;
    background: #eefbf3;
    color: #16a34a;
    font-size: 13px;
    font-weight: 700;
  }

  .selector-chip,
  .latency-chip,
  .gear-btn {
    min-height: 42px;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #fff;
  }

  .selector-chip {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 0 14px;
  }

  .selector-chip span,
  .latency-chip {
    color: #556274;
    font-size: 14px;
    font-weight: 600;
  }

  .selector-chip strong {
    color: #111827;
    font-size: 15px;
    font-weight: 700;
  }

  .latency-chip {
    display: inline-flex;
    align-items: center;
    padding: 0 14px;
  }

  .gear-btn {
    width: 42px;
    cursor: pointer;
    font-size: 16px;
  }

  .funding-upper-grid {
    display: grid;
    grid-template-columns: 1.58fr 0.74fr 1.18fr;
    gap: 12px;
  }

  .funding-lower-grid {
    display: grid;
    grid-template-columns: 0.56fr 1.48fr 0.96fr;
    gap: 12px;
    align-items: stretch;
  }

  .panel {
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    padding: 16px 18px 18px;
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
  }

  .panel-title {
    margin-bottom: 12px;
  }

  .panel-title h3 {
    margin: 0;
    color: #12243f;
    font-size: 16px;
    font-weight: 900;
  }

  .history-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .exchange-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .exchange-card {
    display: flex;
    flex-direction: column;
    min-height: 230px;
    border: 1px solid #edf2f7;
    border-radius: 14px;
    padding: 16px 14px 14px;
  }

  .exchange-brand {
    gap: 10px;
  }

  .exchange-logo {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #f3f4f6;
    color: #111827;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 800;
  }

  .exchange-brand strong {
    font-size: 18px;
    color: #111827;
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #16a34a;
    font-size: 12px;
    font-weight: 700;
  }

  .status-pill i {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #16a34a;
  }

  .exchange-stats {
    flex: 1;
    display: grid;
    gap: 9px;
    margin-top: 14px;
    height: 100%;
    align-content: space-between;
  }

  .exchange-stats div,
  .opportunity-meta div,
  .yield-item {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
  }

  .exchange-stats span,
  .opportunity-meta span,
  .yield-item span {
    color: #566578;
    font-size: 12px;
    font-weight: 700;
  }

  .exchange-stats strong,
  .opportunity-meta strong,
  .yield-item strong {
    font-size: 14px;
    font-weight: 700;
    color: #111827;
  }

  .opportunity-panel {
    display: flex;
    flex-direction: column;
  }

  .opportunity-value {
    margin-top: 8px;
    color: #16a34a;
    font-size: 38px;
    font-weight: 800;
    line-height: 1;
  }

  .opportunity-meta {
    display: grid;
    gap: 10px;
    margin-top: 18px;
  }

  .range-tabs {
    display: inline-flex;
    gap: 8px;
  }

  .range-tabs button {
    cursor: pointer;
  }

  .range-tabs button {
    min-width: 48px;
    height: 40px;
    padding: 0 12px;
    border: 1px solid #d7e1ec;
    border-radius: 10px;
    background: #fff;
    color: #475a77;
    font-size: 14px;
    font-weight: 800;
  }

  .range-tabs .active {
    border-color: rgba(220, 82, 82, 0.38);
    background: linear-gradient(180deg, #ff6868 0%, #ef4343 100%);
    color: #fff;
  }

  .trend-chart-shell {
    height: 260px;
  }

  .trend-chart {
    width: 100%;
    height: 100%;
  }

  .analysis-table th,
  .analysis-table td {
    padding: 12px 10px;
    border-bottom: 1px solid #edf2f7;
    text-align: left;
    font-size: 13px;
  }

  .analysis-table th {
    color: #5b6b7f;
    font-weight: 700;
    background: #fcfcfd;
    font-size: 13px;
    letter-spacing: 0.01em;
  }

  .history-panel .analysis-table {
    flex: 1;
  }

  .analysis-table {
    width: 100%;
    border-collapse: collapse;
  }

  .green {
    color: #16a34a !important;
  }

  .red {
    color: #ef4444 !important;
  }

  .funding-exec-shell {
    color: var(--strategy-text-1);
    background: var(--strategy-bg);
  }

  .panel,
  .exchange-card,
  .opportunity-card,
  .history-panel,
  .yield-item,
  .analysis-card {
    border-color: var(--strategy-border);
    background: linear-gradient(
      180deg,
      var(--strategy-surface) 0%,
      var(--strategy-surface-soft) 100%
    );
    box-shadow: var(--strategy-shadow);
  }

  .topbar-title h2,
  .panel-title h3,
  .selector-chip strong {
    color: var(--strategy-text-1);
  }

  .run-pill,
  .status-pill {
    background: var(--strategy-success-soft);
    color: var(--strategy-success);
  }

  .selector-chip,
  .latency-chip,
  .gear-btn,
  .ghost-btn,
  .field-input,
  .field-select {
    border-color: var(--strategy-border-strong);
    background: var(--strategy-surface);
  }

  .selector-chip span,
  .latency-chip,
  .field-label,
  .analysis-table th,
  .exchange-card small {
    color: var(--strategy-text-3);
  }

  .panel-title h3 {
    font-size: 16px;
    font-weight: 800;
  }

  .analysis-table th {
    color: var(--strategy-text-3);
    background: var(--strategy-table-head-bg);
    font-size: var(--strategy-font-sm);
  }

  .analysis-table td {
    border-bottom-color: var(--strategy-border-soft);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
    color: var(--strategy-text-2);
  }

  @media (max-width: 1400px) {
    .funding-upper-grid,
    .funding-lower-grid,
    .exchange-grid {
      grid-template-columns: 1fr;
    }

    .funding-exec-topbar,
    .topbar-controls,
    .panel-title--between {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
