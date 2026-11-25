const keys = [
  'vixeqVix',
  'dspx',
  'nvda',
  'vix',
  'vvix',
  'vixVxv',
  'vix9dVix',
  'skew',
  'pcEquity',
  'pcTotal',
  'pcIndex',
  'spxGex',
  'dealerGamma',
  'netDelta',
] as const;

export type IndicatorKey = (typeof keys)[number];
export type Inputs = Record<IndicatorKey, number>;
type Signal = 'normal' | 'watch' | 'risk';

export const sourceUrl = 'https://sites.google.com/view/fupeng715/full-page-embed?pli=1&authuser=0';

function preset(label: string, readings: number[]) {
  return { label, values: Object.fromEntries(keys.map((key, i) => [key, readings[i]])) as Inputs };
}

export const scenarios = [
  preset(
    '11/19 OPEX 前基准',
    [1.6, 37.2, 146, 28.4, 122, 1.05, 1.03, 141, 0.72, 1.05, 1.15, -100.5, -7.3, -110],
  ),
  preset(
    '阶段一 · 离散繁荣稳态',
    [2.65, 44.5, 178, 14.2, 84, 0.86, 0.88, 146, 0.52, 0.82, 1.05, 85, 4.8, 65],
  ),
  preset(
    '阶段二 · 偏度与个股预警',
    [2.12, 41, 162, 18.8, 102, 0.96, 0.98, 166, 0.71, 1.01, 1.12, 12, 0.4, -15],
  ),
  preset(
    '阶段三升级 · 宏观全面防御',
    [1.35, 31.5, 132, 35.8, 142, 1.14, 1.11, 132, 0.88, 1.34, 1.42, -118, -9.1, -138],
  ),
  preset(
    '阶段四 · OPEX 重置 / 反向 Vanna',
    [1.72, 36, 151.5, 22.6, 101, 0.96, 0.94, 134, 0.74, 1.08, 1.22, -18, -1.4, 15],
  ),
];

export const stages = [
  {
    id: 1,
    name: '缩圈与离散稳态',
    description:
      '卖指数波动、买个股波动，相关性下降。做市商正 Gamma 对冲缓和波动，机械买盘支撑权重股。',
  },
  {
    id: 2,
    name: '拥挤见顶与先遣撤退',
    description: 'SKEW 升向 160–170，个股看跌交易率先走高，龙头股转弱。',
  },
  {
    id: 3,
    name: '负反馈翻转与 Vanna 踩踏',
    description:
      '离散交易平仓，VIX 超过 28 并伴随倒挂，VVIX 抬升。负 Gamma 与 Vanna 对冲放大抛压。',
  },
  {
    id: 4,
    name: '极端出清与反向 Vanna 修复',
    description: 'OPEX 到期重置，看跌仓位止盈。VVIX 降温，期限倒挂收窄，空头对冲回补。',
  },
];

interface Indicator {
  key: IndicatorKey;
  name: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  decimals: number;
  threshold: string;
  signal: (s: Inputs) => Signal;
}

function indicator(
  key: IndicatorKey,
  name: string,
  unit: string,
  min: number,
  max: number,
  step: number,
  decimals: number,
  threshold: string,
  risk: (s: Inputs) => boolean,
  watch: (s: Inputs) => boolean,
): Indicator {
  return {
    key,
    name,
    unit,
    min,
    max,
    step,
    decimals,
    threshold,
    signal: (s) => (risk(s) ? 'risk' : watch(s) ? 'watch' : 'normal'),
  };
}

const elevated = (key: IndicatorKey, watch: number, risk: number) =>
  [(s: Inputs) => s[key] >= risk, (s: Inputs) => s[key] >= watch] as const;

