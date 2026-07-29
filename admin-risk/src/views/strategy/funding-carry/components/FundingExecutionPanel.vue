<template>
  <section class="panel order-panel">
    <div class="panel-title">
      <h3>套利执行指令</h3>
    </div>

    <div class="stage-tabs funding-stage-tabs">
      <button
        type="button"
        :class="{ active: fundingExecutionStage === 'open' }"
        @click="$emit('update:fundingExecutionStage', 'open')"
        >开仓</button
      >
      <button
        type="button"
        :class="{ active: fundingExecutionStage === 'close' }"
        @click="$emit('update:fundingExecutionStage', 'close')"
        >平仓</button
      >
    </div>

    <template v-if="fundingExecutionStage === 'open'">
      <div class="funding-order-grid">
        <section class="funding-order-column">
          <label class="field field--compact">
            <span>标的</span>
            <select :value="selectedSymbol" @change="emitString('selectedSymbol', $event)">
              <option>BTCUSDT</option>
              <option>ETHUSDT</option>
              <option>SOLUSDT</option>
            </select>
          </label>

          <div class="funding-order-row">
            <label class="field field--compact">
              <span>交易所</span>
              <select :value="selectedVenue" @change="emitString('selectedVenue', $event)">
                <option>Binance</option>
                <option>Bybit</option>
                <option>OKX</option>
              </select>
            </label>

            <label class="field field--compact">
              <span>执行方式</span>
              <select :value="fundingOpenMode" @change="emitOpenMode">
                <option value="market">市价开仓</option>
                <option value="limit">限价开仓</option>
              </select>
            </label>
          </div>

          <div class="funding-order-row">
            <label class="field field--compact">
              <span>名义本金</span>
              <div class="input-with-unit">
                <input :value="notionalValue" type="text" @input="emitString('notionalValue', $event)" />
                <em>USDT</em>
              </div>
            </label>

            <label class="field field--compact">
              <span>数量 (BTC)</span>
              <input :value="orderQty" type="text" @input="emitString('orderQty', $event)" />
            </label>
          </div>

          <div class="funding-order-row">
            <label class="field field--compact">
              <span>现货杠杆</span>
              <select :value="selectedLeverage" @change="emitString('selectedLeverage', $event)">
                <option>1x</option>
                <option>2x</option>
                <option>3x</option>
                <option>5x</option>
              </select>
            </label>

            <label class="field field--compact">
              <span>合约杠杆</span>
              <select :value="fundingHedgeLeverage" @change="emitString('fundingHedgeLeverage', $event)">
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
            </div>
            <div class="funding-leg-card">
              <span>合约头寸</span>
              <strong>{{ fundingLegs.perp }}</strong>
            </div>
          </div>
        </section>

        <section class="funding-order-column">
          <div class="funding-mode-tabs">
            <button
              type="button"
              :class="{ active: fundingOpenDirection === 'collect' }"
              @click="$emit('update:fundingOpenDirection', 'collect')"
            >
              正套开仓
            </button>
            <button
              type="button"
              :class="{ active: fundingOpenDirection === 'pay' }"
              @click="$emit('update:fundingOpenDirection', 'pay')"
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
          </div>

          <div class="funding-order-row">
            <label class="field field--compact">
              <span>开仓阈值</span>
              <div class="input-with-unit">
                <input :value="fundingThreshold" type="text" @input="emitString('fundingThreshold', $event)" />
                <em>%</em>
              </div>
            </label>

            <label class="field field--compact">
              <span>最大可接受入场价差</span>
              <div class="input-with-unit">
                <input :value="fundingEntryBasis" type="text" @input="emitString('fundingEntryBasis', $event)" />
                <em>USDT</em>
              </div>
            </label>
          </div>

          <div class="funding-order-row">
            <label class="field field--compact">
              <span>目标回补价差</span>
              <div class="input-with-unit">
                <input :value="fundingTakeProfit" type="text" @input="emitString('fundingTakeProfit', $event)" />
                <em>USDT</em>
              </div>
            </label>

            <label class="field field--compact">
              <span>止损价差</span>
              <div class="input-with-unit">
                <input :value="stopSpread" type="text" @input="emitString('stopSpread', $event)" />
                <em>USDT</em>
              </div>
            </label>
          </div>
        </section>
      </div>

      <div class="funding-action-row">
        <button class="submit-btn submit-btn--green" type="button" @click="$emit('submitOrder', 'collect')"
          >提交正套开仓</button
        >
        <button class="submit-btn submit-btn--red" type="button" @click="$emit('submitOrder', 'pay')"
          >提交反套开仓</button
        >
      </div>
    </template>

    <template v-else>
      <div class="funding-close-shell">
        <div class="funding-close-head">
          <div class="funding-mode-tabs funding-mode-tabs--close">
            <button
              type="button"
              :class="{ active: fundingCloseMode === 'market' }"
              @click="$emit('update:fundingCloseMode', 'market')"
              >市价平仓</button
            >
            <button
              type="button"
              :class="{ active: fundingCloseMode === 'limit' }"
              @click="$emit('update:fundingCloseMode', 'limit')"
              >限价平仓</button
            >
          </div>

          <label class="field field--compact funding-close-limit">
            <span>平仓触发价差</span>
            <div class="input-with-unit">
              <input :value="fundingCloseBasis" type="text" @input="emitString('fundingCloseBasis', $event)" />
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
                <td><button class="flat-action" type="button" @click="$emit('submitClose', row)">执行平仓</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
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

  type FundingExecutionStage = 'open' | 'close';
  type FundingOpenDirection = 'collect' | 'pay';
  type FundingOpenMode = 'market' | 'limit';
  type FundingCloseMode = 'market' | 'limit';
  type StringField =
    | 'selectedSymbol'
    | 'selectedVenue'
    | 'notionalValue'
    | 'selectedLeverage'
    | 'fundingHedgeLeverage'
    | 'orderQty'
    | 'stopSpread'
    | 'fundingThreshold'
    | 'fundingEntryBasis'
    | 'fundingTakeProfit'
    | 'fundingCloseBasis';

  defineProps<{
    fundingExecutionStage: FundingExecutionStage;
    fundingOpenDirection: FundingOpenDirection;
    fundingOpenMode: FundingOpenMode;
    fundingCloseMode: FundingCloseMode;
    selectedSymbol: string;
    selectedVenue: string;
    notionalValue: string;
    selectedLeverage: string;
    fundingHedgeLeverage: string;
    orderQty: string;
    stopSpread: string;
    fundingThreshold: string;
    fundingEntryBasis: string;
    fundingTakeProfit: string;
    fundingCloseBasis: string;
    fundingLegs: { spot: string; perp: string };
    fundingCloseRows: readonly FundingCloseRow[];
  }>();

  const emit = defineEmits<{
    (event: 'update:fundingExecutionStage', value: FundingExecutionStage): void;
    (event: 'update:fundingOpenDirection', value: FundingOpenDirection): void;
    (event: 'update:fundingOpenMode', value: FundingOpenMode): void;
    (event: 'update:fundingCloseMode', value: FundingCloseMode): void;
    (event: 'update:selectedSymbol', value: string): void;
    (event: 'update:selectedVenue', value: string): void;
    (event: 'update:notionalValue', value: string): void;
    (event: 'update:selectedLeverage', value: string): void;
    (event: 'update:fundingHedgeLeverage', value: string): void;
    (event: 'update:orderQty', value: string): void;
    (event: 'update:stopSpread', value: string): void;
    (event: 'update:fundingThreshold', value: string): void;
    (event: 'update:fundingEntryBasis', value: string): void;
    (event: 'update:fundingTakeProfit', value: string): void;
    (event: 'update:fundingCloseBasis', value: string): void;
    (event: 'submitOrder', value: FundingOpenDirection): void;
    (event: 'submitClose', value: FundingCloseRow): void;
  }>();

  function eventValue(event: Event) {
    return (event.target as HTMLInputElement | HTMLSelectElement).value;
  }

  function emitString(field: StringField, event: Event) {
    emit(`update:${field}` as never, eventValue(event) as never);
  }

  function emitOpenMode(event: Event) {
    emit('update:fundingOpenMode', eventValue(event) as FundingOpenMode);
  }
