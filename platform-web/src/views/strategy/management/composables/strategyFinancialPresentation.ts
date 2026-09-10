import type {
  FinancialAmountsResult,
  StrategyAccountSnapshotResult,
  StrategyPnlResult,
} from '@/api/platform/trading.types';
import type { StrategyCapitalProfile, StrategyPnlProfile } from '@/data/sample/strategy';
import { strategyPnlProfiles } from '@/data/sample/strategy';

export function money(value: string | null | undefined, currency = ''): string {
  if (value == null || value.trim() === '' || !Number.isFinite(Number(value))) return '--';
  return `${Number(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  })}${currency ? ` ${currency}` : ''}`;
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
  if (!snapshot.asOf) return '等待首次同步';
  if (snapshot.isStale) return '数据已陈旧，保留最近成功快照';
  return snapshot.syncStatus === 'syncing' ? '正在同步，展示最近成功快照' : '最近同步成功';
}

const issueLabels: Record<string, string> = {
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

export function financialProfile(
  title: string,
  finance: StrategyPnlResult | null,
  accountNote: string,
  desk?: 'funding' | 'crossSpread',
): StrategyPnlProfile {
  const note =
    finance?.issues?.map((issue) => issueLabels[issue] ?? '数据待核对').join('；') ||
    (finance ? '' : '等待损益数据');
  const currencies = finance?.byCurrency ?? [];
  const chartCurrency = currencies[0]?.currency ?? finance?.currency;
  const points = (finance?.timeline ?? []).filter(
    (point) => point.currency === chartCurrency && Number.isFinite(Number(point.realizedPnl)),
  );
  const from = finance?.coverage
    ?.map((item) => item.historyStart)
    .filter(Boolean)
    .sort()[0];
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
    curveCurrency: chartCurrency,
    timestamps: points.map((point) => point.asOf),
    totalFund: accountNote,
    period: [from ? `最近拉取覆盖自 ${formatTime(from)}` : '', note].filter(Boolean).join('；'),
    xLabels: points.map((point) => formatTime(point.asOf)),
    dailyReturns: [],
    netValues: points.map((point) => Number(point.realizedPnl)),
    metrics: original
      ? original.metrics.map((item) => category(item.label))
      : amountCards(finance, note),
    attributions: original
      ? original.attributions.map((item) => category(item.label))
      : currencies.length > 1
      ? currencies.flatMap((item) =>
          amountCards(item, `${item.currency} 原币口径`).map((card) => ({
            ...card,
            label: `${item.currency} · ${card.label}`,
          })),
        )
      : [],
    breakdownSeries: original
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

export function accountCapitalProfile(
  title: string,
  snapshot: StrategyAccountSnapshotResult | null,
  loadError?: string,
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
        ? [card('全账户总资产', risk.totalAssets, '多币种统一估值；下方展示原币资产')]
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
        tone: snapshot?.isStale ? 'negative' : 'neutral',
      },
      {
        label: '账户权限',
        value:
          snapshot?.capability === 'read_only'
            ? '仅读取'
            : snapshot?.capability === 'trade_and_read'
            ? '可交易、可读取'
            : snapshot
            ? '未绑定'
            : '等待账户数据',
        note: snapshot?.accountCode || '--',
        tone: 'neutral',
      },
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