export const indicatorGroups = [
  {
    name: '离散与相关性',
    indicators: [
      indicator(
        'vixeqVix',
        'VIXEQ / VIX',
        '倍',
        1,
        3.5,
        0.05,
        2,
        '2.00 为回落观察位 · 低于 1.85 触发红线',
        (s) => s.vixeqVix < 1.85,
        (s) => s.vixeqVix < 2.15,
      ),
      indicator(
        'dspx',
        'Cboe DSPX',
        '',
        15,
        60,
        0.5,
        1,
        '相关性升高时观察回落 · DSPX < 35 且 VIX > 25 触发红线',
        (s) => s.dspx < 35 && s.vix > 25,
        (s) => s.dspx < 39,
      ),
      indicator(
        'nvda',
        '英伟达（NVDA）',
        '美元',
        90,
        220,
        0.5,
        1,
        '150 美元为通道观察位 · 低于 148 触发红线',
        (s) => s.nvda < 148,
        (s) => s.nvda < 160,
      ),
    ],
  },
  {
    name: '波动率与流动性',
    indicators: [
      indicator(
        'vix',
        'VIX（30 天）',
        '',
        10,
        55,
        0.2,
        1,
        'Vanna 观察阈值 28',
        ...elevated('vix', 20, 28),
      ),
      indicator(
        'vvix',
        'VVIX',
        '',
        70,
        170,
        1,
        1,
        '110–120 为流动性承压区 · 115 触发红线',
        ...elevated('vvix', 100, 115),
      ),
    ],
  },
  {
    name: '期限结构与偏度',
    indicators: [
      indicator(
        'vixVxv',
        'VIX / VXV',
        '倍',
        0.75,
        1.35,
        0.01,
        2,
        '近远端比值高于 1.00 即倒挂',
        (s) => s.vixVxv > 1,
        (s) => s.vixVxv >= 0.95,
      ),
      indicator(
        'vix9dVix',
        'VIX9D / VIX',
        '倍',
        0.75,
        1.35,
        0.01,
        2,
        '高于 1.00 时超短端反超 30 天端',
        (s) => s.vix9dVix > 1,
        (s) => s.vix9dVix >= 0.95,
      ),
      indicator(
        'skew',
        'Cboe SKEW',
        '',
        115,
        185,
        1,
        1,
        '留意 160–170 区间和见顶回落 · < 150 且 VIX ≥ 25 触发',
        (s) => s.skew < 150 && s.vix >= 25,
        (s) => s.skew >= 160,
      ),
    ],
  },
  {
    name: '期权流量',
    indicators: [
      indicator(
        'pcEquity',
        '个股看跌 / 看涨',
        '',
        0.35,
        1.2,
        0.01,
        2,
        '达到 0.80',
        ...elevated('pcEquity', 0.68, 0.8),
      ),
      indicator(
        'pcTotal',
        '全市场看跌 / 看涨',
        '',
        0.6,
        1.6,
        0.01,
        2,
        '达到 1.25',
        ...elevated('pcTotal', 1, 1.25),
      ),
      indicator(
        'pcIndex',
        '指数看跌 / 看涨',
        '',
        0.7,
        1.8,
        0.01,
        2,
        '达到 1.25',
        ...elevated('pcIndex', 1.12, 1.25),
      ),
    ],
  },
  {
    name: '做市商敞口',
    indicators: [
      indicator(
        'spxGex',
        'SPX GEX',
        '十亿美元',
        -130,
        130,
        0.5,
        1,
        '参考极值 −97 至 −104 十亿美元 · 关注零轴翻转',
        (s) => s.spxGex <= -50,
        (s) => s.spxGex < 0,
      ),
      indicator(
        'dealerGamma',
        'Dealer Agg Gamma',
        '十亿美元',
        -10,
        10,
        0.1,
        1,
        '≤ −5 警报 · −8.6 历史底线',
        (s) => s.dealerGamma <= -5,
        (s) => s.dealerGamma < 0,
      ),
      indicator(
        'netDelta',
        '估算净 Delta 流量',
        '',
        -150,
        150,
        1,
        0,
        '零轴为平衡点 · 负值表示净卖出对冲',
        (s) => s.netDelta <= -60,
        (s) => s.netDelta < 0,
      ),
    ],
  },
];

export const checklists = [
  {
    id: 'risk',
    name: '风险升级',
    items: [
      {
        label: '个股与全市场防御同步升温',
        condition: '个股 P/C ≥ 0.80 且全市场 P/C ≥ 1.25',
        matches: (s: Inputs) => s.pcEquity >= 0.8 && s.pcTotal >= 1.25,
      },
      {
        label: '指数期权防御需求上升',
        condition: '指数 P/C ≥ 1.25',
        matches: (s: Inputs) => s.pcIndex >= 1.25,
      },
      {
        label: '做市商 Gamma 触及历史底线',
        condition: 'Dealer Agg Gamma ≤ −8.6 十亿美元',
        matches: (s: Inputs) => s.dealerGamma <= -8.6,
      },
      {
        label: '高波动和期限倒挂共振',
        condition: 'VIX > 28、VIX / VXV > 1 且 VVIX ≥ 110',
        matches: (s: Inputs) => s.vix > 28 && s.vixVxv > 1 && s.vvix >= 110,
      },
    ],
  },
  {
    id: 'reset',
    name: 'OPEX 后修复',
    items: [
      {
        label: '交割后敞口回升',
        condition: 'SPX GEX > −30 十亿美元且净 Delta ≥ 0',
        matches: (s: Inputs) => s.spxGex > -30 && s.netDelta >= 0,
      },
      {
        label: '波动率对冲需求降温',
        condition: 'VVIX < 110',
        matches: (s: Inputs) => s.vvix < 110,
      },
      {
        label: '两段期限比率解除倒挂',
        condition: 'VIX / VXV 和 VIX9D / VIX 均 < 1',
        matches: (s: Inputs) => s.vixVxv < 1 && s.vix9dVix < 1,
      },
      {
        label: '离散交易压力缓和',
        condition: 'VIXEQ / VIX ≥ 1.70 且 VIX < 25',
        matches: (s: Inputs) => s.vixeqVix >= 1.7 && s.vix < 25,
      },
    ],
  },
];

export function stressScore(s: Inputs) {
  const points = (value: number, benign: number, severe: number, weight: number) =>
    Math.max(0, Math.min(1, (value - benign) / (severe - benign))) * weight;
  return Math.round(
    points(s.vix, 14, 36, 15) +
      points(s.vvix, 85, 135, 10) +
      points(s.vixVxv, 0.88, 1.12, 9) +
      points(s.vix9dVix, 0.88, 1.12, 6) +
      points(s.spxGex, 20, -120, 12) +
      points(s.dealerGamma, 1, -9, 10) +
      points(s.netDelta, 20, -140, 8) +
      points(s.vixeqVix, 2.5, 1.35, 15) +
      points(s.pcEquity, 0.5, 0.9, 6) +
      points(s.pcTotal, 0.8, 1.35, 5) +
      points(s.pcIndex, 1, 1.4, 4),
  );
}

export function marketStage(s: Inputs) {
  if (
    (s.vix >= 26 && (s.vixVxv >= 1 || s.vvix >= 110)) ||
    (s.dealerGamma <= -4.5 && s.spxGex <= -50)
  )
    return 3;
  if (s.dealerGamma >= 1.5 && s.spxGex >= 25 && s.vix < 18 && s.skew < 158) return 1;
  if (
    s.vixVxv < 1 &&
    s.vvix < 110 &&
    s.skew < 155 &&
    s.netDelta >= 0 &&
    s.spxGex < 25 &&
    s.vixeqVix < 2
  )
    return 4;
  return 2;
}
