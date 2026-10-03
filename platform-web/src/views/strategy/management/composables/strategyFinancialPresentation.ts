import type {
  FinancialAmountsResult,
  StrategyAccountSnapshotResult,
  StrategyPnlResult,
} from '@/api/platform/trading.types';
import {
  strategyPnlProfiles,
  type StrategyCapitalProfile,
  type StrategyCapitalRiskCard,
  type StrategyPnlDayPoint,
  type StrategyPnlProfile,
  type StrategyPositionDistribution,
} from '@/data/sample/strategy';
import type { StrategyCategory } from '@/views/strategy/shared/strategyRegistry';

type SnapshotPosition = StrategyAccountSnapshotResult['positions'][number];

export interface FundingExposureGroup {
  roundingBalanced?: boolean;
  instructionId: string;
  perpetualSymbol?: string | null;
  netDeltaQuantity?: string | null;
  spotQuantityStep?: string | null;
  remainingSpotHolding?: string | null;
  remainingPerpetualQuantity?: string | null;
  lifecycleState?: string | null;
}

/**
 * 损益面板的账户读数：逐腿持仓、后端给出的账户级双边/净名义口径，
 * 以及后端逐日盈亏序列（已剔除出入金，日历只做区间聚合）。
 */
export interface PnlAccountInput {
  positions: SnapshotPosition[];
  positionValue?: string | null;
  positionValueNet?: string | null;
  dailyPnl?: StrategyAccountSnapshotResult['dailyPnl'];
  strategyDailyPnl?: StrategyPnlResult['strategyDailyPnl'];
}

export function money(value: string | null | undefined, currency = ''): string {
  if (value == null || value.trim() === '' || !Number.isFinite(Number(value))) return '--';
  return `${Number(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  })}${currency ? ` ${currency}` : ''}`;
}

