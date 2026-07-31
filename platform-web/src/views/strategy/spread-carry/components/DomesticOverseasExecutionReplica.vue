<template>
  <section class="domestic-replica">
    <header class="domestic-topbar">
      <div class="domestic-topbar__left">
        <label class="topbar-control">
          <span>交易场景</span>
          <select v-model="selectedVenueState">
            <option value="SHFE / XAUUSD">SHFE / XAUUSD</option>
            <option value="AU9999 / XAUUSD">AU9999 / XAUUSD</option>
          </select>
        </label>
        <label class="topbar-control">
          <span>主腿标的</span>
          <select v-model="selectedMainLegState" @change="applyTopbarMainLeg">
            <option value="SHFE.au2604">SHFE.au2604</option>
            <option value="SHFE.au2606">SHFE.au2606</option>
            <option value="SHFE.au2612">SHFE.au2612</option>
            <option value="AU9999">AU9999</option>
          </select>
        </label>
        <label class="topbar-control">
          <span>对冲腿标的</span>
          <select v-model="selectedHedgeLegState">
            <option value="XAUUSD">XAUUSD</option>
          </select>
        </label>
        <label class="topbar-control">
          <span>时间精度</span>
          <select v-model="selectedResolutionState">
            <option value="30分钟">30分钟</option>
            <option value="1小时">1小时</option>
            <option value="4小时">4小时</option>
          </select>
        </label>
      </div>

    </header>

    <div class="hero-grid">
      <section class="hero-left">
        <article class="gauge-card">
          <div class="gauge-shell gauge-shell--asset">
            <div class="gauge-core"></div>
            <div class="gauge-needle gauge-needle--blue"></div>
          </div>
          <div class="gauge-meta">
            <div>
              <span>沪金</span>
              <strong>11,312,370.08</strong>
            </div>
            <div>
              <span>伦敦金</span>
              <strong>8,801,303.88</strong>
            </div>
          </div>
          <div class="gauge-caption">资产水平（CNY）</div>
        </article>

        <article class="gauge-card">
          <div class="gauge-shell gauge-shell--position">
            <div class="gauge-core"></div>
            <div class="gauge-needle gauge-needle--green"></div>
          </div>
          <div class="position-balance">
            <span class="green">多</span>
            <div class="position-balance__text">
              <strong>74.58% VS 空 25.42%</strong>
              <small>23,028,402.01 CNY</small>
            </div>
            <span class="red">空</span>
          </div>
          <div class="gauge-caption">仓位平衡</div>
        </article>
      </section>

      <section class="hero-right">
        <div class="account-head">
          <span>账户信息</span>
          <button class="refresh-btn" :disabled="refreshing" @click="triggerRefresh">
            {{ refreshing ? '刷新中' : '刷新' }}
          </button>
        </div>

        <div class="account-rows">
          <div class="account-row">
            <div class="account-row__label">总计</div>
            <div class="account-row__item">
              <span>AUM</span>
              <strong>20,343,790.35 CNY</strong>
              <small>2,984,316.97 USD</small>
            </div>
            <div class="account-row__item">
              <span>杠杆</span>
              <strong>1.1X</strong>
            </div>
            <div class="account-row__item">
              <span>备用金CNY</span>
              <strong>0</strong>
            </div>
            <div class="account-row__item">
              <span>备用金USD</span>
              <strong>0</strong>
            </div>
          </div>

          <div class="account-row account-row--blue">
            <div class="account-row__label">沪金</div>
            <div class="account-row__item">
              <span>AUM</span>
              <strong>11,312,370.08</strong>
              <small>CNY</small>
            </div>
            <div class="account-row__item">
              <span>杠杆</span>
              <strong>1.5X</strong>
            </div>
            <div class="account-row__item account-row__item--wide">
              <span>可用资金率</span>
              <div class="progress-line">
                <i :style="{ width: `${impact.availableAfter}%` }"></i>
                <em>{{ impact.availableAfter.toFixed(2) }}%</em>
              </div>
            </div>
          </div>

          <div class="account-row account-row--yellow">
            <div class="account-row__label">伦敦金</div>
            <div class="account-row__item">
              <span>AUM</span>
              <strong>1,324,857.38</strong>
              <small>USD</small>
            </div>
            <div class="account-row__item">
              <span>杠杆</span>
              <strong>0.6X</strong>
            </div>
            <div class="account-row__item account-row__item--wide">
              <span>预付比率</span>
              <strong>{{ impact.marginAfter.toFixed(4) }}%</strong>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section class="main-board">
      <aside class="left-column">
        <section class="block-card">
          <div class="block-title">交易规则</div>
          <div class="rule-list">
            <div v-for="item in tradingRuleRows" :key="item.label" class="rule-list__row">
              <span class="rule-list__label">{{ item.label }}</span>
              <span class="rule-list__value">{{ item.value }}</span>
            </div>
          </div>
        </section>

        <section class="block-card">
          <div class="block-title block-title--between">
            <span>执行反馈</span>
            <button class="inline-link" @click="clearLogs">清空</button>
          </div>
          <div class="log-list">
            <p v-for="item in executionLogs" :key="item.id">
              <span :class="['log-dot', `is-${item.type}`]"></span>
              {{ item.time }}：{{ item.message }}
            </p>
          </div>
        </section>
      </aside>

      <section class="right-column">
        <div class="trade-head">
          <div class="trade-tabs">
            <button :class="{ active: activeTradeTab === 'open' }" @click="activeTradeTab = 'open'">开仓</button>
            <button :class="{ active: activeTradeTab === 'rollover' }" @click="activeTradeTab = 'rollover'">移仓</button>
          </div>
        </div>

        <div class="selector-row">
          <div class="selector-toolbar">
            <div class="selector-group">
              <span>配平方式</span>
              <div class="balance-tabs">
                <button :class="{ active: balanceMode === 'gram_balance' }" @click="setBalanceMode('gram_balance')">克数配平</button>
                <button :class="{ active: balanceMode === 'value_balance' }" @click="setBalanceMode('value_balance')">金额配平</button>
                <button :class="{ active: balanceMode === 'lot_balance' }" @click="setBalanceMode('lot_balance')">手数配平</button>
                <button :class="{ active: balanceMode === 'custom_ratio' }" @click="setBalanceMode('custom_ratio')">自定义比例</button>
              </div>
            </div>

            <div class="selector-group">
              <span>主腿标的</span>
              <div class="contract-tabs">
                <button :class="{ active: selectedContract === 'SHFE.au2604' }" @click="setContract('SHFE.au2604')">沪金2604</button>
                <button :class="{ active: selectedContract === 'SHFE.au2606' }" @click="setContract('SHFE.au2606')">沪金2606</button>
                <button :class="{ active: selectedContract === 'SHFE.au2612' }" @click="setContract('SHFE.au2612')">沪金2612</button>
                <button :class="{ active: selectedContract === 'SHFE.au2704' }" @click="setContract('SHFE.au2704')">沪金2704</button>
              </div>
            </div>
          </div>
          <div class="selector-right">{{ selectedHedgeLegState }}</div>
        </div>

        <div v-if="balanceMode === 'custom_ratio'" class="custom-ratio-row">
          <label class="custom-ratio-field">
            <span>主腿比例</span>
            <input v-model="customMainRatio" type="number" min="0" step="0.01" />
          </label>
          <label class="custom-ratio-field">
            <span>对冲腿比例</span>
            <input v-model="customHedgeRatio" type="number" min="0" step="0.01" />
          </label>
        </div>

        <div class="legs-grid">
          <article class="leg-panel">
            <div class="leg-panel__stats">
              <div>
                <span>最新价</span>
                <strong class="red">{{ shfeLast.toFixed(1) }}</strong>
              </div>
              <div>
                <span>当前持仓</span>
                <strong>{{ shfePosition.toFixed(0) }}</strong>
              </div>
              <div>
                <span>持仓价值CNY</span>
                <strong>{{ formatNumber(shfePositionValue, 0) }}</strong>
              </div>
            </div>

            <div class="leg-panel__entry">
              <label>
                <span>数量(1000克/手)</span>
                <input :value="shfeLots === 0 ? '' : shfeLots" @input="handleShfeInput" />
              </label>
              <div class="entry-meta">手　　价值: {{ formatNumber(shfeValueCny, 0) }}</div>
            </div>

            <div class="leg-hint">当前可开: 约62手　　可用余额: 10,485,527 CNY</div>
          </article>

          <article class="leg-panel">
            <div class="leg-panel__stats">
              <div>
                <span>最新价</span>
                <strong class="green">{{ xauLast.toFixed(2) }}</strong>
              </div>
              <div>
                <span>当前持仓</span>
                <strong>{{ xauPosition.toFixed(0) }}</strong>
              </div>
              <div>
                <span>持仓价值USD</span>
                <strong>{{ formatNumber(xauPositionValue, 0) }}</strong>
              </div>
            </div>

            <div class="leg-panel__entry">
              <label>
                <span>数量(3110.35克/手)</span>
                <input :value="xauLots.toFixed(2)" readonly />
              </label>
              <div class="entry-meta">手　　价值: {{ formatNumber(xauValueUsd, 0) }} / 克数: {{ xauGrams.toFixed(0) }}</div>
            </div>

            <div class="leg-hint">自动匹配: {{ xauLots.toFixed(2) }} 手　　可用余额: USD</div>
          </article>
        </div>

        <div class="action-row">
          <button :class="['action-btn', { active: selectedAction === 'open' }]" @click="prepareAction('open')">策略开仓</button>
          <button :class="['action-btn', { active: selectedAction === 'close' }]" @click="prepareAction('close')">策略平仓</button>
          <button :class="['action-btn', { active: selectedAction === 'takeProfit' }]" @click="prepareAction('takeProfit')">止盈</button>
          <button :class="['action-btn', { active: selectedAction === 'gridOpen' }]" @click="prepareAction('gridOpen')">网格开仓</button>
        </div>

        <div class="impact-board">
          <div class="impact-title">执行后影响</div>
          <div class="impact-grid">
            <article class="impact-card">
              <span>可用资金率</span>
              <strong>{{ impact.availableBefore.toFixed(2) }}% <em class="green">→ {{ impact.availableAfter.toFixed(2) }}%</em></strong>
            </article>
            <article class="impact-card">
              <span>整体杠杆</span>
              <strong>{{ impact.leverageBefore.toFixed(4) }} → {{ impact.leverageAfter.toFixed(4) }} <em class="orange">MAX={{ impact.maxLeverage.toFixed(4) }}</em></strong>
            </article>
            <article class="impact-card">
              <span>预付比率</span>
              <strong>{{ impact.marginBefore.toFixed(4) }}% <em class="green">→ {{ impact.marginAfter.toFixed(4) }}%</em></strong>
            </article>
          </div>
        </div>

        <div class="confirm-row">
          <button :disabled="!canConfirm || executing" @click="confirmVisible = true">
            {{ executing ? '执行中...' : '确认执行' }}
          </button>
        </div>
      </section>
    </section>

    <div v-if="confirmVisible" class="trade-modal" @click.self="confirmVisible = false">
      <div class="trade-modal__dialog">
        <div class="trade-modal__header">
          <div>
            <p class="trade-modal__eyebrow">TRADE EXECUTION REVIEW</p>
            <h3>确认执行</h3>
          </div>
          <button class="trade-modal__close" @click="confirmVisible = false">×</button>
        </div>

        <div class="trade-modal__body">
          <div class="confirm-lines">
            <p>策略：沪金伦敦金多空策略</p>
            <p>操作：{{ actionText }}</p>
            <p>配平模式：{{ balanceModeText }}</p>
            <p>沪金合约：{{ selectedContract }}</p>
            <p>沪金数量：{{ shfeLots }} 手</p>
            <p>XAUUSD 数量：{{ xauLots.toFixed(2) }} 手</p>
            <p>沪金最新价：{{ shfeLast.toFixed(1) }}</p>
            <p>XAUUSD 最新价：{{ xauLast.toFixed(2) }}</p>
            <p>价差：{{ spreadPercent.toFixed(4) }}% / {{ spreadCny.toFixed(2) }}CNY</p>
          </div>
        </div>

        <div class="trade-modal__footer">
          <button class="modal-btn modal-btn--ghost" @click="confirmVisible = false">取消</button>
          <button class="modal-btn modal-btn--primary" :disabled="executing" @click="executeTrade">
            {{ executing ? '执行中...' : '确认执行' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';

  interface LogItem {
    id: string;
    time: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
  }

  defineProps<{
    selectedVenue: string;
    leftLegSymbol: string;
    rightLegSymbol: string;
    selectedResolution: string;
  }>();

  const activeTradeTab = ref<'open' | 'rollover'>('open');
  const balanceMode = ref<'gram_balance' | 'value_balance' | 'lot_balance' | 'custom_ratio'>('gram_balance');
  const selectedVenueState = ref('SHFE / XAUUSD');
  const selectedMainLegState = ref('SHFE.au2606');
  const selectedHedgeLegState = ref('XAUUSD');
  const selectedResolutionState = ref('30分钟');
  const selectedContract = ref('SHFE.au2606');
  const customMainRatio = ref('1.00');
  const customHedgeRatio = ref('1.00');
  const selectedAction = ref<'open' | 'close' | 'takeProfit' | 'gridOpen' | null>(null);
  const shfeLots = ref(0);
  const refreshing = ref(false);
  const executing = ref(false);
  const confirmVisible = ref(false);
  const tradingRuleRows = [
    { label: '手续费', value: '—' },
    {
      label: '交易时间',
      value: '沪金主力：09:00-11:30 / 13:30-15:00 / 21:00-02:30；XAUUSD+：工作日23H，北京时间05-06（冬）/ 06-07（夏）维护',
    },
    { label: '个人最高杠杆', value: '—' },
    { label: '每日最大回撤', value: '—' },
    { label: '其他限制', value: '—' },
  ] as const;

  const shfeLast = ref(1058.5);
  const xauLast = ref(4820.01);
  const spreadPercent = ref(0.199);
  const spreadCny = ref(2.11);
  const shfePosition = ref(0);
  const xauPosition = ref(0);
  const shfePositionValue = ref(0);
  const xauPositionValue = ref(0);

  const executionLogs = ref<LogItem[]>([
    { id: '1', time: '2026-03-18 15:44:45', type: 'success', message: '开仓成功，沪金下单量为2，伦敦金下单量为0.64' },
    { id: '2', time: '2026-03-18 15:44:45', type: 'success', message: 'MT5下单成功完成，成交数量: 0.64' },
    { id: '3', time: '2026-03-18 15:44:43', type: 'success', message: '策略开仓订单已完成，成交数量: 2，总成交数量: 2' },
    { id: '4', time: '2026-03-18 15:44:42', type: 'info', message: '发起执行策略开仓，沪金=2，伦敦金=0.64' },
  ]);

  const xauLots = computed(() => Number((shfeLots.value * 0.32).toFixed(2)));
  const xauGrams = computed(() => Number((xauLots.value * 3110.35).toFixed(2)));
  const shfeValueCny = computed(() => shfeLots.value * shfeLast.value * 1000);
  const xauValueUsd = computed(() => xauLots.value * xauLast.value);

  const formError = computed(() => {
    if (!selectedAction.value) return '请先选择策略动作';
    if (selectedAction.value === 'close' && shfePosition.value <= 0) return '当前无持仓，无法执行策略平仓';
    if (selectedAction.value !== 'close' && shfeLots.value <= 0) return '请输入有效的沪金手数';
    if (shfeLots.value > 62) return '输入数量超过当前可开手数';
    return '';
  });

  const canConfirm = computed(() => !formError.value && !!selectedAction.value);

  const actionText = computed(() => {
    if (selectedAction.value === 'open') return '策略开仓';
    if (selectedAction.value === 'close') return '策略平仓';
    if (selectedAction.value === 'takeProfit') return '止盈';
    if (selectedAction.value === 'gridOpen') return '网格开仓';
    return '--';
  });

  const balanceModeText = computed(() => {
    if (balanceMode.value === 'gram_balance') return '克数配平';
    if (balanceMode.value === 'value_balance') return '金额配平';
    if (balanceMode.value === 'lot_balance') return '手数配平';
    return '自定义比例';
  });

  const impact = computed(() => {
    const lots = shfeLots.value;
    return {
      availableBefore: 92.69,
      availableAfter: Math.max(0, 92.69 - lots * 0.05),
      leverageBefore: 1.4971,
      leverageAfter: 1.4971 + lots * 0.01,
      maxLeverage: 20,
      marginBefore: 0,
      marginAfter: lots * 0.001,
    };
  });

  function formatNumber(value: number, digits = 2) {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function handleShfeInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    shfeLots.value = Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0;
  }

  function setBalanceMode(mode: typeof balanceMode.value) {
    balanceMode.value = mode;
  }

  function setContract(contract: string) {
    selectedMainLegState.value = contract;
    selectedContract.value = contract;
    applyContractPreset();
  }

  function applyContractPreset() {
    if (selectedContract.value === 'SHFE.au2612') {
      shfeLast.value = 1075.42;
      spreadCny.value = 1.31;
      spreadPercent.value = 0.1115;
      return;
    }
    shfeLast.value = 1058.5;
    spreadCny.value = 2.11;
    spreadPercent.value = 0.199;
  }

  function applyTopbarMainLeg() {
    selectedContract.value = selectedMainLegState.value;
    applyContractPreset();
  }

  function prepareAction(action: 'open' | 'close' | 'takeProfit' | 'gridOpen') {
    selectedAction.value = action;
  }

  function clearLogs() {
    executionLogs.value = [];
  }

  function appendLog(type: LogItem['type'], message: string) {
    executionLogs.value.unshift({
      id: `${Date.now()}-${Math.random()}`,
      time: new Date().toLocaleString('zh-CN', { hour12: false }),
      type,
      message,
    });
  }

  function triggerRefresh() {
    refreshing.value = true;
    appendLog('info', '刷新中，正在同步 mock 行情与账户快照。');
    setTimeout(() => {
      refreshing.value = false;
      appendLog('success', '刷新完成，价格与风险指标已更新。');
    }, 640);
  }

  function executeTrade() {
    if (!canConfirm.value) return;
    executing.value = true;
    setTimeout(() => {
      appendLog('success', `${actionText.value}已提交，等待撮合与对冲确认。`);
      confirmVisible.value = false;
      executing.value = false;
    }, 720);
  }
</script>

<style scoped lang="less">
  .domestic-replica {
    display: flex;
    flex-direction: column;
    gap: 12px;
    color: #172847;
    background: #f8fafc;
  }

  .domestic-topbar,
  .hero-left,
  .hero-right,
  .block-card,
  .right-column {
    min-width: 0;
    border: 1px solid #e7ebf0;
    border-radius: 16px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
  }

  .domestic-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 48px;
    padding: 8px 12px;
    border-radius: var(--strategy-radius-card);
  }

  .domestic-topbar__left,
  .domestic-topbar__right,
  .account-head,
  .trade-head,
  .trade-tabs,
  .selector-row,
  .selector-left,
  .confirm-row {
    display: flex;
    align-items: center;
  }

  .domestic-topbar__left,
  .selector-left {
    gap: var(--strategy-space-1);
    flex-wrap: wrap;
  }

  .topbar-control {
    display: inline-flex;
    align-items: center;
    gap: var(--strategy-space-1);
    min-width: 0;
    flex: 0 0 auto;
  }

  .topbar-control span {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
    letter-spacing: 0;
    white-space: nowrap;
  }

  .topbar-control select {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    min-width: 88px;
    width: auto;
    box-shadow: var(--strategy-shadow-soft);
  }

  .menu-btn,
  .refresh-btn,
  .gear-btn {
    border: 1px solid #dbe2ed;
    background: #fff;
    color: #60708c;
    cursor: pointer;
  }

  .menu-btn {
    width: 30px;
    height: 30px;
    border-radius: 8px;
  }

  .strategy-select,
  .selector-left select,
  .leg-panel input {
    border: 1px solid #d9e2ed;
    border-radius: 10px;
    background: #fff;
    outline: none;
    color: #425470;
  }

  .strategy-select {
    min-width: 340px;
    height: 32px;
    padding: 0 10px;
  }

  .selector-chip,
  .meta-chip,
  .gear-btn {
    min-height: 42px;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #fff;
  }

  .selector-chip,
  .meta-chip {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 0 14px;
  }

  .selector-chip span,
  .meta-chip span {
    color: #556274;
    font-size: 14px;
    font-weight: 600;
  }

  .selector-chip strong,
  .meta-chip strong {
    color: #111827;
    font-size: 15px;
    font-weight: 700;
  }

  .gear-btn {
    width: 42px;
    padding: 0;
    border-radius: 12px;
  }

  .domestic-topbar__right {
    color: #2d3d58;
    font-size: 13px;
  }

  .hero-grid {
    display: grid;
    grid-template-columns: 1.06fr 1fr;
    gap: 0;
  }

  .hero-left {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0;
    padding: 20px 20px 18px;
  }

  .gauge-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    min-height: 228px;
  }

  .gauge-shell {
    position: relative;
    width: 178px;
    height: 92px;
    overflow: hidden;
    border-radius: 178px 178px 0 0;
    background: conic-gradient(from 180deg at 50% 100%, #3a98f6 0 36%, #ffb31f 36% 70%, #f0f4f8 70% 100%);
  }

  .gauge-shell--position {
    background: conic-gradient(from 180deg at 50% 100%, #1fbb72 0 68%, #d73535 68% 100%);
  }

  .gauge-core {
    position: absolute;
    left: 50%;
    bottom: -2px;
    width: 118px;
    height: 60px;
    transform: translateX(-50%);
    border-radius: 118px 118px 0 0;
    background: #fff;
  }

  .gauge-needle {
    position: absolute;
    left: 50%;
    bottom: 8px;
    width: 3px;
    height: 66px;
    transform-origin: bottom center;
    border-radius: 999px;
  }

  .gauge-needle::after {
    content: '';
    position: absolute;
    left: 50%;
    bottom: -4px;
    width: 10px;
    height: 10px;
    transform: translateX(-50%);
    border-radius: 999px;
    background: currentColor;
  }

  .gauge-needle--blue {
    color: #2f8cf0;
    background: #2f8cf0;
    transform: translateX(-50%) rotate(10deg);
  }

  .gauge-needle--green {
    color: #1eb26f;
    background: #1eb26f;
    transform: translateX(-50%) rotate(42deg);
  }

  .gauge-meta,
  .position-balance {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    max-width: 230px;
    font-size: 12px;
  }

  .gauge-meta strong,
  .position-balance__text strong {
    display: block;
    margin-top: 4px;
    color: #1b2c49;
    font-size: 14px;
    font-weight: 700;
  }

  .gauge-caption {
    color: #556b87;
    font-size: 13px;
    font-weight: 700;
  }

  .position-balance__text {
    text-align: center;
  }

  .position-balance__text small {
    display: block;
    margin-top: 4px;
    color: #7789a4;
  }

  .hero-right {
    padding: 12px 14px 12px;
  }

  .account-head {
    justify-content: space-between;
    margin-bottom: 10px;
    color: #233654;
    font-size: 13px;
    font-weight: 700;
  }

  .refresh-btn {
    height: var(--strategy-control-height);
    padding: 0 12px;
    border-radius: var(--strategy-radius-control);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  .account-rows {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .account-row {
    display: grid;
    grid-template-columns: 74px 1.4fr 0.7fr 0.7fr 0.7fr;
    gap: 12px;
    padding: 14px;
    background: #ffffff;
  }

  .account-row--blue {
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .account-row--yellow {
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .account-row__label {
    display: flex;
    align-items: center;
    color: #243552;
    font-size: 18px;
    font-weight: 500;
  }

  .account-row__item span,
  .leg-panel__stats span,
  .leg-panel__entry span,
  .impact-card span {
    color: #5e7390;
    font-size: 13px;
    font-weight: 700;
  }

  .account-row__item strong,
  .impact-card strong {
    display: block;
    margin-top: 4px;
    color: #1b2c49;
    font-size: 17px;
    font-weight: 700;
  }

  .account-row__item small {
    display: block;
    margin-top: 4px;
    color: #7c8ca6;
    font-size: 11px;
  }

  .account-row__item--wide {
    grid-column: span 2;
  }

  .progress-line {
    position: relative;
    height: 16px;
    margin-top: 8px;
    overflow: hidden;
    border-radius: 999px;
    background: #dbe5f0;
  }

  .progress-line i {
    position: absolute;
    inset: 0 auto 0 0;
    border-radius: inherit;
    background: #31ba72;
  }

  .progress-line em {
    position: relative;
    display: block;
    padding-right: 8px;
    color: #fff;
    font-size: 11px;
    font-style: normal;
    line-height: 16px;
    text-align: right;
  }

  .main-board {
    display: grid;
    grid-template-columns: 322px 1fr;
    gap: 12px;
  }

  .left-column,
  .right-column {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .block-card {
    padding: 14px;
  }

  .block-title {
    color: #182a47;
    font-size: 19px;
    font-weight: 900;
  }

  .block-title--between {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 16px;
  }

  .inline-link {
    border: none;
    background: transparent;
    color: #5a7090;
    cursor: pointer;
    font-weight: 700;
  }

  .rule-list {
    display: grid;
    gap: 10px;
    margin-top: 10px;
  }

  .rule-list__row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    min-height: 42px;
    padding: 0 12px;
    border: 1px solid #eef2f6;
    border-radius: 10px;
    background: #fff;
  }

  .rule-list__label {
    color: #5f7390;
    font-size: 13px;
    font-weight: 700;
  }

  .rule-list__value {
    color: #37485f;
    font-size: 12px;
    font-weight: 700;
    text-align: right;
    line-height: 1.45;
  }

  .log-list {
    max-height: 216px;
    margin-top: 10px;
    overflow: auto;
  }

  .log-list p {
    display: flex;
    gap: 8px;
    margin: 0;
    padding: 6px 0;
    color: #37485f;
    font-size: 12px;
    line-height: 1.55;
  }

  .log-dot {
    width: 8px;
    height: 8px;
    margin-top: 5px;
    flex: none;
    border-radius: 999px;
  }

  .is-success {
    background: #22b55e;
  }

  .is-info {
    background: #60a5fa;
  }

  .is-warning {
    background: #f59e0b;
  }

  .is-error {
    background: #ef4444;
  }

  .right-column {
    padding: 14px 16px 16px;
  }

  .trade-head {
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;
  }

  .trade-tabs {
    gap: 0;
  }

  .trade-tabs button {
    min-width: 88px;
    height: var(--strategy-tab-height);
    border: 1px solid var(--strategy-border-strong);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.01em;
    cursor: pointer;
  }

  .trade-tabs button:first-child {
    border-radius: 12px 0 0 12px;
  }

  .trade-tabs button:last-child {
    border-radius: 0 12px 12px 0;
  }

  .trade-tabs button.active {
    border-color: var(--strategy-accent-soft);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .trade-quote-strip {
    display: flex;
    align-items: center;
    gap: 18px;
    color: #4e6180;
    font-size: 14px;
  }

  .blue {
    color: #4281ff;
  }

  .red {
    color: #d63a3a;
  }

  .green {
    color: #1ba45b;
  }

  .orange {
    color: #ef8a15;
  }

  .selector-row {
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 10px;
  }

  .selector-toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .selector-group {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .selector-group > span {
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.01em;
    white-space: nowrap;
  }

  .balance-tabs,
  .contract-tabs {
    display: flex;
    align-items: center;
    gap: 0;
    flex-wrap: wrap;
  }

  .balance-tabs button,
  .contract-tabs button {
    min-width: 84px;
    height: 42px;
    padding: 0 14px;
    border: 1px solid #d7e2ef;
    background: #fff;
    color: #47617f;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.01em;
    cursor: pointer;
  }

  .balance-tabs button:first-child,
  .contract-tabs button:first-child {
    border-radius: 12px 0 0 12px;
  }

  .balance-tabs button:last-child,
  .contract-tabs button:last-child {
    border-radius: 0 12px 12px 0;
  }

  .balance-tabs button:not(:first-child),
  .contract-tabs button:not(:first-child) {
    margin-left: -1px;
  }

  .balance-tabs button.active,
  .contract-tabs button.active {
    border-color: rgba(220, 82, 82, 0.38);
    background: linear-gradient(180deg, #ff6868 0%, #ef4343 100%);
    color: #fff;
    position: relative;
    z-index: 1;
  }

  .custom-ratio-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 180px));
    gap: 12px;
    margin-bottom: 10px;
  }

  .custom-ratio-field {
    display: grid;
    gap: 6px;
  }

  .custom-ratio-field span {
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.01em;
  }

  .custom-ratio-field input,
  .selector-right,
  .leg-panel input {
    height: 42px;
    padding: 0 12px;
    border: 1px solid #d9e2ed;
    border-radius: 10px;
    background: #fff;
    color: #13233f;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }

  .selector-right {
    min-width: 132px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    font-variant-numeric: tabular-nums;
  }

  .legs-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .leg-panel {
    min-height: 208px;
    padding: 16px 18px;
    border: 1px solid #ede9e2;
    border-radius: 16px;
    background: linear-gradient(180deg, #ffffff 0%, #f4f8fb 100%);
  }

  .leg-panel__stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 16px;
  }

  .leg-panel__stats strong {
    display: block;
    margin-top: 4px;
    color: #1b2c49;
    font-size: 28px;
    line-height: 1.08;
    font-weight: 800;
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
  }

  .leg-panel__entry label {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .entry-meta,
  .leg-hint {
    margin-top: 8px;
    color: #627793;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.01em;
  }

  .action-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin-top: 14px;
  }

  .action-btn {
    min-width: 0;
    height: 46px;
    padding: 0 18px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.01em;
    cursor: pointer;
  }

  .action-btn.active {
    border-color: var(--strategy-accent-soft);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .impact-board {
    margin-top: 14px;
  }

  .impact-title {
    margin-bottom: 10px;
    color: #1d2e4a;
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.012em;
  }

  .impact-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .impact-card {
    min-height: 88px;
    padding: 14px 16px;
    border: 1px solid #ede9e2;
    border-radius: 14px;
    background: linear-gradient(180deg, #ffffff 0%, #f4f8fb 100%);
  }

  .impact-card span {
    display: block;
    margin-bottom: 8px;
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.01em;
  }

  .impact-card strong {
    color: #1f314d;
    font-size: 20px;
    font-weight: 800;
    font-style: normal;
    line-height: 1.2;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
  }

  .impact-card em {
    margin-left: 4px;
    font-style: normal;
  }

  .confirm-row {
    justify-content: center;
    margin-top: 14px;
  }

  .confirm-row button {
    min-width: 176px;
    height: 44px;
    border: 1px solid #ebe8e1;
    border-radius: 12px;
    background: #fff;
    color: #526682;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.01em;
    cursor: pointer;
  }

  .confirm-row button:enabled {
    border-color: rgba(220, 82, 82, 0.38);
    background: linear-gradient(180deg, #ff6868 0%, #ef4343 100%);
    color: #fff;
  }

  .trade-modal {
    position: fixed;
    inset: 0;
    z-index: 1200;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(11, 21, 42, 0.28);
  }

  .trade-modal__dialog {
    width: min(560px, calc(100vw - 32px));
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 30px 60px rgba(20, 36, 63, 0.24);
  }

  .trade-modal__header,
  .trade-modal__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 18px;
  }

  .trade-modal__header {
    border-bottom: 1px solid #eef2f6;
  }

  .trade-modal__body {
    padding: 16px 18px 20px;
  }

  .trade-modal__eyebrow {
    display: none;
  }

  .trade-modal__header h3 {
    margin: 0;
    color: #1b2c49;
    font-size: 18px;
  }

  .trade-modal__close {
    border: none;
    background: transparent;
    color: #60708c;
    font-size: 24px;
    cursor: pointer;
  }

  .confirm-lines p {
    margin: 0 0 10px;
    color: #43536d;
    font-size: 14px;
  }

  .modal-btn {
    height: 38px;
    padding: 0 16px;
    border: 1px solid #e0e6ef;
    border-radius: 8px;
    cursor: pointer;
  }

  .modal-btn--ghost {
    background: #fff;
    color: #566883;
  }

  .modal-btn--primary {
    border-color: #d73b3b;
    background: #d73b3b;
    color: #fff;
  }

  .domestic-execution {
    color: var(--strategy-text-1);
    background: var(--strategy-bg);
    font-family: var(--strategy-font-sans);
  }

  .domestic-topbar,
  .hero-left,
  .hero-right,
  .block-card,
  .right-column,
  .leg-panel,
  .impact-card,
  .trade-modal__dialog {
    border-color: var(--strategy-border);
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
  }

  .menu-btn,
  .refresh-btn,
  .selector-chip,
  .meta-chip,
  .gear-btn,
  .strategy-select,
  .selector-left select,
  .leg-panel input,
  .trade-tabs button,
  .action-btn,
  .modal-btn {
    border-color: var(--strategy-border-strong);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
  }

  .trade-tabs .is-active,
  .modal-btn--primary {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
    border-color: var(--strategy-accent-soft);
  }

  .account-head,
  .trade-head h3,
  .trade-modal__header h3,
  .gauge-meta strong,
  .position-balance__text strong {
    color: var(--strategy-text-1);
  }

  .domestic-topbar__right,
  .gauge-caption,
  .position-balance__text small,
  .account-row,
  .trade-modal__eyebrow,
  .confirm-lines p {
    color: var(--strategy-text-3);
  }

  @media (max-width: 1400px) {
    .hero-grid,
    .main-board,
    .legs-grid,
    .impact-grid {
      grid-template-columns: 1fr;
    }

    .hero-left {
      grid-template-columns: 1fr;
    }

    .action-row {
      grid-template-columns: 1fr 1fr;
    }

    .trade-head,
    .selector-row,
    .domestic-topbar {
      flex-direction: column;
      align-items: flex-start;
      height: auto;
      gap: 10px;
    }
  }

  @media (max-width: 1100px) {
    .account-row,
    .leg-panel__stats,
    .action-row {
      grid-template-columns: 1fr 1fr;
    }

    .strategy-select {
      min-width: 0;
      width: 100%;
    }

    .topbar-control {
      width: 100%;
    }
  }

  @media (max-width: 760px) {
    .account-row,
    .leg-panel__stats,
    .action-row,
    .impact-grid {
      grid-template-columns: 1fr;
    }

    .account-row__item--wide {
      grid-column: span 1;
    }
  }
</style>
