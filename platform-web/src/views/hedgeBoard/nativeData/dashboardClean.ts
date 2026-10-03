export type WidgetKind =
  | 'advanced-chart'
  | 'symbol-overview'
  | 'market-overview'
  | 'technical-analysis'
  | 'local-chart'
  | 'external-link';

export type LocalWidgetKey =
  | 'macro-treasury-yields'
  | 'crypto-coinbase-premium'
  | 'crypto-margin-rate'
  | 'crypto-eth-reserves'
  | 'gold-borrow-fee'
  | 'crypto-urpd'
  | 'crypto-treasuries'
  | 'crypto-strategy-holdings'
  | 'gold-comex-inventory'
  | 'macro-treasury-issuance'
  | 'macro-net-liquidity'
  | 'macro-nfci'
  | 'macro-vix'
  | 'gold-gvz'
  | 'crypto-strc'
  | 'crypto-deribit-metrics'
  | 'crypto-stablecoins'
  | 'crypto-fear-greed'
  | 'crypto-funding'
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
  | 'crypto-atm-iv-term'
  | 'btc-treasury-flow'
  | 'crypto-binance-open-interest'
  | 'crypto-eth-etf-flow'
  | 'crypto-intraday-cumulative-volatility'
  | 'gold-intraday-cumulative-volatility'
  | 'cftc-positioning'
  | 'spdr-daily-flow'
  | 'spdr-holdings-vs-price'
  | 'etf-weekly-flows'
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
  sourceLinkLabel?: string;
  /** Keep expensive local widgets unmounted until the user explicitly expands them. */
  deferUntilExpanded?: boolean;
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
    sourceUrl?: string;
    sourceLinkLabel?: string;
    referenceLinks?: Array<{ label: string; href: string }>;
    deferUntilExpanded?: boolean;
  } = {},
): WidgetConfig {
  return {
    kind: 'local-chart',
    title,
    subtitle,
    localKey,
    height: options.height ?? 360,
    sourceNote: options.sourceNote,
    sourceUrl: options.sourceUrl,
    sourceLinkLabel: options.sourceLinkLabel,
    referenceLinks: options.referenceLinks,
    deferUntilExpanded: options.deferUntilExpanded,
  };
}

function withReferenceLinks(
  widget: WidgetConfig,
  referenceLinks: Array<{ label: string; href: string }>,
): WidgetConfig {
  return { ...widget, referenceLinks };
}

function externalReference(
  title: string,
  subtitle: string,
  sourceUrl: string,
  sourceLinkLabel?: string,
): WidgetConfig {
  return { kind: 'external-link', title, subtitle, sourceUrl, sourceLinkLabel, height: 128 };
}

function macroMicroReference(href: string) {
  return [{ label: 'MacroMicro 参考', href }];
}

