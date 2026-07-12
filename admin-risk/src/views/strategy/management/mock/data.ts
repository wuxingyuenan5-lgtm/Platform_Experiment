import type { StrategyDeskKey, StrategyDeskProfile, StrategyOverviewPeriodData } from '../types';

export const strategyDeskOrder: StrategyDeskKey[] = ['funding', 'crossSpread', 'domesticOverseas', 'dip', 'shortLineTraderL'];

function makeOverviewDataset(base: Partial<StrategyOverviewPeriodData> & Pick<StrategyOverviewPeriodData, 'periodLabel' | 'dateLabel' | 'totalFund' | 'xLabels' | 'barValues' | 'lineValues' | 'statCards' | 'stateCounts' | 'profitRows' | 'lossRows' | 'syncRows'>): StrategyOverviewPeriodData {
  return base;
}

const fundingOverview = {
  periods: [
    { key: 'day', label: '日报' },
    { key: 'week', label: '周报' },
    { key: 'month', label: '月报' },
    { key: 'custom', label: '自定义' },
  ] as const,
  datasets: {
    day: makeOverviewDataset({
      periodLabel: '2026年06月25日',
      dateLabel: '2026-06-25 00:00 - 2026-06-25 23:59',
      totalFund: '2,984,316.97 USD',
      xLabels: ['00','01','02','03','04','05','06','07','08','09','10','11','12','13'],
      barValues: [18,12,-8,22,30,16,10,36,44,32,28,20,14,12],
      lineValues: [2,4,5,8,10,12,14,20,24,26,28,31,34,36],
      statCards: [
        { label: '净收益', value: '+68.42', subValue: '当日资金费率', tone: 'positive' },
        { label: '盈利', value: '+82.10', subValue: '已实现 + 浮动', tone: 'positive' },
        { label: '亏损', value: '-13.68', subValue: '执行损耗', tone: 'negative' },
        { label: '收益率', value: '+0.23%', subValue: '当日年化 18.7%', tone: 'positive' },
        { label: '手续费', value: '-5.22', subValue: '交易额 102K', tone: 'negative' },
        { label: '费率收入', value: '+73.64', subValue: '交易覆盖 100%', tone: 'positive' },
      ],
      stateCounts: [
        { label: '启动策略', count: '2', subLabel: '总计' },
        { label: '结束策略', count: '1', subLabel: '总计' },
        { label: '延续策略', count: '5', subLabel: '总计' },
      ],
      profitRows: [
        { type: 'BTC 费率套利', strategyCount: '2', pnl: '+44.32', ratio: '60.2%', tone: 'positive' },
        { type: 'ETH 费率套利', strategyCount: '2', pnl: '+21.58', ratio: '29.3%', tone: 'positive' },
        { type: 'XRP / DOGE', strategyCount: '1', pnl: '+7.74', ratio: '10.5%', tone: 'positive' },
      ],
      lossRows: [
        { type: '执行滑点', strategyCount: '1', pnl: '-8.42', ratio: '61.5%', tone: 'negative' },
        { type: '借贷成本', strategyCount: '1', pnl: '-5.26', ratio: '38.5%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '资金腿与合约腿仓位均已回写。', time: '11:18:24', tone: 'positive' },
        { category: '费率同步', status: '已完成', message: 'Binance / OKX / Bybit 最新费率已入板。', time: '11:18:09', tone: 'positive' },
        { category: '风控检查', status: '监控中', message: 'ETH 单腿延迟仍在监控阈值内。', time: '11:17:41', tone: 'neutral' },
      ],
    }),
    week: makeOverviewDataset({
      periodLabel: '2026 第26周',
      dateLabel: '2026-06-19 - 2026-06-25',
      totalFund: '2,984,316.97 USD',
      xLabels: ['06-19','06-20','06-21','06-22','06-23','06-24','06-25'],
      barValues: [92,14,218,146,214,-34,-252],
      lineValues: [18,26,45,58,74,92,118],
      statCards: [
        { label: '净收益', value: '+267.94', subValue: '周度总收益', tone: 'positive' },
        { label: '盈利', value: '+300.16', subValue: '正收益策略累计', tone: 'positive' },
        { label: '亏损', value: '-32.22', subValue: '亏损策略累计', tone: 'negative' },
        { label: '收益率', value: '+0.38%', subValue: '年化 +27.94%', tone: 'positive' },
        { label: '手续费', value: '-15.22', subValue: '交易额 63.3K', tone: 'negative' },
        { label: '费率收入', value: '+330.49', subValue: '交易覆盖 100%', tone: 'positive' },
      ],
      stateCounts: [
        { label: '启动策略', count: '5', subLabel: '总计' },
        { label: '结束策略', count: '6', subLabel: '总计' },
        { label: '延续策略', count: '13', subLabel: '总计' },
      ],
      profitRows: [
        { type: '费率套利', strategyCount: '13', pnl: '+285.69', ratio: '95.2%', tone: 'positive' },
        { type: '跨所套利', strategyCount: '3', pnl: '+14.47', ratio: '4.8%', tone: 'positive' },
      ],
      lossRows: [
        { type: '跨所套利', strategyCount: '1', pnl: '-32.22', ratio: '100.0%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '资金腿与合约腿仓位均已回写。', time: '11:18:24', tone: 'positive' },
        { category: '费率同步', status: '已完成', message: 'Binance / OKX / Bybit 最新费率已入板。', time: '11:18:09', tone: 'positive' },
        { category: '风控检查', status: '监控中', message: 'ETH 单腿延迟仍在监控阈值内。', time: '11:17:41', tone: 'neutral' },
      ],
    }),
    month: makeOverviewDataset({
      periodLabel: '2026年06月',
      dateLabel: '2026-06-01 - 2026-06-25',
      totalFund: '2,984,316.97 USD',
      xLabels: ['01','03','05','07','09','11','13','15','17','19','21','23','25'],
      barValues: [120,86,144,182,206,140,-52,94,168,196,244,208,126],
      lineValues: [8,10,12,15,17,22,25,28,32,35,39,44,48],
      statCards: [
        { label: '净收益', value: '+1,186.42', subValue: '月度总收益', tone: 'positive' },
        { label: '盈利', value: '+1,344.18', subValue: '正收益策略累计', tone: 'positive' },
        { label: '亏损', value: '-157.76', subValue: '亏损策略累计', tone: 'negative' },
        { label: '收益率', value: '+1.92%', subValue: '年化 +23.10%', tone: 'positive' },
        { label: '手续费', value: '-78.64', subValue: '交易额 514K', tone: 'negative' },
        { label: '费率收入', value: '+1,268.30', subValue: '交易覆盖 96.4%', tone: 'positive' },
      ],
      stateCounts: [
        { label: '启动策略', count: '16', subLabel: '总计' },
        { label: '结束策略', count: '13', subLabel: '总计' },
        { label: '延续策略', count: '27', subLabel: '总计' },
      ],
      profitRows: [
        { type: 'BTC / ETH 主策略', strategyCount: '18', pnl: '+986.20', ratio: '77.8%', tone: 'positive' },
        { type: '长尾币费率', strategyCount: '9', pnl: '+282.10', ratio: '22.2%', tone: 'positive' },
      ],
      lossRows: [
        { type: '执行归因', strategyCount: '4', pnl: '-92.16', ratio: '58.4%', tone: 'negative' },
        { type: '借贷成本', strategyCount: '2', pnl: '-65.60', ratio: '41.6%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '月度仓位与结算历史已合并。', time: '11:18:24', tone: 'positive' },
        { category: '费率同步', status: '已完成', message: '月度费率曲线已重新计算。', time: '11:18:09', tone: 'positive' },
        { category: '风控检查', status: '复核中', message: '个别长尾币杠杆占用偏高，待复核。', time: '11:17:41', tone: 'negative' },
      ],
    }),
    custom: makeOverviewDataset({
      periodLabel: '自定义窗口',
      dateLabel: '2026-06-09 - 2026-06-25',
      totalFund: '2,984,316.97 USD',
      xLabels: ['09','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25'],
      barValues: [88,6,222,148,216,58,-26,-248,60,194,152,162,168,178,392,182,176],
      lineValues: [4,5,7,9,12,14,16,15,18,21,24,27,29,32,34,37,40],
      statCards: [
        { label: '净收益', value: '+742.31', subValue: '自定义窗口', tone: 'positive' },
        { label: '盈利', value: '+813.56', subValue: '正收益策略累计', tone: 'positive' },
        { label: '亏损', value: '-71.25', subValue: '亏损策略累计', tone: 'negative' },
        { label: '收益率', value: '+0.88%', subValue: '窗口收益率', tone: 'positive' },
        { label: '手续费', value: '-42.18', subValue: '交易额 261K', tone: 'negative' },
        { label: '费率收入', value: '+784.24', subValue: '交易覆盖 98.2%', tone: 'positive' },
      ],
      stateCounts: [
        { label: '启动策略', count: '8', subLabel: '总计' },
        { label: '结束策略', count: '7', subLabel: '总计' },
        { label: '延续策略', count: '14', subLabel: '总计' },
      ],
      profitRows: [
        { type: '主策略', strategyCount: '9', pnl: '+690.52', ratio: '88.0%', tone: 'positive' },
        { type: '长尾补充', strategyCount: '5', pnl: '+93.72', ratio: '12.0%', tone: 'positive' },
      ],
      lossRows: [
        { type: '滑点 / 手续费', strategyCount: '3', pnl: '-71.25', ratio: '100%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '自定义窗口内持仓变动已对齐。', time: '11:18:24', tone: 'positive' },
        { category: '费率同步', status: '已完成', message: '自定义窗口费率快照已同步。', time: '11:18:09', tone: 'positive' },
        { category: '风控检查', status: '监控中', message: '窗口内无新增超限账户。', time: '11:17:41', tone: 'positive' },
      ],
    }),
  },
};

const spreadOverview = {
  periods: fundingOverview.periods,
  datasets: {
    day: makeOverviewDataset({
      periodLabel: '2026年06月25日',
      dateLabel: '2026-06-25 00:00 - 2026-06-25 23:59',
      totalFund: '20,343,790.35 CNY',
      xLabels: ['00','01','02','03','04','05','06','07','08','09','10','11'],
      barValues: [22,18,14,-8,-26,28,36,44,22,18,12,8],
      lineValues: [12,11,10,9,8,10,12,14,16,18,19,20],
      statCards: [
        { label: '净收益', value: '-18,422', subValue: '日内汇率拖累', tone: 'negative' },
        { label: '库存费', value: '+3,217', subValue: '日内累计', tone: 'positive' },
        { label: '汇率损益', value: '-6,842', subValue: '美元腿偏弱', tone: 'negative' },
        { label: '收益率', value: '-0.09%', subValue: '当日窗口', tone: 'negative' },
        { label: '换月损耗', value: '-2,114', subValue: '主力换月', tone: 'negative' },
        { label: '价差收敛', value: '+1.18', subValue: 'CNY', tone: 'positive' },
      ],
      stateCounts: [
        { label: '启动策略', count: '1', subLabel: '总计' },
        { label: '结束策略', count: '0', subLabel: '总计' },
        { label: '延续策略', count: '2', subLabel: '总计' },
      ],
      profitRows: [
        { type: '库存费', strategyCount: '1', pnl: '+3,217', ratio: '100%', tone: 'positive' },
      ],
      lossRows: [
        { type: '汇率腿', strategyCount: '1', pnl: '-6,842', ratio: '61%', tone: 'negative' },
        { type: '换月损耗', strategyCount: '1', pnl: '-4,378', ratio: '39%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '沪金与 XAUUSD 持仓已对齐。', time: '11:18:24', tone: 'positive' },
        { category: '价差同步', status: '已完成', message: 'XAUTUSDT.P - XAUUSD 最新价差已刷新。', time: '11:18:09', tone: 'positive' },
        { category: '汇率检查', status: '待确认', message: '美元腿偏移超阈值，待人工确认。', time: '11:17:41', tone: 'negative' },
      ],
    }),
    week: makeOverviewDataset({
      periodLabel: '2026 第26周',
      dateLabel: '2026-06-19 - 2026-06-25',
      totalFund: '20,343,790.35 CNY',
      xLabels: ['06-19','06-20','06-21','06-22','06-23','06-24','06-25'],
      barValues: [42,-38,54,62,70,84,96],
      lineValues: [18,17,16,15,14,13,12],
      statCards: [
        { label: '净收益', value: '-213,909', subValue: '含汇率', tone: 'negative' },
        { label: '库存费', value: '+3,616', subValue: '累计库存费', tone: 'positive' },
        { label: '汇率损益', value: '-20,128', subValue: '美元腿拖累', tone: 'negative' },
        { label: '收益率', value: '-1.04%', subValue: '周度窗口', tone: 'negative' },
        { label: '换月损耗', value: '-82,258', subValue: '主力换月', tone: 'negative' },
        { label: '海内外价差', value: '-44,421', subValue: '累计归因', tone: 'negative' },
      ],
      stateCounts: [
        { label: '启动策略', count: '2', subLabel: '总计' },
        { label: '结束策略', count: '1', subLabel: '总计' },
        { label: '延续策略', count: '6', subLabel: '总计' },
      ],
      profitRows: [
        { type: '库存费收益', strategyCount: '2', pnl: '+3,616', ratio: '100%', tone: 'positive' },
      ],
      lossRows: [
        { type: '汇率盈亏', strategyCount: '2', pnl: '-20,128', ratio: '18%', tone: 'negative' },
        { type: '换月价差', strategyCount: '2', pnl: '-82,258', ratio: '72%', tone: 'negative' },
        { type: '海内外价差', strategyCount: '1', pnl: '-11,523', ratio: '10%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '沪金与 XAUUSD 持仓已对齐。', time: '11:18:24', tone: 'positive' },
        { category: '价差同步', status: '已完成', message: 'XAUTUSDT.P - XAUUSD 最新价差已刷新。', time: '11:18:09', tone: 'positive' },
        { category: '汇率检查', status: '待确认', message: '美元腿偏移超阈值，待人工确认。', time: '11:17:41', tone: 'negative' },
      ],
    }),
    month: makeOverviewDataset({
      periodLabel: '2026年06月',
      dateLabel: '2026-06-01 - 2026-06-25',
      totalFund: '20,343,790.35 CNY',
      xLabels: ['01','03','05','07','09','11','13','15','17','19','21','23','25'],
      barValues: [34,28,-24,44,52,60,88,76,68,84,96,110,120],
      lineValues: [28,26,24,22,21,19,18,17,16,15,14,13,12],
      statCards: [
        { label: '净收益', value: '-512,640', subValue: '月度累计', tone: 'negative' },
        { label: '库存费', value: '+14,580', subValue: '月度累计', tone: 'positive' },
        { label: '汇率损益', value: '-61,842', subValue: '美元腿拖累', tone: 'negative' },
        { label: '收益率', value: '-2.31%', subValue: '月度窗口', tone: 'negative' },
        { label: '换月损耗', value: '-186,220', subValue: '换月累计', tone: 'negative' },
        { label: '海内外价差', value: '-278,440', subValue: '归因累计', tone: 'negative' },
      ],
      stateCounts: [
        { label: '启动策略', count: '6', subLabel: '总计' },
        { label: '结束策略', count: '5', subLabel: '总计' },
        { label: '延续策略', count: '13', subLabel: '总计' },
      ],
      profitRows: [
        { type: '库存费收益', strategyCount: '6', pnl: '+14,580', ratio: '100%', tone: 'positive' },
      ],
      lossRows: [
        { type: '汇率腿', strategyCount: '5', pnl: '-61,842', ratio: '12%', tone: 'negative' },
        { type: '换月损耗', strategyCount: '5', pnl: '-186,220', ratio: '36%', tone: 'negative' },
        { type: '价差偏离', strategyCount: '4', pnl: '-264,578', ratio: '52%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '月度仓位变动已整理完成。', time: '11:18:24', tone: 'positive' },
        { category: '价差同步', status: '已完成', message: '月度价差曲线已重新计算。', time: '11:18:09', tone: 'positive' },
        { category: '汇率检查', status: '复核中', message: '月内美元腿回撤较大，待复核。', time: '11:17:41', tone: 'negative' },
      ],
    }),
    custom: makeOverviewDataset({
      periodLabel: '自定义窗口',
      dateLabel: '2026-06-09 - 2026-06-25',
      totalFund: '20,343,790.35 CNY',
      xLabels: ['09','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25'],
      barValues: [18,22,28,16,-34,-22,30,44,58,72,66,60,52,48,50,42,36],
      lineValues: [26,25,24,24,22,21,20,18,17,16,15,14,14,13,12,12,11],
      statCards: [
        { label: '净收益', value: '-318,420', subValue: '自定义窗口', tone: 'negative' },
        { label: '库存费', value: '+8,642', subValue: '累计库存费', tone: 'positive' },
        { label: '汇率损益', value: '-38,224', subValue: '美元腿拖累', tone: 'negative' },
        { label: '收益率', value: '-1.52%', subValue: '窗口收益率', tone: 'negative' },
        { label: '换月损耗', value: '-96,420', subValue: '换月累计', tone: 'negative' },
        { label: '海内外价差', value: '-192,418', subValue: '归因累计', tone: 'negative' },
      ],
      stateCounts: [
        { label: '启动策略', count: '3', subLabel: '总计' },
        { label: '结束策略', count: '2', subLabel: '总计' },
        { label: '延续策略', count: '7', subLabel: '总计' },
      ],
      profitRows: [
        { type: '库存费收益', strategyCount: '3', pnl: '+8,642', ratio: '100%', tone: 'positive' },
      ],
      lossRows: [
        { type: '汇率腿', strategyCount: '2', pnl: '-38,224', ratio: '20%', tone: 'negative' },
        { type: '换月损耗', strategyCount: '2', pnl: '-96,420', ratio: '51%', tone: 'negative' },
        { type: '价差偏离', strategyCount: '2', pnl: '-54,318', ratio: '29%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '窗口内仓位变化已合并。', time: '11:18:24', tone: 'positive' },
        { category: '价差同步', status: '已完成', message: '窗口内价差与库存费快照已同步。', time: '11:18:09', tone: 'positive' },
        { category: '汇率检查', status: '待确认', message: '窗口内美元腿偏移仍需人工确认。', time: '11:17:41', tone: 'negative' },
      ],
    }),
  },
};

const dipOverview = {
  periods: fundingOverview.periods,
  datasets: {
    day: makeOverviewDataset({
      periodLabel: '2026年06月25日',
      dateLabel: '2026-06-25 00:00 - 2026-06-25 23:59',
      totalFund: '1,582,406.22 USD',
      xLabels: ['00','01','02','03','04','05','06','07','08','09','10','11'],
      barValues: [-8,12,18,22,16,28,42,36,48,30,26,18],
      lineValues: [18,19,20,22,24,26,28,31,33,35,36,38],
      statCards: [
        { label: '净收益', value: '+8,214', subValue: '日内弹性收益', tone: 'positive' },
        { label: '盈利', value: '+12,480', subValue: 'BTC / SOL 贡献', tone: 'positive' },
        { label: '亏损', value: '-4,266', subValue: 'ETH 回撤', tone: 'negative' },
        { label: '收益率', value: '+0.52%', subValue: '日内窗口', tone: 'positive' },
        { label: '手续费', value: '-1,108', subValue: '交易额 89K', tone: 'negative' },
        { label: '止盈兑现', value: '+5,416', subValue: '已实现部分', tone: 'positive' },
      ],
      stateCounts: [
        { label: '启动策略', count: '2', subLabel: '总计' },
        { label: '结束策略', count: '1', subLabel: '总计' },
        { label: '延续策略', count: '3', subLabel: '总计' },
      ],
      profitRows: [
        { type: 'BTC', strategyCount: '1', pnl: '+5,620', ratio: '68%', tone: 'positive' },
        { type: 'SOL', strategyCount: '1', pnl: '+2,594', ratio: '32%', tone: 'positive' },
      ],
      lossRows: [
        { type: 'ETH', strategyCount: '1', pnl: '-4,266', ratio: '100%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '抄底组合仓位已刷新。', time: '11:18:24', tone: 'positive' },
        { category: '止盈检查', status: '监控中', message: 'SOL 止盈挂单仍在等待成交。', time: '11:18:09', tone: 'neutral' },
        { category: '风险检查', status: '已完成', message: '组合集中度仍在阈值内。', time: '11:17:41', tone: 'positive' },
      ],
    }),
    week: makeOverviewDataset({
      periodLabel: '2026 第26周',
      dateLabel: '2026-06-19 - 2026-06-25',
      totalFund: '1,582,406.22 USD',
      xLabels: ['06-19','06-20','06-21','06-22','06-23','06-24','06-25'],
      barValues: [32,-16,48,56,72,88,96],
      lineValues: [12,14,16,21,25,30,36],
      statCards: [
        { label: '净收益', value: '+128,950', subValue: '周度累计', tone: 'positive' },
        { label: '盈利', value: '+152,880', subValue: '正收益策略累计', tone: 'positive' },
        { label: '亏损', value: '-23,930', subValue: '回撤与止损', tone: 'negative' },
        { label: '收益率', value: '+8.14%', subValue: '周度窗口', tone: 'positive' },
        { label: '手续费', value: '-4,520', subValue: '交易额 248K', tone: 'negative' },
        { label: '止盈兑现', value: '+76,580', subValue: '已实现收益', tone: 'positive' },
      ],
      stateCounts: [
        { label: '启动策略', count: '4', subLabel: '总计' },
        { label: '结束策略', count: '3', subLabel: '总计' },
        { label: '延续策略', count: '8', subLabel: '总计' },
      ],
      profitRows: [
        { type: 'BTC', strategyCount: '3', pnl: '+72,440', ratio: '56%', tone: 'positive' },
        { type: 'ETH', strategyCount: '2', pnl: '+28,120', ratio: '22%', tone: 'positive' },
        { type: 'SOL', strategyCount: '3', pnl: '+28,390', ratio: '22%', tone: 'positive' },
      ],
      lossRows: [
        { type: '止损回撤', strategyCount: '2', pnl: '-23,930', ratio: '100%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '抄底组合仓位已刷新。', time: '11:18:24', tone: 'positive' },
        { category: '止盈检查', status: '监控中', message: 'SOL 止盈挂单仍在等待成交。', time: '11:18:09', tone: 'neutral' },
        { category: '风险检查', status: '已完成', message: '组合集中度仍在阈值内。', time: '11:17:41', tone: 'positive' },
      ],
    }),
    month: makeOverviewDataset({
      periodLabel: '2026年06月',
      dateLabel: '2026-06-01 - 2026-06-25',
      totalFund: '1,582,406.22 USD',
      xLabels: ['01','03','05','07','09','11','13','15','17','19','21','23','25'],
      barValues: [18,-22,28,34,42,50,62,68,74,82,90,102,110],
      lineValues: [8,9,10,12,14,16,18,20,23,26,29,32,36],
      statCards: [
        { label: '净收益', value: '+302,840', subValue: '月度累计', tone: 'positive' },
        { label: '盈利', value: '+358,420', subValue: '正收益策略累计', tone: 'positive' },
        { label: '亏损', value: '-55,580', subValue: '回撤与止损', tone: 'negative' },
        { label: '收益率', value: '+18.22%', subValue: '月度窗口', tone: 'positive' },
        { label: '手续费', value: '-12,486', subValue: '交易额 816K', tone: 'negative' },
        { label: '止盈兑现', value: '+188,220', subValue: '已实现收益', tone: 'positive' },
      ],
      stateCounts: [
        { label: '启动策略', count: '12', subLabel: '总计' },
        { label: '结束策略', count: '10', subLabel: '总计' },
        { label: '延续策略', count: '18', subLabel: '总计' },
      ],
      profitRows: [
        { type: 'BTC', strategyCount: '8', pnl: '+162,420', ratio: '54%', tone: 'positive' },
        { type: 'ETH', strategyCount: '5', pnl: '+76,220', ratio: '25%', tone: 'positive' },
        { type: 'SOL', strategyCount: '5', pnl: '+64,200', ratio: '21%', tone: 'positive' },
      ],
      lossRows: [
        { type: '止损回撤', strategyCount: '6', pnl: '-55,580', ratio: '100%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '月度抄底组合仓位已刷新。', time: '11:18:24', tone: 'positive' },
        { category: '止盈检查', status: '监控中', message: '部分保护单待成交。', time: '11:18:09', tone: 'neutral' },
        { category: '风险检查', status: '已完成', message: '组合集中度仍在阈值内。', time: '11:17:41', tone: 'positive' },
      ],
    }),
    custom: makeOverviewDataset({
      periodLabel: '自定义窗口',
      dateLabel: '2026-06-09 - 2026-06-25',
      totalFund: '1,582,406.22 USD',
      xLabels: ['09','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25'],
      barValues: [8,10,-12,18,24,30,34,40,46,54,66,72,78,84,92,100,108],
      lineValues: [10,11,11,12,13,15,17,18,20,22,24,26,29,31,33,35,36],
      statCards: [
        { label: '净收益', value: '+186,220', subValue: '自定义窗口', tone: 'positive' },
        { label: '盈利', value: '+224,460', subValue: '正收益策略累计', tone: 'positive' },
        { label: '亏损', value: '-38,240', subValue: '回撤与止损', tone: 'negative' },
        { label: '收益率', value: '+11.82%', subValue: '窗口收益率', tone: 'positive' },
        { label: '手续费', value: '-8,114', subValue: '交易额 432K', tone: 'negative' },
        { label: '止盈兑现', value: '+102,446', subValue: '已实现收益', tone: 'positive' },
      ],
      stateCounts: [
        { label: '启动策略', count: '6', subLabel: '总计' },
        { label: '结束策略', count: '4', subLabel: '总计' },
        { label: '延续策略', count: '9', subLabel: '总计' },
      ],
      profitRows: [
        { type: 'BTC', strategyCount: '4', pnl: '+102,640', ratio: '55%', tone: 'positive' },
        { type: 'ETH', strategyCount: '2', pnl: '+42,380', ratio: '23%', tone: 'positive' },
        { type: 'SOL', strategyCount: '3', pnl: '+41,200', ratio: '22%', tone: 'positive' },
      ],
      lossRows: [
        { type: '止损回撤', strategyCount: '4', pnl: '-38,240', ratio: '100%', tone: 'negative' },
      ],
      syncRows: [
        { category: '持仓同步', status: '已完成', message: '窗口内抄底仓位已刷新。', time: '11:18:24', tone: 'positive' },
        { category: '止盈检查', status: '监控中', message: '部分保护单待成交。', time: '11:18:09', tone: 'neutral' },
        { category: '风险检查', status: '已完成', message: '窗口内组合集中度仍在阈值内。', time: '11:17:41', tone: 'positive' },
      ],
    }),
  },
};

const baseStrategyDeskProfiles: Record<'funding' | 'spread' | 'dip', StrategyDeskProfile> = {
  funding: {
    key: 'funding',
    label: '资费',
    title: '资金费率套利策略管理',
    subtitle: '这里看的是下单之后的账户运行、收益归因、执行质量与同步状态，不与价差策略混放。',
    strategyName: 'Binance / OKX / Bybit · 资金费率套利',
    filters: ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'XAUT'],
    overview: fundingOverview,
    detail: {
      title: '黄金费率套利 XAUT/XAU',
      status: '运行中',
      actions: ['加仓', '平仓/卖出', '结束策略', '回补快照'],
      metrics: [
        { label: '合约占用资金', value: '6,701.74', tone: 'neutral' },
        { label: '现货占用资金', value: '6,673.83', tone: 'neutral' },
        { label: '期限收益', value: '-16.08', tone: 'negative' },
        { label: '费率收益', value: '-0.085', tone: 'negative' },
        { label: '净收益', value: '-28.97', tone: 'negative' },
        { label: '手续费', value: '12.81', tone: 'negative' },
      ],
      legs: [
        {
          title: '现货腿',
          market: 'gate',
          symbol: 'XAUT/USDT',
          actions: ['编辑', '编辑成交', '手动录入卖出', '结束', '删除'],
          rows: [
            { label: '持仓数量', value: '0' }, { label: '成本均价', value: '5,339.06' }, { label: '最新价', value: '5,129.30' },
            { label: '持仓价值', value: '0.00' }, { label: '未实现盈亏', value: '+0.00', tone: 'positive' }, { label: '已实现盈亏', value: '+0.00', tone: 'positive' },
            { label: '最后同步', value: '2026/3/5 15:37:04' },
          ],
        },
        {
          title: '合约腿',
          market: 'binance',
          symbol: 'XAU/USDT:USDT',
          actions: ['编辑', '结束', '删除'],
          rows: [
            { label: '持仓数量', value: '0' }, { label: '均价', value: '5,361.388' }, { label: '标记价', value: '5,158.18' },
            { label: '未实现盈亏', value: '+0.00', tone: 'positive' }, { label: '已实现盈亏', value: '+0.00', tone: 'positive' }, { label: '下次费率', value: '-0.0028%', tone: 'negative' },
            { label: '下次结算', value: '2026/3/5 16:00:00' }, { label: '最后同步', value: '2026/3/5 15:37:05' },
          ],
        },
      ],
      exposureRows: [
        { label: '合约持仓', value: '0' }, { label: '现货持仓', value: '0' }, { label: '净敞口', value: '0', tone: 'positive' },
      ],
      tabs: [
        { key: 'records', label: '成交记录' }, { key: 'fundingFlow', label: '资金费率流水' }, { key: 'curve', label: '收益曲线' }, { key: 'timeline', label: '费率时间轴' },
      ],
      tabTables: {
        records: {
          columns: [{ key: 'venue', label: '交易所' }, { key: 'type', label: '腿类型' }, { key: 'symbol', label: '交易对' }, { key: 'side', label: '方向' }, { key: 'price', label: '价格' }, { key: 'qty', label: '数量' }, { key: 'fee', label: '手续费' }, { key: 'time', label: '成交时间' }],
          rows: [{ venue: 'binance', type: '合约', symbol: 'XAU/USDT:USDT', side: '买入', price: '5,160.64', qty: '0.002', fee: '0.0000', time: '2026/3/5 15:17:38' }, { venue: 'gate', type: '现货', symbol: 'XAUT/USDT', side: '卖出', price: '5,125.10', qty: '0.0487', fee: '0.2446', time: '2026/3/5 15:16:35' }],
        },
        fundingFlow: {
          columns: [{ key: 'settle', label: '结算时间' }, { key: 'symbol', label: '标的' }, { key: 'rate', label: '费率' }, { key: 'income', label: '费率收入' }, { key: 'source', label: '来源' }],
          rows: [{ settle: '2026/3/5 16:00', symbol: 'XAU/USDT:USDT', rate: '-0.0028%', income: '-0.085', source: 'Binance API' }],
        },
        curve: { columns: [], rows: [] },
        timeline: {
          columns: [{ key: 'time', label: '时间' }, { key: 'event', label: '事件' }, { key: 'remark', label: '说明' }],
          rows: [{ time: '2026/3/5 15:37:05', event: '同步完成', remark: '现货腿与合约腿状态已刷新。' }, { time: '2026/3/5 16:00:00', event: '费率结算', remark: '下一次资金费率结算窗口。' }],
        },
      },
    },
    kpis: [
      { label: '策略净值', value: '4,502,541.72', unit: 'USD', note: '资费账户合计', tone: 'neutral' },
      { label: '累计收益', value: '511,986.31', unit: 'USD', note: '含已实现与未实现', tone: 'positive' },
      { label: '过去24h盈亏', value: '-32.16', unit: 'USD', note: 'ETH 费率回落拖累', tone: 'negative' },
      { label: '活跃策略账户', value: '6', note: '3 交易所 × 2 子账户', tone: 'neutral' },
      { label: '运行中指令', value: '5', note: '2 开仓 / 3 移仓', tone: 'neutral' },
      { label: '胜率', value: '72.4%', note: '近 30 日滚动', tone: 'positive' },
    ],
    gauges: [
      { label: '资产水平', value: '11,312,370.08', subValue: '资金腿 CNY', progress: 62, leftLabel: '资金腿', rightLabel: '合约腿', leftColor: '#2f80ed', rightColor: '#f5a623' },
      { label: '仓位平衡', value: '74.58%', subValue: '多 / 空匹配完成度', progress: 75, leftLabel: '多', rightLabel: '空', leftColor: '#1abc9c', rightColor: '#d74d4d' },
    ],
    accountBreakdown: [
      { label: 'AUM 总计', value: '20,343,790.35 CNY', note: '2,984,316.97 USD', tone: 'neutral' },
      { label: '整体杠杆', value: '1.1X', note: '低于策略上限 1.8X', tone: 'positive' },
      { label: '备用金 CNY', value: '0', note: '当前未额外预留', tone: 'neutral' },
      { label: '备用金 USD', value: '0', note: '当前未额外预留', tone: 'neutral' },
      { label: '主资金账户', value: '11,312,370.08 CNY', note: '可用资金 92.69%', tone: 'positive' },
      { label: '对冲账户', value: '1,324,857.38 USD', note: '预付费比率 97378.75%', tone: 'positive' },
    ],
    executionHeader: '策略执行',
    executionStatus: ['开仓', '移仓', '平仓'],
    executionMetrics: [
      { label: '可用资金率', before: '92.69%', after: '92.69%', tone: 'positive' },
      { label: '整体杠杆', before: '1.4971', after: '1.4971', alert: 'MAX=20.0000', tone: 'neutral' },
      { label: '预付费比率', before: '0.0000%', after: '0.0000%', tone: 'positive' },
    ],
    logs: [
      { time: '2026-06-25 10:31:08', text: 'BTC 套利单已完成，资金腿与合约腿已全部成交。', tone: 'positive' },
      { time: '2026-06-25 10:24:44', text: '策略开仓订单已完成，成交数量 2。', tone: 'positive' },
      { time: '2026-06-25 10:13:04', text: 'XRP 移仓正在执行，剩余 1 手待处理。', tone: 'neutral' },
      { time: '2026-06-25 09:57:12', text: 'ETH 套利单资金腿延迟 800ms，已记录执行异常。', tone: 'negative' },
    ],
    curves: [
      { title: '总收益', amount: '511,986.31', unit: 'USD', tone: 'positive', points: [{ date: '06-18', value: 180 }, { date: '06-19', value: 165 }, { date: '06-20', value: 172 }, { date: '06-21', value: 210 }, { date: '06-22', value: 248 }, { date: '06-23', value: 286 }, { date: '06-24', value: 302 }, { date: '06-25', value: 336 }] },
      { title: '资金费收益', amount: '285,780.00', unit: 'USD', tone: 'positive', points: [{ date: '06-18', value: 42 }, { date: '06-19', value: 48 }, { date: '06-20', value: 50 }, { date: '06-21', value: 65 }, { date: '06-22', value: 88 }, { date: '06-23', value: 108 }, { date: '06-24', value: 132 }, { date: '06-25', value: 168 }] },
      { title: '基差 / 执行归因', amount: '-21,390.00', unit: 'USD', tone: 'negative', points: [{ date: '06-18', value: 18 }, { date: '06-19', value: 16 }, { date: '06-20', value: 11 }, { date: '06-21', value: 8 }, { date: '06-22', value: 5 }, { date: '06-23', value: -6 }, { date: '06-24', value: -22 }, { date: '06-25', value: -31 }] },
    ],
    tabs: [{ key: 'positions', label: '当前持仓' }, { key: 'history', label: '历史订单' }, { key: 'fills', label: '成交记录' }, { key: 'logs', label: '执行记录' }],
    tables: {
      positions: { columns: [{ key: 'symbol', label: '标的' }, { key: 'exchange', label: '平台' }, { key: 'size', label: '数量' }, { key: 'value', label: '价值' }, { key: 'entry', label: '入场价格' }, { key: 'mark', label: '当前价格' }, { key: 'pnl', label: '未结盈亏' }, { key: 'funding', label: '累计资费' }], rows: [{ symbol: 'BTCUSDT', exchange: 'Binance', size: '2.00', value: '214,520', entry: '106,842', mark: '107,204', pnl: '724', funding: '1,842' }, { symbol: 'ETHUSDT', exchange: 'OKX', size: '18.00', value: '61,830', entry: '3,421', mark: '3,398', pnl: '-414', funding: '626' }, { symbol: 'XRPUSDT', exchange: 'Bybit', size: '48,000', value: '104,640', entry: '2.14', mark: '2.18', pnl: '1,920', funding: '308' }] },
      history: { columns: [{ key: 'time', label: '时间' }, { key: 'symbol', label: '标的' }, { key: 'action', label: '动作' }, { key: 'venue', label: '平台' }, { key: 'price', label: '价格' }, { key: 'size', label: '数量' }, { key: 'status', label: '状态' }], rows: [{ time: '06-25 10:24', symbol: 'BTCUSDT', action: '开仓', venue: 'Binance', price: '106,955', size: '0.50', status: '已完成' }, { time: '06-25 09:42', symbol: 'ETHUSDT', action: '移仓', venue: 'OKX', price: '3,405', size: '5.00', status: '已完成' }, { time: '06-25 09:11', symbol: 'DOGEUSDT', action: '平仓', venue: 'Bybit', price: '0.284', size: '32,000', status: '撤单后重发' }] },
      fills: { columns: [{ key: 'orderId', label: '订单号' }, { key: 'symbol', label: '标的' }, { key: 'fillPrice', label: '成交价' }, { key: 'fillSize', label: '成交量' }, { key: 'fee', label: '手续费' }, { key: 'slippage', label: '滑点' }, { key: 'time', label: '成交时间' }], rows: [{ orderId: 'FUND-8244', symbol: 'BTCUSDT', fillPrice: '106,955', fillSize: '0.50', fee: '12.4', slippage: '0.011%', time: '06-25 10:24:44' }, { orderId: 'FUND-8242', symbol: 'ETHUSDT', fillPrice: '3,405', fillSize: '5.00', fee: '8.2', slippage: '0.019%', time: '06-25 09:42:18' }] },
      logs: { columns: [{ key: 'time', label: '时间' }, { key: 'type', label: '类别' }, { key: 'content', label: '内容' }], rows: [{ time: '06-25 10:31:08', type: '执行成功', content: 'BTC 套利单全腿成交完成。' }, { time: '06-25 09:57:12', type: '异常提醒', content: 'ETH 资金腿延迟 800ms，已进入监控队列。' }, { time: '06-25 09:13:50', type: '风控提示', content: 'XRP 名义敞口接近上限 82%。' }] },
    },
  },
  spread: {
    key: 'spread',
    label: '价差',
    title: '价差套利策略管理',
    subtitle: '聚焦 XAUTUSDT.P - XAUUSD 的策略账户运行、库存费、汇率与执行质量。',
    strategyName: 'XAUTUSDT.P - XAUUSD · 跨市场价差套利',
    filters: ['XAUT', '黄金', '汇率', '库存费'],
    overview: spreadOverview,
    detail: {
      title: '黄金价差分析',
      status: '运行中',
      actions: ['添加对比腿', '刷新数据', '回看快照'],
      metrics: [
        { label: '国内金', value: '1,055.5 元', tone: 'neutral' },
        { label: '国外金', value: '4,812.77 美元', tone: 'neutral' },
        { label: '当前价差', value: '-30.9600', tone: 'negative' },
        { label: '标准差', value: '3.8135', tone: 'neutral' },
        { label: '当前价差率', value: '-0.6075%', tone: 'negative' },
        { label: '最长回归', value: '17.0h', tone: 'negative' },
      ],
      legs: [
        {
          title: '对比项 A',
          market: 'XAUT/OKX - XAU/Binance',
          symbol: 'PAXG/Binance',
          actions: ['1H', '4H', '1D'],
          rows: [
            { label: '当前价差', value: '-30.9600', tone: 'negative' }, { label: '均值', value: '-37.9848' }, { label: '最大', value: '-27.4500' },
            { label: '最小', value: '-48.1000' }, { label: '标准差', value: '3.8135' }, { label: '当前价差率', value: '-0.6075%', tone: 'negative' },
            { label: '最短回归', value: '1.0h', tone: 'positive' }, { label: '平均', value: '4.7h' },
          ],
        },
        {
          title: '对比项 B',
          market: 'XAU/Gate 合约 - XAU/Binance',
          symbol: 'XAU/Gate 合约',
          actions: ['100', '200', '500', '1000'],
          rows: [
            { label: '当前价差', value: '-1.9700', tone: 'negative' }, { label: '均值', value: '-7.1429' }, { label: '最大', value: '2.1500', tone: 'positive' },
            { label: '最小', value: '-17.9500' }, { label: '标准差', value: '5.3123' }, { label: '当前价差率', value: '0.0387%', tone: 'positive' },
            { label: '最短回归', value: '2.0h', tone: 'positive' }, { label: '平均', value: '12.5h' },
          ],
        },
      ],
      exposureRows: [
        { label: '对比腿数量', value: '3' }, { label: '活跃价差窗口', value: '2' }, { label: '建议优先级', value: '中等', tone: 'neutral' },
      ],
      tabs: [
        { key: 'records', label: '对比明细' }, { key: 'fundingFlow', label: '回归统计' }, { key: 'curve', label: '价格叠加图' }, { key: 'timeline', label: '回归时间轴' },
      ],
      tabTables: {
        records: {
          columns: [{ key: 'pair', label: '对比项' }, { key: 'window', label: '周期' }, { key: 'basis', label: '当前价差' }, { key: 'rate', label: '价差率' }, { key: 'priority', label: '优先级' }],
          rows: [{ pair: 'XAUT/OKX - XAU/Binance', window: '1H', basis: '-30.9600', rate: '-0.6075%', priority: '中' }, { pair: 'XAU/Gate合约 - XAU/Binance', window: '1H', basis: '-1.9700', rate: '0.0387%', priority: '低' }],
        },
        fundingFlow: {
          columns: [{ key: 'pair', label: '对比项' }, { key: 'longest', label: '最长回归' }, { key: 'shortest', label: '最短回归' }, { key: 'avg', label: '平均' }, { key: 'median', label: '中位数' }],
          rows: [{ pair: 'XAUT/OKX - XAU/Binance', longest: '17.0h', shortest: '1.0h', avg: '4.7h', median: '2.0h' }, { pair: 'XAU/Gate合约 - XAU/Binance', longest: '2.4d', shortest: '2.0h', avg: '12.5h', median: '5.0h' }],
        },
        curve: { columns: [], rows: [] },
        timeline: {
          columns: [{ key: 'time', label: '时间' }, { key: 'event', label: '事件' }, { key: 'remark', label: '说明' }],
          rows: [{ time: '2026/3/13 14:32', event: '刷新数据', remark: '价格叠加图已重算。' }, { time: '2026/3/13 14:25', event: '新增对比项', remark: '加入 Gate 合约腿。' }],
        },
      },
    },
    kpis: [
      { label: '策略净值', value: '20,343,790.35', unit: 'CNY', note: '国内外金账户合计', tone: 'neutral' },
      { label: '累计收益', value: '-213,909.50', unit: 'CNY', note: '含汇率与库存费', tone: 'negative' },
      { label: '库存费盈亏', value: '3,616.75', unit: 'CNY', note: '月度累计', tone: 'positive' },
      { label: '汇率盈亏', value: '-20,128.39', unit: 'CNY', note: '美元腿拖累', tone: 'negative' },
      { label: '运行中移仓', value: '2', note: '主力换月处理中', tone: 'neutral' },
      { label: '对冲完整度', value: '74.58%', note: '多空尚未完全对齐', tone: 'negative' },
    ],
    gauges: [
      { label: '资产水平', value: '11,312,370.08', subValue: '沪金资产水平 CNY', progress: 58, leftLabel: '沪金', rightLabel: '伦敦金', leftColor: '#2f80ed', rightColor: '#ffb020' },
      { label: '仓位平衡', value: '74.58%', subValue: '多 74.58% VS 空 25.42%', progress: 75, leftLabel: '多', rightLabel: '空', leftColor: '#1abc9c', rightColor: '#cf3f4f' },
    ],
    accountBreakdown: [
      { label: 'AUM 总计', value: '20,343,790.35 CNY', note: '2,984,316.97 USD', tone: 'neutral' },
      { label: '整体杠杆', value: '1.1X', note: '处于舒适区间', tone: 'positive' },
      { label: '沪金账户', value: '11,312,370.08 CNY', note: '可用资金 92.69%', tone: 'positive' },
      { label: '伦敦金账户', value: '1,324,857.38 USD', note: '自动匹配中', tone: 'neutral' },
      { label: '国内金', value: '1,055.5 元', note: 'AU9999 当前价格', tone: 'neutral' },
      { label: '国外金', value: '4,812.77 美元', note: 'XAUUSD 当前价格', tone: 'neutral' },
    ],
    executionHeader: '策略执行',
    executionStatus: ['开仓', '移仓', '止盈'],
    executionMetrics: [
      { label: '可用资金率', before: '92.69%', after: '92.69%', tone: 'positive' },
      { label: '整体杠杆', before: '1.4971', after: '1.4971', alert: 'MAX=20.0000', tone: 'neutral' },
      { label: '预付费比率', before: '0.0000%', after: '0.0000%', tone: 'positive' },
    ],
    logs: [
      { time: '2026-06-25 10:18:16', text: '沪金 2612 -> 2704 主力换月已提交。', tone: 'neutral' },
      { time: '2026-06-25 10:03:42', text: 'XAUUSD 对冲腿成交，价差收敛 1.18 CNY。', tone: 'positive' },
      { time: '2026-06-25 09:26:11', text: '汇率腿偏移超阈值，触发人工确认。', tone: 'negative' },
    ],
    curves: [
      { title: '总收益(含汇率)', amount: '-213,909.50', unit: 'CNY', tone: 'negative', points: [{ date: '06-18', value: 46 }, { date: '06-19', value: 24 }, { date: '06-20', value: 10 }, { date: '06-21', value: -14 }, { date: '06-22', value: -82 }, { date: '06-23', value: -126 }, { date: '06-24', value: -188 }, { date: '06-25', value: -252 }] },
      { title: '库存费盈亏', amount: '3,616.75', unit: 'CNY', tone: 'positive', points: [{ date: '06-18', value: 5 }, { date: '06-19', value: 8 }, { date: '06-20', value: 14 }, { date: '06-21', value: 18 }, { date: '06-22', value: 30 }, { date: '06-23', value: 42 }, { date: '06-24', value: 54 }, { date: '06-25', value: 70 }] },
      { title: '汇率盈亏', amount: '-20,128.39', unit: 'CNY', tone: 'negative', points: [{ date: '06-18', value: -4 }, { date: '06-19', value: -6 }, { date: '06-20', value: -9 }, { date: '06-21', value: -12 }, { date: '06-22', value: -18 }, { date: '06-23', value: -24 }, { date: '06-24', value: -36 }, { date: '06-25', value: -48 }] },
    ],
    tabs: [{ key: 'positions', label: '当前持仓' }, { key: 'history', label: '历史订单' }, { key: 'fills', label: '成交记录' }, { key: 'logs', label: '执行记录' }],
    tables: {
      positions: { columns: [{ key: 'symbol', label: '标的' }, { key: 'contract', label: '合约' }, { key: 'size', label: '数量(手)' }, { key: 'value', label: '价值' }, { key: 'entry', label: '入场价格' }, { key: 'mark', label: '当前价格' }, { key: 'carry', label: '库存费' }], rows: [{ symbol: '沪金', contract: 'SHFE.au2612', size: '5.00', value: '5,344,500.00', entry: '1,121.12', mark: '1,068.90', carry: '-261,120.00' }, { symbol: '沪金', contract: 'SHFE.au2704', size: '1.00', value: '1,075,420.00', entry: '989.96', mark: '1,075.42', carry: '-339,140.00' }, { symbol: '伦敦金', contract: 'XAUUSD+', size: '0.64', value: '1,324,857.38', entry: '4,802.15', mark: '4,820.01', carry: '3,617.00' }] },
      history: { columns: [{ key: 'time', label: '时间' }, { key: 'symbol', label: '标的' }, { key: 'action', label: '动作' }, { key: 'price', label: '价格' }, { key: 'basis', label: '价差' }, { key: 'status', label: '状态' }], rows: [{ time: '06-25 10:18', symbol: 'SHFE.au2612', action: '移仓', price: '1,075.42', basis: '1.18 CNY', status: '执行中' }, { time: '06-25 10:03', symbol: 'XAUUSD+', action: '开仓', price: '4,820.01', basis: '0.11%', status: '已完成' }] },
      fills: { columns: [{ key: 'orderId', label: '订单号' }, { key: 'leg', label: '腿' }, { key: 'fillPrice', label: '成交价' }, { key: 'fillSize', label: '成交量' }, { key: 'fee', label: '手续费' }, { key: 'time', label: '成交时间' }], rows: [{ orderId: 'SPRD-1042', leg: '沪金', fillPrice: '1,075.42', fillSize: '1.00', fee: '45.20', time: '06-25 10:18:16' }, { orderId: 'SPRD-1041', leg: 'XAUUSD', fillPrice: '4,820.01', fillSize: '0.64', fee: '11.08', time: '06-25 10:03:42' }] },
      logs: { columns: [{ key: 'time', label: '时间' }, { key: 'type', label: '类别' }, { key: 'content', label: '内容' }], rows: [{ time: '06-25 10:18:16', type: '移仓', content: '主力换月开始执行。' }, { time: '06-25 09:26:11', type: '异常提醒', content: '汇率腿偏移超过预警阈值。' }] },
    },
  },
  dip: {
    key: 'dip',
    label: '抄底',
    title: '抄底策略管理',
    subtitle: '偏重信号后跟踪、仓位回收、止盈止损、持仓结果归因。',
    strategyName: 'BTC / ETH / SOL 抄底组合',
    filters: ['BTC', 'ETH', 'SOL'],
    overview: dipOverview,
    detail: {
      title: 'BULLAUSDT 费率套利',
      status: '运行中',
      actions: ['加仓', '平仓/卖出', '结束策略', '回补快照'],
      metrics: [
        { label: '合约占用资金', value: '6,515.49', tone: 'neutral' },
        { label: '现货占用资金', value: '6,483.09', tone: 'neutral' },
        { label: '期限收益', value: '+103.13', tone: 'positive' },
        { label: '费率收益', value: '+525.23', tone: 'positive' },
        { label: '净收益', value: '+629.05', tone: 'positive' },
        { label: '手续费', value: '1.30', tone: 'negative' },
      ],
      legs: [
        {
          title: '合约腿',
          market: 'binance',
          symbol: 'BULLA/USDT:USDT',
          actions: ['编辑', '结束', '删除'],
          rows: [
            { label: '持仓数量', value: '-447,296' }, { label: '均价', value: '0.0148923630' }, { label: '标记价', value: '0.00885' },
            { label: '未实现盈亏', value: '+2,720.61', tone: 'positive' }, { label: '已实现盈亏', value: '+0.00', tone: 'positive' }, { label: '下次费率', value: '0.1353%', tone: 'positive' },
            { label: '预估费用', value: '+5.3540', tone: 'positive' }, { label: '下次结算', value: '2026/3/13 16:00:00' },
          ],
        },
        {
          title: '现货腿',
          market: 'mexc',
          symbol: 'BULLA/USDT',
          actions: ['编辑', '编辑成交', '手动录入卖出', '结束'],
          rows: [
            { label: '持仓数量', value: '440,000' }, { label: '成本均价', value: '0.0152663047' }, { label: '最新价', value: '0.00879' },
            { label: '持仓价值', value: '3,867.60' }, { label: '未实现盈亏', value: '+3,653.48', tone: 'positive' }, { label: '已实现盈亏', value: '+0.00', tone: 'positive' },
            { label: '最后同步', value: '2026/3/13 14:33:30' },
          ],
        },
      ],
      exposureRows: [
        { label: '合约持仓', value: '447,296' }, { label: '现货持仓', value: '440,000' }, { label: '净敞口', value: '-7,296', tone: 'negative' },
      ],
      tabs: [
        { key: 'records', label: '成交记录' }, { key: 'fundingFlow', label: '资金费率流水' }, { key: 'curve', label: '收益曲线' }, { key: 'timeline', label: '费率时间轴' },
      ],
      tabTables: {
        records: {
          columns: [{ key: 'venue', label: '交易所' }, { key: 'type', label: '腿类型' }, { key: 'symbol', label: '交易对' }, { key: 'side', label: '方向' }, { key: 'price', label: '价格' }, { key: 'qty', label: '数量' }, { key: 'time', label: '成交时间' }],
          rows: [{ venue: 'mexc', type: '现货', symbol: 'BULLA/USDT', side: '买入', price: '0.00909', qty: '1,060.79', time: '2026/3/11 16:18:07' }, { venue: 'binance', type: '合约', symbol: 'BULLA/USDT:USDT', side: '卖出', price: '0.00885', qty: '447,296', time: '2026/3/13 14:33:22' }],
        },
        fundingFlow: {
          columns: [{ key: 'settle', label: '结算时间' }, { key: 'rate', label: '费率' }, { key: 'income', label: '费率收入' }, { key: 'symbol', label: '标的' }],
          rows: [{ settle: '2026/3/13 16:00', rate: '0.1353%', income: '+5.3540', symbol: 'BULLA/USDT:USDT' }],
        },
        curve: { columns: [], rows: [] },
        timeline: {
          columns: [{ key: 'time', label: '时间' }, { key: 'event', label: '事件' }, { key: 'remark', label: '说明' }],
          rows: [{ time: '2026/3/13 14:33:30', event: '同步完成', remark: 'BULLA 双腿状态已刷新。' }, { time: '2026/3/13 16:00:00', event: '费率结算', remark: '下一次费率结算窗口。' }],
        },
      },
    },
    kpis: [
      { label: '策略净值', value: '1,582,406.22', unit: 'USD', note: '组合账户', tone: 'neutral' },
      { label: '累计收益', value: '128,950.40', unit: 'USD', note: '波段抄底累计', tone: 'positive' },
      { label: '24h盈亏', value: '8,214.22', unit: 'USD', note: 'BTC 反弹贡献居多', tone: 'positive' },
      { label: '持仓标的数', value: '3', note: 'BTC / ETH / SOL', tone: 'neutral' },
      { label: '胜率', value: '64.8%', note: '近 90 日滚动', tone: 'positive' },
      { label: '最大回撤', value: '-11.2%', note: '策略历史', tone: 'negative' },
    ],
    gauges: [
      { label: '仓位使用', value: '58%', subValue: '当前仓位利用率', progress: 58, leftLabel: '仓位', rightLabel: '现金', leftColor: '#2f80ed', rightColor: '#94a3b8' },
      { label: '止盈覆盖', value: '67%', subValue: '已有保护单的持仓占比', progress: 67, leftLabel: '已覆盖', rightLabel: '未覆盖', leftColor: '#22a06b', rightColor: '#d74d4d' },
    ],
    accountBreakdown: [
      { label: 'AUM 总计', value: '1,582,406.22 USD', note: '抄底组合账户', tone: 'neutral' },
      { label: '现金占比', value: '42%', note: '保留继续加仓弹药', tone: 'positive' },
      { label: 'BTC 仓位', value: '48%', note: '主仓', tone: 'neutral' },
      { label: 'ETH 仓位', value: '31%', note: '辅助仓', tone: 'neutral' },
      { label: 'SOL 仓位', value: '21%', note: '高弹性仓', tone: 'neutral' },
      { label: '保护单覆盖', value: '67%', note: '仍需补全', tone: 'negative' },
    ],
    executionHeader: '策略执行',
    executionStatus: ['加仓', '减仓', '止盈'],
    executionMetrics: [
      { label: '可用现金', before: '42%', after: '39%', tone: 'neutral' },
      { label: '组合集中度', before: '48%', after: '51%', alert: 'BTC 单币敞口升高', tone: 'negative' },
      { label: '止盈覆盖', before: '67%', after: '73%', tone: 'positive' },
    ],
    logs: [
      { time: '2026-06-25 11:02:18', text: 'BTC 二次加仓完成，均价上移至 105,220。', tone: 'positive' },
      { time: '2026-06-25 10:26:04', text: 'SOL 止盈单挂出，等待成交。', tone: 'neutral' },
    ],
    curves: [
      { title: '策略净值曲线', amount: '1,582,406.22', unit: 'USD', tone: 'positive', points: [{ date: '06-18', value: 102 }, { date: '06-19', value: 98 }, { date: '06-20', value: 110 }, { date: '06-21', value: 116 }, { date: '06-22', value: 124 }, { date: '06-23', value: 132 }, { date: '06-24', value: 144 }, { date: '06-25', value: 156 }] },
      { title: '已实现收益', amount: '76,580.20', unit: 'USD', tone: 'positive', points: [{ date: '06-18', value: 20 }, { date: '06-19', value: 24 }, { date: '06-20', value: 31 }, { date: '06-21', value: 42 }, { date: '06-22', value: 50 }, { date: '06-23', value: 56 }, { date: '06-24', value: 64 }, { date: '06-25', value: 72 }] },
      { title: '浮动盈亏', amount: '52,370.20', unit: 'USD', tone: 'neutral', points: [{ date: '06-18', value: 8 }, { date: '06-19', value: -4 }, { date: '06-20', value: 12 }, { date: '06-21', value: 16 }, { date: '06-22', value: 22 }, { date: '06-23', value: 18 }, { date: '06-24', value: 28 }, { date: '06-25', value: 36 }] },
    ],
    tabs: [{ key: 'positions', label: '当前持仓' }, { key: 'history', label: '历史订单' }, { key: 'fills', label: '成交记录' }, { key: 'logs', label: '执行记录' }],
    tables: {
      positions: { columns: [{ key: 'symbol', label: '标的' }, { key: 'size', label: '数量' }, { key: 'value', label: '市值' }, { key: 'entry', label: '持仓均价' }, { key: 'mark', label: '当前价格' }, { key: 'pnl', label: '浮盈' }, { key: 'stop', label: '止损/止盈' }], rows: [{ symbol: 'BTC', size: '6.20', value: '664,640', entry: '105,220', mark: '107,200', pnl: '12,276', stop: '103,800 / 109,500' }, { symbol: 'ETH', size: '92.00', value: '312,800', entry: '3,182', mark: '3,398', pnl: '19,872', stop: '3,050 / 3,620' }, { symbol: 'SOL', size: '1,850', value: '188,700', entry: '96.4', mark: '102.0', pnl: '10,360', stop: '91.0 / 108.0' }] },
      history: { columns: [{ key: 'time', label: '时间' }, { key: 'symbol', label: '标的' }, { key: 'action', label: '动作' }, { key: 'price', label: '价格' }, { key: 'size', label: '数量' }, { key: 'status', label: '状态' }], rows: [{ time: '06-25 11:02', symbol: 'BTC', action: '加仓', price: '106,280', size: '0.80', status: '已完成' }, { time: '06-25 10:26', symbol: 'SOL', action: '止盈挂单', price: '107.80', size: '300', status: '排队中' }] },
      fills: { columns: [{ key: 'orderId', label: '订单号' }, { key: 'symbol', label: '标的' }, { key: 'fillPrice', label: '成交价' }, { key: 'fillSize', label: '成交量' }, { key: 'fee', label: '手续费' }, { key: 'time', label: '成交时间' }], rows: [{ orderId: 'DIP-2061', symbol: 'BTC', fillPrice: '106,280', fillSize: '0.80', fee: '8.10', time: '06-25 11:02:18' }, { orderId: 'DIP-2058', symbol: 'ETH', fillPrice: '3,344', fillSize: '18.00', fee: '6.44', time: '06-25 10:04:56' }] },
      logs: { columns: [{ key: 'time', label: '时间' }, { key: 'type', label: '类别' }, { key: 'content', label: '内容' }], rows: [{ time: '06-25 11:02:18', type: '执行成功', content: 'BTC 二次加仓成交完成。' }, { time: '06-25 10:26:04', type: '挂单中', content: 'SOL 止盈单等待流动性成交。' }] },
    },
  },
};

function cloneStrategyDeskProfile(profile: StrategyDeskProfile): StrategyDeskProfile {
  return JSON.parse(JSON.stringify(profile)) as StrategyDeskProfile;
}

const crossSpreadProfile = cloneStrategyDeskProfile(baseStrategyDeskProfiles.spread);
crossSpreadProfile.key = 'crossSpread';
crossSpreadProfile.label = '跨所价差';
crossSpreadProfile.title = '跨所价差策略管理';
crossSpreadProfile.subtitle = '沿用现有价差看板模板，先完成跨所价差的损益、资金、订单三段式管理。';
crossSpreadProfile.strategyName = '黄金跨所价差组合';
crossSpreadProfile.tables.logs = {
  columns: [
    { key: 'time', label: '时间' },
    { key: 'strategy', label: '策略' },
    { key: 'direction', label: '方向' },
    { key: 'type', label: '类型' },
    { key: 'qty', label: '数量(盎司)' },
    { key: 'trigger', label: '触发价差' },
    { key: 'fill', label: '成交价差' },
    { key: 'status', label: '状态' },
    { key: 'channel', label: '渠道' },
  ],
  rows: [
    {
      time: '20:44:34',
      strategy: '黄金跨所价差',
      direction: '开多',
      type: '限价开仓',
      qty: '100.00',
      trigger: '-1.00',
      fill: '-1.10',
      status: '成功',
      channel: 'SPREAD_GOLD_001',
    },
    {
      time: '15:45:23',
      strategy: '黄金跨所价差',
      direction: '开多',
      type: '市价开仓',
      qty: '100.00',
      trigger: '-1.80',
      fill: '-1.80',
      status: '成功',
      channel: 'SPREAD_GOLD_001',
    },
    {
      time: '15:39:14',
      strategy: '黄金跨所价差',
      direction: '开空',
      type: '限价开仓',
      qty: '60.00',
      trigger: '-2.20',
      fill: '-2.24',
      status: '待确认',
      channel: 'MANUAL_DESK',
    },
  ],
};

const domesticOverseasProfile = cloneStrategyDeskProfile(baseStrategyDeskProfiles.spread);
domesticOverseasProfile.key = 'domesticOverseas';
domesticOverseasProfile.label = '海内外价差';
domesticOverseasProfile.title = '海内外价差策略管理';
domesticOverseasProfile.subtitle = '先完全复刻价差模板，后续再分化为沪金与伦敦金独立管理视图。';
domesticOverseasProfile.strategyName = '沪金 / 伦敦金海内外价差';
domesticOverseasProfile.tabs = [
  { key: 'current', label: '当前持仓' },
  { key: 'historyShfe', label: '历史订单-沪金' },
  { key: 'historyXau', label: '历史订单-伦敦金' },
  { key: 'recordShfe', label: '成交记录-沪金' },
  { key: 'recordXau', label: '成交记录-伦敦金' },
  { key: 'execution', label: '执行记录' },
];
domesticOverseasProfile.tables = {
  current: {
    columns: [
      { key: 'symbol', label: '标的' },
      { key: 'contract', label: '合约' },
      { key: 'qty', label: '数量（手）' },
      { key: 'value', label: '价值' },
      { key: 'entry', label: '入场价格' },
      { key: 'mark', label: '当前价格' },
      { key: 'unrealized', label: '未结盈亏' },
      { key: 'carry', label: '库存费' },
      { key: 'liq', label: '强平价格' },
      { key: 'stopLoss', label: '止损价格' },
      { key: 'takeProfit', label: '止盈价格' },
      { key: 'action', label: '操作' },
    ],
    rows: [
      {
        symbol: '沪金合计',
        contract: 'SHFE',
        qty: '16.00',
        value: '17,174,120.00',
        entry: '1,057.82',
        mark: '1,075.42',
        unrealized: '-939,400.00',
        carry: '--',
        liq: '--',
        stopLoss: '--',
        takeProfit: '--',
        action: '开启自动止盈',
      },
      {
        symbol: '沪金2612',
        contract: 'SHFE.au2612',
        qty: '5.00',
        value: '5,344,500.00',
        entry: '1,121.12',
        mark: '1,068.90',
        unrealized: '-261,120.00',
        carry: '--',
        liq: '--',
        stopLoss: '--',
        takeProfit: '--',
        action: '--',
      },
    ],
  },
  historyShfe: {
    columns: [
      { key: 'time', label: '时间' },
      { key: 'contract', label: '合约' },
      { key: 'side', label: '方向' },
      { key: 'offset', label: '开平' },
      { key: 'price', label: '委托价格' },
      { key: 'orderQty', label: '委托数量' },
      { key: 'fillQty', label: '成交数量' },
      { key: 'status', label: '状态' },
      { key: 'orderId', label: '订单编号' },
      { key: 'action', label: '操作' },
    ],
    rows: [
      {
        time: '2026-03-18 15:44:43',
        contract: 'SHFE.au2604',
        side: '买入',
        offset: '开仓',
        price: '市价',
        orderQty: '2',
        fillQty: '2',
        status: '全部成交',
        orderId: 'SHFE-20260318-001',
        action: '查看',
      },
    ],
  },
  historyXau: {
    columns: [
      { key: 'time', label: '时间' },
      { key: 'symbol', label: '品种' },
      { key: 'side', label: '方向' },
      { key: 'offset', label: '开平' },
      { key: 'price', label: '委托价格' },
      { key: 'orderQty', label: '委托数量' },
      { key: 'fillQty', label: '成交数量' },
      { key: 'status', label: '状态' },
      { key: 'orderId', label: '订单编号' },
      { key: 'action', label: '操作' },
    ],
    rows: [
      {
        time: '2026-03-18 15:44:45',
        symbol: 'XAUUSD',
        side: 'Sell',
        offset: 'Open',
        price: 'Market',
        orderQty: '0.64',
        fillQty: '0.64',
        status: 'Filled',
        orderId: 'MT5-20260318-641',
        action: '查看',
      },
    ],
  },
  recordShfe: {
    columns: [
      { key: 'time', label: '成交时间' },
      { key: 'contract', label: '合约' },
      { key: 'side', label: '方向' },
      { key: 'offset', label: '开平' },
      { key: 'price', label: '成交价格' },
      { key: 'qty', label: '成交数量' },
      { key: 'fee', label: '手续费' },
      { key: 'slippage', label: '滑点' },
      { key: 'tradeId', label: '成交编号' },
    ],
    rows: [
      {
        time: '2026-03-18 15:44:43',
        contract: 'SHFE.au2604',
        side: '买',
        offset: '开仓',
        price: '1058.5',
        qty: '2',
        fee: '15.2',
        slippage: '0.3',
        tradeId: 'TRD-SHFE-1001',
      },
    ],
  },
  recordXau: {
    columns: [
      { key: 'time', label: '成交时间' },
      { key: 'symbol', label: '品种' },
      { key: 'side', label: '方向' },
      { key: 'offset', label: '开平' },
      { key: 'price', label: '成交价格' },
      { key: 'qty', label: '成交数量' },
      { key: 'fee', label: '手续费' },
      { key: 'slippage', label: '滑点' },
      { key: 'tradeId', label: '成交编号' },
    ],
    rows: [
      {
        time: '2026-03-18 15:44:45',
        symbol: 'XAUUSD',
        side: 'Sell',
        offset: 'Open',
        price: '4820.01',
        qty: '0.64',
        fee: '6.4',
        slippage: '0.1',
        tradeId: 'TRD-MT5-9001',
      },
    ],
  },
  execution: {
    columns: [
      { key: 'time', label: '执行时间' },
      { key: 'strategy', label: '策略名称' },
      { key: 'actionType', label: '操作类型' },
      { key: 'shfeContract', label: '沪金合约' },
      { key: 'shfeSide', label: '沪金方向' },
      { key: 'shfeQty', label: '沪金数量' },
      { key: 'shfePrice', label: '沪金成交均价' },
      { key: 'xauSide', label: '伦敦金方向' },
      { key: 'xauQty', label: '伦敦金数量' },
      { key: 'xauPrice', label: '伦敦金成交均价' },
      { key: 'fx', label: '汇率' },
      { key: 'spread', label: '执行价差' },
      { key: 'status', label: '状态' },
      { key: 'remark', label: '备注' },
    ],
    rows: [
      {
        time: '2026-03-18 15:44:45',
        strategy: '沪金伦敦金多空策略',
        actionType: '开仓',
        shfeContract: 'SHFE.au2604',
        shfeSide: 'Buy',
        shfeQty: '2',
        shfePrice: '1058.5',
        xauSide: 'Sell',
        xauQty: '0.64',
        xauPrice: '4820.01',
        fx: '6.82',
        spread: '1.18CNY',
        status: '成功',
        remark: 'Mock 成交',
      },
    ],
  },
};
domesticOverseasProfile.tables.logs = {
  columns: [
    { key: 'time', label: '时间' },
    { key: 'type', label: '类别' },
    { key: 'content', label: '内容' },
  ],
  rows: [
    { time: '2026-03-18 15:44:45', type: '执行成功', content: '开仓成功，沪金下单量为2，伦敦金下单量为0.64。' },
    { time: '2026-03-18 15:44:45', type: '执行成功', content: 'MT5 下单成功完成，成交数量 0.64。' },
    { time: '2026-03-18 15:44:43', type: '执行完成', content: '策略开仓订单已完成，成交数量 2，总成交数量 2。' },
    { time: '2026-03-18 15:44:42', type: '执行发起', content: '发起执行策略开仓，沪金=2，伦敦金=0.64。' },
  ],
};

function makeTable(columns: { key: string; label: string }[], rows: Record<string, string>[]) {
  return { columns, rows };
}

baseStrategyDeskProfiles.funding.tabs = [
  { key: 'current', label: '当前持仓' },
  { key: 'historySpot', label: '历史订单-现货' },
  { key: 'historyPerp', label: '历史订单-合约' },
  { key: 'fillsSpot', label: '成交记录-现货' },
  { key: 'fillsPerp', label: '成交记录-合约' },
  { key: 'execution', label: '执行记录' },
];

baseStrategyDeskProfiles.funding.tables = {
  current: makeTable(
    [
      { key: 'symbol', label: '标的' },
      { key: 'leg', label: '腿类型' },
      { key: 'venue', label: '平台' },
      { key: 'position', label: '持仓数量' },
      { key: 'notional', label: '名义价值' },
      { key: 'entry', label: '入场价格' },
      { key: 'mark', label: '当前价格' },
      { key: 'funding', label: '累计资金费' },
      { key: 'unrealized', label: '未结盈亏' },
      { key: 'margin', label: '保证金占用' },
      { key: 'status', label: '状态' },
      { key: 'action', label: '操作' },
    ],
    [
      { symbol: 'BTCUSDT', leg: '现货头寸', venue: 'Binance', position: '0.5000 BTC', notional: '102,350.00 USDT', entry: '102,200.00', mark: '102,350.00', funding: '--', unrealized: '+75.00', margin: '10,250.00', status: '正常', action: '查看' },
      { symbol: 'BTCUSDT 永续', leg: '合约头寸', venue: 'Binance', position: '0.5000 BTC', notional: '102,341.20 USDT', entry: '102,212.00', mark: '102,341.20', funding: '+285.40', unrealized: '+64.60', margin: '10,250.00', status: '正常', action: '查看' },
      { symbol: 'ETHUSDT 永续', leg: '合约头寸', venue: 'OKX', position: '5.0000 ETH', notional: '16,990.00 USDT', entry: '3,405.00', mark: '3,398.00', funding: '+118.40', unrealized: '-35.00', margin: '3,100.00', status: '正常', action: '查看' },
    ],
  ),
  historySpot: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'venue', label: '平台' },
      { key: 'symbol', label: '标的' },
      { key: 'side', label: '方向' },
      { key: 'price', label: '委托价格' },
      { key: 'qty', label: '委托数量' },
      { key: 'status', label: '状态' },
      { key: 'orderId', label: '订单号' },
    ],
    [
      { time: '2026-06-25 10:24:12', venue: 'Binance', symbol: 'BTCUSDT 现货', side: '买入', price: '102,200.00', qty: '0.5000', status: '已完成', orderId: 'SPOT-1024' },
      { time: '2026-06-25 09:40:08', venue: 'OKX', symbol: 'ETHUSDT 现货', side: '买入', price: '3,401.20', qty: '5.0000', status: '已完成', orderId: 'SPOT-0940' },
    ],
  ),
  historyPerp: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'venue', label: '平台' },
      { key: 'symbol', label: '标的' },
      { key: 'side', label: '方向' },
      { key: 'price', label: '委托价格' },
      { key: 'qty', label: '委托数量' },
      { key: 'status', label: '状态' },
      { key: 'orderId', label: '订单号' },
    ],
    [
      { time: '2026-06-25 10:24:16', venue: 'Binance', symbol: 'BTCUSDT 永续', side: '卖出', price: '102,212.00', qty: '0.5000', status: '已完成', orderId: 'PERP-1024' },
      { time: '2026-06-25 09:42:18', venue: 'OKX', symbol: 'ETHUSDT 永续', side: '卖出', price: '3,405.00', qty: '5.0000', status: '已完成', orderId: 'PERP-0942' },
    ],
  ),
  fillsSpot: makeTable(
    [
      { key: 'time', label: '成交时间' },
      { key: 'venue', label: '平台' },
      { key: 'symbol', label: '标的' },
      { key: 'fillPrice', label: '成交价' },
      { key: 'fillQty', label: '成交量' },
      { key: 'fee', label: '手续费' },
      { key: 'slippage', label: '滑点' },
      { key: 'tradeId', label: '成交号' },
    ],
    [
      { time: '2026-06-25 10:24:44', venue: 'Binance', symbol: 'BTCUSDT 现货', fillPrice: '102,350.00', fillQty: '0.5000', fee: '12.40', slippage: '0.010%', tradeId: 'FILL-SPOT-8244' },
      { time: '2026-06-25 09:40:32', venue: 'OKX', symbol: 'ETHUSDT 现货', fillPrice: '3,401.20', fillQty: '5.0000', fee: '8.20', slippage: '0.014%', tradeId: 'FILL-SPOT-8242' },
    ],
  ),
  fillsPerp: makeTable(
    [
      { key: 'time', label: '成交时间' },
      { key: 'venue', label: '平台' },
      { key: 'symbol', label: '标的' },
      { key: 'fillPrice', label: '成交价' },
      { key: 'fillQty', label: '成交量' },
      { key: 'fee', label: '手续费' },
      { key: 'funding', label: '结算费率' },
      { key: 'tradeId', label: '成交号' },
    ],
    [
      { time: '2026-06-25 10:24:49', venue: 'Binance', symbol: 'BTCUSDT 永续', fillPrice: '102,341.20', fillQty: '0.5000', fee: '11.80', funding: '+0.0810%', tradeId: 'FILL-PERP-8244' },
      { time: '2026-06-25 09:42:27', venue: 'OKX', symbol: 'ETHUSDT 永续', fillPrice: '3,398.00', fillQty: '5.0000', fee: '7.90', funding: '+0.0520%', tradeId: 'FILL-PERP-8242' },
    ],
  ),
  execution: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'strategy', label: '策略' },
      { key: 'action', label: '动作' },
      { key: 'spotVenue', label: '现货平台' },
      { key: 'spotQty', label: '现货数量' },
      { key: 'perpVenue', label: '合约平台' },
      { key: 'perpQty', label: '合约数量' },
      { key: 'netCarry', label: '净Carry' },
      { key: 'status', label: '状态' },
    ],
    [
      { time: '2026-06-25 10:24:58', strategy: 'BTC 资金费率套利', action: '开仓', spotVenue: 'Binance', spotQty: '0.5000 BTC', perpVenue: 'Binance', perpQty: '0.5000 BTC', netCarry: '+22.31%', status: '成功' },
      { time: '2026-06-25 09:42:38', strategy: 'ETH 资金费率套利', action: '移仓', spotVenue: 'OKX', spotQty: '5.0000 ETH', perpVenue: 'OKX', perpQty: '5.0000 ETH', netCarry: '+18.42%', status: '成功' },
    ],
  ),
};

crossSpreadProfile.tabs = [
  { key: 'current', label: '当前持仓' },
  { key: 'historyBybit', label: '历史订单-BYBIT' },
  { key: 'historyMt5', label: '历史订单-MT5' },
  { key: 'fillsBybit', label: '成交记录-BYBIT' },
  { key: 'fillsMt5', label: '成交记录-MT5' },
  { key: 'execution', label: '执行记录' },
];

crossSpreadProfile.tables = {
  current: makeTable(
    [
      { key: 'symbol', label: '标的' },
      { key: 'leg', label: '腿' },
      { key: 'position', label: '数量(盎司)' },
      { key: 'entry', label: '入场价格' },
      { key: 'mark', label: '当前价格' },
      { key: 'spread', label: '当前价差' },
      { key: 'unrealized', label: '未结盈亏' },
      { key: 'liquidation', label: '爆仓价' },
      { key: 'status', label: '状态' },
      { key: 'action', label: '操作' },
    ],
    [
      { symbol: 'XAUTUSDT.P', leg: 'BYBIT 主腿', position: '100.00', entry: '2,331.22', mark: '2,331.12', spread: '-2.10', unrealized: '-10.00', liquidation: '2,285.00', status: '正常', action: '查看' },
      { symbol: 'XAUUSD', leg: 'MT5 对冲腿', position: '100.00', entry: '2,333.07', mark: '2,333.28', spread: '-2.10', unrealized: '0.00', liquidation: '2,382.00', status: '正常', action: '查看' },
    ],
  ),
  historyBybit: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'symbol', label: '标的' },
      { key: 'side', label: '方向' },
      { key: 'type', label: '类型' },
      { key: 'price', label: '委托价格' },
      { key: 'qty', label: '数量(盎司)' },
      { key: 'status', label: '状态' },
      { key: 'orderId', label: '订单号' },
    ],
    [
      { time: '2026-07-07 15:45:23', symbol: 'XAUTUSDT.P', side: '买入', type: '市价开仓', price: '2,331.22', qty: '100.00', status: '成功', orderId: 'BY-OPEN-154523' },
      { time: '2026-07-07 15:39:14', symbol: 'XAUTUSDT.P', side: '卖出', type: '限价开仓', price: '2,330.60', qty: '60.00', status: '待确认', orderId: 'BY-OPEN-153914' },
    ],
  ),
  historyMt5: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'symbol', label: '标的' },
      { key: 'side', label: '方向' },
      { key: 'type', label: '类型' },
      { key: 'price', label: '委托价格' },
      { key: 'qty', label: '数量(盎司)' },
      { key: 'status', label: '状态' },
      { key: 'orderId', label: '订单号' },
    ],
    [
      { time: '2026-07-07 15:45:23', symbol: 'XAUUSD', side: '卖出', type: '对冲开仓', price: '2,333.07', qty: '100.00', status: '成功', orderId: 'MT5-HEDGE-154523' },
      { time: '2026-07-07 15:39:14', symbol: 'XAUUSD', side: '买入', type: '对冲开仓', price: '2,333.26', qty: '60.00', status: '待确认', orderId: 'MT5-HEDGE-153914' },
    ],
  ),
  fillsBybit: makeTable(
    [
      { key: 'time', label: '成交时间' },
      { key: 'symbol', label: '标的' },
      { key: 'fillPrice', label: '成交价' },
      { key: 'fillQty', label: '成交量' },
      { key: 'slippage', label: '滑点' },
      { key: 'fee', label: '手续费' },
      { key: 'tradeId', label: '成交号' },
    ],
    [
      { time: '2026-07-07 15:45:24', symbol: 'XAUTUSDT.P', fillPrice: '2,331.22', fillQty: '100.00', slippage: '-0.01', fee: '8.20', tradeId: 'BY-FILL-9001' },
      { time: '2026-07-07 15:39:18', symbol: 'XAUTUSDT.P', fillPrice: '2,330.60', fillQty: '60.00', slippage: '-0.02', fee: '4.82', tradeId: 'BY-FILL-9000' },
    ],
  ),
  fillsMt5: makeTable(
    [
      { key: 'time', label: '成交时间' },
      { key: 'symbol', label: '标的' },
      { key: 'fillPrice', label: '成交价' },
      { key: 'fillQty', label: '成交量' },
      { key: 'slippage', label: '滑点' },
      { key: 'fee', label: '手续费' },
      { key: 'tradeId', label: '成交号' },
    ],
    [
      { time: '2026-07-07 15:45:25', symbol: 'XAUUSD', fillPrice: '2,333.07', fillQty: '100.00', slippage: '0.00', fee: '0.00', tradeId: 'MT5-FILL-9001' },
      { time: '2026-07-07 15:39:20', symbol: 'XAUUSD', fillPrice: '2,333.26', fillQty: '60.00', slippage: '0.01', fee: '0.00', tradeId: 'MT5-FILL-9000' },
    ],
  ),
  execution: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'strategy', label: '策略' },
      { key: 'direction', label: '方向' },
      { key: 'type', label: '类型' },
      { key: 'qty', label: '数量(盎司)' },
      { key: 'trigger', label: '触发价差' },
      { key: 'fill', label: '成交价差' },
      { key: 'status', label: '状态' },
      { key: 'channel', label: '渠道' },
    ],
    [
      { time: '20:44:34', strategy: '黄金跨所价差', direction: '开多', type: '限价开仓', qty: '100.00', trigger: '-1.00', fill: '-1.10', status: '成功', channel: 'SPREAD_GOLD_001' },
      { time: '15:45:23', strategy: '黄金跨所价差', direction: '开多', type: '市价开仓', qty: '100.00', trigger: '-1.80', fill: '-1.80', status: '成功', channel: 'SPREAD_GOLD_001' },
      { time: '15:39:14', strategy: '黄金跨所价差', direction: '开空', type: '限价开仓', qty: '60.00', trigger: '-2.20', fill: '-2.24', status: '待确认', channel: 'MANUAL_DESK' },
    ],
  ),
};

