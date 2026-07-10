export type WidgetKind =
  | 'advanced-chart'
  | 'symbol-overview'
  | 'market-overview'
  | 'technical-analysis'
  | 'local-chart';

export type LocalWidgetKey =
  | 'macro-market-detail-table'
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
  | 'gold-vs-gvz';

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

function symbolOverview(
  title: string,
  subtitle: string,
  symbols: [string, string][],
  options: Partial<Record<string, unknown>> = {},
): WidgetConfig {
  return {
    kind: 'symbol-overview',
    title,
    subtitle,
    height: Number(options.height ?? 360),
    scriptSrc: 'https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js',
    config: {
      ...tvBase,
      symbols,
      chartOnly: false,
      width: '100%',
      height: '100%',
      lineWidth: 2,
      isTransparent: false,
      chartType: 'area',
      scalePosition: 'right',
      scaleMode: 'Normal',
      fontFamily: 'Segoe UI, PingFang SC, Microsoft YaHei, sans-serif',
      fontSize: '10',
      valuesTracking: '1',
      changeMode: 'price-and-percent',
      dateRanges: ['1d|1', '1m|30', '3m|60', '12m|1D', '60m|1W', 'all|1M'],
      lineType: 0,
      backgroundColor: '#ffffff',
      gridLineColor: 'rgba(15, 23, 42, 0.08)',
      widgetFontColor: '#0f172a',
      upColor: '#16a34a',
      downColor: '#dc2626',
      borderUpColor: '#16a34a',
      borderDownColor: '#dc2626',
      wickUpColor: '#16a34a',
      wickDownColor: '#dc2626',
      ...options,
    },
  };
}

function technicalAnalysis(
  title: string,
  subtitle: string,
  symbol: string,
  interval = '1D',
): WidgetConfig {
  return {
    kind: 'technical-analysis',
    title,
    subtitle,
    height: 390,
    scriptSrc: 'https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js',
    config: {
      interval,
      width: '100%',
      isTransparent: false,
      height: '100%',
      symbol,
      showIntervalTabs: true,
      displayMode: 'single',
      locale: 'zh_CN',
      colorTheme: 'light',
    },
  };
}

function marketOverview(
  title: string,
  subtitle: string,
  tabs: Array<{ title: string; symbols: Array<Record<string, string>> }>,
): WidgetConfig {
  return {
    kind: 'market-overview',
    title,
    subtitle,
    height: 420,
    scriptSrc: 'https://s3.tradingview.com/external-embedding/embed-widget-market-overview.js',
    config: {
      colorTheme: 'light',
      dateRange: '12M',
      showChart: true,
      locale: 'zh_CN',
      largeChartUrl: '',
      isTransparent: false,
      showSymbolLogo: true,
      showFloatingTooltip: false,
      width: '100%',
      height: '100%',
      plotLineColorGrowing: 'rgba(22, 163, 74, 1)',
      plotLineColorFalling: 'rgba(220, 38, 38, 1)',
      gridLineColor: 'rgba(15, 23, 42, 0.08)',
      scaleFontColor: 'rgba(15, 23, 42, 0.58)',
      belowLineFillColorGrowing: 'rgba(22, 163, 74, 0.12)',
      belowLineFillColorFalling: 'rgba(220, 38, 38, 0.12)',
      belowLineFillColorGrowingBottom: 'rgba(22, 163, 74, 0.02)',
      belowLineFillColorFallingBottom: 'rgba(220, 38, 38, 0.02)',
      symbolActiveColor: 'rgba(22, 93, 255, 0.12)',
      tabs,
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
    summary: '宏观页负责给出大的环境判断，先看流动性，再看利率汇率与增长通胀，最后再映射到风险偏好。',
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
          advancedChart('Net Dollar Liquidity', 'Formula: WALCL - WDTGAL - RRPONTTLD', 'FRED:WALCL-FRED:WDTGAL-FRED:RRPONTTLD', {
            height: 640,
            hide_side_toolbar: false,
          }),
        ],
      },
      {
        id: 'macro-market',
        eyebrow: 'Market',
        title: '宏观市场明细',
        description: '统一终端式明细布局，按流动性、利率汇率、风险偏好与经济四组变量展开。',
        layout: 'hero',
        widgets: [
          localChart('Macro Market Detail', '统一终端式明细布局，聚焦流动性、利率汇率、风险偏好与经济四组变量。', 'macro-market-detail-table', {
            height: 620,
            sourceNote: '数据展示：前端静态设计稿，后续再接入实时宏观行情与衍生指标',
          }),
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
            sourceNote: '数据展示：前端静态设计稿，后续再接入实时行情',
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
            sourceNote: '数据源：World Gold Council ETF flows-chart2 / archive-tablegroup API',
          }),
          localChart('全球 ETF 年内汇总', '', 'etf-ytd-summary', {
            height: 430,
            sourceNote: '数据源：World Gold Council regional year-to-date dataset',
          }),
          localChart('金价 vs SPDR 每日流量', '', 'spdr-daily-flow', {
            height: 420,
            sourceNote: '数据源：SPDR Gold Shares historical archive',
          }),
          localChart('SPDR 持仓量 vs 黄金价格', '', 'spdr-holdings-vs-price', {
            height: 420,
            sourceNote: '数据源：SPDR Gold Shares historical archive',
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
            sourceNote: '数据源：World Gold Council central bank reserves snapshot API',
          }),
          localChart('近一年持续增持的央行', '', 'central-bank-buyers', {
            height: 420,
            sourceNote: '数据源：World Gold Council date_range reserves API',
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
          localChart('金价 vs 10Y 名义利率', '左轴黄金价格，右轴美国 10 年名义国债收益率', 'gold-vs-nominal', {
            height: 400,
            sourceNote: '数据源：SPDR archive gold proxy + U.S. Treasury nominal yield curve',
          }),
          localChart('金价 vs 10Y 通胀预期', '用名义 10Y 减实际 10Y 得到 breakeven', 'gold-vs-breakeven', {
            height: 400,
            sourceNote: '数据源：U.S. Treasury nominal/real yield curves',
          }),
          localChart('金价 vs 10Y 实际利率', '实际利率是黄金最硬的宏观约束之一', 'gold-vs-real', {
            height: 400,
            sourceNote: '数据源：SPDR archive gold proxy + U.S. Treasury real yield curve',
          }),
          advancedChart('Gold vs DXY', '黄金与美元指数', 'OANDA:XAUUSD', {
            compareSymbols: [{ symbol: 'TVC:DXY', position: 'SameScale' }],
            height: 420,
          }),
        ],
      },
    ],
  },
  {
    id: 'crypto',
    label: '加密',
    eyebrow: 'Crypto',
    headline: '加密页按 BTC 主图、市场明细、ETF 资金、扩散结构与财库公司购币展开。',
    summary: '加密不能脱离宏观看，重点是看 BTC 主线、ETF 资金是否持续吸纳、以及风险是否继续向高 beta 扩散。',
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
            sourceNote: '数据展示：前端静态设计稿，后续再接入实时行情',
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
