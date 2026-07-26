<template>
  <section class="market-lifecycle">
    <header class="market-lifecycle__header">
      <div>
        <p>SYNTHETIC LIFECYCLE</p>
        <h3>跨所价差交易执行区</h3>
      </div>
      <div class="market-lifecycle__status">
        <span>{{ leftLegSymbol }} / {{ rightLegSymbol }}</span>
        <strong>市价 / FOK / PostOnly</strong>
      </div>
    </header>

    <div class="market-lifecycle__grid">
      <section class="market-lifecycle__card">
        <div class="market-lifecycle__card-head">
          <div>
            <h4>合成开仓</h4>
            <p>Bybit 确认精确成交后，MT5 按实际数量对冲</p>
          </div>
          <button type="button" :disabled="loading" @click="refreshPlans">刷新</button>
        </div>

        <div class="market-lifecycle__form">
          <label>
            <span>方向</span>
            <select v-model="direction" @change="applyDirectionDefaults">
              <option value="LONG_SPREAD">开多价差</option>
              <option value="SHORT_SPREAD">开空价差</option>
            </select>
          </label>
          <label>
            <span>执行方式</span>
            <select v-model="openExecutionMode">
              <option value="market">市价</option>
              <option value="limit">限价</option>
            </select>
          </label>
          <label v-if="openExecutionMode === 'limit'">
            <span>限价策略</span>
            <select v-model="openLimitStrategy">
              <option value="fok">FOK 全成全撤</option>
              <option value="post_only_chase">PostOnly 追单</option>
            </select>
          </label>
          <label>
            <span>数量（盎司）</span>
            <input v-model="quantityOz" inputmode="decimal" />
          </label>
          <label v-if="openExecutionMode === 'limit'">
            <span>限制价差</span>
            <input v-model="openLimitSpread" inputmode="decimal" />
          </label>
          <label>
            <span>止盈平仓价差</span>
            <input v-model="takeProfitSpread" inputmode="decimal" />
          </label>
          <label>
            <span>止盈执行</span>
            <select v-model="takeProfitExecutionMode">
              <option value="market">市价</option>
              <option value="limit">限价</option>
            </select>
          </label>
          <label v-if="takeProfitExecutionMode === 'limit'">
            <span>止盈限价策略</span>
            <select v-model="takeProfitLimitStrategy">
              <option value="fok">FOK 全成全撤</option>
              <option value="post_only_chase">PostOnly 追单</option>
            </select>
          </label>
          <label>
            <span>止损平仓价差</span>
            <input v-model="stopLossSpread" inputmode="decimal" />
          </label>
          <label>
            <span>止损执行</span>
            <select v-model="stopLossExecutionMode">
              <option value="market">市价（默认）</option>
              <option value="limit">限价</option>
            </select>
          </label>
          <label v-if="stopLossExecutionMode === 'limit'">
            <span>止损限价策略</span>
            <select v-model="stopLossLimitStrategy">
              <option value="fok">FOK 全成全撤</option>
              <option value="post_only_chase">PostOnly 追单</option>
            </select>
          </label>
        </div>

        <div class="market-lifecycle__formula">
          <span>可成交价差方向</span>
          <strong>{{ executableSpreadLabel }}</strong>
          <small>{{ thresholdRuleLabel }}</small>
          <small v-if="openExecutionMode === 'limit'">{{ limitRuleLabel }}</small>
          <small v-if="usesPostOnly" class="is-warn">
            PostOnly Chase 默认关闭，必须在受控 Runtime 主机显式启用；断线或事件不一致将停止追单。
          </small>
          <small v-if="stopLossExecutionMode === 'limit'" class="is-warn">
            限价止损可能未成交并保持计划活动；风险降低优先时应使用市价。
          </small>
        </div>

        <button
          type="button"
          class="market-lifecycle__primary"
          :disabled="loading || Boolean(validationError)"
          @click="submitOpen"
        >
          {{ openButtonLabel }}
        </button>
        <p v-if="validationError" class="market-lifecycle__error">{{ validationError }}</p>
      </section>

      <section class="market-lifecycle__card market-lifecycle__card--plans">
        <div class="market-lifecycle__card-head">
          <div>
            <h4>真实退出计划</h4>
            <p>人工、止盈和止损复用同一 Close Action，并保存各自限价策略</p>
          </div>
          <span>{{ activePlans.length }} 笔活动计划</span>
        </div>

        <div class="market-lifecycle__close-controls">
          <label>
            <span>人工平仓方式</span>
            <select v-model="closeExecutionMode">
              <option value="market">市价</option>
              <option value="limit">限价</option>
            </select>
          </label>
          <label v-if="closeExecutionMode === 'limit'">
            <span>人工限价策略</span>
            <select v-model="closeLimitStrategy">
              <option value="fok">FOK 全成全撤</option>
              <option value="post_only_chase">PostOnly 追单</option>
            </select>
          </label>
          <label v-if="closeExecutionMode === 'limit'">
            <span>平仓限制价差</span>
            <input v-model="closeLimitSpread" inputmode="decimal" />
          </label>
          <small v-if="closeValidationError">{{ closeValidationError }}</small>
        </div>

        <div class="market-lifecycle__table-wrap">
          <table>
            <thead>
              <tr>
                <th>方向</th>
                <th>盎司</th>
                <th>开仓价差</th>
                <th>止盈 / 止损</th>
                <th>TP / SL 执行</th>
                <th>MT5 Ticket</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="plans.length === 0">
                <td colspan="8">暂无真实退出计划</td>
              </tr>
              <tr v-for="plan in plans" :key="plan.planId">
                <td :class="plan.direction === 'LONG_SPREAD' ? 'is-long' : 'is-short'">
                  {{ plan.direction === 'LONG_SPREAD' ? '多价差' : '空价差' }}
                </td>
                <td>{{ formatNumber(plan.quantityOz) }}</td>
                <td>{{ formatSigned(plan.entrySpread) }}</td>
                <td>
                  {{ formatSigned(plan.takeProfitSpread) }} /
                  {{ formatSigned(plan.stopLossSpread) }}
                </td>
                <td>
                  {{
                    executionSelectionLabel(
                      plan.takeProfitExecutionMode,
                      plan.takeProfitLimitStrategy,
                    )
                  }}
                  /
                  {{
                    executionSelectionLabel(plan.stopLossExecutionMode, plan.stopLossLimitStrategy)
                  }}
                </td>
                <td>{{ plan.mt5PositionId }}</td>
                <td>{{ planStatusLabel(plan.status) }}</td>
                <td>
                  <button
                    type="button"
                    class="market-lifecycle__close"
                    :disabled="loading || plan.status !== 'active' || Boolean(closeValidationError)"
                    @click="submitClose(plan)"
                  >
                    {{ closeButtonLabel }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <section v-if="limitEvidence" class="market-lifecycle__evidence">
      <div>
        <span>限价策略 / TIF</span>
        <strong>
          {{ limitStrategyLabel(limitEvidence.limitStrategy) }} /
          {{ limitEvidence.timeInForce }}
        </strong>
      </div>
      <div>
        <span>限价方向</span>
        <strong>{{ limitDirectionLabel(limitEvidence.direction) }}</strong>
      </div>
      <div>
        <span>限制 / 可成交价差</span>
        <strong>
          {{ formatSigned(limitEvidence.limitSpread) }} /
          {{ formatSigned(limitEvidence.executableSpread) }}
        </strong>
      </div>
      <div>
        <span>Bybit 硬价格边界</span>
        <strong>{{ formatNumber(limitEvidence.bybitLimitPrice) }}</strong>
      </div>
      <div>
        <span>MT5 参考 / Tick / 预留</span>
        <strong>
          {{ formatNumber(limitEvidence.mt5ReferencePrice) }} /
          {{ formatNumber(limitEvidence.bybitTickSize) }} /
          {{ formatNumber(limitEvidence.hedgeReserve) }}
        </strong>
      </div>
    </section>

    <footer class="market-lifecycle__footer">
      <span>PostOnly 仅在精确全成后放行 MT5；IOC 尚未接入。</span>
      <strong v-if="message" :class="messageTone">{{ message }}</strong>
    </footer>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import {
    closeCrossSpreadMarket,
    getCrossSpreadExitPlans,
    openCrossSpreadMarket,
    type CrossSpreadDirection,
    type CrossSpreadExecutionMode,
    type CrossSpreadExitPlanResult,
    type CrossSpreadLimitExecutionResult,
    type CrossSpreadLimitStrategy,
  } from '@/api/platform/crossSpreadLifecycle';

  defineProps<{
    leftLegSymbol: string;
    rightLegSymbol: string;
  }>();

  const direction = ref<CrossSpreadDirection>('LONG_SPREAD');
  const openExecutionMode = ref<CrossSpreadExecutionMode>('market');
  const openLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const takeProfitExecutionMode = ref<CrossSpreadExecutionMode>('market');
  const takeProfitLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const stopLossExecutionMode = ref<CrossSpreadExecutionMode>('market');
  const stopLossLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const closeExecutionMode = ref<CrossSpreadExecutionMode>('market');
  const closeLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const quantityOz = ref('1');
  const openLimitSpread = ref('-0.8');
  const closeLimitSpread = ref('-1.2');
  const takeProfitSpread = ref('0');
  const stopLossSpread = ref('-3');
  const plans = ref<CrossSpreadExitPlanResult[]>([]);
  const limitEvidence = ref<CrossSpreadLimitExecutionResult | null>(null);
  const loading = ref(false);
  const message = ref('');
  const messageTone = ref<'is-success' | 'is-error' | 'is-warn'>('is-success');

  const activePlans = computed(() => plans.value.filter((plan) => plan.status === 'active'));
  const usesPostOnly = computed(
    () =>
      (openExecutionMode.value === 'limit' && openLimitStrategy.value === 'post_only_chase') ||
      (takeProfitExecutionMode.value === 'limit' &&
        takeProfitLimitStrategy.value === 'post_only_chase') ||
      (stopLossExecutionMode.value === 'limit' &&
        stopLossLimitStrategy.value === 'post_only_chase'),
  );
  const executableSpreadLabel = computed(() =>
    direction.value === 'LONG_SPREAD'
      ? '买 Bybit / 卖 MT5：BY Ask - MT5 Bid'
      : '卖 Bybit / 买 MT5：BY Bid - MT5 Ask',
  );
  const thresholdRuleLabel = computed(() =>
    direction.value === 'LONG_SPREAD'
      ? '止盈：平仓价差 ≥ 止盈值；止损：平仓价差 ≤ 止损值'
      : '止盈：平仓价差 ≤ 止盈值；止损：平仓价差 ≥ 止损值',
  );
  const limitRuleLabel = computed(() => {
    const strategy = limitStrategyLabel(openLimitStrategy.value);
    return direction.value === 'LONG_SPREAD'
      ? `${strategy} 不能突破买入价差最大限制`
      : `${strategy} 不能突破卖出价差最小限制`;
  });
  const openButtonLabel = computed(() => {
    if (loading.value) return '执行中...';
    const action = direction.value === 'LONG_SPREAD' ? '开多价差' : '开空价差';
    return openExecutionMode.value === 'limit'
      ? `${limitStrategyLabel(openLimitStrategy.value)} ${action}`
      : `市价${action}`;
  });
  const closeButtonLabel = computed(() =>
    closeExecutionMode.value === 'limit'
      ? `${limitStrategyLabel(closeLimitStrategy.value)} 平仓`
      : '市价平仓',
  );
  const validationError = computed(() => {
    const quantity = Number(quantityOz.value);
    const takeProfit = Number(takeProfitSpread.value);
    const stopLoss = Number(stopLossSpread.value);
    if (!Number.isFinite(quantity) || quantity <= 0) return '数量必须大于 0';
    if (!Number.isFinite(takeProfit) || !Number.isFinite(stopLoss)) {
      return '止盈止损必须是有效数字';
    }
    if (openExecutionMode.value === 'limit' && !Number.isFinite(Number(openLimitSpread.value))) {
      return '限价限制价差必须是有效数字';
    }
    if (direction.value === 'LONG_SPREAD' && takeProfit <= stopLoss) {
      return '多价差的止盈平仓价差必须高于止损平仓价差';
    }
    if (direction.value === 'SHORT_SPREAD' && takeProfit >= stopLoss) {
      return '空价差的止盈平仓价差必须低于止损平仓价差';
    }
    return '';
  });
  const closeValidationError = computed(() => {
    if (closeExecutionMode.value !== 'limit') return '';
    return Number.isFinite(Number(closeLimitSpread.value)) ? '' : '限价平仓限制价差必须是有效数字';
  });

  function applyDirectionDefaults() {
    if (direction.value === 'LONG_SPREAD') {
      takeProfitSpread.value = '0';
      stopLossSpread.value = '-3';
      openLimitSpread.value = '-0.8';
    } else {
      takeProfitSpread.value = '-3';
      stopLossSpread.value = '0';
      openLimitSpread.value = '-1.2';
    }
  }

  async function refreshPlans() {
    loading.value = true;
    try {
      plans.value = await getCrossSpreadExitPlans();
      setMessage('退出计划已刷新', 'is-success');
    } catch (error: unknown) {
      setMessage(resolveError(error, '退出计划读取失败'), 'is-error');
    } finally {
      loading.value = false;
    }
  }

  async function submitOpen() {
    if (validationError.value) return;
    loading.value = true;
    limitEvidence.value = null;
    try {
      const result = await openCrossSpreadMarket({
        direction: direction.value,
        quantityOz: quantityOz.value,
        takeProfitSpread: takeProfitSpread.value,
        stopLossSpread: stopLossSpread.value,
        executionMode: openExecutionMode.value,
        limitStrategy: openLimitStrategy.value,
        takeProfitExecutionMode: takeProfitExecutionMode.value,
        stopLossExecutionMode: stopLossExecutionMode.value,
        takeProfitLimitStrategy: takeProfitLimitStrategy.value,
        stopLossLimitStrategy: stopLossLimitStrategy.value,
        ...(openExecutionMode.value === 'limit' ? { limitSpread: openLimitSpread.value } : {}),
      });
      limitEvidence.value = result.limitExecution || null;
      if (result.executionBatch.status === 'hedged' && result.exitPlan) {
        setMessage(`开仓与退出计划已建立：${result.exitPlan.planId}`, 'is-success');
      } else {
        setMessage(
          result.executionBatch.failureReason || '开仓未形成完整退出计划，请检查执行批次',
          'is-warn',
        );
      }
      await loadPlansSilently();
    } catch (error: unknown) {
      setMessage(resolveError(error, '合成开仓失败'), 'is-error');
    } finally {
      loading.value = false;
    }
  }

  async function submitClose(plan: CrossSpreadExitPlanResult) {
    if (closeValidationError.value) return;
    loading.value = true;
    limitEvidence.value = null;
    try {
      const result = await closeCrossSpreadMarket(
        plan.planId,
        closeExecutionMode.value,
        closeExecutionMode.value === 'limit' ? closeLimitSpread.value : undefined,
        closeLimitStrategy.value,
      );
      limitEvidence.value = result.limitExecution || null;
      if (result.executionBatch.status === 'hedged' && result.exitPlan.status === 'closed') {
        setMessage(`退出计划 ${plan.planId} 已完成平仓`, 'is-success');
      } else if (result.exitPlan.status === 'active') {
        setMessage('限价未成交，退出计划仍保持活动状态', 'is-warn');
      } else {
        setMessage(
          result.executionBatch.failureReason || '平仓未完全对冲，已进入人工介入',
          'is-warn',
        );
      }
      await loadPlansSilently();
    } catch (error: unknown) {
      setMessage(resolveError(error, '合成平仓失败'), 'is-error');
      await loadPlansSilently();
    } finally {
      loading.value = false;
    }
  }

  async function loadPlansSilently() {
    try {
      plans.value = await getCrossSpreadExitPlans();
    } catch {
      // Preserve the last known plan list; the visible action reports the primary result.
    }
  }

  function setMessage(nextMessage: string, nextTone: 'is-success' | 'is-error' | 'is-warn') {
    message.value = nextMessage;
    messageTone.value = nextTone;
  }

  function resolveError(error: unknown, fallback: string) {
    if (typeof error === 'object' && error !== null) {
      const candidate = error as {
        message?: string;
        response?: { data?: { detail?: string | Array<{ msg?: string }> } };
      };
      const detail = candidate.response?.data?.detail;
      if (Array.isArray(detail)) {
        return (
          detail
            .map((item) => item.msg)
            .filter(Boolean)
            .join('；') || fallback
        );
      }
      return detail || candidate.message || fallback;
    }
    return fallback;
  }

  function formatNumber(value: string) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed.toFixed(2) : '--';
  }

  function formatSigned(value: string) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return '--';
    return `${parsed > 0 ? '+' : ''}${parsed.toFixed(2)}`;
  }

  function limitDirectionLabel(directionValue: CrossSpreadLimitExecutionResult['direction']) {
    return directionValue === 'BUY_BYBIT_SELL_MT5' ? '买 Bybit / 卖 MT5' : '卖 Bybit / 买 MT5';
  }

  function limitStrategyLabel(strategy: CrossSpreadLimitStrategy) {
    return strategy === 'post_only_chase' ? 'PostOnly Chase' : 'FOK';
  }

  function executionSelectionLabel(
    mode: CrossSpreadExecutionMode,
    strategy: CrossSpreadLimitStrategy,
  ) {
    return mode === 'market' ? '市价' : limitStrategyLabel(strategy);
  }

  function planStatusLabel(status: CrossSpreadExitPlanResult['status']) {
    const labels: Record<CrossSpreadExitPlanResult['status'], string> = {
      active: '监控中',
      triggered: '已触发',
      closing: '平仓中',
      closed: '已平仓',
      manual_intervention: '人工介入',
    };
    return labels[status];
  }

  onMounted(loadPlansSilently);
