export type FundingExchange = 'Bybit' | 'Binance' | 'OKX';
export type FundingSymbol = 'BTC' | 'ETH' | 'SOL';
export type FundingRange = 'current' | 'week' | 'month';

export const fundingSampleMeta = Object.freeze({
  state: 'sample' as const,
  source: 'sample:funding-carry-research',
  asOf: '非实时 · 参考提交 bbdff039',
  actionable: false,
});

export const fundingRangeOptions: Array<{ value: FundingRange; label: string }> = [
  { value: 'current', label: '当前周期' },
  { value: 'week', label: '近7日' },
  { value: 'month', label: '近30日' },
];

export const fundingMarketRows = [
  { exchange: 'Bybit', symbol: 'BTC', rate: '+0.0100%', basis: '-0.14%', liquidity: '高' },
  { exchange: 'Binance', symbol: 'BTC', rate: '+0.0068%', basis: '-0.09%', liquidity: '高' },
  { exchange: 'OKX', symbol: 'BTC', rate: '-0.0112%', basis: '+0.12%', liquidity: '高' },
  { exchange: 'Bybit', symbol: 'ETH', rate: '+0.0081%', basis: '-0.08%', liquidity: '高' },
  { exchange: 'Binance', symbol: 'SOL', rate: '-0.0042%', basis: '+0.06%', liquidity: '中' },
];

export const fundingChartSeries = [
  { label: 'Bybit', values: [38, 44, 39, 55, 50, 63, 58, 69, 66] },
  { label: 'Binance', values: [31, 35, 38, 41, 39, 48, 46, 51, 54] },
  { label: 'OKX', values: [61, 56, 58, 49, 52, 42, 46, 36, 33] },
];

export const fundingResearch = {
  summary: [
    { label: '费率差', value: '0.021%', note: '8小时样例口径' },
    { label: '理论年化', value: '18.4%', note: '未扣成本，非收益承诺' },
    { label: '现货/永续基差', value: '-0.14%', note: '非实时样例' },
    { label: '风险等级', value: '中', note: '不可执行研究' },
  ],
  details: [
    { label: '建议结构', value: '买现货 / 卖永续' },
    { label: '资金费结算', value: '每8小时' },
    { label: '主要风险', value: '基差扩张、费率反转、流动性' },
    { label: '执行状态', value: 'Live Write 关闭' },
  ],
};

export const fundingOrderPreview = {
  strategyLabel: '资金费率套利组合',
  fields: [
    { label: '名义金额', value: '10,000 USDT' },
    { label: '开仓方式', value: '双腿同步限价' },
    { label: '最大滑点', value: '0.05%' },
  ],
  legs: [
    { leg: '现货', venue: 'Bybit', side: '买入', quantity: '0.16 BTC', status: '未提交' },
    { leg: '永续', venue: 'OKX', side: '卖出', quantity: '0.16 BTC', status: '未提交' },
  ],
};
