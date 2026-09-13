import { computed, ref } from 'vue';

import {
  getStrategyAccountBindings,
  getStrategyAccountSnapshot,
  getStrategyPnl,
  getTradingPosition,
} from '@/api/platform/trading';
import type {
  PositionResult,
  StrategyAccountSnapshotResult,
  StrategyPnlResult,
} from '@/api/platform/trading.types';
import type { StrategyCapitalProfile } from '@/data/sample/strategy';
import { getStrategyManifest } from '@/views/strategy/shared/strategyRegistry';
import {
  accountCapitalProfile,
  accountState,
  financialProfile,
  formatTime,
  money,
  netExposureRiskCard,
} from './strategyFinancialPresentation';

const STRATEGY_INSTANCE_ID = 'strategy_cross_venue_spread_instance_default';
const CROSS_POSITION_INSTRUMENTS: Record<
  string,
  {
    instrumentId: string;
    symbol: string;
    instrumentType: string;
    category: string;
    multiplier: number;
    valueCurrency: string;
  }
> = {
  'bybit-live-main': {
    instrumentId: 'instrument_xau_usdt_perp',
    symbol: 'XAUTUSDT',
    instrumentType: 'crypto_perp',
    category: 'linear',
    multiplier: 1,
    valueCurrency: 'USDT',
  },
  'mt5-live-main': {
    instrumentId: 'instrument_xau_usd',
    symbol: 'XAUUSD.S',
    instrumentType: 'mt5_contract',
    category: 'mt5',
    multiplier: 100,
    valueCurrency: 'USD',
  },
};

function currentCrossPosition(
  account: StrategyAccountSnapshotResult,
  live: PositionResult | null | undefined,
): StrategyAccountSnapshotResult {
  const config = account.accountId ? CROSS_POSITION_INSTRUMENTS[account.accountId] : undefined;
  if (!config || !live) return account;
  const previous =
    account.positions.find(
      (position) => position.instrumentId === config.instrumentId && position.currentPrice != null,
    ) ??
    account.positions.find((position) => position.instrumentId === config.instrumentId) ??
    null;
  const currentPrice = previous?.currentPrice ?? null;
  const quantity = Number(live.netQuantity);
  const price = Number(currentPrice);
  const positionValue =
    Number.isFinite(quantity) && Number.isFinite(price) && currentPrice != null
      ? String(Math.abs(quantity * config.multiplier * price))
      : previous?.positionValue ?? null;
  return {
    ...account,
    positions: [
      {
        ...previous,
        ...live,
        accountId: account.accountId || live.accountId,
        instrumentId: config.instrumentId,
        symbol: config.symbol,
        instrumentType: config.instrumentType,
        category: config.category,
        currentPrice,
        positionValue,
        positionValueCurrency: positionValue == null ? null : config.valueCurrency,
        currency: previous?.currency ?? config.valueCurrency,
      },
    ],
    positionValue,
    positionValueNet: positionValue,
    positionValueCurrency: positionValue == null ? null : config.valueCurrency,
  };
}

export function mergeCrossDailyPnl(
  snapshots: StrategyAccountSnapshotResult[],
): NonNullable<StrategyAccountSnapshotResult['dailyPnl']> {
  const byDate = new Map<
    string,
    Array<NonNullable<StrategyAccountSnapshotResult['dailyPnl']>[number]>
  >();
  snapshots.forEach((snapshot) => {
    (snapshot.dailyPnl ?? []).forEach((point) => {
      const rows = byDate.get(point.date) ?? [];
      rows.push(point);
      byDate.set(point.date, rows);
    });
  });
  return [...byDate.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, rows]) => {
    const currencies = new Set(rows.map((row) => row.currency).filter(Boolean));
    const complete = rows.length === snapshots.length && currencies.size === 1;
    const currency = currencies.size === 1 ? [...currencies][0] : rows[0]?.currency || '';
    const numericRows = rows.filter(
      (row) => row.pnl != null && row.equityOpen != null && row.equityClose != null,
    );
    const pnl = complete && numericRows.length === rows.length
      ? numericRows.reduce((sum, row) => sum + Number(row.pnl), 0)
      : null;
    const equityOpen = complete && numericRows.length === rows.length
      ? numericRows.reduce((sum, row) => sum + Number(row.equityOpen), 0)
      : null;
    const equityClose = complete && numericRows.length === rows.length
      ? numericRows.reduce((sum, row) => sum + Number(row.equityClose), 0)
      : null;
    return {
      date,
      currency,
      pnl: pnl == null ? null : String(pnl),
      returnRate: pnl != null && equityOpen != null && equityOpen > 0
        ? String((pnl / equityOpen) * 100)
        : null,
      equityOpen: equityOpen == null ? null : String(equityOpen),
      equityClose: equityClose == null ? null : String(equityClose),
      quality: complete && pnl != null ? 'estimated' : 'missing_history',
    };
  });
}

