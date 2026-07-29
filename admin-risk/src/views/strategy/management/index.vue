<template>
  <div class="strategy-management-page">
    <section class="strategy-top-toolbar">
      <div class="strategy-top-toolbar__left">
        <CompactSegmentTabs :items="deskTabs" v-model="activeDesk" />
      </div>

      <div class="strategy-top-toolbar__meta">
        <CompactSegmentTabs :items="sectionTabs" v-model="activeSection" />
      </div>
    </section>

    <template v-if="activeSection === 'pnl'">
      <StrategyPnlPanel :active-desk="activeDesk" />
    </template>

    <template v-else-if="activeSection === 'capital'">
      <StrategyKpiGrid :items="capitalProfile.overview" />

      <StrategyCapitalFinanceBoard
        :risk-cards="capitalProfile.riskCards"
        :structure-cards="capitalProfile.structureCards"
      />

      <StrategyCapitalRulePanel
        v-if="capitalProfile.specialRulePanel"
        :panel="capitalProfile.specialRulePanel"
      />

      <StrategyCapitalRiskOverview
        v-if="capitalProfile.riskOverview"
        :overview="capitalProfile.riskOverview"
      />

      <StrategyRuntimePanel :cards="capitalProfile.comparisonCards" />

      <StrategyCapitalNetValueBoard v-if="capitalProfile.curve.title" :curve="capitalProfile.curve" />

      <StrategyCurveGrid
        v-if="capitalProfile.metricCurves?.length"
        :curves="capitalProfile.metricCurves"
      />
    </template>

    <template v-else>
      <section class="records-only-grid">
        <StrategyRecordsPanel
          :tabs="orderProfile.tabs"
          :tables="orderProfile.tables"
          v-model:activeTab="activeRecordTab"
        />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue';
  import CompactSegmentTabs from '../shared/CompactSegmentTabs.vue';
  import StrategyKpiGrid from './components/StrategyKpiGrid.vue';
  import StrategyRuntimePanel from './components/StrategyRuntimePanel.vue';
  import StrategyCurveGrid from './components/StrategyCurveGrid.vue';
  import StrategyRecordsPanel from './components/StrategyRecordsPanel.vue';
  import StrategyCapitalFinanceBoard from './components/StrategyCapitalFinanceBoard.vue';
  import StrategyCapitalNetValueBoard from './components/StrategyCapitalNetValueBoard.vue';
  import StrategyCapitalRulePanel from './components/StrategyCapitalRulePanel.vue';
  import StrategyCapitalRiskOverview from './components/StrategyCapitalRiskOverview.vue';
  import StrategyPnlPanel from './components/StrategyPnlPanel.vue';
  import { strategyCapitalProfiles } from './mock/capital';
  import { strategyDeskOrder, strategyOrderProfiles } from './mock/orders';
  import {
    getAccountBalanceLatest,
    getExecutionBatches,
    getFills,
    getOrders,
  } from '@/api/platform/trading';
  import { getCrossSpreadExitPlans } from '@/api/platform/crossSpreadLifecycle';
  import { getCrossSpreadObservability } from '@/api/platform/crossSpreadObservability';
  import type {
    BalanceResult,
    ExecutionBatchResult,
    FillResult,
    OrderDetailResult,
  } from '@/api/platform/trading.types';
  import type { CrossSpreadExitPlanResult } from '@/api/platform/crossSpreadLifecycle';
  import type { CrossSpreadObservabilityResult } from '@/api/platform/crossSpreadObservability';
  import type {
    StrategyCapitalProfile,
    StrategyDeskKey,
    StrategyTableSection,
  } from './types';

  const activeDesk = ref<StrategyDeskKey>('funding');
  const activeRecordTab = ref('positions');
  const activeSection = ref<'pnl' | 'capital' | 'orders'>('pnl');
  const CROSS_SPREAD_STRATEGY_ID = 'strategy_cross_venue_spread_instance_default';
  const BYBIT_ACCOUNT_ID = 'account_crypto_test';
  const MT5_ACCOUNT_ID = 'account_mt5_demo';
  const liveCapitalProfile = ref<StrategyCapitalProfile | null>(null);
  const liveOrderProfile = ref<typeof strategyOrderProfiles.crossSpread | null>(null);
  const liveDataLoading = ref(false);
  const liveDataError = ref('');

  const deskTabs = strategyDeskOrder.map((key) => ({
    key,
    label: strategyOrderProfiles[key].label,
  }));

  const sectionTabs = [
    { key: 'pnl', label: '策略损益' },
    { key: 'capital', label: '账户资金' },
    { key: 'orders', label: '订单信息' },
  ];

  const orderProfile = computed(() => {
    if (activeDesk.value === 'crossSpread' && liveOrderProfile.value) return liveOrderProfile.value;
    return strategyOrderProfiles[activeDesk.value];
  });
  const capitalProfile = computed(() => {
    if (activeDesk.value === 'crossSpread' && liveCapitalProfile.value) return liveCapitalProfile.value;
    return strategyCapitalProfiles[activeDesk.value];
  });

  watch(
    () => activeDesk.value,
    () => {
      activeRecordTab.value = orderProfile.value.tabs[0]?.key || 'positions';
      activeSection.value = 'pnl';
      loadCrossSpreadManagementData();
    },
    { immediate: true },
  );

  watch(activeSection, () => {
    loadCrossSpreadManagementData();
  });

  onMounted(loadCrossSpreadManagementData);

  async function loadCrossSpreadManagementData() {
    if (activeDesk.value !== 'crossSpread') return;
    if (activeSection.value === 'pnl') return;
    liveDataLoading.value = true;
    liveDataError.value = '';
    try {
      const [
        observability,
        bybitBalance,
        mt5Balance,
        orders,
        fills,
        batches,
        exitPlans,
      ] = await Promise.all([
        getCrossSpreadObservability(24, 50, 'fast'),
        getAccountBalanceLatest(BYBIT_ACCOUNT_ID),
        getAccountBalanceLatest(MT5_ACCOUNT_ID),
        getOrders(),
        getFills(),
        getExecutionBatches(CROSS_SPREAD_STRATEGY_ID),
        getCrossSpreadExitPlans(),
      ]);
      liveCapitalProfile.value = buildCrossSpreadCapitalProfile(
        observability,
        bybitBalance,
        mt5Balance,
      );
      liveOrderProfile.value = buildCrossSpreadOrderProfile(
        observability,
        orders,
        fills,
        batches,
        exitPlans,
      );
    } catch (error) {
      liveDataError.value = error instanceof Error ? error.message : '跨所价差管理数据加载失败';
    } finally {
      liveDataLoading.value = false;
    }
  }

  function buildCrossSpreadCapitalProfile(
    observability: CrossSpreadObservabilityResult,
    bybitBalance: BalanceResult | null,
    mt5Balance: BalanceResult | null,
  ): StrategyCapitalProfile {
    const bybitRisk = trustedRisk(observability.bybit.accountRisk);
    const mt5Risk = trustedRisk(observability.mt5.accountRisk);
    const bybitTrustedBalance = trustedBalance(bybitBalance);
    const mt5TrustedBalance = trustedBalance(mt5Balance);
    const bybitEquity = optionalNumber(bybitRisk?.equity ?? bybitTrustedBalance?.equity);
    const mt5Equity = optionalNumber(mt5Risk?.equity ?? mt5TrustedBalance?.equity);
    const bybitAvailable = optionalNumber(bybitRisk?.availableBalance ?? bybitTrustedBalance?.availableBalance);
    const mt5Available = optionalNumber(mt5Risk?.availableBalance ?? mt5TrustedBalance?.availableBalance);
    const bybitInitialMargin = numberValue(bybitRisk?.initialMargin);
    const mt5InitialMargin = numberValue(mt5Risk?.initialMargin);
    const totalEquity = sumPresent([bybitEquity, mt5Equity]);
    const totalAvailable = sumPresent([bybitAvailable, mt5Available]);
    const totalInitialMargin = bybitInitialMargin + mt5InitialMargin;
    const bybitWeight = totalEquity !== null && bybitEquity !== null && totalEquity > 0 ? Math.round((bybitEquity / totalEquity) * 100) : 0;
    const hasAnyCapital = totalEquity !== null || totalAvailable !== null;
    const statusTone = hasAnyCapital ? 'positive' : 'neutral';

    return {
      overview: [
        kpi('账户净值', money(totalEquity), 'USDT', hasAnyCapital ? 'Bybit + MT5 实盘口径' : '暂无实盘余额', statusTone),
        kpi('可用资金', money(totalAvailable), 'USDT', hasAnyCapital ? '双账户 availableBalance 合计' : '暂无实盘余额', hasAnyCapital ? 'positive' : 'neutral'),
        kpi('保证金占用', money(totalInitialMargin), 'USDT', '双账户 initialMargin 合计', totalInitialMargin > 0 ? 'neutral' : 'positive'),
        kpi('Bybit 权益', money(bybitEquity), bybitRisk?.currency || bybitTrustedBalance?.currency || 'USDT', bybitEquity === null ? '暂无实盘余额' : observability.bybit.status, bybitEquity === null ? 'neutral' : 'positive'),
        kpi('MT5 权益', money(mt5Equity), mt5Risk?.currency || mt5TrustedBalance?.currency || 'USDT', mt5Equity === null ? '暂无实盘余额' : observability.mt5.status, mt5Equity === null ? 'neutral' : 'positive'),
        kpi('数据时间', formatTime(observability.asOf), '', '来自跨所价差观测接口', 'neutral'),
      ],
      riskCards: [
        risk('Bybit 保证金率', rateText(bybitRisk?.accountImRate), observability.bybit.status, toneFromNullable(bybitRisk?.accountImRate, false)),
        risk('MT5 Margin Level', rateText(mt5Risk?.marginLevel, 2, false), observability.mt5.status, toneFromNullable(mt5Risk?.marginLevel, true)),
        risk('Bybit 未实现盈亏', signedMoney(bybitRisk?.unrealizedPnl), 'accountRisk.unrealizedPnl', toneFromSigned(bybitRisk?.unrealizedPnl)),
        risk('MT5 未实现盈亏', signedMoney(mt5Risk?.unrealizedPnl), 'accountRisk.unrealizedPnl', toneFromSigned(mt5Risk?.unrealizedPnl)),
      ],
      structureCards: [
        risk('Bybit 可用资金', money(bybitAvailable), BYBIT_ACCOUNT_ID, bybitAvailable !== null && bybitAvailable > 0 ? 'positive' : 'neutral'),
        risk('MT5 可用资金', money(mt5Available), MT5_ACCOUNT_ID, mt5Available !== null && mt5Available > 0 ? 'positive' : 'neutral'),
        risk('Bybit 持仓数', String(trustedPositions(observability.bybit.positions).length), observability.bybit.symbol, 'neutral'),
        risk('MT5 持仓数', String(trustedPositions(observability.mt5.positions).length), observability.mt5.symbol, 'neutral'),
      ],
      comparisonCards: hasAnyCapital ? [
        {
          title: 'Bybit / MT5 资金对照',
          centerValue: `${money(totalEquity)} USDT`,
          centerLabel: '双账户权益合计',
          leftLabel: 'Bybit',
          leftValue: `${money(bybitEquity)} ${bybitRisk?.currency || bybitTrustedBalance?.currency || 'USDT'}`,
          leftNote: `可用 ${money(bybitAvailable)}`,
          rightLabel: 'MT5',
          rightValue: `${money(mt5Equity)} ${mt5Risk?.currency || mt5TrustedBalance?.currency || 'USDT'}`,
          rightNote: `可用 ${money(mt5Available)}`,
          progress: bybitWeight,
          startColor: '#19a463',
          endColor: '#ef4444',
        },
      ] : [],
      curve: emptyCapitalCurve(),
      metricCurves: [],
    };
  }

  function buildCrossSpreadOrderProfile(
    observability: CrossSpreadObservabilityResult,
    orders: OrderDetailResult[],
    fills: FillResult[],
    batches: ExecutionBatchResult[],
    exitPlans: CrossSpreadExitPlanResult[],
  ) {
    const realOrders = orders.filter(isTrustedOrder);
    const realOrderIds = new Set(realOrders.map((item) => item.orderId));
    const realBatches = batches.filter((item) => item.legs.length > 0 && item.legs.every((leg) => leg.orderId && realOrderIds.has(leg.orderId)));
    const realBatchIds = new Set(realBatches.map((item) => item.batchId));
    const realExitPlans = exitPlans.filter((item) => realBatchIds.has(item.openBatchId));
    const bybitOrders = realOrders.filter((item) => item.accountId === BYBIT_ACCOUNT_ID);
    const mt5Orders = realOrders.filter((item) => item.accountId === MT5_ACCOUNT_ID);
    const crossFills = fills.filter((item) => (item.accountId === BYBIT_ACCOUNT_ID || item.accountId === MT5_ACCOUNT_ID) && !item.fillId.startsWith('FAKE-') && realOrderIds.has(item.orderId));
    const tables: Record<string, StrategyTableSection> = {
      positions: {
        columns: [
          { key: 'venue', label: '场所' },
          { key: 'symbol', label: '标的' },
          { key: 'side', label: '方向' },
          { key: 'quantity', label: '持仓数量' },
          { key: 'averagePrice', label: '持仓均价' },
          { key: 'currentPrice', label: '当前价格' },
          { key: 'unrealizedPnl', label: '未实现PnL' },
          { key: 'status', label: '状态' },
        ],
        rows: [
          ...trustedPositions(observability.bybit.positions).map((item) => ({
            venue: 'Bybit',
            symbol: item.symbol,
            side: sideText(Number(item.netQuantity) >= 0 ? 'buy' : 'sell'),
            quantity: String(item.netQuantity),
            averagePrice: text(item.averagePrice),
            currentPrice: text(item.currentPrice ?? item.markPrice),
            unrealizedPnl: signedMoney(item.unrealizedPnl),
            status: item.dataQualityState || observability.bybit.status,
          })),
          ...trustedPositions(observability.mt5.positions).map((item) => ({
            venue: 'MT5',
            symbol: item.symbol,
            side: sideText(Number(item.netQuantity) >= 0 ? 'buy' : 'sell'),
            quantity: String(item.netQuantity),
            averagePrice: text(item.averagePrice),
            currentPrice: text(item.currentPrice ?? item.markPrice),
            unrealizedPnl: signedMoney(item.unrealizedPnl),
            status: item.dataQualityState || observability.mt5.status,
          })),
        ],
      },
      leftHistory: orderTable('Bybit 订单', bybitOrders),
      rightHistory: orderTable('MT5 订单', mt5Orders),
      fills: {
        columns: [
          { key: 'fillId', label: '成交号' },
          { key: 'venue', label: '场所' },
          { key: 'orderId', label: '订单号' },
          { key: 'side', label: '方向' },
          { key: 'quantity', label: '成交数量' },
          { key: 'price', label: '成交价格' },
          { key: 'time', label: '成交时间' },
        ],
        rows: crossFills.map((item) => ({
          fillId: item.fillId,
          venue: item.accountId === BYBIT_ACCOUNT_ID ? 'Bybit' : 'MT5',
          orderId: item.orderId,
          side: sideText(item.side),
          quantity: item.quantity,
          price: item.price,
          time: formatTime(item.occurredAt),
        })),
      },
      logs: {
        columns: [
          { key: 'time', label: '时间' },
          { key: 'type', label: '类型' },
          { key: 'content', label: '内容' },
          { key: 'status', label: '状态' },
        ],
        rows: [
          ...realBatches.map((item) => ({
            time: formatTime(item.updatedAt),
            type: '执行批次',
            content: `${item.direction} / ${item.batchId}`,
            status: item.failureReason || item.status,
          })),
          ...realExitPlans.map((item) => ({
            time: formatTime(item.updatedAt),
            type: '退出计划',
            content: `${item.direction} ${item.quantityOz} oz，TP ${item.takeProfitSpread} / SL ${item.stopLossSpread}`,
            status: item.status,
          })),
        ],
      },
    };

    return {
      label: '跨所价差',
      tabs: [
        { key: 'positions', label: '当前持仓' },
        { key: 'leftHistory', label: '历史订单-Bybit' },
        { key: 'rightHistory', label: '历史订单-MT5' },
        { key: 'fills', label: '成交记录' },
        { key: 'logs', label: '执行记录' },
      ],
      tables,
    };
  }

  function orderTable(_title: string, orders: OrderDetailResult[]): StrategyTableSection {
    return {
      columns: [
        { key: 'time', label: '时间' },
        { key: 'orderId', label: '订单号' },
        { key: 'symbol', label: '标的' },
        { key: 'side', label: '方向' },
        { key: 'orderType', label: '类型' },
        { key: 'quantity', label: '数量' },
        { key: 'price', label: '价格' },
        { key: 'status', label: '状态' },
      ],
      rows: orders.map((item) => ({
        time: formatTime(item.updatedAt || item.createdAt),
        orderId: item.orderId,
        symbol: item.symbol,
        side: sideText(item.side),
        orderType: item.orderType === 'market' ? '市价' : '限价',
        quantity: item.quantity,
        price: text(item.price),
        status: statusText(item.status),
      })),
    };
  }

  function kpi(label: string, value: string, unit: string, note: string, tone: 'positive' | 'negative' | 'neutral') {
    return { label, value, unit, note, tone };
  }

  function risk(label: string, value: string, note: string, tone: 'positive' | 'negative' | 'neutral') {
    return { label, value, note, tone };
  }

  function numberValue(value: string | number | null | undefined) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function optionalNumber(value: string | number | null | undefined) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function sumPresent(values: Array<number | null>) {
    const present = values.filter((value): value is number => value !== null);
    return present.length ? present.reduce((sum, value) => sum + value, 0) : null;
  }

  function money(value: string | number | null | undefined) {
    const parsed = optionalNumber(value);
    if (parsed === null) return '--';
    return parsed.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }

  function trustedBalance(balance: BalanceResult | null) {
    if (!balance) return null;
    return isTrustedSource(balance.source) ? balance : null;
  }

  function trustedRisk<T extends { source?: string | null }>(risk: T | null | undefined) {
    if (!risk) return null;
    return isTrustedSource(risk.source) ? risk : null;
  }

  function trustedPositions<T extends { source?: string | null }>(positions: T[]) {
    return positions.filter((position) => isTrustedSource(position.source));
  }

  function isTrustedOrder(order: OrderDetailResult) {
    return !order.externalOrderId?.startsWith('FAKE-');
  }

  function isTrustedSource(source: string | null | undefined) {
    if (!source) return false;
    return !['fake', 'seed', 'mock', 'simulation'].includes(source.toLowerCase());
  }

  function emptyCapitalCurve() {
    return {
      title: '',
      subtitle: '',
      metricOptions: [],
      periodOptions: [],
      defaultMetric: '',
      defaultPeriod: '',
      xLabels: [],
      netValueData: [],
      drawdownData: [],
      summaries: [],
    };
  }

  function signedMoney(value: string | number | null | undefined) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return '--';
    return `${parsed > 0 ? '+' : ''}${money(parsed)}`;
  }

  function rateText(value: string | number | null | undefined, digits = 2, percent = true) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return '--';
    return percent ? `${(parsed * 100).toFixed(digits)}%` : parsed.toFixed(digits);
  }

  function toneFromSigned(value: string | number | null | undefined): 'positive' | 'negative' | 'neutral' {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed === 0) return 'neutral';
    return parsed > 0 ? 'positive' : 'negative';
  }

  function toneFromNullable(value: string | number | null | undefined, higherIsBetter: boolean): 'positive' | 'negative' | 'neutral' {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return 'neutral';
    return higherIsBetter ? (parsed > 0 ? 'positive' : 'negative') : (parsed > 0.8 ? 'negative' : 'positive');
  }

  function text(value: string | number | null | undefined) {
    if (value === null || value === undefined || value === '') return '--';
    return String(value);
  }

  function sideText(side: string) {
    return side === 'buy' ? '买入' : side === 'sell' ? '卖出' : side;
  }

  function statusText(status: string) {
    const map: Record<string, string> = {
      processing: '处理中',
      acknowledged: '已确认',
      filled: '全部成交',
      rejected: '已拒绝',
      result_unknown: '结果未知',
    };
    return map[status] || status;
  }

  function formatTime(value: string | null | undefined) {
    if (!value) return '--';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('zh-CN', { hour12: false });
  }
</script>

<style lang="less">
  @import '../shared/strategy-theme.less';
</style>

<style scoped lang="less">
  .strategy-management-page {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 6px 4px 0;
    background: var(--strategy-bg);
    color: var(--strategy-text-1);
  }

  .records-only-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
  }
</style>
