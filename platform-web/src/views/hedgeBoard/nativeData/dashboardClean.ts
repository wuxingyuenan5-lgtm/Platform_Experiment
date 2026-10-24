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
  | 'gold-shfe-curve'
  | 'gold-shfe-iv'
  | 'gold-open-interest'
  | 'crypto-halving-cycles'
  | 'gold-borrow-fee'
  | 'crypto-urpd'
  | 'crypto-address-distribution'
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
  | 'crypto-dvol'
  | 'crypto-etf-premium'
  | 'crypto-gex-deribit'
  | 'crypto-gex-ibit'
  | 'crypto-stablecoins'
  | 'crypto-fear-greed'
  | 'crypto-funding'
  | 'macro-market-detail-table'
  | 'macro-global-m2'
  | 'macro-global-m2-yoy'
  | 'macro-fed-balance-structure'
  | 'macro-fed-assets'
  | 'macro-cn-rates'
  | 'macro-cn-treasury'
  | 'macro-cn-growth'
  | 'macro-cn-pmi'
  | 'macro-cn-credit'
  | 'macro-cn-inflation'
  | 'macro-cn-risk-leverage'
  | 'macro-cn-risk-volatility'
  | 'macro-cn-policy-rates'
  | 'macro-cn-money-stock'
  | 'macro-cn-reserves'
  | 'macro-cn-rrr'
  | 'macro-cn-investment'
  | 'macro-cn-property'
  | 'macro-cn-trade'
  | 'macro-cn-fiscal'
  | 'macro-cn-profits'
  | 'macro-cn-labor'
  | 'macro-cn-youth-labor'
  | 'macro-cn-price-details'
  | 'macro-cn-ppi-details'
  | 'macro-cn-confidence'
  | 'macro-cn-fx'
  | 'macro-fedwatch'
  | 'macro-polymarket-fed'
  | 'macro-corporate-yields'
  | 'macro-inflation-nowcast'
  | 'macro-inflation-expectations'
  | 'macro-gdp-now'
  | 'macro-lending-standards'
  | 'macro-us-pmi'
  | 'macro-growth-production'
  | 'macro-growth-labor'
  | 'macro-growth-activity'
  | 'macro-actual-inflation'
  | 'macro-upstream-inflation'
  | 'macro-market-inflation'
  | 'macro-rate-corridor'
  | 'macro-real-yield'
  | 'macro-risk-hy-oas'
  | 'macro-risk-credit-ratio'
  | 'gold-market-detail-table'
  | 'crypto-market-detail-table'
  | 'btc-etf-flow'
  | 'crypto-atm-iv-term'
  | 'btc-treasury-flow'
  | 'crypto-binance-open-interest'
  | 'crypto-binance-eth-combined'
  | 'crypto-options-distribution'
  | 'crypto-eth-etf-flow'
  | 'crypto-intraday-cumulative-volatility'
  | 'gold-intraday-cumulative-volatility'
  | 'cftc-positioning'
  | 'gold-positioning'
  | 'gold-report'
  | 'gold-analysts'
  | 'china-gold-etf-flow'
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
  region?: '美国' | '中国';
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
              ...localChart('美元净流动性', '美元净流动性=资产-TGA-RRP', 'macro-net-liquidity', {
                height: 420,
              }),
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
            '美联储负债端结构',
            '流通货币 / ON RRP / TGA / 准备金 · 百万美元',
            'macro-fed-balance-structure',
            {
              height: 420,
              sourceNote: 'Federal Reserve / FRED',
              referenceLinks: [
                {
                  label: 'TradingView 模板',
                  href: 'https://cn.tradingview.com/chart/EUMNyM4l/',
                },
              ],
            },
          ),
          localChart(
            '美联储资产端结构',
            '国债剩余期限：1年以内 / 1至5年 / 5至10年 / 10年以上及 MBS · 百万美元',
            'macro-fed-assets',
            {
              height: 420,
              sourceUrl: 'https://www.federalreserve.gov/releases/h41/',
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
          localChart('美国 PMI', 'ISM 制造业 / 服务业 · 50为荣枯线', 'macro-us-pmi'),
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
        description:
          '美国关注美债曲线、政策走廊和FOMC定价；中国关注LPR、银行间资金利率与国债曲线。',
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
            'Polymarket · FOMC 利率路径',
            '各次 FOMC 会议的加息、维持与降息概率及历史变化',
            'macro-polymarket-fed',
            { height: 360, sourceNote: 'Polymarket 公开市场历史快照 · 本地落库' },
          ),
          localChart(
            '美国公司债收益率 · AAA / BBB / CCC 及以下',
            'ICE BofA 公司债指数有效收益率 · 日收盘 · %',
            'macro-corporate-yields',
            {
              referenceLinks: [
                { label: 'AAA · FRED', href: 'https://fred.stlouisfed.org/series/BAMLC0A1CAAAEY' },
                { label: 'BBB · FRED', href: 'https://fred.stlouisfed.org/series/BAMLC0A4CBBBEY' },
                {
                  label: 'CCC 及以下 · FRED',
                  href: 'https://fred.stlouisfed.org/series/BAMLH0A3HYCEY',
                },
              ],
              sourceNote: 'ICE Data Indices, LLC via FRED · 日收盘 · 非季调',
            },
          ),
          localChart(
            '美国高收益债信用利差（OAS）',
            'ICE BofA US High Yield OAS via FRED',
            'macro-risk-hy-oas',
          ),
          localChart(
            '美国10年实际利率',
            '10年期通胀保值国债实际收益率 · FRED DFII10',
            'macro-real-yield',
          ),
        ],
      },
      {
        id: 'macro-risk-appetite',
        eyebrow: 'Risk Appetite',
        title: '信用风险偏好',
        description: '观察波动率、信用资产相对表现与金融状况。',
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
        id: 'gold-market',
        eyebrow: 'Market',
        title: '商品市场明细',
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

          localChart('黄金分时累计波动', '', 'gold-intraday-cumulative-volatility', {
            height: 420,
          }),
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
            'SPDR GLD资金流',
            'SPDR 持仓日变化（吨） / XAUUSD（USD/oz）',
            'spdr-daily-flow',
            {
              height: 420,
              sourceNote: 'SPDR Gold Shares / MT5 XAUUSD',
              referenceLinks: macroMicroReference(
                'https://sc.macromicro.me/collections/45/mm-gold-price/23274/gld-fund-flow',
              ),
            },
          ),
          localChart(
            '中国黄金 ETF 资金流',
            '中国大陆月度净资金流（USD） / XAUUSD（USD/oz）',
            'china-gold-etf-flow',
            {
              height: 420,
              sourceUrl: 'https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows',
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
            'SPDR 持仓量',
            'SPDR 官方持仓（吨） / XAUUSD（USD/oz）',
            'spdr-holdings-vs-price',
            {
              height: 420,
              sourceNote: 'SPDR Gold Shares / MT5 XAUUSD',
              referenceLinks: macroMicroReference(
                'https://sc.macromicro.me/collections/45/mm-gold-price/712/spdr-gold-trust-etf-gold-price',
              ),
            },
          ),
          localChart(
            '黄金期货未平仓量',
            'COMEX GC / 上期所 AU · 分市场持仓，全球总量暂缺',
            'gold-open-interest',
            {
              height: 480,
              sourceUrl:
                'https://en.macromicro.me/collections/45/mm-gold-price/110916/global-gold-futures-open-interest-by-exchanges-stacked-bar-chart',
            },
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
          localChart('央行购金', '', 'central-bank-buyers', {
            height: 420,
            sourceNote: 'World Gold Council · 月报披露',
            referenceLinks: macroMicroReference(
              'https://en.macromicro.me/charts/93189/gold-demand-central-banks-and-other-inst',
            ),
          }),
          localChart('官方黄金储备 · 分国家', '', 'central-bank-holders', {
            height: 420,
            sourceNote: 'World Gold Council / IMF · 季度截面',
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
        description: '黄金、美元指数、长短端利差、名义利率与通胀预期。',
        layout: 'hero',
        widgets: [
          localChart(
            '金价驱动分析',
            '黄金与美元、30Y−10Y 利差 / 10Y 名义利率、盈亏平衡通胀率与实际利率',
            'gold-vs-real',
            {
              height: 400,
              sourceNote: 'U.S. Treasury / FRED / Yahoo Finance',
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
          localChart('沪金期限结构', '上期所 · 各交割合约日结算价 · 元/克', 'gold-shfe-curve', {
            sourceUrl: 'https://www.shfe.com.cn/reports/tradedata/dailyandweeklydata/',
          }),
          localChart(
            '沪金期权波动率',
            '上期所公布的各月份隐含波动率 · 非 ATM 波动率',
            'gold-shfe-iv',
            {
              sourceUrl: 'https://www.openvlab.cn/volatility/analysis/AU',
              referenceLinks: [
                {
                  label: '上期所数据',
                  href: 'https://www.shfe.com.cn/reports/tradedata/dailyandweeklydata/',
                },
              ],
            },
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
            'CFTC 官方周度持仓；黄金支持多口径历史，保留白银、铜、WTI 与天然气。',
            'cftc-positioning',
            {
              height: 620,
              deferUntilExpanded: true,
              sourceNote: 'CFTC 官方黄金多口径及商品周度落库序列',
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
        id: 'gold-research-analysts',
        eyebrow: 'Analyst Views',
        title: '金属分析师跟踪',
        description: '',
        layout: 'hero',
        widgets: [localChart('分析师观点与情景', '', 'gold-analysts', { height: 720 })],
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
        id: 'crypto-market',
        eyebrow: 'Market',
        title: '加密市场明细',
        description: '',
        layout: 'hero',
        widgets: [
          advancedChart('BTCUSDT Main Chart', '', 'BINANCE:BTCUSDT', {
            height: 620,
            hide_side_toolbar: false,
          }),
          localChart('BTC IV (DERIBIT DVOL)', '30 日预期年化波动率 · UTC 日收盘', 'crypto-dvol', {
            height: 320,
            sourceUrl: 'https://www.deribit.com/statistics/BTC/volatility-index',
          }),

          localChart('BTC 分时累计波动', '', 'crypto-intraday-cumulative-volatility', {
            height: 420,
          }),
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
        title: 'ETF 与资金面',
        description: '',
        layout: 'two',
        widgets: [
          localChart('BTC ETF 日流量', '', 'btc-etf-flow', {
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
          localChart('ETH ETF 日流量', 'SoSoValue', 'crypto-eth-etf-flow', {
            height: 420,
          }),
          localChart(
            'BTC 财库公司每周变动',
            'SoSoValue · 上市公司买入 BTC 周度资金净流入',
            'btc-treasury-flow',
            {
              height: 420,
              sourceUrl: 'https://sosovalue.com/zh/assets/bitcoin-treasuries/weekly-net-inflow',
            },
          ),
          withReferenceLinks(
            localChart(
              '上市公司 BTC 持仓分布',
              'BitcoinTreasuries 公开公司样本；日期为采集日，各公司披露截止日不同',
              'crypto-treasuries',
            ),
            [{ label: 'BitcoinTreasuries 参考', href: 'https://bitcointreasuries.net/' }],
          ),
          localChart(
            'Strategic ETH Reserve',
            '公开来源的 ACTIVE 实体；保留报告/自报/钱包追踪分类及原始更新时间，不代表统一时点储备',
            'crypto-eth-reserves',
          ),
          localChart('稳定币市值历史', 'DefiLlama · 流通市值（USD）', 'crypto-stablecoins'),
          withReferenceLinks(
            localChart(
              'STRC 股价历史',
              '交易所日线收盘价 · Yahoo Finance · 最新交易日可能尚未收盘',
              'crypto-strc',
            ),
            [
              {
                label: 'STRC ATM Tracker',
                href: 'https://bitcoinforcorporations.com/strc-atm-tracker/',
              },
            ],
          ),
          withReferenceLinks(
            localChart(
              'Strategy BTC 持仓',
              'BitcoinTreasuries 披露快照 · 历史从接入日积累，日期为采集日',
              'crypto-strategy-holdings',
            ),
            [
              {
                label: '企业财库周度流入参考',
                href: 'https://sosovalue.com/zh/assets/bitcoin-treasuries/weekly-net-inflow',
              },
            ],
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
            'Binance BTC · 价格 / 未平仓量 / 资金费率',
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
            '暂无已接通数据 · CoinGlass · 跨交易所 OI',
            'https://www.coinglass.com/zh/pro/futures/OpenInterest',
          ),
          localChart('Binance ETH · 价格 / 未平仓量 / 资金费率', '', 'crypto-binance-eth-combined'),
          externalReference(
            'CoinGlass 加密衍生品风险指数',
            '暂无已接通数据 · CoinGlass · 衍生品市场风险指标',
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
            '暂无已接通数据 · CoinGlass · 杠杆清算密集区',
            'https://www.coinglass.com/zh/pro/futures/LiquidationHeatMap?coin=BTC',
          ),
        ],
      },
      {
        id: 'crypto-external-research',
        eyebrow: 'Research Links',
        title: '期权分析',
        description: '期权隐波、持仓与 Gamma 敞口估算。',
        layout: 'two',
        widgets: [
          localChart('期权分布', 'Deribit · BTC', 'crypto-options-distribution', {
            height: 680,
            sourceUrl: 'https://www.deribit.com/statistics/BTC/metrics/options',
          }),
          localChart('BTC 期权隐含波动率', 'Deribit 期权数据实验室', 'crypto-atm-iv-term', {
            height: 420,
            sourceUrl: 'https://www.greeks.live/deribit/tools/datalab/BTC',
          }),
          localChart(
            'BTC 期权持仓与看跌／看涨比',
            'Call / Put 未平仓量与 Put/Call 比率 · 日内采集快照，历史从接入日积累',
            'crypto-deribit-metrics',
          ),
          localChart(
            'Deribit BTC Gamma 敞口估算',
            '公开期权链 · 远期 Gamma 模型',
            'crypto-gex-deribit',
            {
              sourceUrl:
                'https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option',
              height: 590,
            },
          ),
          localChart('IBIT Gamma 敞口估算', 'Cboe 延迟期权链 · 公布 Gamma', 'crypto-gex-ibit', {
            sourceUrl: 'https://www.cboe.com/delayed_quotes/ibit/quote_table',
            height: 590,
          }),
        ],
      },
      {
        id: 'crypto-onchain-toolbox',
        eyebrow: 'On-chain & Cycle',
        title: '链上成本、周期与研究跟踪',
        description: '用于观察筹码成本分布、地址结构、周期位置与研究观点。',
        layout: 'three',
        widgets: [
          localChart(
            'BTC ETF 溢价 / 折价',
            'IBIT / BITB / HODL · 发行方日度披露',
            'crypto-etf-premium',
            {
              sourceUrl: 'https://www.coinglass.com/pro/etf/Premium',
              referenceLinks: [
                {
                  label: '发行方数据',
                  href: 'https://www.ishares.com/us/products/333011/ishares-bitcoin-trust-etf',
                },
              ],
            },
          ),
          externalReference(
            'BTC 三大驱动因素',
            '暂无已接通数据 · MacroMicro · 流动性、实际利率与 GDP',
            'https://www.macromicro.me/collections/22514/bi-te-bi_418919/111972/bi-te-bi-BTC-qu-dong-san-da-yin-su-liu-dong-xing-shi-ji-li-lyu-GDP',
          ),
          localChart(
            'Realized Price Distribution',
            'BGeometrics · UTXO 最后移动时的价格区间与 BTC 数量，不等于投资者持仓成本',
            'crypto-urpd',
          ),
          localChart(
            'Bitcoin 减半周期表现',
            'Blockchain.com · 四次减半日价格归一为 100',
            'crypto-halving-cycles',
            {
              height: 480,
              sourceUrl: 'https://www.coinglass.com/pro/i/bitcoin-price-performance-since-halving',
              referenceLinks: [
                {
                  label: '价格数据',
                  href: 'https://www.blockchain.com/explorer/charts/market-price',
                },
              ],
            },
          ),
          localChart(
            'Bitcoin Address Distribution',
            'BGeometrics · 按来源余额区间统计地址数量，地址不等于持币人数或独立实体',
            'crypto-address-distribution',
            { sourceUrl: 'https://charts.bgeometrics.com/bitcoin_distribution_addr_tables.html' },
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
            '暂无已接通数据 · OKLink · CEX 地址与链上资金流跟踪',
            'https://www.oklink.com/zh-hans/cex-list',
          ),
        ],
      },
    ],
  },
];

const chinaMacroSections: Record<string, Array<[string, string, LocalWidgetKey]>> = {
  'macro-liquidity': [
    [
      '中国货币存量',
      'M2 / M1余额、同比、环比与社融存量同比；M1自2025年调整统计口径',
      'macro-cn-money-stock',
    ],
    ['中国存款准备金率', '大型 / 中小金融机构调整后水平 · 按生效日记录的政策事件', 'macro-cn-rrr'],
    ['中国外汇储备', '国家外汇储备 · 亿美元', 'macro-cn-reserves'],
  ],
  'macro-rates': [
    ['中国政策利率与回购资金面', '央行7天逆回购中标利率 / DR001 / DR007', 'macro-cn-policy-rates'],
    [
      '中国政策定价与银行间利率',
      'LPR 1年 / 5年以上；Shibor 隔夜 / 1周 / 3月（无担保拆借）',
      'macro-cn-rates',
    ],
    ['中国国债收益率', '财政部中国国债收益率曲线 · 2年 / 10年 / 30年', 'macro-cn-treasury'],
  ],
  'macro-growth': [
    ['中国增长与内需', 'GDP累计同比 / 规上工业增加值同比 / 社会消费品零售同比', 'macro-cn-growth'],
    ['中国景气调查', '制造业 PMI / 非制造业商务活动指数 · 50为荣枯线', 'macro-cn-pmi'],
    ['中国新增信贷', '当月新增人民币贷款 / 社会融资规模增量 · 亿元', 'macro-cn-credit'],
    ['中国投资结构', '固定资产 / 制造业 / 基建 / 民间投资累计同比', 'macro-cn-investment'],
    ['中国房地产周期', '开发投资 / 商品房销售面积与金额 / 新开工面积累计同比', 'macro-cn-property'],
    ['中国进出口', '出口 / 进口金额同比 · 美元口径', 'macro-cn-trade'],
    ['中国财政收支', '财政收入 / 预算支出累计同比', 'macro-cn-fiscal'],
    ['中国工业企业利润', '规模以上工业企业利润总额累计同比', 'macro-cn-profits'],
    ['中国城镇就业', '全国 / 31个大城市城镇调查失业率', 'macro-cn-labor'],
    [
      '中国分年龄就业',
      '16–24 / 25–29 / 30–59岁，不含在校生；新口径自2023年12月起',
      'macro-cn-youth-labor',
    ],
  ],
  'macro-inflation': [
    [
      '中国居民与工业价格',
      'CPI / PPI 同比 · 关注内需价格、工业出厂价格及通缩压力',
      'macro-cn-inflation',
    ],
    ['中国消费价格分项', '核心 / 食品 / 非食品CPI同比', 'macro-cn-price-details'],
    ['中国工业价格分项', 'PPI生产资料 / 生活资料同比', 'macro-cn-ppi-details'],
  ],
  'macro-risk-appetite': [
    [
      '中国杠杆交易与风险偏好',
      '融资余额 / 融资融券成交额占比 · 观察杠杆需求',
      'macro-cn-risk-leverage',
    ],
    [
      '中国股票市场波动',
      '上证综指20交易日已实现波动率（年化），不是隐含波动率',
      'macro-cn-risk-volatility',
    ],
    ['中国消费者信心', '消费者信心 / 预期指数', 'macro-cn-confidence'],
    [
      '人民币汇率与风险偏好',
      '离岸人民币兑美元 · 每美元折合人民币，升高表示人民币走弱',
      'macro-cn-fx',
    ],
  ],
};
for (const section of researchModules.find((module) => module.id === 'macro')!.sections) {
  const charts = chinaMacroSections[section.id];
  if (!charts) continue;
  if (section.id !== 'macro-liquidity') {
    section.widgets.forEach((widget) => {
      widget.region = '美国';
    });
  }
  section.widgets.push(
    ...charts.map(([title, subtitle, key]) => ({
      ...localChart(title, subtitle, key, { height: 420 }),
      region: '中国' as const,
    })),
  );
}
