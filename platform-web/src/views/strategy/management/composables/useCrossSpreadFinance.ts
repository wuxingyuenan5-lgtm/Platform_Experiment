import { computed, ref } from 'vue';

import {
  getStrategyAccountBindings,
  getStrategyAccountSnapshot,
  getStrategyPnl,
} from '@/api/platform/trading';
import type {
  StrategyAccountSnapshotResult,
  StrategyPnlResult,
} from '@/api/platform/trading.types';
import type { StrategyCapitalProfile } from '@/data/sample/strategy';
import {
  accountCapitalProfile,
  accountState,
  financialProfile,
  formatTime,
  money,
} from './strategyFinancialPresentation';

const STRATEGY_INSTANCE_ID = 'strategy_cross_venue_spread_instance_default';

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
      accounts.value = results.flatMap((result, index) => {
        if (result.status === 'fulfilled') return [result.value];
        const previous = accounts.value.find((item) => item.accountId === ids[index]);
        return previous ? [{ ...previous, isStale: true }] : [];
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
    ),
  );

  const liveCapitalProfile = computed<StrategyCapitalProfile>(() => {
    const profiles = accounts.value.map((item) =>
      accountCapitalProfile(item.accountCode || '跨所价差', item),
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
    const first = profiles[0] || accountCapitalProfile('跨所价差', null);
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
      riskCards: profiles.flatMap((profile, index) =>
        profile.riskCards.map((card) => ({
          ...card,
          label: `${accounts.value[index].accountCode} · ${card.label}`,
        })),
      ),
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
