import type { FillResult, OrderDetailResult } from '@/api/platform/trading.types';
import type { StrategyTableSection } from '@/data/sample/strategy';
import { fillOriginLabel, nativeAmount } from './strategyRecordPresentation';

const dateFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hourCycle: 'h23',
});

export function recordTime(value?: string | null) {
  if (!value || !Number.isFinite(Date.parse(value))) return '--';
  const parts = Object.fromEntries(
    dateFormatter.formatToParts(new Date(value)).map((p) => [p.type, p.value]),
  );
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
}

export function recordDate(row: Record<string, string>) {
  const value = row._timestamp
    ? recordTime(row._timestamp)
    : row.time || row.orderTime || row.fillTime || row.executionTime || row.date || '';
  return /^\d{4}-\d{2}-\d{2}/.test(value) ? value.slice(0, 10) : '';
}

export function recordMatches(
  row: Record<string, string>,
  filters: {
    startDate: string;
    endDate: string;
    action: string;
    status: string;
    venue: string;
    search: string;
  },
) {
  const day = recordDate(row);
  if ((filters.startDate || filters.endDate) && !day) return false;
  return (
    (!filters.startDate || day >= filters.startDate) &&
    (!filters.endDate || day <= filters.endDate) &&
    (!filters.action || row._action === filters.action) &&
    (!filters.status || row.status === filters.status) &&
    (!filters.venue || row.venue === filters.venue) &&
    (!filters.search ||
      Object.values(row).join(' ').toLowerCase().includes(filters.search.trim().toLowerCase()))
  );
}

export function recordVenue(account?: string | null) {
  return /mt5/i.test(account || '')
    ? 'MT5'
    : /bybit|crypto/i.test(account || '')
    ? 'Bybit'
    : account || '--';
}

export function recordAction(action?: string | null) {
  return (
    (
      { open: '开仓', close: '平仓', reverse: '反向开平', risk_reduction: '异常处理' } as Record<
        string,
        string
      >
    )[action || ''] || '开平待核对'
  );
}

const statuses: Record<string, string> = {
  filled: '已成交',
  acknowledged: '已受理',
  pending: '待处理',
  processing: '处理中',
  executing: '执行中',
  rejected: '已拒绝',
  failed: '失败',
  canceled: '已撤单',
  cancelled: '已撤单',
  result_unknown: '结果未知',
  partially_filled: '部分成交',
  partially_executed: '部分成交',
  manual_intervention: '需人工处理',
  completed: '已完成',
  hedged: '双腿已成交',
};
export const recordStatus = (value: string) => statuses[value] || value;
const sideText = (side: string) => (side === 'buy' ? '买入' : side === 'sell' ? '卖出' : side);
const field = (label: string, value?: string | null) => ({ label, value: value || '--' });

export function quantityWithUnit(quantity: string, symbol: string, account: string) {
  if (recordVenue(account) === 'MT5') return `${quantity} 手`;
  const unit = symbol.replace(/(USDT|USDC|USD)$/i, '');
  return `${quantity} ${unit === symbol ? '' : unit}`.trim();
}

function fillTime(fill: FillResult) {
  if (fill.timeQuality === 'source_clock_conflict')
    return {
      timestamp: fill.orderConfirmedAt || '',
      label: '订单确认时间',
      warning: '原始成交时间冲突',
    };
  if (fill.timeQuality === 'source_clock_unverified')
    return {
      timestamp: '',
      label: '成交时间待核对',
      warning: '原始时钟待核对',
    };
  return {
    timestamp: fill.occurredAt,
    label:
      fill.origin === 'runtime_confirmation'
        ? '订单确认时间'
        : fill.origin === 'legacy'
        ? '历史记录时间（来源待核对）'
        : '成交时间',
    warning: '',
  };
}

