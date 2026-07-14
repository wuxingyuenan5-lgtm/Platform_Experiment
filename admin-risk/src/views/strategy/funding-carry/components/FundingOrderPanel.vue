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
              <div><span>最新价格</span><strong>{{ item.price }}</strong></div>
              <div><span>资金费率</span><strong class="green">{{ item.rate }}</strong></div>
              <div><span>预期年化</span><strong class="green">{{ item.apr }}</strong></div>
              <div><span>下次结算</span><strong>{{ item.window }}</strong></div>
              <div><span>标记价格</span><strong>{{ item.markPrice }}</strong></div>
              <div><span>24H成交量</span><strong>{{ item.volume }}</strong></div>
              <div><span>持仓量</span><strong>{{ item.oi }}</strong></div>
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
      <section class="panel status-panel">
        <div class="panel-title">
          <h3>交易规则</h3>
        </div>

        <div class="rule-list">
          <div v-for="item in tradingRuleRows" :key="item.label" class="rule-list__row">
            <span class="rule-list__label">{{ item.label }}</span>
            <span class="rule-list__value">{{ item.value }}</span>
          </div>
        </div>

        <div class="status-feedback">
          <div class="status-feedback__head">
            <strong>执行反馈</strong>
            <button type="button" @click="executionFeedback = []">清空</button>
          </div>

          <div class="status-feedback__list">
            <p v-for="item in executionFeedback" :key="item.id">
              <i :class="['status-feedback__dot', item.tone]"></i>
              <span>{{ item.time }}: {{ item.text }}</span>
            </p>
          </div>
        </div>
      </section>

      <section class="panel order-panel">
        <div class="panel-title">
          <h3>套利执行指令</h3>
        </div>

        <div class="stage-tabs funding-stage-tabs">
          <button type="button" :class="{ active: fundingExecutionStage === 'open' }" @click="fundingExecutionStage = 'open'">开仓</button>
          <button type="button" :class="{ active: fundingExecutionStage === 'close' }" @click="fundingExecutionStage = 'close'">平仓</button>
        </div>

        <template v-if="fundingExecutionStage === 'open'">
          <div class="funding-order-grid">
            <section class="funding-order-column">
              <label class="field field--compact">
                <span>标的</span>
                <select v-model="selectedSymbol">
                  <option>BTCUSDT</option>
                  <option>ETHUSDT</option>
                  <option>SOLUSDT</option>
                </select>
              </label>

              <div class="funding-order-row">
                <label class="field field--compact">
                  <span>交易所</span>
                  <select v-model="selectedVenue">
                    <option>Binance</option>
                    <option>Bybit</option>
                    <option>OKX</option>
                  </select>
                </label>

                <label class="field field--compact">
                  <span>执行方式</span>
                  <select v-model="fundingOpenMode">
                    <option value="market">市价开仓</option>
                    <option value="limit">限价开仓</option>
                  </select>
                </label>
              </div>

              <div class="funding-order-row">
                <label class="field field--compact">
                  <span>名义本金</span>
                  <div class="input-with-unit">
                    <input v-model="notionalValue" type="text" />
                    <em>USDT</em>
                  </div>
                </label>

                <label class="field field--compact">
                  <span>数量 (BTC)</span>
                  <input v-model="orderQty" type="text" />
                </label>
              </div>

              <div class="funding-order-row">
                <label class="field field--compact">
                  <span>现货杠杆</span>
                  <select v-model="selectedLeverage">
                    <option>1x</option>
                    <option>2x</option>
                    <option>3x</option>
                    <option>5x</option>
                  </select>
                </label>

                <label class="field field--compact">
                  <span>合约杠杆</span>
                  <select v-model="fundingHedgeLeverage">
                    <option>1x</option>
                    <option>2x</option>
                    <option>3x</option>
                    <option>5x</option>
                  </select>
                </label>
              </div>

              <div class="funding-leg-grid">
                <div class="funding-leg-card">
                  <span>现货头寸</span>
                  <strong>{{ fundingLegs.spot }}</strong>
                  <em>买入 {{ selectedVenue }} 现货</em>
                </div>
                <div class="funding-leg-card">
                  <span>合约头寸</span>
                  <strong>{{ fundingLegs.perp }}</strong>
                  <em>卖出 {{ selectedVenue }} 永续</em>
                </div>
              </div>
            </section>

            <section class="funding-order-column">
              <div class="funding-mode-tabs">
                <button
                  type="button"
                  :class="{ active: fundingOpenDirection === 'collect' }"
                  @click="fundingOpenDirection = 'collect'"
                >
                  正套开仓
                </button>
                <button
                  type="button"
                  :class="{ active: fundingOpenDirection === 'pay' }"
                  @click="fundingOpenDirection = 'pay'"
                >
                  反套开仓
                </button>
              </div>

              <div class="funding-metric-grid">
                <div class="mini-kpi">
                  <span>当前资金费率</span>
                  <strong>+0.0810%</strong>
                </div>
                <div class="mini-kpi">
                  <span>现货-永续价差</span>
                  <strong>+10.5 USDT (+0.0102%)</strong>
                </div>
                <div class="mini-kpi">
                  <span>资费 | 买方库存费 | 卖方库存费</span>
                  <strong>+0.0810% | 0.0120% | 0.0090%</strong>
                </div>
                <div class="mini-kpi">
                  <span>预计持仓周期</span>
                  <strong>30 天</strong>
                </div>
              </div>

              <div class="funding-order-row">
                <label class="field field--compact">
                  <span>开仓阈值</span>
                  <div class="input-with-unit">
                    <input v-model="fundingThreshold" type="text" />
                    <em>%</em>
                  </div>
                </label>

                <label class="field field--compact">
                  <span>最大可接受入场价差</span>
                  <div class="input-with-unit">
                    <input v-model="fundingEntryBasis" type="text" />
                    <em>USDT</em>
                  </div>
                </label>
              </div>

              <div class="funding-order-row">
                <label class="field field--compact">
                  <span>目标回补价差</span>
                  <div class="input-with-unit">
                    <input v-model="fundingTakeProfit" type="text" />
                    <em>USDT</em>
                  </div>
                </label>

                <label class="field field--compact">
                  <span>止损价差</span>
                  <div class="input-with-unit">
                    <input v-model="stopSpread" type="text" />
                    <em>USDT</em>
                  </div>
                </label>
              </div>
            </section>
          </div>

          <div class="yield-strip">
            <div class="yield-item">
              <span>预计资金费收益</span>
              <strong class="green">+2,430.00 USDT</strong>
              <em>(2.43%)</em>
            </div>
            <div class="yield-op">-</div>
            <div class="yield-item">
              <span>手续费成本</span>
              <strong class="red">-120.00 USDT</strong>
              <em>(-0.12%)</em>
            </div>
            <div class="yield-op">+</div>
            <div class="yield-item">
              <span>基差回归收益</span>
              <strong class="green">+30.50 USDT</strong>
              <em>(+0.03%)</em>
            </div>
            <div class="yield-op">=</div>
            <div class="yield-item">
              <span>综合净收益</span>
              <strong class="green">+2,340.50 USDT</strong>
              <em>(2.34%)</em>
            </div>
          </div>

          <div class="funding-action-row">
            <button class="submit-btn submit-btn--green" type="button" @click="submitFundingOrder('collect')">提交正套开仓</button>
            <button class="submit-btn submit-btn--red" type="button" @click="submitFundingOrder('pay')">提交反套开仓</button>
          </div>
        </template>

        <template v-else>
          <div class="funding-close-shell">
            <div class="funding-close-head">
              <div class="funding-mode-tabs funding-mode-tabs--close">
                <button type="button" :class="{ active: fundingCloseMode === 'market' }" @click="fundingCloseMode = 'market'">市价平仓</button>
                <button type="button" :class="{ active: fundingCloseMode === 'limit' }" @click="fundingCloseMode = 'limit'">限价平仓</button>
              </div>

              <label class="field field--compact funding-close-limit">
                <span>平仓触发价差</span>
                <div class="input-with-unit">
                  <input v-model="fundingCloseBasis" type="text" />
                  <em>USDT</em>
                </div>
              </label>
            </div>

            <div class="funding-close-table-wrap">
              <table class="funding-close-table">
                <thead>
                  <tr>
                    <th>组合</th>
                    <th>现货头寸</th>
                    <th>合约头寸</th>
                    <th>当前资金费率</th>
                    <th>当前基差</th>
                    <th>未实现盈亏</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in fundingCloseRows" :key="row.id">
                    <td>{{ row.name }}</td>
                    <td>{{ row.spot }}</td>
                    <td>{{ row.perp }}</td>
                    <td>{{ row.rate }}</td>
                    <td>{{ row.basis }}</td>
                    <td :class="row.pnl.startsWith('-') ? 'red' : 'green'">{{ row.pnl }}</td>
                    <td class="green">{{ row.status }}</td>
                    <td><button class="flat-action" type="button" @click="submitFundingClose(row)">执行平仓</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </section>

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
              <td :class="row.state.includes('高') ? 'green' : row.state.includes('低') ? 'red' : ''">{{ row.state }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <section class="panel positions-panel">
      <div class="panel-title">
        <h3>当前持仓总览</h3>
      </div>

      <div class="positions-metrics">
        <div class="positions-metric"><span>累计资金费收益</span><strong class="green">+1,156.60 USDT</strong></div>
        <div class="positions-metric"><span>未实现盈亏</span><strong class="green">+1,036.20 USDT</strong></div>
        <div class="positions-metric"><span>当前基差 (现货-永续)</span><strong class="green">+10.5 USDT (+0.0102%)</strong></div>
        <div class="positions-metric"><span>保证金率</span><strong class="green">35.00%</strong></div>
        <div class="positions-metric"><span>Delta 偏离</span><strong>0.00%</strong></div>
        <div class="positions-metric"><span>强平距离</span><strong class="green">28.00%</strong></div>
      </div>

      <div class="positions-table-wrap">
        <table class="positions-table">
          <thead>
            <tr>
              <th>组合 / 方向</th>
              <th>交易所</th>
              <th>品种</th>
              <th>数量 (BTC)</th>
              <th>开仓价格 (USDT)</th>
              <th>当前价格 (USDT)</th>
              <th>当前资金费率</th>
              <th>入场价差 (USDT)</th>
              <th>当前基差 (USDT)</th>
              <th>累计资金费收益 (USDT)</th>
              <th>未实现盈亏 (USDT)</th>
              <th>保证金 (USDT)</th>
              <th>保证金率</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in positionRows" :key="row.name + row.leg">
              <td>
                <strong>{{ row.name }}</strong>
                <p>{{ row.leg }}</p>
              </td>
              <td>{{ row.exchange }}</td>
              <td>{{ row.symbol }}</td>
              <td>{{ row.qty }}</td>
              <td>{{ row.entry }}</td>
              <td>{{ row.mark }}</td>
              <td>{{ row.funding }}</td>
              <td>{{ row.entryBasis }}</td>
              <td class="green">{{ row.currentBasis }}</td>
              <td class="green">{{ row.carry }}</td>
              <td class="green">{{ row.pnl }}</td>
              <td>{{ row.margin }}</td>
              <td>{{ row.marginRatio }}</td>
              <td class="green">{{ row.status }}</td>
              <td><button class="flat-action" type="button">平仓</button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="positions-footer">
        <span>名义本金: 100,000.00 USDT</span>
        <span>总保证金: 40,300.00 USDT</span>
        <span>整体保证金率: 35.00%</span>
        <span class="green">预计年化综合净收益率: +22.31%</span>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, ref, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
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

  const positionRows = [
    {
      name: '套利组合 #1',
      leg: '现货买入',
      exchange: 'Binance',
      symbol: 'BTC/USDT',
      qty: '0.5000',
      entry: '102,200.0',
      mark: '102,350.0',
      funding: '--',
      entryBasis: '+12.0',
      currentBasis: '+10.5',
      carry: '+285.40',
      pnl: '+75.00',
      margin: '10,250.00',
      marginRatio: '35.10%',
      status: '正常',
    },
    {
      name: '套利组合 #1',
      leg: '永续卖出',
      exchange: 'Binance',
      symbol: 'BTCUSDT 永续',
      qty: '0.5000',
      entry: '102,212.0',
      mark: '102,341.2',
      funding: '+0.0810%',
      entryBasis: '+12.0',
      currentBasis: '+10.5',
      carry: '+285.40',
      pnl: '+64.60',
      margin: '10,250.00',
      marginRatio: '35.10%',
      status: '正常',
    },
    {
      name: '套利组合 #2',
      leg: '现货买入',
      exchange: 'Binance',
      symbol: 'BTC/USDT',
      qty: '0.4791',
      entry: '101,980.0',
      mark: '102,350.0',
      funding: '--',
      entryBasis: '+8.5',
      currentBasis: '+10.5',
      carry: '+195.30',
      pnl: '+177.30',
      margin: '9,800.00',
      marginRatio: '34.80%',
      status: '正常',
    },
    {
      name: '套利组合 #2',
      leg: '永续卖出',
      exchange: 'Binance',
      symbol: 'BTCUSDT 永续',
      qty: '0.4791',
      entry: '101,988.5',
      mark: '102,341.2',
      funding: '+0.0810%',
      entryBasis: '+8.5',
      currentBasis: '+10.5',
      carry: '+195.30',
      pnl: '+169.30',
      margin: '9,800.00',
      marginRatio: '34.80%',
      status: '正常',
    },
  ];

  const fundingCloseRows = ref([
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

  const executionFeedback = ref([
    { id: 'feedback-1', tone: 'is-success', time: '2026-03-18 15:44:45', text: '正套开仓成功，现货腿与永续腿已同步成交。' },
    { id: 'feedback-2', tone: 'is-success', time: '2026-03-18 15:44:45', text: '对冲腿下单完成，成交均价与预估偏差可控。' },
    { id: 'feedback-3', tone: 'is-success', time: '2026-03-18 15:44:43', text: '执行引擎已完成风控校验，保证金占用正常。' },
    { id: 'feedback-4', tone: 'is-info', time: '2026-03-18 15:44:42', text: '已发起套利执行请求，等待交易所返回最终回报。' },
  ]);

  const fundingLegs = computed(() => {
    const qty = Number(orderQty.value || 0).toFixed(4);
    const directionLabel = fundingOpenDirection.value === 'collect' ? '正套' : '反套';
    return {
      spot: `${directionLabel} ${qty} BTC`,
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
    pushExecutionFeedback(`${sideLabel}开仓已提交，${selectedVenue.value} ${selectedSymbol.value} 名义本金 ${notionalValue.value} USDT。`);
  }

  function submitFundingClose(row: (typeof fundingCloseRows.value)[number]) {
    pushExecutionFeedback(`${row.name} 已发起${fundingCloseMode.value === 'market' ? '市价' : '限价'}平仓。`, 'is-info');
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
  .yield-item,
  .positions-footer {
    display: flex;
    align-items: center;
  }

  .funding-exec-topbar,
  .panel-title--between,
  .exchange-card__head,
  .positions-footer {
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
    font-size: 18px;
    font-weight: 900;
  }

  .status-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 14px;
  }

  .order-panel,
  .history-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .order-panel {
    min-height: 684px;
  }

  .rule-list {
    display: grid;
    gap: 10px;
  }

  .rule-list__row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    min-height: 42px;
    padding: 0 12px;
    border: 1px solid #e6ebf2;
    border-radius: 10px;
    background: #fff;
  }

  .rule-list__label {
    color: #5d6d80;
    font-size: 13px;
    font-weight: 700;
  }

  .rule-list__value {
    color: #364152;
    font-size: 12px;
    font-weight: 700;
    text-align: right;
    line-height: 1.45;
  }

  .status-feedback {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #eef2f7;
  }

  .status-feedback__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .status-feedback__head strong {
    color: #111827;
    font-size: 15px;
    font-weight: 800;
  }

  .status-feedback__head button {
    border: none;
    background: transparent;
    color: #526173;
    font-size: 12px;
    cursor: pointer;
    font-weight: 700;
  }

  .status-feedback__list {
    display: grid;
    gap: 10px;
  }

  .status-feedback__list p {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin: 0;
    color: #364152;
    font-size: 12px;
    line-height: 1.55;
  }

  .status-feedback__dot {
    width: 8px;
    height: 8px;
    margin-top: 5px;
    border-radius: 999px;
    flex: none;
  }

  .status-feedback__dot.is-success {
    background: #22c55e;
  }

  .status-feedback__dot.is-info {
    background: #60a5fa;
  }

  .exchange-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .exchange-card {
    min-height: 214px;
    border: 1px solid #edf2f7;
    border-radius: 14px;
    padding: 14px 14px 16px;
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
    display: grid;
    gap: 9px;
    margin-top: 14px;
  }

  .exchange-stats div,
  .opportunity-meta div,
  .yield-item,
  .positions-metric {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
  }

  .exchange-stats span,
  .opportunity-meta span,
  .mini-kpi span,
  .field span,
  .yield-item span,
  .positions-metric span,
  .funding-leg-card span {
    color: #566578;
    font-size: 13px;
    font-weight: 700;
  }

  .exchange-stats strong,
  .opportunity-meta strong,
  .mini-kpi strong,
  .yield-item strong,
  .positions-metric strong {
    font-size: 15px;
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

  .range-tabs,
  .stage-tabs,
  .funding-mode-tabs {
    display: inline-flex;
    gap: 8px;
  }

  .range-tabs button,
  .stage-tabs button,
  .funding-mode-tabs button,
  .submit-btn,
  .flat-action {
    cursor: pointer;
  }

  .range-tabs button,
  .stage-tabs button,
  .funding-mode-tabs button {
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

  .range-tabs .active,
  .stage-tabs .active,
  .funding-mode-tabs .active {
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

  .funding-stage-tabs {
    margin-bottom: 14px;
  }

  .funding-order-grid {
    display: grid;
    grid-template-columns: 1.03fr 1fr;
    gap: 16px;
    min-height: 330px;
    align-items: start;
  }

  .funding-order-column {
    display: grid;
    gap: 12px;
  }

  .funding-order-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .field {
    display: grid;
    gap: 6px;
  }

  .field--compact span {
    font-size: 14px;
    font-weight: 900;
    color: #465e7d;
  }

  .field select,
  .field input {
    width: 100%;
    height: 48px;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
    background: #fff;
    padding: 0 12px;
    color: #13233f;
    font-size: 15px;
    font-weight: 700;
  }

  .input-with-unit {
    display: grid;
    grid-template-columns: 1fr 72px;
    overflow: hidden;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
  }

  .input-with-unit input {
    border: none;
    border-radius: 0;
  }

  .input-with-unit em {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #ffffff;
    color: #866948;
    font-size: 14px;
    font-style: normal;
    font-weight: 800;
  }

  .funding-leg-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .funding-leg-card {
    display: grid;
    gap: 8px;
    min-height: 96px;
    padding: 14px;
    border: 1px solid #e9edf2;
    border-radius: 14px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .funding-leg-card strong {
    color: #111827;
    font-size: 24px;
    font-weight: 800;
  }

  .funding-leg-card em {
    color: #6d7d90;
    font-size: 12px;
    font-style: normal;
    font-weight: 700;
  }

  .funding-mode-tabs {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .funding-mode-tabs button {
    height: 40px;
    border-radius: 10px;
  }

  .funding-metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .mini-kpi {
    min-height: 88px;
    border: 1px solid #e9edf2;
    border-radius: 14px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    padding: 14px;
  }

  .yield-strip {
    display: grid;
    grid-template-columns: 1fr 32px 1fr 32px 1fr 32px 1fr;
    gap: 10px;
    align-items: center;
    margin-top: 14px;
    padding: 14px;
    border: 1px solid #e9edf2;
    border-radius: 14px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .yield-item {
    justify-content: space-between;
  }

  .yield-item em {
    color: #708094;
    font-size: 12px;
    font-style: normal;
    font-weight: 700;
  }

  .yield-op {
    color: #98a2b3;
    text-align: center;
    font-size: 18px;
    font-weight: 800;
  }

  .funding-action-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-top: 14px;
  }

  .submit-btn {
    width: 100%;
    height: 52px;
    border: none;
    border-radius: 12px;
    color: #fff;
    font-size: 16px;
    font-weight: 900;
  }

  .submit-btn--green {
    background: linear-gradient(90deg, #119c41 0%, #0fa24c 100%);
  }

  .submit-btn--red {
    background: linear-gradient(90deg, #df3342 0%, #f14f5c 100%);
  }

  .funding-close-shell {
    display: grid;
    gap: 16px;
    min-height: 388px;
    align-content: start;
  }

  .funding-close-head {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 12px;
  }

  .funding-close-limit {
    min-width: 260px;
  }

  .funding-close-table-wrap {
    flex: 1;
    overflow: auto;
    border: 1px solid #e9edf2;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.95);
  }

  .funding-close-table {
    width: 100%;
    border-collapse: collapse;
  }

  .funding-close-table th,
  .funding-close-table td,
  .analysis-table th,
  .analysis-table td,
  .positions-table th,
  .positions-table td {
    padding: 12px 10px;
    border-bottom: 1px solid #edf2f7;
    text-align: left;
    font-size: 13px;
  }

  .funding-close-table th,
  .analysis-table th,
  .positions-table th {
    color: #5b6b7f;
    font-weight: 700;
    background: #fcfcfd;
    font-size: 12px;
  }

  .positions-panel {
    padding-bottom: 10px;
  }

  .history-panel .analysis-table {
    flex: 1;
  }

  .positions-metrics {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 12px;
  }

  .positions-metric {
    min-height: 64px;
    padding: 10px 12px;
    border: 1px solid #edf2f7;
    border-radius: 12px;
    background: #fff;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
  }

  .analysis-table,
  .positions-table {
    width: 100%;
    border-collapse: collapse;
  }

  .positions-table-wrap {
    overflow: auto;
  }

  .positions-table {
    min-width: 1600px;
  }

  .positions-table td strong {
    color: #111827;
    font-size: 13px;
  }

  .positions-table td p {
    margin: 4px 0 0;
    color: #16a34a;
    font-size: 12px;
    font-weight: 700;
  }

  .flat-action {
    min-width: 104px;
    height: 40px;
    border: 1px solid #2e61d8;
    border-radius: 10px;
    background: #fff;
    color: #2e61d8;
    font-size: 14px;
    font-weight: 800;
  }

  .positions-footer {
    gap: 28px;
    margin-top: 12px;
    color: #364152;
    font-size: 13px;
    font-weight: 700;
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
  .status-panel,
  .yield-item,
  .funding-leg-card,
  .metric-block,
  .analysis-card,
  .positions-table-wrap {
    border-color: var(--strategy-border);
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
  }

  .topbar-title h2,
  .panel-title h3,
  .positions-table td strong,
  .flat-action,
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
  .field-select,
  .stage-tabs button,
  .funding-mode-tabs button,
  .flat-action {
    border-color: var(--strategy-border-strong);
    background: var(--strategy-surface);
  }

  .selector-chip span,
  .latency-chip,
  .field-label,
  .rule-list__label,
  .analysis-table th,
  .positions-table th,
  .positions-footer,
  .exchange-card small {
    color: var(--strategy-text-3);
  }

  .stage-tabs .active,
  .funding-mode-tabs .active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px rgba(201, 72, 72, 0.1);
  }

  @media (max-width: 1400px) {
    .funding-upper-grid,
    .funding-lower-grid,
    .positions-metrics,
    .exchange-grid,
    .funding-order-grid,
    .funding-order-row,
    .funding-leg-grid,
    .funding-metric-grid,
    .funding-action-row {
      grid-template-columns: 1fr;
    }

    .funding-exec-topbar,
    .topbar-controls,
    .panel-title--between,
    .positions-footer,
    .funding-close-head {
      flex-direction: column;
      align-items: flex-start;
    }

    .yield-strip {
      grid-template-columns: 1fr;
    }

    .yield-op {
      display: none;
    }
  }

  @media (max-width: 1024px) {
    .funding-close-head,
    .rule-list {
      gap: 10px;
    }

    .funding-close-limit {
      min-width: 0;
      width: 100%;
    }

    .positions-table-wrap,
    .funding-close-table-wrap {
      width: 100%;
    }
  }
</style>
