import { buildTradeRecords, recordTime } from './strategyTradeRecords';
import { computed, onBeforeUnmount, reactive } from 'vue';
import { nativeAmount, settlementLabel } from './strategyRecordPresentation';
import { useQueries } from '@tanstack/vue-query';
import {
  strategyQueryClient,
  strategyQueryKey,
  fetchStrategyQuery,
} from '@/api/platform/strategyQueries';
import {
  accountCapitalProfile,
  accountState,
  financialProfile,
  money,
} from './strategyFinancialPresentation';

import { getStrategyAccountSnapshot } from '@/api/platform/trading';
import type { StrategyAccountSnapshotResult } from '@/api/platform/trading.types';
import { strategyRegistryMap } from '@/views/strategy/shared/strategyRegistry';
import type {
  StrategyCapitalProfile,
  StrategyDeskKey,
  StrategyOrderProfile,
  StrategyPnlProfile,
  StrategyTableSection,
} from '@/data/sample/strategy';

type AccountStrategyDesk = 'funding' | 'dip' | 'shortLineTraderL' | 'shortLineTraderW';

const instanceIds: Record<AccountStrategyDesk, string> = {
  funding: 'strategy_funding_arbitrage_instance_default',
  dip: 'strategy_bottom_fishing_instance_default',
  shortLineTraderL: 'strategy_short_term_l_instance_default',
  shortLineTraderW: 'strategy_short_term_w_instance_default',
};

const labels: Record<AccountStrategyDesk, string> = {
  funding: '资费套利',
  dip: '抄底',
  shortLineTraderL: '短线交易员 WW',
  shortLineTraderW: '短线交易员 BL',
};

function accountDesk(key: StrategyDeskKey): key is AccountStrategyDesk {
  return key in instanceIds;
}

function orderProfile(
  desk: AccountStrategyDesk,
  snapshot: StrategyAccountSnapshotResult | null,
): StrategyOrderProfile {
  const records = buildTradeRecords(
    snapshot?.orders || [],
    snapshot?.fills || [],
    snapshot?.economicEvents || [],
  );
  if (snapshot && snapshot.fillsTotal > snapshot.fills.length) {
    records.fills.description += ` 当前载入最近 ${snapshot.fills.length} / ${snapshot.fillsTotal} 条成交。`;
    records.activity.description += ' 汇总范围为当前已载入的委托和成交。';
  }
  const tables: Record<string, StrategyTableSection> = {
    positions: {
      columns: [
        { key: 'instrumentId', label: '标的' },
        { key: 'quantity', label: '净持仓' },
        { key: 'averagePrice', label: '均价' },
        { key: 'currentPrice', label: '当前价格' },
        { key: 'unrealizedPnl', label: '浮盈亏' },
        { key: 'takeProfitPrice', label: '止盈' },
        { key: 'stopLossPrice', label: '止损' },
        { key: 'liquidationPrice', label: '强平价' },
        { key: 'swap', label: '库存费' },
      ],
      rows: (snapshot?.positions || []).map((position) => ({
        instrumentId: position.symbol || position.instrumentId,
        currentPrice: position.currentPrice || '--',
        unrealizedPnl: money(position.unrealizedPnl, position.currency || ''),
        takeProfitPrice: position.takeProfitPrice || '--',
        stopLossPrice: position.stopLossPrice || '--',
        liquidationPrice: position.liquidationPrice || '--',
        swap: money(position.swap, position.currency || ''),
        quantity: position.netQuantity,
        averagePrice: position.averagePrice || '--',
      })),
    },
    activity: records.activity,
    orders: records.orders,
    fills: records.fills,
    settlements: {
      columns: [
        { key: 'eventId', label: '流水ID' },
        { key: 'orderId', label: '订单ID' },
        { key: 'instructionId', label: '指令ID' },
        { key: 'time', label: '结算时间' },
        { key: 'kind', label: '类型' },
        { key: 'symbol', label: '标的' },
        { key: 'amount', label: '原币收支' },
        { key: 'source', label: '来源' },
      ],
      rows: (snapshot?.economicEvents ?? []).map((event) => ({
        eventId: event.externalEventId,
        orderId: event.orderId || '--',
        instructionId: event.instructionId || '--',
        source: event.source || '--',
        time: recordTime(event.occurredAt),
        kind: settlementLabel(event.eventType),
        symbol: event.symbol || '--',
        amount: nativeAmount(event.amount, event.currency),
      })),
    },
  };
  for (const section of Object.values(tables)) {
    if (snapshot?.snapshotScope === 'account') {
      section.description = `账户监控记录。${section.description || ''}`;
    }
    if (!snapshot?.accountId) section.emptyMessage = accountState(snapshot);
    if (snapshot?.isStale)
      section.description = `${accountState(snapshot)}。${section.description || ''}`;
  }
  return {
    label: `${labels[desk]}订单信息`,
    tabs: [
      { key: 'positions', label: '当前持仓' },
      { key: 'activity', label: '开平记录' },
      { key: 'fills', label: '逐笔成交' },
      {
        key: 'orders',
        label: `委托明细（最近 ${snapshot?.orders.length ?? 0} / ${snapshot?.ordersTotal ?? 0}）`,
      },
      {
        key: 'settlements',
        label: snapshot?.snapshotScope === 'strategy' ? '策略结算流水' : '结算流水',
      },
    ],
    tables,
  };
}

