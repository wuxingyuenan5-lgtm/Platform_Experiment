import type { StrategyDeskKey } from './types';

type Tone = 'positive' | 'negative' | 'neutral';

export interface StrategyPnlAttributionItem {
  label: string;
  value: string;
  ratio: string;
  tone?: Tone;
}

export interface StrategyPnlProfile {
  title: string;
  totalFund: string;
  period: string;
  xLabels: string[];
  dailyReturns: number[];
  netValues: number[];
  metrics: StrategyPnlAttributionItem[];
  attributions: StrategyPnlAttributionItem[];
  breakdownSeries: Array<{
    name: string;
    color: string;
    data: number[];
  }>;
  legSnapshots?: Array<{
    title: string;
    venue: string;
    symbol: string;
    rows: Array<{
      label: string;
      value: string;
      tone?: Tone;
    }>;
  }>;
  detailCurves: Array<{
    title: string;
    value: string;
    tone?: Tone;
    data: number[];
  }>;
}

const labels = ['06-19', '06-20', '06-21', '06-22', '06-23', '06-24', '06-25'];

export const strategyPnlProfiles = {
  funding: {
    title: '资费套利损益总览',
    totalFund: '2,984,316.97 USD',
    period: '2026-06-19 - 2026-06-25',
    xLabels: labels,
    dailyReturns: [42, -16, 54, 61, 69, 82, 96],
    netValues: [1.0, 1.006, 1.011, 1.018, 1.026, 1.031, 1.038],
    metrics: [
      { label: '累计总损益', value: '+511,986.31', ratio: '+11.37%', tone: 'positive' },
      { label: '持仓损益', value: '+82,360', ratio: '+24.1%', tone: 'positive' },
      { label: '过去24H盈亏', value: '-32.16', ratio: '-0.01%', tone: 'negative' },
      { label: '过去7天盈亏', value: '+8,214.22', ratio: '+0.18%', tone: 'positive' },
    ],
    attributions: [
      { label: '资费收益', value: '+142,680', ratio: '+41.8%', tone: 'positive' },
      { label: '基差收益', value: '+96,420', ratio: '+28.2%', tone: 'positive' },
      { label: '现货附加收益', value: '+18,640', ratio: '+5.5%', tone: 'positive' },
      { label: '现货借贷成本', value: '-24,180', ratio: '-7.1%', tone: 'negative' },
      { label: '30天内最大回撤', value: '-1.10', ratio: '-1.10%', tone: 'negative' },
      { label: '累计交易成本', value: '-11,420', ratio: '-3.3%', tone: 'negative' },
      { label: '执行偏差', value: '-4,280', ratio: '-1.3%', tone: 'negative' },
    ],
    breakdownSeries: [
      { name: '净收益', color: '#3498db', data: [0, 36, 78, 126, 184, 238, 302] },
      { name: '合约盈亏', color: '#55d6d9', data: [0, -680, -1840, -4200, -3960, -2600, 2860] },
      { name: '现货盈亏', color: '#f4bf45', data: [0, 920, 2450, 3840, 3960, 4020, -2680] },
      { name: '费率累计', color: '#ee746f', data: [0, 18, 38, 64, 96, 122, 146] },
      { name: '手续费', color: '#d05caa', data: [0, -2, -4, -6, -8, -10, -12] },
    ],
    legSnapshots: [
      {
        title: '现货腿',
        venue: 'gate',
        symbol: 'XAUT/USDT',
        rows: [
          { label: '持仓数量', value: '0' },
          { label: '成本均价', value: '5,339.06' },
          { label: '最新价', value: '5,129.30' },
          { label: '持仓价值', value: '0.00' },
          { label: '未实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '已实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '最后同步', value: '2026/3/5 15:37:04' },
        ],
      },
      {
        title: '合约腿',
        venue: 'binance',
        symbol: 'XAU/USDT:USDT',
        rows: [
          { label: '持仓数量', value: '0' },
          { label: '均价', value: '5,361.388' },
          { label: '标记价', value: '5,158.18' },
          { label: '未实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '已实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '下次费率', value: '-0.0028%', tone: 'negative' },
          { label: '下次结算', value: '2026/3/5 16:00:00' },
          { label: '最后同步', value: '2026/3/5 15:37:05' },
        ],
      },
    ],
    detailCurves: [
      {
        title: '资费收益',
        value: '+142,680',
        tone: 'positive',
        data: [12, 18, 31, 44, 58, 72, 88],
      },
      { title: '基差收益', value: '+96,420', tone: 'positive', data: [8, 12, 18, 26, 33, 44, 57] },
      { title: '现货附加收益', value: '+18,640', tone: 'positive', data: [2, 4, 6, 8, 10, 13, 16] },
      {
        title: '现货借贷成本',
        value: '-24,180',
        tone: 'negative',
        data: [-2, -5, -8, -11, -14, -18, -22],
      },
      { title: '持仓损益', value: '+82,360', tone: 'positive', data: [7, 14, 20, 27, 39, 58, 82] },
      {
        title: '累计交易成本',
        value: '-11,420',
        tone: 'negative',
        data: [-1, -3, -5, -7, -8, -10, -11],
      },
      {
        title: '执行偏差',
        value: '-4,280',
        tone: 'negative',
        data: [-0.6, -1.1, -1.4, -1.9, -2.4, -3.1, -4.3],
      },
    ],
  },
  crossSpread: {
    title: '跨所价差损益总览',
    totalFund: '20,343,790.35 CNY',
    period: '2026-06-19 - 2026-06-25',
    xLabels: labels,
    dailyReturns: [42, -38, 54, 62, 70, 84, 96],
    netValues: [18, 17.2, 16.4, 15.5, 14.6, 13.3, 12],
    metrics: [
      { label: '累计总损益', value: '-213,909.50', ratio: '-1.04%', tone: 'negative' },
      { label: '过去24H盈亏', value: '-18,422', ratio: '-0.09%', tone: 'negative' },
      { label: '过去7天盈亏', value: '+36,780', ratio: '+0.18%', tone: 'positive' },
      { label: '胜率', value: '63.8', ratio: '%', tone: 'positive' },
    ],
    attributions: [
      { label: 'XAUT/XAU价差损益', value: '-44,421', ratio: '-20.8%', tone: 'negative' },
      { label: '永续/现货价差损益', value: '+31,860', ratio: '+14.9%', tone: 'positive' },
      { label: 'USDT/USD偏离损益', value: '-20,128', ratio: '-9.4%', tone: 'negative' },
      { label: '腿间持仓损益', value: '-96,420', ratio: '-45.1%', tone: 'negative' },
      { label: '库存费', value: '+8,642', ratio: '+4.0%', tone: 'positive' },
      { label: '资费', value: '-6,280', ratio: '-2.9%', tone: 'negative' },
      { label: '累计交易成本', value: '-12,486', ratio: '-5.8%', tone: 'negative' },
      { label: '执行偏差', value: '-4,114', ratio: '-1.9%', tone: 'negative' },
    ],
    breakdownSeries: [
      { name: '净收益', color: '#3498db', data: [0, -38, 16, 78, 148, 232, 328] },
      { name: '合约盈亏', color: '#55d6d9', data: [0, -820, -2200, -4450, -4220, -3920, 2920] },
      { name: '现货盈亏', color: '#f4bf45', data: [0, 760, 2180, 3900, 4200, 3980, -2720] },
      { name: '费率累计', color: '#ee746f', data: [0, -1, -2, -3, -4, -5, -6] },
      { name: '手续费', color: '#d05caa', data: [0, -2, -4, -6, -8, -10, -12] },
    ],
    legSnapshots: [
      {
        title: '现货腿',
        venue: 'gate',
        symbol: 'XAUT/USDT',
        rows: [
          { label: '持仓数量', value: '0' },
          { label: '成本均价', value: '5,339.06' },
          { label: '最新价', value: '5,129.30' },
          { label: '持仓价值', value: '0.00' },
          { label: '未实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '已实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '最后同步', value: '2026/3/5 15:37:04' },
        ],
      },
      {
        title: '合约腿',
        venue: 'binance',
        symbol: 'XAU/USDT:USDT',
        rows: [
          { label: '持仓数量', value: '0' },
          { label: '均价', value: '5,361.388' },
          { label: '标记价', value: '5,158.18' },
          { label: '未实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '已实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '下次费率', value: '-0.0028%', tone: 'negative' },
          { label: '下次结算', value: '2026/3/5 16:00:00' },
          { label: '最后同步', value: '2026/3/5 15:37:05' },
        ],
      },
    ],
    detailCurves: [
      {
        title: 'XAUT/XAU价差损益',
        value: '-44,421',
        tone: 'negative',
        data: [-4, -12, -20, -26, -32, -39, -44],
      },
      {
        title: '永续/现货价差损益',
        value: '+31,860',
        tone: 'positive',
        data: [3, 5, 9, 14, 19, 24, 32],
      },
      {
        title: 'USDT/USD偏离损益',
        value: '-20,128',
        tone: 'negative',
        data: [-2, -6, -8, -12, -15, -17, -20],
      },
      {
        title: '腿间持仓损益',
        value: '-96,420',
        tone: 'negative',
        data: [-10, -18, -31, -44, -62, -79, -96],
      },
      { title: '库存费', value: '+8,642', tone: 'positive', data: [1, 2, 3, 4, 5, 7, 9] },
      {
        title: '资费',
        value: '-6,280',
        tone: 'negative',
        data: [-0.8, -1.5, -2.3, -3.1, -4.0, -5.1, -6.3],
      },
      {
        title: '累计交易成本',
        value: '-12,486',
        tone: 'negative',
        data: [-1.2, -2.5, -4.1, -5.8, -7.2, -9.6, -12.5],
      },
      {
        title: '执行偏差',
        value: '-4,114',
        tone: 'negative',
        data: [-0.4, -0.9, -1.3, -1.8, -2.2, -3.0, -4.1],
      },
    ],
  },
  domesticOverseas: {
    title: '海内外价差损益总览',
    totalFund: '20,343,790.35 CNY',
    period: '2026-06-19 - 2026-06-25',
    xLabels: labels,
    dailyReturns: [-18, -24, 16, 28, 42, 31, -12],
    netValues: [1.0, 0.998, 0.994, 0.991, 0.996, 1.001, 1.006],
    metrics: [
      { label: '累计总损益（含汇率）', value: '-318,420', ratio: '-1.52%', tone: 'negative' },
      { label: '累计损益（除汇率）', value: '+96,840', ratio: '+0.46%', tone: 'positive' },
      { label: '汇率损益', value: '-378,224', ratio: '-1.80%', tone: 'negative' },
      { label: '配平误差', value: '-37,036', ratio: '-0.18%', tone: 'negative' },
    ],
    attributions: [
      { label: '累计损益（除汇率）', value: '+96,840', ratio: '+30.4%', tone: 'positive' },
      { label: '汇率损益', value: '-378,224', ratio: '-118.8%', tone: 'negative' },
      { label: '配平误差', value: '-37,036', ratio: '-11.6%', tone: 'negative' },
      { label: '累计交易成本', value: '-12,486', ratio: '-3.9%', tone: 'negative' },
    ],
    breakdownSeries: [
      { name: '净收益', color: '#3498db', data: [0, -24, -8, 20, 62, 93, 81] },
      { name: '国内腿盈亏', color: '#55d6d9', data: [0, -520, -1680, -2820, -1980, -820, 940] },
      { name: '海外腿盈亏', color: '#f4bf45', data: [0, 460, 1280, 2260, 2380, 1880, -640] },
      { name: '汇率损益', color: '#ee746f', data: [0, -88, -142, -196, -251, -314, -378] },
      { name: '交易成本', color: '#d05caa', data: [0, -2, -4, -6, -8, -10, -12] },
    ],
    legSnapshots: [
      {
        title: '国内腿',
        venue: '国内期货账户',
        symbol: 'AU / 黄金对冲',
        rows: [
          { label: '持仓数量', value: '0' },
          { label: '成本均价', value: '553.40' },
          { label: '最新价', value: '556.20' },
          { label: '持仓价值', value: '12,007,815.82' },
          { label: '未实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '已实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '最后同步', value: '2026/3/5 15:37:04' },
        ],
      },
      {
        title: '海外腿',
        venue: '海外黄金账户',
        symbol: 'XAU/USD',
        rows: [
          { label: '持仓数量', value: '0' },
          { label: '均价', value: '2,318.40' },
          { label: '标记价', value: '2,291.80' },
          { label: '未实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '已实现盈亏', value: '+0.00', tone: 'positive' },
          { label: '汇率口径', value: '实时汇率' },
          { label: '下次结算', value: '2026/3/5 16:00:00' },
          { label: '最后同步', value: '2026/3/5 15:37:05' },
        ],
      },
    ],
    detailCurves: [
      {
        title: '库存费累计收益',
        value: '+14,580',
        tone: 'positive',
        data: [2, 3, 5, 7, 9, 12, 15],
      },
      {
        title: '海内外溢价损益',
        value: '-44,421',
        tone: 'negative',
        data: [-5, -10, -14, -21, -28, -36, -44],
      },
      {
        title: '期现价差损益',
        value: '+31,860',
        tone: 'positive',
        data: [4, 8, 13, 18, 22, 27, 32],
      },
      {
        title: '汇率损益',
        value: '-378,224',
        tone: 'negative',
        data: [-32, -88, -142, -196, -251, -314, -378],
      },
      {
        title: '海外本金汇率损益',
        value: '-126,480',
        tone: 'negative',
        data: [-8, -24, -42, -61, -82, -104, -126],
      },
      {
        title: '库存费汇率损益',
        value: '-38,640',
        tone: 'negative',
        data: [-3, -8, -15, -21, -27, -32, -39],
      },
      {
        title: '国内汇率变动持仓损益',
        value: '-96,130',
        tone: 'negative',
        data: [-9, -23, -39, -56, -68, -81, -96],
      },
      {
        title: '海外持仓汇率损益',
        value: '-71,244',
        tone: 'negative',
        data: [-6, -18, -29, -41, -53, -62, -71],
      },
      {
        title: '国内对冲持仓汇率损益',
        value: '-45,730',
        tone: 'negative',
        data: [-4, -10, -18, -26, -33, -39, -46],
      },
    ],
  },
  dip: {
    title: '抄底策略损益总览',
    totalFund: '1,582,406.22 USD',
    period: '2026-06-19 - 2026-06-25',
    xLabels: labels,
    dailyReturns: [12, -8, 24, 38, 46, 58, 66],
    netValues: [1.0, 0.994, 1.005, 1.014, 1.026, 1.033, 1.041],
    metrics: [
      { label: '累计总损益', value: '+128,950.40', ratio: '+8.88%', tone: 'positive' },
      { label: '过去24H盈亏', value: '+8,214.22', ratio: '+0.52%', tone: 'positive' },
      { label: '最大回撤', value: '-11.2', ratio: '%', tone: 'negative' },
      { label: '单标的贡献', value: 'BTC', ratio: '+48%', tone: 'positive' },
    ],
    attributions: [
      { label: '已实现收益', value: '+76,580', ratio: '+59.4%', tone: 'positive' },
      { label: '浮动盈亏', value: '+41,820', ratio: '+32.4%', tone: 'positive' },
      { label: '止损损耗', value: '-8,114', ratio: '-6.3%', tone: 'negative' },
      { label: '交易成本', value: '-4,520', ratio: '-3.5%', tone: 'negative' },
    ],
    breakdownSeries: [
      { name: '净收益', color: '#3498db', data: [0, -8, 16, 54, 100, 158, 224] },
      { name: '已实现收益', color: '#55d6d9', data: [0, 8, 18, 32, 48, 62, 77] },
      { name: '浮动盈亏', color: '#f4bf45', data: [0, -12, 4, 16, 24, 33, 42] },
      { name: '止损损耗', color: '#ee746f', data: [0, -1, -2, -3, -5, -7, -8] },
      { name: '交易成本', color: '#d05caa', data: [0, -0.5, -1, -1.6, -2.2, -3, -4.5] },
    ],
    detailCurves: [
      {
        title: '已实现收益',
        value: '+76,580',
        tone: 'positive',
        data: [6, 12, 20, 29, 41, 58, 77],
      },
      { title: '浮动盈亏', value: '+41,820', tone: 'positive', data: [4, -2, 8, 16, 24, 32, 42] },
      { title: '止损损耗', value: '-8,114', tone: 'negative', data: [-1, -2, -2, -4, -5, -7, -8] },
      {
        title: '交易成本',
        value: '-4,520',
        tone: 'negative',
        data: [-0.5, -1, -1.6, -2.2, -3, -3.8, -4.5],
      },
    ],
  },
  shortLineTraderL: {
    title: '短线交易员A损益总览',
    totalFund: '6,842,190.50 CNY',
    period: '2026-06-19 - 2026-06-25',
    xLabels: labels,
    dailyReturns: [18, 26, -12, 34, 42, 28, 46],
    netValues: [1.0, 1.006, 1.012, 1.009, 1.018, 1.024, 1.031],
    metrics: [
      { label: '日内总盈亏', value: '+42,680', ratio: '+0.63%', tone: 'positive' },
      { label: '已实现盈亏', value: '+31,240', ratio: '+0.46%', tone: 'positive' },
      { label: '浮动盈亏', value: '+11,440', ratio: '+0.17%', tone: 'positive' },
      { label: '胜率', value: '62.5', ratio: '%', tone: 'positive' },
    ],
    attributions: [
      { label: '止盈贡献', value: '+58,420', ratio: '+136.9%', tone: 'positive' },
      { label: '止损损耗', value: '-16,860', ratio: '-39.5%', tone: 'negative' },
      { label: '手续费成本', value: '-4,880', ratio: '-11.4%', tone: 'negative' },
      { label: '股指贡献', value: '+24,160', ratio: '+56.6%', tone: 'positive' },
      { label: '黄金贡献', value: '+14,220', ratio: '+33.3%', tone: 'positive' },
      { label: '币贡献', value: '+4,300', ratio: '+10.1%', tone: 'positive' },
    ],
    breakdownSeries: [
      { name: '净收益', color: '#3498db', data: [0, 18, 44, 32, 66, 94, 140] },
      { name: '止盈贡献', color: '#55d6d9', data: [0, 8, 14, 20, 28, 47, 58] },
      { name: '止损损耗', color: '#f4bf45', data: [0, -2, -4, -8, -10, -14, -17] },
      { name: '品种贡献', color: '#ee746f', data: [0, 6, 14, 18, 24, 32, 43] },
      { name: '手续费成本', color: '#d05caa', data: [0, -0.6, -1.1, -1.9, -2.4, -3.8, -4.9] },
    ],
    detailCurves: [
      { title: '止盈贡献', value: '+58,420', tone: 'positive', data: [8, 14, 20, 28, 36, 47, 58] },
      {
        title: '止损损耗',
        value: '-16,860',
        tone: 'negative',
        data: [-2, -4, -8, -10, -12, -14, -17],
      },
      { title: '股指贡献', value: '+24,160', tone: 'positive', data: [3, 8, 10, 14, 17, 21, 24] },
      { title: '黄金贡献', value: '+14,220', tone: 'positive', data: [2, 4, 5, 8, 10, 12, 14] },
      { title: '币贡献', value: '+4,300', tone: 'positive', data: [1, 2, 2.5, 3, 3.5, 3.9, 4.3] },
      {
        title: '手续费成本',
        value: '-4,880',
        tone: 'negative',
        data: [-0.6, -1.1, -1.9, -2.4, -3.1, -3.8, -4.9],
      },
    ],
  },
  spread: {
    title: '价差策略损益总览',
    totalFund: '20,343,790.35 CNY',
    period: '2026-06-19 - 2026-06-25',
    xLabels: labels,
    dailyReturns: [42, -38, 54, 62, 70, 84, 96],
    netValues: [18, 17.2, 16.4, 15.5, 14.6, 13.3, 12],
    metrics: [],
    attributions: [],
    breakdownSeries: [],
    detailCurves: [],
  },
} as unknown as Record<StrategyDeskKey, StrategyPnlProfile> & {
  shortLineTraderW: StrategyPnlProfile;
};

strategyPnlProfiles.shortLineTraderW = JSON.parse(
  JSON.stringify(strategyPnlProfiles.shortLineTraderL),
) as StrategyPnlProfile;
strategyPnlProfiles.shortLineTraderW.title = '短线交易员B损益总览';
strategyPnlProfiles.shortLineTraderW.dailyReturns = [10, -6, 18, 22, -8, 30, 26];
strategyPnlProfiles.shortLineTraderW.netValues = [1.0, 1.003, 1.007, 1.011, 1.008, 1.016, 1.021];
strategyPnlProfiles.shortLineTraderW.metrics = [
  { label: '回归交易盈亏', value: '+31,860', ratio: '+0.47%', tone: 'positive' },
  { label: '已实现盈亏', value: '+22,480', ratio: '+0.33%', tone: 'positive' },
  { label: '浮动盈亏', value: '+9,380', ratio: '+0.14%', tone: 'positive' },
  { label: '胜率', value: '55.8', ratio: '%', tone: 'positive' },
];
strategyPnlProfiles.shortLineTraderW.attributions = [
  { label: '均值回归贡献', value: '+43,120', ratio: '+135.3%', tone: 'positive' },
  { label: '趋势冲击损耗', value: '-9,680', ratio: '-30.4%', tone: 'negative' },
  { label: '低波动篮子贡献', value: '+18,760', ratio: '+58.9%', tone: 'positive' },
  { label: '红利篮子贡献', value: '+9,240', ratio: '+29.0%', tone: 'positive' },
  { label: '手续费成本', value: '-3,420', ratio: '-10.7%', tone: 'negative' },
];
strategyPnlProfiles.shortLineTraderW.detailCurves = [
  { title: '均值回归贡献', value: '+43,120', tone: 'positive', data: [5, 9, 14, 22, 28, 36, 43] },
  { title: '趋势冲击损耗', value: '-9,680', tone: 'negative', data: [-1, -2, -3, -5, -7, -8, -10] },
  { title: '低波动篮子贡献', value: '+18,760', tone: 'positive', data: [2, 4, 7, 9, 12, 15, 19] },
  { title: '红利篮子贡献', value: '+9,240', tone: 'positive', data: [1, 2, 4, 5, 6, 8, 9] },
  {
    title: '手续费成本',
    value: '-3,420',
    tone: 'negative',
    data: [-0.4, -0.8, -1.1, -1.6, -2.2, -2.8, -3.4],
  },
];
