<template>
  <section class="cross-replica">
    <header class="cross-head">
      <div class="cross-head__title">
        <h2>黄金跨所价差交易面板</h2>
        <span class="status-pill">运行中</span>
      </div>

      <div class="cross-head__controls">
        <label class="select-chip">
          <span>标的</span>
          <select v-model="selectedPair">
            <option :value="`${leftLegSymbol}-${rightLegSymbol}`">BYBIT: {{ leftLegSymbol }} vs MT5: {{ rightLegSymbol }}</option>
          </select>
        </label>
        <div class="meta-chip">
          <span>刷新间隔:</span>
          <strong>{{ latencyMs }}ms</strong>
          <i class="online-dot"></i>
        </div>
        <button class="gear-btn" type="button">⚙</button>
      </div>
    </header>

    <div class="cross-top-grid">
      <section class="cross-card">
        <div class="card-head">
          <div>
            <h3>市场报价</h3>
            <span>实时</span>
          </div>
        </div>

        <div class="quote-grid">
          <article class="quote-card">
            <div class="quote-card__head">
              <strong>BYBIT: {{ leftLegSymbol }}</strong>
              <span class="live-tag"><i class="online-dot"></i>在线</span>
            </div>
            <div class="quote-stats">
              <div class="quote-stat">
                <span>Bid</span>
                <strong class="green">2,331.12</strong>
                <small>USDT</small>
              </div>
              <div class="quote-stat">
                <span>Mid</span>
                <strong>2,331.17</strong>
                <small>USDT</small>
              </div>
              <div class="quote-stat">
                <span class="red-text">Ask</span>
                <strong class="red">2,331.22</strong>
                <small>USDT</small>
              </div>
              <div class="quote-stat">
                <span>延迟</span>
                <strong>18 ms</strong>
                <small>&nbsp;</small>
              </div>
            </div>
          </article>

          <article class="quote-card">
            <div class="quote-card__head">
              <strong>MT5: {{ rightLegSymbol }}</strong>
              <span class="live-tag"><i class="online-dot"></i>在线</span>
            </div>
            <div class="quote-stats">
              <div class="quote-stat">
                <span>Bid</span>
                <strong class="green">2,333.28</strong>
                <small>USD</small>
              </div>
              <div class="quote-stat">
                <span>Mid</span>
                <strong>2,333.33</strong>
                <small>USD</small>
              </div>
              <div class="quote-stat">
                <span class="red-text">Ask</span>
                <strong class="red">2,333.38</strong>
                <small>USD</small>
              </div>
              <div class="quote-stat">
                <span>延迟</span>
                <strong>22 ms</strong>
                <small>&nbsp;</small>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="cross-card cross-card--summary">
        <div class="card-head">
          <div>
            <h3>价差汇总</h3>
          </div>
        </div>

        <div class="summary-grid">
          <article class="summary-item">
            <label>做多价差 <small>(BY Ask - MT5 Bid)</small></label>
            <strong class="red">-2.06 <em>USDT</em></strong>
          </article>
          <article class="summary-item">
            <label>做空价差 <small>(BY Bid - MT5 Ask)</small></label>
            <strong class="red">-2.26 <em>USDT</em></strong>
          </article>
          <article class="summary-item">
            <label>资费 | 买方库存费 | 卖方库存费</label>
            <strong>0.010% | 0.043% | 0.021%</strong>
          </article>
          <article class="summary-item">
            <label>USDT/USD Basis</label>
            <strong class="green">-0.0002 (-0.02%)</strong>
          </article>
        </div>
      </section>

      <section class="cross-card cross-card--chart">
        <div class="card-head card-head--between">
          <div>
            <h3>做多价差走势</h3>
            <span>(BY Ask - MT5 Bid)</span>
          </div>
          <div class="range-tabs">
            <button
              v-for="range in ranges"
              :key="range"
              :class="{ active: selectedRange === range }"
              @click="selectedRange = range"
            >
              {{ range }}
            </button>
            <button class="gear-btn gear-btn--mini" type="button">⤢</button>
          </div>
        </div>

        <div ref="chartRef" class="spread-chart"></div>
      </section>
    </div>

    <div class="cross-mid-grid">
      <section class="cross-card cross-card--status">
        <div class="card-head">
          <div>
            <h3>策略执行</h3>
          </div>
        </div>

        <div class="status-mini-head">
          <span>最大杠杆</span>
          <span>执行方式</span>
          <span>状态</span>
          <span>操作</span>
        </div>

        <div class="status-mini-empty">
          <div class="status-mini-empty__icon"></div>
          <span>暂无数据</span>
        </div>

        <div class="status-mini-log">
          <div class="status-mini-log__head">
            <strong>执行反馈</strong>
          </div>

          <div class="status-mini-log__list">
            <p v-for="item in executionLogs.slice(0, 4)" :key="item.id">
              <i :class="['status-mini-log__dot', item.status === '成功' ? 'is-success' : item.status === '待确认' ? 'is-warn' : 'is-info']"></i>
              <span>{{ item.time }}: {{ item.direction }} {{ item.type }}</span>
            </p>
          </div>
        </div>
      </section>
      <section class="cross-card cross-card--execution">
        <div class="card-head">
          <div>
            <h3>价差执行指令</h3>
          </div>
        </div>

        <div class="stage-tabs">
          <button :class="{ active: executionStage === 'open' }" @click="executionStage = 'open'">开仓价差</button>
          <button :class="{ active: executionStage === 'close' }" @click="executionStage = 'close'">平仓价差</button>
        </div>

        <template v-if="executionStage === 'open'">
          <div class="execution-grid">
            <div class="execution-column execution-column--left">
              <label class="field-block">
                <span>下单数量</span>
                <div class="input-row input-row--qty">
                  <input :value="qtyOz.toFixed(2)" @input="handleQtyInput" />
                  <button type="button" class="unit-btn">盎司</button>
                  <button type="button" @click="nudgeQty(-10)">-</button>
                  <button type="button" @click="nudgeQty(10)">+</button>
                </div>
                <p v-if="qtyError" class="field-error">{{ qtyError }}</p>
              </label>

              <div class="mini-panel">
                <span class="mini-panel__title">自动配平</span>
                <div class="mini-grid">
                  <article class="metric-card">
                    <small>BYBIT 手数</small>
                    <strong>{{ formatNumber(bybitQty, 2) }}</strong>
                  </article>
                  <article class="metric-card">
                    <small>MT5 手数</small>
                    <strong>{{ formatNumber(mt5Lot, 2) }}</strong>
                  </article>
                </div>
              </div>

              <div class="mini-grid">
                <label class="field-block">
                  <span>BY 杠杆</span>
                  <div class="input-row">
                    <input :value="String(leverage)" @input="handleLeverageInput" />
                    <em>x</em>
                  </div>
                </label>
                <label class="field-block">
                  <span>MT5 杠杆</span>
                  <div class="input-row">
                    <input :value="String(leverage)" @input="handleLeverageInput" />
                    <em>x</em>
                  </div>
                </label>
              </div>
            </div>

            <div class="execution-column execution-column--pricing">
              <div class="mode-tabs">
                <button :class="{ active: executionMode === 'market' }" @click="executionMode = 'market'">市价开仓</button>
                <button :class="{ active: executionMode === 'limit' }" @click="executionMode = 'limit'">限价开仓</button>
              </div>

              <label class="field-block">
                <span>开仓价差</span>
                <div class="input-row">
                  <input v-model="triggerSpreadInput" inputmode="decimal" @blur="commitSpreadInput('trigger')" />
                  <em>USDT</em>
                </div>
              </label>

              <label class="field-block">
                <span>可接受价差</span>
                <div class="input-row">
                  <input v-model="acceptableSpreadInput" inputmode="decimal" @blur="commitSpreadInput('acceptable')" />
                  <em>USDT</em>
                </div>
              </label>
            </div>

            <div class="execution-column execution-column--right">
              <div class="execution-column__spacer" aria-hidden="true"></div>
              <label class="field-block field-block--lower">
                <span>止盈价差</span>
                <div class="input-row input-row--select">
                  <input v-model="takeProfitSpreadInput" inputmode="decimal" @blur="commitSpreadInput('takeProfit')" />
                  <em>USDT</em>
                  <select v-model="takeProfitExecution">
                    <option value="limit">限价</option>
                    <option value="market">市价</option>
                  </select>
                </div>
              </label>

              <label class="field-block">
                <span>止损价差</span>
                <div class="input-row input-row--select">
                  <input v-model="stopLossSpreadInput" inputmode="decimal" @blur="commitSpreadInput('stopLoss')" />
                  <em>USDT</em>
                  <select v-model="stopLossExecution">
                    <option value="market">市价</option>
                    <option value="limit">限价</option>
                  </select>
                </div>
              </label>
            </div>
          </div>

          <div class="submit-row">
            <button class="submit-btn submit-btn--green" @click="prepareOpenDraft('long')">开多价差</button>
            <button class="submit-btn submit-btn--red" @click="prepareOpenDraft('short')">开空价差</button>
          </div>
        </template>

        <template v-else>
          <div class="close-shell">
            <div class="mode-tabs">
              <button :class="{ active: closeExecutionMode === 'market' }" @click="closeExecutionMode = 'market'">市价平仓</button>
              <button :class="{ active: closeExecutionMode === 'limit' }" @click="closeExecutionMode = 'limit'">限价平仓</button>
            </div>

            <label class="field-block field-block--compact">
              <span>限价价差</span>
              <div class="input-row">
                <input v-model="closeLimitSpreadInput" inputmode="decimal" @blur="commitSpreadInput('closeLimit')" />
                <em>USDT</em>
              </div>
            </label>

            <table class="basic-table">
              <thead>
                <tr>
                  <th>方向</th>
                  <th>盎司</th>
                  <th>杠杆</th>
                  <th>开仓价差</th>
                  <th>止盈 / 止损</th>
                  <th>执行方式</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="position in closeOrders" :key="position.id">
                  <td :class="position.direction === 'LONG_SPREAD' ? 'green' : 'red'">
                    {{ position.direction === 'LONG_SPREAD' ? '多头' : '空头' }}
                  </td>
                  <td>{{ formatNumber(position.qtyOz, 2) }}</td>
                  <td>{{ position.leverage }}x</td>
                  <td>{{ formatSigned(position.entrySpread) }}</td>
                  <td>{{ formatSigned(position.takeProfit) }} / {{ formatSigned(position.stopLoss) }}</td>
                  <td>{{ position.execution }}</td>
                  <td>
                    <button class="row-btn" @click="openConfirm(`CLOSE:${position.id}`)">手动平仓</button>
                  </td>
                </tr>
              </tbody>
            </table>

            <button class="submit-btn submit-btn--red submit-btn--full" @click="openConfirm('CLOSE_ALL')">手动全平</button>
          </div>
        </template>
      </section>

      <section class="cross-card cross-card--monitor">
        <div class="card-head">
          <div>
            <h3>价差统计分析</h3>
          </div>
        </div>

        <div class="analysis-range analysis-range--inline">
          <div class="analysis-group analysis-group--row">
            <span>时间周期</span>
            <div class="analysis-tabs">
              <button
                v-for="period in analysisPeriods"
                :key="period"
                :class="{ active: selectedAnalysisPeriod === period }"
                @click="selectedAnalysisPeriod = period"
              >
                {{ period }}
              </button>
            </div>
          </div>
          <div class="analysis-group analysis-group--row">
            <span>数据范围</span>
            <div class="analysis-tabs">
              <button
                v-for="range in analysisDataRanges"
                :key="range"
                :class="{ active: selectedAnalysisDataRange === range }"
                @click="selectedAnalysisDataRange = range"
              >
                {{ range }}
              </button>
            </div>
          </div>
        </div>

        <div class="stats-list">
          <div><span>90%分位</span><strong>0.82 USDT</strong></div>
          <div><span>75%分位</span><strong>0.18 USDT</strong></div>
          <div><span>50%分位（中位数）</span><strong class="green">-0.06 USDT</strong></div>
          <div><span>25%分位</span><strong class="green">-0.34 USDT</strong></div>
          <div><span>10%分位</span><strong class="green">-0.92 USDT</strong></div>
        </div>

        <div class="monitor-box">
          <label class="field-block">
            <span>价差监控类型</span>
            <div class="input-row input-row--select">
              <select v-model="alertType">
                <option value="做多价差">做多价差（BY Ask - MT5 Bid）</option>
                <option value="做空价差">做空价差（BY Bid - MT5 Ask）</option>
                <option value="USDT Basis">USDT Basis</option>
              </select>
            </div>
          </label>

          <div class="monitor-grid">
            <label class="field-block">
              <span>触发条件</span>
              <div class="input-row input-row--select">
                <select v-model="alertOperator">
                  <option value="<=">&lt;=</option>
                  <option value=">=">&gt;=</option>
                </select>
                <input :value="alertThreshold.toFixed(2)" @input="handleDecimalInput('alertThreshold', $event)" />
                <em>USDT</em>
              </div>
            </label>
            <label class="field-block">
              <span>持续时间</span>
              <div class="input-row">
                <input :value="String(alertSeconds)" @input="handleIntegerInput('alertSeconds', $event)" />
                <em>分钟</em>
              </div>
            </label>
            <label class="field-block">
              <span>触发后延迟校验</span>
              <div class="input-row">
                <input :value="String(alertDelay)" @input="handleIntegerInput('alertDelay', $event)" />
                <em>秒</em>
              </div>
            </label>
            <label class="field-block">
              <span>预警渠道</span>
              <div class="input-row input-row--select">
                <select v-model="alertChannel">
                  <option value="全部渠道">全部渠道</option>
                  <option value="页面">页面</option>
                  <option value="声音">声音</option>
                  <option value="Webhook">Webhook</option>
                </select>
              </div>
            </label>
          </div>
        </div>

        <div class="monitor-footer">
          <div class="monitor-status monitor-status--row">
            <div>
              <span>监控状态</span>
              <strong :class="monitorRunning ? 'green' : 'warning'">{{ monitorRunning ? '运行中' : '已暂停' }}</strong>
            </div>
            <div>
              <span>运行时长</span>
              <strong>{{ monitorRuntime }}</strong>
            </div>
            <div>
              <span>上次触发</span>
              <strong>{{ lastTriggerTime }}</strong>
            </div>
          </div>

          <div class="submit-row submit-row--compact">
            <button class="submit-btn submit-btn--green submit-btn--monitor" @click="toggleMonitor(true)">下达监控</button>
            <button class="submit-btn submit-btn--red submit-btn--monitor" @click="toggleMonitor(false)">停止监控</button>
          </div>
        </div>
      </section>
    </div>

    <section class="cross-card cross-card--overview">
      <div class="card-head">
        <div class="overview-title">
          <h3>价差持仓总览</h3>
        </div>
      </div>

      <div class="overview-range">
        <div class="overview-range__meta">
          <span class="green">多 50.03%</span>
          <span class="red">49.97% 空</span>
        </div>
        <div class="overview-range__track">
          <div class="overview-range__green" style="width: 50.03%"></div>
          <div class="overview-range__red" style="width: 49.97%"></div>
        </div>
      </div>

      <div class="overview-summary overview-summary--top">
        <div class="overview-summary__item">
          <span>双边总损益</span>
          <strong class="green">-21.00</strong>
        </div>
        <div class="overview-summary__item">
          <span>单边总损益</span>
          <strong class="green">BY: -10 | MT5: -11</strong>
        </div>
        <div class="overview-summary__item">
          <span>单边爆仓价</span>
          <strong class="red">BY: 2,285 | MT5: 2,382</strong>
        </div>
      </div>

      <table class="overview-table">
        <thead>
          <tr>
            <th>方向</th>
            <th>盎司</th>
            <th>持仓价差（滑点）</th>
            <th>当前价差</th>
            <th>开仓明细</th>
            <th>未实现PnL (USDT)</th>
            <th>单边盈亏</th>
            <th>止盈价差</th>
            <th>止损价差</th>
            <th>爆仓价</th>
            <th>占用保证金</th>
            <th>开仓时间</th>
            <th>持仓时长</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="green">多头</td>
            <td>150.00</td>
            <td class="green">-1.85 (-0.05)</td>
            <td class="green">-2.10</td>
            <td>BY: 2,331.22 | MT5: 2,333.07</td>
            <td class="green">-37.50</td>
            <td>BY: -11 | MT5: -13</td>
            <td>-3.00</td>
            <td>1.00</td>
            <td class="red">BY 2,285 | MT5 2,382</td>
            <td>1,205.00 USDT</td>
            <td>2026-07-07 15:45:23</td>
            <td>01:26:45</td>
            <td class="green">正常</td>
          </tr>
          <tr>
            <td class="green">多头</td>
            <td>120.00</td>
            <td class="green">-2.05 (-0.05)</td>
            <td class="green">-2.32</td>
            <td>BY: 2,331.20 | MT5: 2,333.25</td>
            <td class="green">-32.40</td>
            <td>BY: -14 | MT5: -18</td>
            <td>-3.20</td>
            <td>1.00</td>
            <td class="red">BY 2,283 | MT5 2,380</td>
            <td>962.10 USDT</td>
            <td>2026-07-07 15:30:11</td>
            <td>01:41:57</td>
            <td class="green">正常</td>
          </tr>
          <tr>
            <td class="red">空头</td>
            <td>80.00</td>
            <td class="green">-1.10 (0.00)</td>
            <td class="green">-1.45</td>
            <td>BY: 2,331.15 | MT5: 2,332.25</td>
            <td class="green">-28.00</td>
            <td>BY: -9 | MT5: -11</td>
            <td>-2.80</td>
            <td>1.00</td>
            <td class="red">BY 2,287 | MT5 2,384</td>
            <td>641.40 USDT</td>
            <td>2026-07-07 15:13:03</td>
            <td>02:02:05</td>
            <td class="green">正常</td>
          </tr>
        </tbody>
      </table>

    </section>

    <div v-if="confirmVisible" class="trade-modal" @click.self="confirmVisible = false">
      <div class="trade-modal__dialog">
        <div class="trade-modal__header">
          <div>
            <p class="trade-modal__eyebrow">SPREAD ORDER CONFIRM</p>
            <h3>确认价差指令</h3>
          </div>
          <button class="trade-modal__close" @click="confirmVisible = false">×</button>
        </div>

        <div class="trade-modal__body">
          <div class="confirm-grid">
            <div><span>交易对</span><strong>{{ leftLegSymbol }} - {{ rightLegSymbol }}</strong></div>
            <div><span>动作</span><strong>{{ confirmSummary.action }}</strong></div>
            <div><span>盎司</span><strong>{{ confirmSummary.qty }}</strong></div>
            <div><span>BYBIT / MT5</span><strong>{{ confirmSummary.legs }}</strong></div>
            <div><span>执行方式</span><strong>{{ confirmSummary.mode }}</strong></div>
            <div><span>触发 / 接受</span><strong>{{ confirmSummary.spreadRange }}</strong></div>
            <div><span>止盈</span><strong>{{ confirmSummary.takeProfit }}</strong></div>
            <div><span>止损</span><strong>{{ confirmSummary.stopLoss }}</strong></div>
          </div>
        </div>

        <div class="trade-modal__footer">
          <button class="modal-btn modal-btn--ghost" @click="confirmVisible = false">取消</button>
          <button class="modal-btn modal-btn--primary" :disabled="submitLoading" @click="confirmOrder">
            {{ submitLoading ? '执行中...' : '确认执行' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';

  interface CloseOrder {
    id: string;
    direction: 'LONG_SPREAD' | 'SHORT_SPREAD';
    qtyOz: number;
    leverage: number;
    entrySpread: number;
    takeProfit: number;
    stopLoss: number;
    execution: string;
  }

  interface LogEntry {
    id: string;
    time: string;
    direction: string;
    type: string;
    qty: string;
    trigger: string;
    fill: string;
    status: string;
    channel: string;
  }

  defineProps<{
    leftLegSymbol: string;
    rightLegSymbol: string;
  }>();

  const ranges = ['1m', '5m', '15m', '1h', '4h', '1D'];
  const analysisPeriods = ['1m', '5m', '15m', '1h'];
  const analysisDataRanges = ['500', '1000', '自定义'];
  const selectedPair = ref('XAUTUSDT.P-XAUUSD');
  const selectedRange = ref('15m');
  const selectedAnalysisPeriod = ref('1m');
  const selectedAnalysisDataRange = ref('500');
  const latencyMs = ref(18);
  const executionStage = ref<'open' | 'close'>('open');
  const executionMode = ref<'market' | 'limit'>('market');
  const closeExecutionMode = ref<'market' | 'limit'>('market');
  const qtyOz = ref(100);
  const leverage = ref(10);
  const triggerSpread = ref(-1);
  const acceptableSpread = ref(-1.1);
  const takeProfitSpread = ref(-3);
  const stopLossSpread = ref(1);
  const takeProfitExecution = ref<'market' | 'limit'>('limit');
  const stopLossExecution = ref<'market' | 'limit'>('market');
  const closeLimitSpread = ref(-1.9);
  const triggerSpreadInput = ref(formatEditableNumber(triggerSpread.value));
  const acceptableSpreadInput = ref(formatEditableNumber(acceptableSpread.value));
  const takeProfitSpreadInput = ref(formatEditableNumber(takeProfitSpread.value));
  const stopLossSpreadInput = ref(formatEditableNumber(stopLossSpread.value));
  const closeLimitSpreadInput = ref(formatEditableNumber(closeLimitSpread.value));
  const submitLoading = ref(false);
  const confirmVisible = ref(false);
  const confirmAction = ref('OPEN_LONG');
  const openDirection = ref<'long' | 'short'>('long');
  const monitorRunning = ref(true);
  const monitorRuntime = ref('01:26:45');
  const lastTriggerTime = ref('15:34:01');
  const alertType = ref('做多价差');
  const alertOperator = ref('<=');
  const alertThreshold = ref(-2.5);
  const alertSeconds = ref(1);
  const alertDelay = ref(30);
  const alertChannel = ref('全部渠道');

  watch([triggerSpread, acceptableSpread, takeProfitSpread, stopLossSpread, closeLimitSpread], syncSpreadInputs);

  const closeOrders = ref<CloseOrder[]>([
    {
      id: 'close-1',
      direction: 'LONG_SPREAD',
      qtyOz: 100,
      leverage: 10,
      entrySpread: -1.85,
      takeProfit: -3,
      stopLoss: 1,
      execution: '限价 / 市价',
    },
    {
      id: 'close-2',
      direction: 'SHORT_SPREAD',
      qtyOz: 60,
      leverage: 8,
      entrySpread: -2.24,
      takeProfit: -0.8,
      stopLoss: -3.2,
      execution: '市价 / 限价',
    },
  ]);

  const executionLogs = ref<LogEntry[]>([
    { id: 'seed-1', time: '20:44:34', direction: '开多', type: '限价开仓', qty: '100.00', trigger: '-1.00', fill: '-1.10', status: '成功', channel: 'SPREAD_GOLD_001' },
    { id: 'seed-2', time: '15:45:23', direction: '开多', type: '市价开仓', qty: '100.00', trigger: '-1.80', fill: '-1.80', status: '成功', channel: 'SPREAD_GOLD_001' },
    { id: 'seed-3', time: '15:39:14', direction: '开空', type: '限价开仓', qty: '60.00', trigger: '-2.20', fill: '-2.24', status: '待确认', channel: 'MANUAL_DESK' },
  ]);

  const bybitQty = computed(() => qtyOz.value);
  const mt5Lot = computed(() => qtyOz.value * 0.01);
  const qtyError = computed(() => {
    if (qtyOz.value <= 0) return '数量需大于 0';
    if (qtyOz.value < 10) return '当前数量过低，无法完成 MT5 对冲换算';
    return '';
  });

  const confirmSummary = computed(() => {
    if (confirmAction.value === 'CLOSE_ALL') {
      return {
        action: '手动全平',
        qty: `${formatNumber(closeOrders.value.reduce((sum, item) => sum + item.qtyOz, 0), 2)} 盎司`,
        legs: '逐笔平仓全部持仓',
        mode: closeExecutionMode.value === 'market' ? '市价平仓' : '限价平仓',
        spreadRange: `${closeLimitSpread.value.toFixed(2)} USDT`,
        takeProfit: '--',
        stopLoss: '--',
      };
    }

    if (confirmAction.value.startsWith('CLOSE:')) {
      const target = closeOrders.value.find((item) => `CLOSE:${item.id}` === confirmAction.value);
      return {
        action: target?.direction === 'LONG_SPREAD' ? '平多价差' : '平空价差',
        qty: `${formatNumber(target?.qtyOz ?? 0, 2)} 盎司`,
        legs: `${formatNumber(target?.qtyOz ?? 0, 2)} / ${formatNumber((target?.qtyOz ?? 0) * 0.01, 2)}`,
        mode: closeExecutionMode.value === 'market' ? '市价平仓' : '限价平仓',
        spreadRange: `${closeLimitSpread.value.toFixed(2)} USDT`,
        takeProfit: `${formatSigned(target?.takeProfit ?? 0)} USDT`,
        stopLoss: `${formatSigned(target?.stopLoss ?? 0)} USDT`,
      };
    }

    return {
      action: openDirection.value === 'long' ? '开多价差' : '开空价差',
      qty: `${formatNumber(qtyOz.value, 2)} 盎司`,
      legs: `${formatNumber(bybitQty.value, 2)} / ${formatNumber(mt5Lot.value, 2)}`,
      mode: executionMode.value === 'market' ? '市价开仓' : '限价开仓',
      spreadRange: `${triggerSpread.value.toFixed(2)} / ${acceptableSpread.value.toFixed(2)} USDT`,
      takeProfit: `${takeProfitSpread.value.toFixed(2)} USDT / ${takeProfitExecution.value === 'limit' ? '限价' : '市价'}`,
      stopLoss: `${stopLossSpread.value.toFixed(2)} USDT / ${stopLossExecution.value === 'limit' ? '限价' : '市价'}`,
    };
  });

  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>);

  const chartSeries = [-2.3, -1.7, -1.1, -0.8, -0.9, -1.5, -2.1, -1.8, -0.4, 1.2, 0.6, -0.2, -1.4, -2.06];
  const chartLabels = ['05-28 06:00', '07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '18:30'];

  function renderChart() {
    nextTick(() => {
      chart?.setOptions({
        grid: { left: 56, right: 20, top: 30, bottom: 76 },
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: chartLabels,
          boundaryGap: false,
          axisLine: { lineStyle: { color: '#d7deea' } },
          axisLabel: { color: '#70819c', fontSize: 12 },
        },
        yAxis: {
          type: 'value',
          min: -4,
          max: 2,
          splitNumber: 3,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: '#70819c', fontSize: 12 },
          splitLine: { lineStyle: { color: '#eef2f8' } },
        },
        dataZoom: [
          {
            type: 'inside',
            start: 0,
            end: 100,
          },
          {
            type: 'slider',
            bottom: 16,
            height: 22,
            borderColor: '#dbe7fb',
            fillerColor: 'rgba(84, 138, 255, 0.12)',
            backgroundColor: '#f4f8ff',
            handleStyle: { color: '#4f7bf5' },
          },
        ],
        series: [
          {
            data: chartSeries,
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: { color: '#ff3535', width: 3 },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(255, 53, 53, 0.22)' },
                  { offset: 1, color: 'rgba(255, 53, 53, 0.03)' },
                ],
              },
            },
          },
        ],
      });
    });
  }

  function formatNumber(value: number, digits = 2) {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function formatSigned(value: number) {
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}`;
  }

  function formatEditableNumber(value: number) {
    if (!Number.isFinite(value)) return '0';
    return Number.isInteger(value) ? String(value) : String(value);
  }

  function parseEditableNumber(value: string) {
    const normalized = value.trim().replace(/[^0-9.\-]/g, '');
    if (!normalized || normalized === '-' || normalized === '.' || normalized === '-.') return null;
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function syncSpreadInputs() {
    triggerSpreadInput.value = formatEditableNumber(triggerSpread.value);
    acceptableSpreadInput.value = formatEditableNumber(acceptableSpread.value);
    takeProfitSpreadInput.value = formatEditableNumber(takeProfitSpread.value);
    stopLossSpreadInput.value = formatEditableNumber(stopLossSpread.value);
    closeLimitSpreadInput.value = formatEditableNumber(closeLimitSpread.value);
  }

  function commitSpreadInput(field: 'trigger' | 'acceptable' | 'takeProfit' | 'stopLoss' | 'closeLimit') {
    const inputMap = {
      trigger: triggerSpreadInput,
      acceptable: acceptableSpreadInput,
      takeProfit: takeProfitSpreadInput,
      stopLoss: stopLossSpreadInput,
      closeLimit: closeLimitSpreadInput,
    };
    const valueMap = {
      trigger: triggerSpread,
      acceptable: acceptableSpread,
      takeProfit: takeProfitSpread,
      stopLoss: stopLossSpread,
      closeLimit: closeLimitSpread,
    };
    const parsed = parseEditableNumber(inputMap[field].value);
    if (parsed === null) {
      inputMap[field].value = formatEditableNumber(valueMap[field].value);
      return;
    }
    valueMap[field].value = parsed;
    inputMap[field].value = formatEditableNumber(parsed);
  }

  function handleQtyInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    qtyOz.value = Number.isFinite(value) ? Math.max(0, value) : 0;
  }

  function handleLeverageInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    leverage.value = Number.isFinite(value) ? Math.max(1, Math.min(20, value)) : 1;
  }

  function handleDecimalInput(field: 'alertThreshold', event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    const nextValue = Number.isFinite(value) ? value : 0;
    if (field === 'alertThreshold') alertThreshold.value = nextValue;
  }

  function handleIntegerInput(field: 'alertSeconds' | 'alertDelay', event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    const nextValue = Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0;
    if (field === 'alertSeconds') alertSeconds.value = nextValue;
    if (field === 'alertDelay') alertDelay.value = nextValue;
  }

  function nudgeQty(delta: number) {
    qtyOz.value = Math.max(0, qtyOz.value + delta);
  }

  function prepareOpenDraft(direction: 'long' | 'short') {
    openDirection.value = direction;
    openConfirm(direction === 'long' ? 'OPEN_LONG' : 'OPEN_SHORT');
  }

  function openConfirm(action: string) {
    confirmAction.value = action;
    confirmVisible.value = true;
  }

  function appendLog(entry: Omit<LogEntry, 'id'>) {
    executionLogs.value.unshift({
      id: `${Date.now()}-${Math.random()}`,
      ...entry,
    });
  }

  function nowTime() {
    return new Date().toLocaleTimeString('zh-CN', { hour12: false });
  }

  function confirmOrder() {
    submitLoading.value = true;
    setTimeout(() => {
      if (confirmAction.value === 'CLOSE_ALL') {
        closeOrders.value = [];
      }
      if (confirmAction.value.startsWith('CLOSE:')) {
        const orderId = confirmAction.value.split(':')[1];
        closeOrders.value = closeOrders.value.filter((item) => item.id !== orderId);
      }
      appendLog({
        time: nowTime(),
        direction: confirmSummary.value.action,
        type: confirmSummary.value.mode,
        qty: confirmSummary.value.qty,
        trigger: confirmSummary.value.spreadRange,
        fill: confirmSummary.value.spreadRange,
        status: '成功',
        channel: 'SPREAD_GOLD_001',
      });
      submitLoading.value = false;
      confirmVisible.value = false;
    }, 560);
  }

  function toggleMonitor(nextState: boolean) {
    monitorRunning.value = nextState;
    lastTriggerTime.value = nextState ? '15:34:01' : '--';
  }

  onMounted(() => {
    renderChart();
  });
</script>

<style scoped lang="less">
  .cross-replica {
    display: flex;
    flex-direction: column;
    gap: 14px;
    color: #10203f;
    background: #f8fafc;
    font-family: var(--strategy-font-sans);
  }

  .cross-head,
  .cross-card {
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
  }

  .cross-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
    padding: 16px 18px;
  }

  .cross-head__title,
  .cross-head__controls,
  .quote-card__head,
  .card-head--between,
  .submit-row,
  .monitor-footer,
  .overview-title,
  .overview-range {
    display: flex;
    align-items: center;
  }

  .cross-head__title {
    gap: 12px;
  }

  .cross-head__title h2 {
    margin: 0;
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 700;
    letter-spacing: -0.015em;
    color: #13233f;
  }

  .status-pill {
    padding: 6px 13px;
    border-radius: 999px;
    background: rgba(39, 184, 115, 0.12);
    color: #1a9b58;
    font-size: 12px;
    font-weight: 800;
  }

  .cross-head__controls {
    gap: 10px;
  }

  .select-chip,
  .meta-chip {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 38px;
    padding: 0 14px;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.88);
    color: #637491;
    font-size: 12px;
    font-weight: 600;
  }

  .select-chip select,
  .input-row input,
  .input-row select {
    border: none;
    background: transparent;
    outline: none;
    color: #1a2a48;
    font-size: 14px;
  }

  .select-chip select {
    min-width: 296px;
    font-weight: 700;
  }

  .meta-chip strong {
    color: #18294b;
    font-weight: 700;
  }

  .online-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #1db954;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.12);
  }

  .gear-btn {
    width: 38px;
    height: 38px;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
    background: #ffffff;
    color: #8a6c49;
    cursor: pointer;
  }

  .gear-btn--mini {
    width: 32px;
    height: 32px;
  }

  .cross-top-grid,
  .cross-mid-grid {
    display: grid;
    gap: 14px;
  }

  .cross-top-grid {
    grid-template-columns: 1.42fr 0.86fr 1.08fr;
  }

  .cross-mid-grid {
    grid-template-columns: 0.54fr 1.34fr 0.82fr;
  }

  .cross-card {
    padding: 16px 18px 18px;
  }

  .cross-card--status {
    padding: 14px;
  }

  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  .card-head h3 {
    margin: 0;
    font-family: var(--strategy-font-heading);
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.012em;
    color: #162845;
  }

  .card-head span {
    margin-top: 4px;
    display: inline-block;
    color: #687b97;
    font-size: 12px;
    font-weight: 500;
  }

  .quote-grid,
  .summary-grid,
  .mini-grid,
  .monitor-grid {
    display: grid;
    gap: 12px;
  }

  .status-mini-head {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    padding: 2px 2px 10px;
    color: #60738e;
    font-size: 12px;
    font-weight: 600;
  }

  .status-mini-empty {
    display: flex;
    min-height: 168px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    border: 1px solid #e6ebf2;
    background: #fff;
    color: #b7c0cf;
  }

  .status-mini-empty__icon {
    width: 28px;
    height: 28px;
    border: 2px solid #c8d2e3;
    background: linear-gradient(180deg, #ffffff 0%, #f5f8fd 100%);
  }

  .status-mini-log {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #eef2f7;
  }

  .status-mini-log__head {
    margin-bottom: 10px;
  }

  .status-mini-log__head strong {
    color: #111827;
    font-size: 15px;
    font-weight: 700;
  }

  .status-mini-log__list {
    display: grid;
    gap: 10px;
  }

  .status-mini-log__list p {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin: 0;
    color: #475467;
    font-size: 12px;
    line-height: 1.55;
  }

  .status-mini-log__dot {
    width: 8px;
    height: 8px;
    margin-top: 5px;
    border-radius: 999px;
    flex: none;
  }

  .status-mini-log__dot.is-success {
    background: #22c55e;
  }

  .status-mini-log__dot.is-warn {
    background: #f59e0b;
  }

  .status-mini-log__dot.is-info {
    background: #60a5fa;
  }

  .quote-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .quote-card,
  .metric-card {
    border: 1px solid #e9edf2;
    border-radius: 16px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .quote-card {
    display: flex;
    flex-direction: column;
    padding: 16px 18px 18px;
    min-height: 214px;
  }

  .quote-card__head {
    justify-content: space-between;
    margin-bottom: 18px;
    color: #1a2b4a;
  }

  .quote-card__head strong {
    font-size: 16px;
    font-weight: 700;
  }

  .live-tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: #19a04d;
    font-size: 12px;
    font-weight: 600;
  }

  .quote-stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(78px, 1fr));
    gap: 8px;
    flex: 1;
  }

  .quote-stat {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 8px;
    min-height: 126px;
  }

  .quote-stat span,
  .summary-item small,
  .metric-card small,
  .field-block span,
  .stats-list span,
  .monitor-status span {
    color: #4d6383;
    font-size: 13px;
    font-weight: 600;
  }

  .quote-stat strong {
    font-family: var(--strategy-font-data);
    font-size: clamp(15px, 0.96vw, 26px);
    line-height: 1.08;
    font-weight: 700;
    letter-spacing: -0.02em;
    white-space: nowrap;
  }

  .quote-stat small {
    color: #7285a1;
    font-size: 11px;
    font-weight: 500;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    overflow: hidden;
    border: 1px solid #e9edf2;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.9);
  }

  .summary-item {
    min-height: 106px;
    padding: 14px 16px;
    border-right: 1px solid #e9edf2;
    border-bottom: 1px solid #e9edf2;
  }

  .summary-item:nth-child(2n) {
    border-right: none;
  }

  .summary-item:nth-last-child(-n + 2) {
    border-bottom: none;
  }

  .summary-item label {
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 7px;
    color: #1d2e4d;
    font-family: var(--strategy-font-heading);
    font-size: 16px;
    font-weight: 700;
  }

  .summary-item label small {
    color: #6b7f9c;
    font-size: 12px;
    font-weight: 500;
  }

  .summary-item strong {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    margin-top: 18px;
    color: #10203f;
    font-family: var(--strategy-font-data);
    font-size: 17px;
    font-weight: 700;
  }

  .summary-item strong em {
    font-size: 14px;
    font-style: normal;
  }

  .spread-chart {
    height: 238px;
  }

  .range-tabs,
  .stage-tabs,
  .mode-tabs,
  .analysis-tabs {
    display: flex;
    gap: 8px;
  }

  .range-tabs button,
  .stage-tabs button,
  .mode-tabs button,
  .analysis-tabs button,
  .row-btn {
    border: 1px solid #d7e2ef;
    border-radius: 10px;
    background: #fff;
    color: #47617f;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  .range-tabs button,
  .analysis-tabs button {
    height: 32px;
    min-width: 42px;
    padding: 0 12px;
  }

  .stage-tabs {
    margin-bottom: 14px;
  }

  .stage-tabs button {
    min-width: 118px;
    height: 44px;
    padding: 0 18px;
  }

  .mode-tabs {
    margin-bottom: 12px;
  }

  .mode-tabs button {
    flex: 1;
    height: 44px;
    padding: 0 18px;
  }

  .range-tabs button.active,
  .stage-tabs button.active,
  .mode-tabs button.active,
  .analysis-tabs button.active {
    border-color: rgba(220, 82, 82, 0.38);
    background: linear-gradient(180deg, #ff6868 0%, #ef4343 100%);
    color: #fff;
    box-shadow: 0 8px 20px rgba(239, 67, 67, 0.18);
  }

  .execution-grid {
    display: grid;
    grid-template-columns: 1.08fr 1fr 1fr;
    gap: 20px;
    align-items: start;
  }

  .execution-column {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .execution-column--pricing {
    gap: 14px;
    padding-top: 18px;
  }

  .execution-column--right {
    gap: 14px;
    padding-top: 18px;
  }

  .execution-column__spacer {
    height: 64px;
    flex: none;
  }

  .field-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .field-block--lower {
    margin-top: 0;
  }

  .field-block--compact {
    max-width: 360px;
    margin-bottom: 4px;
  }

  .input-row {
    display: grid;
    grid-template-columns: 1fr 62px;
    height: 48px;
    overflow: hidden;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
    background: #fff;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  }

  .input-row input,
  .input-row select {
    width: 100%;
    padding: 0 14px;
    font-family: var(--strategy-font-data);
    font-size: 14px;
    font-weight: 600;
  }

  .input-row em {
    display: flex;
    align-items: center;
    justify-content: center;
    border-left: 1px solid #e7ebf0;
    background: #fffaf4;
    color: #856746;
    font-size: 14px;
    font-style: normal;
    font-weight: 700;
  }

  .input-row--qty {
    grid-template-columns: 1fr 64px 40px 40px;
  }

  .input-row--select {
    grid-template-columns: 1fr 66px 88px;
  }

  .input-row--select select {
    border-left: 1px solid #e7ebf0;
  }

  .input-row--qty button,
  .unit-btn {
    border: none;
    border-left: 1px solid #e7ebf0;
    background: #fffaf4;
    color: #856746;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  .mini-panel {
    padding: 12px 14px 14px;
    border: 1px solid #e9edf2;
    border-radius: 16px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .mini-panel__title {
    display: block;
    margin-bottom: 10px;
    color: #516682;
    font-size: 13px;
    font-weight: 600;
  }

  .mini-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-card {
    min-height: 74px;
    padding: 12px 14px;
    border: 1px solid #e9edf2;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.94);
  }

  .metric-card strong {
    display: block;
    margin-top: 8px;
    color: #172947;
    font-family: var(--strategy-font-data);
    font-size: 17px;
    font-weight: 700;
  }

  .submit-row {
    justify-content: space-between;
    gap: 16px;
    margin-top: 16px;
  }

  .submit-row--compact {
    margin-top: 0;
  }

  .submit-btn {
    flex: 1;
    height: 52px;
    border: none;
    border-radius: 12px;
    color: #fff;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.01em;
    cursor: pointer;
  }

  .submit-btn--green {
    background: linear-gradient(90deg, #16a34a 0%, #0f8f3e 100%);
  }

  .submit-btn--red {
    background: linear-gradient(90deg, #ff4b4b 0%, #e92222 100%);
  }

  .submit-btn--full {
    width: 100%;
    margin-top: 16px;
    min-height: 58px;
    font-size: 18px;
  }

  .submit-btn--monitor {
    max-width: 156px;
  }

  .close-shell {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .basic-table,
  .overview-table {
    width: 100%;
    border-collapse: collapse;
  }

  .basic-table th,
  .basic-table td,
  .overview-table th,
  .overview-table td {
    padding: 13px 10px;
    border-bottom: 1px solid #efe7dc;
    font-size: 13px;
    text-align: left;
    white-space: nowrap;
  }

  .basic-table th,
  .overview-table th {
    color: #60738e;
    font-size: 12px;
    font-weight: 600;
  }

  .basic-table td,
  .overview-table td {
    color: #22324d;
    font-family: var(--strategy-font-data);
    font-weight: 600;
  }

  .row-btn {
    min-width: 104px;
    height: 40px;
    padding: 0 16px;
    font-size: 14px;
    font-weight: 600;
  }

  .analysis-range,
  .analysis-group,
  .monitor-status {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .analysis-range {
    gap: 12px;
    margin-bottom: 14px;
  }

  .analysis-range--inline {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
  }

  .analysis-range--inline .analysis-group {
    flex: 1;
    min-width: 0;
  }

  .analysis-group--row {
    flex-direction: row;
    align-items: center;
    gap: 14px;
  }

  .analysis-group--row .analysis-tabs {
    flex-wrap: wrap;
  }

  .analysis-group span {
    color: #556a87;
    font-size: 13px;
    font-weight: 700;
    white-space: nowrap;
  }

  .stats-list {
    display: grid;
    gap: 10px;
    margin-bottom: 14px;
    padding: 12px 14px 10px;
    border: 1px solid #efe7dc;
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(253, 249, 243, 0.98) 100%);
  }

  .stats-list div,
  .monitor-status div {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .stats-list strong,
  .monitor-status strong {
    color: #152646;
    font-size: 14px;
    font-weight: 800;
  }

  .monitor-box {
    margin-bottom: 14px;
    padding: 14px 16px 16px;
    border: 1px solid #efe7dc;
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(253, 249, 243, 0.98) 100%);
  }

  .monitor-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-top: 12px;
  }

  .monitor-footer {
    justify-content: space-between;
    gap: 16px;
  }

  .monitor-status {
    flex: 1;
  }

  .monitor-status--row {
    flex-direction: row;
    align-items: center;
    gap: 26px;
    padding-top: 2px;
  }

  .monitor-status--row div {
    min-width: 0;
  }

  .monitor-status strong {
    font-size: 16px;
  }

  .cross-card--overview {
    padding-bottom: 14px;
  }

  .overview-range {
    display: grid;
    gap: 6px;
    max-width: 540px;
    margin-bottom: 12px;
  }

  .overview-range__meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    font-weight: 800;
    line-height: 1;
  }

  .overview-range__track {
    position: relative;
    display: flex;
    height: 6px;
    overflow: hidden;
    border-radius: 999px;
    background: #eef2f8;
  }

  .overview-range__green {
    height: 100%;
    background: linear-gradient(90deg, #19a34b 0%, #16b257 100%);
  }

  .overview-range__red {
    height: 100%;
    background: linear-gradient(90deg, #ff6868 0%, #ff3d3d 100%);
  }

  .overview-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #edf2f8;
  }

  .overview-summary--top {
    margin-bottom: 12px;
  }

  .overview-summary__item {
    display: flex;
    align-items: baseline;
    gap: 10px;
    min-width: 0;
  }

  .overview-summary__item span {
    color: #61728e;
    font-size: 15px;
    font-weight: 700;
    white-space: nowrap;
  }

  .overview-summary__item strong {
    font-size: 19px;
    font-weight: 800;
    line-height: 1.1;
    white-space: nowrap;
  }

  .green {
    color: #179b4b !important;
  }

  .red,
  .red-text {
    color: #ef3232 !important;
  }

  .warning {
    color: #d07d1e !important;
  }

  .field-error {
    margin: 0;
    color: #d92b2b;
    font-size: 12px;
  }

  .trade-modal {
    position: fixed;
    inset: 0;
    z-index: 1200;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(11, 21, 42, 0.3);
  }

  .trade-modal__dialog {
    width: min(620px, calc(100vw - 32px));
    border-radius: 20px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    box-shadow: 0 30px 60px rgba(23, 41, 72, 0.24);
  }

  .trade-modal__header,
  .trade-modal__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 20px;
  }

  .trade-modal__header {
    border-bottom: 1px solid #edf2f8;
  }

  .trade-modal__body {
    padding: 18px 20px 22px;
  }

  .trade-modal__eyebrow {
    display: none;
  }

  .trade-modal__header h3 {
    margin: 0;
    color: #172947;
    font-size: 18px;
  }

  .trade-modal__close {
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    color: #678;
    font-size: 20px;
    cursor: pointer;
  }

  .confirm-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .confirm-grid div {
    padding: 12px 14px;
    border: 1px solid #e3ebf6;
    border-radius: 12px;
    background: #fbfdff;
  }

  .confirm-grid span {
    display: block;
    margin-bottom: 8px;
    color: #7b8aa5;
    font-size: 12px;
  }

  .confirm-grid strong {
    color: #172947;
    font-size: 14px;
    font-weight: 800;
  }

  .modal-btn {
    height: 40px;
    padding: 0 18px;
    border-radius: 10px;
    border: 1px solid #dfe7f4;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }

  .modal-btn--ghost {
    background: #fff;
    color: #526581;
  }

  .modal-btn--primary {
    border-color: #ff4b4b;
    background: #ff4b4b;
    color: #fff;
  }

  .cross-replica {
    color: var(--strategy-text-1);
    background: var(--strategy-bg);
  }

  .cross-head,
  .cross-card,
  .quote-card,
  .mini-panel,
  .metric-card,
  .summary-grid,
  .stats-list,
  .monitor-box,
  .trade-modal__dialog {
    border-color: var(--strategy-border);
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
  }

  .cross-head__title h2,
  .card-head h3,
  .summary-item label,
  .summary-item strong,
  .metric-card strong,
  .quote-card__head strong,
  .monitor-status strong,
  .overview-title h3 {
    color: var(--strategy-text-1);
  }

  .card-head span,
  .summary-item label small,
  .quote-stat small,
  .mini-panel__title,
  .analysis-group span,
  .status-mini-head,
  .overview-summary__item span {
    color: var(--strategy-text-3);
  }

  .status-pill {
    background: var(--strategy-success-soft);
    color: var(--strategy-success);
  }

  .select-chip,
  .meta-chip,
  .gear-btn,
  .input-row,
  .range-tabs button,
  .stage-tabs button,
  .mode-tabs button,
  .analysis-tabs button,
  .row-btn {
    border-color: var(--strategy-border-strong);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
  }

  .range-tabs button.active,
  .stage-tabs button.active,
  .mode-tabs button.active,
  .analysis-tabs button.active {
    border-color: rgba(201, 72, 72, 0.18);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px rgba(201, 72, 72, 0.08);
  }

  .select-chip select,
  .input-row input,
  .input-row select,
  .meta-chip strong {
    color: var(--strategy-text-1);
  }

  .input-row em,
  .input-row--qty button,
  .unit-btn {
    border-left-color: var(--strategy-border);
    background: var(--strategy-surface-muted);
    color: var(--strategy-text-2);
  }

  @media (max-width: 1480px) {
    .cross-top-grid,
    .cross-mid-grid,
    .execution-grid {
      grid-template-columns: 1fr;
    }

    .cross-head,
    .cross-head__controls {
      flex-direction: column;
      align-items: flex-start;
    }

    .select-chip select {
      min-width: 0;
      width: 100%;
    }

    .field-block--lower {
      margin-top: 0;
    }

    .execution-column__spacer {
      display: none;
    }

    .monitor-grid,
    .mini-grid,
    .quote-grid {
      grid-template-columns: 1fr;
    }

    .quote-stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .analysis-range--inline,
    .monitor-status--row,
    .overview-summary {
      grid-template-columns: 1fr;
      flex-direction: column;
    }
  }

  @media (max-width: 960px) {
    .stage-tabs,
    .mode-tabs,
    .submit-row,
    .monitor-footer {
      flex-direction: column;
      align-items: stretch;
    }

    .field-block--compact {
      max-width: none;
    }

    .basic-table,
    .overview-table {
      display: block;
      overflow-x: auto;
    }
  }
</style>
