import type { FillResult, OrderDetailResult } from '@/api/platform/trading.types';
import type { StrategyTableSection } from '@/data/sample/strategy';
import Decimal from 'decimal.js';
import { fillOriginLabel, nativeAmount } from './strategyRecordPresentation';

type EconomicEventRecord = {
  eventType: string;
  amount: string;
  currency: string;
  orderId?: string | null;
  instructionId?: string | null;
  batchId?: string | null;
};

type FinancialBreakdown = {
  realizedPnl: Map<string, Decimal>;
  fees: Map<string, Decimal>;
  fundingPnl: Map<string, Decimal>;
  swapPnl: Map<string, Decimal>;
};

const emptyFinancialBreakdown = (): FinancialBreakdown => ({
  realizedPnl: new Map(),
  fees: new Map(),
  fundingPnl: new Map(),
  swapPnl: new Map(),
});

function addFinancialAmount(
  target: Map<string, Decimal>,
  amount: string | null | undefined,
  currency: string | null | undefined,
  sign: 1 | -1 = 1,
) {
  if (amount == null || !currency) return;
  const key = currency.toUpperCase();
  const value = new Decimal(amount).mul(sign);
  target.set(key, (target.get(key) || new Decimal(0)).plus(value));
}

function formatFinancialAmounts(values: Map<string, Decimal>): string {
  return (
    Array.from(values.entries())
      .map(([currency, amount]) => `${amount.toFixed()} ${currency}`)
      .join(' / ') || '--'
  );
}

function addBreakdown(target: FinancialBreakdown, source: FinancialBreakdown) {
  (Object.keys(target) as Array<keyof FinancialBreakdown>).forEach((field) => {
    source[field].forEach((amount, currency) => {
      target[field].set(currency, (target[field].get(currency) || new Decimal(0)).plus(amount));
    });
  });
}

function netFinancialAmounts(breakdown: FinancialBreakdown): string {
  const currencies = new Set([
    ...breakdown.realizedPnl.keys(),
    ...breakdown.fees.keys(),
    ...breakdown.fundingPnl.keys(),
    ...breakdown.swapPnl.keys(),
  ]);
  if (!currencies.size) return '--';
  const net = new Map<string, Decimal>();
  currencies.forEach((currency) => {
    const value = (breakdown.realizedPnl.get(currency) || new Decimal(0))
      .minus(breakdown.fees.get(currency) || new Decimal(0))
      .plus(breakdown.fundingPnl.get(currency) || new Decimal(0))
      .plus(breakdown.swapPnl.get(currency) || new Decimal(0));
    net.set(currency, value);
  });
  return formatFinancialAmounts(net);
}

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