export function buildTradeRecords(orders: OrderDetailResult[], fills: FillResult[]) {
  const orderById = new Map(orders.map((o) => [o.orderId, o]));
  const orderDetails: NonNullable<StrategyTableSection['details']> = {};
  const fillDetails: NonNullable<StrategyTableSection['details']> = {};
  const orderRows = orders
    .map((order) => {
      const ownFills = fills.filter((f) => f.orderId === order.orderId);
      const timestamp = order.timeQuality === 'source_clock_unverified' ? '' : order.createdAt;
      const row = {
        _key: order.orderId,
        _timestamp: timestamp,
        _action: order.action || 'unknown',
        _search: [
          order.orderId,
          order.externalOrderId,
          order.commandId,
          order.instructionId,
          order.batchId,
        ].join(' '),
        action: recordAction(order.action),
        side: sideText(order.side),
        symbol: order.symbol,
        venue: recordVenue(order.accountId),
        quantity: quantityWithUnit(order.quantity, order.symbol, order.accountId),
        price: order.price || '市价',
        status: recordStatus(order.status),
        time: recordTime(timestamp),
        timeLabel:
          order.timeQuality === 'source_clock_unverified'
            ? '委托时间待核对'
            : order.timeQuality === 'venue_time'
            ? '场所委托时间'
            : '平台提交时间',
        timeWarning: order.timeQuality === 'source_clock_unverified' ? '原始时钟待核对' : '',
        orderId: order.orderId,
        instructionId: order.instructionId || '',
      };
      orderDetails[row._key] = {
        fields: [
          field('平台订单', order.orderId),
          field('交易所委托', order.externalOrderId),
          field('交易指令', order.instructionId),
          field('执行批次', order.batchId),
          field('账户', order.accountId),
          field('原指令方向', order.direction),
          field('只减仓', order.reduceOnly == null ? '--' : order.reduceOnly ? '是' : '否'),
          field('订单类型', order.orderType),
          field('原始委托时间（北京时间）', recordTime(order.createdAt)),
          field('原始时间字段', order.createdAt),
          field('已成交数量', order.filledQuantity),
          field('成交均价', order.averageFillPrice),
          field('拒绝原因', order.rejectReason),
          field('撤单原因', order.cancelReason),
          field('关联成交明细', String(ownFills.length)),
        ],
      };
      return row;
    })
    .sort((a, b) => (Date.parse(b._timestamp) || 0) - (Date.parse(a._timestamp) || 0));
  const fillRows = fills
    .map((fill) => {
      const order = orderById.get(fill.orderId);
      const clock = fillTime(fill);
      const action = fill.action || order?.action;
      const symbol = fill.symbol || order?.symbol || fill.instrumentId;
      const row = {
        _key: fill.fillId,
        _timestamp: clock.timestamp,
        _action: action || 'unknown',
        _search: [
          fill.fillId,
          fill.externalFillId,
          fill.orderId,
          fill.externalOrderId,
          fill.instructionId,
          fill.batchId,
        ].join(' '),
        action: recordAction(action),
        side: sideText(fill.side),
        symbol,
        venue: recordVenue(fill.accountId),
        quantity: quantityWithUnit(fill.quantity, symbol, fill.accountId),
        price: fill.price,
        fee: nativeAmount(fill.fee, fill.currency),
        time: recordTime(clock.timestamp),
        timeLabel: clock.label,
        timeWarning: clock.warning,
        fillId: fill.externalFillId || fill.fillId,
        orderId: fill.orderId,
        instructionId: fill.instructionId || '',
        origin: fillOriginLabel(fill.origin, fill.source),
      };
      fillDetails[row._key] = {
        fields: [
          field('成交编号', fill.externalFillId || fill.fillId),
          field('平台订单', fill.orderId),
          field('交易所委托', fill.externalOrderId),
          field('交易指令', fill.instructionId),
          field('执行批次', fill.batchId),
          field('账户', fill.accountId),
          field('记录来源', row.origin),
          field('原始成交时间（北京时间）', recordTime(fill.occurredAt)),
          field('原始时间字段', fill.occurredAt),
          field('平台订单确认时间（北京时间）', recordTime(fill.orderConfirmedAt)),
          field(
            '时间说明',
            clock.warning
              ? `${clock.warning}；订单确认只证明该订单成交已被平台确认，不代表逐笔成交时刻。`
              : clock.label,
          ),
        ],
      };
      return row;
    })
    .sort((a, b) => (Date.parse(b._timestamp) || 0) - (Date.parse(a._timestamp) || 0));
  const orderColumns = [
    { key: 'action', label: '开 / 平' },
    { key: 'symbol', label: '标的' },
    { key: 'venue', label: '场所' },
    { key: 'side', label: '买卖' },
    { key: 'quantity', label: '委托数量' },
    { key: 'price', label: '委托价' },
    { key: 'status', label: '订单状态' },
    { key: 'time', label: '提交时间 · 北京时间' },
  ];
  const fillColumns = [
    { key: 'action', label: '开 / 平' },
    { key: 'symbol', label: '标的' },
    { key: 'venue', label: '场所' },
    { key: 'side', label: '买卖' },
    { key: 'quantity', label: '成交数量' },
    { key: 'price', label: '成交价' },
    { key: 'fee', label: '原币手续费' },
    { key: 'time', label: '记录时间 · 北京时间' },
  ];
  const groups = new Map<string, { orders: typeof orderRows; fills: typeof fillRows }>();
  for (const order of orders) {
    const key = order.instructionId || order.batchId || order.orderId;
    const group = groups.get(key) || { orders: [], fills: [] };
    group.orders.push(orderRows.find((row) => row.orderId === order.orderId)!);
    groups.set(key, group);
  }
  for (const fill of fills) {
    const order = orderById.get(fill.orderId);
    const key =
      fill.instructionId || order?.instructionId || fill.batchId || order?.batchId || fill.orderId;
    const group = groups.get(key) || { orders: [], fills: [] };
    group.fills.push(fillRows.find((row) => row._key === fill.fillId)!);
    groups.set(key, group);
  }
  const activityDetails: NonNullable<StrategyTableSection['details']> = {};
  const activityRows = Array.from(groups, ([key, group]) => {
    const all = [...group.orders, ...group.fills];
    const actions = Array.from(new Set(all.map((row) => row._action)));
    const action = actions.length === 1 ? actions[0] : 'mixed';
    const timestamps = (group.orders.length ? group.orders : group.fills)
      .map((r) => r._timestamp)
      .filter(Boolean)
      .sort();
    const state = group.orders.some((r) => r.status === '结果未知')
      ? '结果未知'
      : group.orders.some((r) => ['已拒绝', '失败', '需人工处理'].includes(r.status))
      ? '有异常委托'
      : group.orders.length && group.orders.every((r) => r.status === '已成交')
      ? '委托均已成交'
      : group.orders.length
      ? Array.from(new Set(group.orders.map((r) => r.status))).join(' / ')
      : '仅成交明细';
    activityDetails[key] = {
      fields: [field('关联指令 / 批次 / 订单', key)],
      sections: [
        {
          title: '各腿委托',
          columns: [...orderColumns, { key: 'orderId', label: '平台订单' }],
          rows: group.orders,
        },
        {
          title: '各腿成交',
          columns: [
            ...fillColumns,
            { key: 'fillId', label: '成交编号' },
            { key: 'orderId', label: '平台订单' },
          ],
          rows: group.fills,
        },
      ],
    };
    return {
      _key: key,
      _timestamp: timestamps[0] || '',
      _action: action,
      _search: all.map((row) => row._search).join(' '),
      action: action === 'mixed' ? '多项操作' : recordAction(action),
      symbol: Array.from(new Set(all.map((r) => r.symbol))).join(' / '),
      venue: Array.from(new Set(all.map((r) => r.venue))).join(' + '),
      quantity: `${group.orders.length} 笔委托 · ${group.fills.length} 笔成交`,
      status: state,
      time: recordTime(timestamps[0]),
    };
  }).sort((a, b) => (Date.parse(b._timestamp) || 0) - (Date.parse(a._timestamp) || 0));
  return {
    activity: {
      columns: orderColumns
        .filter((c) => !['side', 'price'].includes(c.key))
        .map((c) => (c.key === 'quantity' ? { ...c, label: '执行明细' } : c)),
      rows: activityRows,
      details: activityDetails,
      description: '按关联交易指令汇总。展开查看各腿委托和成交；委托完成不代表当前仍有持仓。',
    },
    orders: {
      columns: orderColumns,
      rows: orderRows,
      details: orderDetails,
      description: '一行一笔委托。开平依据所属交易指令；没有可靠归属的历史记录保留待核对。',
    },
    fills: {
      columns: fillColumns,
      rows: fillRows,
      details: fillDetails,
      description:
        '一行一笔成交。时间异常时明确标注订单确认时间；原始成交时间和完整编号可在详情核对。',
    },
  } satisfies Record<string, StrategyTableSection>;
}
