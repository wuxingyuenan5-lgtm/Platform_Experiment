<template>
  <section class="cross-card cross-card--execution">
    <div class="card-head">
      <div>
        <h3>价差执行指令</h3>
      </div>
    </div>

    <div class="stage-tabs">
      <button
        :class="{ active: executionStage === 'open' }"
        @click="$emit('update:executionStage', 'open')"
        >开仓价差</button
      >
      <button
        :class="{ active: executionStage === 'close' }"
        @click="$emit('update:executionStage', 'close')"
        >平仓价差</button
      >
      <button
        :class="{ active: executionStage === 'funding' }"
        @click="$emit('update:executionStage', 'funding')"
        >移动双边资金</button
      >
    </div>

    <template v-if="executionStage === 'open'">
      <div class="execution-grid">
        <div class="execution-column execution-column--left">
          <label class="field-block">
            <span>下单数量</span>
            <div class="input-row input-row--qty">
              <input
                :value="qtyInput"
                inputmode="decimal"
                @input="emitInput('qtyInput', $event)"
                @blur="$emit('commitQtyInput')"
              />
              <button type="button" class="unit-btn">盎司</button>
              <button type="button" @click="$emit('nudgeQty', -10)">-</button>
              <button type="button" @click="$emit('nudgeQty', 10)">+</button>
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
                <strong>{{ formatNullablePrice(mt5Lot, 2) }}</strong>
              </article>
            </div>
          </div>

          <label class="field-block">
            <span>Bybit 杠杆（XAUTUSDT）</span>
            <div class="input-row">
              <input v-model="bybitLeverageInput" inputmode="decimal" aria-label="Bybit 杠杆" />
              <em>x</em>
              <button type="button" :disabled="leverageLoading" @click="applyBybitLeverage">{{
                leverageLoading ? '设置中' : '应用到交易所'
              }}</button>
            </div>
            <p class="execution-note">{{
              leverageMessage || '账户级真实设置：仅在 Bybit 回执成功后生效。MT5 杠杆由账户管理。'
            }}</p>
          </label>
        </div>

        <div class="execution-column execution-column--pricing">
          <div class="mode-tabs">
            <button
              :class="{ active: executionMode === 'market' }"
              @click="$emit('update:executionMode', 'market')"
              >市价开仓</button
            >
            <button
              :class="{ active: executionMode === 'limit' }"
              @click="$emit('update:executionMode', 'limit')"
              >限价开仓</button
            >
          </div>

          <label class="field-block">
            <span>开仓价差</span>
            <div class="input-row">
              <input
                :value="triggerSpreadInput"
                inputmode="decimal"
                @input="emitInput('triggerSpreadInput', $event)"
                @blur="$emit('commitSpreadInput', 'trigger')"
              />
              <em>USDT</em>
            </div>
          </label>

          <label class="field-block">
            <span>可接受价差</span>
            <div class="input-row">
              <input
                :value="acceptableSpreadInput"
                inputmode="decimal"
                @input="emitInput('acceptableSpreadInput', $event)"
                @blur="$emit('commitSpreadInput', 'acceptable')"
              />
              <em>USDT</em>
            </div>
          </label>

          <label v-if="executionMode === 'limit'" class="field-block">
            <span>开仓限价策略</span>
            <div class="input-row input-row--single-select">
              <select :value="openLimitStrategy" @change="emitSelect('openLimitStrategy', $event)">
                <option value="fok">FOK 全成全撤</option>
                <option value="post_only_chase">PostOnly Chase</option>
              </select>
            </div>
          </label>

          <label v-if="takeProfitExecution === 'limit'" class="field-block">
            <span>止盈限价策略</span>
            <div class="input-row input-row--single-select">
              <select
                :value="takeProfitLimitStrategy"
                @change="emitSelect('takeProfitLimitStrategy', $event)"
              >
                <option value="fok">FOK 全成全撤</option>
                <option value="post_only_chase">PostOnly Chase</option>
              </select>
            </div>
          </label>
        </div>

        <div class="execution-column execution-column--right">
          <div class="risk-stack">
            <label class="field-block field-block--stacked">
              <span>止盈价差</span>
              <div class="input-row input-row--select">
                <input
                  :value="takeProfitSpreadInput"
                  inputmode="decimal"
                  @input="emitInput('takeProfitSpreadInput', $event)"
                  @blur="$emit('commitSpreadInput', 'takeProfit')"
                />
                <em>USDT</em>
                <select
                  class="stacked-select"
                  :value="takeProfitExecution"
                  @change="emitSelect('takeProfitExecution', $event)"
                >
                  <option value="limit">限价</option>
                  <option value="market">市价</option>
                </select>
              </div>
              <div
                v-if="takeProfitExecution === 'limit'"
                class="input-row input-row--single-select"
              >
                <select
                  :value="takeProfitLimitStrategy"
                  @change="emitSelect('takeProfitLimitStrategy', $event)"
                >
                  <option value="fok">FOK 全成全撤</option>
                  <option value="post_only_chase">PostOnly Chase</option>
                </select>
              </div>
            </label>

            <label class="field-block field-block--stacked">
              <span>止损价差</span>
              <div class="input-row input-row--select">
                <input
                  :value="stopLossSpreadInput"
                  inputmode="decimal"
                  @input="emitInput('stopLossSpreadInput', $event)"
                  @blur="$emit('commitSpreadInput', 'stopLoss')"
                />
                <em>USDT</em>
                <select
                  class="stacked-select"
                  :value="stopLossExecution"
                  @change="emitSelect('stopLossExecution', $event)"
                >
                  <option value="market">市价</option>
                  <option value="limit">限价</option>
                </select>
              </div>
              <div v-if="stopLossExecution === 'limit'" class="input-row input-row--single-select">
                <select
                  :value="stopLossLimitStrategy"
                  @change="emitSelect('stopLossLimitStrategy', $event)"
                >
                  <option value="fok">FOK 全成全撤</option>
                  <option value="post_only_chase">PostOnly Chase</option>
                </select>
              </div>
            </label>
          </div>
        </div>
      </div>

      <div class="submit-row">
        <button
          class="submit-btn submit-btn--green"
          :disabled="submitLoading"
          @click="$emit('prepareOpenDraft', 'long')"
          >开多价差</button
        >
        <button
          class="submit-btn submit-btn--red"
          :disabled="submitLoading"
          @click="$emit('prepareOpenDraft', 'short')"
          >开空价差</button
        >
      </div>

      <div v-if="executionMessage || limitEvidence" class="execution-feedback">
        <strong v-if="executionMessage" :class="executionMessageTone">{{
          executionMessage
        }}</strong>
        <span v-if="limitEvidence">
          {{ limitStrategyLabel(limitEvidence.limitStrategy) }} /
          {{ limitEvidence.timeInForce }}，限制
          {{ formatNullableSigned(limitEvidence.limitSpread) }}，可成交
          {{ formatNullableSigned(limitEvidence.executableSpread) }}
        </span>
      </div>
    </template>

    <template v-else-if="executionStage === 'close'">
      <div class="close-shell">
        <div class="mode-tabs">
          <button
            :class="{ active: closeExecutionMode === 'market' }"
            @click="$emit('update:closeExecutionMode', 'market')"
            >市价平仓</button
          >
          <button
            :class="{ active: closeExecutionMode === 'limit' }"
            @click="$emit('update:closeExecutionMode', 'limit')"
            >限价平仓</button
          >
        </div>

        <div class="close-market-strip">
          <article>
            <span>平多当前价差</span>
            <strong :class="spreadTone(longSpread)"
              >{{ formatNullableSigned(longSpread) }} USDT</strong
            >
          </article>
          <article>
            <span>平空当前价差</span>
            <strong :class="spreadTone(shortSpread)"
              >{{ formatNullableSigned(shortSpread) }} USDT</strong
            >
          </article>
        </div>

        <label v-if="closeExecutionMode === 'limit'" class="field-block field-block--compact">
          <span>平仓限制价差</span>
          <div class="input-row">
            <input
              :value="closeLimitSpreadInput"
              inputmode="decimal"
              @input="emitInput('closeLimitSpreadInput', $event)"
              @blur="$emit('commitSpreadInput', 'closeLimit')"
            />
            <em>USDT</em>
          </div>
        </label>

        <label v-if="closeExecutionMode === 'limit'" class="field-block field-block--compact">
          <span>平仓限价策略</span>
          <div class="input-row input-row--single-select">
            <select :value="closeLimitStrategy" @change="emitSelect('closeLimitStrategy', $event)">
              <option value="fok">FOK 全成全撤</option>
              <option value="post_only_chase">PostOnly Chase</option>
            </select>
          </div>
        </label>

        <table class="basic-table">
          <thead>
            <tr>
              <th>方向</th>
              <th>盎司</th>
              <th>账户杠杆</th>
              <th>开仓价差</th>
              <th>当前价差</th>
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
              <td>账户级（只读）</td>
              <td>{{ formatSigned(position.entrySpread) }}</td>
              <td :class="spreadTone(closeMarketSpread(position.direction))">{{
                formatNullableSigned(closeMarketSpread(position.direction))
              }}</td>
              <td
                >{{ formatNullableSigned(position.takeProfit) }} /
                {{ formatNullableSigned(position.stopLoss) }}</td
              >
              <td>{{ position.execution }}</td>
              <td>
                <button
                  class="row-btn"
                  :disabled="submitLoading"
                  @click="$emit('openConfirm', `CLOSE:${position.id}`)"
                  >手动平仓</button
                >
              </td>
            </tr>
            <tr v-if="!closeOrders.length">
              <td colspan="8">暂无真实退出计划</td>
            </tr>
          </tbody>
        </table>

        <button
          class="submit-btn submit-btn--red submit-btn--full"
          :disabled="submitLoading || !closeOrders.length"
          @click="$emit('openConfirm', 'CLOSE_ALL')"
          >手动全平</button
        >

        <div v-if="executionMessage || limitEvidence" class="execution-feedback">
          <strong v-if="executionMessage" :class="executionMessageTone">{{
            executionMessage
          }}</strong>
          <span v-if="limitEvidence">
            {{ limitStrategyLabel(limitEvidence.limitStrategy) }} /
            {{ limitEvidence.timeInForce }}，限制
            {{ formatNullableSigned(limitEvidence.limitSpread) }}，可成交
            {{ formatNullableSigned(limitEvidence.executableSpread) }}
          </span>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="funding-shell">
        <div class="funding-balance-grid">
          <article class="funding-balance-card">
            <span>Bybit 所内真实可调拨余额</span>
            <strong>
              {{ fundingBalanceText(bybitAmount, quote?.bybitTransferable.currency) }}
            </strong>
            <small v-if="quote?.bybitTransferable.dataQualityState === 'unavailable'">
              {{ quote.bybitTransferable.reason || '数据暂不可用' }}
            </small>
          </article>
          <article class="funding-balance-card">
            <span>MT5 真实可转出余额</span>
            <strong>{{ fundingBalanceText(mt5Amount, quote?.mt5Withdrawable.currency) }}</strong>
            <small v-if="quote?.mt5Withdrawable.dataQualityState === 'unavailable'">
              {{ quote.mt5Withdrawable.reason || '数据暂不可用' }}
            </small>
          </article>
        </div>

        <div class="funding-form-grid">
          <label class="field-block">
            <span>调拨方向</span>
            <div class="input-row input-row--single-select">
              <select v-model="direction" aria-label="资金调拨方向">
                <option value="bybit_to_mt5">Bybit UTA → Funding → MT5</option>
                <option value="mt5_to_bybit">MT5 → Funding → Bybit UTA</option>
              </select>
            </div>
          </label>
          <button type="button" class="row-btn funding-swap" @click="swapDirection">
            手工换向
          </button>
          <label class="field-block">
            <span>调拨金额</span>
            <div class="input-row">
              <input
                :value="amountInput"
                inputmode="decimal"
                aria-label="资金调拨金额"
                @input="updateFundingAmount"
              />
              <em>USDT 等值</em>
            </div>
            <p v-if="amountError" class="field-error">{{ amountError }}</p>
          </label>
        </div>

        <div class="funding-projection">
          <span>确认前预计余额</span>
          <div class="mini-grid">
            <article class="metric-card">
              <small>Bybit 调拨后</small>
              <strong>
                {{
                  fundingBalanceText(
                    projectedBalances?.bybit ?? null,
                    quote?.bybitTransferable.currency,
                  )
                }}
              </strong>
            </article>
            <article class="metric-card">
              <small>MT5 调拨后</small>
              <strong>
                {{
                  fundingBalanceText(
                    projectedBalances?.mt5 ?? null,
                    quote?.mt5Withdrawable.currency,
                  )
                }}
              </strong>
            </article>
          </div>
        </div>

        <label class="funding-confirm">
          <input v-model="confirmed" type="checkbox" />
          <span>我已核对调拨方向、金额和调拨后预计余额</span>
        </label>

        <div v-if="transfer" class="funding-status" :data-status="transfer.status">
          <strong>{{ fundingStatusLabel(transfer.status) }}</strong>
          <span>资金位置：{{ fundingLocationLabel(transfer.currentLocation) }}</span>
          <span v-if="transfer.failureReason">{{ transfer.failureReason }}</span>
        </div>

        <div v-if="quote?.mode === 'assisted'" class="funding-assisted">
          <strong>辅助模式</strong>
          <span>真实 MT5 Transfer API 尚未确认，请复制金额并在 Bybit 官方资金页完成。</span>
          <div class="funding-actions">
            <button type="button" class="row-btn" @click="copyAmount">一键复制金额</button>
            <button type="button" class="row-btn" @click="openOfficialFundingPage">
              打开 Bybit 官方资金页
            </button>
          </div>
        </div>

        <div class="funding-actions">
          <button
            type="button"
            class="submit-btn submit-btn--green"
            :disabled="!canSubmit"
            @click="submitTransfer"
          >
            {{
              loading ? '处理中' : quote?.mode === 'assisted' ? '记录并进入辅助调拨' : '确认调拨'
            }}
          </button>
          <button
            type="button"
            class="row-btn"
            :disabled="loading"
            @click="refreshTransferAndBalances"
          >
            刷新并核对两边余额
          </button>
        </div>
        <p v-if="balanceVerification === 'matched'" class="funding-verified">
          两边余额已与调拨后预计值一致。
        </p>
        <p v-else-if="balanceVerification === 'not_matched'" class="execution-note">
          最新余额尚未与预计值一致，请在 Bybit 完成后再次刷新。
        </p>
        <p v-if="error" class="field-error">{{ error }}</p>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import type {
    CrossSpreadExecutionMode,
    CrossSpreadLimitExecutionResult,
    CrossSpreadLimitStrategy,
  } from '@/api/platform/crossSpreadLifecycle';
  import { useCrossSpreadFundingTransfer } from '../composables/useCrossSpreadFundingTransfer';

  type SpreadInputField = 'trigger' | 'acceptable' | 'takeProfit' | 'stopLoss' | 'closeLimit';
  type EditableInputName =
    | 'qtyInput'
    | 'triggerSpreadInput'
    | 'acceptableSpreadInput'
    | 'takeProfitSpreadInput'
    | 'stopLossSpreadInput'
    | 'closeLimitSpreadInput';
  type SelectInputName =
    | 'openLimitStrategy'
    | 'takeProfitExecution'
    | 'takeProfitLimitStrategy'
    | 'stopLossExecution'
    | 'stopLossLimitStrategy'
    | 'closeLimitStrategy';

  interface CloseOrder {
    id: string;
    direction: 'LONG_SPREAD' | 'SHORT_SPREAD';
    qtyOz: number;
    entrySpread: number;
    takeProfit: number | null;
    stopLoss: number | null;
    execution: string;
  }

  const props = defineProps<{
    executionStage: 'open' | 'close' | 'funding';
    executionMode: CrossSpreadExecutionMode;
    closeExecutionMode: CrossSpreadExecutionMode;
    qtyInput: string;
    qtyError: string;
    bybitQty: number;
    mt5Lot: number | null;
    longSpread: number | null;
    shortSpread: number | null;
    triggerSpreadInput: string;
    acceptableSpreadInput: string;
    openLimitStrategy: CrossSpreadLimitStrategy;
    takeProfitExecution: CrossSpreadExecutionMode;
    takeProfitLimitStrategy: CrossSpreadLimitStrategy;
    takeProfitSpreadInput: string;
    stopLossSpreadInput: string;
    stopLossExecution: CrossSpreadExecutionMode;
    stopLossLimitStrategy: CrossSpreadLimitStrategy;
    closeLimitSpreadInput: string;
    closeLimitStrategy: CrossSpreadLimitStrategy;
    submitLoading: boolean;
    executionMessage: string;
    executionMessageTone: 'is-success' | 'is-error' | 'is-warn';
    limitEvidence: CrossSpreadLimitExecutionResult | null;
    closeOrders: CloseOrder[];
  }>();

  const emit = defineEmits<{
    (event: 'update:executionStage', value: 'open' | 'close' | 'funding'): void;
    (event: 'update:executionMode', value: CrossSpreadExecutionMode): void;
    (event: 'update:closeExecutionMode', value: CrossSpreadExecutionMode): void;
    (event: 'update:qtyInput', value: string): void;
    (event: 'update:triggerSpreadInput', value: string): void;
    (event: 'update:acceptableSpreadInput', value: string): void;
    (event: 'update:openLimitStrategy', value: CrossSpreadLimitStrategy): void;
    (event: 'update:takeProfitExecution', value: CrossSpreadExecutionMode): void;
    (event: 'update:takeProfitLimitStrategy', value: CrossSpreadLimitStrategy): void;
    (event: 'update:stopLossExecution', value: CrossSpreadExecutionMode): void;
    (event: 'update:stopLossLimitStrategy', value: CrossSpreadLimitStrategy): void;
    (event: 'update:takeProfitSpreadInput', value: string): void;
    (event: 'update:stopLossSpreadInput', value: string): void;
    (event: 'update:closeLimitSpreadInput', value: string): void;
    (event: 'update:closeLimitStrategy', value: CrossSpreadLimitStrategy): void;
    (event: 'commitQtyInput'): void;
    (event: 'nudgeQty', value: number): void;
    (event: 'commitSpreadInput', value: SpreadInputField): void;
    (event: 'prepareOpenDraft', value: 'long' | 'short'): void;
    (event: 'openConfirm', value: string): void;
  }>();

  const bybitLeverageInput = ref('20');
  const leverageLoading = ref(false);
  const leverageMessage = ref('');
  const {
    amountError,
    amountInput,
    balanceVerification,
    bybitAmount,
    canSubmit,
    confirmed,
    copyAmount,
    direction,
    error,
    loading,
    mt5Amount,
    openOfficialFundingPage,
    projectedBalances,
    quote,
    refreshTransferAndBalances,
    submitTransfer,
    swapDirection,
    transfer,
    updateAmount,
  } = useCrossSpreadFundingTransfer();
  async function applyBybitLeverage() {
    const leverage = Number(bybitLeverageInput.value);
    if (!Number.isFinite(leverage) || leverage <= 0 || leverage > 100) {
      leverageMessage.value = '请输入 0–100 的有效杠杆。';
      return;
    }
    leverageLoading.value = true;
    leverageMessage.value = '';
    try {
      const response = await fetch('http://127.0.0.1:8100/venue/bybit/leverage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accountId: 'bybit-live-main', symbol: 'XAUTUSDT', leverage }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || '交易所未接受杠杆设置');
      leverageMessage.value = `交易所已确认 ${body.symbol} 为 ${body.leverage}x。`;
    } catch (error) {
      leverageMessage.value = error instanceof Error ? `设置失败：${error.message}` : '设置失败。';
    } finally {
      leverageLoading.value = false;
    }
  }

  function emitInput(name: EditableInputName, event: Event) {
    const value = (event.target as HTMLInputElement).value;
    emit(`update:${name}` as never, value as never);
  }

  function emitSelect(name: SelectInputName, event: Event) {
    const value = (event.target as HTMLSelectElement).value;
    emit(`update:${name}` as never, value as never);
  }

  function parseOptionalNumber(value: string | number | null | undefined) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatNumber(value: number, digits = 2) {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function formatSigned(value: number) {
    return `${value > 0 ? '+' : ''}${formatNumber(value)}`;
  }

  function formatNullablePrice(value: string | number | null | undefined, digits = 2) {
    const parsed = parseOptionalNumber(value);
    return parsed === null ? '--' : formatNumber(parsed, digits);
  }

  function formatNullableSigned(value: string | number | null | undefined) {
    const parsed = parseOptionalNumber(value);
    if (parsed === null) return '--';
    return formatSigned(parsed);
  }

  function spreadTone(value: string | number | null | undefined) {
    const parsed = parseOptionalNumber(value);
    if (parsed === null) return '';
    return parsed <= 0 ? 'green' : 'red';
  }

  function closeMarketSpread(direction: CloseOrder['direction']) {
    return direction === 'LONG_SPREAD' ? props.longSpread : props.shortSpread;
  }

  function limitStrategyLabel(strategy: CrossSpreadLimitStrategy) {
    return strategy === 'post_only_chase' ? 'PostOnly Chase' : 'FOK';
  }

  function updateFundingAmount(event: Event) {
    updateAmount((event.target as HTMLInputElement).value);
  }

  function fundingBalanceText(value: string | null, currency?: string) {
    return value === null ? '--' : `${value} ${currency || 'USDT'}`;
  }

  function fundingStatusLabel(status: string) {
    return {
      pending: '待完成',
      completed: '已完成',
      failed: '失败',
      result_unknown: '结果未知，禁止自动重试',
    }[status];
  }

  function fundingLocationLabel(location: string) {
    return {
      bybit_uta: 'Bybit UTA',
      funding: 'Bybit Funding',
      mt5: 'MT5',
      unknown: '待人工核对',
    }[location];
  }
</script>

<style scoped lang="less">
  .cross-card {
    padding: 16px 18px 18px;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #fff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgb(94 109 133 / 4%);
  }

  .card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .card-head h3 {
    margin: 0;
    color: #162845;
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.012em;
  }

  .stage-tabs,
  .mode-tabs,
  .submit-row {
    display: flex;
    gap: 8px;
  }

  .stage-tabs {
    margin-bottom: 14px;
  }

  .stage-tabs button,
  .mode-tabs button,
  .row-btn {
    border: 1px solid #d7e2ef;
    border-radius: 10px;
    background: #fff;
    color: #47617f;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
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

  .stage-tabs button.active,
  .mode-tabs button.active {
    border-color: rgb(220 82 82 / 38%);
    background: linear-gradient(180deg, #ff6868 0%, #ef4343 100%);
    box-shadow: 0 8px 20px rgb(239 67 67 / 18%);
    color: #fff;
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

  .execution-column--pricing,
  .execution-column--right {
    gap: 14px;
    padding-top: 18px;
  }

  .risk-stack {
    display: grid;
    gap: 14px;
    padding: 2px;
  }

  .field-block--stacked {
    gap: 10px;
    padding: 14px;
    border: 1px solid #e9edf2;
    border-radius: 16px;
    background: linear-gradient(180deg, #fff 0%, #fcfdff 100%);
    box-shadow: 0 6px 18px rgb(94 109 133 / 5%);
  }

  .field-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .field-block span,
  .metric-card small,
  .close-market-strip span {
    color: #2f3640;
    font-size: 13px;
    font-weight: 800;
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
    box-shadow: inset 0 1px 0 rgb(255 255 255 / 80%);
  }

  .input-row input,
  .input-row select {
    width: 100%;
    min-width: 0;
    padding: 0 14px;
    border: none;
    outline: none;
    background: transparent;
    color: #1a2a48;
    font-family: var(--strategy-font-data);
    font-size: 15px;
    font-weight: 700;
  }

  .input-row em {
    display: flex;
    align-items: center;
    justify-content: center;
    border-left: 1px solid #e7ebf0;
    background: #fff;
    color: #152646;
    font-size: 13px;
    font-style: normal;
    font-weight: 700;
  }

  .input-row--qty {
    grid-template-columns: 1fr 64px 40px 40px;
  }

  .input-row--select {
    grid-template-columns: minmax(0, 1fr) 60px 76px;
  }

  .input-row--select select {
    border-left: 1px solid #e7ebf0;
    color: #1a2a48;
    font-size: 14px;
    font-weight: 700;
  }

  .stacked-select {
    background: #f8fbff !important;
  }

  .input-row--single-select {
    grid-template-columns: minmax(0, 1fr);
  }

  .input-row--single-select select {
    padding-right: 30px;
  }

  .input-row--qty button,
  .unit-btn {
    border: none;
    border-left: 1px solid #e7ebf0;
    background: #fff;
    color: #152646;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
  }

  .mini-panel,
  .metric-card,
  .close-market-strip article {
    border: 1px solid #e9edf2;
    background: linear-gradient(180deg, #fff 0%, #fcfdff 100%);
  }

  .mini-panel {
    padding: 12px 14px 14px;
    border-radius: 16px;
  }

  .mini-panel__title {
    display: block;
    margin-bottom: 10px;
    color: #2f3640;
    font-size: 15px;
    font-weight: 800;
  }

  .mini-grid,
  .close-market-strip {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .metric-card,
  .close-market-strip article {
    min-height: 74px;
    padding: 12px 14px;
    border-radius: 14px;
  }

  .metric-card strong,
  .close-market-strip strong {
    display: block;
    margin-top: 8px;
    color: #172947;
    font-family: var(--strategy-font-data);
    font-size: 16px;
    font-weight: 700;
  }

  .submit-row {
    justify-content: space-between;
    gap: 16px;
    margin-top: 16px;
  }

  .submit-btn {
    flex: 1;
    height: 52px;
    border: none;
    border-radius: 12px;
    color: #fff;
    font-size: 18px;
    font-weight: 800;
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
    min-height: 58px;
    margin-top: 16px;
    font-size: 18px;
  }

  .close-shell {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .funding-shell {
    display: grid;
    gap: 16px;
  }

  .funding-balance-grid,
  .funding-form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .funding-balance-card,
  .funding-projection,
  .funding-assisted,
  .funding-status {
    padding: 14px;
    border: 1px solid #e7ebf0;
    border-radius: 14px;
    background: #fff;
  }

  .funding-balance-card span,
  .funding-projection > span {
    color: #47617f;
    font-size: 13px;
    font-weight: 700;
  }

  .funding-balance-card strong {
    display: block;
    margin-top: 8px;
    color: #172947;
    font-family: var(--strategy-font-data);
    font-size: 18px;
  }

  .funding-balance-card small {
    display: block;
    margin-top: 8px;
    color: var(--strategy-danger, #ef3232);
  }

  .funding-form-grid {
    grid-template-columns: minmax(0, 1fr) 112px minmax(0, 1fr);
    align-items: end;
  }

  .funding-swap {
    margin-bottom: 1px;
  }

  .funding-projection > span {
    display: block;
    margin-bottom: 10px;
  }

  .funding-confirm {
    display: flex;
    gap: 9px;
    align-items: center;
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
  }

  .funding-status,
  .funding-assisted {
    display: grid;
    gap: 6px;
    color: #47617f;
    font-size: 13px;
  }

  .funding-status[data-status='completed'],
  .funding-verified {
    color: var(--strategy-success, #179b4b);
  }

  .funding-status[data-status='failed'],
  .funding-status[data-status='result_unknown'] {
    color: var(--strategy-danger, #ef3232);
  }

  .funding-actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .funding-actions .submit-btn {
    font-size: 16px;
  }

  .funding-verified {
    margin: 0;
    font-size: 13px;
    font-weight: 700;
  }

  .basic-table {
    width: 100%;
    border-collapse: collapse;
  }

  .basic-table th,
  .basic-table td {
    padding: 13px 10px;
    border-bottom: 1px solid #d8e2ec;
    font-size: 13px;
    text-align: left;
    white-space: nowrap;
  }

  .basic-table th {
    color: #2f3640;
    font-size: 14px;
    font-weight: 800;
  }

  .basic-table td {
    color: #22324d;
    font-family: var(--strategy-font-data);
    font-size: 13px;
    font-weight: 700;
  }

  .row-btn {
    min-width: 104px;
    height: 40px;
    padding: 0 16px;
    font-size: 14px;
    font-weight: 600;
  }

  .execution-feedback {
    display: grid;
    gap: 6px;
    padding: 10px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface-muted);
    color: var(--strategy-text-2);
  }

  .execution-feedback strong {
    font-size: 14px;
  }

  .execution-feedback .is-success,
  .green {
    color: var(--strategy-success, #179b4b) !important;
  }

  .execution-feedback .is-error,
  .red {
    color: var(--strategy-danger, #ef3232) !important;
  }

  .execution-feedback .is-warn {
    color: var(--strategy-warning, #d07d1e) !important;
  }

  .field-error {
    margin: 0;
    color: #d92b2b;
    font-size: 12px;
  }

  @media (max-width: 1480px) {
    .execution-grid {
      grid-template-columns: 1fr;
    }

    .field-block--lower {
      margin-top: 0;
    }
  }

  @media (max-width: 960px) {
    .stage-tabs,
    .mode-tabs,
    .submit-row,
    .close-market-strip {
      grid-template-columns: 1fr;
      flex-direction: column;
    }

    .funding-balance-grid,
    .funding-form-grid,
    .funding-actions {
      grid-template-columns: 1fr;
      flex-direction: column;
    }

    .basic-table {
      display: block;
      overflow-x: auto;
    }
  }
</style>
