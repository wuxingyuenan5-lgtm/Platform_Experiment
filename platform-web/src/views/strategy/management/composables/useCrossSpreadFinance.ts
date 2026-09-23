import { computed, onBeforeUnmount, ref } from 'vue';

import {
  getStrategyAccountBindings,
  getStrategyAccountSnapshot,
  getStrategyPnl,
} from '@/api/platform/trading';
import { fetchStrategyQuery } from '@/api/platform/strategyQueries';
import type {
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
const CROSS_ACCOUNT_IDS = ['bybit-live-main', 'mt5-live-main'] as const;
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
): StrategyAccountSnapshotResult {
  const config = account.accountId ? CROSS_POSITION_INSTRUMENTS[account.accountId] : undefined;
  if (!config) return account;
  const positions = account.positions.filter(
    (position) =>
      position.instrumentId === config.instrumentId || position.symbol === config.symbol,
  );
  if (positions.length === account.positions.length) return account;
  return {
    ...account,
    positions,
    positionValue: null,
    positionValueNet: null,
    positionValueCurrency: null,
    leverage: null,
  };
}

export function mergeCrossDailyPnl(
  snapshots: StrategyAccountSnapshotResult[],
): NonNullable<StrategyAccountSnapshotResult['dailyPnl']> {
  const byDate = new Map<
    string,
    Array<{
      accountId: string | null;
      point: NonNullable<StrategyAccountSnapshotResult['dailyPnl']>[number];
    }>
  >();
  snapshots.forEach((snapshot) => {
    (snapshot.dailyPnl ?? []).forEach((point) => {
      const rows = byDate.get(point.date) ?? [];
      rows.push({ accountId: snapshot.accountId, point });
      byDate.set(point.date, rows);
    });
  });
  return [...byDate.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, rows]) => {
      const currencies = new Set(rows.map((row) => row.point.currency).filter(Boolean));
      const complete =
        snapshots.length === CROSS_ACCOUNT_IDS.length &&
        rows.length === CROSS_ACCOUNT_IDS.length &&
        new Set(rows.map((row) => row.accountId)).size === CROSS_ACCOUNT_IDS.length &&
        new Set(snapshots.map((snapshot) => snapshot.accountId)).size ===
          CROSS_ACCOUNT_IDS.length &&
        rows.every((row) =>
          CROSS_ACCOUNT_IDS.includes(row.accountId as (typeof CROSS_ACCOUNT_IDS)[number]),
        ) &&
        snapshots.every((snapshot) =>
          CROSS_ACCOUNT_IDS.includes(snapshot.accountId as (typeof CROSS_ACCOUNT_IDS)[number]),
        ) &&
        currencies.size === 1;
      const currency = currencies.size === 1 ? [...currencies][0] : rows[0]?.point.currency || '';
      const numericRows = rows.filter(
        (row) =>
          row.point.pnl != null &&
          row.point.equityOpen != null &&
          row.point.equityClose != null &&
          Number.isFinite(Number(row.point.pnl)) &&
          Number.isFinite(Number(row.point.equityOpen)) &&
          Number.isFinite(Number(row.point.equityClose)),
      );
      const pnl =
        complete && numericRows.length === rows.length
          ? numericRows.reduce((sum, row) => sum + Number(row.point.pnl), 0)
          : null;
      const equityOpen =
        complete && numericRows.length === rows.length
          ? numericRows.reduce((sum, row) => sum + Number(row.point.equityOpen), 0)
          : null;
      const equityClose =
        complete && numericRows.length === rows.length
          ? numericRows.reduce((sum, row) => sum + Number(row.point.equityClose), 0)
          : null;
      return {
        date,
        currency,
        pnl: pnl == null ? null : String(pnl),
        returnRate:
          pnl != null && equityOpen != null && equityOpen > 0
            ? String((pnl / equityOpen) * 100)
            : null,
        equityOpen: equityOpen == null ? null : String(equityOpen),
        equityClose: equityClose == null ? null : String(equityClose),
        quality: complete && pnl != null ? 'estimated' : 'missing_history',
      };
    });
}

