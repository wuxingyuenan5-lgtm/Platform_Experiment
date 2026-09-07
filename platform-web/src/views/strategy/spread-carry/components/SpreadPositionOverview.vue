<template>
  <section class="cross-card cross-card--overview">
    <div class="card-head">
      <div class="overview-title">
        <h3>价差持仓总览</h3>
      </div>
    </div>

    <div v-if="overviewRows.length" class="overview-range">
      <div class="overview-range__meta">
        <span class="green">多 {{ formatPercent(longExposureRatio) }}</span>
        <span class="red">{{ formatPercent(shortExposureRatio) }} 空</span>
      </div>
      <div class="overview-range__track">
        <div
          class="overview-range__green"
          :style="{ width: formatPercent(longExposureRatio) }"
        ></div>
        <div
          class="overview-range__red"
          :style="{ width: formatPercent(shortExposureRatio) }"
        ></div>
      </div>
    </div>

    <div v-if="overviewRows.length" class="overview-summary overview-summary--top">
      <div class="overview-summary__item">
        <span>双边总损益</span>
        <strong :class="totalPnlTone">{{ formatSignedNumber(totalPnlUsdt) }} USDT</strong>
      </div>
      <div class="overview-summary__item">
        <span>单边总损益</span>
        <strong>
          BY: <em :class="pnlTone(legPnlByUsdt)">{{ formatSignedNumber(legPnlByUsdt) }}</em> | MT5:
          <em :class="pnlTone(legPnlMt5Usdt)">{{ formatSignedNumber(legPnlMt5Usdt) }}</em>
        </strong>
      </div>
      <div class="overview-summary__item">
        <span>单边爆仓价</span>
        <strong class="red">BY: {{ liquidationByText }} | MT5: {{ liquidationMt5Text }}</strong>
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
          <th>权益 / 可用</th>
          <th>持仓时长</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="overviewRows.length === 0">
          <td colspan="15">{{ emptyText }}</td>
        </tr>
        <template v-for="row in overviewRows" :key="row.id">
          <tr>
            <td :class="row.direction === '多头' ? 'green' : 'red'">{{ row.direction }}</td>
            <td>{{ formatNumber(row.qty, 2) }}</td>
            <td>{{ row.entrySpread }}</td>
            <td :class="spreadTone(row.currentSpread)">{{ row.currentSpread }}</td>
            <td>{{ row.detail }}</td>
            <td>{{ row.pnl }}</td>
            <td>{{ row.legPnl }}</td>
            <td>
              <button
                v-if="row.exitPlanId"
                type="button"
                class="exit-threshold-button"
                @click="beginExitPlanEdit(row)"
              >
                {{ row.takeProfit }}
              </button>
              <span v-else>{{ row.takeProfit }}</span>
            </td>
            <td>
              <button
                v-if="row.exitPlanId"
                type="button"
                class="exit-threshold-button"
                @click="beginExitPlanEdit(row)"
              >
                {{ row.stopLoss }}
              </button>
              <span v-else>{{ row.stopLoss }}</span>
            </td>
            <td>{{ row.liquidation }}</td>
            <td>{{ row.margin }}</td>
            <td>{{ row.openTime }}</td>
            <td>{{ row.accountRisk }}</td>
            <td>{{ row.holdingTime }}</td>
            <td>{{ row.status }}</td>
          </tr>
          <tr v-if="editingPlanId === row.exitPlanId" class="exit-threshold-editor-row">
            <td colspan="15">
              <form class="exit-threshold-editor" @submit.prevent="saveExitPlanEdit">
                <strong>修改止盈止损</strong>
                <label>
                  止盈价差
                  <input v-model.trim="takeProfitInput" inputmode="decimal" placeholder="不修改" />
                </label>
                <label>
                  止损价差
                  <input v-model.trim="stopLossInput" inputmode="decimal" placeholder="不修改" />
                </label>
                <label>
                  止盈执行
                  <select v-model="takeProfitExecutionMode">
                    <option value="market">市价</option>
                    <option value="limit">限价</option>
                  </select>
                </label>
                <label v-if="takeProfitExecutionMode === 'limit'">
                  止盈限价策略
                  <select v-model="takeProfitLimitStrategy">
                    <option value="fok">FOK 全成全撤</option>
                    <option value="post_only_chase">PostOnly Chase</option>
                  </select>
                </label>
                <label>
                  止损执行
                  <select v-model="stopLossExecutionMode">
                    <option value="market">市价</option>
                    <option value="limit">限价</option>
                  </select>
                </label>
                <label v-if="stopLossExecutionMode === 'limit'">
                  止损限价策略
                  <select v-model="stopLossLimitStrategy">
                    <option value="fok">FOK 全成全撤</option>
                    <option value="post_only_chase">PostOnly Chase</option>
                  </select>
                </label>
                <span class="exit-threshold-editor__hint">
                  触发时针对该计划当前剩余
                  {{
                    formatNumber(row.qty, 2)
                  }}
                  盎司；手动部分平仓后的剩余数量继续沿用本设置。保存不会立即平仓。
                </span>
                <p v-if="saveError" class="exit-threshold-editor__error">{{ saveError }}</p>
                <button type="button" class="exit-threshold-editor__cancel" @click="cancelEdit">
                  取消
                </button>
                <button type="submit" class="exit-threshold-editor__save" :disabled="saving">
                  {{ saving ? '保存中…' : '保存' }}
                </button>
              </form>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type {
    CrossSpreadExecutionMode,
    CrossSpreadExitPlanThresholdUpdateInput,
    CrossSpreadLimitStrategy,
  } from '@/api/platform/crossSpreadLifecycle';

  interface OverviewRow {
    id: string;
    exitPlanId: string | null;
    takeProfitExecutionMode: CrossSpreadExecutionMode | null;
    stopLossExecutionMode: CrossSpreadExecutionMode | null;
    takeProfitLimitStrategy: CrossSpreadLimitStrategy | null;
    stopLossLimitStrategy: CrossSpreadLimitStrategy | null;
    direction: string;
    qty: number;
    entrySpread: string;
    currentSpread: string;
    detail: string;
    accountStatus: string;
    accountRisk: string;
    pnl: string;
    legPnl: string;
    takeProfit: string;
    stopLoss: string;
    liquidation: string;
    margin: string;
    openTime: string;
    holdingTime: string;
    status: string;
  }

  const props = defineProps<{
    overviewRows: OverviewRow[];
    emptyText: string;
    longSpread: string | number | null | undefined;
    updateExitPlan: (
      planId: string,
      input: CrossSpreadExitPlanThresholdUpdateInput,
    ) => Promise<void>;
  }>();

  const editingPlanId = ref<string | null>(null);
  const takeProfitInput = ref('');
  const stopLossInput = ref('');
  const takeProfitExecutionMode = ref<CrossSpreadExecutionMode>('market');
  const stopLossExecutionMode = ref<CrossSpreadExecutionMode>('market');
  const takeProfitLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const stopLossLimitStrategy = ref<CrossSpreadLimitStrategy>('fok');
  const saving = ref(false);
  const saveError = ref('');

  function editableValue(value: string) {
    return value === '--' ? '' : value.replace(/,/g, '');
  }

  function beginExitPlanEdit(row: OverviewRow) {
    if (!row.exitPlanId || saving.value) return;
    editingPlanId.value = row.exitPlanId;
    takeProfitInput.value = editableValue(row.takeProfit);
    stopLossInput.value = editableValue(row.stopLoss);
    takeProfitExecutionMode.value = row.takeProfitExecutionMode || 'market';
    stopLossExecutionMode.value = row.stopLossExecutionMode || 'market';
    takeProfitLimitStrategy.value = row.takeProfitLimitStrategy || 'fok';
    stopLossLimitStrategy.value = row.stopLossLimitStrategy || 'fok';
    saveError.value = '';
  }

  function cancelEdit() {
    if (saving.value) return;
    editingPlanId.value = null;
    takeProfitInput.value = '';
    stopLossInput.value = '';
    saveError.value = '';
  }

  function validThreshold(value: string) {
    if (!value) return undefined;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? value : null;
  }

  async function saveExitPlanEdit() {
    const planId = editingPlanId.value;
    if (!planId || saving.value) return;
    const takeProfitSpread = validThreshold(takeProfitInput.value);
    const stopLossSpread = validThreshold(stopLossInput.value);
    if (takeProfitSpread === null || stopLossSpread === null) return;
    const update: CrossSpreadExitPlanThresholdUpdateInput = {
      ...(takeProfitSpread === undefined ? {} : { takeProfitSpread }),
      ...(stopLossSpread === undefined ? {} : { stopLossSpread }),
      takeProfitExecutionMode: takeProfitExecutionMode.value,
      stopLossExecutionMode: stopLossExecutionMode.value,
      takeProfitLimitStrategy: takeProfitLimitStrategy.value,
      stopLossLimitStrategy: stopLossLimitStrategy.value,
    };
    saving.value = true;
    saveError.value = '';
    let saved = false;
    try {
      await props.updateExitPlan(planId, update);
      saved = true;
    } catch (error: unknown) {
      saveError.value = error instanceof Error ? error.message : '退出计划更新失败';
    } finally {
      saving.value = false;
    }
    if (saved) cancelEdit();
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

  function formatSignedNumber(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return '--';
    return formatNumber(value, 2);
  }

  function parseLegPart(text: string, prefix: 'BY' | 'MT5'): number | null {
    if (!text) return null;
    const parts = text.split(' | ');
    for (const part of parts) {
      const t = part.trim();
      if (t.startsWith(prefix + ': ')) {
        const num = parseFloat(t.slice((prefix + ': ').length).replace(/,/g, ''));
        return Number.isFinite(num) ? num : null;
      }
    }
    return null;
  }

  function extractLegText(text: string, prefix: 'BY' | 'MT5'): string {
    if (!text) return '--';
    const parts = text.split(' | ');
    for (const part of parts) {
      const t = part.trim();
      if (t.startsWith(prefix + ': ')) return t.slice((prefix + ': ').length);
    }
    return '--';
  }

  const totalPnlUsdt = computed<number | null>(() => {
    let sum = 0;
    let hasAny = false;
    for (const row of props.overviewRows) {
      const v = parseOptionalNumber(row.pnl);
      if (v !== null) {
        sum += v;
        hasAny = true;
      }
    }
    return hasAny ? sum : null;
  });

  const legPnlByUsdt = computed<number | null>(() => {
    let sum = 0;
    let hasAny = false;
    for (const row of props.overviewRows) {
      const v = parseLegPart(row.legPnl, 'BY');
      if (v !== null) {
        sum += v;
        hasAny = true;
      }
    }
    return hasAny ? sum : null;
  });

  const legPnlMt5Usdt = computed<number | null>(() => {
    let sum = 0;
    let hasAny = false;
    for (const row of props.overviewRows) {
      const v = parseLegPart(row.legPnl, 'MT5');
      if (v !== null) {
        sum += v;
        hasAny = true;
      }
    }
    return hasAny ? sum : null;
  });

  const liquidationByText = computed<string>(() => {
    if (props.overviewRows.length !== 1) return props.overviewRows.length ? '详见持仓行' : '--';
    return extractLegText(props.overviewRows[0].liquidation, 'BY');
  });

  const liquidationMt5Text = computed<string>(() => {
    if (props.overviewRows.length !== 1) return props.overviewRows.length ? '详见持仓行' : '--';
    return extractLegText(props.overviewRows[0].liquidation, 'MT5');
  });

  const totalPnlTone = computed<string>(() => {
    const v = totalPnlUsdt.value;
    if (v === null) return '';
    return v >= 0 ? 'green' : 'red';
  });

  function pnlTone(value: number | null | undefined) {
    if (value === null || value === undefined || !Number.isFinite(value)) return '';
    return value >= 0 ? 'green' : 'red';
  }

  function spreadTone(value: string | number | null | undefined) {
    const parsed = parseOptionalNumber(value);
    if (parsed === null) return '';
    return parsed <= 0 ? 'green' : 'red';
  }

  const totalExposure = computed(() =>
    props.overviewRows.reduce((sum, row) => sum + Math.max(row.qty, 0), 0),
  );

  const longExposure = computed(() =>
    props.overviewRows.reduce(
      (sum, row) => sum + (row.direction === '多头' ? Math.max(row.qty, 0) : 0),
      0,
    ),
  );

  const longExposureRatio = computed(() => {
    if (!totalExposure.value) return 0;
    return (longExposure.value / totalExposure.value) * 100;
  });

  const shortExposureRatio = computed(() => {
    if (!totalExposure.value) return 0;
    return 100 - longExposureRatio.value;
  });

  function formatPercent(value: number) {
    return `${Math.max(0, Math.min(100, value)).toFixed(2)}%`;
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

  .cross-card--overview {
    padding-bottom: 14px;
  }

  .card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .overview-title {
    display: flex;
    align-items: center;
  }

  .overview-title h3 {
    color: #162845;
    font-size: 21px;
    font-weight: 800;
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
    display: flex;
    position: relative;
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
    font-size: 24px;
    font-weight: 600;
    line-height: 1.1;
    white-space: nowrap;
  }

  .overview-summary__item strong {
    font-size: 24px;
    font-weight: 600;
    line-height: 1.1;
    white-space: nowrap;
  }

  .overview-summary__item strong em {
    font: inherit;
  }

  .overview-table {
    display: block;
    width: 100%;
    max-width: 100%;
    overflow-x: auto;
    border-collapse: collapse;
  }

  .overview-table th,
  .overview-table td {
    padding: 13px 10px;
    border-bottom: 1px solid #d8e2ec;
    font-size: 13px;
    text-align: left;
    white-space: nowrap;
  }

  .exit-threshold-button {
    padding: 0;
    border: 0;
    border-bottom: 1px dashed #7f8fa7;
    color: inherit;
    background: transparent;
    cursor: pointer;
    font: inherit;
  }

  .exit-threshold-button:hover {
    border-bottom-color: #276ef1;
    color: #276ef1;
  }

  .exit-threshold-editor-row td {
    padding: 10px;
    background: #f7faff;
  }

  .exit-threshold-editor {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
  }

  .exit-threshold-editor label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #52647d;
  }

  .exit-threshold-editor input {
    width: 92px;
    padding: 5px 7px;
    border: 1px solid #cbd8ea;
    border-radius: 6px;
    color: #22324d;
    background: #fff;
    font: inherit;
  }

  .exit-threshold-editor select {
    padding: 5px 7px;
    border: 1px solid #cbd8ea;
    border-radius: 6px;
    color: #22324d;
    background: #fff;
    font: inherit;
  }

  .exit-threshold-editor__hint {
    color: #6b7d96;
    font-size: 12px;
  }

  .exit-threshold-editor__error {
    flex-basis: 100%;
    margin: 0;
    color: #d9363e;
    font-size: 12px;
  }

  .exit-threshold-editor button {
    padding: 5px 10px;
    border-radius: 6px;
    font: inherit;
    cursor: pointer;
  }

  .exit-threshold-editor__cancel {
    border: 1px solid #cbd8ea;
    color: #52647d;
    background: #fff;
  }

  .exit-threshold-editor__save {
    border: 1px solid #276ef1;
    color: #fff;
    background: #276ef1;
  }

  .exit-threshold-editor__save:disabled {
    cursor: wait;
    opacity: 0.7;
  }

  .overview-table th {
    color: #2f3640;
    font-size: 14px;
    font-weight: 800;
  }

  .overview-table td {
    color: #22324d;
    font-family: var(--strategy-font-data);
    font-size: 13px;
    font-weight: 500;
  }

  .green {
    color: #179b4b !important;
  }

  .red {
    color: #ef3232 !important;
  }

  @media (max-width: 1480px) {
    .overview-summary {
      grid-template-columns: 1fr;
      flex-direction: column;
    }
  }
</style>
