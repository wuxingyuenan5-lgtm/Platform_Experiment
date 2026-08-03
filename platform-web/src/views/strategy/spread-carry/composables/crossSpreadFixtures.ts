export const CROSS_SPREAD_RANGES = ['1m', '5m', '15m', '1h', '4h', '1D'] as const;

export const CROSS_SPREAD_ANALYSIS_PERIODS = ['1m', '5m', '15m', '1h'] as const;

export const CROSS_SPREAD_ANALYSIS_DATA_RANGES = ['500', '1000'] as const;

export const CROSS_SPREAD_TRADING_RULE_ROWS = [
  { label: '手续费', value: '—' },
  {
    label: '交易时间',
    value: 'XAUTUSDT.P：24H；XAUUSD+：工作日23H，北京时间05-06（冬）/ 06-07（夏）维护',
  },
  { label: '个人最高杠杆', value: '—' },
  { label: '每日最大回撤', value: '—' },
  { label: '其他限制', value: '—' },
] as const;

export const CROSS_SPREAD_DEFAULT_EXECUTION_LOGS = [
  {
    id: 'seed-1',
    time: '20:44:34',
    direction: '开多',
    type: '限价开仓',
    qty: '100.00',
    trigger: '-1.00',
    fill: '-1.10',
    status: '成功',
    channel: 'SPREAD_GOLD_001',
  },
  {
    id: 'seed-2',
    time: '15:45:23',
    direction: '开多',
    type: '市价开仓',
    qty: '100.00',
    trigger: '-1.80',
    fill: '-1.80',
    status: '成功',
    channel: 'SPREAD_GOLD_001',
  },
  {
    id: 'seed-3',
    time: '15:39:14',
    direction: '开空',
    type: '限价开仓',
    qty: '60.00',
    trigger: '-2.20',
    fill: '-2.24',
    status: '待确认',
    channel: 'MANUAL_DESK',
  },
] as const;
