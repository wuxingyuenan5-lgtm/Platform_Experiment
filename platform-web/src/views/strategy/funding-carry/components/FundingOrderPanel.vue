<template>
  <section class="funding-exec-shell" data-testid="funding-order-panel">
    <header class="funding-exec-topbar">
      <div class="selector-chip"
        ><span>标的</span><strong>{{ strategyLabel }}</strong></div
      >
      <button type="button" class="refresh-btn" @click="$emit('refresh')">刷新行情</button>
    </header>

    <div class="funding-upper-grid">
      <section class="panel quote-panel">
        <div class="panel-title"><h3>资金费率行情</h3></div>
        <article class="exchange-card">
          <div class="exchange-card__head">
            <div class="exchange-brand"
              ><span class="exchange-logo">B</span><strong>Bybit</strong></div
            >
            <span class="status-pill" :class="{ offline: !context }"
              ><i></i>{{ context ? '在线' : '不可用' }}</span
            >
          </div>
          <div class="exchange-stats">
            <div
              ><span>现货中间价</span><strong>{{ context?.spotQuote?.mid ?? '--' }}</strong></div
            >
            <div
              ><span>永续中间价</span
              ><strong>{{ context?.perpetualQuote?.mid ?? '--' }}</strong></div
            >
            <div
              ><span>资金费率</span
              ><strong :class="fundingTone">{{ fundingRateLabel }}</strong></div
            >
            <div
              ><span>下次结算</span><strong>{{ formatTime(context?.nextFundingTime) }}</strong></div
            >
            <div
              ><span>期现基差</span><strong>{{ context?.basis ?? '--' }}</strong></div
            >
            <div
              ><span>数据时间</span><strong>{{ formatTime(context?.asOf) }}</strong></div
            >
          </div>
        </article>
      </section>

      <section class="panel opportunity-panel">
        <div class="panel-title"><h3>资金费率机会</h3></div>
        <div class="opportunity-value" :class="fundingTone">{{ fundingRateLabel }}</div>
        <div class="opportunity-meta">
          <div><span>交易所</span><strong>Bybit</strong></div>
          <div><span>套利方向</span><strong>现货买入 + 永续卖出</strong></div>
          <div
            ><span>期现基差</span><strong>{{ context?.basis ?? '--' }}</strong></div
          >
          <div
            ><span>账户可用资金</span><strong>{{ fundingAvailable }}</strong></div
          >
          <div
            ><span>建议数量</span><strong>{{ context?.suggestedQuantity ?? '--' }}</strong></div
          >
        </div>
      </section>

      <section class="panel trend-panel">
        <div class="panel-title panel-title--between">
          <h3>资金费率实时截面</h3>
          <span class="data-badge">{{ context?.dataQualityState ?? '等待同步' }}</span>
        </div>
        <div ref="chartRef" class="trend-chart"></div>
      </section>
    </div>

    <div class="funding-lower-grid">
      <section class="panel status-panel">
        <div class="panel-title"><h3>交易规则</h3></div>
        <div class="rule-list">
          <div class="rule-list__row"><span>执行方式</span><strong>PostOnly 逐次追价</strong></div>
          <div class="rule-list__row"
            ><span>现货最小数量</span
            ><strong>{{ context?.minimumQuantity?.spot ?? '--' }}</strong></div
          >
          <div class="rule-list__row"
            ><span>永续最小数量</span
            ><strong>{{ context?.minimumQuantity?.perpetual ?? '--' }}</strong></div
          >
          <div class="rule-list__row"
            ><span>现货数量步长</span
            ><strong>{{ context?.quantityStep?.spot ?? '--' }}</strong></div
          >
          <div class="rule-list__row"
            ><span>永续数量步长</span
            ><strong>{{ context?.quantityStep?.perpetual ?? '--' }}</strong></div
          >
          <div class="rule-list__row"
            ><span>交易权限</span><strong>{{ readinessLabel }}</strong></div
          >
        </div>
        <div class="status-feedback">
          <strong>执行反馈</strong>
          <p v-if="error" class="error-text">{{ error }}</p>
          <p v-else-if="pendingDraft">{{ stateLabel(workspaceState) }}，正在恢复同一指令</p>
          <p v-else>{{ stateLabel(workspaceState) }}</p>
        </div>
      </section>

      <section class="panel order-panel">
        <div class="panel-title"><h3>套利执行指令</h3></div>
        <div class="stage-tabs">
          <button type="button" :class="{ active: stage === 'open' }" @click="stage = 'open'"
            >开仓</button
          >
          <button type="button" :class="{ active: stage === 'close' }" @click="stage = 'close'"
            >平仓</button
          >
        </div>

        <template v-if="stage === 'open'">
          <div class="funding-order-grid">
            <section class="funding-order-column">
              <label class="field">
                <span>标的</span>
                <select
                  :value="context?.perpetualSymbol"
                  @change="handleSymbolChange(($event.target as HTMLSelectElement).value)"
                >
                  <option
                    v-for="item in context?.symbolOptions ?? []"
                    :key="item.perpetualSymbol"
                    :value="item.perpetualSymbol"
                  >
                    {{ item.baseAsset }} · {{ item.perpetualSymbol }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span>名义本金</span>
                <div class="input-with-unit">
                  <input
                    :value="notionalInput"
                    type="text"
                    @input="
                      $emit('update:notional-input', ($event.target as HTMLInputElement).value)
                    "
                  />
                  <em>USDT</em>
                </div>
              </label>
              <label class="field">
                <span>执行数量</span>
                <input :value="quantityInput" type="text" readonly />
              </label>
            </section>

            <section class="funding-order-column">
              <div class="funding-leg-grid">
                <div class="funding-leg-card"
                  ><span>现货头寸</span><strong>买入 {{ quantityInput || '--' }}</strong
                  ><small>{{ context?.spotSymbol ?? '--' }}</small></div
                >
                <div class="funding-leg-card"
                  ><span>永续头寸</span><strong>卖出 {{ quantityInput || '--' }}</strong
                  ><small>{{ context?.perpetualSymbol ?? '--' }}</small></div
                >
              </div>
              <div class="funding-metric-grid">
                <div class="mini-kpi"
                  ><span>当前资金费率</span><strong>{{ fundingRateLabel }}</strong></div
                >
                <div class="mini-kpi"
                  ><span>预计资金占用</span
                  ><strong>{{ context?.requestedNotional ?? notionalInput }} USDT</strong></div
                >
              </div>
            </section>
          </div>
          <button
            class="submit-btn submit-btn--green"
            type="button"
            :disabled="!canSubmit || submitting"
            @click="$emit('submit-open')"
          >
            {{ submitting ? '提交中' : '提交正套开仓' }}
          </button>
        </template>

        <template v-else>
          <div class="funding-close-shell">
            <div class="funding-close-table-wrap">
              <table class="funding-close-table">
                <thead
                  ><tr
                    ><th>组合</th><th>已对冲</th><th>权威已平</th><th>剩余可平</th><th>状态</th
                    ><th>操作</th></tr
                  ></thead
                >
                <tbody>
                  <tr
                    v-for="item in activeGroups"
                    :key="item.instructionId"
                    :class="{ selected: selectedCloseInstructionId === item.instructionId }"
                  >
                    <td>{{ item.perpetualSymbol }} / {{ item.spotSymbol }}</td>
                    <td>{{ item.hedgedQuantity }}</td>
                    <td>{{
                      item.authoritativeClosedQuantity ?? item.alreadyClosedQuantity ?? '0'
                    }}</td>
                    <td>{{ item.remainingClosableQuantity ?? '0' }}</td>
                    <td>{{ stateLabel(item.status) }}</td>
                    <td
                      ><button
                        type="button"
                        class="flat-action"
                        @click="$emit('select-close-instruction', item.instructionId)"
                        >选择</button
                      ></td
                    >
                  </tr>
                  <tr v-if="!activeGroups.length"
                    ><td colspan="6" class="empty-cell">暂无活动组合</td></tr
                  >
                </tbody>
              </table>
            </div>
            <button
              class="submit-btn submit-btn--red"
              type="button"
              :disabled="!canSubmit || submitting || !selectedCloseInstructionId"
              @click="$emit('submit-close')"
            >
              {{ submitting ? '提交中' : '执行组合平仓' }}
            </button>
          </div>
        </template>
      </section>

      <section class="panel history-panel">
        <div class="panel-title"><h3>执行记录</h3></div>
        <table class="analysis-table">
          <thead
            ><tr><th>组合</th><th>数量</th><th>资金费</th><th>手续费</th><th>状态</th></tr></thead
          >
          <tbody>
            <tr v-for="item in historyGroups" :key="item.instructionId">
              <td>{{ item.perpetualSymbol }} / {{ item.spotSymbol }}</td>
              <td>{{ item.hedgedQuantity }}</td>
              <td>{{ item.fundingFees ?? '--' }}</td>
              <td>{{ item.fees ?? '--' }}</td>
              <td>{{ stateLabel(item.status) }}</td>
            </tr>
            <tr v-if="!historyGroups.length"
              ><td colspan="5" class="empty-cell">暂无已完成组合</td></tr
            >
          </tbody>
        </table>
      </section>
    </div>

    <section class="panel positions-panel">
      <div class="panel-title"><h3>当前持仓总览</h3></div>
      <div class="positions-metrics">
        <div
          ><span>活动组合</span><strong>{{ activeGroups.length }}</strong></div
        >
        <div
          ><span>待平预约</span><strong>{{ pendingCloseTotal }}</strong></div
        >
        <div
          ><span>结果未知预约</span><strong>{{ unknownReservedTotal }}</strong></div
        >
        <div
          ><span>Funding 已预约</span
          ><strong>{{ context?.activeReservation?.fundingReserved ?? '0' }}</strong></div
        >
        <div
          ><span>Cross 已预约</span
          ><strong>{{ context?.activeReservation?.crossReserved ?? '0' }}</strong></div
        >
        <div
          ><span>可用资金</span><strong>{{ fundingAvailable }}</strong></div
        >
      </div>
      <div class="positions-table-wrap">
        <table class="positions-table">
          <thead
            ><tr
              ><th>组合</th><th>现货腿</th><th>永续腿</th><th>累计现货成交</th><th>累计永续成交</th
              ><th>剩余数量</th><th>状态</th><th>更新时间</th></tr
            ></thead
          >
          <tbody>
            <tr v-for="item in activeGroups" :key="item.instructionId">
              <td>{{ item.instructionId }}</td
              ><td>{{ item.spotSymbol }}</td
              ><td>{{ item.perpetualSymbol }}</td>
              <td>{{ item.cumulativeSpotFill ?? item.hedgedQuantity }}</td
              ><td>{{ item.cumulativePerpetualFill ?? item.hedgedQuantity }}</td>
              <td>{{ item.remainingClosableQuantity ?? item.residualQuantity }}</td
              ><td>{{ stateLabel(item.status) }}</td
              ><td>{{ formatTime(item.asOf) }}</td>
            </tr>
            <tr v-if="!activeGroups.length"
              ><td colspan="8" class="empty-cell">暂无真实 Funding 持仓</td></tr
            >
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, ref, watch, type Ref } from 'vue';
  import Decimal from 'decimal.js';
  import { useECharts } from '@/hooks/web/useECharts';

  const props = defineProps<{
    context: Record<string, any> | null;
    positionGroups: Array<Record<string, any>>;
    pendingDraft: Record<string, any> | null;
    workspaceState: string;
    submitting: boolean;
    error: string | null;
    quantityInput: string;
    notionalInput: string;
    selectedCloseInstructionId: string;
    selectedCloseGroup: Record<string, any> | null;
    canSubmit: boolean;
  }>();

  const emit = defineEmits<{
    (event: 'update:notional-input', value: string): void;
    (event: 'update:quantity-input', value: string): void;
    (event: 'submit-open'): void;
    (event: 'submit-close'): void;
    (event: 'refresh'): void;
    (event: 'select-symbol', perpetualSymbol: string, spotSymbol: string): void;
    (event: 'select-close-instruction', instructionId: string): void;
  }>();

  const stage = ref<'open' | 'close'>('open');
  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>);
  const activeGroups = computed(() =>
    props.positionGroups.filter((item) => item.lifecycleState !== 'history'),
  );
  const historyGroups = computed(() =>
    props.positionGroups.filter((item) => item.lifecycleState === 'history'),
  );
  const strategyLabel = computed(
    () => `${props.context?.venue ?? 'Bybit'} ${props.context?.perpetualSymbol ?? 'Funding'}`,
  );
  const fundingAvailable = computed(
    () =>
      `${props.context?.activeReservation?.fundingAvailable ?? '--'} ${
        props.context?.activeReservation?.currency ?? 'USDT'
      }`,
  );
  const fundingRateValue = computed(() => {
    const value = Number(props.context?.fundingRate);
    return Number.isFinite(value) ? value * 100 : null;
  });
  const fundingRateLabel = computed(() =>
    fundingRateValue.value === null ? '--' : `${fundingRateValue.value.toFixed(4)}%`,
  );
  const fundingTone = computed(() =>
    fundingRateValue.value !== null && fundingRateValue.value < 0 ? 'red' : 'green',
  );
  const readinessLabel = computed(() =>
    props.context?.controlledLiveReadiness?.ready === true ? '可执行' : '未开启',
  );

  function sum(items: Array<Record<string, any>>, key: string) {
    return items
      .reduce((total, item) => {
        try {
          return total.plus(String(item[key] ?? '0'));
        } catch {
          return total;
        }
      }, new Decimal(0))
      .toFixed();
  }
  const pendingCloseTotal = computed(() => sum(activeGroups.value, 'pendingCloseQuantity'));
  const unknownReservedTotal = computed(() =>
    sum(activeGroups.value, 'resultUnknownReservedQuantity'),
  );

  function handleSymbolChange(perpetualSymbol: string) {
    const option = props.context?.symbolOptions?.find(
      (item: Record<string, any>) => item.perpetualSymbol === perpetualSymbol,
    );
    if (option) emit('select-symbol', option.perpetualSymbol, option.spotSymbol);
  }
  function formatTime(value: unknown) {
    if (!value) return '--';
    const date = new Date(String(value));
    return Number.isNaN(date.getTime())
      ? String(value)
      : date.toLocaleString('zh-CN', { hour12: false });
  }
  function stateLabel(state: unknown) {
    const labels: Record<string, string> = {
      loading: '等待指令',
      submitting: '提交中',
      accepted: '已受理',
      executing: '执行中',
      partially_hedged: '部分对冲',
      reconciling: '对账中',
      completed: '已完成',
      failed: '已失败',
      result_unknown: '结果待确认',
      manual_intervention: '需要人工处理',
      hedged: '已对冲',
    };
    return labels[String(state ?? '')] ?? String(state || '尚未开始');
  }
  async function renderChart() {
    const rate = fundingRateValue.value;
    await chart.setOptions({
      tooltip: { trigger: 'axis' },
      grid: { left: 26, right: 20, top: 22, bottom: 36, containLabel: true },
      xAxis: {
        type: 'category',
        data: props.context ? [formatTime(props.context.asOf)] : [],
        axisLabel: { color: '#8b95a7' },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#8b95a7', formatter: (value: number) => `${value.toFixed(3)}%` },
        splitLine: { lineStyle: { color: '#edf2f7' } },
      },
      series: [
        {
          type: 'line',
          smooth: true,
          symbolSize: 8,
          lineStyle: { color: '#ff4d4f', width: 2 },
          data: rate === null ? [] : [rate],
        },
      ],
    });
    await nextTick();
    chart.resize();
  }
  watch(() => props.context, renderChart, { deep: true });
  onMounted(renderChart);
