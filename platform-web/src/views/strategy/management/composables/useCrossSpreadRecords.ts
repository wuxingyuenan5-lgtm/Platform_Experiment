import { computed, ref } from 'vue';

import {
  getCrossSpreadObservability,
  type CrossSpreadObservabilityResult,
} from '@/api/platform/crossSpreadObservability';
import { getExecutionBatches, getFills, getOrders } from '@/api/platform/trading';
import type {
  ExecutionBatchResult,
  FillResult,
  OrderDetailResult,
} from '@/api/platform/trading.types';
import type { StrategyTableSection, StrategyTableTab } from '@/data/sample/strategy';

const CROSS_SPREAD_SYMBOLS = new Set(['XAUTUSDT', 'XAUUSD', 'XAUUSD.S']);
const CROSS_SPREAD_INSTRUMENT_IDS = new Set(['instrument_xau_usdt_perp', 'instrument_xau_usd']);

const statusLabelMap: Record<string, string> = {
  filled: '已成交',
  acknowledged: '已受理',
  pending: '待处理',
  executing: '执行中',
  rejected: '已拒绝',
  failed: '已失败',
  result_unknown: '结果未知',
  canceled: '已撤单',
  hedged: '已对冲',
  partially_executed: '部分成交',
  manual_intervention: '需人工介入',
};

function statusLabel(value: string | null | undefined): string {
  if (!value) return '--';
  return statusLabelMap[value] ?? value;
}

function batchDisplayStatus(batch: ExecutionBatchResult): string {
  if (
    batch.legs.some((leg) => leg.status === 'result_unknown') ||
    /result[_ ]unknown|result is unknown/i.test(batch.failureReason ?? '')
  ) {
    return 'result_unknown';
  }
  return batch.status;
}

function legStatusText(batch: ExecutionBatchResult): string {
  return (
    batch.legs
      .map((leg) => `${venueLabel(leg.accountId)}:${statusLabel(leg.status)}`)
      .join(' / ') || '--'
  );
}

function sideLabel(side: string | null | undefined): string {
  if (!side) return '--';
  const normalized = side.toLowerCase();
  if (normalized === 'buy') return '买入';
  if (normalized === 'sell') return '卖出';
  return side;
}

function directionLabel(direction: string | null | undefined): string {
  if (!direction) return '--';
  const map: Record<string, string> = {
    OPEN_LONG: '开多',
    OPEN_SHORT: '开空',
    CLOSE_LONG: '平多',
    CLOSE_SHORT: '平空',
    OPEN_LONG_SPREAD: '开多价差',
    OPEN_SHORT_SPREAD: '开空价差',
    CLOSE_LONG_SPREAD: '平多价差',
    CLOSE_SHORT_SPREAD: '平空价差',
  };
  return map[direction] ?? direction;
}

function venueLabel(accountId: string | null | undefined): string {
  if (!accountId) return '--';
  const normalized = accountId.toLowerCase();
  if (normalized.startsWith('bybit') || normalized.includes('crypto')) return 'Bybit';
  if (normalized.startsWith('mt5') || normalized.includes('mt5')) return 'MT5';
  return accountId;
}

function formatTime(value: string | null | undefined): string {
  if (!value) return '--';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString('zh-CN', { hour12: false });
}

function isCrossSpreadSymbol(symbol: string | null | undefined): boolean {
  return CROSS_SPREAD_SYMBOLS.has(String(symbol ?? '').toUpperCase());
}

function isCrossSpreadInstrument(instrumentId: string | null | undefined): boolean {
  return CROSS_SPREAD_INSTRUMENT_IDS.has(String(instrumentId ?? ''));
}

function instrumentIdFromSymbol(symbol: string | null | undefined): string {
  return String(symbol ?? '').toUpperCase() === 'XAUTUSDT'
    ? 'instrument_xau_usdt_perp'
    : 'instrument_xau_usd';
}