domesticOverseasProfile.tabs = [
  { key: 'current', label: '当前持仓' },
  { key: 'historyShfe', label: '历史订单-沪金' },
  { key: 'historyXau', label: '历史订单-伦敦金' },
  { key: 'fillsShfe', label: '成交记录-沪金' },
  { key: 'fillsXau', label: '成交记录-伦敦金' },
  { key: 'execution', label: '执行记录' },
];

domesticOverseasProfile.tables = {
  current: makeTable(
    [
      { key: 'symbol', label: '标的' },
      { key: 'contract', label: '合约' },
      { key: 'qty', label: '数量（手）' },
      { key: 'value', label: '价值' },
      { key: 'entry', label: '入场价格' },
      { key: 'mark', label: '当前价格' },
      { key: 'unrealized', label: '未结盈亏' },
      { key: 'carry', label: '库存费' },
      { key: 'liq', label: '强平价格' },
      { key: 'stopLoss', label: '止损价格' },
      { key: 'takeProfit', label: '止盈价格' },
      { key: 'action', label: '操作' },
    ],
    [
      { symbol: '沪金合计', contract: 'SHFE', qty: '16.00', value: '17,174,120.00', entry: '1,057.82', mark: '1,075.42', unrealized: '-939,400.00', carry: '--', liq: '--', stopLoss: '--', takeProfit: '--', action: '开启自动止盈' },
      { symbol: '沪金2612', contract: 'SHFE.au2612', qty: '5.00', value: '5,344,500.00', entry: '1,121.12', mark: '1,068.90', unrealized: '-261,120.00', carry: '--', liq: '--', stopLoss: '--', takeProfit: '--', action: '--' },
      { symbol: '伦敦金', contract: 'XAUUSD', qty: '0.64', value: '1,324,857.38', entry: '4,820.01', mark: '4,820.01', unrealized: '0.00', carry: '--', liq: '--', stopLoss: '--', takeProfit: '--', action: '--' },
    ],
  ),
  historyShfe: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'contract', label: '合约' },
      { key: 'side', label: '方向' },
      { key: 'offset', label: '开平' },
      { key: 'price', label: '委托价格' },
      { key: 'orderQty', label: '委托数量' },
      { key: 'fillQty', label: '成交数量' },
      { key: 'status', label: '状态' },
      { key: 'orderId', label: '订单编号' },
    ],
    [
      { time: '2026-03-18 15:44:43', contract: 'SHFE.au2604', side: '买入', offset: '开仓', price: '市价', orderQty: '2', fillQty: '2', status: '全部成交', orderId: 'SHFE-20260318-001' },
    ],
  ),
  historyXau: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'symbol', label: '品种' },
      { key: 'side', label: '方向' },
      { key: 'offset', label: '开平' },
      { key: 'price', label: '委托价格' },
      { key: 'orderQty', label: '委托数量' },
      { key: 'fillQty', label: '成交数量' },
      { key: 'status', label: '状态' },
      { key: 'orderId', label: '订单编号' },
    ],
    [
      { time: '2026-03-18 15:44:45', symbol: 'XAUUSD', side: 'Sell', offset: 'Open', price: 'Market', orderQty: '0.64', fillQty: '0.64', status: 'Filled', orderId: 'MT5-20260318-641' },
    ],
  ),
  fillsShfe: makeTable(
    [
      { key: 'time', label: '成交时间' },
      { key: 'contract', label: '合约' },
      { key: 'side', label: '方向' },
      { key: 'offset', label: '开平' },
      { key: 'price', label: '成交价格' },
      { key: 'qty', label: '成交数量' },
      { key: 'fee', label: '手续费' },
      { key: 'slippage', label: '滑点' },
      { key: 'tradeId', label: '成交编号' },
    ],
    [
      { time: '2026-03-18 15:44:43', contract: 'SHFE.au2604', side: '买入', offset: '开仓', price: '1058.5', qty: '2', fee: '15.2', slippage: '0.3', tradeId: 'TRD-SHFE-1001' },
    ],
  ),
  fillsXau: makeTable(
    [
      { key: 'time', label: '成交时间' },
      { key: 'symbol', label: '品种' },
      { key: 'side', label: '方向' },
      { key: 'offset', label: '开平' },
      { key: 'price', label: '成交价格' },
      { key: 'qty', label: '成交数量' },
      { key: 'fee', label: '手续费' },
      { key: 'slippage', label: '滑点' },
      { key: 'tradeId', label: '成交编号' },
    ],
    [
      { time: '2026-03-18 15:44:45', symbol: 'XAUUSD', side: 'Sell', offset: 'Open', price: '4820.01', qty: '0.64', fee: '6.4', slippage: '0.1', tradeId: 'TRD-MT5-9001' },
    ],
  ),
  execution: makeTable(
    [
      { key: 'time', label: '执行时间' },
      { key: 'strategy', label: '策略名称' },
      { key: 'actionType', label: '操作类型' },
      { key: 'shfeContract', label: '沪金合约' },
      { key: 'shfeSide', label: '沪金方向' },
      { key: 'shfeQty', label: '沪金数量' },
      { key: 'shfePrice', label: '沪金成交均价' },
      { key: 'xauSide', label: '伦敦金方向' },
      { key: 'xauQty', label: '伦敦金数量' },
      { key: 'xauPrice', label: '伦敦金成交均价' },
      { key: 'fx', label: '汇率' },
      { key: 'spread', label: '执行价差' },
      { key: 'status', label: '状态' },
      { key: 'remark', label: '备注' },
    ],
    [
      { time: '2026-03-18 15:44:45', strategy: '沪金伦敦金多空策略', actionType: '开仓', shfeContract: 'SHFE.au2604', shfeSide: 'Buy', shfeQty: '2', shfePrice: '1058.5', xauSide: 'Sell', xauQty: '0.64', xauPrice: '4820.01', fx: '6.82', spread: '1.18CNY', status: '成功', remark: 'Mock 成交' },
    ],
  ),
};