</script>

<style scoped lang="less">
  .funding-exec-shell {
    display: grid;
    gap: 12px;
    color: var(--strategy-text-1);
  }

  .funding-exec-topbar,
  .panel-title--between,
  .exchange-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .selector-chip {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    min-height: 42px;
    padding: 0 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: #fff;
  }

  .selector-chip span {
    color: var(--strategy-text-3);
  }

  .refresh-btn,
  .flat-action {
    height: 38px;
    padding: 0 14px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 10px;
    background: #fff;
    color: var(--strategy-text-2);
    font-weight: 700;
    cursor: pointer;
  }

  .funding-upper-grid {
    display: grid;
    grid-template-columns: 1.45fr 0.75fr 1.1fr;
    gap: 12px;
  }

  .funding-lower-grid {
    display: grid;
    grid-template-columns: 0.6fr 1.5fr 0.9fr;
    gap: 12px;
    align-items: stretch;
  }

  .panel {
    padding: 16px 18px 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 18px;
    background: #fff;
    box-shadow: var(--strategy-shadow-card);
  }

  .panel-title {
    margin-bottom: 12px;
  }

  .panel-title h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 16px;
    font-weight: 800;
  }

  .exchange-card {
    padding: 16px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 14px;
  }

  .exchange-brand {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .exchange-logo {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #f3f4f6;
    font-weight: 800;
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--strategy-success);
    font-size: 12px;
    font-weight: 700;
  }

  .status-pill i {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentcolor;
  }

  .status-pill.offline {
    color: var(--strategy-danger);
  }

  .exchange-stats,
  .opportunity-meta,
  .rule-list {
    display: grid;
    gap: 10px;
    margin-top: 14px;
  }

  .exchange-stats div,
  .opportunity-meta div,
  .rule-list__row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }

  .exchange-stats span,
  .opportunity-meta span,
  .rule-list__row span {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .opportunity-value {
    margin: 18px 0;
    font-size: 36px;
    font-weight: 800;
  }

  .green {
    color: var(--strategy-success) !important;
  }

  .red {
    color: var(--strategy-danger) !important;
  }

  .data-badge {
    color: var(--strategy-text-faint);
    font-size: 12px;
  }

  .trend-chart {
    height: 250px;
  }

  .rule-list__row {
    align-items: center;
    min-height: 42px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 10px;
  }

  .status-feedback {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid var(--strategy-border-soft);
  }

  .status-feedback p {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .error-text {
    color: var(--strategy-danger) !important;
  }

  .stage-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 14px;
  }

  .stage-tabs button {
    min-width: 72px;
    height: 40px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 10px;
    background: #fff;
    color: var(--strategy-text-2);
    font-weight: 700;
    cursor: pointer;
  }

  .stage-tabs button.active {
    background: var(--strategy-accent-soft);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
    color: var(--strategy-accent-strong);
  }

  .funding-order-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .funding-order-column {
    display: grid;
    gap: 12px;
    align-content: start;
  }

  .field {
    display: grid;
    gap: 6px;
  }

  .field span {
    color: var(--strategy-text-2);
    font-size: 13px;
    font-weight: 700;
  }

  .field select,
  .field input {
    width: 100%;
    height: 46px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 12px;
    background: #fff;
  }

  .input-with-unit {
    display: grid;
    grid-template-columns: 1fr 72px;
    overflow: hidden;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 12px;
  }

  .input-with-unit input {
    border: 0;
    border-radius: 0;
  }

  .input-with-unit em {
    display: grid;
    place-items: center;
    color: var(--strategy-text-3);
    font-style: normal;
    font-weight: 700;
  }

  .funding-leg-grid,
  .funding-metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .funding-leg-card,
  .mini-kpi {
    display: grid;
    gap: 6px;
    min-height: 88px;
    padding: 12px 14px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 14px;
  }

  .funding-leg-card span,
  .mini-kpi span,
  .funding-leg-card small {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .funding-leg-card strong,
  .mini-kpi strong {
    font-size: 18px;
  }

  .submit-btn {
    width: 100%;
    height: 50px;
    margin-top: 14px;
    border: 0;
    border-radius: 12px;
    color: #fff;
    font-weight: 800;
    cursor: pointer;
  }

  .submit-btn--green {
    background: linear-gradient(90deg, #119c41, #0fa24c);
  }

  .submit-btn--red {
    background: linear-gradient(90deg, #df3342, #f14f5c);
  }

  .submit-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .funding-close-shell {
    display: grid;
    gap: 14px;
  }

  .funding-close-table-wrap,
  .positions-table-wrap {
    overflow: auto;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 14px;
  }

  .funding-close-table,
  .analysis-table,
  .positions-table {
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
    border-bottom: 1px solid var(--strategy-border-soft);
    font-size: 12px;
    text-align: left;
    white-space: nowrap;
  }

  th {
    background: var(--strategy-table-head-bg);
    color: var(--strategy-text-3);
  }

  tr.selected {
    background: var(--strategy-surface-selected);
  }

  .positions-metrics {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 12px;
  }

  .positions-metrics div {
    display: grid;
    gap: 4px;
    padding: 10px 12px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 12px;
  }

  .positions-metrics span {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .positions-table {
    min-width: 1180px;
  }

  .empty-cell {
    color: var(--strategy-text-faint);
    text-align: center !important;
  }

  @media (max-width: 1400px) {
    .funding-upper-grid,
    .funding-lower-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 800px) {
    .funding-order-grid,
    .funding-leg-grid,
    .funding-metric-grid,
    .positions-metrics {
      grid-template-columns: 1fr;
    }

    .funding-exec-topbar {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
