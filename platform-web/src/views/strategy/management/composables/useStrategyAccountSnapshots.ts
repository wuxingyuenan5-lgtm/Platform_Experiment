import { computed, ref } from 'vue';

import { getStrategyAccountSnapshot } from '@/api/platform/trading';
import type { StrategyAccountSnapshotResult } from '@/api/platform/trading.types';
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
  shortLineTraderL: '短线交易员 A',
  shortLineTraderW: '短线交易员 B',
};

const statusLabels: Record<string, string> = {
  filled: '已成交',
  acknowledged: '已受理',
  processing: '处理中',
  pending: '待处理',
  rejected: '已拒绝',
  result_unknown: '结果未知',
  canceled: '已撤单',
};

function accountDesk(key: StrategyDeskKey): key is AccountStrategyDesk {
  return key in instanceIds;
}

function money(value: string | null | undefined, currency = ''): string {
  if (value == null) return '--';
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return '--';
  return `${parsed.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}${currency ? ` ${currency}` : ''}`;
}

function signedMoney(value: string | null | undefined, currency = ''): string {
  if (value == null || !Number.isFinite(Number(value))) return '--';
  const parsed = Number(value);
  return `${parsed > 0 ? '+' : parsed < 0 ? '-' : ''}${money(String(Math.abs(parsed)), currency)}`;
}

function tone(value: string | null | undefined): 'positive' | 'negative' | 'neutral' {
  const parsed = Number(value);
  return parsed > 0 ? 'positive' : parsed < 0 ? 'negative' : 'neutral';
}

function formatTime(value: string | null | undefined): string {
  if (!value) return '--';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false });
}

function unavailableReason(snapshot: StrategyAccountSnapshotResult | null): string {
  if (!snapshot) return '账户快照未加载';
  if (snapshot.syncErrorCode === 'account_unbound') return '暂未绑定账号';
  if (snapshot.syncStatus === 'waiting_initial_sync') return '等待首次同步';
  if (snapshot.syncStatus === 'syncing') return '正在同步';
  if (snapshot.syncStatus === 'ready') return '最近同步成功';
  if (snapshot.syncStatus === 'stale') return '数据过期';
  if (snapshot.syncErrorCode === 'credential_unavailable') return '凭据未配置';
  if (snapshot.syncErrorCode === 'runtime_unavailable') return 'Runtime 不可达';
  if (snapshot.dataQualityState === 'unbound') return '暂未绑定账号';
  if (snapshot.dataQualityState === 'unavailable') return '账户不可用';
  return snapshot.dataQualityState || '数据待同步';
}

function pnlProfile(
  desk: AccountStrategyDesk,
  snapshot: StrategyAccountSnapshotResult | null,
): StrategyPnlProfile {
  const currency = snapshot?.balance?.currency || 'USDT';
  const pnl = snapshot?.pnl;
  const reason = unavailableReason(snapshot);
  return {
    title: `${labels[desk]}损益总览`,
    totalFund: money(snapshot?.balance?.equity, currency),
    period: snapshot?.asOf ? `截至 ${formatTime(snapshot.asOf)}` : reason,
    xLabels: [],
    dailyReturns: [],
    netValues: [],
    metrics: [
      {
        label: '已实现损益',
        value: signedMoney(pnl?.realizedPnl, currency),
        ratio: reason,
        tone: tone(pnl?.realizedPnl),
      },
      {
        label: '交易损益',
        value: signedMoney(pnl?.tradingPnl, currency),
        ratio: reason,
        tone: tone(pnl?.tradingPnl),
      },
      {
        label: '累计手续费',
        value: signedMoney(pnl?.fees, currency),
        ratio: reason,
        tone: tone(pnl?.fees),
      },
      {
        label: '账户净值',
        value: money(snapshot?.balance?.equity, currency),
        ratio: reason,
        tone: 'neutral',
      },
    ],
    attributions: [
      {
        label: '已实现损益',
        value: signedMoney(pnl?.realizedPnl, currency),
        ratio: reason,
        tone: tone(pnl?.realizedPnl),
      },
      {
        label: '交易损益',
        value: signedMoney(pnl?.tradingPnl, currency),
        ratio: reason,
        tone: tone(pnl?.tradingPnl),
      },
      {
        label: '交易手续费',
        value: signedMoney(pnl?.fees, currency),
        ratio: reason,
        tone: tone(pnl?.fees),
      },
    ],
    breakdownSeries: [
      { name: '已实现损益', color: '#3498db', data: [] },
      { name: '交易损益', color: '#55d6d9', data: [] },
      { name: '交易手续费', color: '#ee746f', data: [] },
    ],
    legSnapshots: [
      {
        title: snapshot?.accountCode || 'Bybit 账户',
        venue: 'Bybit',
        symbol: '--',
        rows: [
          {
            label: '账户权限',
            value:
              snapshot?.capability === 'trade_and_read'
                ? '可交易、可读取'
                : snapshot?.capability === 'read_only'
                ? '仅可读取'
                : '未绑定',
          },
          { label: '数据状态', value: reason },
          { label: '最后同步', value: formatTime(snapshot?.asOf) },
        ],
      },
    ],
    detailCurves: [
      {
        title: '已实现损益',
        value: signedMoney(pnl?.realizedPnl, currency),
        tone: tone(pnl?.realizedPnl),
        data: [],
      },
      {
        title: '交易损益',
        value: signedMoney(pnl?.tradingPnl, currency),
        tone: tone(pnl?.tradingPnl),
        data: [],
      },
      {
        title: '交易手续费',
        value: signedMoney(pnl?.fees, currency),
        tone: tone(pnl?.fees),
        data: [],
      },
    ],
  };
}

