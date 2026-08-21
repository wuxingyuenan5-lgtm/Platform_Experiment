export const CROSS_SPREAD_RANGES = ['1m', '5m', '15m', '1h', '4h', '1D'] as const;

export const CROSS_SPREAD_ANALYSIS_PERIODS = ['1m', '5m', '15m', '1h'] as const;

export const CROSS_SPREAD_ANALYSIS_DATA_RANGES = ['500', '1000'] as const;

export const CROSS_SPREAD_TRADING_RULE_ROWS = [
  { label: '手续费', value: '—' },
  {
    label: '交易时间',
    value: 'XAUTUSDT：24H；XAUUSD：工作日23H，北京时间05-06（冬）/ 06-07（夏）维护',
  },
  { label: '个人最高杠杆', value: '—' },
  { label: '每日最大回撤', value: '—' },
  { label: '其他限制', value: '—' },
] as const;