export function useCrossSpreadFinance() {
  const loading = ref(false);
  const strategyPnl = ref<StrategyPnlResult | null>(null);
  const accounts = ref<StrategyAccountSnapshotResult[]>([]);
  let inFlight: Promise<void> | null = null;

  async function load() {
    loading.value = true;
    try {
      const [bindings, pnl] = await Promise.all([
        getStrategyAccountBindings(STRATEGY_INSTANCE_ID),
        getStrategyPnl(STRATEGY_INSTANCE_ID),
      ]);
      const ids = [
        ...new Set(
          bindings
            .filter((item) => item.status === 'active' && item.role !== 'local_test')
            .map((item) => item.accountId),
        ),
      ];
      const results = await Promise.allSettled(
        ids.map((id) => getStrategyAccountSnapshot(STRATEGY_INSTANCE_ID, id)),
      );
      const nextAccounts = results.flatMap((result, index) => {
        if (result.status === 'fulfilled') return [result.value];
        const previous = accounts.value.find((item) => item.accountId === ids[index]);
        return previous ? [{ ...previous, isStale: true }] : [];
      });
      const livePositions = await Promise.allSettled(
        nextAccounts.map((account) => {
          const config = account.accountId ? CROSS_POSITION_INSTRUMENTS[account.accountId] : undefined;
          return config ? getTradingPosition(account.accountId || '', config.instrumentId) : null;
        }),
      );
      accounts.value = nextAccounts.map((account, index) => {
        const liveResult = livePositions[index];
        return currentCrossPosition(
          account,
          liveResult && liveResult.status === 'fulfilled' ? liveResult.value : null,
        );
      });
      strategyPnl.value = pnl;
    } catch {
      accounts.value = accounts.value.map((item) => ({ ...item, isStale: true }));
      if (strategyPnl.value)
        strategyPnl.value = {
          ...strategyPnl.value,
          dataQualityState: 'partial',
          issues: [...(strategyPnl.value.issues ?? []), 'stale_account_snapshot'],
        };
    } finally {
      loading.value = false;
    }
  }

  function refresh(_section: 'pnl' | 'capital' = 'pnl'): Promise<void> {
    if (!inFlight)
      inFlight = load().finally(() => {
        inFlight = null;
      });
    return inFlight;
  }

  const pnlProfile = computed(() =>
    financialProfile(
      '跨所价差损益',
      strategyPnl.value,
      accounts.value
        .map(
          (item) =>
            `${item.accountCode} 交易权益 ${money(
              item.balance?.equity,
              item.balance?.currency,
            )} · ${accountState(item)}`,
        )
        .join('；') || '等待绑定账户数据',
      'crossSpread',
      {
        positions: accounts.value.flatMap((item) => item.positions ?? []),
        dailyPnl: mergeCrossDailyPnl(accounts.value),
      },
    ),
  );

  const liveCapitalProfile = computed<StrategyCapitalProfile>(() => {
    const category = getStrategyManifest('crossSpread').category;
    const profiles = accounts.value.map((item) =>
      accountCapitalProfile(item.accountCode || '跨所价差', item, undefined, category),
    );
    const bybit = accounts.value.find((item) => item.accountRisk?.assetScope === 'unified_trading');
    const mt5 = accounts.value.find((item) => item.accountCode === 'MT5-LIVE-001');
    const choices = [
      { key: 'totalAssets', label: '全账户总资产', account: bybit, total: true },
      { key: 'mt5Equity', label: 'MT5-LIVE-001 · 交易账户权益', account: mt5, total: false },
      {
        key: 'bybitEquity',
        label: 'BYBIT-LIVE-001 · 统一交易账户权益',
        account: bybit,
        total: false,
      },
    ];
    const metricSeries = Object.fromEntries(
      choices.map(({ key, label, account, total }) => {
        const points = (account?.equityHistory || [])
          .map((point) => ({
            date: formatTime(point.asOf),
            value: total ? point.totalAssets : point.equity,
            drawdown: total ? point.totalAssetsDrawdown : point.equityDrawdown,
          }))
          .filter((point) => point.value != null && Number.isFinite(Number(point.value)));
        const currency = account?.accountRisk?.currency || account?.balance?.currency || '';
        return [
          key,
          {
            title: label,
            xLabels: points.map((point) => point.date),
            netValueData: points.map((point) => Number(point.value)),
            drawdownData: points.map((point) =>
              point.drawdown == null ? null : Number(point.drawdown),
            ),
            summaries: [
              {
                label,
                value: money(
                  total ? account?.accountRisk?.totalAssets : account?.balance?.equity,
                  currency,
                ),
              },
            ],
          },
        ];
      }),
    );
    const dataStatusCards = accounts.value.map((item) => {
      const name = item.accountCode || item.accountId || '--';
      const isProblem =
        item.isStale ||
        (item.accountId &&
          item.syncStatus &&
          !['ready', 'syncing'].includes(item.syncStatus));
      return {
        label: name,
        value: accountState(item),
        tone: isProblem ? ('negative' as const) : ('neutral' as const),
      };
    });
    const problemStatuses = dataStatusCards.filter((item) => item.tone === 'negative');
    const statusValue = dataStatusCards.length
      ? problemStatuses.length
        ? problemStatuses.map((item) => `${item.label}：${item.value}`).join('；')
        : '全部正常'
      : '等待绑定账户数据';
    const first = profiles[0] || accountCapitalProfile('跨所价差', null);
    const crossNetExposureCard = netExposureRiskCard(
      accounts.value.flatMap((item) => item.positions ?? []),
      'crossSpread',
    );
    return {
      ...first,
      overview: profiles
        .flatMap((profile, index) =>
          profile.overview.map((card) => ({
            ...card,
            label: `${accounts.value[index].accountCode} · ${card.label}`,
          })),
        )
        .filter((card) => card.label !== 'MT5-LIVE-001 · 维持保证金')
        .sort((a, b) => {
          const order = [
            'BYBIT-LIVE-001 · 全账户总资产',
            'BYBIT-LIVE-001 · 统一交易账户权益',
            'MT5-LIVE-001 · 交易账户权益',
            'BYBIT-LIVE-001 · 可用保证金',
            'MT5-LIVE-001 · 可用保证金',
            'BYBIT-LIVE-001 · 维持保证金',
          ];
          const rank = (label: string) => {
            const index = order.indexOf(label);
            return index < 0 ? order.length : index;
          };
          return rank(a.label) - rank(b.label);
        }),
      riskCards: [
        {
          label: '数据状态',
          value: statusValue,
          note: dataStatusCards.length
            ? dataStatusCards.map((item) => `${item.label}：${item.value}`).join('；')
            : '--',
          tone: problemStatuses.length ? 'negative' : 'neutral',
        },
        ...(crossNetExposureCard ? [crossNetExposureCard] : []),
        ...profiles.flatMap((profile, index) =>
          profile.riskCards
            .filter((card) => card.label !== '数据状态')
            .filter((card) => !card.label.includes('净敞口'))
            .map((card) => ({
              ...card,
              label: `${accounts.value[index].accountCode} · ${card.label}`,
            }))
            .filter((card) => card.label !== 'MT5-LIVE-001 · 交易所杠杆设置'),
        ).sort((left, right) => {
          const metricOrder = ['杠杆率', '爆仓价', '账户浮盈亏', '单边资金利用率'];
          const accountOrder = ['BYBIT-LIVE-001', 'MT5-LIVE-001'];
          const metricRank = (label: string) => {
            const index = metricOrder.findIndex((metric) => label.includes(metric));
            return index < 0 ? metricOrder.length : index;
          };
          const accountRank = (label: string) => {
            const index = accountOrder.findIndex((account) => label.startsWith(account));
            return index < 0 ? accountOrder.length : index;
          };
          const metricDiff = metricRank(left.label) - metricRank(right.label);
          if (metricDiff !== 0) return metricDiff;
          return accountRank(left.label) - accountRank(right.label);
        }),
      ],
      structureCards: profiles.flatMap((profile, index) =>
        profile.structureCards.map((card) => ({
          ...card,
          label: `${accounts.value[index].accountCode} · ${card.label}`,
        })),
      ),
      metricCurves: [],
      curve: {
        ...first.curve,
        ...metricSeries.totalAssets,
        defaultMetric: 'totalAssets',
        metricOptions: choices.map(({ key, label }) => ({ key, label })),
        metricSeries,
      },
    };
  });

  return { loading, refresh, pnlProfile, liveCapitalProfile };
}
