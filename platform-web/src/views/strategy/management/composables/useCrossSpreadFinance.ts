import { computed, ref } from 'vue';

import { getCrossSpreadObservability } from '@/api/platform/crossSpreadObservability';
import {
  getAccountBalanceLatest,
  getCrossSpreadSnapshot,
  getEquityHistory,
  getFills,
  getStrategyAccountBindings,
  getTradingPnl,
} from '@/api/platform/trading';
import type {
  BalanceResult,
  EquityHistoryPointResult,
  FillResult,
  PnlResult,
  StrategyAccountBindingResult,
  CrossSpreadSnapshotResult,
} from '@/api/platform/trading.types';
import type {
  CrossSpreadObservabilityResult,
  CrossSpreadVenueObservability,
  VenuePositionSnapshot,
} from '@/api/platform/crossSpreadObservability';
import type {
  StrategyAccountBreakdown,
  StrategyCapitalProfile,
  StrategyCurveCard,
  StrategyKpiCard,
  StrategyPnlAttributionItem,
  StrategyPnlProfile,
} from '@/data/sample/strategy';
import { strategyPnlProfiles } from '@/data/sample/strategy';

type MetricTone = 'positive' | 'negative' | 'neutral';

const STRATEGY_INSTANCE_ID = 'strategy_cross_venue_spread_instance_default';
const BYBIT_INSTRUMENT_ID = 'instrument_xau_usdt_perp';
const MT5_INSTRUMENT_ID = 'instrument_xau_usd';
const TRUSTED_XAU_PRICE_FLOOR = 1000;

interface StrategyPnlMetric {
  label: string;
  value: string;
  ratio: string;
  tone: MetricTone;
}

interface DerivedPnlPoint {
  time: string;
  totalRealized: number;
  bybitRealized: number;
  mt5Realized: number;
}

interface DerivedLegState {
  quantity: number;
  averagePrice: number | null;
  realized: number;
}

function toNumber(value: string | number | null | undefined): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function money(value: number, currency: string): string {
  return `${value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ${currency}`;
}

function normalizeCurrency(value: string | null | undefined): string {
  const normalized = String(value ?? '').toUpperCase();
  if (!normalized) return 'USDT';
  if (normalized === 'UST') return 'USDT';
  return normalized;
}

function signedMoney(value: number, currency: string): string {
  const rendered = money(Math.abs(value), currency);
  return `${value > 0 ? '+' : value < 0 ? '-' : ''}${rendered}`;
}

