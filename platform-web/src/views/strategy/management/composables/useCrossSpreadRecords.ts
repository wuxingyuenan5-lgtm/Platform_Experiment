import { buildTradeRecords, recordTime } from './strategyTradeRecords';
import { computed, ref } from 'vue';
import { nativeAmount, settlementLabel } from './strategyRecordPresentation';

import { getCrossSpreadSnapshot } from '@/api/platform/trading';
import { getExecutionBatches, getFills, getOrders, getStrategyPnl } from '@/api/platform/trading';
import type {
  ExecutionBatchResult,
  FillResult,
  OrderDetailResult,
  StrategyPnlResult,
  CrossSpreadPositionOverviewResult,
} from '@/api/platform/trading.types';
import type { StrategyTableSection, StrategyTableTab } from '@/data/sample/strategy';

const STRATEGY_INSTANCE_ID = 'strategy_cross_venue_spread_instance_default';

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

const formatTime = recordTime;

const crossSpreadTabs: StrategyTableTab[] = [
  { key: 'positions', label: '当前持仓' },
  { key: 'activity', label: '开平记录' },
  { key: 'fills', label: '逐笔成交' },
  { key: 'history', label: '委托明细' },
  { key: 'logs', label: '执行记录' },
  { key: 'settlements', label: '原币结算流水' },
];

export function useCrossSpreadRecords() {
  const loading = ref(false);
  const error = ref('');
  const abnormalOrders = ref<CrossSpreadPositionOverviewResult['abnormalOrders']>([]);

  const orders = ref<OrderDetailResult[]>([]);
  const fills = ref<FillResult[]>([]);
  const batches = ref<ExecutionBatchResult[]>([]);
  const finance = ref<StrategyPnlResult | null>(null);
  const bybitPositions = ref<Array<Record<string, string>>>([]);
  const mt5Positions = ref<Array<Record<string, string>>>([]);

  const tables = computed<Record<string, StrategyTableSection>>(() => {
    const records = buildTradeRecords(orders.value, fills.value);

    return {
      positions: {
        columns: [
          { key: 'symbol', label: '标的' },
          { key: 'planId', label: '组合' },
          { key: 'ticket', label: 'MT5 Ticket' },
          { key: 'venue', label: '场所' },
          { key: 'side', label: '方向' },
          { key: 'quantity', label: '数量' },
          { key: 'averagePrice', label: '均价' },
          { key: 'unrealizedPnl', label: '未实现盈亏（USDT）' },
          { key: 'status', label: '状态' },
        ],
        rows: [...bybitPositions.value, ...mt5Positions.value],
      },
      activity: records.activity,
      history: records.orders,
      fills: records.fills,
      settlements: {
        columns: [
          { key: 'eventId', label: '流水ID' },
          { key: 'orderId', label: '订单ID' },
          { key: 'instructionId', label: '指令ID' },
          { key: 'kind', label: '类型' },
          { key: 'symbol', label: '标的' },
          { key: 'amount', label: '原币收支' },
          { key: 'source', label: '来源' },
          { key: 'time', label: '时间' },
        ],
        rows: (finance.value?.economicEvents ?? []).map((event) => ({
          eventId: event.externalEventId,
          orderId: event.orderId || '--',
          instructionId: event.instructionId || '--',
          kind: settlementLabel(event.eventType),
          symbol: event.symbol || '--',
          amount: nativeAmount(event.amount, event.currency),
          source: event.source || '--',
          time: formatTime(event.occurredAt),
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
          batchId: String(batch.batchId ?? '--'),
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
      const [orderRows, fillRows, batchRows, snapshot, financials] = await Promise.all([
        getOrders(STRATEGY_INSTANCE_ID),
        getFills(STRATEGY_INSTANCE_ID),
        getExecutionBatches(STRATEGY_INSTANCE_ID),
        getCrossSpreadSnapshot(),
        getStrategyPnl(STRATEGY_INSTANCE_ID),
      ]);
      orders.value = orderRows;
      fills.value = fillRows;
      batches.value = batchRows.filter((batch) => batch.strategyKey === 'cross_venue_spread');
      finance.value = financials;
      const overview = snapshot.positionOverview;
      abnormalOrders.value = overview?.abnormalOrders ?? [];
      const abnormal = new Set((overview?.abnormalOrders ?? []).map((row) => row.planId));
      const groups = (overview?.groups ?? []).filter((row) => !abnormal.has(row.planId));
      const rows = (venue: 'bybit' | 'mt5') =>
        groups.map((row) => ({
          symbol: venue === 'bybit' ? snapshot.bybit.symbol : snapshot.mt5.symbol,
          venue: venue === 'bybit' ? 'Bybit' : 'MT5',
          side: (row.direction === 'LONG_SPREAD') === (venue === 'bybit') ? '多头' : '空头',
          quantity: String((venue === 'bybit' ? row.bybitQuantity : row.mt5Quantity) ?? '--'),
          averagePrice: String(
            (venue === 'bybit' ? row.bybitEntryPrice : row.mt5EntryPrice) ?? '--',
          ),
          unrealizedPnl: String((venue === 'bybit' ? row.bybitPnlUsdt : row.mt5PnlUsdt) ?? '--'),
          status: row.reason || '正常',
          planId: row.planId,
          ticket: venue === 'mt5' ? row.mt5PositionId || '--' : '--',
        }));
      bybitPositions.value = rows('bybit');
      mt5Positions.value = rows('mt5');
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
    abnormalOrders,
    tabs: crossSpreadTabs,
    tables,
    refresh,
  };
}

export type { StrategyTableSection, StrategyTableTab };