baseStrategyDeskProfiles.dip.tabs = [
  { key: 'current', label: '当前持仓' },
  { key: 'history', label: '历史订单' },
  { key: 'fills', label: '成交记录' },
  { key: 'execution', label: '执行记录' },
];

baseStrategyDeskProfiles.dip.tables = {
  current: makeTable(
    [
      { key: 'symbol', label: '标的' },
      { key: 'direction', label: '方向' },
      { key: 'size', label: '数量' },
      { key: 'value', label: '市值' },
      { key: 'entry', label: '持仓均价' },
      { key: 'mark', label: '当前价格' },
      { key: 'pnl', label: '浮盈' },
      { key: 'stop', label: '止损/止盈' },
      { key: 'status', label: '状态' },
      { key: 'action', label: '操作' },
    ],
    [
      { symbol: 'BTC', direction: '多头', size: '6.20', value: '664,640', entry: '105,220', mark: '107,200', pnl: '+12,276', stop: '103,800 / 109,500', status: '正常', action: '查看' },
      { symbol: 'ETH', direction: '多头', size: '92.00', value: '312,800', entry: '3,182', mark: '3,398', pnl: '+19,872', stop: '3,050 / 3,620', status: '正常', action: '查看' },
      { symbol: 'SOL', direction: '多头', size: '1,850', value: '188,700', entry: '96.4', mark: '102.0', pnl: '+10,360', stop: '91.0 / 108.0', status: '排队中', action: '查看' },
    ],
  ),
  history: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'symbol', label: '标的' },
      { key: 'action', label: '动作' },
      { key: 'price', label: '价格' },
      { key: 'size', label: '数量' },
      { key: 'status', label: '状态' },
      { key: 'orderId', label: '订单号' },
    ],
    [
      { time: '06-25 11:02', symbol: 'BTC', action: '加仓', price: '106,280', size: '0.80', status: '已完成', orderId: 'DIP-2061' },
      { time: '06-25 10:26', symbol: 'SOL', action: '止盈挂单', price: '107.80', size: '300', status: '排队中', orderId: 'DIP-2060' },
    ],
  ),
  fills: makeTable(
    [
      { key: 'time', label: '成交时间' },
      { key: 'symbol', label: '标的' },
      { key: 'fillPrice', label: '成交价' },
      { key: 'fillSize', label: '成交量' },
      { key: 'fee', label: '手续费' },
      { key: 'slippage', label: '滑点' },
      { key: 'tradeId', label: '成交号' },
    ],
    [
      { time: '06-25 11:02:18', symbol: 'BTC', fillPrice: '106,280', fillSize: '0.80', fee: '8.10', slippage: '0.012%', tradeId: 'DIP-FILL-2061' },
      { time: '06-25 10:04:56', symbol: 'ETH', fillPrice: '3,344', fillSize: '18.00', fee: '6.44', slippage: '0.018%', tradeId: 'DIP-FILL-2058' },
    ],
  ),
  execution: makeTable(
    [
      { key: 'time', label: '时间' },
      { key: 'strategy', label: '策略' },
      { key: 'symbol', label: '标的' },
      { key: 'action', label: '动作' },
      { key: 'size', label: '数量' },
      { key: 'price', label: '执行价格' },
      { key: 'risk', label: '风险动作' },
      { key: 'status', label: '状态' },
    ],
    [
      { time: '06-25 11:02:18', strategy: '波段抄底', symbol: 'BTC', action: '加仓', size: '0.80', price: '106,280', risk: '同步上调止盈', status: '成功' },
      { time: '06-25 10:26:04', strategy: '波段抄底', symbol: 'SOL', action: '止盈挂单', size: '300', price: '107.80', risk: '挂保护单', status: '排队中' },
    ],
  ),
};