/** 合约、盈亏这类字符串型小数：空值保持为空，不折算成 0。 */
function numeric(value: unknown): number | null {
  if (typeof value !== 'string' && typeof value !== 'number') return null;
  if (typeof value === 'string' && value.trim() === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return '--';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '--' : date.toLocaleString('zh-CN', { hour12: false });
}

export function accountState(snapshot: StrategyAccountSnapshotResult | null): string {
  if (!snapshot) return '等待账户数据';
  if (!snapshot.accountId) return '暂未绑定账号';
  if (snapshot.syncStatus === 'identity_mismatch') return '账户身份校验失败';
  if (snapshot.syncStatus === 'restore_failed') return '主账号恢复失败';
  if (snapshot.syncStatus && !['ready', 'syncing'].includes(snapshot.syncStatus))
    return '账户同步失败，保留最近成功快照';
  if (!snapshot.asOf) return '等待首次同步';
  if (snapshot.isStale) return '数据已陈旧，保留最近成功快照';
  return snapshot.syncStatus === 'syncing' ? '正在同步，展示最近成功快照' : '最近同步成功';
}

const issueLabels: Record<string, string> = {
  management_projection_stale: '后台统计更新延迟，保留最近成功结果',
  session_marks_unavailable: '缺少双边开市估值',
  historical_carry_unavailable: '缺少开市估值时点的库存费',
  waiting_initial_sync: '等待首次同步',
  fill_details_pending: '部分成交费用仍待同步',
  opening_cost_basis_unavailable: '历史开仓成本不完整',
  fee_currency_unavailable: '部分手续费币种缺失',
  stale_account_snapshot: '账户快照已陈旧',
  economic_events_pending: '结算流水待同步',
  mark_price_unavailable: '部分持仓缺少最新估值',
  historical_fx_unavailable: '不同币种分别展示',
  unattributed_economic_events: '部分结算尚未归属策略',
};
const amountFields = [
  ['realizedPnl', '已实现交易损益'],
  ['tradingPnl', '持仓浮盈亏'],
  ['fees', '手续费支出'],
  ['fundingPnl', '资金费收支'],
  ['swapPnl', '库存费收支'],
  ['netPnl', '净损益'],
] as const;

function amountCards(finance: FinancialAmountsResult | null, note: string) {
  return amountFields.map(([key, label]) => {
    const value = finance?.[key];
    const sign = value == null ? 0 : Number(value) * (key === 'fees' ? -1 : 1);
    return {
      label,
      value: money(value, finance?.currency),
      ratio: note,
      tone:
        sign > 0 ? ('positive' as const) : sign < 0 ? ('negative' as const) : ('neutral' as const),
    };
  });
}

const sideLabels: Record<'long' | 'short', string> = { long: '多头', short: '空头' };

type PositionLeg = {
  position: SnapshotPosition;
  value: number;
  side: 'long' | 'short';
  identityKey: string;
  quantity: number;
  unit: string;
  assetKey: string;
  assetLabel: string;
};
type PositionAggregate = { currency: string; netValue: number; grossValue: number };
type QuantityAggregate = {
  netQuantity: number;
  longQuantity: number;
  shortQuantity: number;
  unit: string;
  assetLabel: string;
};

function normalizePositionSymbol(value?: string | null): string {
  return value == null ? '' : value.trim().replace(/\s+/g, '');
}

function positionAssetDescriptor(position: SnapshotPosition) {
  const symbol = normalizePositionSymbol(
    position.symbol || position.instrumentId || '--',
  ).toUpperCase();
  if (symbol.includes('XAU')) return { key: 'XAU', label: '黄金', unit: 'oz' };
  const instrumentAsset = symbol
    .replace(/^INSTRUMENT_/, '')
    .replace(/_(?:SPOT|PERP)$/, '')
    .split('_')[0];
  const coin = symbol.startsWith('INSTRUMENT_')
    ? instrumentAsset
    : symbol.replace(/USDT$|USDC$|USD$|PERP$|永续$/g, '');
  return { key: coin || symbol || '--', label: coin || symbol || '--', unit: '枚' };
}

function positionQuantityMultiplier(
  position: SnapshotPosition,
  desk?: 'funding' | 'crossSpread',
): number {
  const symbol = normalizePositionSymbol(
    position.symbol || position.instrumentId || '--',
  ).toUpperCase();
  if (
    desk === 'crossSpread' &&
    position.instrumentType === 'mt5_contract' &&
    symbol.includes('XAU')
  )
    return 100;
  return 1;
}

function formatPositionQuantity(value: number, unit: string): string {
  return `${value.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  })} ${unit}`;
}

function netQuantitySummary(positions: SnapshotPosition[], desk?: 'funding' | 'crossSpread') {
  const byAsset = new Map<string, { net: number; unit: string; label: string }>();
  for (const position of positions) {
    const raw = numeric(position.netQuantity);
    if (raw == null || raw === 0) continue;
    const asset = positionAssetDescriptor(position);
    const current = byAsset.get(asset.key) || { net: 0, unit: asset.unit, label: asset.label };
    current.net += raw * positionQuantityMultiplier(position, desk);
    byAsset.set(asset.key, current);
  }
  const tolerance = 1e-9;
  const rows = [...byAsset.values()];
  if (!rows.length) return null;
  const unbalanced = rows.some((item) => Math.abs(item.net) > tolerance);
  const value = rows
    .map((item) => {
      const net = Math.abs(item.net) <= tolerance ? 0 : item.net;
      const side = net > 0 ? '净多' : net < 0 ? '净空' : '净额';
      return `${item.label}: ${side} ${formatPositionQuantity(Math.abs(net), item.unit)}`;
    })
    .join('；');
  return { value, unbalanced };
}

export function netExposureRiskCard(
  positions: SnapshotPosition[],
  desk?: 'funding' | 'crossSpread',
): StrategyCapitalRiskCard | null {
  // Funding exposure is defined by each order group, not by symbol-level
  // aggregation. Callers must use fundingGroupExposureRiskCard instead.
  if (desk === 'funding') return null;
  const summary = netQuantitySummary(positions, desk);
  if (!summary) return null;
  return {
    label: '净敞口',
    value: summary.unbalanced ? `未配平：${summary.value}` : summary.value,
    note: summary.unbalanced
      ? '多空标的数量未配平，请核对双腿持仓'
      : '按标的原币数量相抵，当前已配平',
    tone: summary.unbalanced ? 'negative' : 'neutral',
  };
}

export function fundingGroupExposureRiskCard(
  groups: FundingExposureGroup[],
): StrategyCapitalRiskCard | null {
  const active = groups.filter((group) => group.lifecycleState === 'active');
  if (!active.length) return null;
  const rows = active.map((group) => ({
    label: group.perpetualSymbol || group.instructionId,
    spot: numeric(group.remainingSpotHolding),
    perpetual: numeric(group.remainingPerpetualQuantity),
    net:
      numeric(group.netDeltaQuantity) ??
      (numeric(group.remainingSpotHolding) != null &&
      numeric(group.remainingPerpetualQuantity) != null
        ? numeric(group.remainingSpotHolding)! - numeric(group.remainingPerpetualQuantity)!
        : Number.NaN),
    roundingBalanced: group.roundingBalanced === true,
    tolerance:
      Number.isFinite(Number(group.spotQuantityStep)) && Number(group.spotQuantityStep) > 0
        ? Number(group.spotQuantityStep)
        : 1e-9,
  }));
  const value = rows
    .map((row) => {
      const net = Number.isFinite(row.net) && Math.abs(row.net) > row.tolerance ? row.net : 0;
      const side = net > 0 ? '净多' : net < 0 ? '净空' : '净额';
      const spot =
        row.spot != null && Number.isFinite(row.spot)
          ? formatPositionQuantity(row.spot, '枚')
          : '--';
      const perpetual =
        row.perpetual != null && Number.isFinite(row.perpetual)
          ? formatPositionQuantity(row.perpetual, '枚')
          : '--';
      const netText = Number.isFinite(row.net)
        ? `${side} ${formatPositionQuantity(Math.abs(row.net), '枚')}`
        : '待核对';
      return `${row.label}: 现货 ${spot}；永续 ${perpetual}；${netText}`;
    })
    .join('；');
  const unbalanced = rows.some(
    (row) => !row.roundingBalanced && Number.isFinite(row.net) && Math.abs(row.net) > row.tolerance,
  );
  return {
    label: '净敞口',
    value: unbalanced ? `未配平：${value}` : value,
    note: unbalanced
      ? '按每个资费订单组的现货与永续两条腿核对'
      : '各资费订单组已按最小单位配平，实际余差保留展示',
    tone: unbalanced ? 'negative' : 'neutral',
  };
}

/**
 * 仓位分布：按标的拆解持仓名义价值，用于观察风险集中度与对冲双腿配比。
 *
 * 只使用交易所上报的 `positionValue`（策略口径下由后端读模型按合约乘数还原），
 * 前端不自行推算名义价值；多币种并存时按原币分组分别计算占比，不发明汇率。
 */
export function buildPositionDistribution(
  positions: SnapshotPosition[],
  grossValue?: string | null,
  netValue?: string | null,
  desk?: 'funding' | 'crossSpread',
): StrategyPositionDistribution {
  const normalizeCurrency = (value?: string | null) =>
    value == null ? '' : value.trim().toUpperCase();
  const resolveCurrency = (position: SnapshotPosition) => {
    return normalizeCurrency(position.positionValueCurrency);
  };
  const resolveSymbol = (position: SnapshotPosition) =>
    normalizePositionSymbol(position.symbol || position.instrumentId || '--');
  const sideFromQuantity = (position: SnapshotPosition): 'long' | 'short' => {
    const netQuantity = numeric(position.netQuantity);
    if (netQuantity != null && netQuantity !== 0) return netQuantity > 0 ? 'long' : 'short';
    const positionValue = numeric(position.positionValue);
    if (positionValue != null && positionValue !== 0) return positionValue > 0 ? 'long' : 'short';
    return 'long';
  };
  const assetDescriptor = (position: SnapshotPosition) => {
    return positionAssetDescriptor(position);
  };
  const quantityMultiplier = (position: SnapshotPosition) => {
    return positionQuantityMultiplier(position, desk);
  };
  const positionQuantity = (position: SnapshotPosition, value: number) => {
    const raw = numeric(position.netQuantity);
    if (raw == null || raw === 0) return value;
    return Math.abs(raw * quantityMultiplier(position));
  };
  const formatQuantity = formatPositionQuantity;
  const positionIdentityKey = (
    position: SnapshotPosition,
    value: number,
    side: 'long' | 'short',
  ) => {
    const symbol = resolveSymbol(position);
    const currency = resolveCurrency(position);
    const externalId = normalizePositionSymbol(position.externalPositionId);
    const venueHint = normalizePositionSymbol(position.category || position.instrumentType || '');
    if (externalId && externalId !== '0')
      return ['external', venueHint, symbol, externalId].join('@@');
    return [
      'fallback',
      venueHint,
      symbol,
      currency,
      side,
      numeric(position.netQuantity) ?? '',
      numeric(position.averagePrice) ?? '',
      value,
    ].join('@@');
  };

  const seenPositions = new Set<string>();
  const legs = positions
    .map((position) => {
      const raw = position.positionValue;
      if (raw == null) return null;
      const value = Number(raw);
      if (!Number.isFinite(value) || value === 0) return null;
      const side: 'long' | 'short' = sideFromQuantity(position);
      const absoluteValue = Math.abs(value);
      const asset = assetDescriptor(position);
      const identityKey = positionIdentityKey(position, absoluteValue, side);
      if (seenPositions.has(identityKey)) return null;
      seenPositions.add(identityKey);
      return {
        position,
        value: absoluteValue,
        side,
        identityKey,
        quantity: positionQuantity(position, absoluteValue),
        unit: asset.unit,
        assetKey: asset.key,
        assetLabel: asset.label,
      };
    })
    .filter((leg): leg is PositionLeg => leg !== null);
  const byCurrency = new Map<string, PositionLeg[]>();
  const bySymbol = new Map<string, PositionAggregate>();
  const byAssetQuantity = new Map<string, QuantityAggregate>();
  for (const leg of legs) {
    const currency = resolveCurrency(leg.position);
    byCurrency.set(currency, [...(byCurrency.get(currency) ?? []), leg]);
    const symbol = resolveSymbol(leg.position);
    const key = `${symbol}@@${currency}`;
    const current = bySymbol.get(key) || { currency, netValue: 0, grossValue: 0 };
    current.netValue += leg.side === 'short' ? -leg.value : leg.value;
    current.grossValue += leg.value;
    bySymbol.set(key, current);
    const assetCurrent = byAssetQuantity.get(leg.assetKey) || {
      netQuantity: 0,
      longQuantity: 0,
      shortQuantity: 0,
      unit: leg.unit,
      assetLabel: leg.assetLabel,
    };
    assetCurrent.netQuantity += leg.side === 'short' ? -leg.quantity : leg.quantity;
    if (leg.side === 'short') assetCurrent.shortQuantity += leg.quantity;
    else assetCurrent.longQuantity += leg.quantity;
    byAssetQuantity.set(leg.assetKey, assetCurrent);
  }
  const groups = [...byCurrency].map(([currency, rows]) => {
    const total = rows.reduce((sum, row) => sum + row.value, 0);
    return {
      currency,
      gross: money(String(total), currency),
      legs: rows.map((row) => ({
        label: `${normalizePositionSymbol(
          row.position.symbol || row.position.instrumentId || '--',
        )} · ${sideLabels[row.side]}`,
        side: row.side,
        value: row.value,
        amount: money(String(row.value), currency),
        share: total ? `${((row.value / total) * 100).toFixed(2)}%` : '--',
        currency,
        unit: row.unit,
        tone: 'neutral' as const,
      })),
    };
  });
  const mergedLegs = [...bySymbol].map(([key, aggregate]) => {
    const [symbol, currency] = key.split('@@');
    const net = aggregate.netValue;
    const side = net >= 0 ? ('long' as const) : ('short' as const);
    const netValue = Math.abs(net);
    const gross = aggregate.grossValue;
    return {
      symbol,
      currency,
      side,
      net: netValue,
      signedNet: net,
      gross,
    };
  });
  const mergedTotalGross = mergedLegs.reduce((sum, leg) => sum + leg.gross, 0);
  const mergedTotalSignedNet = mergedLegs.reduce((sum, leg) => sum + leg.signedNet, 0);
  const mergedTotalAbsNet = mergedLegs.reduce((sum, leg) => sum + leg.net, 0);
  const mixedCurrency = groups.length > 1;
  const grossByCurrency = new Map<string, number>();
  const netByCurrency = new Map<string, number>();
  for (const [currency, rows] of byCurrency.entries()) {
    const gross = rows.reduce((sum, row) => sum + row.value, 0);
    const net = rows.reduce((sum, row) => sum + (row.side === 'short' ? -row.value : row.value), 0);
    grossByCurrency.set(currency, gross);
    netByCurrency.set(currency, net);
  }
  const summarizeByCurrency = (totals: Map<string, number>) =>
    [...totals.entries()]
      .filter((item) => Number.isFinite(item[1]))
      .map(([currency, value]) => `${currency || '未标注'}: ${money(String(value), currency)}`)
      .join('；');
  const mixedGross = summarizeByCurrency(grossByCurrency);
  const mixedNet = summarizeByCurrency(netByCurrency);
  const quantityBySideSummary = () =>
    [...byAssetQuantity.values()]
      .map((item) => {
        const parts = [
          item.longQuantity > 0 ? `多头 ${formatQuantity(item.longQuantity, item.unit)}` : '',
          item.shortQuantity > 0 ? `空头 ${formatQuantity(item.shortQuantity, item.unit)}` : '',
        ].filter(Boolean);
        return parts.length ? `${item.assetLabel}: ${parts.join(' / ')}` : '';
      })
      .filter(Boolean)
      .join('；');
  const quantityNetSummary = () =>
    [...byAssetQuantity.values()]
      .map((item) => {
        const net = item.netQuantity;
        const side = net > 0 ? '净多' : net < 0 ? '净空' : '净额';
        return `${item.assetLabel}: ${side} ${formatQuantity(Math.abs(net), item.unit)}`;
      })
      .join('；');
  const appendQuantity = (amount: string, label: string, summary: string) =>
    summary ? `${amount}；${label}：${summary}` : amount;
  const mergedSlices = (desk === 'crossSpread' ? mergedLegs : [])
    .filter((item) => item.net > 0)
    .sort((left, right) => right.net - left.net)
    .map((item) => {
      const share = mixedCurrency
        ? '--'
        : mergedTotalAbsNet
        ? `${((item.net / mergedTotalAbsNet) * 100).toFixed(2)}%`
        : '--';
      return {
        label: `${item.symbol} · ${sideLabels[item.side]}`,
        side: item.side,
        value: item.net,
        amount: money(String(item.net), item.currency),
        share,
        currency: item.currency,
        tone: item.side === 'long' ? ('positive' as const) : ('negative' as const),
      };
    });
  const individualSlices = legs
    .sort((left, right) => right.value - left.value)
    .map((leg) => {
      const currency = resolveCurrency(leg.position);
      const symbol = resolveSymbol(leg.position);
      const currencyTotal = byCurrency.get(currency)?.reduce((sum, row) => sum + row.value, 0);
      return {
        label: `${symbol} · ${sideLabels[leg.side]}`,
        side: leg.side,
        value: leg.value,
        amount: money(String(leg.value), currency),
        share: currencyTotal ? `${((leg.value / currencyTotal) * 100).toFixed(2)}%` : '--',
        currency,
        tone: leg.side === 'long' ? ('positive' as const) : ('negative' as const),
      };
    });
  const slices = desk === 'crossSpread' ? mergedSlices : individualSlices;
  const isEmptyPosition =
    !slices.length &&
    legs.length > 0 &&
    positions.every((position) => numeric(position.positionValue) != null);
  // 只有真实的双腿一多一空才叫“双边对冲”，否则按单向合计表述，不替策略假设口径。
  const hedged =
    legs.some((leg) => leg.side === 'long') && legs.some((leg) => leg.side === 'short');
  const chartCurrency = mixedCurrency ? '' : groups[0]?.currency || '';
  // 普通账户优先取后端账户级读数；跨所价差用已去重的双腿重算，避免同一快照腿
  // 在上游重复投影时把展示值放大。
  const derivedGross = mergedTotalGross;
  const derivedNet = Math.abs(mergedTotalSignedNet);
  const preferDerivedExposure = desk === 'crossSpread';
  const settle = (reported: string | null | undefined, derived: number, mixedSummary: string) => {
    if (mixedCurrency) return mixedSummary || '--';
    if (reported != null) return money(reported, chartCurrency);
    return legs.length ? money(String(derived), chartCurrency) : '--';
  };
  return {
    title: '仓位分布',
    currency: chartCurrency,
    mixedCurrency,
    grossLabel: mixedCurrency
      ? '持仓价值（原币分别展示）'
      : hedged
      ? '持仓价值（双边）'
      : '持仓价值（合计）',
    gross: appendQuantity(
      mixedCurrency
        ? settle(null, derivedGross, mixedGross)
        : settle(preferDerivedExposure ? null : grossValue, derivedGross, ''),
      '标的数量',
      quantityBySideSummary(),
    ),
    netLabel: mixedCurrency
      ? '净敞口（原币分别展示）'
      : hedged
      ? '净敞口（对冲后）'
      : '净敞口（多空相抵后）',
    net: appendQuantity(
      mixedCurrency
        ? settle(null, derivedNet, mixedNet)
        : settle(preferDerivedExposure ? null : netValue, derivedNet, ''),
      '标的净额',
      quantityNetSummary(),
    ),
    groups,
    slices,
    emptyMessage: isEmptyPosition
      ? '对冲已平衡，当前净仓位为 0'
      : positions.length
      ? '持仓暂无可比名义价值'
      : '暂无持仓，等待账户上报',
  };
}

export function financialProfile(
  title: string,
  finance: StrategyPnlResult | null,
  accountNote: string,
  desk?: 'funding' | 'crossSpread',
  account: PnlAccountInput = { positions: [] },
): StrategyPnlProfile {
  const note =
    finance?.issues?.map((issue) => issueLabels[issue] ?? '数据待核对').join('；') ||
    (finance ? '' : '等待损益数据');
  const currencies = finance?.byCurrency ?? [];
  const chartCurrency = finance?.currency;
  // 策略页的日历与收益曲线共用策略归属序列；账户资金仍保留原始账户权益。
  const strategyScope = desk === 'funding' || desk === 'crossSpread';
  const sourceDailyPnl = strategyScope ? account.strategyDailyPnl ?? [] : account.dailyPnl ?? [];
  const dailyPnlPoints: StrategyPnlDayPoint[] = sourceDailyPnl.map((point) => ({
    date: point.date,
    pnl: numeric(point.pnl),
    rate: numeric(point.returnRate),
    quality: point.quality ?? 'unavailable',
  }));
  const curveDailyPoints = dailyPnlPoints.filter((point) => point.quality !== 'market_closed');
  const valuedDailyPoints = curveDailyPoints;
  let cumulativeDailyPnl = 0;
  const dailyCurveValues = valuedDailyPoints.map((point) => {
    if (
      point.pnl == null ||
      !Number.isFinite(point.pnl) ||
      !['complete', 'estimated'].includes(point.quality)
    ) {
      cumulativeDailyPnl = 0;
      return null;
    }
    cumulativeDailyPnl += point.pnl;
    return cumulativeDailyPnl;
  });
  const points = (strategyScope ? [] : finance?.timeline ?? []).filter(
    (point) => point.currency === chartCurrency && Number.isFinite(Number(point.realizedPnl)),
  );
  const liveCurveUsesDaily = dailyCurveValues.some((value) => value != null);
  const curveTimestamps = liveCurveUsesDaily
    ? valuedDailyPoints.map((point) => `${point.date}T23:59:59Z`)
    : points.map((point) => point.asOf);
  const curveLabels = liveCurveUsesDaily
    ? valuedDailyPoints.map((point) => point.date)
    : points.map((point) => formatTime(point.asOf));
  const original = desk ? strategyPnlProfiles[desk] : null;
  const fields: Record<string, keyof FinancialAmountsResult> = {
    累计总损益: 'netPnl',
    持仓损益: 'tradingPnl',
    资费收益: 'fundingPnl',
    资费: 'fundingPnl',
    库存费: 'swapPnl',
    累计交易成本: 'fees',
  };
  const category = (label: string) => {
    const field = fields[label];
    const raw = field && finance ? finance[field] : null;
    const value = typeof raw === 'string' ? raw : null;
    return {
      label,
      value: money(value, finance?.currency),
      ratio: note,
      tone: 'neutral' as const,
    };
  };
  return {
    title,
    curveKind: 'realized',
    curveBarLabel: liveCurveUsesDaily ? '每日净损益' : '每日已实现损益',
    curveLineLabel: strategyScope ? '区间累计净损益' : '累计已实现损益',
    curveCurrency: chartCurrency,
    timestamps: curveTimestamps,
    totalFund: accountNote,
    period: [
      finance?.valuationPolicy === 'mt5_open'
        ? `过滤 MT5 休市；有效估值：${formatTime(finance.valuationAsOf)}；开市后衔接上次有效估值`
        : '',
      liveCurveUsesDaily
        ? `自 ${valuedDailyPoints[0].date} 展示已记录历史；缺失处断开，各完整区间单独累计`
        : '暂无连续完整的每日损益',
      note,
    ]
      .filter(Boolean)
      .join('；'),
    xLabels: curveLabels,
    dailyReturns: liveCurveUsesDaily
      ? valuedDailyPoints.map((point, index) =>
          dailyCurveValues[index] == null ? null : point.pnl,
        )
      : [],
    netValues: liveCurveUsesDaily
      ? dailyCurveValues
      : points.map((point) => Number(point.realizedPnl)),
    metrics: finance
      ? amountCards(finance, note)
      : original
      ? original.metrics.map((item) => category(item.label))
      : [],
    attributions: finance
      ? currencies.length > 1
        ? currencies.flatMap((item) =>
            amountCards(item, '').map((card) => ({
              ...card,
              label: `${item.currency} · ${card.label}`,
            })),
          )
        : amountCards(finance, note)
      : original
      ? original.attributions.map((item) => category(item.label))
      : [],
    breakdownSeries: liveCurveUsesDaily
      ? [{ name: '区间累计净损益', color: '#3498db', data: dailyCurveValues }]
      : finance
      ? [
          {
            name: '累计已实现损益',
            color: '#3498db',
            data: points.map((point) => Number(point.realizedPnl)),
          },
        ]
      : original
      ? original.breakdownSeries.map((item) => ({ ...item, data: [] }))
      : [
          {
            name: `已实现交易损益 ${chartCurrency ?? ''}`,
            color: '#3498db',
            data: points.map((point) => Number(point.realizedPnl)),
          },
        ],
    legSnapshots: (finance?.byAccount ?? []).map((item) => ({
      title: item.accountId || '--',
      venue: item.currency,
      symbol: '成交与结算',
      rows: amountCards(item, note).map((card) => ({
        label: card.label,
        value: card.value,
        tone: card.tone,
      })),
    })),
    detailCurves: original
      ? original.detailCurves.map((item) => ({
          title: item.title,
          value: category(item.title).value,
          tone: 'neutral',
          data: [],
        }))
      : [],
    positionDistribution: buildPositionDistribution(
      account.positions,
      account.positionValue,
      account.positionValueNet,
      desk,
    ),
    dailyPnl: dailyPnlPoints,
    dailyPnlCurrency:
      (typeof sourceDailyPnl[0]?.currency === 'string' ? sourceDailyPnl[0].currency : null) ||
      chartCurrency ||
      '',
  };
}

const assetLabels: Record<string, string> = {
  FundingAccount: '资金账户',
  UnifiedTradingAccount: '统一交易账户',
  Earn: '理财',
  TradingBot: '交易机器人',
  CopyTrading: '跟单',
  TradFi: 'TradFi / MT5',
  Alpha: 'Alpha',
  Loans: '借贷',
  crypto: '加密资产',
  stocks: '股票 / RWA',
};

/**
 * 持仓价值与杠杆率卡片。
 *
 * 套利对冲类在策略口径下同时持有对冲双腿：双边名义反映对冲规模，净敞口反映
 * 方向性残留，两者必须分开呈现，否则会把对冲规模误读为方向性风险。贝塔类与
 * 日内类只有单向持仓，套用双边口径会低估敞口。账户口径（如跨所价差的单腿账户）
 * 不虚构配对敞口，只报该账户自身的持仓价值与杠杆率。
 *
 * 口径说明：`leverage` 为本地读数 = 持仓价值 / 账户权益；`venueLeverage` 为
 * 交易所/券商上报的账户参数，两者含义不同，分开命名以免混用。
 */
function exposureRiskCards(
  category: StrategyCategory,
  snapshot: StrategyAccountSnapshotResult | null,
  currency: string,
  fundingExposureGroups?: FundingExposureGroup[] | null,
): StrategyCapitalRiskCard[] {
  if (!snapshot) return [];
  const hedgedPair = category === 'arbitrage' && snapshot.snapshotScope === 'strategy';
  const legCurrency = snapshot.positionValueCurrency || currency;
  const cards: StrategyCapitalRiskCard[] = [];
  const netExposureCard = hedgedPair
    ? fundingExposureGroups != null
      ? fundingGroupExposureRiskCard(fundingExposureGroups)
      : null
    : null;
  if (netExposureCard) cards.push(netExposureCard);
  const leverage = snapshot.leverage == null ? null : Number(snapshot.leverage);
  if (leverage != null && Number.isFinite(leverage)) {
    cards.push({
      label: hedgedPair ? '杠杆率（双边）' : '杠杆率',
      value: `${leverage.toFixed(2)}X`,
      note: hedgedPair ? '双边持仓价值 / 账户权益' : '持仓价值 / 账户权益',
      tone: 'neutral',
    });
  }
  const venueLeverage = snapshot.venueLeverage == null ? null : Number(snapshot.venueLeverage);
  if (venueLeverage != null && Number.isFinite(venueLeverage)) {
    cards.push({
      label: '交易所杠杆设置',
      value: `${venueLeverage.toFixed(0)}X`,
      note: '交易所或券商账户参数，非策略实际占用',
      tone: 'neutral',
    });
  }
  const occupiedMargin = snapshot.accountRisk?.margin;
  const accountEquity = snapshot.accountRisk?.equity ?? snapshot.balance?.equity;
  const occupied = occupiedMargin == null ? null : Number(occupiedMargin);
  const equityBase = accountEquity == null ? null : Number(accountEquity);
  if (
    occupied != null &&
    Number.isFinite(occupied) &&
    equityBase != null &&
    Number.isFinite(equityBase) &&
    equityBase > 0
  ) {
    cards.push({
      label: hedgedPair ? '单边资金利用率' : '资金利用率',
      value: `${((occupied / equityBase) * 100).toFixed(2)}%`,
      note: hedgedPair
        ? '交易所上报占用保证金 / 账户权益；对冲账户双腿共用同一保证金池'
        : '交易所上报占用保证金 / 账户权益',
      tone: 'neutral',
    });
  }
  const liquidationLegs = (snapshot.positions ?? [])
    .map((position) => ({
      symbol: position.symbol || position.instrumentId,
      price: Number(position.liquidationPrice),
      mark: Number(position.currentPrice),
    }))
    .filter((leg) => Number.isFinite(leg.price) && leg.price > 0);
  if (liquidationLegs.length) {
    // 多腿账户并列展示逐腿爆仓价，按距当前价远近排序，最近的一条最先读到。
    const ranked = liquidationLegs
      .map((leg) => ({
        ...leg,
        distance:
          Number.isFinite(leg.mark) && leg.mark > 0 ? Math.abs(leg.price / leg.mark - 1) : null,
      }))
      .sort(
        (a, b) =>
          (a.distance ?? Number.POSITIVE_INFINITY) - (b.distance ?? Number.POSITIVE_INFINITY),
      );
    const nearest = ranked[0];
    cards.push({
      label: liquidationLegs.length > 1 ? '最近爆仓价' : '爆仓价',
      value: money(String(nearest.price), legCurrency),
      note:
        nearest.distance == null
          ? `${nearest.symbol} · 交易所上报逐腿爆仓价`
          : `${nearest.symbol} · 距当前价 ${(nearest.distance * 100).toFixed(2)}%`,
      tone: 'neutral',
    });
  } else {
    cards.push({
      label: '爆仓价',
      value: '--',
      note: '交易所未上报逐腿爆仓价，该账户按账户级风险率强平',
      tone: 'neutral',
    });
  }
  return cards;
}

export function accountCapitalProfile(
  title: string,
  snapshot: StrategyAccountSnapshotResult | null,
  loadError?: string,
  category: StrategyCategory = 'directional',
  fundingExposureGroups?: FundingExposureGroup[] | null,
): StrategyCapitalProfile {
  const risk = snapshot?.accountRisk;
  const currency = risk?.currency || snapshot?.balance?.currency || '';
  const note = loadError || accountState(snapshot);
  const isValuation = risk?.assetScope === 'unified_trading';
  const label = isValuation ? '统一交易账户权益' : '交易账户权益';
  const curveLabel = isValuation ? '全账户总资产' : label;
  const curveValue = isValuation ? risk?.totalAssets : snapshot?.balance?.equity;
  const history = (snapshot?.equityHistory ?? [])
    .map((point) => ({ ...point, value: isValuation ? point.totalAssets : point.equity }))
    .filter((point) => point.value != null && Number.isFinite(Number(point.value)));
  const card = (name: string, value: string | null | undefined, description = note) => ({
    label: name,
    value: money(value, currency),
    note: description,
    tone: 'neutral' as const,
  });
  return {
    overview: [
      ...(risk?.totalAssets != null
        ? [
            card(
              '全账户总资产',
              risk.totalAssets,
              risk.assetBreakdown?.some((asset) => asset.accountType === 'TradFi')
                ? '已含 MT5/TradFi 与现货资产及浮盈亏；不再另加 MT5 权益'
                : '账户资产估值，包含浮盈亏；下方展示原币资产',
            ),
          ]
        : []),
      card(label, snapshot?.balance?.equity),
      card('可用保证金', risk?.freeMargin, '交易保证金额度'),
      card('维持保证金', risk?.maintenanceMargin),
    ],
    riskCards: [
      {
        label: '数据状态',
        value: note,
        note: `最后成功：${formatTime(snapshot?.lastSuccessfulSyncAt || snapshot?.asOf)}`,
        tone:
          loadError ||
          snapshot?.isStale ||
          (snapshot?.accountId &&
            snapshot.syncStatus &&
            !['ready', 'syncing'].includes(snapshot.syncStatus))
            ? 'negative'
            : 'neutral',
      },
      ...exposureRiskCards(category, snapshot, currency, fundingExposureGroups),
      card('账户浮盈亏', risk?.unrealizedPnl, '账户范围，可能包含其他策略'),
    ],
    structureCards: ['FundingAccount', 'UnifiedTradingAccount', 'TradFi', 'Earn'].flatMap(
      (accountType) => {
        const item = risk?.assetBreakdown?.find((asset) => asset.accountType === accountType);
        return item
          ? [
              {
                label: assetLabels[accountType],
                value: money(item.totalEquity, item.valuationCurrency || currency),
                note: '',
                tone: 'neutral' as const,
              },
            ]
          : [];
      },
    ),
    comparisonCards: [],
    metricCurves: [],
    curve: {
      title: `${title} · ${curveLabel}`,
      subtitle: `${note}；回撤按展示区间剔除资金进出估算，缺失区间不显示`,
      metricOptions: [{ key: 'equity', label: `${curveLabel} ${currency}` }],
      periodOptions: [{ key: 'all', label: '已记录' }],
      defaultMetric: 'equity',
      defaultPeriod: 'all',
      timestamps: history.map((point) => point.asOf),
      xLabels: history.map((point) => formatTime(point.asOf)),
      netValueData: history.map((point) => Number(point.value)),
      drawdownData: history.map((point) => {
        const value = isValuation ? point.totalAssetsDrawdown : point.equityDrawdown;
        return value == null ? null : Number(value);
      }),
      summaries: [card(curveLabel, curveValue)],
    },
  };
}