export function buildTradeRecords(
  orders: OrderDetailResult[],
  fills: FillResult[],
  economicEvents: EconomicEventRecord[] = [],
) {
  const orderById = new Map(orders.map((o) => [o.orderId, o]));
  const fillsByOrder = new Map<string, FillResult[]>();
  fills.forEach((fill) => {
    const rows = fillsByOrder.get(fill.orderId) || [];
    rows.push(fill);
    fillsByOrder.set(fill.orderId, rows);
  });

  function financialBreakdownForOrder(order: OrderDetailResult): FinancialBreakdown {
    const breakdown = emptyFinancialBreakdown();
    const ownFills = fillsByOrder.get(order.orderId) || [];
    const fillHasFee = ownFills.some((fill) => fill.fee != null);
    const fillHasSwap = ownFills.some((fill) => fill.swap != null);
    const fillHasRealizedPnl = ownFills.some((fill) => fill.realizedPnl != null);
    ownFills.forEach((fill) => {
      addFinancialAmount(breakdown.realizedPnl, fill.realizedPnl, fill.currency);
      addFinancialAmount(breakdown.fees, fill.fee, fill.currency);
      addFinancialAmount(breakdown.swapPnl, fill.swap, fill.currency);
    });
    economicEvents.forEach((event) => {
      const belongsToOrder =
        event.orderId === order.orderId ||
        (!event.orderId &&
          ((event.instructionId && event.instructionId === order.instructionId) ||
            (event.batchId && event.batchId === order.batchId)));
      if (!belongsToOrder) return;
      if (event.eventType === 'fee' && fillHasFee) return;
      if (event.eventType === 'swap' && fillHasSwap) return;
      if (event.eventType === 'realized_pnl' && fillHasRealizedPnl) return;
      if (event.eventType === 'fee')
        // Financial readmodel stores fee events as negative cash movement;
        // display the positive cost and subtract it once from net PnL.
        addFinancialAmount(breakdown.fees, event.amount, event.currency, -1);
      if (event.eventType === 'funding')
        addFinancialAmount(breakdown.fundingPnl, event.amount, event.currency);
      if (event.eventType === 'swap')
        addFinancialAmount(breakdown.swapPnl, event.amount, event.currency);
      if (event.eventType === 'realized_pnl')
        addFinancialAmount(breakdown.realizedPnl, event.amount, event.currency);
    });
    return breakdown;
  }

  const financialByOrder = new Map<string, FinancialBreakdown>();
  orders.forEach((order) => financialByOrder.set(order.orderId, financialBreakdownForOrder(order)));
  const orderDetails: NonNullable<StrategyTableSection['details']> = {};
  const fillDetails: NonNullable<StrategyTableSection['details']> = {};
  const orderRows = orders
    .map((order) => {
      const ownFills = fills.filter((f) => f.orderId === order.orderId);
      const breakdown = financialByOrder.get(order.orderId) || emptyFinancialBreakdown();
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
        realizedPnl: formatFinancialAmounts(breakdown.realizedPnl),
        costs:
          [
            breakdown.fees.size ? `手续费 ${formatFinancialAmounts(breakdown.fees)}` : '',
            breakdown.fundingPnl.size
              ? `资金费 ${formatFinancialAmounts(breakdown.fundingPnl)}`
              : '',
            breakdown.swapPnl.size ? `库存费 ${formatFinancialAmounts(breakdown.swapPnl)}` : '',
          ]
            .filter(Boolean)
            .join(' · ') || '--',
        netPnl: netFinancialAmounts(breakdown),
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
          field('已实现盈亏', formatFinancialAmounts(breakdown.realizedPnl)),
          field('手续费', formatFinancialAmounts(breakdown.fees)),
          field('资金费', formatFinancialAmounts(breakdown.fundingPnl)),
          field('库存费', formatFinancialAmounts(breakdown.swapPnl)),
          field('已实现净额', netFinancialAmounts(breakdown)),
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
        realizedPnl: nativeAmount(fill.realizedPnl, fill.currency),
        swap: nativeAmount(fill.swap, fill.currency),
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
          field('已实现盈亏', nativeAmount(fill.realizedPnl, fill.currency)),
          field('库存费', nativeAmount(fill.swap, fill.currency)),
          field('手续费', nativeAmount(fill.fee, fill.currency)),
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
    { key: 'realizedPnl', label: '已实现盈亏' },
    { key: 'costs', label: '手续费 / 资金费 / 库存费' },
    { key: 'netPnl', label: '已实现净额' },
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
    { key: 'realizedPnl', label: '已实现盈亏' },
    { key: 'swap', label: '库存费' },
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
  const formatHoldingTime = (milliseconds: number, active = false) => {
    const totalMinutes = Math.max(0, Math.floor(milliseconds / 60_000));
    const days = Math.floor(totalMinutes / (24 * 60));
    const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
    const minutes = totalMinutes % 60;
    const body = days
      ? `${days}天${hours}小时`
      : hours
      ? `${hours}小时${minutes}分`
      : `${minutes}分钟`;
    return active ? `持仓中 ${body}` : body;
  };
  const groupEntries = Array.from(groups.entries()).sort(([, left], [, right]) => {
    const leftTime = Date.parse(
      (left.orders[0]?._timestamp || left.fills[0]?._timestamp || '') as string,
    );
    const rightTime = Date.parse(
      (right.orders[0]?._timestamp || right.fills[0]?._timestamp || '') as string,
    );
    return (leftTime || 0) - (rightTime || 0);
  });
  const openQueues = new Map<string, Array<{ key: string; at: number }>>();
  const holdingByGroup = new Map<string, string>();
  for (const [key, group] of groupEntries) {
    const sourceOrders = group.orders
      .map((row) => orderById.get(row.orderId))
      .filter((row): row is OrderDetailResult => Boolean(row));
    const action = Array.from(new Set(sourceOrders.map((row) => row.action).filter(Boolean)));
    if (action.length !== 1) continue;
    const groupAction = action[0];
    const at = Date.parse(
      (group.orders[0]?._timestamp || group.fills[0]?._timestamp || '') as string,
    );
    if (!Number.isFinite(at)) continue;
    const validOrders = sourceOrders.filter(
      (row) => !['rejected', 'failed', 'canceled', 'cancelled'].includes(row.status),
    );
    if (!validOrders.length) continue;
    const positionKeys = new Set(validOrders.map((row) => `${row.accountId}@@${row.instrumentId}`));
    if (groupAction === 'open') {
      positionKeys.forEach((positionKey) => {
        const queue = openQueues.get(positionKey) || [];
        queue.push({ key, at });
        openQueues.set(positionKey, queue);
      });
      holdingByGroup.set(key, formatHoldingTime(Date.now() - at, true));
    } else if (groupAction === 'close') {
      const durations: number[] = [];
      positionKeys.forEach((positionKey) => {
        const queue = openQueues.get(positionKey) || [];
        const open = queue.shift();
        if (open) durations.push(Math.max(0, at - open.at));
        openQueues.set(positionKey, queue);
      });
      if (durations.length) {
        const min = Math.min(...durations);
        const max = Math.max(...durations);
        holdingByGroup.set(
          key,
          min === max
            ? formatHoldingTime(min)
            : `${formatHoldingTime(min)} - ${formatHoldingTime(max)}`,
        );
      }
    }
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
    const groupFinancials = emptyFinancialBreakdown();
    group.orders.forEach((row) => {
      const breakdown = financialByOrder.get(row.orderId);
      if (breakdown) addBreakdown(groupFinancials, breakdown);
    });
    activityDetails[key] = {
      fields: [
        field('关联指令 / 批次 / 订单', key),
        field('已实现盈亏', formatFinancialAmounts(groupFinancials.realizedPnl)),
        field('手续费', formatFinancialAmounts(groupFinancials.fees)),
        field('资金费', formatFinancialAmounts(groupFinancials.fundingPnl)),
        field('库存费', formatFinancialAmounts(groupFinancials.swapPnl)),
        field('已实现净额', netFinancialAmounts(groupFinancials)),
        field('持仓时间', holdingByGroup.get(key)),
      ],
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
      realizedPnl: formatFinancialAmounts(groupFinancials.realizedPnl),
      costs:
        [
          groupFinancials.fees.size ? `手续费 ${formatFinancialAmounts(groupFinancials.fees)}` : '',
          groupFinancials.fundingPnl.size
            ? `资金费 ${formatFinancialAmounts(groupFinancials.fundingPnl)}`
            : '',
          groupFinancials.swapPnl.size
            ? `库存费 ${formatFinancialAmounts(groupFinancials.swapPnl)}`
            : '',
        ]
          .filter(Boolean)
          .join(' · ') || '--',
      netPnl: netFinancialAmounts(groupFinancials),
      holdingTime: holdingByGroup.get(key) || '--',
      time: recordTime(timestamps[0]),
    };
  }).sort((a, b) => (Date.parse(b._timestamp) || 0) - (Date.parse(a._timestamp) || 0));
  return {
    activity: {
      columns: [
        ...orderColumns
          .filter((c) => !['side', 'price'].includes(c.key))
          .map((c) => (c.key === 'quantity' ? { ...c, label: '执行明细' } : c)),
        { key: 'holdingTime', label: '持仓时间' },
      ],
      rows: activityRows,
      details: activityDetails,
      description: '按关联交易指令汇总。展开查看各腿委托和成交；委托完成不代表当前仍有持仓。',
    },
    orders: {
      columns: orderColumns,
      rows: orderRows,
      details: orderDetails,
      description:
        '一行一笔委托。盈亏、手续费、资金费和库存费按已载入的原生成交与结算流水归属；缺少原币或归属时显示待核对。',
    },
    fills: {
      columns: fillColumns,
      rows: fillRows,
      details: fillDetails,
      description:
        '一行一笔成交。原币手续费、已实现盈亏和库存费来自原生成交；时间异常时明确标注订单确认时间。',
    },
  } satisfies Record<string, StrategyTableSection>;
}