function signedNumber(value: number, digits = 2): string {
  return `${value > 0 ? '+' : value < 0 ? '-' : ''}${Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

function percent(value: number, digits = 2): string {
  return `${value.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}%`;
}

function toneFromNumber(value: number): MetricTone {
  if (value > 0) return 'positive';
  if (value < 0) return 'negative';
  return 'neutral';
}

function firstActiveBinding(
  bindings: StrategyAccountBindingResult[],
  role: string,
  preferredAccountId?: string | null,
) {
  const candidates = bindings.filter(
    (binding) => binding.role === role && binding.status === 'active',
  );
  if (!candidates.length) return null;
  if (preferredAccountId) {
    const exact = candidates.find((binding) => binding.accountId === preferredAccountId);
    if (exact) return exact;
  }
  return candidates[0];
}

function formatTime(value: string | null | undefined): string {
  if (!value) return '--';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString('zh-CN', { hour12: false });
}

function formatLabelTime(value: string | null | undefined): string {
  if (!value) return '--';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
}

function isTrustedLegacyFilteredFill(fill: FillResult): boolean {
  const instrumentId = fill.instrumentId ?? '';
  const price = toNumber(fill.price);
  if (!instrumentId.includes('xau')) return true;
  return price >= TRUSTED_XAU_PRICE_FLOOR;
}

function calculatePositionUpdate(
  oldQuantity: number,
  oldAverage: number | null,
  signedFill: number,
  fillPrice: number,
) {
  if (oldQuantity === 0 || oldQuantity * signedFill > 0) {
    const newQuantity = oldQuantity + signedFill;
    const oldNotional = Math.abs(oldQuantity) * (oldAverage ?? 0);
    const newNotional = Math.abs(signedFill) * fillPrice;
    const newAverage =
      newQuantity === 0 ? null : (oldNotional + newNotional) / Math.abs(newQuantity);
    return { quantity: newQuantity, averagePrice: newAverage, realized: 0 };
  }

  const closingQuantity = Math.min(Math.abs(oldQuantity), Math.abs(signedFill));
  const direction = oldQuantity > 0 ? 1 : -1;
  const referenceAverage = oldAverage ?? fillPrice;
  const realized = closingQuantity * (fillPrice - referenceAverage) * direction;
  const newQuantity = oldQuantity + signedFill;

  if (newQuantity === 0) {
    return { quantity: newQuantity, averagePrice: null, realized };
  }
  if (oldQuantity * newQuantity > 0) {
    return { quantity: newQuantity, averagePrice: oldAverage, realized };
  }
  return { quantity: newQuantity, averagePrice: fillPrice, realized };
}

function derivePnlTimeline(
  fills: FillResult[],
  bybitAccountId: string | null,
  mt5AccountId: string | null,
) {
  const ordered = [...fills]
    .filter(isTrustedLegacyFilteredFill)
    .sort(
      (left, right) => new Date(left.occurredAt).getTime() - new Date(right.occurredAt).getTime(),
    );

  const states = new Map<string, DerivedLegState>();
  const points: DerivedPnlPoint[] = [];
  let totalRealized = 0;
  let bybitRealized = 0;
  let mt5Realized = 0;

  for (const fill of ordered) {
    const key = `${fill.accountId}:${fill.instrumentId}`;
    const state = states.get(key) ?? { quantity: 0, averagePrice: null, realized: 0 };
    const quantity = toNumber(fill.quantity);
    const price = toNumber(fill.price);
    const signedFill = String(fill.side).toLowerCase() === 'buy' ? quantity : -quantity;
    const nextState = calculatePositionUpdate(
      state.quantity,
      state.averagePrice,
      signedFill,
      price,
    );
    state.quantity = nextState.quantity;
    state.averagePrice = nextState.averagePrice;
    state.realized += nextState.realized;
    states.set(key, state);

    totalRealized += nextState.realized;
    if (fill.accountId === bybitAccountId) bybitRealized += nextState.realized;
    if (fill.accountId === mt5AccountId) mt5Realized += nextState.realized;

    points.push({
      time: fill.occurredAt,
      totalRealized: Number(totalRealized.toFixed(2)),
      bybitRealized: Number(bybitRealized.toFixed(2)),
      mt5Realized: Number(mt5Realized.toFixed(2)),
    });
  }

  return {
    points,
    totalRealized: Number(totalRealized.toFixed(4)),
    bybitRealized: Number(bybitRealized.toFixed(4)),
    mt5Realized: Number(mt5Realized.toFixed(4)),
    trustedFillCount: ordered.length,
  };
}

function navPointsFromSnapshotsOrRealized(
  bybitHistory: EquityHistoryPointResult[],
  mt5History: EquityHistoryPointResult[],
) {
  const orderedBybit = [...bybitHistory].sort(
    (left, right) => new Date(left.asOf).getTime() - new Date(right.asOf).getTime(),
  );
  const orderedMt5 = [...mt5History].sort(
    (left, right) => new Date(left.asOf).getTime() - new Date(right.asOf).getTime(),
  );
  const timestamps = Array.from(
    new Set([...orderedBybit.map((item) => item.asOf), ...orderedMt5.map((item) => item.asOf)]),
  ).sort((left, right) => new Date(left).getTime() - new Date(right).getTime());

  if (!timestamps.length) {
    return [];
  }

  let bybitIndex = 0;
  let mt5Index = 0;
  let bybitEquity = 0;
  let mt5Equity = 0;
  const merged = timestamps.map((time) => {
    while (
      bybitIndex < orderedBybit.length &&
      new Date(orderedBybit[bybitIndex].asOf).getTime() <= new Date(time).getTime()
    ) {
      bybitEquity = toNumber(orderedBybit[bybitIndex].equity);
      bybitIndex += 1;
    }
    while (
      mt5Index < orderedMt5.length &&
      new Date(orderedMt5[mt5Index].asOf).getTime() <= new Date(time).getTime()
    ) {
      mt5Equity = toNumber(orderedMt5[mt5Index].equity);
      mt5Index += 1;
    }
    return { time, equity: Number((bybitEquity + mt5Equity).toFixed(2)) };
  });

  const capitalBase = Math.max(merged.find((point) => point.equity > 0)?.equity ?? 0, 1);
  return merged.map((point) => ({
    time: point.time,
    equity: point.equity,
    capitalBase,
    nav: point.equity / capitalBase,
    currency: 'USDT',
  }));
}

function drawdowns(values: number[]) {
  let peak = -Infinity;
  return values.map((value) => {
    peak = Math.max(peak, value);
    if (peak <= 0) return 0;
    return Number((((value - peak) / peak) * 100).toFixed(2));
  });
}

function dayReturns(values: number[]) {
  return values.map((value, index) => {
    if (index === 0) return 0;
    return Number((value - values[index - 1]).toFixed(2));
  });
}

function positionSnapshotRows(position: VenuePositionSnapshot | null | undefined) {
  const quantity = toNumber(position?.netQuantity);
  const hasMeaningfulPosition =
    position &&
    (Math.abs(quantity) > 0 ||
      position.averagePrice != null ||
      position.currentPrice != null ||
      position.unrealizedPnl != null ||
      position.realizedPnl != null);

  if (!hasMeaningfulPosition) {
    return [
      { label: '持仓数量', value: '--' },
      { label: '均价', value: '--' },
      { label: '最新价', value: '--' },
      { label: '未实现盈亏', value: '--' },
      { label: '已实现盈亏', value: '--' },
      { label: '最后同步', value: position?.asOf ? formatTime(position.asOf) : '--' },
    ];
  }

  const unrealized = toNumber(position.unrealizedPnl);
  const realized = toNumber(position.realizedPnl);
  return [
    { label: '持仓数量', value: String(position.netQuantity ?? '--') },
    {
      label: '均价',
      value:
        position.averagePrice == null
          ? '--'
          : signedNumber(toNumber(position.averagePrice)).replace(/^\+/, ''),
    },
    {
      label: '最新价',
      value:
        position.currentPrice == null
          ? '--'
          : signedNumber(toNumber(position.currentPrice)).replace(/^\+/, ''),
    },
    {
      label: '未实现盈亏',
      value: signedNumber(unrealized),
      tone: toneFromNumber(unrealized),
    },
    {
      label: '已实现盈亏',
      value: signedNumber(realized),
      tone: toneFromNumber(realized),
    },
    { label: '最后同步', value: formatTime(position.asOf) },
  ];
}

function venueStatusNote(venue: CrossSpreadVenueObservability | null | undefined) {
  if (!venue) return '接口未返回';
  if (venue.status === 'complete') return '完整';
  if (venue.status === 'partial') return '部分';
  return '不可用';
}

function trustedDataNote(trustedFillCount: number) {
  return trustedFillCount > 0 ? `可信成交 ${trustedFillCount} 笔` : '暂无可信成交记录';
}

function effectiveBalance(
  snapshot: BalanceResult | null,
  accountRisk: CrossSpreadVenueObservability['accountRisk'] | null | undefined,
) {
  // Account risk is the live venue source.  A persisted balance snapshot is
  // never a substitute when a live venue read is unavailable.
  const equity = accountRisk?.equity;
  const availableBalance = accountRisk?.availableBalance;
  return {
    currency: normalizeCurrency(accountRisk?.currency),
    equity: equity == null ? null : toNumber(equity),
    availableBalance: availableBalance == null ? null : toNumber(availableBalance),
    asOf: accountRisk?.asOf || null,
    available:
      accountRisk?.dataQualityState === 'complete' && equity != null && availableBalance != null,
  };
}

function toUsdt(value: number | null, currency: string, usdtUsd: number | null): number | null {
  if (value === null) return null;
  if (currency === 'USDT') return value;
  // The snapshot quotes the value of one USDT in USD, so USD is divided by it.
  if (currency === 'USD' && usdtUsd !== null && usdtUsd > 0) return value / usdtUsd;
  return null;
}

function hasLivePosition(position: VenuePositionSnapshot | null | undefined): boolean {
  return Math.abs(toNumber(position?.netQuantity)) > 0;
}

function venueUnrealizedPnl(venue: CrossSpreadVenueObservability | null | undefined): number {
  if (!venue) return 0;
  const positions = (venue.positions ?? []).filter(hasLivePosition);
  if (positions.length) {
    return positions.reduce((sum, position) => sum + toNumber(position.unrealizedPnl), 0);
  }
  if (venue.status === 'complete') {
    return 0;
  }
  return toNumber(venue.accountRisk?.unrealizedPnl);
}

function zeroSeries(length: number) {
  return Array.from({ length }, () => 0);
}

export function useCrossSpreadFinance() {
  const loading = ref(false);
  const bindings = ref<StrategyAccountBindingResult[]>([]);
  const observability = ref<CrossSpreadObservabilityResult | null>(null);
  const marketSnapshot = ref<CrossSpreadSnapshotResult | null>(null);
  const bybitEquityHistory = ref<EquityHistoryPointResult[]>([]);
  const mt5EquityHistory = ref<EquityHistoryPointResult[]>([]);
  const bybitBalance = ref<BalanceResult | null>(null);
  const mt5Balance = ref<BalanceResult | null>(null);
  const bybitPnl = ref<PnlResult | null>(null);
  const mt5Pnl = ref<PnlResult | null>(null);
  const fills = ref<FillResult[]>([]);

  const bybitBinding = computed(() =>
    firstActiveBinding(bindings.value, 'venue_a', observability.value?.bybit?.accountId),
  );
  const mt5Binding = computed(() =>
    firstActiveBinding(bindings.value, 'mt5_leg', observability.value?.mt5?.accountId),
  );

  const bybitAccountId = computed(
    () => observability.value?.bybit?.accountId || bybitBinding.value?.accountId || null,
  );
  const mt5AccountId = computed(
    () => observability.value?.mt5?.accountId || mt5Binding.value?.accountId || null,
  );

  const selectedFills = computed(() =>
    fills.value.filter(
      (fill) => fill.accountId === bybitAccountId.value || fill.accountId === mt5AccountId.value,
    ),
  );

  const derivedPnl = computed(() =>
    derivePnlTimeline(selectedFills.value, bybitAccountId.value, mt5AccountId.value),
  );
  const bybitBalanceView = computed(() =>
    effectiveBalance(bybitBalance.value, observability.value?.bybit?.accountRisk),
  );
  const mt5BalanceView = computed(() =>
    effectiveBalance(mt5Balance.value, observability.value?.mt5?.accountRisk),
  );

  const usdtUsd = computed(() => {
    const value = toNumber(marketSnapshot.value?.metrics.usdtUsd);
    return value > 0 ? value : null;
  });
  const currenciesComparable = computed(
    () =>
      bybitBalanceView.value.available &&
      mt5BalanceView.value.available &&
      toUsdt(1, bybitBalanceView.value.currency, usdtUsd.value) !== null &&
      toUsdt(1, mt5BalanceView.value.currency, usdtUsd.value) !== null,
  );
  const currencyMismatchNote = computed(() =>
    currenciesComparable.value ? '' : '币种不一致，无法汇总',
  );
  const bybitEquity = computed(
    () =>
      toUsdt(bybitBalanceView.value.equity, bybitBalanceView.value.currency, usdtUsd.value) ?? 0,
  );
  const mt5Equity = computed(
    () => toUsdt(mt5BalanceView.value.equity, mt5BalanceView.value.currency, usdtUsd.value) ?? 0,
  );
  const bybitAvailable = computed(
    () =>
      toUsdt(
        bybitBalanceView.value.availableBalance,
        bybitBalanceView.value.currency,
        usdtUsd.value,
      ) ?? 0,
  );
  const mt5Available = computed(
    () =>
      toUsdt(mt5BalanceView.value.availableBalance, mt5BalanceView.value.currency, usdtUsd.value) ??
      0,
  );
  const bybitUnrealized = computed(
    () =>
      toUsdt(
        venueUnrealizedPnl(observability.value?.bybit),
        bybitBalanceView.value.currency,
        usdtUsd.value,
      ) ?? 0,
  );
  const mt5Unrealized = computed(
    () =>
      toUsdt(
        venueUnrealizedPnl(observability.value?.mt5),
        mt5BalanceView.value.currency,
        usdtUsd.value,
      ) ?? 0,
  );
  // Native account values remain separate. This cross-venue total uses the
  // current USDT/USD quote and the supported UST = USDT convention.
  const totalEquity = computed(() => bybitEquity.value + mt5Equity.value);
  const totalUnrealized = computed(() => bybitUnrealized.value + mt5Unrealized.value);
  const totalRealized = computed(() => derivedPnl.value.totalRealized);
  const strategyFees = computed(
    () => toNumber(bybitPnl.value?.fees) + toNumber(mt5Pnl.value?.fees),
  );
  const totalPnl = computed(() => totalUnrealized.value + totalRealized.value - strategyFees.value);
  // The historical accounting endpoints are not yet venue-reconciled for this
  // strategy. Do not turn their legacy rows into a zero realized PnL or fee.
  const verifiedHistoryAvailable = computed(() => false);
  const financialDataAvailable = computed(
    () =>
      observability.value?.status === 'complete' &&
      bybitBalanceView.value.available &&
      mt5BalanceView.value.available &&
      currenciesComparable.value &&
      usdtUsd.value !== null,
  );

  const pnlMetrics = computed<StrategyPnlMetric[]>(() => [
    {
      label: '累计总盈亏',
      value: '--',
      ratio: verifiedHistoryAvailable.value
        ? trustedDataNote(derivedPnl.value.trustedFillCount)
        : '历史已实现损益接口待对账',
      tone: 'neutral',
    },
    {
      label: '未实现盈亏',
      value: financialDataAvailable.value ? signedMoney(totalUnrealized.value, 'USDT') : '--',
      ratio: financialDataAvailable.value ? '当前双腿浮动' : '数据暂不可用',
      tone: financialDataAvailable.value ? toneFromNumber(totalUnrealized.value) : 'neutral',
    },
    {
      label: '已实现盈亏',
      value: '--',
      ratio: verifiedHistoryAvailable.value ? '基于可核验成交重算' : '历史已实现损益接口待对账',
      tone: 'neutral',
    },
    {
      label: '累计费用',
      value: '--',
      ratio: verifiedHistoryAvailable.value ? '双腿费用合计' : '历史费用接口待对账',
      tone: 'neutral',
    },
  ]);

  const capitalOverview = computed<StrategyKpiCard[]>(() => [
    {
      label: '总权益',
      value: financialDataAvailable.value ? money(totalEquity.value, 'USDT') : '--',
      note: financialDataAvailable.value
        ? '跨所总权益（Bybit + MT5，按当前 USDT/USD 折算）'
        : currencyMismatchNote.value || '数据暂不可用',
      tone: financialDataAvailable.value ? toneFromNumber(totalPnl.value) : 'neutral',
    },
    {
      label: 'Bybit 权益',
      value: bybitBalanceView.value.available
        ? money(bybitBalanceView.value.equity ?? 0, bybitBalanceView.value.currency)
        : '--',
      note:
        bybitBalanceView.value.available && currenciesComparable.value
          ? `可用 ${money(
              bybitBalanceView.value.availableBalance ?? 0,
              bybitBalanceView.value.currency,
            )} · ${formatTime(bybitBalanceView.value.asOf)}`
          : currencyMismatchNote.value || '数据暂不可用',
      tone: 'neutral',
    },
    {
      label: 'MT5 权益',
      value: mt5BalanceView.value.available
        ? money(mt5BalanceView.value.equity ?? 0, mt5BalanceView.value.currency)
        : '--',
      note:
        mt5BalanceView.value.available && currenciesComparable.value
          ? `可用 ${money(
              mt5BalanceView.value.availableBalance ?? 0,
              mt5BalanceView.value.currency,
            )} · ${formatTime(mt5BalanceView.value.asOf)}`
          : currencyMismatchNote.value || '数据暂不可用',
      tone: 'neutral',
    },
    {
      label: '实时状态',
      value: observability.value?.status === 'complete' ? '双边已连通' : '数据待补齐',
      note: `Bybit ${venueStatusNote(observability.value?.bybit)} / MT5 ${venueStatusNote(
        observability.value?.mt5,
      )}`,
      tone: observability.value?.status === 'complete' ? 'positive' : 'neutral',
    },
  ]);

  const capitalStructureCards = computed<StrategyAccountBreakdown[]>(() => [
    {
      label: bybitBinding.value?.accountCode || 'Bybit 账户',
      value:
        bybitBalanceView.value.available && currenciesComparable.value
          ? money(bybitBalanceView.value.equity ?? 0, bybitBalanceView.value.currency)
          : '--',
      note: bybitBalanceView.value.available
        ? `浮盈 ${signedMoney(
            venueUnrealizedPnl(observability.value?.bybit),
            bybitBalanceView.value.currency,
          )}`
        : '数据暂不可用',
      tone: toneFromNumber(bybitUnrealized.value),
    },
    {
      label: mt5Binding.value?.accountCode || 'MT5 账户',
      value:
        mt5BalanceView.value.available && currenciesComparable.value
          ? money(mt5BalanceView.value.equity ?? 0, mt5BalanceView.value.currency)
          : '--',
      note: mt5BalanceView.value.available
        ? `浮盈 ${signedMoney(
            venueUnrealizedPnl(observability.value?.mt5),
            mt5BalanceView.value.currency,
          )}`
        : '数据暂不可用',
      tone: toneFromNumber(mt5Unrealized.value),
    },
  ]);

  const curvePoints = computed<
    Array<{ time: string; equity: number; capitalBase: number; nav: number; currency: string }>
  >(() => []);

  const capitalCurveConfig = computed<StrategyCapitalProfile['curve']>(() => {
    const points = curvePoints.value;
    const netValueData = points.map((point) => Number(point.nav.toFixed(4)));
    const equityData = points.map((point) => point.equity);
    const pointDrawdowns = drawdowns(netValueData);
    const latestNav = netValueData[netValueData.length - 1] ?? 0;
    const maxDrawdown = Math.min(...pointDrawdowns, 0);
    return {
      title: '账户净值',
      subtitle: '基于双腿账户实时权益聚合',
      metricOptions: [{ key: 'nav', label: '净值' }],
      periodOptions: [{ key: 'all', label: '全部' }],
      defaultMetric: 'nav',
      defaultPeriod: 'all',
      xLabels: points.map((point) => formatLabelTime(point.time)),
      netValueData,
      drawdownData: pointDrawdowns,
      summaries: [
        {
          label: '最新净值',
          value: points.length ? latestNav.toFixed(4) : '--',
          tone: points.length && latestNav >= 1 ? 'positive' : 'neutral',
        },
        {
          label: '账户权益',
          value: points.length ? money(equityData[equityData.length - 1] ?? 0, 'USDT') : '--',
        },
        {
          label: '最大回撤',
          value: points.length ? percent(maxDrawdown) : '--',
          tone: maxDrawdown < 0 ? 'negative' : 'neutral',
        },
      ],
    };
  });

  const pnlProfile = computed<StrategyPnlProfile>(() => {
    const baseProfile = strategyPnlProfiles.crossSpread;
    const points = curvePoints.value;
    const netValues = points.map((point) => Number(point.nav.toFixed(4)));
    const totalPnlSeries =
      financialDataAvailable.value && derivedPnl.value.points.length
        ? derivedPnl.value.points.map((point) => point.totalRealized)
        : [];
    const returns = dayReturns(totalPnlSeries);
    const bybitPosition = observability.value?.bybit?.positions?.find(hasLivePosition) ?? null;
    const mt5Position = observability.value?.mt5?.positions?.find(hasLivePosition) ?? null;

    const attributionOverlay = new Map<string, StrategyPnlAttributionItem>([
      [
        'XAUT/XAU价差损益',
        {
          label: 'XAUT/XAU价差损益',
          value: '--',
          ratio: verifiedHistoryAvailable.value
            ? trustedDataNote(derivedPnl.value.trustedFillCount)
            : '历史已实现损益接口待对账',
          tone: 'neutral',
        },
      ],
      [
        '腿间持仓损益',
        {
          label: '腿间持仓损益',
          value: financialDataAvailable.value ? signedMoney(totalUnrealized.value, 'USDT') : '--',
          ratio: financialDataAvailable.value ? '当前双腿浮动' : '数据暂不可用',
          tone: financialDataAvailable.value ? toneFromNumber(totalUnrealized.value) : 'neutral',
        },
      ],
      [
        '累计交易成本',
        {
          label: '累计交易成本',
          value: '--',
          ratio: verifiedHistoryAvailable.value ? '双腿费用合计' : '历史费用接口待对账',
          tone: 'neutral',
        },
      ],
    ]);

    const attributions: StrategyPnlAttributionItem[] = baseProfile.attributions.map(
      (item) =>
        attributionOverlay.get(item.label) ?? {
          label: item.label,
          value: '--',
          ratio: '接口待接入',
          tone: 'neutral',
        },
    );

    const detailCurveOverlay = new Map<
      string,
      {
        value: string;
        tone: MetricTone;
        data: number[];
      }
    >([
      [
        'XAUT/XAU价差损益',
        {
          value: '--',
          tone: 'neutral',
          data: [],
        },
      ],
      [
        '腿间持仓损益',
        {
          value: financialDataAvailable.value ? signedMoney(totalUnrealized.value, 'USDT') : '--',
          tone: financialDataAvailable.value ? toneFromNumber(totalUnrealized.value) : 'neutral',
          data: financialDataAvailable.value ? points.map(() => totalUnrealized.value) : [],
        },
      ],
      [
        '累计交易成本',
        {
          value: '--',
          tone: 'neutral',
          data: [],
        },
      ],
    ]);

    const detailCurves: StrategyCurveCard[] = baseProfile.detailCurves.map((item) => {
      const overlay = detailCurveOverlay.get(item.title);
      return {
        title: item.title,
        amount: overlay?.value ?? '--',
        unit: '',
        tone: overlay?.tone ?? 'neutral',
        points: points.map((point, index) => ({
          date: formatLabelTime(point.time),
          value: overlay?.data[index] ?? 0,
        })),
      };
    });

    const breakdownSeries = baseProfile.breakdownSeries.map((item) => {
      if (item.name === '净收益') {
        return { ...item, data: totalPnlSeries };
      }
      if (item.name === '手续费') {
        return { ...item, data: points.map(() => -strategyFees.value) };
      }
      return { ...item, data: zeroSeries(points.length) };
    });

    return {
      title: '跨所价差损益总览',
      totalFund: financialDataAvailable.value ? money(totalEquity.value, 'USDT') : '--',
      period:
        points.length > 1
          ? `${formatTime(points[0].time)} - ${formatTime(points[points.length - 1].time)}`
          : formatTime(points[0]?.time),
      xLabels: points.map((point) => formatLabelTime(point.time)),
      dailyReturns: returns,
      netValues,
      metrics: pnlMetrics.value,
      attributions,
      breakdownSeries,
      legSnapshots: [
        {
          title: 'Bybit 腿',
          venue:
            bybitBinding.value?.accountCode || observability.value?.bybit?.accountId || 'Bybit',
          symbol: observability.value?.bybit?.symbol || 'XAUTUSDT',
          rows: positionSnapshotRows(bybitPosition),
        },
        {
          title: 'MT5 腿',
          venue: mt5Binding.value?.accountCode || observability.value?.mt5?.accountId || 'MT5',
          symbol: observability.value?.mt5?.symbol || 'XAUUSD',
          rows: positionSnapshotRows(mt5Position),
        },
      ],
      detailCurves: detailCurves.map((item) => ({
        title: item.title,
        value: item.amount,
        tone: item.tone,
        data: item.points.map((point) => point.value),
      })),
    };
  });

  const liveCapitalProfile = computed<StrategyCapitalProfile>(() => {
    const bybitRisk = observability.value?.bybit?.accountRisk;
    const mt5Risk = observability.value?.mt5?.accountRisk;
    const bybitUsage =
      bybitEquity.value > 0
        ? ((bybitEquity.value - bybitAvailable.value) / bybitEquity.value) * 100
        : 0;
    const mt5Usage =
      mt5Equity.value > 0 ? ((mt5Equity.value - mt5Available.value) / mt5Equity.value) * 100 : 0;
    return {
      overview: capitalOverview.value,
      riskCards: [
        {
          label: 'Bybit 资金占用',
          value: percent(bybitUsage),
          note: bybitRisk?.marginMode || venueStatusNote(observability.value?.bybit),
          tone: bybitUsage > 80 ? 'negative' : 'neutral',
        },
        {
          label: 'MT5 资金占用',
          value: percent(mt5Usage),
          note: mt5Risk?.marginMode || venueStatusNote(observability.value?.mt5),
          tone: mt5Usage > 80 ? 'negative' : 'neutral',
        },
        {
          label: 'Bybit 浮盈',
          value:
            bybitBalanceView.value.available && currenciesComparable.value
              ? signedMoney(
                  venueUnrealizedPnl(observability.value?.bybit),
                  bybitBalanceView.value.currency,
                )
              : '--',
          note: bybitAccountId.value || '--',
          tone: toneFromNumber(bybitUnrealized.value),
        },
        {
          label: 'MT5 浮盈',
          value:
            mt5BalanceView.value.available && currenciesComparable.value
              ? signedMoney(
                  venueUnrealizedPnl(observability.value?.mt5),
                  mt5BalanceView.value.currency,
                )
              : '--',
          note: mt5AccountId.value || '--',
          tone: toneFromNumber(mt5Unrealized.value),
        },
      ],
      structureCards: capitalStructureCards.value,
      comparisonCards: [],
      curve: capitalCurveConfig.value,
      metricCurves: [],
    };
  });

  async function refresh() {
    loading.value = true;
    try {
      const [nextBindings, nextObservability, nextFills, nextMarketSnapshot] = await Promise.all([
        getStrategyAccountBindings(STRATEGY_INSTANCE_ID),
        getCrossSpreadObservability(1, 20, 'fast'),
        getFills(),
        getCrossSpreadSnapshot(),
      ]);

      bindings.value = nextBindings;
      observability.value = nextObservability;
      marketSnapshot.value = nextMarketSnapshot;
      fills.value = nextFills.filter(
        (fill) =>
          fill.instrumentId === BYBIT_INSTRUMENT_ID || fill.instrumentId === MT5_INSTRUMENT_ID,
      );

      const nextBybitBinding = firstActiveBinding(
        nextBindings,
        'venue_a',
        nextObservability.bybit?.accountId,
      );
      const nextMt5Binding = firstActiveBinding(
        nextBindings,
        'mt5_leg',
        nextObservability.mt5?.accountId,
      );

      const [
        nextBybitBalance,
        nextMt5Balance,
        nextBybitPnl,
        nextMt5Pnl,
        nextBybitEquityCurve,
        nextMt5EquityCurve,
      ] = await Promise.all([
        nextBybitBinding
          ? getAccountBalanceLatest(nextBybitBinding.accountId)
          : Promise.resolve(null),
        nextMt5Binding ? getAccountBalanceLatest(nextMt5Binding.accountId) : Promise.resolve(null),
        nextBybitBinding
          ? getTradingPnl(nextBybitBinding.accountId, BYBIT_INSTRUMENT_ID)
          : Promise.resolve(null),
        nextMt5Binding
          ? getTradingPnl(nextMt5Binding.accountId, MT5_INSTRUMENT_ID)
          : Promise.resolve(null),
        nextBybitBinding ? getEquityHistory(nextBybitBinding.accountId) : Promise.resolve([]),
        nextMt5Binding ? getEquityHistory(nextMt5Binding.accountId) : Promise.resolve([]),
      ]);

      bybitBalance.value = nextBybitBalance;
      mt5Balance.value = nextMt5Balance;
      bybitPnl.value = nextBybitPnl;
      mt5Pnl.value = nextMt5Pnl;
      bybitEquityHistory.value = nextBybitEquityCurve;
      mt5EquityHistory.value = nextMt5EquityCurve;
    } catch {
      bindings.value = [];
      observability.value = null;
      marketSnapshot.value = null;
      bybitEquityHistory.value = [];
      mt5EquityHistory.value = [];
      bybitBalance.value = null;
      mt5Balance.value = null;
      bybitPnl.value = null;
      mt5Pnl.value = null;
      fills.value = [];
    } finally {
      loading.value = false;
    }
  }

  return {
    loading,
    refresh,
    bybitBalance,
    mt5Balance,
    bybitPnl,
    mt5Pnl,
    bybitEquity,
    mt5Equity,
    totalEquity,
    totalUnrealized,
    totalRealized,
    capitalOverview,
    capitalStructureCards,
    liveCapitalProfile,
    pnlMetrics,
    pnlProfile,
    pnlTotalFund: computed(() => money(totalEquity.value, 'USDT')),
  };
}