function mergeOrders(
  platformOrders: OrderDetailResult[],
  observability: CrossSpreadObservabilityResult,
  currentAccountIds: Set<string>,
) {
  const merged = new Map<string, OrderDetailResult>();
  for (const order of platformOrders) {
    merged.set(order.externalOrderId || order.orderId, order);
  }
  for (const venue of [observability.bybit, observability.mt5]) {
    for (const order of venue.recentOrders ?? []) {
      if (!currentAccountIds.has(order.accountId) || !isCrossSpreadSymbol(order.symbol)) continue;
      const key = String(
        order.externalOrderId ||
          order.platformOrderId ||
          `${order.accountId}:${order.symbol}:${order.asOf}`,
      );
      if (merged.has(key)) continue;
      merged.set(key, {
        orderId: String(order.platformOrderId || order.externalOrderId || key),
        commandId: String(order.platformOrderId || order.externalOrderId || key),
        status: order.status,
        externalOrderId: String(order.externalOrderId || ''),
        accountId: order.accountId,
        instrumentId: instrumentIdFromSymbol(order.symbol),
        symbol: order.symbol,
        side: order.side,
        orderType: order.orderType,
        quantity: String(order.quantity ?? '0'),
        price: order.price == null ? null : String(order.price),
        createdAt: order.asOf,
        updatedAt: order.asOf,
      });
    }
  }
  return [...merged.values()].sort(
    (left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime(),
  );
}

function mergeFills(
  platformFills: FillResult[],
  observability: CrossSpreadObservabilityResult,
  currentAccountIds: Set<string>,
) {
  const merged = new Map<string, FillResult>();
  for (const fill of platformFills) {
    const key = [
      fill.accountId,
      fill.instrumentId,
      fill.side,
      fill.quantity,
      fill.price,
      fill.occurredAt,
    ].join('|');
    merged.set(key, fill);
  }
  for (const venue of [observability.bybit, observability.mt5]) {
    for (const fill of venue.recentFills ?? []) {
      if (!currentAccountIds.has(fill.accountId) || !isCrossSpreadSymbol(fill.symbol)) continue;
      const instrumentId = instrumentIdFromSymbol(fill.symbol);
      const key = [
        fill.accountId,
        instrumentId,
        fill.side,
        String(fill.quantity ?? '0'),
        String(fill.price ?? '0'),
        fill.occurredAt,
      ].join('|');
      if (merged.has(key)) continue;
      merged.set(key, {
        fillId: String(fill.externalFillId || key),
        orderId: String(fill.externalOrderId || ''),
        accountId: fill.accountId,
        instrumentId,
        side: fill.side,
        quantity: String(fill.quantity ?? '0'),
        price: String(fill.price ?? '0'),
        occurredAt: fill.occurredAt,
      });
    }
  }
  return [...merged.values()].sort(
    (left, right) => new Date(right.occurredAt).getTime() - new Date(left.occurredAt).getTime(),
  );
}

function positionRows(
  venue: 'bybit' | 'mt5',
  positions: Array<{
    symbol: string;
    netQuantity: string | number | null | undefined;
    averagePrice?: string | number | null;
    unrealizedPnl?: string | number | null;
    positionStatus?: string | null;
  }>,
): Array<Record<string, string>> {
  return positions.map((position) => ({
    symbol: position.symbol || '--',
    venue: venue === 'bybit' ? 'Bybit' : 'MT5',
    side: parseFloat(String(position.netQuantity ?? '0')) < 0 ? '空头' : '多头',
    quantity: String(position.netQuantity ?? '--'),
    averagePrice: String(position.averagePrice ?? '--'),
    unrealizedPnl: String(position.unrealizedPnl ?? '--'),
    status: position.positionStatus === 'Normal' ? '正常' : position.positionStatus ?? '--',
  }));
}

const crossSpreadTabs: StrategyTableTab[] = [
  { key: 'positions', label: '当前持仓' },
  { key: 'history', label: '历史订单' },
  { key: 'fills', label: '成交记录' },
  { key: 'logs', label: '执行记录' },
];

export function useCrossSpreadRecords() {
  const loading = ref(false);
  const error = ref('');

  const orders = ref<OrderDetailResult[]>([]);
  const fills = ref<FillResult[]>([]);
  const batches = ref<ExecutionBatchResult[]>([]);
  const bybitPositions = ref<Array<Record<string, string>>>([]);
  const mt5Positions = ref<Array<Record<string, string>>>([]);

  const tables = computed<Record<string, StrategyTableSection>>(() => {
    const orderSymbolById = new Map(orders.value.map((order) => [order.orderId, order.symbol]));

    return {
      positions: {
        columns: [
          { key: 'symbol', label: '标的' },
          { key: 'venue', label: '场所' },
          { key: 'side', label: '方向' },
          { key: 'quantity', label: '数量' },
          { key: 'averagePrice', label: '均价' },
          { key: 'unrealizedPnl', label: '未实现盈亏' },
          { key: 'status', label: '状态' },
        ],
        rows: [...bybitPositions.value, ...mt5Positions.value],
      },
      history: {
        columns: [
          { key: 'orderId', label: '订单ID' },
          { key: 'symbol', label: '标的' },
          { key: 'venue', label: '场所' },
          { key: 'side', label: '方向' },
          { key: 'orderType', label: '类型' },
          { key: 'quantity', label: '数量' },
          { key: 'status', label: '状态' },
          { key: 'orderTime', label: '时间' },
        ],
        rows: orders.value.map((order) => ({
          orderId: String(order.orderId ?? '--').slice(0, 12),
          symbol: order.symbol ?? '--',
          venue: venueLabel(order.accountId),
          side: sideLabel(order.side),
          orderType: order.orderType === 'market' ? '市价' : order.orderType ?? '--',
          quantity: String(order.quantity ?? '--'),
          status: statusLabel(order.status),
          orderTime: formatTime(order.createdAt),
        })),
      },
      fills: {
        columns: [
          { key: 'fillId', label: '成交ID' },
          { key: 'symbol', label: '标的' },
          { key: 'side', label: '方向' },
          { key: 'quantity', label: '数量' },
          { key: 'price', label: '价格' },
          { key: 'fillTime', label: '时间' },
        ],
        rows: fills.value.map((fill) => ({
          fillId: String(fill.fillId ?? '--').slice(0, 12),
          symbol: orderSymbolById.get(fill.orderId) ?? fill.instrumentId ?? '--',
          side: sideLabel(fill.side),
          quantity: String(fill.quantity ?? '--'),
          price: String(fill.price ?? '--'),
          fillTime: formatTime(fill.occurredAt),
        })),
      },
      logs: {
        columns: [
          { key: 'batchId', label: '批次ID' },
          { key: 'direction', label: '方向' },
          { key: 'status', label: '状态' },
          { key: 'accountId', label: '账户' },
          { key: 'legStatus', label: '双腿状态' },
          { key: 'failureReason', label: '失败/未知原因' },
          { key: 'executionTime', label: '时间' },
        ],
        rows: batches.value.map((batch) => ({
          batchId: String(batch.batchId ?? '--').slice(0, 12),
          direction: directionLabel(batch.direction),
          status: statusLabel(batchDisplayStatus(batch)),
          accountId: venueLabel(batch.accountId),
          legStatus: legStatusText(batch),
          failureReason: batch.failureReason || '--',
          executionTime: formatTime(batch.createdAt),
        })),
      },
    };
  });

  async function refresh() {
    loading.value = true;
    error.value = '';
    try {
      const [orderRows, fillRows, batchRows, observability] = await Promise.all([
        getOrders(),
        getFills(),
        getExecutionBatches(),
        getCrossSpreadObservability(24, 50, 'audit'),
      ]);
      const currentAccountIds = new Set(
        [observability?.bybit?.accountId, observability?.mt5?.accountId].filter(
          (value): value is string => Boolean(value),
        ),
      );
      const selectedPlatformOrders = orderRows.filter(
        (order) =>
          currentAccountIds.has(order.accountId) &&
          (isCrossSpreadSymbol(order.symbol) || isCrossSpreadInstrument(order.instrumentId)),
      );
      const selectedPlatformFills = fillRows.filter(
        (fill) =>
          currentAccountIds.has(fill.accountId) && isCrossSpreadInstrument(fill.instrumentId),
      );
      orders.value = mergeOrders(selectedPlatformOrders, observability, currentAccountIds);
      fills.value = mergeFills(selectedPlatformFills, observability, currentAccountIds);
      batches.value = batchRows.filter(
        (batch) =>
          batch.strategyKey === 'cross_venue_spread' &&
          batch.legs.some((leg) => {
            const accountId = leg.accountId;
            return typeof accountId === 'string' && currentAccountIds.has(accountId);
          }),
      );
      bybitPositions.value = positionRows(
        'bybit',
        (observability?.bybit?.positions ?? []).filter(
          (position) => Math.abs(parseFloat(String(position.netQuantity ?? '0'))) > 0,
        ),
      );
      mt5Positions.value = positionRows(
        'mt5',
        (observability?.mt5?.positions ?? []).filter(
          (position) => Math.abs(parseFloat(String(position.netQuantity ?? '0'))) > 0,
        ),
      );
    } catch (caught: unknown) {
      error.value =
        typeof caught === 'object' && caught !== null
          ? (caught as { message?: string }).message ?? '订单数据加载失败'
          : '订单数据加载失败';
    } finally {
      loading.value = false;
    }
  }

  return {
    loading,
    error,
    tabs: crossSpreadTabs,
    tables,
    refresh,
  };
}

export type { StrategyTableSection, StrategyTableTab };
