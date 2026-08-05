export const dashboardSampleMeta = Object.freeze({
  state: 'sample' as const,
  source: 'sample:dashboard-restoration',
  asOf: '非实时 · 参考提交 bbdff039',
  actionable: false,
});

export const marketOverviewItems = [
  {
    label: '全球股票',
    color: '#d59b42',
    spark: '0,15 12,11 24,14 36,8 48,13 60,9 72,12 78,7',
  },
  {
    label: '大宗商品',
    color: '#6ca6ee',
    spark: '0,12 12,9 24,14 36,6 48,13 60,8 72,13 78,9',
  },
  {
    label: '美元指数',
    color: '#d59b42',
    spark: '0,13 12,10 24,12 36,9 48,13 60,10 72,12 78,9',
  },
  {
    label: '风险收益比',
    color: '#b6c0ca',
    spark: '0,12 12,10 24,11 36,8 48,10 60,9 72,10 78,8',
  },
];

export const pulseRows = [
  {
    title: 'AI + 生产力',
    path: '/hedge-board/us',
    color: '#d59b42',
    spark: '0,15 12,12 24,13 36,9 48,11 60,8 72,10 82,7',
    icon: 'database',
  },
  {
    title: 'Breakevens vs Gold',
    path: '/hedge-board/gold',
    color: '#6ca6ee',
    spark: '0,13 12,15 24,10 36,16 48,11 60,14 72,10 82,13',
    icon: 'projection',
  },
  {
    title: 'DXY vs US10Y',
    path: '/hedge-board/macro',
    color: '#b6c0ca',
    spark: '0,11 12,10 24,12 36,10 48,11 60,9 72,10 82,8',
    icon: 'line',
  },
];

export const allocationLegend = [
  { label: '权益类', color: '#dfc89e' },
  { label: '固收类', color: '#8fb2d8' },
  { label: '大宗商品', color: '#eee0c7' },
  { label: '加密资产', color: '#c9cdd3' },
  { label: '现金及其他', color: '#e9edf2' },
];

export const allocationStats = ['组合波动率（年化）', '最大回撤', '夏普比率', 'VaR（95%）'];

export const strategyRows = [
  {
    title: '宏观对冲策略',
    path: '/strategy/management',
    color: '#d59b42',
    spark: '0,15 12,11 24,14 36,9 48,13 60,8 72,12 82,9',
    icon: 'projection',
  },
  {
    title: '跨资产配置策略',
    path: '/strategy/management',
    color: '#6ca6ee',
    spark: '0,12 12,14 24,10 36,16 48,11 60,15 72,10 82,13',
    icon: 'cluster',
  },
  {
    title: '事件驱动策略',
    path: '/strategy/management',
    color: '#b6c0ca',
    spark: '0,10 12,11 24,9 36,11 48,10 60,9 72,10 82,9',
    icon: 'calendar',
  },
];

export const calendarRows = [
  { time: '09:30', region: '中国', title: '规模以上工业增加值' },
  { time: '17:00', region: '欧元区', title: 'CPI 终值（同比）' },
  { time: '20:30', region: '美国', title: '零售销售月率' },
  { time: '22:00', region: '美国', title: '密歇根大学消费者信心指数初值' },
];
