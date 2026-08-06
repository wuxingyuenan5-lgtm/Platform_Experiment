export const spreadSampleMeta = Object.freeze({
  state: 'sample' as const,
  source: 'sample:spread-research',
  asOf: '非实时 · 参考提交 bbdff039',
  actionable: false,
});

export const spreadOverview = [
  { label: '做多价差', value: '+18.42', note: '主腿 Ask - 对冲腿 Bid' },
  { label: '做空价差', value: '+17.96', note: '主腿 Bid - 对冲腿 Ask' },
  { label: 'USDT/USD', value: '1.0008', note: '样例换算因子' },
  { label: '资金费库存', value: '+0.010%', note: '非实时' },
];

export const spreadChartDates = [
  '03-17',
  '03-18',
  '03-19',
  '03-20',
  '03-21',
  '03-22',
  '03-24',
  '03-26',
  '03-28',
  '03-30',
  '04-01',
  '04-03',
  '04-05',
  '04-07',
  '04-09',
  '04-11',
  '04-13',
  '04-15',
];
export const spreadSeries = [
  18.2, 17.9, 16.8, 14.4, 12.2, 10.9, 8.1, 7.4, 8.6, 10.3, 12.5, 14.8, 16.7, 18.1, 19.4, 18.8, 18.1,
  17.3,
];
export const goldPriceSeries = [
  2331, 2334, 2338, 2329, 2321, 2318, 2306, 2301, 2305, 2316, 2328, 2340, 2352, 2359, 2362, 2361,
  2358, 2354,
];

export const spreadDecomposition = [
  { label: '价差变动总损益', value: '--' },
  { label: '合约溢价贡献', value: '+6.18' },
  { label: '稳定币换汇贡献', value: '+1.87' },
  { label: '场所报价差贡献', value: '+9.96' },
  { label: '累计资金费', value: '--' },
  { label: '累计手续费', value: '--' },
  { label: '滑点成本', value: '-0.42（单独披露）' },
];

export const spreadScenarios = [
  {
    title: '价差扩张',
    body: '主腿相对对冲腿继续走强，观察资金费与库存是否同步恶化。',
    result: '研究阈值：+20.00',
  },
  {
    title: '均值回归',
    body: '价差回到中轴，检查两腿流动性和成交确认是否完整。',
    result: '研究阈值：+14.50',
  },
  {
    title: '结果不确定',
    body: '任一场所查询不可用时保持 fail-closed，不把 ACK 当作 Fill。',
    result: '状态：result_unknown',
  },
];
