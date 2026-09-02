export type WidgetKind =
  | 'advanced-chart'
  | 'symbol-overview'
  | 'market-overview'
  | 'technical-analysis'
  | 'local-chart';

export type LocalWidgetKey =
  | 'macro-market-detail-table'
  | 'macro-global-m2'
  | 'macro-global-m2-yoy'
  | 'macro-growth-production'
  | 'macro-growth-labor'
  | 'macro-growth-activity'
  | 'macro-actual-inflation'
  | 'macro-upstream-inflation'
  | 'macro-market-inflation'
  | 'macro-rate-corridor'
  | 'macro-risk-hy-oas'
  | 'macro-risk-credit-ratio'
  | 'gold-market-detail-table'
  | 'crypto-market-detail-table'
  | 'btc-etf-flow'
  | 'btc-treasury-flow'
  | 'spdr-daily-flow'
  | 'spdr-holdings-vs-price'
  | 'etf-weekly-flows'
  | 'etf-ytd-summary'
  | 'central-bank-holders'
  | 'central-bank-buyers'
  | 'gold-vs-nominal'
  | 'gold-vs-breakeven'
  | 'gold-vs-real'
  | 'gold-vs-gvz'
  | 'cftc-gold-net'
  | 'cftc-gold-percentile'
  | 'cftc-silver-net'
  | 'cftc-silver-percentile'
  | 'cftc-copper-net'
  | 'cftc-copper-percentile'
  | 'cftc-wti-net'
  | 'cftc-wti-percentile'
  | 'cftc-natural-gas-net'
  | 'cftc-natural-gas-percentile'
  | 'commodity-wti-curve'
  | 'commodity-brent-curve'
  | 'commodity-copper-curve'
  | 'commodity-cme-inventory'
  | 'commodity-lme-inventory'
  | 'commodity-copper-spreads'
  | 'commodity-brent-wti-spread'
  | 'commodity-ovx'
  | 'commodity-cvol'
  | 'eia-crude-stocks'
  | 'eia-products-stocks';

export interface WidgetConfig {
  kind: WidgetKind;
  title: string;
  subtitle: string;
  sourceNote?: string;
  height?: number;
  scriptSrc?: string;
  config?: Record<string, unknown>;
  localKey?: LocalWidgetKey;
}

export interface ChartSection {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  layout?: 'hero' | 'two' | 'three';
  widgets: WidgetConfig[];
}

export interface ResearchModule {
  id: string;
  label: string;
  eyebrow: string;
  headline: string;
  summary: string;
  summaryPoints: string[];
  formula?: {
    title: string;
    description: string;
  };
  sourceLinks: Array<{
    label: string;
    href: string;
  }>;
  sections: ChartSection[];
}

const tvBase = {
  colorTheme: 'light',
  locale: 'zh_CN',
  autosize: true,
};

function advancedChart(
  title: string,
  subtitle: string,
  symbol: string,
  options: Partial<Record<string, unknown>> = {},
): WidgetConfig {
  return {
    kind: 'advanced-chart',
    title,
    subtitle,
    height: Number(options.height ?? 420),
    scriptSrc: 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js',
    config: {
      ...tvBase,
      symbol,
      interval: 'D',
      timezone: 'Asia/Shanghai',
      theme: 'light',
      style: '1',
      allow_symbol_change: true,
      hide_side_toolbar: true,
      withdateranges: true,
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: true,
      details: false,
      hotlist: false,
      calendar: false,
      studies: [],
      support_host: 'https://www.tradingview.com',
      ...options,
    },
  };
}

function localChart(
  title: string,
  subtitle: string,
  localKey: LocalWidgetKey,
  options: { height?: number; sourceNote?: string } = {},
): WidgetConfig {
  return {
    kind: 'local-chart',
    title,
    subtitle,
    localKey,
    height: options.height ?? 360,
    sourceNote: options.sourceNote,
  };
}

export const pageSections = [
  { id: 'macro', index: '01', label: '宏观', description: '经济、通胀、流动性。' },
  { id: 'gold', index: '02', label: '商品', description: '贵金属、能源、资金面与比价结构。' },
  { id: 'crypto', index: '03', label: '加密', description: 'BTC 主图、扩散、风险偏好。' },
];

