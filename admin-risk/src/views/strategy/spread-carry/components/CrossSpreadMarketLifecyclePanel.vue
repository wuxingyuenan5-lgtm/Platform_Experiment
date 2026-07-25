<template>
  <section class="market-lifecycle">
    <header class="market-lifecycle__header">
      <div>
        <p>MARKET LIFECYCLE</p>
        <h3>市价生命周期运行区</h3>
      </div>
      <div class="market-lifecycle__status">
        <span>{{ leftLegSymbol }} / {{ rightLegSymbol }}</span>
        <strong>仅市价已接入</strong>
      </div>
    </header>

    <div class="market-lifecycle__grid">
      <section class="market-lifecycle__card">
        <div class="market-lifecycle__card-head">
          <div>
            <h4>市价开仓</h4>
            <p>Bybit 确认成交后，MT5 按实际数量对冲</p>
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
            <span>数量（盎司）</span>
            <input v-model="quantityOz" inputmode="decimal" />
          </label>
          <label>
            <span>止盈平仓价差</span>
            <input v-model="takeProfitSpread" inputmode="decimal" />
          </label>
          <label>
            <span>止损平仓价差</span>
            <input v-model="stopLossSpread" inputmode="decimal" />
          </label>
        </div>

        <div class="market-lifecycle__formula">
          <span>触发观察</span>
          <strong>{{ executableSpreadLabel }}</strong>
          <small>{{ thresholdRuleLabel }}</small>
        </div>

        <button
          type="button"
          class="market-lifecycle__primary"
          :disabled="loading || Boolean(validationError)"
          @click="submitOpen"
        >
          {{
            loading ? '执行中...' : direction === 'LONG_SPREAD' ? '市价开多价差' : '市价开空价差'
          }}
        </button>
        <p v-if="validationError" class="market-lifecycle__error">{{ validationError }}</p>
      </section>

      <section class="market-lifecycle__card market-lifecycle__card--plans">
        <div class="market-lifecycle__card-head">
          <div>
            <h4>真实退出计划</h4>
            <p>止盈止损达到指定可执行平仓价差后，按市价平仓</p>
          </div>
          <span>{{ activePlans.length }} 笔活动计划</span>
        </div>

        <div class="market-lifecycle__table-wrap">
          <table>
            <thead>
              <tr>
                <th>方向</th>
                <th>盎司</th>
                <th>开仓价差</th>
                <th>止盈 / 止损</th>
                <th>MT5 Ticket</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="plans.length === 0">
                <td colspan="7">暂无真实退出计划</td>
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
                <td>{{ plan.mt5PositionId }}</td>
                <td>{{ planStatusLabel(plan.status) }}</td>
                <td>
                  <button
                    type="button"
                    class="market-lifecycle__close"
                    :disabled="loading || plan.status !== 'active'"
                    @click="submitClose(plan)"
                  >
                    市价平仓
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <footer class="market-lifecycle__footer">
      <span>限价开仓、限价平仓及限价止盈止损继续保留在原设计中，本阶段尚未接入。</span>
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
    type CrossSpreadExitPlanResult,
  } from '@/api/platform/crossSpreadLifecycle';

  defineProps<{
    leftLegSymbol: string;
    rightLegSymbol: string;
  }>();

  const direction = ref<CrossSpreadDirection>('LONG_SPREAD');
  const quantityOz = ref('100');
  const takeProfitSpread = ref('0');
  const stopLossSpread = ref('-3');
  const plans = ref<CrossSpreadExitPlanResult[]>([]);
  const loading = ref(false);
  const message = ref('');
  const messageTone = ref<'is-success' | 'is-error' | 'is-warn'>('is-success');

  const activePlans = computed(() => plans.value.filter((plan) => plan.status === 'active'));
  const executableSpreadLabel = computed(() =>
    direction.value === 'LONG_SPREAD'
      ? '做空价差（BY Bid - MT5 Ask）'
      : '做多价差（BY Ask - MT5 Bid）',
  );
  const thresholdRuleLabel = computed(() =>
    direction.value === 'LONG_SPREAD'
      ? '止盈：平仓价差 ≥ 止盈值；止损：平仓价差 ≤ 止损值'
      : '止盈：平仓价差 ≤ 止盈值；止损：平仓价差 ≥ 止损值',
  );
  const validationError = computed(() => {
    const quantity = Number(quantityOz.value);
    const takeProfit = Number(takeProfitSpread.value);
    const stopLoss = Number(stopLossSpread.value);
    if (!Number.isFinite(quantity) || quantity <= 0) return '数量必须大于 0';
    if (!Number.isFinite(takeProfit) || !Number.isFinite(stopLoss)) return '止盈止损必须是有效数字';
    if (direction.value === 'LONG_SPREAD' && takeProfit <= stopLoss) {
      return '多价差的止盈平仓价差必须高于止损平仓价差';
    }
    if (direction.value === 'SHORT_SPREAD' && takeProfit >= stopLoss) {
      return '空价差的止盈平仓价差必须低于止损平仓价差';
    }
    return '';
  });

  function applyDirectionDefaults() {
    if (direction.value === 'LONG_SPREAD') {
      takeProfitSpread.value = '0';
      stopLossSpread.value = '-3';
    } else {
      takeProfitSpread.value = '-3';
      stopLossSpread.value = '0';
    }
  }

  async function refreshPlans() {
    loading.value = true;
    try {
      plans.value = await getCrossSpreadExitPlans();
      setMessage('退出计划已刷新', 'is-success');
    } catch (error: any) {
      setMessage(resolveError(error, '退出计划读取失败'), 'is-error');
    } finally {
      loading.value = false;
    }
  }

  async function submitOpen() {
    if (validationError.value) return;
    loading.value = true;
    try {
      const result = await openCrossSpreadMarket({
        direction: direction.value,
        quantityOz: quantityOz.value,
        takeProfitSpread: takeProfitSpread.value,
        stopLossSpread: stopLossSpread.value,
        executionMode: 'market',
      });
      if (result.executionBatch.status === 'hedged' && result.exitPlan) {
        setMessage(`开仓与退出计划已建立：${result.exitPlan.planId}`, 'is-success');
      } else {
        setMessage(
          result.executionBatch.failureReason || '开仓未形成完整退出计划，请检查执行批次',
          'is-warn',
        );
      }
      await loadPlansSilently();
    } catch (error: any) {
      setMessage(resolveError(error, '市价开仓失败'), 'is-error');
    } finally {
      loading.value = false;
    }
  }

  async function submitClose(plan: CrossSpreadExitPlanResult) {
    loading.value = true;
    try {
      const result = await closeCrossSpreadMarket(plan.planId, 'market');
      if (result.executionBatch.status === 'hedged' && result.exitPlan.status === 'closed') {
        setMessage(`退出计划 ${plan.planId} 已市价平仓`, 'is-success');
      } else {
        setMessage(
          result.executionBatch.failureReason || '平仓未完全对冲，已进入人工介入',
          'is-warn',
        );
      }
      await loadPlansSilently();
    } catch (error: any) {
      setMessage(resolveError(error, '市价平仓失败'), 'is-error');
      await loadPlansSilently();
    } finally {
      loading.value = false;
    }
  }

  async function loadPlansSilently() {
    try {
      plans.value = await getCrossSpreadExitPlans();
    } catch {
      // Preserve the last known plan list; the visible action already reports the primary result.
    }
  }

  function setMessage(nextMessage: string, nextTone: 'is-success' | 'is-error' | 'is-warn') {
    message.value = nextMessage;
    messageTone.value = nextTone;
  }

  function resolveError(error: any, fallback: string) {
    return error?.response?.data?.detail || error?.message || fallback;
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

  .market-lifecycle__form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .market-lifecycle__form label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    color: #637491;
    font-size: 12px;
  }

  .market-lifecycle__form input,
  .market-lifecycle__form select {
    height: 38px;
    padding: 0 10px;
    border: 1px solid #e1e7f0;
    border-radius: 9px;
    background: #fbfcfe;
    color: #172946;
    outline: none;
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
    .market-lifecycle__grid {
      grid-template-columns: 1fr;
    }
  }
</style>