export function useCrossSpreadFinance() {
  type FinanceSection = 'pnl' | 'capital' | 'orders';
  const loading = ref(false);
  const strategyPnl = ref<StrategyPnlResult | null>(null);
  const accounts = ref<StrategyAccountSnapshotResult[]>([]);
  const refreshFailure = ref(false);
  const pnlRefreshFailure = ref(false);
  const hasLoaded = ref(false);
  let disposed = false;
  let refreshGeneration = 0;

  async function load(section: FinanceSection, generation: number) {
    loading.value = true;
    try {
      const bindings = await fetchStrategyQuery(
        ['cross-spread', 'account-bindings', STRATEGY_INSTANCE_ID],
        () => getStrategyAccountBindings(STRATEGY_INSTANCE_ID),
      );
      const ids = [
        ...new Set(
          bindings
            .filter((item) => item.status === 'active' && item.role !== 'local_test')
            .map((item) => item.accountId),
        ),
      ];
      const [pnlResult, results] = await Promise.all([
        fetchStrategyQuery(['cross-spread', 'pnl', STRATEGY_INSTANCE_ID], () =>
          getStrategyPnl(STRATEGY_INSTANCE_ID),
        )
          .then((value) => ({ status: 'fulfilled' as const, value }))
          .catch((reason: unknown) => ({ status: 'rejected' as const, reason })),
        Promise.allSettled(
          ids.map((id) =>
            fetchStrategyQuery(
              ['cross-spread', 'account-snapshot', STRATEGY_INSTANCE_ID, id, 'summary'],
              (signal) =>
                getStrategyAccountSnapshot(STRATEGY_INSTANCE_ID, id, signal, {
                  includeDetails: false,
                }),
            ),
          ),
        ),
      ]);
      if (disposed || generation !== refreshGeneration) return;
      refreshFailure.value = results.some((result) => result.status === 'rejected');
      const nextAccounts = results.flatMap((result, index) => {
        if (result.status === 'fulfilled') return [result.value];
        const previous = accounts.value.find((item) => item.accountId === ids[index]);
        return previous ? [{ ...previous, isStale: true }] : [];
      });
      accounts.value = nextAccounts.map((account) => currentCrossPosition(account));
      if (pnlResult?.status === 'fulfilled') {
        pnlRefreshFailure.value = false;
        strategyPnl.value = pnlResult.value;
      } else if (pnlResult?.status === 'rejected') {
        pnlRefreshFailure.value = true;
        if (strategyPnl.value)
          strategyPnl.value = {
            ...strategyPnl.value,
            dataQualityState: 'partial',
            issues: [...(strategyPnl.value.issues ?? []), 'stale_strategy_pnl'],
          };
      }
    } catch {
      if (disposed || generation !== refreshGeneration) return;
      refreshFailure.value = true;
      if (section !== 'capital') pnlRefreshFailure.value = true;
      accounts.value = accounts.value.map((item) => ({ ...item, isStale: true }));
      if (strategyPnl.value)
        strategyPnl.value = {
          ...strategyPnl.value,
          dataQualityState: 'partial',
          issues: [...(strategyPnl.value.issues ?? []), 'stale_account_snapshot'],
        };
    } finally {
      if (!disposed && generation === refreshGeneration) {
        loading.value = false;
        hasLoaded.value = true;
      }
    }
  }

  function refresh(section: FinanceSection = 'pnl'): Promise<void> {
    if (disposed) return Promise.resolve();
    const generation = ++refreshGeneration;
    return load(section, generation);
  }

  onBeforeUnmount(() => {
    disposed = true;
    refreshGeneration += 1;
  });

  const pnlProfile = computed(() =>
    financialProfile(
      '跨所价差损益',
      strategyPnl.value,
      pnlRefreshFailure.value
        ? '策略损益加载失败，保留最近成功数据'
        : accounts.value
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
        strategyDailyPnl: strategyPnl.value?.strategyDailyPnl,
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
    const sessionPoints = (bybit?.sessionEquityHistory ?? []).filter(
      (point) => point.totalAssets != null && Number.isFinite(Number(point.totalAssets)),
    );
    const lastSessionPoint = sessionPoints.at(-1);
    metricSeries['totalAssets:mt5_open'] = {
      title: '全账户总资产',
      xLabels: sessionPoints.map((point) => formatTime(point.asOf)),
      netValueData: sessionPoints.map((point) => Number(point.totalAssets)),
      drawdownData: sessionPoints.map((point) =>
        point.totalAssetsDrawdown == null ? null : Number(point.totalAssetsDrawdown),
      ),
      summaries: [
        {
          label: '有效开市估值',
          value: money(lastSessionPoint?.totalAssets, bybit?.accountRisk?.currency),
        },
        {
          label: '估值时间',
          value: lastSessionPoint ? formatTime(lastSessionPoint.asOf) : '暂无有效开市估值',
        },
      ],
    };
    const dataStatusCards = accounts.value.map((item) => {
      const name = item.accountCode || item.accountId || '--';
      const isProblem =
        item.isStale ||
        (item.accountId && item.syncStatus && !['ready', 'syncing'].includes(item.syncStatus));
      return {
        label: name,
        value: accountState(item),
        tone: isProblem ? ('negative' as const) : ('neutral' as const),
      };
    });
    const problemStatuses = dataStatusCards.filter((item) => item.tone === 'negative');
    const missingCrossLeg =
      accounts.value.length > 0 &&
      !CROSS_ACCOUNT_IDS.every((accountId) =>
        accounts.value.some((account) => account.accountId === accountId),
      );
    const statusValue = dataStatusCards.length
      ? refreshFailure.value || missingCrossLeg || problemStatuses.length
        ? problemStatuses.map((item) => `${item.label}：${item.value}`).join('；') ||
          (refreshFailure.value ? '账户数据加载失败，连接状态待核验' : '账户绑定不完整')
        : '全部正常'
      : refreshFailure.value
      ? '账户数据加载失败，连接状态待核验'
      : hasLoaded.value
      ? '暂未绑定账号'
      : '账户数据加载中';
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
            ? dataStatusCards
                .map(
                  (item, index) =>
                    `${item.label}：${item.value}；最后成功：${formatTime(
                      accounts.value[index].lastSuccessfulSyncAt || accounts.value[index].asOf,
                    )}`,
                )
                .join('；')
            : '--',
          tone:
            refreshFailure.value || missingCrossLeg || problemStatuses.length
              ? 'negative'
              : 'neutral',
        },
        ...(crossNetExposureCard ? [crossNetExposureCard] : []),
        ...profiles
          .flatMap((profile, index) =>
            profile.riskCards
              .filter((card) => card.label !== '数据状态')
              .filter((card) => !card.label.includes('净敞口'))
              .map((card) => ({
                ...card,
                label: `${accounts.value[index].accountCode} · ${card.label}`,
              }))
              .filter((card) => card.label !== 'MT5-LIVE-001 · 交易所杠杆设置'),
          )
          .sort((left, right) => {
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
        modeMetricKeys: ['totalAssets'],
        modeOptions: [
          { key: 'mt5_open', label: '过滤 MT5 休市' },
          { key: 'continuous', label: '7×24 小时' },
        ],
        defaultMode: 'mt5_open',
      },
    };
  });

  const financialSyncFailed = computed(() =>
    accounts.value.some((account) => account.financialSyncStatus === 'failed'),
  );
  return { loading, refresh, pnlProfile, liveCapitalProfile, financialSyncFailed };
}
