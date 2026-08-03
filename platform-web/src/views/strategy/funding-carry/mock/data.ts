import type {
  FundingChartPanelData,
  FundingExchange,
  FundingExchangeProfile,
  FundingMarketBoardData,
  FundingMarketRange,
  FundingOrderPanelData,
  FundingSymbol,
  FundingViewMode,
} from '../types';

type FundingMetricTone = 'positive' | 'negative' | 'neutral';
type FundingMetricInput =
  | [label: string, value: string]
  | [label: string, value: string, unit: string]
  | [label: string, value: string, unit: string, tone: FundingMetricTone];

export const fundingViewLabels: Record<FundingViewMode, string> = {
  basis: '期现价差',
  funding: '资金费率',
  borrow: '借贷利率',
};

export const fundingRangeLabels: Record<FundingMarketRange, string> = {
  current: '当前',
  '1d': '1日费率',
  '7d': '7日费率',
  '30d': '30日费率',
  '1y': '1年费率',
};

export const defaultExchange: FundingExchange = 'Binance';
export const defaultSymbol: FundingSymbol = 'BTC';

const sharedSymbols: FundingSymbol[] = ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'XAUT'];

function formatPercent(value: number, digits = 2) {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(digits)}%`;
}

function makeResearch(
  exchange: FundingExchange,
  symbol: FundingSymbol,
  netCarry: number,
  basisDrag: number,
  borrowCost: number,
  fundingRate: number,
  stability: number,
  capacity: number,
  note: string,
) {
  const decisionTone = netCarry >= 14 ? 'bull' : netCarry >= 9 ? 'flat' : 'bear';
  const decisionLabel =
    decisionTone === 'bull' ? '值得做' : decisionTone === 'flat' ? '继续观察' : '暂不建议';

  return {
    symbol,
    headline: `${exchange} · ${symbol} 当前更适合放在资金费率研究优先池，而不是直接下沉为执行任务。`,
    note,
    executionMemo: `当前建议把 ${exchange} 的 ${symbol} 放在研究优先级较高的位置，继续跟踪 funding、净 carry、稳定性与容量。后续接入正式系统时，这一页输出给策略层的应是标准化字段，而不是人工解释后的文字。`,
    decision: {
      label: decisionLabel,
      tone: decisionTone,
    },
    chips: ['现货多头', '永续空头', '单交易所内对冲', '研究优先页'],
    breakdownRows: [
      {
        label: 'Funding 收益年化',
        value: formatPercent(netCarry + basisDrag + borrowCost),
        note: '永续空头侧的毛收益口径',
      },
      {
        label: '期现价差拖累',
        value: `-${Math.abs(basisDrag).toFixed(2)}%`,
        note: '基差与对冲效率折损',
      },
      {
        label: '借贷利率',
        value: `-${Math.abs(borrowCost).toFixed(2)}%`,
        note: '现货资金占用与融资成本',
      },
      { label: '净 Carry 年化', value: formatPercent(netCarry), note: '研究排序主口径' },
    ],
    insightBlocks: [
      {
        title: '收益拆解',
        badge: formatPercent(netCarry),
        tone: 'bull',
        description: `Funding ${
          fundingRate >= 0 ? '为正' : '承压'
        }，但真正决定优先级的是净 carry。当前 ${symbol} 在扣除期现价差与借贷成本后，仍保留可研究的收益厚度。`,
        meta: [
          `Funding ${formatPercent(fundingRate, 4)}`,
          `Basis ${formatPercent(basisDrag)}`,
          `Borrow ${formatPercent(borrowCost)}`,
        ],
      },
      {
        title: '稳定性',
        badge: `${stability}`,
        tone: stability >= 78 ? 'bull' : stability >= 65 ? 'flat' : 'bear',
        description: note,
        meta: [`Stability ${stability}`, `Capacity ${capacity}`, 'Regime Watch Enabled'],
      },
      {
        title: '容量判断',
        badge: `${capacity}`,
        tone: capacity >= 82 ? 'bull' : capacity >= 65 ? 'flat' : 'bear',
        description:
          capacity >= 82
            ? '容量较厚，适合中等规模持续跟踪。'
            : capacity >= 65
            ? '容量尚可，但更适合分批执行与限额约束。'
            : '容量偏薄，更适合作为机会观察而非大规模部署对象。',
        meta: ['Spot / Perp 流动性观察', '滑点需要单列', '执行窗口应限时'],
      },
      {
        title: '执行提示',
        badge: '研究页',
        tone: 'flat',
        description: '这一块只保留策略执行所需的规则摘要，不放任务流转表，不混入交易员运营动作。',
        meta: [`Exchange ${exchange}`, `Asset ${symbol}`, 'Spot Long + Perp Short'],
      },
    ],
  };
}

function parseMetric(metric: FundingMetricInput) {
  if (metric.length === 2) {
    const [label, value] = metric;
    return { label, value };
  }
  if (metric.length === 3) {
    const [label, value, unit] = metric;
    return { label, value, unit };
  }
  const [label, value, unit, tone] = metric;
  return { label, value, unit, tone };
}

function makeProfile(
  exchange: FundingExchange,
  metrics: FundingMetricInput[],
  rows: Array<[FundingSymbol, number, number, number, number, number, number, string]>,
): FundingExchangeProfile {
  const snapshots = rows.map(
    ([symbol, fundingRate, netCarry, basisDrag, borrowCost, stability, capacity]) => ({
      symbol,
      fundingRate,
      netCarry,
      basisDrag,
      borrowCost,
      stability,
      capacity,
    }),
  );
  const research = Object.fromEntries(
    rows.map(
      ([symbol, fundingRate, netCarry, basisDrag, borrowCost, stability, capacity, note]) => [
        symbol,
        makeResearch(
          exchange,
          symbol,
          netCarry,
          basisDrag,
          borrowCost,
          fundingRate,
          stability,
          capacity,
          note,
        ),
      ],
    ),
  ) as Record<FundingSymbol, FundingExchangeProfile['research'][FundingSymbol]>;
  return {
    exchange,
    updatedAt: '2026-06-24 16:09:05',
    overviewTitle: '资金费率套利总览',
    overviewDescription: '先判断是否值得研究，再决定是否值得进入正式策略池。',
    metrics: metrics.map(parseMetric),
    snapshots,
    research,
  };
}

export const fundingCarryProfiles: Record<FundingExchange, FundingExchangeProfile> = {
  Binance: makeProfile(
    'Binance',
    [
      ['账户净值', '450,525.47', 'USD'],
      ['策略类型', '资金套利', 'Mode'],
      ['保证金余额', '413,860.97', 'USD'],
      ['收益率', '11.37', '%', 'positive'],
      ['过去24h盈亏', '-32.16', 'USD', 'negative'],
      ['累计收益', '51,198.61', 'USD'],
      ['当前净 Carry', '+12.40', '%', 'positive'],
      ['稳定度评分', '84', '0-100'],
    ],
    [
      ['BTC', 0.008, 12.4, 4.2, 2.1, 84, 97, '主流大币，适合中等规模与滚动跟踪。'],
      ['ETH', -0.0041, 9.1, 3.6, 2.4, 79, 90, '收益不差，但 funding 与基差波动更明显。'],
      ['SOL', 0.0132, 18.7, 7.9, 3.5, 68, 74, '弹性高，但更容易从结构机会变成情绪机会。'],
      ['DOGE', -0.0006, 13.3, 5.8, 2.9, 58, 70, '零售驱动更强，适合观察，不适合盲目放大。'],
      ['XRP', -0.0056, 11.8, 4.9, 2.6, 66, 78, '资金费率与政策敏感度共振，需要看 regime。'],
      ['XAUT', 0.0021, 7.5, 1.4, 1.8, 73, 42, '标的特殊，容量与交易便利性是主要约束。'],
    ],
  ),
  OKX: makeProfile(
    'OKX',
    [
      ['账户净值', '391,842.22', 'USD'],
      ['策略类型', '资金套利', 'Mode'],
      ['保证金余额', '346,001.13', 'USD'],
      ['收益率', '9.82', '%', 'positive'],
      ['过去24h盈亏', '+118.52', 'USD', 'positive'],
      ['累计收益', '43,772.43', 'USD'],
      ['当前净 Carry', '+10.60', '%', 'positive'],
      ['稳定度评分', '81', '0-100'],
    ],
    [
      ['BTC', 0.0062, 10.6, 3.9, 1.8, 81, 94, '深度稳，执行体验平衡，适合作为标准观察样本。'],
      ['ETH', -0.0034, 8.4, 3.3, 2.1, 75, 86, '相对平稳，但收益厚度略弱于 Binance。'],
      ['SOL', 0.0111, 16.1, 6.7, 3.0, 66, 69, '机会仍在，但要更严控成交成本。'],
      ['DOGE', -0.0004, 11.5, 4.8, 2.5, 57, 65, '容量一般，适合事件窗口而非长时间挂着。'],
      ['XRP', -0.0042, 10.2, 4.2, 2.2, 64, 71, '可观察，但不宜作为高权重品种。'],
      ['XAUT', 0.0017, 6.8, 1.2, 1.5, 72, 40, '更像补充型机会，不应主打。'],
    ],
  ),
  Bybit: makeProfile(
    'Bybit',
    [
      ['账户净值', '278,560.91', 'USD'],
      ['策略类型', '资金套利', 'Mode'],
      ['保证金余额', '242,170.28', 'USD'],
      ['收益率', '8.44', '%', 'positive'],
      ['过去24h盈亏', '-86.70', 'USD', 'negative'],
      ['累计收益', '31,890.20', 'USD'],
      ['当前净 Carry', '+9.40', '%', 'positive'],
      ['稳定度评分', '76', '0-100'],
    ],
    [
      ['BTC', 0.0054, 9.4, 3.4, 1.7, 76, 88, '结构仍可看，但厚度和稳定性略次于前两家。'],
      ['ETH', -0.0028, 7.6, 3.0, 1.9, 72, 81, '比较适合做比较样本，不一定是最优执行地。'],
      ['SOL', 0.0102, 14.8, 6.0, 2.8, 63, 64, '收益有吸引力，但更吃风格与时机。'],
      ['DOGE', -0.0003, 10.1, 4.3, 2.1, 54, 61, '适合小规模、短窗口。'],
      ['XRP', -0.0038, 9.5, 3.9, 2.0, 61, 67, '边际可看，但更适合作为备选。'],
      ['XAUT', 0.0012, 5.4, 1.0, 1.4, 69, 35, '容量偏小，优先级较低。'],
    ],
  ),
};

export const fundingMarketBoard: FundingMarketBoardData = {
  updatedAt: '2026-06-24 16:12:30',
  symbolOptions: ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'XAUT'],
  resolutionOptions: ['30分钟', '1小时', '4小时', '8小时'],
  summaryCards: [
    { title: '资金费率套利', value: '0.0015%', subtitle: 'BTC 持仓加权资金费率', tone: 'positive' },
    {
      title: '累计资金费率',
      value: '-0.0008%',
      subtitle: 'ETH 持仓加权资金费率',
      tone: 'negative',
    },
    {
      title: '成交额加权费率',
      value: '0.0015%',
      subtitle: 'BTC 成交额加权资金费率',
      tone: 'positive',
    },
    {
      title: '净资金费率',
      value: '-0.0008%',
      subtitle: 'ETH 成交额加权资金费率',
      tone: 'negative',
    },
  ],
  highest: [
    { market: 'Gate POWER/USDT', value: 0.3395 },
    { market: 'Binance KORU/USDT', value: 0.323 },
    { market: 'Bybit SIREN/USDT', value: 0.2514 },
    { market: 'Gate HANA/USDT', value: 0.2325 },
    { market: 'Bitget SIREN/USDT', value: 0.2057 },
  ],
  lowest: [
    { market: 'Gate VIC/USDT', value: -1.6972 },
    { market: 'Bybit LRC/USDT', value: -1.599 },
    { market: 'Gate T/USDT', value: -1.4208 },
    { market: 'Bybit T/USDT', value: -1.2247 },
    { market: 'Bybit TAIKO/USDT', value: -1.1714 },
  ],
  usdtExchanges: ['Binance', 'OKX', 'Bybit', 'KuCoin', 'Gate', 'Bitget', 'MEXC', 'WhiteBIT'],
  inverseExchanges: ['Binance', 'OKX', 'Bybit'],
  rows: [
    {
      symbol: 'BTC',
      usdtPerps: {
        Binance: 0.0003,
        OKX: 0.0033,
        Bybit: -0.0021,
        KuCoin: -0.0012,
        Gate: -0.0003,
        Bitget: -0.0004,
        MEXC: 0.0002,
        WhiteBIT: 0.0158,
      },
      inversePerps: { Binance: 0.0095, OKX: 0.0041, Bybit: 0.0051 },
    },
    {
      symbol: 'ETH',
      usdtPerps: {
        Binance: -0.0017,
        OKX: -0.0029,
        Bybit: 0.0014,
        KuCoin: 0.0071,
        Gate: 0.0029,
        Bitget: 0.0039,
        MEXC: -0.0017,
        WhiteBIT: -0.002,
      },
      inversePerps: { Binance: -0.0122, OKX: -0.0059, Bybit: -0.003 },
    },
    {
      symbol: 'SOL',
      usdtPerps: {
        Binance: -0.0189,
        OKX: -0.0096,
        Bybit: -0.0187,
        KuCoin: 0.01,
        Gate: -0.0175,
        Bitget: -0.0187,
        MEXC: -0.0189,
        WhiteBIT: -0.0273,
      },
      inversePerps: { Binance: -0.0129, OKX: -0.0099, Bybit: -0.0087 },
    },
    {
      symbol: 'XRP',
      usdtPerps: {
        Binance: -0.0075,
        OKX: -0.0059,
        Bybit: -0.0016,
        KuCoin: 0.006,
        Gate: 0.0006,
        Bitget: -0.0036,
        MEXC: -0.0075,
        WhiteBIT: 0.01,
      },
      inversePerps: { Binance: -0.0114, OKX: 0.0064, Bybit: -0.0164 },
    },
    {
      symbol: 'DOGE',
      usdtPerps: {
        Binance: -0.0033,
        OKX: 0.0007,
        Bybit: -0.0214,
        KuCoin: 0.01,
        Gate: 0.01,
        Bitget: -0.0023,
        MEXC: -0.0032,
        WhiteBIT: -0.0101,
      },
      inversePerps: { Binance: -0.0006, OKX: 0.01, Bybit: 0.01 },
    },
    {
      symbol: 'BNB',
      usdtPerps: {
        Binance: 0.0,
        OKX: -0.0056,
        Bybit: -0.0258,
        KuCoin: 0.0009,
        Gate: -0.0112,
        Bitget: -0.0186,
        MEXC: 0.0,
        WhiteBIT: 0.01,
      },
      inversePerps: { Binance: 0.0476, OKX: null, Bybit: null },
    },
    {
      symbol: 'XAUT',
      usdtPerps: {
        Binance: -0.0067,
        OKX: -0.0022,
        Bybit: 0.0094,
        KuCoin: null,
        Gate: -0.0044,
        Bitget: 0.005,
        MEXC: -0.0066,
        WhiteBIT: 0.01,
      },
      inversePerps: { Binance: null, OKX: null, Bybit: null },
    },
  ],
};

export const fundingChartPanel: FundingChartPanelData = {
  title: 'BTC持仓加权资金费率',
  legendPrice: 'BTC价格',
  legendFunding: '持仓加权',
  points: [
    { date: '2026-05-28', price: 98000, funding: 0.009 },
    { date: '2026-05-30', price: 97200, funding: 0.006 },
    { date: '2026-06-01', price: 95500, funding: -0.002 },
    { date: '2026-06-03', price: 96000, funding: 0.001 },
    { date: '2026-06-05', price: 94800, funding: -0.004 },
    { date: '2026-06-07', price: 92400, funding: -0.011 },
    { date: '2026-06-09', price: 93100, funding: -0.008 },
    { date: '2026-06-11', price: 94400, funding: -0.005 },
    { date: '2026-06-13', price: 93800, funding: 0.004 },
    { date: '2026-06-15', price: 92700, funding: 0.009 },
    { date: '2026-06-17', price: 91400, funding: -0.003 },
    { date: '2026-06-19', price: 90500, funding: 0.005 },
    { date: '2026-06-21', price: 91800, funding: 0.007 },
    { date: '2026-06-23', price: 91000, funding: 0.003 },
    { date: '2026-06-24', price: 90600, funding: -0.002 },
  ],
};

export const fundingOrderPanel: FundingOrderPanelData = {
  strategyLabel: '沪金伦敦金多空策略 / SHFE_XAU',
  nextWindow: '13:30:00 — 15:00:00',
  accountMetrics: [
    { label: '总计 AUM', value: '20,343,790.35 CNY' },
    { label: '总杠杆', value: '1.1X' },
    { label: '净金账户', value: '11,312,370.08 CNY', tone: 'neutral' },
    { label: '伦敦金账户', value: '1,324,857.38 USD', tone: 'neutral' },
  ],
  executionMetrics: [
    { label: '可用资金率', value: '92.69%', tone: 'positive' },
    { label: '整体杠杆', value: '1.4971 → 1.4971', tone: 'neutral' },
    { label: '预计对冲比率', value: '0.0000% → 0.0000%', tone: 'positive' },
  ],
  leftLegTitle: '现货腿 / 沪金2604',
  rightLegTitle: '永续腿 / XAUUSD',
  leftLegMetrics: [
    { label: '最新价', value: '1058.5', tone: 'negative' },
    { label: '当前持仓', value: '0' },
    { label: '持仓价值 CNY', value: '0' },
    { label: '可用余额', value: '10,485,527 CNY' },
  ],
  rightLegMetrics: [
    { label: '最新价', value: '4,820.01', tone: 'positive' },
    { label: '当前持仓', value: '0' },
    { label: '持仓价值 USD', value: '0' },
    { label: '可用余额', value: '0 USD' },
  ],
  actionButtons: ['策略开仓', '策略平仓', '止盈', '网格开仓'],
  impactMetrics: [
    { label: '资金占用变化', value: '92.69% → 92.69%', tone: 'positive' },
    { label: '最大杠杆约束', value: 'MAX=20.0000', tone: 'negative' },
    { label: '对冲偏离', value: '0.0000%', tone: 'positive' },
  ],
  logs: [
    '2026-06-24 15:44:45 · 开仓成功，净金下单量为2，伦敦金下单量为0.64',
    '2026-06-24 15:44:43 · 策略开仓订单已完成，成交数量：2，总成交数量：2',
    '2026-06-24 15:44:22 · 发现执行策略开仓，总下单量=净金2；伦敦金0.64',
    '2026-06-24 10:43:04 · 最终计算：净金5手，伦敦金1.61份，误差-7.66',
  ],
};

export const allFundingSymbols = sharedSymbols;