function distributionPositions(
  snapshot: StrategyAccountSnapshotResult | undefined,
): StrategyAccountSnapshotResult['positions'] {
  // The catalog read model already projects Funding strategy positions into
  // the snapshot. Finance history is not a second current-position source.
  return snapshot?.positions ?? [];
}

export function useStrategyAccountSnapshots() {
  const detailsModes = reactive<Record<AccountStrategyDesk, boolean>>({
    funding: false,
    dip: false,
    shortLineTraderL: false,
    shortLineTraderW: false,
  });
  let disposed = false;
  const queries = useQueries(
    {
      queries: computed(() =>
        (Object.keys(instanceIds) as AccountStrategyDesk[]).map((desk) => {
          const includeDetails = detailsModes[desk];
          return {
            queryKey: strategyQueryKey(
              'account-snapshot',
              instanceIds[desk],
              includeDetails ? 'full' : 'summary',
            ),
            queryFn: ({ signal }: { signal: AbortSignal }) =>
              getStrategyAccountSnapshot(instanceIds[desk], undefined, signal, {
                includeDetails,
              }),
            enabled: false,
          };
        }),
      ),
    },
    strategyQueryClient,
  );
  const desks = Object.keys(instanceIds) as AccountStrategyDesk[];
  const snapshots = computed(
    () =>
      Object.fromEntries(
        queries.value.map((query, index) => [
          desks[index],
          query.data && (query.isError ? { ...query.data, isStale: true } : query.data),
        ]),
      ) as Partial<Record<AccountStrategyDesk, StrategyAccountSnapshotResult>>,
  );
  const errors = computed(
    () =>
      Object.fromEntries(
        queries.value.map((query, index) => [
          desks[index],
          query.isError ? '账户数据加载失败，连接状态待核验' : '',
        ]),
      ) as Partial<Record<AccountStrategyDesk, string>>,
  );
  async function refresh(
    desk?: StrategyDeskKey,
    section: 'pnl' | 'capital' | 'orders' = 'capital',
  ) {
    if (disposed) return;
    const keys = desk && accountDesk(desk) ? [desk] : desks;
    keys.forEach((key) => {
      detailsModes[key] = section !== 'capital';
    });
    await Promise.allSettled(
      keys.map((key) =>
        fetchStrategyQuery(
          ['account-snapshot', instanceIds[key], detailsModes[key] ? 'full' : 'summary'],
          (signal) =>
            getStrategyAccountSnapshot(instanceIds[key], undefined, signal, {
              includeDetails: detailsModes[key],
            }),
        ),
      ),
    );
  }

  onBeforeUnmount(() => {
    disposed = true;
  });

  return {
    refresh,
    errors,
    financialSyncFailures: computed(
      () =>
        Object.fromEntries(
          desks.map((desk) => [desk, snapshots.value[desk]?.financialSyncStatus === 'failed']),
        ) as Record<AccountStrategyDesk, boolean>,
    ),
    loading: computed(
      () =>
        Object.fromEntries(
          queries.value.map((query, index) => [desks[index], query.isFetching]),
        ) as Record<AccountStrategyDesk, boolean>,
    ),
    pnlProfiles: computed(
      () =>
        Object.fromEntries(
          (Object.keys(instanceIds) as AccountStrategyDesk[]).map((desk) => [
            desk,
            financialProfile(
              `${labels[desk]}损益`,
              snapshots.value[desk]?.finance || null,
              errors.value[desk] || accountState(snapshots.value[desk] || null),
              desk === 'funding' ? 'funding' : undefined,
              {
                positions: distributionPositions(snapshots.value[desk]),
                positionValue: snapshots.value[desk]?.positionValue ?? null,
                positionValueNet: snapshots.value[desk]?.positionValueNet ?? null,
                dailyPnl: snapshots.value[desk]?.dailyPnl ?? [],
                strategyDailyPnl:
                  snapshots.value[desk]?.strategyDailyPnl ??
                  snapshots.value[desk]?.finance?.strategyDailyPnl ??
                  [],
              },
            ),
          ]),
        ) as Record<AccountStrategyDesk, StrategyPnlProfile>,
    ),
    capitalProfiles: computed(
      () =>
        Object.fromEntries(
          (Object.keys(instanceIds) as AccountStrategyDesk[]).map((desk) => {
            const snapshot = snapshots.value[desk];
            const capitalSnapshot = snapshot
              ? { ...snapshot, positions: distributionPositions(snapshot) }
              : null;
            return [
              desk,
              accountCapitalProfile(
                labels[desk],
                capitalSnapshot,
                errors.value[desk],
                strategyRegistryMap[desk].category,
              ),
            ];
          }),
        ) as Record<AccountStrategyDesk, StrategyCapitalProfile>,
    ),
    orderProfiles: computed(
      () =>
        Object.fromEntries(
          (Object.keys(instanceIds) as AccountStrategyDesk[]).map((desk) => [
            desk,
            orderProfile(desk, snapshots.value[desk] || null),
          ]),
        ) as Record<AccountStrategyDesk, StrategyOrderProfile>,
    ),
    isAccountStrategy: accountDesk,
  };
}
