export type WidgetKind =
  | 'advanced-chart'
  | 'symbol-overview'
  | 'market-overview'
  | 'technical-analysis'
  | 'local-chart'
  | 'external-link';

export type LocalWidgetKey =
  | 'macro-market-detail-table'
  | 'macro-global-m2'
  | 'macro-global-m2-yoy'
  | 'macro-fed-balance-structure'
  | 'macro-fedwatch'
  | 'macro-polymarket-fed'
  | 'macro-inflation-nowcast'
  | 'macro-inflation-expectations'
  | 'macro-gdp-now'
  | 'macro-lending-standards'
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
  | 'crypto-binance-spot'
  | 'crypto-binance-funding'
  | 'crypto-binance-open-interest'
  | 'crypto-binance-basis'
  | 'crypto-stablecoin-supply'
  | 'crypto-options-iv'
  | 'crypto-onchain'
  | 'crypto-eth-etf-flow'
  | 'crypto-coinglass'
  | 'crypto-bybit'
  | 'crypto-okx'
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
  sourceUrl?: string;
  referenceLinks?: Array<{ label: string; href: string }>;
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
    sourceUrl: `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}`,
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
  options: {
    height?: number;
    sourceNote?: string;
    referenceLinks?: Array<{ label: string; href: string }>;
  } = {},
): WidgetConfig {
  return {
    kind: 'local-chart',
    title,
    subtitle,
    localKey,
    height: options.height ?? 360,
    sourceNote: options.sourceNote,
    referenceLinks: options.referenceLinks,
  };
}

function withReferenceLinks(
  widget: WidgetConfig,
  referenceLinks: Array<{ label: string; href: string }>,
): WidgetConfig {
  return { ...widget, referenceLinks };
}

function externalReference(title: string, subtitle: string, sourceUrl: string): WidgetConfig {
  return { kind: 'external-link', title, subtitle, sourceUrl, height: 128 };
}

function macroMicroReference(href: string) {
  return [{ label: 'MacroMicro 参考', href }];
}