function treasuryYieldOverview(): WidgetConfig {
  return {
    kind: 'local-chart',
    localKey: 'macro-treasury-yields',
    title: '美债收益率曲线走势',
    subtitle: '3M / 2Y / 10Y / 30Y · Treasury / FRED',
    height: 420,
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
            {
              ...localChart(
                '美元净流动性',
                'WALCL − WDTGAL − RRPONTSYD × 1000 · USD million · 同日观测代理',
                'macro-net-liquidity',
                { height: 420 },
              ),
              sourceUrl: undefined,
            },
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
            '美国国债总发行额',
            'Treasury · 按发行月汇总拍卖接受额（含滚动续发），当月未完整',
            'macro-treasury-issuance',
          ),
          localChart(
            '美联储资产负债结构',
            'Fed 总资产（周三值）与准备金、TGA、流通货币（周均值）；不作会计分项求和',
            'macro-fed-balance-structure',
            {
              height: 300,
              sourceNote: 'Federal Reserve / FRED',
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
          localChart(
            'GDPNow',
            'Atlanta Fed · FRED 每季度最新估计，年化环比；不含季度内历次预测路径',
            'macro-gdp-now',
            {
              height: 280,
              sourceNote: 'FRED / Atlanta Fed',
            },
          ),
          localChart('银行信贷标准', '商业和工业贷款标准收紧比例', 'macro-lending-standards', {
            height: 280,
            sourceNote: 'Federal Reserve SLOOS / FRED',
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
              sourceNote: 'Federal Reserve Bank of Cleveland',
            },
          ),
          localChart(
            '消费者通胀预期',
            '1年 / 3年 / 5年消费者通胀预期',
            'macro-inflation-expectations',
            { height: 280, sourceNote: 'Federal Reserve Bank of New York · SCE' },
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
          localChart('CME FedWatch · FOMC 利率概率', '期货隐含的 FOMC 利率概率', 'macro-fedwatch'),
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
          withReferenceLinks(
            {
              ...localChart('VIX 波动率', 'Cboe VIX via FRED', 'macro-vix', {
                height: 360,
              }),
              sourceUrl: undefined,
            },
            [
              {
                label: 'TradingView 模板',
                href: 'https://cn.tradingview.com/chart/qGloFInw/',
              },
            ],
          ),
          localChart(
            '美国高收益债 OAS',
            'ICE BofA US High Yield OAS via FRED',
            'macro-risk-hy-oas',
          ),
          localChart('HYG / LQD', '同日 adjusted close ratio', 'macro-risk-credit-ratio'),
          localChart('美国金融状况指数', 'Chicago Fed NFCI', 'macro-nfci', { height: 360 }),
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
          localChart('Gold IV (GVZCLS)', 'Cboe 黄金 ETF 波动率指数', 'gold-gvz', {
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
            referenceLinks: [
              { label: 'TradingView 模板', href: 'https://cn.tradingview.com/chart/3pJneWqX/' },
            ],
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
          localChart(
            '金价 vs SPDR 持仓日变化',
            '持仓变化单位为吨，不是美元现金流；金价采用 COMEX 近月期货',
            'spdr-daily-flow',
            {
              height: 420,
              sourceNote: 'SPDR Gold Shares / Yahoo Finance',
              referenceLinks: macroMicroReference(
                'https://sc.macromicro.me/collections/45/mm-gold-price/23274/gld-fund-flow',
              ),
            },
          ),
          localChart('全球各地区 ETF 每周流入', '', 'etf-weekly-flows', {
            height: 430,
            sourceNote: 'External Link · World Gold Council · permission_required',
            referenceLinks: macroMicroReference(
              'https://sc.macromicro.me/collections/45/mm-gold-price/110882/global-gold-etf-net-flow-weekly-regional-sum',
            ),
          }),
          localChart(
            'SPDR 持仓量 vs 黄金期货价格',
            'SPDR 官方持仓（吨） / COMEX 近月期货（USD/oz）',
            'spdr-holdings-vs-price',
            {
              height: 420,
              sourceNote: 'SPDR Gold Shares / Yahoo Finance',
              referenceLinks: macroMicroReference(
                'https://sc.macromicro.me/collections/45/mm-gold-price/712/spdr-gold-trust-etf-gold-price',
              ),
            },
          ),
          externalReference(
            '全球黄金期货未平仓量',
            'MacroMicro · 分交易所累计未平仓量',
            'https://en.macromicro.me/collections/45/mm-gold-price/110916/global-gold-futures-open-interest-by-exchanges-stacked-bar-chart',
          ),
          externalReference(
            '商品期货持仓分析',
            '交易法门 · 商品期货持仓与结构分析',
            'https://www.jiaoyifamen.com/variety/',
          ),
          localChart(
            'COMEX 黄金总库存',
            'CME · 注册 / 合格 / 合计 · 金衡盎司 · 按活动日归档，历史从接入日积累',
            'gold-comex-inventory',
          ),
          localChart('各国央行黄金净购买量', '', 'central-bank-buyers', {
            height: 420,
            sourceNote: 'External Link · World Gold Council · permission_required',
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/93189/gold-demand-central-banks-and-other-inst',
            ),
          }),
          localChart('全球央行黄金储备', '', 'central-bank-holders', {
            height: 420,
            sourceNote: 'External Link · World Gold Council · permission_required',
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/78898/world-central-bank-gold-reserves',
            ),
          }),
        ],
      },
      {
        id: 'gold-rates',
        eyebrow: 'Rates & Inflation',
        title: '金价驱动分析',
        description: '以实际利率为核心观察黄金的宏观驱动。',
        layout: 'hero',
        widgets: [
          localChart(
            '金价驱动分析',
            'COMEX 黄金近月期货与 10Y 实际利率，分别使用左右轴',
            'gold-vs-real',
            {
              height: 400,
              sourceNote: 'FRED DFII10 / Yahoo GC=F',
              referenceLinks: [
                { label: 'TradingView 模板', href: 'https://cn.tradingview.com/chart/k8dNGuui/' },
                {
                  label: 'MacroMicro 参考',
                  href: 'https://sc.macromicro.me/collections/45/mm-gold-price/724/3month-bond-real-yield-gold-price',
                },
              ],
            },
          ),
          externalReference(
            'MacroMicro 黄金研究',
            '黄金、流动性与央行需求集合',
            'https://sc.macromicro.me/commodities/gold',
          ),
        ],
      },
      {
        id: 'gold-browser-toolbox',
        eyebrow: 'Owner Toolkit',
        title: '商品补充分析',
        description: 'Owner 浏览器中的黄金研究框架入口，按实物、期货、期权与辅助研究集中保留。',
        layout: 'three',
        widgets: [
          localChart(
            'GLD 借券费率',
            'Interactive Brokers 经 ChartExchange · 单一券商最新快照，历史从接入日积累',
            'gold-borrow-fee',
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
            'CME QuikStrike 黄金期权',
            'CME · 期权波动率与策略工具入口',
            'https://cmegroup-sso.quikstrike.net/User/Disclaimer.aspx?ret=%2fUser%2fPartnerRegister.aspx',
          ),
          externalReference(
            '黄金 Seasonal Chart',
            'TradingView · XAUUSD 季节性走势（外部跳转）',
            'https://www.tradingview.com/chart/?symbol=XAUUSD',
            '打开 Seasonal Chart ↗',
          ),
          localChart(
            'CFTC 持仓报告',
            '官方 CFTC PRE 周度持仓；点击后加载历史分位与净头寸。',
            'cftc-positioning',
            {
              height: 620,
              deferUntilExpanded: true,
              sourceNote: 'CFTC PRE Disaggregated Futures Only · 周度落库序列',
              referenceLinks: [
                {
                  label: 'CFTC 官方报告',
                  href: 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
                },
              ],
            },
          ),
        ],
      },
      {
        id: 'gold-intraday-cumulative-volatility',
        eyebrow: 'Intraday Volatility',
        title: '黄金分时累计波动',
        description:
          '后端从共享 Bybit 高精度归档采样，按 UTC 亚洲、欧洲、美洲盘口展示累计波动，并叠加以美洲盘首个有效收盘价为基准的黄金价格线。',
        layout: 'hero',
        widgets: [
          localChart('黄金分时累计波动', '', 'gold-intraday-cumulative-volatility', {
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
            sourceUrl: undefined,
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
            referenceLinks: [
              { label: 'TradingView 模板', href: 'https://cn.tradingview.com/chart/lYCXN3KJ/' },
            ],
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
            referenceLinks: [
              {
                label: '30日均线',
                href: 'https://studio.glassnode.com/charts/institutions.UsSpotEtfFlowsNet?a=BTC&mAvg=30&resolution=24h&s=1704657272&u=1788393600&zoom=',
              },
              {
                label: '各ETF细节',
                href: 'https://studio.glassnode.com/charts/institutions.UsSpotEtfFlowsAll?a=BTC&mAvg=30&resolution=24h&s=1757139104&u=1788675104&zoom=365',
              },
            ],
          }),
          localChart('ETH ETF 日流量 vs ETH 价格', 'SoSoValue', 'crypto-eth-etf-flow', {
            height: 420,
          }),
          localChart('Bitcoin Treasuries Weekly Net Inflow', '', 'btc-treasury-flow', {
            height: 420,
            sourceNote: '',
            referenceLinks: [
              {
                label: 'SoSoValue 参考 ↗',
                href: 'https://sosovalue.com/zh/assets/bitcoin-treasuries/weekly-net-inflow',
              },
            ],
          }),
          withReferenceLinks(
            localChart(
              '上市公司 BTC 持仓分布',
              'BitcoinTreasuries 公开公司样本；日期为采集日，各公司披露截止日不同',
              'crypto-treasuries',
            ),
            [{ label: 'BitcoinTreasuries 参考', href: 'https://bitcointreasuries.net/' }],
          ),
          localChart('稳定币市值历史', 'DefiLlama · 流通市值（USD）', 'crypto-stablecoins'),
          localChart(
            'Strategy BTC 持仓',
            'BitcoinTreasuries 披露快照 · 历史从接入日积累，日期为采集日',
            'crypto-strategy-holdings',
          ),
          localChart(
            'Strategic ETH Reserve',
            '公开来源的 ACTIVE 实体；保留报告/自报/钱包追踪分类及原始更新时间，不代表统一时点储备',
            'crypto-eth-reserves',
          ),
          externalReference(
            'STRC ATM Tracker',
            'Bitcoin for Corporations · ATM 融资进度',
            'https://bitcoinforcorporations.com/strc-atm-tracker/',
          ),
          localChart(
            'STRC 股价历史',
            '交易所日线收盘价 · Yahoo Finance · 最新交易日可能尚未收盘',
            'crypto-strc',
          ),
        ],
      },
      {
        id: 'crypto-native-venue',
        eyebrow: 'Derivatives · Native',
        title: '衍生品数据',
        description:
          'Binance 持仓与资金费率、Coinbase 跨所日线溢价及 Bybit 公开借贷成本分别保留来源口径。Crypto 数据按 UTC 7×24 日历维护。',
        layout: 'two',
        widgets: [
          localChart(
            'Binance BTC / ETH 未平仓量',
            'USD-M 日末名义价值 · not Aggregate',
            'crypto-binance-open-interest',
            {
              referenceLinks: [
                { label: 'TradingView 模板', href: 'https://cn.tradingview.com/chart/UPwf4Qx8/' },
              ],
            },
          ),
          externalReference(
            '全市场期货未平仓量',
            'CoinGlass · 跨交易所 OI',
            'https://www.coinglass.com/zh/pro/futures/OpenInterest',
          ),
          localChart('资费详情', 'Binance BTC / ETH · 单一交易所历史资金费率', 'crypto-funding'),
          externalReference(
            'CoinGlass 加密衍生品风险指数',
            'CoinGlass · 衍生品市场风险指标',
            'https://www.coinglass.com/zh-TW/pro/i/CDRI',
          ),
          localChart(
            '保证金借贷利率',
            'Bybit USDT VIP 0 公开小时利率，非账户实际费用；历史从接入日积累',
            'crypto-margin-rate',
          ),
          localChart('加密恐惧与贪婪指数', 'Alternative.me · 0–100', 'crypto-fear-greed'),
          localChart(
            'Coinbase / Binance 现货溢价',
            '已闭合 UTC 日线 · 使用 Coinbase USDT/USD 校正计价货币；非 CoinGlass 指数',
            'crypto-coinbase-premium',
          ),
          externalReference(
            'BTC 清算热力图',
            'CoinGlass · 杠杆清算密集区',
            'https://www.coinglass.com/zh/pro/futures/LiquidationHeatMap?coin=BTC',
          ),
        ],
      },
      {
        id: 'crypto-external-research',
        eyebrow: 'Research Links',
        title: '期权分析',
        description: '受许可或维护边界限制的专题，保留精确数据入口，不复制第三方静态快照。',
        layout: 'three',
        widgets: [
          localChart('Greeks.live BTC Data Lab', 'Deribit 期权数据实验室', 'crypto-atm-iv-term', {
            height: 420,
            sourceUrl: 'https://www.greeks.live/deribit/tools/datalab/BTC',
          }),
          localChart(
            'Deribit BTC Options Metrics',
            'Call / Put 未平仓量与 Put/Call 比率 · 日内采集快照，历史从接入日积累',
            'crypto-deribit-metrics',
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
            'BTC ETF 溢价',
            'CoinGlass · 比特币 ETF 溢价与折价',
            'https://www.coinglass.com/pro/etf/Premium',
          ),
          externalReference(
            'BTC 三大驱动因素',
            'MacroMicro · 流动性、实际利率与 GDP',
            'https://www.macromicro.me/collections/22514/bi-te-bi_418919/111972/bi-te-bi-BTC-qu-dong-san-da-yin-su-liu-dong-xing-shi-ji-li-lyu-GDP',
          ),
          localChart(
            'Realized Price Distribution',
            'BGeometrics · UTXO 最后移动时的价格区间与 BTC 数量，不等于投资者持仓成本',
            'crypto-urpd',
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
          externalReference('Murphy Chen', 'X · 链上与周期研究跟踪', 'https://x.com/Murphychen888'),
          externalReference(
            'Market Beggar 市场观点',
            'X · 指定市场研究帖',
            'https://x.com/market_beggar/status/2096487388092698821?s=20',
          ),
          externalReference(
            'BTC Seasonal Chart',
            'TradingView · BTCUSD 季节性走势（外部跳转）',
            'https://www.tradingview.com/chart/?symbol=BTCUSD',
            '打开 Seasonal Chart ↗',
          ),
          externalReference(
            'Unbias Analysts',
            '加密研究员与观点聚合',
            'https://unbias.fyi/analysts?source=all',
          ),
          externalReference(
            '交易所链上资金监控',
            'OKLink · CEX 地址与链上资金流跟踪',
            'https://www.oklink.com/zh-hans/cex-list',
          ),
        ],
      },
      {
        id: 'crypto-intraday-cumulative-volatility',
        eyebrow: 'Intraday Volatility',
        title: 'BTC 分时累计波动',
        description:
          '后端从共享 Bybit 高精度归档采样，按 UTC 亚洲、欧洲、美洲盘口展示累计波动，并叠加以美洲盘首个有效收盘价为基准的 BTC 价格线。',
        layout: 'hero',
        widgets: [
          localChart('BTC 分时累计波动', '', 'crypto-intraday-cumulative-volatility', {
            height: 420,
          }),
        ],
      },
    ],
  },
];