export const researchModules: ResearchModule[] = [
  {
    id: 'macro',
    label: '宏观',
    eyebrow: 'Macro',
    headline: '先定宏观环境，再解释黄金和加密的价格主线。',
    summary:
      '宏观页负责给出大的环境判断，先看流动性，再看利率汇率与增长通胀，最后再映射到风险偏好。',
    summaryPoints: ['先看流动性', '再看利率汇率', '最后看风险偏好与经济'],
    sourceLinks: [
      { label: 'Dollar Liquidity', href: 'https://dollarliquidity.com/zh' },
      { label: 'FRED', href: 'https://fred.stlouisfed.org/' },
      { label: 'TradingView', href: 'https://www.tradingview.com/' },
    ],
    sections: [
      {
        id: 'macro-liquidity',
        eyebrow: 'Liquidity',
        title: '流动性总图',
        description: '先看净美元流动性，再拆解 Fed、TGA 与逆回购的贡献。',
        layout: 'hero',
        widgets: [
          advancedChart(
            'Net Dollar Liquidity',
            'Formula: WALCL - WDTGAL - RRPONTTLD',
            'FRED:WALCL-FRED:WDTGAL-FRED:RRPONTTLD',
            {
              height: 640,
              hide_side_toolbar: false,
            },
          ),
        ],
      },
      {
        id: 'macro-global-m2',
        eyebrow: 'Global Liquidity',
        title: 'Global M2 Proxy',
        description:
          '美国、中国、欧元区、日本与英国广义货币按共同月份对齐，并使用 ECB 官方日汇率月均值折算为美元。该指标为方法论代理，不是官方统一全球 M2。',
        layout: 'two',
        widgets: [
          localChart(
            'Global M2 Level',
            'Aggregate and five regional USD components',
            'macro-global-m2',
            {
              height: 420,
              sourceNote: 'Fed / PBOC-validated adapter / ECB / BOJ / BoE; ECB reference FX',
            },
          ),
          localChart(
            'Global M2 YoY',
            'Five-region methodology-based proxy growth',
            'macro-global-m2-yoy',
            { height: 420 },
          ),
        ],
      },
      {
        id: 'macro-market',
        eyebrow: 'Market',
        title: '宏观市场明细',
        description: '统一终端式明细布局，按流动性、利率汇率、风险偏好与经济四组变量展开。',
        layout: 'hero',
        widgets: [
          localChart(
            'Macro Market Detail',
            '统一终端式明细布局，聚焦流动性、利率汇率、风险偏好与经济四组变量。',
            'macro-market-detail-table',
            {
              height: 620,
              sourceNote: '',
            },
          ),
        ],
      },
      {
        id: 'macro-growth',
        eyebrow: 'Growth',
        title: '增长与经济活动',
        description: '生产、劳动力与广义活动指标使用各自适配频率，不对低频数据补点。',
        layout: 'two',
        widgets: [
          localChart(
            '增长与生产',
            'Real GDP YoY / Industrial Production YoY',
            'macro-growth-production',
          ),
          localChart('初请失业金四周均值', 'Initial Claims 4W MA', 'macro-growth-labor'),
          localChart('广义经济活动', 'CFNAI / CFNAIMA3', 'macro-growth-activity'),
        ],
      },
      {
        id: 'macro-inflation',
        eyebrow: 'Inflation',
        title: '实际、上游与市场隐含通胀',
        description: '明确区分已实现通胀、上游价格和中长期市场定价。',
        layout: 'two',
        widgets: [
          localChart('实际通胀', 'CPI / Core CPI / PCE / Core PCE YoY', 'macro-actual-inflation'),
          localChart('上游通胀', 'PPI Final Demand YoY', 'macro-upstream-inflation'),
          localChart('市场隐含通胀', '5Y / 10Y Breakeven / 5Y5Y Forward', 'macro-market-inflation'),
        ],
      },
      {
        id: 'macro-rates',
        eyebrow: 'Rates',
        title: '短端利率走廊',
        description: '目标区间、准备金利率、逆回购、EFFR 与 SOFR 的统一比较。',
        layout: 'hero',
        widgets: [
          localChart(
            'Short-End Rate Corridor',
            'Fed target / IORB / ON RRP / EFFR / SOFR',
            'macro-rate-corridor',
          ),
        ],
      },
      {
        id: 'macro-risk-appetite',
        eyebrow: 'Risk Appetite',
        title: '信用风险偏好',
        description: '分别观察高收益信用利差与 HYG/LQD 相对表现，避免混用纵轴。',
        layout: 'two',
        widgets: [
          localChart(
            '美国高收益债 OAS',
            'ICE BofA US High Yield OAS via FRED',
            'macro-risk-hy-oas',
          ),
          localChart('HYG / LQD', '同日 adjusted close ratio', 'macro-risk-credit-ratio'),
        ],
      },
    ],
  },
  {
    id: 'gold',
    label: '商品',
    eyebrow: 'Commodities',
    headline: '商品页按主图、市场横截面、资金面、官方部门、利率与波动率展开。',
    summary: '这一页不再只盯黄金，而是把贵金属、能源、工业金属与资金结构放进同一套研究壳里。',
    summaryPoints: ['先看黄金主图', '再看商品横截面', '最后看资金与利率约束'],
    sourceLinks: [],
    sections: [
      {
        id: 'gold-main',
        eyebrow: 'Price',
        title: '黄金主图',
        description: '',
        layout: 'hero',
        widgets: [
          advancedChart('XAUUSD Main Chart', '', 'OANDA:XAUUSD', {
            height: 620,
            hide_side_toolbar: false,
          }),
          advancedChart('Gold IV (GVZCLS)', '', 'FRED:GVZCLS', {
            height: 320,
          }),
        ],
      },
      {
        id: 'gold-market',
        eyebrow: 'Market',
        title: '商品市场明细',
        description: '沿用统一市场明细结构，补齐商品横截面与相对比价。',
        layout: 'hero',
        widgets: [
          localChart('Commodity Market Detail', '', 'gold-market-detail-table', {
            height: 620,
            sourceNote: '',
          }),
        ],
      },
      {
        id: 'gold-flows',
        eyebrow: 'ETF & Flows',
        title: 'ETF 与资金面',
        description: '',
        layout: 'two',
        widgets: [
          localChart('全球各地区 ETF 每周流入', '', 'etf-weekly-flows', {
            height: 430,
            sourceNote: 'External Link · World Gold Council · permission_required',
          }),
          localChart('全球 ETF 年内汇总', '', 'etf-ytd-summary', {
            height: 430,
            sourceNote: 'External Link · World Gold Council · permission_required',
          }),
          localChart('金价 vs SPDR 每日流量', '', 'spdr-daily-flow', {
            height: 420,
            sourceNote: 'External Link · SPDR Gold Shares · permission_required',
          }),
          localChart('SPDR 持仓量 vs 黄金价格', '', 'spdr-holdings-vs-price', {
            height: 420,
            sourceNote: 'External Link · SPDR Gold Shares · permission_required',
          }),
        ],
      },
      {
        id: 'gold-central-bank',
        eyebrow: 'Official Sector',
        title: '央行购金与官方储备',
        description: '',
        layout: 'two',
        widgets: [
          localChart('官方黄金储备前十', '', 'central-bank-holders', {
            height: 420,
            sourceNote: 'External Link · World Gold Council · permission_required',
          }),
          localChart('近一年持续增持的央行', '', 'central-bank-buyers', {
            height: 420,
            sourceNote: 'External Link · World Gold Council · permission_required',
          }),
        ],
      },
      {
        id: 'gold-rates',
        eyebrow: 'Rates & Inflation',
        title: '利率与通胀',
        description: '把名义利率、通胀预期和实际利率放在同一组里看。',
        layout: 'two',
        widgets: [
          localChart(
            '金价 vs 10Y 名义利率',
            '左轴黄金价格，右轴美国 10 年名义国债收益率',
            'gold-vs-nominal',
            {
              height: 400,
              sourceNote: 'External Link · U.S. Treasury · no local gold proxy',
            },
          ),
          localChart(
            '金价 vs 10Y 通胀预期',
            '用名义 10Y 减实际 10Y 得到 breakeven',
            'gold-vs-breakeven',
            {
              height: 400,
              sourceNote: 'External Link · U.S. Treasury · no local gold proxy',
            },
          ),
          localChart('金价 vs 10Y 实际利率', '实际利率是黄金最硬的宏观约束之一', 'gold-vs-real', {
            height: 400,
            sourceNote: 'External Link · U.S. Treasury · no local gold proxy',
          }),
          advancedChart('Gold vs DXY', '黄金与美元指数', 'OANDA:XAUUSD', {
            compareSymbols: [{ symbol: 'TVC:DXY', position: 'SameScale' }],
            height: 420,
          }),
        ],
      },
      {
        id: 'commodity-positioning',
        eyebrow: 'Positioning / CFTC',
        title: '核心商品持仓结构',
        description:
          'CFTC Disaggregated Futures Only 周报；净持仓按明确 Contract Market Code 映射，拥挤度为 Managed Money Net 的滚动 260 周历史分位。',
        layout: 'two',
        widgets: [
          localChart('Gold Net Position', 'Managed Money / Producer-Merchant', 'cftc-gold-net'),
          localChart('Gold 5Y Percentile', 'Managed Money Net', 'cftc-gold-percentile'),
          localChart('Silver Net Position', 'Managed Money / Producer-Merchant', 'cftc-silver-net'),
          localChart('Silver 5Y Percentile', 'Managed Money Net', 'cftc-silver-percentile'),
          localChart('Copper Net Position', 'Managed Money / Producer-Merchant', 'cftc-copper-net'),
          localChart('Copper 5Y Percentile', 'Managed Money Net', 'cftc-copper-percentile'),
          localChart('WTI Net Position', 'Managed Money / Producer-Merchant', 'cftc-wti-net'),
          localChart('WTI 5Y Percentile', 'Managed Money Net', 'cftc-wti-percentile'),
          localChart(
            'Natural Gas Net Position',
            'Managed Money / Producer-Merchant',
            'cftc-natural-gas-net',
          ),
          localChart(
            'Natural Gas 5Y Percentile',
            'Managed Money Net',
            'cftc-natural-gas-percentile',
          ),
        ],
      },
      {
        id: 'commodity-eia-inventory',
        eyebrow: 'Inventory / EIA',
        title: '美国能源库存',
        description: 'EIA API v2 官方周频库存；保留周频口径和 stale 状态，不做日频 forward-fill。',
        layout: 'two',
        widgets: [
          localChart('Crude Oil Stocks', 'U.S. Commercial / Cushing', 'eia-crude-stocks', {
            sourceNote: 'Native · U.S. EIA Open Data API v2 · weekly',
          }),
          localChart(
            'Products Stocks',
            'Motor Gasoline / Distillate Fuel Oil',
            'eia-products-stocks',
            { sourceNote: 'Native · U.S. EIA Open Data API v2 · weekly' },
          ),
        ],
      },
      {
        id: 'commodity-official-references',
        eyebrow: 'Curves / Physical / Volatility',
        title: '期限结构、库存与波动率',
        description:
          'CME、ICE、LME 与 Cboe 的受限市场数据按 Phase F 采用官方 External Link；不在本地复制曲线、库存或指数历史。',
        layout: 'two',
        widgets: [
          localChart('WTI Futures Curve', 'CME official contract chain', 'commodity-wti-curve'),
          localChart('Brent Futures Curve', 'ICE official contract chain', 'commodity-brent-curve'),
          localChart('Copper Prompt Curve', 'LME official contract page', 'commodity-copper-curve'),
          localChart(
            'CME Delivery & Stocks',
            'CME official delivery reports',
            'commodity-cme-inventory',
          ),
          localChart(
            'LME Copper Stocks',
            'LME official reports and data',
            'commodity-lme-inventory',
          ),
          localChart(
            'Copper Cross-Market Spreads',
            'COMEX / LME / SHFE legs',
            'commodity-copper-spreads',
          ),
          localChart('Brent - WTI Spread', 'ICE / CME licensed legs', 'commodity-brent-wti-spread'),
          localChart('OVX', 'Cboe Crude Oil ETF Volatility Index', 'commodity-ovx'),
          localChart('CVOL', 'CME Group Volatility Indexes', 'commodity-cvol'),
        ],
      },
    ],
  },
  {
    id: 'crypto',
    label: '加密',
    eyebrow: 'Crypto',
    headline: '加密页按 BTC 主图、市场明细、ETF 资金、扩散结构与财库公司购币展开。',
    summary:
      '加密不能脱离宏观看，重点是看 BTC 主线、ETF 资金是否持续吸纳、以及风险是否继续向高 beta 扩散。',
    summaryPoints: ['BTC 主图先看', '再看主流币与 ETF 资金', '最后看扩散与财库公司购币'],
    sourceLinks: [],
    sections: [
      {
        id: 'crypto-main',
        eyebrow: 'BTC',
        title: 'BTC 主图',
        description: '',
        layout: 'hero',
        widgets: [
          advancedChart('BTCUSDT Main Chart', '', 'BINANCE:BTCUSDT', {
            height: 620,
            hide_side_toolbar: false,
          }),
          advancedChart('BTC IV (DERIBIT DVOL)', '', 'DERIBIT:DVOL', {
            height: 320,
          }),
        ],
      },
      {
        id: 'crypto-market',
        eyebrow: 'Market',
        title: '加密市场明细',
        description: '沿用统一市场明细结构，补齐主流资产、代理资产与相对比价。',
        layout: 'hero',
        widgets: [
          localChart('Crypto Market Detail', '', 'crypto-market-detail-table', {
            height: 620,
            sourceNote: '',
          }),
        ],
      },
      {
        id: 'crypto-etf',
        eyebrow: 'ETF Flow',
        title: 'BTC ETF 与价格',
        description: '',
        layout: 'two',
        widgets: [
          localChart('BTC ETF 日流量 vs BTC 价格', '', 'btc-etf-flow', {
            height: 420,
            sourceNote: '',
          }),
          localChart('Bitcoin Treasuries Weekly Net Inflow', '', 'btc-treasury-flow', {
            height: 420,
            sourceNote: '',
          }),
        ],
      },
    ],
  },
];