function capitalProfile(
  desk: AccountStrategyDesk,
  snapshot: StrategyAccountSnapshotResult | null,
): StrategyCapitalProfile {
  const currency = snapshot?.balance?.currency || 'USDT';
  const pnl = snapshot?.pnl;
  const reason = unavailableReason(snapshot);
  return {
    overview: [
      {
        label: '账户净值',
        value: money(snapshot?.balance?.equity, currency),
        note: snapshot?.accountCode || reason,
        tone: 'neutral',
      },
      {
        label: '可用资金',
        value: money(snapshot?.balance?.availableBalance, currency),
        note: reason,
        tone: 'neutral',
      },
      {
        label: '已实现损益',
        value: signedMoney(pnl?.realizedPnl, currency),
        note: reason,
        tone: tone(pnl?.realizedPnl),
      },
      {
        label: '交易损益',
        value: signedMoney(pnl?.tradingPnl, currency),
        note: reason,
        tone: tone(pnl?.tradingPnl),
      },
    ],
    riskCards: [
      {
        label: '账户数据状态',
        value: snapshot?.dataQualityState || '--',
        note: reason,
        tone: snapshot?.dataQualityState === 'unavailable' ? 'neutral' : 'positive',
      },
      {
        label: '账户能力',
        value:
          snapshot?.capability === 'trade_and_read'
            ? '可交易'
            : snapshot?.capability === 'read_only'
            ? '仅读取'
            : '未绑定',
        note: '读取权限向所有授权用户开放',
        tone: 'neutral',
      },
    ],
    structureCards: [
      { label: '账户', value: snapshot?.accountCode || '--', note: 'Bybit', tone: 'neutral' },
      { label: '最后同步', value: formatTime(snapshot?.asOf), note: reason, tone: 'neutral' },
    ],
    comparisonCards: [],
    metricCurves: [],
    curve: {
      title: `${labels[desk]}账户净值曲线`,
      subtitle: reason,
      metricOptions: [{ key: 'equity', label: '账户净值' }],
      periodOptions: [{ key: 'all', label: '全部' }],
      defaultMetric: 'equity',
      defaultPeriod: 'all',
      xLabels: [],
      netValueData: [],
      drawdownData: [],
      summaries: [
        { label: '账户净值', value: money(snapshot?.balance?.equity, currency), tone: 'neutral' },
        {
          label: '可用资金',
          value: money(snapshot?.balance?.availableBalance, currency),
          tone: 'neutral',
        },
      ],
    },
  };
}

function orderProfile(
  desk: AccountStrategyDesk,
  snapshot: StrategyAccountSnapshotResult | null,
): StrategyOrderProfile {
  const tables: Record<string, StrategyTableSection> = {
    positions: {
      columns: [
        { key: 'instrumentId', label: '标的' },
        { key: 'quantity', label: '净持仓' },
        { key: 'averagePrice', label: '均价' },
      ],
      rows: (snapshot?.positions || []).map((position) => ({
        instrumentId: position.instrumentId,
        quantity: position.netQuantity,
        averagePrice: position.averagePrice || '--',
      })),
    },
    orders: {
      columns: [
        { key: 'orderId', label: '订单ID' },
        { key: 'symbol', label: '标的' },
        { key: 'side', label: '方向' },
        { key: 'quantity', label: '数量' },
        { key: 'status', label: '状态' },
        { key: 'time', label: '时间' },
      ],
      rows: (snapshot?.orders || []).map((order) => ({
        orderId: order.orderId.slice(0, 12),
        symbol: order.symbol,
        side: order.side === 'buy' ? '买入' : '卖出',
        quantity: order.quantity,
        status: statusLabels[order.status] || order.status,
        time: formatTime(order.createdAt),
      })),
    },
    fills: {
      columns: [
        { key: 'fillId', label: '成交ID' },
        { key: 'instrumentId', label: '标的' },
        { key: 'side', label: '方向' },
        { key: 'quantity', label: '数量' },
        { key: 'price', label: '价格' },
        { key: 'time', label: '时间' },
      ],
      rows: (snapshot?.fills || []).map((fill) => ({
        fillId: fill.fillId.slice(0, 12),
        instrumentId: fill.instrumentId,
        side: fill.side === 'buy' ? '买入' : '卖出',
        quantity: fill.quantity,
        price: fill.price,
        time: formatTime(fill.occurredAt),
      })),
    },
  };
  return {
    label: `${labels[desk]}订单信息`,
    tabs: [
      { key: 'positions', label: '当前持仓' },
      { key: 'orders', label: '历史订单' },
      { key: 'fills', label: '成交记录' },
    ],
    tables,
  };
}

export function useStrategyAccountSnapshots() {
  const snapshots = ref<Partial<Record<AccountStrategyDesk, StrategyAccountSnapshotResult>>>({});

  async function refresh(desk?: StrategyDeskKey) {
    const keys =
      desk && accountDesk(desk) ? [desk] : (Object.keys(instanceIds) as AccountStrategyDesk[]);
    const results = await Promise.all(
      keys.map(async (key) => [key, await getStrategyAccountSnapshot(instanceIds[key])] as const),
    );
    snapshots.value = { ...snapshots.value, ...Object.fromEntries(results) };
  }

  return {
    refresh,
    pnlProfiles: computed(
      () =>
        Object.fromEntries(
          (Object.keys(instanceIds) as AccountStrategyDesk[]).map((desk) => [
            desk,
            pnlProfile(desk, snapshots.value[desk] || null),
          ]),
        ) as Record<AccountStrategyDesk, StrategyPnlProfile>,
    ),
    capitalProfiles: computed(
      () =>
        Object.fromEntries(
          (Object.keys(instanceIds) as AccountStrategyDesk[]).map((desk) => [
            desk,
            capitalProfile(desk, snapshots.value[desk] || null),
          ]),
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