</script>

<style scoped lang="less">
  .panel {
    min-width: 0;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 18px;
    background: linear-gradient(
      180deg,
      var(--strategy-surface) 0%,
      var(--strategy-surface-soft) 100%
    );
    box-shadow: var(--strategy-shadow);
  }

  .panel-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .panel-title h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.012em;
  }

  .order-panel {
    display: flex;
    flex-direction: column;
    min-height: 684px;
    height: 100%;
  }

  .stage-tabs,
  .funding-mode-tabs {
    display: inline-flex;
    gap: 8px;
  }

  .stage-tabs button,
  .funding-mode-tabs button,
  .submit-btn,
  .flat-action {
    cursor: pointer;
  }

  .stage-tabs button,
  .funding-mode-tabs button {
    min-width: 48px;
    height: 40px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 10px;
    background: var(--strategy-surface);
    color: #47617f;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.01em;
  }

  .stage-tabs .active,
  .funding-mode-tabs .active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
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
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.01em;
  }

  .field select,
  .field input {
    width: 100%;
    height: 48px;
    padding: 0 12px;
    border: 1px solid #e7ebf0;
    border-radius: 12px;
    background: #fff;
    color: #13233f;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: -0.01em;
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
    color: #6b7280;
    font-size: 13px;
    font-style: normal;
    font-weight: 800;
    letter-spacing: 0.02em;
  }

  .funding-leg-grid,
  .funding-metric-grid,
  .funding-action-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .funding-leg-card,
  .mini-kpi {
    border: 1px solid #e9edf2;
    border-radius: 14px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .funding-leg-card {
    display: grid;
    gap: 6px;
    min-height: 88px;
    padding: 12px 14px;
  }

  .funding-leg-card span,
  .mini-kpi span {
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.01em;
  }

  .funding-leg-card strong,
  .mini-kpi strong {
    color: #111827;
    font-size: 20px;
    font-weight: 800;
    line-height: 1.2;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
  }

  .funding-mode-tabs {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .mini-kpi {
    min-height: 76px;
    padding: 12px 14px;
  }

  .funding-action-row {
    margin-top: 14px;
  }

  .submit-btn {
    width: 100%;
    height: 52px;
    border: none;
    border-radius: 12px;
    color: #fff;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.01em;
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
  .funding-close-table td {
    padding: 12px 10px;
    border-bottom: 1px solid var(--strategy-border-soft);
    text-align: left;
    font-size: var(--strategy-font-sm);
  }

  .funding-close-table th {
    color: var(--strategy-text-3);
    background: var(--strategy-table-head-bg);
    font-weight: 700;
  }

  .funding-close-table td {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .flat-action {
    min-width: 104px;
    height: 40px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.01em;
  }

  .green {
    color: #16a34a !important;
  }

  .red {
    color: #ef4444 !important;
  }

  @media (max-width: 1400px) {
    .funding-order-grid,
    .funding-order-row,
    .funding-leg-grid,
    .funding-metric-grid,
    .funding-action-row {
      grid-template-columns: 1fr;
    }

    .funding-close-head {
      flex-direction: column;
      align-items: flex-start;
    }
  }

  @media (max-width: 1024px) {
    .funding-close-head {
      gap: 10px;
    }

    .funding-close-limit {
      min-width: 0;
      width: 100%;
    }

    .funding-close-table-wrap {
      width: 100%;
    }
  }
</style>