</script>

<style scoped lang="less">
  .market-lifecycle {
    margin-top: 14px;
    padding: 18px;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
    color: #10203f;
  }

  .market-lifecycle__header,
  .market-lifecycle__card-head,
  .market-lifecycle__footer,
  .market-lifecycle__status {
    display: flex;
    align-items: center;
  }

  .market-lifecycle__header,
  .market-lifecycle__card-head,
  .market-lifecycle__footer {
    justify-content: space-between;
    gap: 16px;
  }

  .market-lifecycle__header {
    margin-bottom: 14px;
  }

  .market-lifecycle__header p,
  .market-lifecycle__card-head p {
    margin: 0;
    color: #7b8ba5;
    font-size: 12px;
  }

  .market-lifecycle__header h3,
  .market-lifecycle__card-head h4 {
    margin: 4px 0 0;
    color: #13233f;
  }

  .market-lifecycle__status {
    gap: 10px;
    font-size: 12px;
  }

  .market-lifecycle__status strong {
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(39, 184, 115, 0.12);
    color: #1a9b58;
  }

  .market-lifecycle__grid {
    display: grid;
    grid-template-columns: minmax(300px, 0.72fr) minmax(560px, 1.28fr);
    gap: 14px;
  }

  .market-lifecycle__card {
    padding: 15px;
    border: 1px solid #edf0f5;
    border-radius: 14px;
    background: #ffffff;
  }

  .market-lifecycle__card-head {
    margin-bottom: 12px;
  }

  .market-lifecycle__card-head button,
  .market-lifecycle__close {
    border: 1px solid #d8e1ef;
    border-radius: 9px;
    background: #ffffff;
    color: #31527f;
    cursor: pointer;
  }

  .market-lifecycle__card-head button {
    padding: 7px 11px;
  }

  .market-lifecycle__form,
  .market-lifecycle__close-controls {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .market-lifecycle__form label,
  .market-lifecycle__close-controls label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    color: #637491;
    font-size: 12px;
  }

  .market-lifecycle__form input,
  .market-lifecycle__form select,
  .market-lifecycle__close-controls input,
  .market-lifecycle__close-controls select {
    height: 38px;
    padding: 0 10px;
    border: 1px solid #e1e7f0;
    border-radius: 9px;
    background: #fbfcfe;
    color: #172946;
    outline: none;
  }

  .market-lifecycle__close-controls {
    margin-bottom: 10px;
    padding: 10px;
    border-radius: 10px;
    background: #f8fafc;
  }

  .market-lifecycle__close-controls small {
    align-self: end;
    color: #c83c3c;
  }

  .market-lifecycle__formula {
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin: 12px 0;
    padding: 10px;
    border-radius: 10px;
    background: #f4f7fb;
  }

  .market-lifecycle__formula span,
  .market-lifecycle__formula small {
    color: #71819b;
    font-size: 12px;
  }

  .market-lifecycle__primary {
    width: 100%;
    height: 40px;
    border: 0;
    border-radius: 10px;
    background: #214f93;
    color: #ffffff;
    font-weight: 700;
    cursor: pointer;
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }

  .market-lifecycle__error {
    margin: 8px 0 0;
    color: #c83c3c;
    font-size: 12px;
  }

  .market-lifecycle__table-wrap {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 10px 8px;
    border-bottom: 1px solid #edf0f5;
    text-align: left;
    white-space: nowrap;
  }

  th {
    color: #71819b;
    font-weight: 600;
  }

  .is-long {
    color: #159b5e;
  }

  .is-short {
    color: #d04444;
  }

  .market-lifecycle__close {
    padding: 6px 9px;
  }

  .market-lifecycle__evidence {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
    margin-top: 12px;
    padding: 12px;
    border: 1px solid #dfe7f2;
    border-radius: 12px;
    background: #f7faff;
  }

  .market-lifecycle__evidence div {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .market-lifecycle__evidence span {
    color: #71819b;
    font-size: 11px;
  }

  .market-lifecycle__evidence strong {
    color: #1b3f72;
    font-size: 12px;
  }

  .market-lifecycle__footer {
    margin-top: 12px;
    color: #7787a1;
    font-size: 12px;
  }

  .market-lifecycle__footer strong {
    text-align: right;
  }

  .is-success {
    color: #159b5e;
  }

  .is-warn {
    color: #a96a13;
  }

  .is-error {
    color: #c83c3c;
  }

  @media (max-width: 1180px) {
    .market-lifecycle__grid,
    .market-lifecycle__evidence {
      grid-template-columns: 1fr;
    }
  }
</style>
