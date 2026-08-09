<template>
  <section class="domestic-execution" data-testid="domestic-overseas-execution-workspace">
    <header class="domestic-execution__topbar">
      <label>
        <span>交易场景</span>
        <select v-model="selectedVenueState">
          <option>SHFE / XAUUSD</option>
          <option>AU9999 / XAUUSD</option>
        </select>
      </label>
      <label>
        <span>国内品种</span>
        <select v-model="selectedMainLegState" @change="applyContractPreset">
          <option>SHFE.au2604</option>
          <option>SHFE.au2606</option>
          <option>SHFE.au2612</option>
          <option>AU9999</option>
        </select>
      </label>
      <label>
        <span>海外品种</span>
        <select v-model="selectedHedgeLegState">
          <option>XAUUSD</option>
        </select>
      </label>
      <label>
        <span>时间精度</span>
        <select v-model="selectedResolutionState">
          <option>30分钟</option>
          <option>1小时</option>
          <option>4小时</option>
        </select>
      </label>
    </header>

    <section class="hero-grid" data-testid="domestic-account-overview">
      <section class="hero-left">
        <article class="gauge-card" data-testid="domestic-asset-gauge">
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
        <article class="gauge-card" data-testid="domestic-position-gauge">
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
          <button type="button" :disabled="refreshing" @click="refreshState">
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
    </section>

    <section class="execution-board">
      <aside class="side-column">
        <section class="panel">
          <h3>交易规则</h3>
          <dl class="rule-list">
            <div v-for="item in tradingRules" :key="item.label">
              <dt>{{ item.label }}</dt>
              <dd>{{ item.value }}</dd>
            </div>
          </dl>
        </section>

        <section class="panel">
          <header class="panel-header">
            <h3>执行反馈</h3>
            <button type="button" @click="executionLogs = []">清空</button>
          </header>
          <div class="log-list" data-testid="domestic-execution-log">
            <p v-for="item in executionLogs" :key="item.id">
              <i :class="`is-${item.tone}`"></i>
              <span>{{ item.time }}：{{ item.message }}</span>
            </p>
          </div>
        </section>
      </aside>

      <section class="trade-panel">
        <header class="trade-head">
          <div class="trade-tabs">
            <button
              type="button"
              :class="{ active: activeTradeTab === 'open' }"
              @click="activeTradeTab = 'open'"
            >
              开仓
            </button>
            <button
              type="button"
              :class="{ active: activeTradeTab === 'rollover' }"
              @click="activeTradeTab = 'rollover'"
            >
              移仓
            </button>
          </div>
          <div class="quote-strip">
            <span>{{ selectedMainLegState }} {{ shfeLast.toFixed(2) }}</span>
            <span>{{ selectedHedgeLegState }} {{ xauLast.toFixed(2) }}</span>
            <strong>{{ spreadPercent.toFixed(4) }}% / {{ spreadCny.toFixed(2) }} CNY</strong>
          </div>
        </header>

        <div class="selector-toolbar">
          <div>
            <span>配平方式</span>
            <div class="button-group">
              <button
                v-for="item in balanceModes"
                :key="item.key"
                type="button"
                :class="{ active: balanceMode === item.key }"
                @click="balanceMode = item.key"
              >
                {{ item.label }}
              </button>
            </div>
          </div>
          <div>
            <span>国内合约</span>
            <div class="button-group">
              <button
                v-for="item in domesticContracts"
                :key="item.value"
                type="button"
                :class="{ active: selectedMainLegState === item.value }"
                @click="setContract(item.value)"
              >
                {{ item.label }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="balanceMode === 'custom_ratio'" class="custom-ratio">
          <label
            ><span>国内比例</span
            ><input v-model="customMainRatio" type="number" min="0" step="0.01"
          /></label>
          <label
            ><span>海外比例</span
            ><input v-model="customHedgeRatio" type="number" min="0" step="0.01"
          /></label>
        </div>

        <div class="legs-grid">
          <article class="leg-panel">
            <h3>国内交易腿</h3>
            <div class="leg-stats">
              <div><span>方向</span><strong class="positive">买入</strong></div>
              <div
                ><span>最新价</span><strong>{{ shfeLast.toFixed(2) }}</strong></div
              >
              <div
                ><span>当前持仓</span><strong>{{ shfePosition }}</strong></div
              >
            </div>
            <label class="lot-field">
              <span>数量（1000克/手）</span>
              <input :value="shfeLots || ''" @input="handleLotsInput" />
            </label>
            <p>价值 {{ formatNumber(shfeValueCny, 0) }} CNY，可开约 62 手。</p>
          </article>

          <article class="leg-panel">
            <h3>海外交易腿</h3>
            <div class="leg-stats">
              <div><span>方向</span><strong class="negative">卖出</strong></div>
              <div
                ><span>最新价</span><strong>{{ xauLast.toFixed(2) }}</strong></div
              >
              <div
                ><span>当前持仓</span><strong>{{ xauPosition }}</strong></div
              >
            </div>
            <label class="lot-field">
              <span>数量（3110.35克/手）</span>
              <input :value="xauLots.toFixed(2)" readonly />
            </label>
            <p>价值 {{ formatNumber(xauValueUsd, 0) }} USD，克数 {{ xauGrams.toFixed(0) }}。</p>
          </article>
        </div>

        <div class="action-row">
          <button
            v-for="item in actionButtons"
            :key="item.key"
            type="button"
            :class="{ active: selectedAction === item.key }"
            @click="selectedAction = item.key"
          >
            {{ item.label }}
          </button>
        </div>

        <section class="impact-panel">
          <h3>执行后影响</h3>
          <div class="impact-grid">
            <article>
              <span>可用资金率</span>
              <strong>92.69% → {{ impact.availableAfter.toFixed(2) }}%</strong>
            </article>
            <article>
              <span>整体杠杆</span>
              <strong>1.4971 → {{ impact.leverageAfter.toFixed(4) }}</strong>
            </article>
            <article>
              <span>预付款比例</span>
              <strong>0.0000% → {{ impact.marginAfter.toFixed(4) }}%</strong>
            </article>
            <article>
              <span>费用估算</span>
              <strong>{{ estimatedFee }} CNY</strong>
            </article>
          </div>
        </section>

        <section class="risk-panel">
          <h3>风险检查</h3>
          <div class="risk-grid">
            <span class="passed">资金可用</span>
            <span class="passed">汇率偏离可控</span>
            <span :class="formError ? 'blocked' : 'passed'">{{ formError || '数量检查通过' }}</span>
          </div>
        </section>

        <div class="confirm-row">
          <button
            data-testid="domestic-submit-review"
            type="button"
            :disabled="!canConfirm || executing"
            @click="confirmVisible = true"
          >
            {{ executing ? '生成中' : '提交复核' }}
          </button>
        </div>
      </section>
    </section>

    <section class="result-panel">
      <header>
        <h3>委托与成交</h3>
        <div class="table-tabs">
          <button
            v-for="item in tableTabs"
            :key="item.key"
            type="button"
            :class="{ active: activeTable === item.key }"
            @click="activeTable = item.key"
          >
            {{ item.label }}
          </button>
        </div>
      </header>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th v-for="column in activeColumns" :key="column.key">{{ column.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in activeRows" :key="index">
              <td v-for="column in activeColumns" :key="column.key">{{ row[column.key] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="confirmVisible" class="trade-modal" @click.self="confirmVisible = false">
      <div class="trade-modal__dialog">
        <header>
          <h3>提交复核</h3>
          <button type="button" @click="confirmVisible = false">×</button>
        </header>
        <div class="confirm-lines">
          <p>策略：海内外黄金价差</p>
          <p>操作：{{ actionLabel }}</p>
          <p>配平：{{ balanceModeLabel }}</p>
          <p>国内：{{ selectedMainLegState }} / {{ shfeLots }} 手 / {{ shfeLast.toFixed(2) }}</p>
          <p
            >海外：{{ selectedHedgeLegState }} / {{ xauLots.toFixed(2) }} 手 /
            {{ xauLast.toFixed(2) }}</p
          >
          <p>汇率：{{ fxRate.toFixed(4) }}</p>
          <p>价差：{{ spreadPercent.toFixed(4) }}% / {{ spreadCny.toFixed(2) }} CNY</p>
        </div>
        <footer>
          <button type="button" @click="confirmVisible = false">取消</button>
          <button type="button" :disabled="executing" @click="submitExecution">提交复核</button>
        </footer>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';

  type BalanceMode = 'gram_balance' | 'value_balance' | 'lot_balance' | 'custom_ratio';
  type ActionKey = 'open' | 'close' | 'takeProfit' | 'gridOpen';
  type TableKey = 'positions' | 'orders' | 'fills' | 'logs';

  interface LogItem {
    id: string;
    time: string;
    tone: 'info' | 'warning';
    message: string;
  }

  interface TableColumn {
    key: string;
    label: string;
  }

  const props = withDefaults(
    defineProps<{
      selectedVenue?: string;
      leftLegSymbol?: string;
      rightLegSymbol?: string;
      selectedResolution?: string;
    }>(),
    {
      selectedVenue: 'SHFE / XAUUSD',
      leftLegSymbol: 'SHFE.au2606',
      rightLegSymbol: 'XAUUSD',
      selectedResolution: '30分钟',
    },
  );

  const activeTradeTab = ref<'open' | 'rollover'>('open');
  const balanceMode = ref<BalanceMode>('gram_balance');
  const selectedAction = ref<ActionKey | null>(null);
  const selectedVenueState = ref(props.selectedVenue);
  const selectedMainLegState = ref(props.leftLegSymbol);
  const selectedHedgeLegState = ref(props.rightLegSymbol);
  const selectedResolutionState = ref(props.selectedResolution);
  const customMainRatio = ref('1.00');
  const customHedgeRatio = ref('1.00');
  const shfeLots = ref(0);
  const refreshing = ref(false);
  const executing = ref(false);
  const confirmVisible = ref(false);
  const activeTable = ref<TableKey>('positions');

  const shfeLast = ref(1058.5);
  const xauLast = ref(4820.01);
  const fxRate = ref(6.8214);
  const spreadPercent = ref(0.199);
  const spreadCny = ref(2.11);
  const shfePosition = ref(0);
  const xauPosition = ref(0);

  const balanceModes: Array<{ key: BalanceMode; label: string }> = [
    { key: 'gram_balance', label: '克数配平' },
    { key: 'value_balance', label: '金额配平' },
    { key: 'lot_balance', label: '手数配平' },
    { key: 'custom_ratio', label: '自定义比例' },
  ];

  const domesticContracts = [
    { value: 'SHFE.au2604', label: '沪金2604' },
    { value: 'SHFE.au2606', label: '沪金2606' },
    { value: 'SHFE.au2612', label: '沪金2612' },
    { value: 'SHFE.au2704', label: '沪金2704' },
  ];

  const actionButtons: Array<{ key: ActionKey; label: string }> = [
    { key: 'open', label: '策略开仓' },
    { key: 'close', label: '策略平仓' },
    { key: 'takeProfit', label: '止盈' },
    { key: 'gridOpen', label: '网格开仓' },
  ];

  const tradingRules = [
    { label: '手续费', value: '按国内期货与海外 CFD 账户规则估算' },
    { label: '交易时间', value: 'SHFE 日夜盘 / XAUUSD 工作日 23H' },
    { label: '个人最高杠杆', value: '20X' },
    { label: '每日最大回撤', value: '2.50%' },
    { label: '其他限制', value: '汇率偏离、两侧流动性和保证金同步检查' },
  ];

  const executionLogs = ref<LogItem[]>([
    {
      id: 'log-1',
      time: '2026-03-18 15:44:45',
      tone: 'info',
      message: '海内外价差执行工作台已准备，等待复核。',
    },
    {
      id: 'log-2',
      time: '2026-03-18 15:44:42',
      tone: 'warning',
      message: '真实执行接口未接入，提交后仅生成本地待复核记录。',
    },
  ]);

  const tableTabs: Array<{ key: TableKey; label: string }> = [
    { key: 'positions', label: '当前持仓' },
    { key: 'orders', label: '历史订单' },
    { key: 'fills', label: '成交记录' },
    { key: 'logs', label: '执行记录' },
  ];

  const tables = ref<Record<TableKey, { columns: TableColumn[]; rows: Record<string, string>[] }>>({
    positions: {
      columns: [
        { key: 'symbol', label: '标的' },
        { key: 'direction', label: '方向' },
        { key: 'size', label: '数量' },
        { key: 'entry', label: '持仓价差' },
        { key: 'mark', label: '当前价差' },
        { key: 'pnl', label: '未实现盈亏' },
      ],
      rows: [
        {
          symbol: 'SHFE.au2606 / XAUUSD',
          direction: '多 / 空',
          size: '2.00 手 / 0.64 手',
          entry: '1.06 CNY',
          mark: '1.18 CNY',
          pnl: '+3,870 CNY',
        },
      ],
    },
    orders: {
      columns: [
        { key: 'time', label: '时间' },
        { key: 'action', label: '动作' },
        { key: 'spread', label: '价差' },
        { key: 'status', label: '状态' },
      ],
      rows: [
        { time: '10:18:30', action: '策略开仓', spread: '1.18 CNY', status: '待复核' },
        { time: '09:52:15', action: '策略平仓', spread: '0.82 CNY', status: '监控中' },
      ],
    },
    fills: {
      columns: [
        { key: 'orderId', label: '记录号' },
        { key: 'leg', label: '腿别' },
        { key: 'price', label: '参考价' },
        { key: 'size', label: '数量' },
        { key: 'time', label: '时间' },
      ],
      rows: [
        {
          orderId: 'DO-REVIEW-2606',
          leg: '国内腿',
          price: '1,058.50',
          size: '2.00',
          time: '待复核',
        },
        {
          orderId: 'DO-REVIEW-XAU',
          leg: '海外腿',
          price: '4,820.01',
          size: '0.64',
          time: '待复核',
        },
      ],
    },
    logs: {
      columns: [
        { key: 'time', label: '时间' },
        { key: 'type', label: '类别' },
        { key: 'content', label: '内容' },
      ],
      rows: [
        { time: '10:21:56', type: '刷新', content: '价差、汇率、配平手数已同步。' },
        { time: '10:14:09', type: '预警', content: '汇率腿偏移接近预警阈值。' },
      ],
    },
  });

  const xauLots = computed(() => Number((shfeLots.value * 0.32).toFixed(2)));
  const xauGrams = computed(() => Number((xauLots.value * 3110.35).toFixed(2)));
  const shfeValueCny = computed(() => shfeLots.value * shfeLast.value * 1000);
  const xauValueUsd = computed(() => xauLots.value * xauLast.value);
  const estimatedFee = computed(() => formatNumber(shfeLots.value * 78.5 + xauLots.value * 42, 2));

  const impact = computed(() => ({
    availableAfter: Math.max(0, 92.69 - shfeLots.value * 0.05),
    leverageAfter: 1.4971 + shfeLots.value * 0.01,
    marginAfter: shfeLots.value * 0.001,
  }));

  const formError = computed(() => {
    if (!selectedAction.value) return '请选择策略动作';
    if (selectedAction.value === 'close' && shfePosition.value <= 0)
      return '当前无持仓，无法执行策略平仓';
    if (selectedAction.value !== 'close' && shfeLots.value <= 0) return '请输入有效的国内手数';
    if (shfeLots.value > 62) return '输入数量超过当前可开手数';
    return '';
  });

  const canConfirm = computed(() => !formError.value && !!selectedAction.value);
  const activeColumns = computed(() => tables.value[activeTable.value].columns);
  const activeRows = computed(() => tables.value[activeTable.value].rows);

  const actionLabel = computed(
    () => actionButtons.find((item) => item.key === selectedAction.value)?.label || '--',
  );
  const balanceModeLabel = computed(
    () => balanceModes.find((item) => item.key === balanceMode.value)?.label || '--',
  );

  watch(
    () => props.selectedVenue,
    (value) => {
      selectedVenueState.value = value;
    },
    { immediate: true },
  );
  watch(
    () => props.leftLegSymbol,
    (value) => {
      selectedMainLegState.value = value;
    },
    { immediate: true },
  );
  watch(
    () => props.rightLegSymbol,
    (value) => {
      selectedHedgeLegState.value = value;
    },
    { immediate: true },
  );
  watch(
    () => props.selectedResolution,
    (value) => {
      selectedResolutionState.value = value;
    },
    { immediate: true },
  );

  function formatNumber(value: number, digits = 2) {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function handleLotsInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    shfeLots.value = Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0;
  }

  function setContract(contract: string) {
    selectedMainLegState.value = contract;
    applyContractPreset();
  }

  function applyContractPreset() {
    if (selectedMainLegState.value === 'SHFE.au2612') {
      shfeLast.value = 1075.42;
      spreadCny.value = 1.31;
      spreadPercent.value = 0.124;
      return;
    }

    if (selectedMainLegState.value === 'SHFE.au2704') {
      shfeLast.value = 1082.9;
      spreadCny.value = 3.42;
      spreadPercent.value = 0.322;
      return;
    }

    shfeLast.value = selectedMainLegState.value === 'SHFE.au2604' ? 1054.2 : 1058.5;
    spreadCny.value = selectedMainLegState.value === 'SHFE.au2604' ? 0.86 : 2.11;
    spreadPercent.value = selectedMainLegState.value === 'SHFE.au2604' ? 0.081 : 0.199;
  }

  function nowText() {
    return new Date().toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-');
  }

  function refreshState() {
    refreshing.value = true;
    window.setTimeout(() => {
      refreshing.value = false;
      executionLogs.value.unshift({
        id: `log-${Date.now()}`,
        time: nowText(),
        tone: 'info',
        message: '账户、汇率和两侧价格已刷新。',
      });
    }, 360);
  }

  function submitExecution() {
    if (!canConfirm.value) return;
    executing.value = true;
    window.setTimeout(() => {
      const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
      tables.value.orders.rows.unshift({
        time,
        action: actionLabel.value,
        spread: `${spreadCny.value.toFixed(2)} CNY`,
        status: '待复核',
      });
      tables.value.logs.rows.unshift({
        time,
        type: '复核',
        content: `${actionLabel.value}复核记录已生成，状态为待复核。`,
      });
      executionLogs.value.unshift({
        id: `log-${Date.now()}`,
        time: nowText(),
        tone: 'info',
        message: `${actionLabel.value}复核记录已生成，状态为待复核。`,
      });
      activeTable.value = 'orders';
      confirmVisible.value = false;
      executing.value = false;
    }, 320);
  }
</script>

<style scoped lang="less">
  .domestic-execution {
    display: flex;
    flex-direction: column;
    gap: 12px;
    color: var(--strategy-text-1);
    background: var(--strategy-bg);
    font-family: var(--strategy-font-sans);
  }

  .domestic-execution__topbar,
  .hero-left,
  .hero-right,
  .panel,
  .trade-panel,
  .result-panel {
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: linear-gradient(
      180deg,
      var(--strategy-surface) 0%,
      var(--strategy-surface-soft) 100%
    );
    box-shadow: var(--strategy-shadow);
  }

  .domestic-execution__topbar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    padding: 8px 12px;
  }

  label,
  .selector-toolbar > div,
  .lot-field {
    display: grid;
    gap: 6px;
  }

  .domestic-execution__topbar label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  label span,
  .selector-toolbar span,
  .leg-stats span,
  .impact-grid span,
  .rule-list dt {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
  }

  select,
  input,
  button {
    height: var(--strategy-control-height);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  button {
    cursor: pointer;
    padding: 0 14px;
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }

  .hero-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.06fr) minmax(560px, 1fr);
    gap: 12px;
  }

  .hero-left {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0;
    min-width: 0;
    padding: 12px 16px;
  }

  .panel-header,
  .trade-head,
  .result-panel header,
  .trade-modal__dialog header,
  .trade-modal__dialog footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .result-panel header {
    margin-bottom: 12px;
  }

  dl,
  .rule-list {
    margin: 0;
  }

  .rule-list {
    display: grid;
    gap: 8px;
    width: 100%;
    padding: 0 12px 12px;
  }

  .rule-list div {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  dd {
    margin: 0;
    color: var(--strategy-text-1);
    font-weight: 800;
  }

  h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .gauge-card {
    display: flex;
    min-height: 206px;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 10px;
    padding: 0 16px;
  }

  .gauge-card + .gauge-card {
    border-left: 1px solid var(--strategy-border-soft);
  }

  .gauge-shell {
    position: relative;
    width: 178px;
    height: 92px;
    overflow: hidden;
    border-radius: 178px 178px 0 0;
    background: conic-gradient(
      from 180deg at 50% 100%,
      #3a98f6 0 36%,
      #ffb31f 36% 70%,
      #f0f4f8 70% 100%
    );
  }

  .gauge-shell--position {
    background: conic-gradient(from 180deg at 50% 100%, #1fbb72 0 68%, #d73535 68% 100%);
  }

  .gauge-core {
    position: absolute;
    bottom: -2px;
    left: 50%;
    width: 118px;
    height: 60px;
    border-radius: 118px 118px 0 0;
    background: var(--strategy-surface);
    transform: translateX(-50%);
  }

  .gauge-needle {
    position: absolute;
    bottom: 8px;
    left: 50%;
    width: 3px;
    height: 66px;
    border-radius: 999px;
    transform-origin: bottom center;
  }

  .gauge-needle::after {
    position: absolute;
    bottom: -4px;
    left: 50%;
    width: 10px;
    height: 10px;
    border-radius: 999px;
    background: currentColor;
    content: '';
    transform: translateX(-50%);
  }

  .gauge-needle--blue {
    background: #2f8cf0;
    color: #2f8cf0;
    transform: translateX(-50%) rotate(10deg);
  }

  .gauge-needle--green {
    background: #1eb26f;
    color: #1eb26f;
    transform: translateX(-50%) rotate(42deg);
  }

  .gauge-meta,
  .position-balance {
    display: flex;
    width: 100%;
    max-width: 230px;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
  }

  .gauge-meta strong,
  .position-balance__text strong {
    display: block;
    margin-top: 4px;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 800;
  }

  .position-balance__text {
    text-align: center;
  }

  .position-balance__text small {
    display: block;
    margin-top: 4px;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
  }

  .gauge-caption {
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 800;
  }

  .green {
    color: var(--strategy-success);
  }

  .red {
    color: var(--strategy-danger);
  }

  .hero-right {
    min-width: 0;
    padding: 10px 12px;
  }

  .account-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 800;
  }

  .account-rows {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .account-row {
    display: grid;
    grid-template-columns: 74px 1.4fr 0.7fr 0.7fr 0.7fr;
    gap: 12px;
    min-height: 48px;
    align-items: center;
    padding: 6px 12px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
  }

  .account-row__label {
    display: flex;
    align-items: center;
    color: var(--strategy-text-1);
    font-size: 16px;
    font-weight: 700;
  }

  .account-row__item {
    min-width: 0;
  }

  .account-row__item span {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 800;
  }

  .account-row__item strong {
    display: block;
    margin-top: 2px;
    color: var(--strategy-text-1);
    font-size: 14px;
    font-weight: 800;
    white-space: nowrap;
  }

  .account-row__item small {
    display: block;
    margin-top: 2px;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
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
    background: var(--strategy-success);
  }

  .progress-line em {
    position: relative;
    display: block;
    padding-right: 8px;
    color: #fff;
    font-size: var(--strategy-font-xs);
    font-style: normal;
    font-weight: 800;
    line-height: 16px;
    text-align: right;
  }

  .execution-board {
    display: grid;
    grid-template-columns: 322px 1fr;
    gap: 12px;
  }

  .side-column {
    display: grid;
    align-content: start;
    gap: 12px;
  }

  .panel,
  .trade-panel,
  .result-panel {
    padding: 14px;
  }

  .rule-list {
    margin-top: 12px;
  }

  .rule-list div {
    min-height: 42px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
  }

  .rule-list dd {
    max-width: 172px;
    text-align: right;
    line-height: 1.45;
  }

  .log-list {
    display: grid;
    gap: 8px;
    margin-top: 12px;
  }

  .log-list p {
    display: flex;
    gap: 8px;
    margin: 0;
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-sm);
    line-height: 1.55;
  }

  .log-list i {
    width: 8px;
    height: 8px;
    margin-top: 5px;
    flex: none;
    border-radius: 999px;
  }

  .passed {
    background: var(--strategy-success);
  }

  .is-info {
    background: #60a5fa;
  }

  .is-warning {
    background: #f59e0b;
  }

  .trade-panel {
    min-width: 0;
  }

  .trade-tabs,
  .button-group,
  .table-tabs {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .trade-tabs button.active,
  .button-group button.active,
  .action-row button.active,
  .table-tabs button.active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
  }

  .quote-strip {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 12px;
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .selector-toolbar {
    display: flex;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 16px;
    margin: 14px 0;
  }

  .custom-ratio {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 180px));
    gap: 12px;
    margin-bottom: 12px;
  }

  .legs-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .leg-panel,
  .impact-grid article {
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .leg-panel {
    padding: 16px;
  }

  .leg-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin: 12px 0;
  }

  .leg-stats strong {
    display: block;
    margin-top: 4px;
    font-size: 20px;
    font-weight: 800;
  }

  .positive {
    color: var(--strategy-success);
  }

  .negative {
    color: var(--strategy-danger);
  }

  .leg-panel p {
    margin: 8px 0 0;
    color: var(--strategy-text-3);
    font-weight: 700;
  }

  .action-row,
  .impact-grid,
  .risk-grid {
    display: grid;
    gap: 10px;
  }

  .action-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 14px;
  }

  .impact-panel,
  .risk-panel {
    margin-top: 14px;
  }

  .impact-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 10px;
  }

  .impact-grid article {
    min-height: 82px;
    padding: 12px;
  }

  .impact-grid strong {
    display: block;
    margin-top: 8px;
    font-size: 18px;
    font-weight: 800;
  }

  .risk-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-top: 10px;
  }

  .risk-grid span {
    min-height: 38px;
    padding: 10px 12px;
    border-radius: var(--strategy-radius-control);
    color: #fff;
    font-weight: 800;
  }

  .blocked {
    background: var(--strategy-danger);
  }

  .confirm-row {
    display: flex;
    justify-content: center;
    margin-top: 14px;
  }

  .confirm-row button:enabled,
  .trade-modal__dialog footer button:last-child {
    border-color: var(--strategy-accent-soft);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .table-wrap {
    overflow-x: auto;
  }

  table {
    min-width: 820px;
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 12px 10px;
    border-bottom: 1px solid var(--strategy-border-soft);
    text-align: left;
    font-size: var(--strategy-font-sm);
  }

  th {
    color: var(--strategy-text-3);
    background: var(--strategy-table-head-bg);
    font-weight: 800;
  }

  td {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .trade-modal {
    position: fixed;
    inset: 0;
    z-index: 1200;
    display: grid;
    place-items: center;
    background: rgba(11, 21, 42, 0.28);
  }

  .trade-modal__dialog {
    width: min(560px, calc(100vw - 32px));
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: 0 30px 60px rgba(20, 36, 63, 0.24);
  }

  .trade-modal__dialog header,
  .trade-modal__dialog footer,
  .confirm-lines {
    padding: 16px 18px;
  }

  .trade-modal__dialog header {
    border-bottom: 1px solid var(--strategy-border-soft);
  }

  .trade-modal__dialog header button {
    width: 36px;
    padding: 0;
    font-size: 20px;
  }

  .confirm-lines p {
    margin: 0 0 10px;
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  @media (max-width: 1400px) {
    .execution-board,
    .legs-grid,
    .impact-grid {
      grid-template-columns: 1fr;
    }

    .trade-head {
      align-items: flex-start;
      flex-direction: column;
    }

    .quote-strip {
      justify-content: flex-start;
    }
  }

  @media (max-width: 760px) {
    .hero-grid,
    .hero-left,
    .leg-stats,
    .action-row,
    .risk-grid,
    .custom-ratio {
      grid-template-columns: 1fr;
    }

    .gauge-card + .gauge-card {
      border-top: 1px solid var(--strategy-border-soft);
      border-left: 0;
    }

    .account-row {
      grid-template-columns: 1fr;
    }

    .account-row__item--wide {
      grid-column: auto;
    }
  }
</style>