function treasuryYieldOverview(): WidgetConfig {
  return {
    kind: 'symbol-overview',
    title: '美债收益率曲线走势',
    subtitle: '3M / 2Y / 10Y / 30Y U.S. Treasury yields',
    height: 500,
    scriptSrc: 'https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js',
    sourceUrl: 'https://www.tradingview.com/markets/bonds/prices-usa/',
    config: {
      ...tvBase,
      symbols: [
        ['美国 3M', 'TVC:US03MY|1D'],
        ['美国 2Y', 'TVC:US02Y|1D'],
        ['美国 10Y', 'TVC:US10Y|1D'],
        ['美国 30Y', 'TVC:US30Y|1D'],
      ],
      chartOnly: false,
      width: '100%',
      height: 500,
      locale: 'zh_CN',
      colorTheme: 'light',
      autosize: true,
      showVolume: false,
      showMA: false,
      hideDateRanges: false,
      hideMarketStatus: false,
      hideSymbolLogo: false,
      scalePosition: 'right',
      scaleMode: 'Normal',
      fontFamily: 'Arial, sans-serif',
      fontSize: '10',
      noTimeScale: false,
      valuesTracking: '1',
      changeMode: 'price-and-percent',
      chartType: 'area',
      lineWidth: 2,
      lineType: 0,
    },
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
        title: '流动性',
        description: '从全球货币供给、美元净流动性与美联储负债结构观察流动性环境。',
        layout: 'two',
        widgets: [
          localChart('Global M2 Proxy', '全球主要央行广义货币的美元折算代理', 'macro-global-m2', {
            height: 420,
            sourceNote: 'Native proxy · reference methodology: MacroMicro',
          }),
          withReferenceLinks(
            advancedChart(
              '美元净流动性',
              'Formula: WALCL - WDTGAL - RRPONTTLD',
              'FRED:WALCL-FRED:WDTGAL-FRED:RRPONTTLD',
              {
                height: 420,
                hide_side_toolbar: false,
              },
            ),
            [
              {
                label: 'TradingView 模板',
                href: 'https://cn.tradingview.com/chart/K47lvX8b/',
              },
              {
                label: '美元流动性大全',
                href: 'https://dollarliquidity.com/zh',
              },
            ],
          ),
          localChart(
            '美联储资产负债结构',
            '准备金、TGA、逆回购及其他负债结构',
            'macro-fed-balance-structure',
            {
              height: 300,
              sourceNote: 'External Link · MacroMicro',
              referenceLinks: [
                {
                  label: 'TradingView 模板',
                  href: 'https://cn.tradingview.com/chart/EUMNyM4l/',
                },
              ],
            },
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
            {
              referenceLinks: [
                {
                  label: 'TradingView 模板',
                  href: 'https://cn.tradingview.com/chart/AmPBnM2J/',
                },
                {
                  label: '金十美国数据',
                  href: 'https://datas.jin10.com/#/category/52001/detail/52013',
                },
                {
                  label: '美国宏观',
                  href: 'https://sc.macromicro.me/macro/us',
                },
                {
                  label: '中国宏观',
                  href: 'https://sc.macromicro.me/macro/cn',
                },
              ],
            },
          ),
          localChart('初请失业金四周均值', 'Initial Claims 4W MA', 'macro-growth-labor'),
          localChart('广义经济活动', 'CFNAI / CFNAIMA3', 'macro-growth-activity'),
          localChart('GDPNow', '亚特兰大联储实时 GDP 增长估计', 'macro-gdp-now', {
            height: 280,
            sourceNote: 'External Link · Atlanta Fed',
          }),
          localChart('银行信贷标准', '商业和工业贷款标准收紧比例', 'macro-lending-standards', {
            height: 280,
            sourceNote: 'External Link · Federal Reserve / MacroMicro',
          }),
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
          localChart(
            '通胀 Nowcast',
            'Cleveland Fed CPI / PCE nowcasting',
            'macro-inflation-nowcast',
            {
              height: 280,
              sourceNote: 'External Link · Cleveland Fed',
            },
          ),
          localChart(
            '消费者通胀预期',
            '1年 / 3年 / 5年消费者通胀预期',
            'macro-inflation-expectations',
            { height: 280, sourceNote: 'External Link · New York Fed' },
          ),
        ],
      },
      {
        id: 'macro-rates',
        eyebrow: 'Rates',
        title: '利率',
        description: '同时观察美债期限曲线、短端政策走廊与市场对下一次 FOMC 的概率定价。',
        layout: 'two',
        widgets: [
          withReferenceLinks(treasuryYieldOverview(), [
            {
              label: 'TradingView 模板',
              href: 'https://cn.tradingview.com/chart/WJhhGPpA/',
            },
          ]),
          localChart(
            '短期利率走廊',
            'Fed target / IORB / ON RRP / EFFR / SOFR',
            'macro-rate-corridor',
            {
              referenceLinks: [
                {
                  label: 'TradingView 模板',
                  href: 'https://cn.tradingview.com/chart/lJmN3igH/',
                },
              ],
            },
          ),
          localChart('CME FedWatch', '期货隐含的 FOMC 利率概率', 'macro-fedwatch', {
            height: 280,
            sourceNote: 'External Link · CME Group',
          }),
          localChart(
            'Polymarket 美联储利率路径',
            '事件市场对下一次美联储决议的押注',
            'macro-polymarket-fed',
            { height: 280, sourceNote: 'External Link · Polymarket' },
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
          withReferenceLinks(
            advancedChart('VIX 波动率', 'Equity volatility regime', 'TVC:VIX', { height: 360 }),
            [
              {
                label: 'TradingView 模板',
                href: 'https://cn.tradingview.com/chart/qGloFInw/',
              },
            ],
          ),
          advancedChart('美国金融状况指数', 'Chicago Fed NFCI', 'FRED:NFCI', { height: 360 }),
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
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/23274/gld-fund-flow',
            ),
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
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/78898/world-central-bank-gold-reserves',
            ),
          }),
          localChart('近一年持续增持的央行', '', 'central-bank-buyers', {
            height: 420,
            sourceNote: 'External Link · World Gold Council · permission_required',
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/93189/gold-demand-central-banks-and-other-inst',
            ),
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
              referenceLinks: macroMicroReference(
                'https://en.macromicro.me/charts/81733/Gold-Price-vs-US5-Year-Real-Yield',
              ),
            },
          ),
          localChart(
            '金价 vs 10Y 通胀预期',
            '用名义 10Y 减实际 10Y 得到 breakeven',
            'gold-vs-breakeven',
            {
              height: 400,
              sourceNote: 'External Link · U.S. Treasury · no local gold proxy',
              referenceLinks: macroMicroReference('https://en.macromicro.me/charts/10319/xau'),
            },
          ),
          localChart('金价 vs 10Y 实际利率', '实际利率是黄金最硬的宏观约束之一', 'gold-vs-real', {
            height: 400,
            sourceNote: 'External Link · U.S. Treasury · no local gold proxy',
            referenceLinks: macroMicroReference(
              'https://www.macromicro.me/charts/22895/huang-jin-VS-shi-zhi-li-lv-Real-interest-rate',
            ),
          }),
          withReferenceLinks(
            advancedChart('Gold vs DXY', '黄金与美元指数', 'OANDA:XAUUSD', {
              compareSymbols: [{ symbol: 'TVC:DXY', position: 'SameScale' }],
              height: 420,
            }),
            macroMicroReference(
              'https://en.macromicro.me/charts/81733/Gold-Price-vs-US5-Year-Real-Yield',
            ),
          ),
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
          localChart('Gold Net Position', 'Managed Money / Producer-Merchant', 'cftc-gold-net', {
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/31138/gold-future-options-fund-net-position-vs-price',
            ),
          }),
          localChart('Gold 5Y Percentile', 'Managed Money Net', 'cftc-gold-percentile', {
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/31138/gold-future-options-fund-net-position-vs-price',
            ),
          }),
          localChart(
            'Silver Net Position',
            'Managed Money / Producer-Merchant',
            'cftc-silver-net',
            {
              referenceLinks: macroMicroReference(
                'https://en.macromicro.me/collections/3961/silver-managed-money/31173/silver-future-options-fund-net-position-vs-price',
              ),
            },
          ),
          localChart('Silver 5Y Percentile', 'Managed Money Net', 'cftc-silver-percentile', {
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/collections/3961/silver-managed-money/31173/silver-future-options-fund-net-position-vs-price',
            ),
          }),
          localChart(
            'Copper Net Position',
            'Managed Money / Producer-Merchant',
            'cftc-copper-net',
            {
              referenceLinks: macroMicroReference(
                'https://en.macromicro.me/series/8311/copper-futures-and-options-manage-money-net-position',
              ),
            },
          ),
          localChart('Copper 5Y Percentile', 'Managed Money Net', 'cftc-copper-percentile', {
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/series/8311/copper-futures-and-options-manage-money-net-position',
            ),
          }),
          localChart('WTI Net Position', 'Managed Money / Producer-Merchant', 'cftc-wti-net', {
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/31152/crude-oil-wti-brent-managed-money-net-position',
            ),
          }),
          localChart('WTI 5Y Percentile', 'Managed Money Net', 'cftc-wti-percentile', {
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/31152/crude-oil-wti-brent-managed-money-net-position',
            ),
          }),
          localChart(
            'Natural Gas Net Position',
            'Managed Money / Producer-Merchant',
            'cftc-natural-gas-net',
            {
              referenceLinks: macroMicroReference(
                'https://en.macromicro.me/charts/30979/natural-gas-future-options-fund-net-position-vs-price',
              ),
            },
          ),
          localChart(
            'Natural Gas 5Y Percentile',
            'Managed Money Net',
            'cftc-natural-gas-percentile',
            {
              referenceLinks: macroMicroReference(
                'https://en.macromicro.me/charts/30979/natural-gas-future-options-fund-net-position-vs-price',
              ),
            },
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
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/81111/yuan-you-ku-cun',
            ),
          }),
          localChart(
            'Products Stocks',
            'Motor Gasoline / Distillate Fuel Oil',
            'eia-products-stocks',
            {
              sourceNote: 'Native · U.S. EIA Open Data API v2 · weekly',
              referenceLinks: macroMicroReference(
                'https://en.macromicro.me/charts/81111/yuan-you-ku-cun',
              ),
            },
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
          localChart('WTI Futures Curve', 'CME official contract chain', 'commodity-wti-curve', {
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/148223/volatility-wti-crude-oil-volatility-term-structure',
            ),
          }),
          localChart(
            'Brent Futures Curve',
            'ICE official contract chain',
            'commodity-brent-curve',
            {
              referenceLinks: macroMicroReference(
                'https://en.macromicro.me/charts/889/commodity-brent',
              ),
            },
          ),
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
          localChart(
            'Brent - WTI Spread',
            'ICE / CME licensed legs',
            'commodity-brent-wti-spread',
            {
              referenceLinks: macroMicroReference(
                'https://en.macromicro.me/collections/19/mm-oil-price/1024/brent-wti-price-spread',
              ),
            },
          ),
          localChart('OVX', 'Cboe Crude Oil ETF Volatility Index', 'commodity-ovx', {
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/148223/volatility-wti-crude-oil-volatility-term-structure',
            ),
          }),
          localChart('CVOL', 'CME Group Volatility Indexes', 'commodity-cvol'),
        ],
      },
      {
        id: 'gold-browser-toolbox',
        eyebrow: 'Owner Toolkit',
        title: '黄金与商品补充研究工具',
        description: 'Owner 浏览器中的黄金研究框架入口，按实物、期货、期权与辅助研究集中保留。',
        layout: 'three',
        widgets: [
          externalReference(
            'GLD 借券费率',
            'ChartExchange · ETF 做空拥挤与借券成本',
            'https://chartexchange.com/symbol/nyse-gld/borrow-fee/',
          ),
          externalReference(
            '全球黄金期货未平仓量',
            'MacroMicro · 分交易所累计未平仓量',
            'https://en.macromicro.me/collections/45/mm-gold-price/110916/global-gold-futures-open-interest-by-exchanges-stacked-bar-chart',
          ),
          externalReference(
            'COMEX 黄金总库存',
            'CommoditiesChart · 注册与合格库存',
            'https://commoditieschart.net/zh/metals/gold/comex-gold-stocks',
          ),
          externalReference(
            '沪金期限结构',
            '奇货可查 · AU 近远月结构',
            'https://x.qhkch.com/fundamental/futurespot/fut_spot_structure?variety=%E6%B2%AA%E9%87%91',
          ),
          externalReference(
            '沪金期权波动率',
            'OpenVlab · AU 隐含波动率分析',
            'https://www.openvlab.cn/volatility/analysis/AU',
          ),
          externalReference(
            '商品期权 PCR',
            '交易法门 · Put/Call Ratio',
            'https://www.jiaoyifamen.com/variety/option-PCR',
          ),
          externalReference(
            'CFTC 持仓分析',
            '交易法门 · 商品资金持仓辅助视图',
            'https://www.jiaoyifamen.com/variety/positionAnalysis-CFTC',
          ),
          externalReference(
            '期货席位成本',
            '交易法门 · 席位与成本结构',
            'https://www.jiaoyifamen.com/variety/seat-cost',
          ),
          externalReference(
            'CME QuikStrike 黄金期权',
            'CME · 期权波动率与策略工具入口',
            'https://cmegroup-sso.quikstrike.net/User/Disclaimer.aspx?ret=%2fUser%2fPartnerRegister.aspx',
          ),
          externalReference(
            'MacroMicro 黄金研究',
            '黄金、流动性与央行需求集合',
            'https://en.macromicro.me/collections/45/mm-gold-price',
          ),
          externalReference(
            '黄金与全球 M2',
            'MacroMicro · 主要央行货币供应',
            'https://en.macromicro.me/collections/45/mm-gold-price/3439/major-bank-m2-comparsion',
          ),
          externalReference(
            '全球央行净购金',
            'MacroMicro · 全球央行季度净购买',
            'https://en.macromicro.me/collections/45/mm-gold-price/93189/gold-demand-central-banks-and-other-inst',
          ),
          externalReference(
            'Owner 黄金复盘模板',
            'TradingView · XAUUSD 复盘布局',
            'https://cn.tradingview.com/chart/CVV3rItf/',
          ),
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
          localChart('ETH ETF 日流量', 'Farside Investors', 'crypto-eth-etf-flow', {
            height: 420,
          }),
          localChart('Bitcoin Treasuries Weekly Net Inflow', '', 'btc-treasury-flow', {
            height: 420,
            sourceNote: '',
          }),
        ],
      },
      {
        id: 'crypto-native-venue',
        eyebrow: 'Derivatives · Native',
        title: 'Binance BTC / ETH 现货与衍生品结构',
        description: '单一 Venue 口径，不代表全市场聚合；Crypto 数据按 UTC 7×24 日历维护。',
        layout: 'two',
        widgets: [
          localChart(
            'BTC / ETH Spot · Binance Venue',
            '已收盘 UTC 日线 · not Aggregate',
            'crypto-binance-spot',
          ),
          localChart(
            'BTC / ETH Funding · Binance Venue',
            'USD-M 日内费率日均 · not Aggregate',
            'crypto-binance-funding',
          ),
          localChart(
            'BTC / ETH Open Interest · Binance Venue',
            'USD-M 日末名义价值 · not Aggregate',
            'crypto-binance-open-interest',
          ),
          localChart(
            'BTC / ETH Perpetual Basis · Binance Venue',
            'USD-M 日末基差率 · not Aggregate',
            'crypto-binance-basis',
          ),
        ],
      },
      {
        id: 'crypto-external-research',
        eyebrow: 'Research Links',
        title: '稳定币、期权与链上研究入口',
        description: '受许可或维护边界限制的专题，保留精确数据入口，不复制第三方静态快照。',
        layout: 'three',
        widgets: [
          localChart('Stablecoin Supply', 'DefiLlama', 'crypto-stablecoin-supply'),
          localChart('Options IV / Skew', 'Deribit / Greeks.live', 'crypto-options-iv'),
          localChart('On-chain Signals', 'Checkonchain / Glassnode', 'crypto-onchain'),
          localChart('Aggregate Derivatives', 'CoinGlass', 'crypto-coinglass'),
          localChart('Bybit Derivatives', 'Bybit', 'crypto-bybit'),
          localChart('OKX Derivatives', 'OKX', 'crypto-okx'),
        ],
      },
      {
        id: 'crypto-capital-toolbox',
        eyebrow: 'Capital Flows & Treasury',
        title: 'ETF、稳定币与财库公司工具',
        description: '跟踪法币入口、稳定币流动性以及上市公司 BTC / ETH 储备与融资。',
        layout: 'three',
        widgets: [
          externalReference(
            'SoSoValue 现货 ETF 资金流',
            'BTC / ETH 等美国现货 ETF 汇总',
            'https://sosovalue.com/zh/assets/etf/Total_Crypto_Spot_ETF_Fund_Flow?page=usBTC',
          ),
          externalReference(
            '稳定币市值历史',
            'CoinGlass · 稳定币供应趋势',
            'https://www.coinglass.com/pro/stablecoin',
          ),
          externalReference(
            'Bitcoin Treasuries 周度净流入',
            'SoSoValue · 企业与机构购币',
            'https://sosovalue.com/zh/assets/bitcoin-treasuries/weekly-net-inflow',
          ),
          externalReference(
            'Strategy BTC 持仓',
            'BitcoinTreasuries · Strategy 持仓与分析',
            'https://bitcointreasuries.net/public-companies/strategy',
          ),
          externalReference(
            'Strategic ETH Reserve',
            '企业与机构 ETH 储备',
            'https://www.strategicethreserve.xyz/',
          ),
          externalReference(
            'STRC ATM Tracker',
            'Bitcoin for Corporations · ATM 融资进度',
            'https://bitcoinforcorporations.com/strc-atm-tracker/',
          ),
          externalReference(
            'STRC 实时定价',
            'STRC 股价、收益率与 ATM 状态',
            'https://strc.live/ticker/strc',
          ),
        ],
      },
      {
        id: 'crypto-derivatives-toolbox',
        eyebrow: 'Derivatives & Options',
        title: '全市场杠杆、清算与期权结构',
        description: '覆盖聚合未平仓量、清算位置、波动率、偏度与 Gamma 暴露。',
        layout: 'three',
        widgets: [
          externalReference(
            '全市场期货未平仓量',
            'CoinGlass · 跨交易所 OI',
            'https://www.coinglass.com/zh/pro/futures/OpenInterest',
          ),
          externalReference(
            'BTC 清算热力图',
            'CoinGlass · 杠杆清算密集区',
            'https://www.coinglass.com/zh/pro/futures/LiquidationHeatMap?coin=BTC',
          ),
          externalReference(
            'Coinbase Premium Index',
            'CoinGlass · 美国现货相对溢价',
            'https://www.coinglass.com/pro/i/coinbase-bitcoin-premium-index',
          ),
          externalReference(
            'Deribit BTC Options Metrics',
            '期限结构、偏度、Put/Call 与到期分布',
            'https://www.deribit.com/statistics/BTC/metrics/options',
          ),
          externalReference(
            'Greeks.live BTC Data Lab',
            'Deribit 期权数据实验室',
            'https://www.greeks.live/deribit/tools/datalab/BTC',
          ),
          externalReference(
            'Laevitas BTC Gamma Exposure',
            'Deribit BTC 期权 GEX',
            'https://app.laevitas.ch/assets/options/gex/btc/deribit',
          ),
          externalReference(
            'IBIT Gamma Exposure',
            'Barchart · IBIT 期权 GEX',
            'https://www.barchart.com/etfs-funds/quotes/IBIT/gamma-exposure',
          ),
          externalReference(
            'CoinGlass BTC 行情终端',
            'BTCUSDT K线与衍生品入口',
            'https://www.coinglass.com/tv/zh/Binance_BTCUSDT',
          ),
        ],
      },
      {
        id: 'crypto-onchain-toolbox',
        eyebrow: 'On-chain & Cycle',
        title: '链上成本、周期与研究跟踪',
        description: '用于观察筹码成本分布、地址结构、周期位置与研究观点。',
        layout: 'three',
        widgets: [
          externalReference(
            'Realized Price Distribution',
            'Bitcoin Magazine Pro · 实现价格分布',
            'https://charts.bgeometrics.com/distribution_realized_price.html',
          ),
          externalReference(
            'Bitcoin Address Distribution',
            'Bitcoin Magazine Pro · 地址持币分布',
            'https://charts.bgeometrics.com/bitcoin_distribution_addr_tables.html',
          ),
          externalReference(
            'Bitcoin 减半周期表现',
            'CoinGlass · 历次减半后的价格路径',
            'https://www.coinglass.com/pro/i/bitcoin-price-performance-since-halving',
          ),
          externalReference(
            'Glassnode Week On-chain',
            '周度链上市场研究',
            'https://research.glassnode.com/the-week-onchain-week-18-2026/',
          ),
          externalReference(
            'Unbias Analysts',
            '加密研究员与观点聚合',
            'https://unbias.fyi/analysts?source=all',
          ),
          externalReference(
            'Owner BTC 看盘模板',
            'TradingView · BTCUSD 日常看盘布局',
            'https://cn.tradingview.com/chart/3QJfnHcC/?symbol=COINBASE%3ABTCUSD',
          ),
        ],
      },
    ],
  },
];
