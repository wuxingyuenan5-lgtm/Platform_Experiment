<template>
  <section class="live-observability">
    <header class="panel-header">
      <div>
        <p>LIVE OBSERVABILITY</p>
        <h3>实盘账户只读验收面板</h3>
        <span>不包含下单、撤单或持仓修改操作</span>
      </div>
      <div class="panel-controls">
        <label>
          <span>历史范围</span>
          <select v-model.number="historyHours" :disabled="loading" @change="refresh">
            <option :value="24">24 小时</option>
            <option :value="72">3 天</option>
            <option :value="168">7 天</option>
          </select>
        </label>
        <button type="button" :disabled="loading" @click="refresh">
          {{ loading ? '读取中...' : '刷新实盘数据' }}
        </button>
      </div>
    </header>

    <div v-if="errorMessage" class="panel-alert is-error">
      {{ errorMessage }}
    </div>
    <div v-else-if="result?.warnings.length" class="panel-alert is-warn">
      <strong>部分数据不可用</strong>
      <span v-for="warning in result.warnings" :key="warning">{{ warning }}</span>
    </div>

    <div v-if="result" class="venue-grid">
      <article v-for="venue in venues" :key="venue.accountId" class="venue-card">
        <header class="venue-header">
          <div>
            <p>{{ venue.venue }}</p>
            <h4>{{ venue.symbol }}</h4>
            <span>{{ venue.accountId }}</span>
          </div>
          <strong :class="statusClass(venue.status)">
            {{ statusLabel(venue.status) }}
          </strong>
        </header>

        <div class="risk-grid">
          <div v-for="metric in riskMetrics(venue)" :key="metric.label" class="risk-item">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <small v-if="metric.hint">{{ metric.hint }}</small>
          </div>
        </div>

        <section class="data-section">
          <div class="section-title">
            <h5>当前持仓</h5>
            <span :class="sectionClass(venue.sectionStates.positions)">
              {{ sectionLabel(venue.sectionStates.positions) }}
            </span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>方向 / 数量</th>
                  <th>开仓 / 当前</th>
                  <th>浮动盈亏</th>
                  <th>强平 / Stop Out</th>
                  <th>止盈 / 止损</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="venue.positions.length === 0">
                  <td colspan="5">
                    {{ emptyLabel(venue.sectionStates.positions, '当前无持仓') }}
                  </td>
                </tr>
                <tr v-for="position in venue.positions" :key="position.externalPositionId">
                  <td>
                    <strong
                      :class="numberValue(position.netQuantity) >= 0 ? 'is-long' : 'is-short'"
                    >
                      {{ numberValue(position.netQuantity) >= 0 ? '多' : '空' }}
                      {{ formatNumber(absValue(position.netQuantity), 4) }}
                    </strong>
                    <small>{{ position.externalPositionId }}</small>
                  </td>
                  <td>
                    {{ formatNumber(position.averagePrice) }} /
                    {{ formatNumber(position.markPrice ?? position.currentPrice) }}
                  </td>
                  <td>{{ formatSigned(position.unrealizedPnl) }} {{ position.currency }}</td>
                  <td>{{ liquidationLabel(venue, position) }}</td>
                  <td>
                    {{ formatNumber(position.takeProfitPrice) }} /
                    {{ formatNumber(position.stopLossPrice) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="data-section">
          <div class="section-title">
            <h5>活动订单</h5>
            <span>{{ venue.activeOrders.length }} 笔</span>
          </div>
          <div class="order-chips">
            <span v-if="venue.activeOrders.length === 0">
              {{ emptyLabel(venue.sectionStates.activeOrders, '当前无活动订单') }}
            </span>
            <span v-for="order in venue.activeOrders" :key="order.externalOrderId">
              {{ order.side === 'buy' ? '买' : '卖' }}
              {{ formatNumber(order.remainingQuantity, 4) }} · {{ order.status }} ·
              {{ order.externalOrderId }}
            </span>
          </div>
        </section>

        <section class="data-section">
          <div class="section-title">
            <h5>最近订单</h5>
            <span>{{ venue.recentOrders.length }} 笔</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>方向</th>
                  <th>类型</th>
                  <th>成交 / 委托</th>
                  <th>状态</th>
                  <th>订单号</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="venue.recentOrders.length === 0">
                  <td colspan="6">
                    {{ emptyLabel(venue.sectionStates.recentOrders, '历史范围内无订单') }}
                  </td>
                </tr>
                <tr v-for="order in venue.recentOrders" :key="order.externalOrderId">
                  <td>{{ formatTime(order.asOf) }}</td>
                  <td>{{ order.side === 'buy' ? '买' : '卖' }}</td>
                  <td>{{ order.orderType === 'market' ? '市价' : '限价' }}</td>
                  <td>
                    {{ formatNumber(order.filledQuantity, 4) }} /
                    {{ formatNumber(order.quantity, 4) }}
                  </td>
                  <td>
                    {{ order.status }}
                    <small v-if="order.rejectReason || order.cancelReason">
                      {{ order.rejectReason || order.cancelReason }}
                    </small>
                  </td>
                  <td>{{ order.externalOrderId }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="data-section">
          <div class="section-title">
            <h5>最近成交</h5>
            <span>{{ venue.recentFills.length }} 笔</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>方向</th>
                  <th>数量</th>
                  <th>价格</th>
                  <th>费用</th>
                  <th>成交号</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="venue.recentFills.length === 0">
                  <td colspan="6">
                    {{ emptyLabel(venue.sectionStates.recentFills, '历史范围内无成交') }}
                  </td>
                </tr>
                <tr v-for="fill in venue.recentFills" :key="fill.externalFillId">
                  <td>{{ formatTime(fill.occurredAt) }}</td>
                  <td>{{ fill.side === 'buy' ? '买' : '卖' }}</td>
                  <td>{{ formatNumber(fill.quantity, 4) }}</td>
                  <td>{{ formatNumber(fill.price) }}</td>
                  <td>{{ formatNumber(fill.fee, 4) }} {{ fill.currency }}</td>
                  <td>{{ fill.externalFillId }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </article>
    </div>

    <footer class="panel-footer">
      <span>
        Bybit 强平价仅展示交易所返回值；MT5 不提供可靠的单仓强平价，使用账户 Margin Call / Stop Out
        监控。
      </span>
      <strong v-if="result">更新时间：{{ formatTime(result.asOf) }}</strong>
    </footer>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import {
    getCrossSpreadObservability,
    type CrossSpreadObservabilityResult,
    type CrossSpreadVenueObservability,
    type NumericValue,
    type ObservabilitySectionState,
    type ObservabilityState,
    type VenuePositionSnapshot,
  } from '@/api/platform/crossSpreadObservability';

  interface RiskMetric {
    label: string;
    value: string;
    hint?: string;
  }

  const historyHours = ref(24);
  const loading = ref(false);
  const result = ref<CrossSpreadObservabilityResult | null>(null);
  const errorMessage = ref('');

  const venues = computed(() => (result.value ? [result.value.bybit, result.value.mt5] : []));

  async function refresh() {
    loading.value = true;
    errorMessage.value = '';
    try {
      result.value = await getCrossSpreadObservability(historyHours.value, 20);
    } catch (error: unknown) {
      errorMessage.value = resolveError(error);
    } finally {
      loading.value = false;
    }
  }

  function riskMetrics(venue: CrossSpreadVenueObservability): RiskMetric[] {
    const risk = venue.accountRisk;
    if (!risk) {
      return [
        {
          label: '账户风险',
          value: '读取不可用',
          hint: venue.sectionStates.accountRisk,
        },
      ];
    }
    if (venue.venue === 'Bybit') {
      return [
        { label: '账户权益', value: money(risk.equity, risk.currency) },
        { label: '可用余额', value: money(risk.availableBalance, risk.currency) },
        { label: '初始保证金', value: money(risk.initialMargin, risk.currency) },
        { label: '维持保证金', value: money(risk.maintenanceMargin, risk.currency) },
        { label: '账户 MM 比率', value: formatPercent(risk.accountMmRate) },
        { label: '未实现盈亏', value: money(risk.unrealizedPnl, risk.currency) },
      ];
    }
    return [
      { label: '账户权益', value: money(risk.equity, risk.currency) },
      { label: '可用保证金', value: money(risk.availableBalance, risk.currency) },
      { label: '已用保证金', value: money(risk.initialMargin, risk.currency) },
      { label: '保证金水平', value: formatPercent(risk.marginLevel, false) },
      {
        label: 'Margin Call',
        value: thresholdValue(risk.marginCallLevel, risk.marginThresholdMode),
      },
      {
        label: 'Stop Out',
        value: thresholdValue(risk.stopOutLevel, risk.marginThresholdMode),
      },
    ];
  }

  function liquidationLabel(venue: CrossSpreadVenueObservability, position: VenuePositionSnapshot) {
    if (position.liquidationPrice != null) return formatNumber(position.liquidationPrice);
    if (venue.venue === 'MT5') {
      return `单仓不提供；Stop Out ${thresholdValue(
        venue.accountRisk?.stopOutLevel,
        venue.accountRisk?.marginThresholdMode,
      )}`;
    }
    return '当前账户模式未返回有限值';
  }

  function statusLabel(status: ObservabilityState) {
    return { complete: '完整', partial: '部分可用', unavailable: '不可用' }[status];
  }

  function statusClass(status: ObservabilityState) {
    return `is-${status}`;
  }

  function sectionLabel(status?: ObservabilitySectionState) {
    return status === 'complete' ? '已读取' : '不可用';
  }

  function sectionClass(status?: ObservabilitySectionState) {
    return status === 'complete' ? 'is-complete' : 'is-unavailable';
  }

  function emptyLabel(status: ObservabilitySectionState | undefined, healthyLabel: string) {
    return status === 'complete' ? healthyLabel : '读取失败，不能解释为零';
  }

  function formatNumber(value: NumericValue | null | undefined, digits = 2) {
    const parsed = numberValue(value);
    return Number.isFinite(parsed) ? parsed.toFixed(digits) : '--';
  }

  function formatSigned(value: NumericValue | null | undefined) {
    const parsed = numberValue(value);
    if (!Number.isFinite(parsed)) return '--';
    return `${parsed > 0 ? '+' : ''}${parsed.toFixed(2)}`;
  }

  function formatPercent(value: NumericValue | null | undefined, decimalRatio = true) {
    const parsed = numberValue(value);
    if (!Number.isFinite(parsed)) return '--';
    const percent = decimalRatio && Math.abs(parsed) <= 1 ? parsed * 100 : parsed;
    return `${percent.toFixed(2)}%`;
  }

  function thresholdValue(value: NumericValue | null | undefined, mode?: string | null) {
    const parsed = numberValue(value);
    if (!Number.isFinite(parsed)) return '--';
    return mode === '1' ? parsed.toFixed(2) : `${parsed.toFixed(2)}%`;
  }

  function money(value: NumericValue | null | undefined, currency: string) {
    const rendered = formatNumber(value);
    return rendered === '--' ? rendered : `${rendered} ${currency}`;
  }

  function numberValue(value: NumericValue | null | undefined) {
    if (value == null || value === '') return Number.NaN;
    return Number(value);
  }

  function absValue(value: NumericValue) {
    return Math.abs(numberValue(value));
  }

  function formatTime(value: string) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '--' : date.toLocaleString('zh-CN', { hour12: false });
  }

  function resolveError(error: unknown) {
    if (typeof error === 'object' && error !== null) {
      const candidate = error as {
        message?: string;
        response?: { data?: { detail?: string } };
      };
      return candidate.response?.data?.detail || candidate.message || '实盘只读数据读取失败';
    }
    return '实盘只读数据读取失败';
  }

  onMounted(refresh);
</script>

<style scoped lang="less">
  .live-observability {
    margin-top: 14px;
    padding: 18px;
    border: 1px solid #e4eaf2;
    border-radius: 18px;
    background: #fbfcfe;
    color: #172946;
  }

  .panel-header,
  .venue-header,
  .section-title,
  .panel-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .panel-header p,
  .venue-header p {
    margin: 0;
    color: #71819b;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .panel-header h3,
  .venue-header h4 {
    margin: 4px 0;
  }

  .panel-header span,
  .venue-header span,
  .panel-footer {
    color: #71819b;
    font-size: 12px;
  }

  .panel-controls {
    display: flex;
    align-items: end;
    gap: 10px;
  }

  .panel-controls label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    color: #71819b;
    font-size: 11px;
  }

  select,
  button {
    height: 36px;
    padding: 0 12px;
    border: 1px solid #d7e0ed;
    border-radius: 9px;
    background: #ffffff;
    color: #31527f;
  }

  button {
    cursor: pointer;
    font-weight: 700;
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }

  .panel-alert {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    font-size: 12px;
  }

  .panel-alert.is-error {
    background: #fff2f2;
    color: #b23b3b;
  }

  .panel-alert.is-warn {
    background: #fff8e9;
    color: #966013;
  }

  .venue-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    margin-top: 14px;
  }

  .venue-card {
    min-width: 0;
    padding: 15px;
    border: 1px solid #e6ebf2;
    border-radius: 14px;
    background: #ffffff;
  }

  .venue-header > strong,
  .section-title span {
    padding: 5px 8px;
    border-radius: 999px;
    font-size: 11px;
  }

  .is-complete,
  .is-long {
    color: #168a56;
  }

  .is-partial,
  .is-warn {
    color: #a66a10;
  }

  .is-unavailable,
  .is-error,
  .is-short {
    color: #bd4141;
  }

  .risk-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin-top: 12px;
  }

  .risk-item {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
    padding: 10px;
    border-radius: 10px;
    background: #f4f7fb;
  }

  .risk-item span,
  .risk-item small {
    color: #71819b;
    font-size: 11px;
  }

  .risk-item strong {
    overflow: hidden;
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .data-section {
    margin-top: 14px;
  }

  .section-title {
    margin-bottom: 7px;
  }

  .section-title h5 {
    margin: 0;
  }

  .table-wrap {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
  }

  th,
  td {
    padding: 8px 7px;
    border-bottom: 1px solid #edf0f5;
    text-align: left;
    white-space: nowrap;
  }

  th {
    color: #71819b;
    font-weight: 600;
  }

  td small {
    display: block;
    max-width: 160px;
    overflow: hidden;
    color: #8190a7;
    text-overflow: ellipsis;
  }

  .order-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .order-chips span {
    padding: 6px 8px;
    border-radius: 8px;
    background: #f4f7fb;
    color: #526885;
    font-size: 11px;
  }

  .panel-footer {
    margin-top: 12px;
  }

  @media (max-width: 1500px) {
    .venue-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 900px) {
    .panel-header,
    .panel-footer {
      align-items: flex-start;
      flex-direction: column;
    }

    .risk-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
