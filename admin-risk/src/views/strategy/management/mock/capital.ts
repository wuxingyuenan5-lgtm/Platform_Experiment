import type { StrategyCapitalProfile, StrategyDeskKey } from '../types';

function makeMetricCurve(
  title: string,
  points: number[],
  amount = '',
  tone: 'positive' | 'negative' | 'neutral' = 'neutral',
  unit = '',
) {
  const dates = ['06-14', '06-17', '06-20', '06-23', '06-26', '06-29', '07-02', '07-05', '07-08', '07-11'];
  const latestValue = points[points.length - 1] ?? 0;
  return {
    title,
    amount: amount || String(latestValue),
    unit,
    tone,
    points: dates.map((date, index) => ({
      date,
      value: points[index] ?? points[points.length - 1] ?? 0,
    })),
  };
}

function makeCapitalMetricCurves(volPoints: number[], sharpePoints: number[]) {
  return [
    makeMetricCurve('波动率', volPoints, `${((volPoints[volPoints.length - 1] ?? 0) * 100).toFixed(2)}`, 'negative', '%'),
    makeMetricCurve('夏普比率', sharpePoints, (sharpePoints[sharpePoints.length - 1] ?? 0).toFixed(2), 'negative'),
  ];
}

export const strategyCapitalProfiles = {
  funding: {
    overview: [
      { label: '账户净值', value: '4,502,541.72', unit: 'USD', note: '资费套利总账户', tone: 'neutral' },
      { label: '累计收益', value: '+511,986.31 (+11.37%)', note: '刨除手续费后的累计结果', tone: 'positive' },
      { label: '过去24H盈亏', value: '-32.16 (-0.01%)', note: 'ETH 资费回落拖累', tone: 'negative' },
      { label: '过去7天盈亏', value: '+8,214.22 (+0.18%)', note: '周内资费结算净额', tone: 'positive' },
      { label: '过去30天盈亏', value: '+96,308.40 (+2.19%)', note: '近月资费收益累计', tone: 'positive' },
      { label: '可用资金', value: '3,948,220.55', unit: 'USD', note: '可继续支持滚动开平仓', tone: 'positive' },
      { label: '合约占用资金', value: '670,174.00', unit: 'USD', note: '合约腿保证金占用', tone: 'neutral' },
      { label: '现货占用资金', value: '436,306.10', unit: 'USD', note: '现货腿资金占用', tone: 'neutral' },
      { label: '杠杆', value: '1.10X', note: '低于策略上限 1.80X', tone: 'positive' },
      { label: '风险等级', value: '中', note: '合约腿保证金占用偏高', tone: 'negative' },
    ],
    riskCards: [
      { label: '保证金安全垫', value: '31%', note: '距离预警线仍有缓冲', tone: 'positive' },
      { label: '预警次数', value: '2', note: '过去7天资费腿触发预警', tone: 'neutral' },
      { label: 'MMR', value: '9.6%', note: '合约腿维持保证金率', tone: 'neutral' },
      { label: '爆仓价', value: 'BTC 96,840', note: '主风险腿参考值', tone: 'negative' },
    ],
    structureCards: [
      { label: '现货账户资产', value: '2,744,220 USD', note: '现货腿可用资金 82%', tone: 'positive' },
      { label: '合约账户资产', value: '1,758,322 USD', note: '合约腿占用仍高于现货腿', tone: 'neutral' },
      { label: '币种结构', value: 'BTC / ETH / XRP', note: 'BTC 仍是主贡献腿', tone: 'neutral' },
      { label: '结算口径', value: '实时结算', note: '支持实时 / 结算口径切换', tone: 'neutral' },
    ],
    comparisonCards: [
      {
        title: '双端资金对照',
        centerValue: '4,502,541.72 USD',
        centerLabel: '现货 / 合约资金结构',
        leftLabel: '现货账户',
        leftValue: '2,744,220 USD（58%）',
        leftNote: '现货头寸 58%',
        rightLabel: '合约账户',
        rightValue: '1,758,322 USD（42%）',
        rightNote: '合约保证金 42%',
        progress: 61,
        startColor: '#3f7cff',
        endColor: '#89a8ff',
      },
    ],
    curve: {
      title: '资费套利账户净值曲线',
      subtitle: '保留净值与回撤两条主线，支持实时与结算口径切换。',
      metricOptions: [
        { key: 'account', label: '账户净值' },
        { key: 'strategy', label: '策略净值' },
      ],
      periodOptions: [
        { key: 'day', label: '日' },
        { key: '7d', label: '7天' },
        { key: '30d', label: '30天' },
      ],
      modeOptions: [
        { key: 'realtime', label: '实时口径' },
        { key: 'settlement', label: '结算口径' },
      ],
      defaultMetric: 'account',
      defaultPeriod: '30d',
      defaultMode: 'realtime',
      xLabels: ['06-14', '06-17', '06-20', '06-23', '06-26', '06-29', '07-02', '07-05', '07-08', '07-11'],
      netValueData: [1.0, 1.006, 1.011, 1.018, 1.026, 1.031, 1.038, 1.044, 1.051, 1.057],
      drawdownData: [-0.6, -0.8, -0.4, -0.9, -0.7, -1.1, -0.5, -0.7, -0.4, -0.3],
      summaries: [
        { label: '区间收益', value: '+5.7%', tone: 'positive' },
        { label: '区间最大回撤', value: '-1.1%', tone: 'negative' },
      ],
    },
    metricCurves: makeCapitalMetricCurves(
      [0.018, 0.019, 0.021, 0.022, 0.024, 0.026, 0.023, 0.021, 0.02, 0.019],
      [1.08, 1.09, 1.11, 1.12, 1.15, 1.16, 1.14, 1.13, 1.12, 1.11],
    ),
  },
  spread: {
    overview: [],
    riskCards: [],
    structureCards: [],
    curve: {
      title: '',
      subtitle: '',
      metricOptions: [],
      periodOptions: [],
      defaultMetric: '',
      defaultPeriod: '',
      xLabels: [],
      netValueData: [],
      drawdownData: [],
      summaries: [],
    },
  },
  crossSpread: {
    overview: [
      { label: '账户净值', value: '20,343,790.35', unit: 'CNY', note: '跨所价差总账户', tone: 'neutral' },
      { label: '累计收益', value: '-213,909.50 (-1.04%)', note: '价差与换月拖累', tone: 'negative' },
      { label: '过去24H盈亏', value: '-18,422 (-0.09%)', note: '日内汇率与换月扰动', tone: 'negative' },
      { label: '过去7天盈亏', value: '+36,780 (+0.18%)', note: '主力腿回补带来修复', tone: 'positive' },
      { label: '过去30天盈亏', value: '-512,640 (-2.31%)', note: '月度表现仍处修复期', tone: 'negative' },
      { label: '可用资金', value: '11,428,540', unit: 'CNY', note: '双端账户仍可继续调仓', tone: 'positive' },
      { label: 'A侧占用资金', value: '4,286,120', unit: 'CNY', note: '主交易所保证金占用', tone: 'neutral' },
      { label: 'B侧占用资金', value: '2,828,160', unit: 'CNY', note: '对冲交易所保证金占用', tone: 'neutral' },
      { label: '杠杆', value: '1.10X', note: '处于舒适区间', tone: 'positive' },
      { label: '风险等级', value: '中', note: '双端风险线未完全同步', tone: 'negative' },
      { label: '胜率', value: '63.8%', note: '按有效开平仓统计', tone: 'positive' },
    ],
    riskCards: [
      { label: '保证金安全垫', value: '24%', note: 'A侧安全垫偏薄', tone: 'negative' },
      { label: '预警次数', value: '3', note: '过去7天出现跨所偏移预警', tone: 'neutral' },
      { label: 'MMR', value: '11.8%', note: '主风险账户维持保证金率', tone: 'neutral' },
      { label: '爆仓价', value: 'XAU 1,018.4', note: '主合约腿参考值', tone: 'negative' },
    ],
    structureCards: [
      { label: '交易所A账户', value: '11,312,370 CNY', note: '可用资金 92.69%', tone: 'positive' },
      { label: '交易所B账户', value: '1,324,857 USD', note: '自动匹配进行中', tone: 'neutral' },
      { label: '主要风险腿', value: 'A侧主力换月', note: '当前仍在滚动移仓', tone: 'negative' },
      { label: '资金调度', value: '偏向B侧补充', note: '建议优先回补对冲腿', tone: 'neutral' },
    ],
    comparisonCards: [
      {
        title: '双端资金对照',
        centerValue: '20,343,790.35 CNY',
        centerLabel: '交易所 A / B 资金状态',
        leftLabel: '交易所A',
        leftValue: '11,312,370 CNY（74.58%）',
        leftNote: 'A侧仓位 74.58%',
        rightLabel: '交易所B',
        rightValue: '1,324,857 USD（25.42%）',
        rightNote: 'B侧保证金 25.42%',
        progress: 57,
        startColor: '#3f7cff',
        endColor: '#77a6ff',
      },
    ],
    curve: {
      title: '跨所价差账户净值曲线',
      subtitle: '统一保留净值与回撤，观察双端账户净值修复节奏。',
      metricOptions: [
        { key: 'strategy', label: '策略净值' },
        { key: 'account', label: '账户净值' },
      ],
      periodOptions: [
        { key: 'day', label: '日' },
        { key: '7d', label: '7天' },
        { key: '30d', label: '30天' },
      ],
      modeOptions: [
        { key: 'total', label: '总账户' },
        { key: 'split', label: '分账户' },
      ],
      defaultMetric: 'strategy',
      defaultPeriod: '30d',
      defaultMode: 'total',
      xLabels: ['06-14', '06-17', '06-20', '06-23', '06-26', '06-29', '07-02', '07-05', '07-08', '07-11'],
      netValueData: [1.0, 0.996, 0.991, 0.984, 0.989, 0.992, 0.998, 1.004, 1.009, 1.013],
      drawdownData: [-0.8, -1.4, -2.3, -2.9, -2.0, -1.8, -1.3, -1.0, -0.7, -0.5],
      summaries: [
        { label: '区间收益', value: '+1.3%', tone: 'positive' },
        { label: '区间最大回撤', value: '-2.9%', tone: 'negative' },
      ],
    },
    metricCurves: makeCapitalMetricCurves(
      [0.021, 0.022, 0.023, 0.024, 0.028, 0.031, 0.029, 0.025, 0.023, 0.022],
      [0.96, 0.98, 1.01, 1.02, 0.94, 0.91, 0.95, 0.99, 1.0, 1.01],
    ),
  },
  domesticOverseas: {
    overview: [
      { label: '账户净值', value: '20,343,790.35', unit: 'CNY', note: '海内外价差总账户', tone: 'neutral' },
      { label: '累计收益', value: '-318,420 (-1.52%)', note: '汇率腿仍在拖累', tone: 'negative' },
      { label: '过去24H盈亏', value: '-18,422 (-0.09%)', note: '汇率与海外腿拖累', tone: 'negative' },
      { label: '过去7天盈亏', value: '+42,880 (+0.21%)', note: '国内腿修复更快', tone: 'positive' },
      { label: '过去30天盈亏', value: '-278,440 (-1.31%)', note: '海外腿仍未完全修复', tone: 'negative' },
      { label: '可用资金', value: '11,007,815', unit: 'CNY', note: '国内外账户均可继续调度', tone: 'positive' },
      { label: '国内占用资金', value: '3,914,860', unit: 'CNY', note: '国内腿保证金占用', tone: 'neutral' },
      { label: '海外占用资金', value: '4,305,580', unit: 'CNY', note: '海外腿保证金占用', tone: 'neutral' },
      { label: '杠杆', value: '1.14X', note: '仍在安全区内', tone: 'positive' },
      { label: '风险等级', value: '中', note: '海外账户可用资金偏低', tone: 'negative' },
      { label: '胜率', value: '61.2%', note: '按完整对冲回合统计', tone: 'positive' },
    ],
    riskCards: [
      { label: '保证金安全垫', value: '22%', note: '海外账户安全垫偏薄', tone: 'negative' },
      { label: '预警次数', value: '4', note: '近7天出现汇率偏移提醒', tone: 'neutral' },
      { label: 'MMR', value: '12.4%', note: '海外主账户维持保证金率', tone: 'neutral' },
      { label: '爆仓价', value: 'XAUUSD 2,291', note: '海外黄金腿参考值', tone: 'negative' },
    ],
    structureCards: [
      { label: '国内账户', value: '12,007,816 CNY', note: '国内腿仍是主资金池', tone: 'positive' },
      { label: '海外账户', value: '9,765,941 CNY', note: '已按实时汇率换算', tone: 'neutral' },
      { label: '汇率口径', value: '实时 / 固定', note: '支持双口径对照观察', tone: 'neutral' },
      { label: '主要风险腿', value: '海外黄金腿', note: '保证金与汇率双重敏感', tone: 'negative' },
    ],
    comparisonCards: [
      {
        title: '双端资金对照',
        centerValue: '21,773,757.12 CNY',
        centerLabel: '国内 / 海外资金状态',
        leftLabel: '国内账户',
        leftValue: '12,007,816 CNY（48%）',
        leftNote: '国内仓位 48%',
        rightLabel: '海外账户',
        rightValue: '9,765,941 CNY（52%）',
        rightNote: '海外保证金 52%',
        progress: 55,
        startColor: '#3f7cff',
        endColor: '#77a6ff',
      },
    ],
    riskOverview: {
      title: '海内外价差风险总览',
      rows: [
        {
          product: '黄金测试产品1号/live_trading',
          type: '账户',
          level: '二级风险',
          factor: 'marginLevel',
          firstValue: '10633.14',
          latestValue: '10605.7',
          latestTime: '2025-12-12 17:54:00',
          count: '3',
          status: '处理完成',
          tone: 'neutral',
        },
      ],
    },
    curve: {
      title: '海内外价差账户净值曲线',
      subtitle: '净值与回撤统一保留，支持实时汇率与固定汇率切换。',
      metricOptions: [
        { key: 'strategy', label: '策略净值' },
        { key: 'account', label: '账户净值' },
      ],
      periodOptions: [
        { key: 'day', label: '日' },
        { key: '7d', label: '7天' },
        { key: '30d', label: '30天' },
      ],
      modeOptions: [
        { key: 'realtime', label: '实时汇率' },
        { key: 'fixed', label: '固定汇率' },
      ],
      defaultMetric: 'strategy',
      defaultPeriod: '30d',
      defaultMode: 'realtime',
      xLabels: ['06-14', '06-17', '06-20', '06-23', '06-26', '06-29', '07-02', '07-05', '07-08', '07-11'],
      netValueData: [1.0, 0.998, 0.994, 0.991, 0.996, 1.001, 1.006, 1.012, 1.018, 1.021],
      drawdownData: [-0.7, -1.1, -1.8, -2.2, -1.4, -1.1, -0.9, -0.6, -0.4, -0.3],
      summaries: [
        { label: '区间收益', value: '+2.1%', tone: 'positive' },
        { label: '区间最大回撤', value: '-2.2%', tone: 'negative' },
      ],
    },
    metricCurves: makeCapitalMetricCurves(
      [0.022, 0.024, 0.026, 0.027, 0.03, 0.034, 0.032, 0.029, 0.026, 0.024],
      [0.92, 0.95, 0.97, 0.99, 0.9, 0.88, 0.91, 0.94, 0.96, 0.98],
    ),
  },
  dip: {
    overview: [
      { label: '账户净值', value: '1,582,406.22', unit: 'USD', note: '抄底组合账户', tone: 'neutral' },
      { label: '累计收益', value: '+128,950.40 (+8.88%)', note: '波段抄底累计结果', tone: 'positive' },
      { label: '过去24H盈亏', value: '+8,214.22 (+0.52%)', note: 'BTC 反弹贡献居多', tone: 'positive' },
      { label: '过去7天盈亏', value: '+24,680.30 (+1.63%)', note: '回补阶段收益继续释放', tone: 'positive' },
      { label: '过去30天盈亏', value: '+66,540.18 (+4.39%)', note: '近月组合净值修复明显', tone: 'positive' },
      { label: '可用资金', value: '664,720.10', unit: 'USD', note: '保留继续加仓弹药', tone: 'positive' },
      { label: '保证金占用', value: '356,840.00', unit: 'USD', note: '主要集中在高弹性币', tone: 'neutral' },
      { label: '杠杆', value: '1.18X', note: '当前未超出风控上限', tone: 'positive' },
      { label: '风险等级', value: '中低', note: 'BTC 仓位仍是主要风险来源', tone: 'neutral' },
    ],
    riskCards: [
      { label: '保证金安全垫', value: '36%', note: '仍有继续调仓空间', tone: 'positive' },
      { label: '预警次数', value: '1', note: '过去7天仅出现一次仓位预警', tone: 'neutral' },
      { label: '爆仓价', value: 'BTC 93,420', note: '当前主仓风险线参考值', tone: 'negative' },
      { label: '止损覆盖', value: '67%', note: '保护单仍需继续补全', tone: 'negative' },
    ],
    structureCards: [
      { label: '仓位利用率', value: '58%', note: '当前处于中等仓位区间', tone: 'neutral' },
      { label: '现金缓冲', value: '42%', note: '保留继续补仓能力', tone: 'positive' },
      { label: '主仓标的', value: 'BTC', note: '当前仍是最主要风险暴露', tone: 'neutral' },
      { label: '保护单覆盖', value: '67%', note: '仍需补齐尾部保护', tone: 'negative' },
    ],
    curve: {
      title: '抄底策略账户净值曲线',
      subtitle: '统一保留净值与回撤，观察补仓与止盈节奏。',
      metricOptions: [
        { key: 'account', label: '账户净值' },
        { key: 'strategy', label: '策略净值' },
      ],
      periodOptions: [
        { key: 'day', label: '日' },
        { key: '7d', label: '7天' },
        { key: '30d', label: '30天' },
      ],
      defaultMetric: 'account',
      defaultPeriod: '30d',
      xLabels: ['06-14', '06-17', '06-20', '06-23', '06-26', '06-29', '07-02', '07-05', '07-08', '07-11'],
      netValueData: [1.0, 0.994, 1.005, 1.014, 1.026, 1.033, 1.041, 1.056, 1.072, 1.089],
      drawdownData: [-1.4, -2.2, -1.5, -1.0, -0.8, -1.1, -0.7, -0.5, -0.4, -0.3],
      summaries: [
        { label: '区间收益', value: '+8.9%', tone: 'positive' },
        { label: '区间最大回撤', value: '-2.2%', tone: 'negative' },
      ],
    },
    metricCurves: makeCapitalMetricCurves(
      [0.026, 0.028, 0.031, 0.033, 0.036, 0.038, 0.035, 0.032, 0.03, 0.028],
      [0.86, 0.89, 0.93, 0.95, 0.98, 1.0, 0.97, 0.94, 0.92, 0.91],
    ),
  },
  shortLineTraderL: {
    overview: [
      { label: '账户净值', value: '6,842,190.50', unit: 'CNY', note: '短线交易员L总账户', tone: 'neutral' },
      { label: '累计收益', value: '+426,880 (+6.66%)', note: '刨除手续费后的日内累计', tone: 'positive' },
      { label: '过去24H盈亏', value: '+42,680 (+0.63%)', note: '日内总盈亏', tone: 'positive' },
      { label: '过去7天盈亏', value: '+102,480 (+1.52%)', note: '近7天已实现与浮盈合计', tone: 'positive' },
      { label: '过去30天盈亏', value: '+236,580 (+3.58%)', note: '近月多品种日内累计', tone: 'positive' },
      { label: '可用资金', value: '4,118,240.60', unit: 'CNY', note: '可继续支持日内调仓', tone: 'positive' },
      { label: '保证金占用', value: '1,862,420.30', unit: 'CNY', note: '股指与黄金占用为主', tone: 'neutral' },
      { label: '杠杆', value: '1.27X', note: '仍低于日内风控上限', tone: 'positive' },
      { label: '风险等级', value: '中低', note: '币组波动放大需继续观察', tone: 'neutral' },
      { label: '胜率', value: '62.5%', note: '按近30天有效单统计', tone: 'positive' },
    ],
    riskCards: [
      { label: '保证金安全垫', value: '29%', note: '距离日内风险线仍有缓冲', tone: 'positive' },
      { label: '当日最大回撤', value: '-12,360', note: '回撤仍在风控线内', tone: 'negative' },
      { label: '风控触发次数', value: '2', note: '当日已触发两次风控动作', tone: 'neutral' },
      { label: '隔夜仓位状态', value: '无隔夜', note: '当前符合日内纪律', tone: 'positive' },
    ],
    structureCards: [
      { label: '股指账户', value: '3,120,000 CNY', note: '主交易账户，日内占用最高', tone: 'neutral' },
      { label: '黄金账户', value: '1,840,000 CNY', note: '兼顾沪金与外盘金', tone: 'neutral' },
      { label: '币账户', value: '1,120,000 CNY', note: '弹性高，单笔仓位受控', tone: 'neutral' },
      { label: '保护单覆盖', value: '73%', note: '仍需继续补齐', tone: 'negative' },
    ],
    curve: {
      title: '短线交易员L账户净值曲线',
      subtitle: '统一保留净值与回撤，并支持按品类切换观察。',
      metricOptions: [
        { key: 'total', label: '总账户' },
        { key: 'index', label: '股指' },
        { key: 'gold', label: '黄金' },
        { key: 'crypto', label: '币' },
      ],
      periodOptions: [
        { key: 'day', label: '日' },
        { key: '7d', label: '7天' },
        { key: '30d', label: '30天' },
      ],
      defaultMetric: 'total',
      defaultPeriod: '7d',
      xLabels: ['09:00', '09:30', '10:00', '10:30', '11:00', '13:00', '13:30', '14:00', '14:30', '15:00'],
      netValueData: [1.0, 1.004, 1.002, 1.007, 1.011, 1.016, 1.013, 1.019, 1.025, 1.031],
      drawdownData: [-0.4, -0.8, -1.6, -1.2, -0.9, -1.8, -2.1, -1.6, -1.0, -0.7],
      summaries: [
        { label: '区间收益', value: '+3.1%', tone: 'positive' },
        { label: '区间最大回撤', value: '-2.1%', tone: 'negative' },
      ],
    },
    metricCurves: makeCapitalMetricCurves(
      [0.028, 0.029, 0.031, 0.03, 0.032, 0.034, 0.033, 0.035, 0.037, 0.036],
      [1.02, 1.04, 1.03, 1.05, 1.08, 1.09, 1.07, 1.08, 1.1, 1.11],
    ),
    specialRulePanel: {
      title: '短线交易员L专属风控规则组件',
      status: '正常',
      statusNote: '当前未进入停手或冷静期，规则内容未来可动态调整。',
      tone: 'positive',
      metrics: [
        { label: '当前风控状态', value: '正常', note: '未触发停手 / 冷静期', tone: 'positive' },
        { label: '当日已实现收益', value: '+31,240', note: '距 5R 停手线仍有空间', tone: 'positive' },
        { label: '手续费占比', value: '18.4%', note: '未超过 25% 成本限制', tone: 'positive' },
        { label: '违规次数', value: '1', note: '近7天记录一次人工违规', tone: 'negative' },
      ],
      alerts: [
        { time: '2026-07-12 13:12:33', text: 'BTC 追单后波动放大，触发一次风控减仓提醒。', tone: 'neutral' },
        { time: '2026-07-12 10:18:44', text: '黄金止盈单撤回，已发送人工复核消息。', tone: 'neutral' },
        { time: '2026-07-12 09:36:08', text: 'IF2609 保护止损已同步挂出，风控检测通过。', tone: 'positive' },
      ],
    },
  },
} as unknown as Record<StrategyDeskKey, StrategyCapitalProfile> & {
  shortLineTraderW: StrategyCapitalProfile;
};

strategyCapitalProfiles.spread = strategyCapitalProfiles.crossSpread;
strategyCapitalProfiles.shortLineTraderW = JSON.parse(
  JSON.stringify(strategyCapitalProfiles.shortLineTraderL),
) as StrategyCapitalProfile;
strategyCapitalProfiles.shortLineTraderW.overview = strategyCapitalProfiles.shortLineTraderW.overview.map((item) => ({
  ...item,
  note: item.note.replaceAll('短线交易员L', '短线交易员W'),
}));
strategyCapitalProfiles.shortLineTraderW.overview[0] = {
  ...strategyCapitalProfiles.shortLineTraderW.overview[0],
  note: '短线交易员W总账户',
};
strategyCapitalProfiles.shortLineTraderW.curve = {
  ...strategyCapitalProfiles.shortLineTraderW.curve,
  title: '短线交易员W账户净值曲线',
};
if (strategyCapitalProfiles.shortLineTraderW.specialRulePanel) {
  strategyCapitalProfiles.shortLineTraderW.specialRulePanel.title = '短线交易员W专属风控规则组件';
}