export const strategyDeskProfiles: Record<StrategyDeskKey, StrategyDeskProfile> = {
  ...baseStrategyDeskProfiles,
  crossSpread: crossSpreadProfile,
  domesticOverseas: domesticOverseasProfile,
  shortLineTraderL: (() => {
    const profile = cloneStrategyDeskProfile(domesticOverseasProfile);
    profile.key = 'shortLineTraderL';
    profile.label = '短线交易员L';
    profile.title = '短线交易员L策略管理';
    profile.subtitle = '聚焦股指期货、黄金、币的日内风险交易，先统一损益、资金与订单三页语义，再逐步细化到独立工作台。';
    profile.strategyName = '短线交易员L';
    profile.filters = ['股指期货', '黄金', '币', '日内', '止盈止损'];
    profile.overview = {
      periods: fundingOverview.periods,
      datasets: {
        day: makeOverviewDataset({
          periodLabel: '2026年07月12日',
          dateLabel: '2026-07-12 09:00 - 2026-07-12 15:00',
          totalFund: '6,842,190.50 CNY',
          xLabels: ['09:00', '09:30', '10:00', '10:30', '11:00', '13:00', '13:30', '14:00', '14:30', '15:00'],
          barValues: [22, 46, -18, 38, 54, 61, -12, 28, 44, 18],
          lineValues: [4, 12, 8, 16, 24, 30, 26, 31, 38, 42],
          statCards: [
            { label: '日内净收益', value: '+42,680', subValue: '股指 + 黄金主导', tone: 'positive' },
            { label: '已实现收益', value: '+31,240', subValue: '平仓兑现部分', tone: 'positive' },
            { label: '浮动盈亏', value: '+11,440', subValue: '尾盘仍有持仓', tone: 'positive' },
            { label: '胜率', value: '63.6%', subValue: '当日 11 笔有效单', tone: 'positive' },
            { label: '最大回撤', value: '-12,360', subValue: '10:05 附近回撤', tone: 'negative' },
            { label: '风险状态', value: '正常', subValue: '未触发强平或熔断保护', tone: 'positive' },
          ],
          stateCounts: [
            { label: '新开仓', count: '7', subLabel: '总计' },
            { label: '已平仓', count: '5', subLabel: '总计' },
            { label: '持仓中', count: '3', subLabel: '总计' },
          ],
          profitRows: [
            { type: '股指期货', strategyCount: '3', pnl: '+21,480', ratio: '50.3%', tone: 'positive' },
            { type: '黄金', strategyCount: '4', pnl: '+12,940', ratio: '30.3%', tone: 'positive' },
            { type: '币', strategyCount: '4', pnl: '+8,260', ratio: '19.4%', tone: 'positive' },
          ],
          lossRows: [
            { type: '止损单', strategyCount: '2', pnl: '-7,820', ratio: '63.3%', tone: 'negative' },
            { type: '追单滑点', strategyCount: '2', pnl: '-4,540', ratio: '36.7%', tone: 'negative' },
          ],
          syncRows: [
            { category: '成交同步', status: '已完成', message: '股指、黄金、币的成交回报已汇总。', time: '15:02:18', tone: 'positive' },
            { category: '止损检查', status: '已完成', message: '全部保护单状态已刷新。', time: '15:01:42', tone: 'positive' },
            { category: '风险复核', status: '监控中', message: 'BTC 余仓继续观察，不留过夜。', time: '14:58:07', tone: 'neutral' },
          ],
        }),
        week: makeOverviewDataset({
          periodLabel: '2026 第28周',
          dateLabel: '2026-07-08 - 2026-07-12',
          totalFund: '6,842,190.50 CNY',
          xLabels: ['07-08', '07-09', '07-10', '07-11', '07-12'],
          barValues: [18, -12, 26, 34, 42],
          lineValues: [6, 4, 12, 18, 24],
          statCards: [
            { label: '周度净收益', value: '+118,420', subValue: '周内累计', tone: 'positive' },
            { label: '已实现收益', value: '+94,180', subValue: '主动止盈较多', tone: 'positive' },
            { label: '浮动盈亏', value: '+24,240', subValue: '剩余轻仓', tone: 'positive' },
            { label: '胜率', value: '61.2%', subValue: '周内 49 笔有效单', tone: 'positive' },
            { label: '最大回撤', value: '-38,650', subValue: '周内最大单日回撤', tone: 'negative' },
            { label: '风险状态', value: '正常', subValue: '风控边界内', tone: 'positive' },
          ],
          stateCounts: [
            { label: '新开仓', count: '31', subLabel: '总计' },
            { label: '已平仓', count: '28', subLabel: '总计' },
            { label: '持仓中', count: '4', subLabel: '总计' },
          ],
          profitRows: [
            { type: '股指期货', strategyCount: '12', pnl: '+58,320', ratio: '49.2%', tone: 'positive' },
            { type: '黄金', strategyCount: '15', pnl: '+37,860', ratio: '32.0%', tone: 'positive' },
            { type: '币', strategyCount: '22', pnl: '+22,240', ratio: '18.8%', tone: 'positive' },
          ],
          lossRows: [
            { type: '止损单', strategyCount: '9', pnl: '-22,160', ratio: '57.3%', tone: 'negative' },
            { type: '滑点与手续费', strategyCount: '12', pnl: '-16,490', ratio: '42.7%', tone: 'negative' },
          ],
          syncRows: [
            { category: '成交同步', status: '已完成', message: '周内成交已完成汇总。', time: '15:02:18', tone: 'positive' },
            { category: '止损检查', status: '已完成', message: '全部保护单状态已刷新。', time: '15:01:42', tone: 'positive' },
            { category: '风险复核', status: '监控中', message: '周内最大回撤仍在容忍区间。', time: '14:58:07', tone: 'neutral' },
          ],
        }),
        month: makeOverviewDataset({
          periodLabel: '2026年07月',
          dateLabel: '2026-07-01 - 2026-07-12',
          totalFund: '6,842,190.50 CNY',
          xLabels: ['07-01', '07-03', '07-05', '07-07', '07-09', '07-11', '07-12'],
          barValues: [12, 18, -14, 26, 34, 28, 42],
          lineValues: [4, 8, 6, 10, 16, 21, 27],
          statCards: [
            { label: '月内净收益', value: '+236,580', subValue: '月内累计', tone: 'positive' },
            { label: '已实现收益', value: '+194,760', subValue: '平仓兑现', tone: 'positive' },
            { label: '浮动盈亏', value: '+41,820', subValue: '轻仓留存', tone: 'positive' },
            { label: '胜率', value: '59.8%', subValue: '月内 118 笔有效单', tone: 'positive' },
            { label: '最大回撤', value: '-86,240', subValue: '月内单日回撤', tone: 'negative' },
            { label: '风险状态', value: '正常', subValue: '无重大异常', tone: 'positive' },
          ],
          stateCounts: [
            { label: '新开仓', count: '76', subLabel: '总计' },
            { label: '已平仓', count: '69', subLabel: '总计' },
            { label: '持仓中', count: '6', subLabel: '总计' },
          ],
          profitRows: [
            { type: '股指期货', strategyCount: '26', pnl: '+116,340', ratio: '49.2%', tone: 'positive' },
            { type: '黄金', strategyCount: '34', pnl: '+73,820', ratio: '31.2%', tone: 'positive' },
            { type: '币', strategyCount: '58', pnl: '+46,420', ratio: '19.6%', tone: 'positive' },
          ],
          lossRows: [
            { type: '止损单', strategyCount: '22', pnl: '-46,080', ratio: '53.4%', tone: 'negative' },
            { type: '滑点与手续费', strategyCount: '31', pnl: '-40,160', ratio: '46.6%', tone: 'negative' },
          ],
          syncRows: [
            { category: '成交同步', status: '已完成', message: '月内成交已完成汇总。', time: '15:02:18', tone: 'positive' },
            { category: '止损检查', status: '已完成', message: '全部保护单状态已刷新。', time: '15:01:42', tone: 'positive' },
            { category: '风险复核', status: '监控中', message: '月内风险曲线稳定。', time: '14:58:07', tone: 'neutral' },
          ],
        }),
        custom: makeOverviewDataset({
          periodLabel: '自定义窗口',
          dateLabel: '2026-07-10 - 2026-07-12',
          totalFund: '6,842,190.50 CNY',
          xLabels: ['07-10', '07-11', '07-12'],
          barValues: [26, 34, 42],
          lineValues: [8, 16, 24],
          statCards: [
            { label: '窗口净收益', value: '+102,480', subValue: '近三日累计', tone: 'positive' },
            { label: '已实现收益', value: '+83,960', subValue: '平仓兑现', tone: 'positive' },
            { label: '浮动盈亏', value: '+18,520', subValue: '尾盘余仓', tone: 'positive' },
            { label: '胜率', value: '62.5%', subValue: '近三日 32 笔有效单', tone: 'positive' },
            { label: '最大回撤', value: '-24,280', subValue: '窗口内回撤', tone: 'negative' },
            { label: '风险状态', value: '正常', subValue: '未触发熔断保护', tone: 'positive' },
          ],
          stateCounts: [
            { label: '新开仓', count: '19', subLabel: '总计' },
            { label: '已平仓', count: '16', subLabel: '总计' },
            { label: '持仓中', count: '3', subLabel: '总计' },
          ],
          profitRows: [
            { type: '股指期货', strategyCount: '6', pnl: '+46,220', ratio: '45.1%', tone: 'positive' },
            { type: '黄金', strategyCount: '8', pnl: '+33,760', ratio: '32.9%', tone: 'positive' },
            { type: '币', strategyCount: '18', pnl: '+22,500', ratio: '22.0%', tone: 'positive' },
          ],
          lossRows: [
            { type: '止损单', strategyCount: '5', pnl: '-13,480', ratio: '55.5%', tone: 'negative' },
            { type: '滑点与手续费', strategyCount: '8', pnl: '-10,800', ratio: '44.5%', tone: 'negative' },
          ],
          syncRows: [
            { category: '成交同步', status: '已完成', message: '窗口内成交已完成汇总。', time: '15:02:18', tone: 'positive' },
            { category: '止损检查', status: '已完成', message: '全部保护单状态已刷新。', time: '15:01:42', tone: 'positive' },
            { category: '风险复核', status: '监控中', message: 'BTC 余仓继续观察，不留过夜。', time: '14:58:07', tone: 'neutral' },
          ],
        }),
      },
    };
    profile.detail = {
      title: '短线交易员L · 日内交易快照',
      status: '运行中',
      actions: ['减仓', '平仓', '止盈调整', '回补快照'],
      metrics: [
        { label: '当日交易数', value: '11', tone: 'neutral' },
        { label: '当日净收益', value: '+42,680', tone: 'positive' },
        { label: '已实现收益', value: '+31,240', tone: 'positive' },
        { label: '浮动盈亏', value: '+11,440', tone: 'positive' },
        { label: '最大回撤', value: '-12,360', tone: 'negative' },
        { label: '保护单覆盖', value: '73%', tone: 'positive' },
      ],
      legs: [
        {
          title: '股指期货组',
          market: 'CFFEX / 日内',
          symbol: 'IF2609 / IC2609',
          actions: ['查看持仓', '收紧止损', '平掉余仓'],
          rows: [
            { label: '主方向', value: '多头' },
            { label: '开仓窗口', value: '09:32 - 10:08' },
            { label: '已实现收益', value: '+21,480', tone: 'positive' },
            { label: '浮动盈亏', value: '+2,880', tone: 'positive' },
            { label: '当日回撤', value: '-5,120', tone: 'negative' },
            { label: '保护状态', value: '止损已挂出', tone: 'positive' },
          ],
        },
        {
          title: '黄金组',
          market: 'SHFE / XAUUSD',
          symbol: 'AU2510 / XAUUSD',
          actions: ['查看持仓', '止盈调整', '手动平仓'],
          rows: [
            { label: '主方向', value: '空头' },
            { label: '开仓窗口', value: '10:16 - 10:44' },
            { label: '已实现收益', value: '+12,940', tone: 'positive' },
            { label: '浮动盈亏', value: '+1,260', tone: 'positive' },
            { label: '当日回撤', value: '-3,640', tone: 'negative' },
            { label: '保护状态', value: '止盈单待优化', tone: 'neutral' },
          ],
        },
        {
          title: '币组',
          market: 'Binance / Bybit',
          symbol: 'BTCUSDT / ETHUSDT / SOLUSDT',
          actions: ['查看持仓', '撤单重挂', '减小仓位'],
          rows: [
            { label: '主方向', value: '突破追单' },
            { label: '开仓窗口', value: '13:05 - 14:12' },
            { label: '已实现收益', value: '+8,260', tone: 'positive' },
            { label: '浮动盈亏', value: '-880', tone: 'negative' },
            { label: '当日回撤', value: '-3,600', tone: 'negative' },
            { label: '保护状态', value: '余仓继续观察', tone: 'neutral' },
          ],
        },
      ],
      exposureRows: [
        { label: '股指期货名义敞口', value: '1,860,000 CNY' },
        { label: '黄金名义敞口', value: '920,000 CNY' },
        { label: '币名义敞口', value: '510,000 CNY' },
        { label: '隔夜敞口', value: '0', tone: 'positive' },
      ],
      tabs: [
        { key: 'records', label: '当日成交' },
        { key: 'riskFlow', label: '风控动作' },
        { key: 'timeline', label: '交易时间轴' },
      ],
      tabTables: {
        records: {
          columns: [
            { key: 'market', label: '市场' },
            { key: 'symbol', label: '品种' },
            { key: 'side', label: '方向' },
            { key: 'price', label: '成交价' },
            { key: 'qty', label: '数量' },
            { key: 'time', label: '成交时间' },
          ],
          rows: [
            { market: '股指期货', symbol: 'IF2609', side: '买入', price: '4,012.6', qty: '4', time: '2026-07-12 09:34:19' },
            { market: '黄金', symbol: 'XAUUSD', side: '卖出', price: '2,364.2', qty: '1.50', time: '2026-07-12 10:16:45' },
            { market: '币', symbol: 'BTCUSDT', side: '买入', price: '108,438', qty: '0.30', time: '2026-07-12 13:05:10' },
          ],
        },
        riskFlow: {
          columns: [
            { key: 'time', label: '时间' },
            { key: 'symbol', label: '品种' },
            { key: 'event', label: '风险动作' },
            { key: 'remark', label: '说明' },
          ],
          rows: [
            { time: '2026-07-12 09:36:08', symbol: 'IF2609', event: '挂止损', remark: '开仓后同步挂保护止损。' },
            { time: '2026-07-12 10:18:44', symbol: 'XAUUSD', event: '撤止盈单', remark: '回撤未到目标位，改为手动平仓。' },
            { time: '2026-07-12 13:12:33', symbol: 'BTCUSDT', event: '减小仓位', remark: '波动加大，先减半。' },
          ],
        },
        timeline: {
          columns: [
            { key: 'time', label: '时间' },
            { key: 'event', label: '事件' },
            { key: 'remark', label: '说明' },
          ],
          rows: [
            { time: '2026-07-12 09:34:19', event: '股指开仓', remark: '开盘二次突破，按计划开仓。' },
            { time: '2026-07-12 10:16:45', event: '黄金开仓', remark: '日内冲高转弱，切入空头。' },
            { time: '2026-07-12 13:05:10', event: 'BTC 追单', remark: '放量突破后跟进。' },
          ],
        },
      },
    };
    profile.kpis = [
      { label: '账户净值', value: '6,842,190.50', unit: 'CNY', note: '短线交易总账户', tone: 'neutral' },
      { label: '可用资金', value: '4,118,240.60', unit: 'CNY', note: '可继续支持日内调仓', tone: 'positive' },
      { label: '保证金占用', value: '1,862,420.30', unit: 'CNY', note: '股指期货与黄金占用为主', tone: 'neutral' },
      { label: '当日净收益', value: '+42,680', unit: 'CNY', note: '日内累计', tone: 'positive' },
      { label: '风险等级', value: '中低', note: '距离风控阈值仍有缓冲', tone: 'positive' },
      { label: '隔夜仓位', value: '0%', note: '当前目标不留隔夜', tone: 'positive' },
    ];
    profile.gauges = [
      { label: '保证金使用', value: '27%', subValue: '当前保证金使用率', progress: 27, leftLabel: '已占用', rightLabel: '可用', leftColor: '#2f80ed', rightColor: '#94a3b8' },
      { label: '风险缓冲', value: '74%', subValue: '距离日内风控线剩余空间', progress: 74, leftLabel: '缓冲', rightLabel: '已用', leftColor: '#22a06b', rightColor: '#d74d4d' },
    ];
    profile.accountBreakdown = [
      { label: '股指期货账户', value: '3,120,000 CNY', note: '主交易账户，日内占用最高', tone: 'neutral' },
      { label: '黄金账户', value: '1,840,000 CNY', note: '兼顾沪金与外盘金', tone: 'neutral' },
      { label: '币账户', value: '1,120,000 CNY', note: '弹性高，单笔仓位受控', tone: 'neutral' },
      { label: '可用保证金', value: '4,118,240.60 CNY', note: '支持继续调仓', tone: 'positive' },
      { label: '风控预警线', value: '55%', note: '当前使用率明显低于阈值', tone: 'positive' },
      { label: '保护单覆盖', value: '73%', note: '仍需继续补齐', tone: 'negative' },
    ];
    profile.executionMetrics = [
      { label: '可用资金率', before: '64%', after: '60%', tone: 'neutral' },
      { label: '单品种集中度', before: '38%', after: '34%', tone: 'positive' },
      { label: '保护单覆盖', before: '68%', after: '73%', tone: 'positive' },
    ];
    profile.logs = [
      { time: '2026-07-12 13:12:33', text: 'BTC 追单后波动加大，已先减半。', tone: 'neutral' },
      { time: '2026-07-12 10:18:44', text: '黄金止盈单撤回，改为手动平仓方案。', tone: 'neutral' },
      { time: '2026-07-12 09:36:08', text: 'IF2609 保护止损已同步挂出。', tone: 'positive' },
    ];
    profile.curves = [
      { title: '日内累计收益', amount: '+42,680', unit: 'CNY', tone: 'positive', points: [{ date: '09:00', value: 4 }, { date: '09:30', value: 12 }, { date: '10:00', value: 8 }, { date: '10:30', value: 16 }, { date: '11:00', value: 24 }, { date: '13:00', value: 30 }, { date: '13:30', value: 26 }, { date: '14:00', value: 31 }, { date: '14:30', value: 38 }, { date: '15:00', value: 42 }] },
      { title: '已实现收益', amount: '+31,240', unit: 'CNY', tone: 'positive', points: [{ date: '09:00', value: 2 }, { date: '09:30', value: 8 }, { date: '10:00', value: 6 }, { date: '10:30', value: 12 }, { date: '11:00', value: 18 }, { date: '13:00', value: 22 }, { date: '13:30', value: 23 }, { date: '14:00', value: 26 }, { date: '14:30', value: 29 }, { date: '15:00', value: 31 }] },
      { title: '日内回撤', amount: '-12,360', unit: 'CNY', tone: 'negative', points: [{ date: '09:00', value: -1 }, { date: '09:30', value: -2 }, { date: '10:00', value: -6 }, { date: '10:30', value: -4 }, { date: '11:00', value: -3 }, { date: '13:00', value: -5 }, { date: '13:30', value: -8 }, { date: '14:00', value: -6 }, { date: '14:30', value: -4 }, { date: '15:00', value: -3 }] },
    ];
    profile.tabs = [
      { key: 'current', label: '当前持仓' },
      { key: 'history', label: '历史订单' },
      { key: 'fills', label: '成交记录' },
      { key: 'execution', label: '执行记录' },
    ];
    profile.tables = {
      current: makeTable(
        [
          { key: 'symbol', label: '品种' },
          { key: 'market', label: '市场' },
          { key: 'direction', label: '方向' },
          { key: 'entryType', label: '开仓类型' },
          { key: 'entryTime', label: '开仓时间' },
          { key: 'entryPrice', label: '开仓价' },
          { key: 'markPrice', label: '当前价' },
          { key: 'pnl', label: '浮盈浮亏' },
          { key: 'stopBand', label: '止盈/止损' },
          { key: 'status', label: '订单状态' },
        ],
        [
          { symbol: 'IF2609', market: '股指期货', direction: '多头', entryType: '信号开仓', entryTime: '2026-07-12 09:34:18', entryPrice: '4,012.4', markPrice: '4,026.8', pnl: '+2,880', stopBand: '4,038 / 3,998', status: '已提交' },
          { symbol: 'XAUUSD', market: '黄金', direction: '空头', entryType: '手动开仓', entryTime: '2026-07-12 10:16:42', entryPrice: '2,364.2', markPrice: '2,357.9', pnl: '+1,260', stopBand: '2,352 / 2,370', status: '部分成交' },
          { symbol: 'BTCUSDT', market: '币', direction: '多头', entryType: '突破追单', entryTime: '2026-07-12 13:05:09', entryPrice: '108,420', markPrice: '107,980', pnl: '-880', stopBand: '109,600 / 107,600', status: '已提交' },
        ],
      ),
      history: makeTable(
        [
          { key: 'time', label: '下单时间' },
          { key: 'symbol', label: '品种' },
          { key: 'market', label: '市场' },
          { key: 'direction', label: '方向' },
          { key: 'offset', label: '开仓/平仓' },
          { key: 'orderType', label: '委托类型' },
          { key: 'price', label: '委托价格' },
          { key: 'qty', label: '委托数量' },
          { key: 'status', label: '订单状态' },
          { key: 'orderId', label: '订单号' },
        ],
        [
          { time: '2026-07-12 13:05:09', symbol: 'BTCUSDT', market: '币', direction: '买入', offset: '开仓', orderType: '市价单', price: '108,420', qty: '0.50', status: '已提交', orderId: 'STL-130509' },
          { time: '2026-07-12 10:18:44', symbol: 'XAUUSD', market: '黄金', direction: '买入', offset: '平仓', orderType: '止盈单', price: '2,352.0', qty: '2.00', status: '已撤单', orderId: 'STL-101844' },
          { time: '2026-07-12 09:34:18', symbol: 'IF2609', market: '股指期货', direction: '买入', offset: '开仓', orderType: '限价单', price: '4,012.4', qty: '4', status: '全部成交', orderId: 'STL-093418' },
          { time: '2026-07-12 09:11:06', symbol: 'AU2510', market: '黄金', direction: '卖出', offset: '开仓', orderType: '条件单', price: '768.3', qty: '3', status: '已失败', orderId: 'STL-091106' },
        ],
      ),
      fills: makeTable(
        [
          { key: 'time', label: '成交时间' },
          { key: 'symbol', label: '品种' },
          { key: 'market', label: '市场' },
          { key: 'direction', label: '方向' },
          { key: 'offset', label: '开仓/平仓' },
          { key: 'fillPrice', label: '成交价' },
          { key: 'fillQty', label: '成交量' },
          { key: 'amount', label: '成交金额' },
          { key: 'fee', label: '手续费' },
          { key: 'status', label: '订单状态' },
        ],
        [
          { time: '2026-07-12 13:05:10', symbol: 'BTCUSDT', market: '币', direction: '买入', offset: '开仓', fillPrice: '108,438', fillQty: '0.30', amount: '32,531.40', fee: '9.76', status: '部分成交' },
          { time: '2026-07-12 10:16:45', symbol: 'XAUUSD', market: '黄金', direction: '卖出', offset: '开仓', fillPrice: '2,364.2', fillQty: '1.50', amount: '3,546.30', fee: '5.20', status: '全部成交' },
          { time: '2026-07-12 09:34:19', symbol: 'IF2609', market: '股指期货', direction: '买入', offset: '开仓', fillPrice: '4,012.6', fillQty: '4', amount: '802,520', fee: '32.00', status: '全部成交' },
        ],
      ),
      execution: makeTable(
        [
          { key: 'time', label: '执行时间' },
          { key: 'symbol', label: '品种' },
          { key: 'market', label: '市场' },
          { key: 'action', label: '执行动作' },
          { key: 'trigger', label: '触发原因' },
          { key: 'price', label: '执行价格' },
          { key: 'qty', label: '数量' },
          { key: 'status', label: '订单状态' },
          { key: 'remark', label: '备注' },
        ],
        [
          { time: '2026-07-12 13:05:10', symbol: 'BTCUSDT', market: '币', action: '突破追单', trigger: '盘中放量上破', price: '108,438', qty: '0.30', status: '部分成交', remark: '剩余数量继续排队' },
          { time: '2026-07-12 10:18:44', symbol: 'XAUUSD', market: '黄金', action: '止盈撤单', trigger: '回撤未到止盈位', price: '2,352.0', qty: '2.00', status: '已撤单', remark: '改用手动平仓' },
          { time: '2026-07-12 09:34:19', symbol: 'IF2609', market: '股指期货', action: '信号开仓', trigger: '开盘二次突破', price: '4,012.6', qty: '4', status: '全部成交', remark: '已同步挂出保护止损' },
          { time: '2026-07-12 09:11:08', symbol: 'AU2510', market: '黄金', action: '条件单触发', trigger: '早盘弱势破位', price: '768.3', qty: '3', status: '已失败', remark: '交易时段限制，需改到主力合约' },
        ],
      ),
    };
    return profile;
  })(),
};
