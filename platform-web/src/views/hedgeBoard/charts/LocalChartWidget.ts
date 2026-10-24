import {
  defineAsyncComponent,
  defineComponent,
  h,
  type AsyncComponentLoader,
  type PropType,
} from 'vue';

import { type LocalWidgetKey, type WidgetConfig } from '../nativeData/dashboardClean';

const PanelLoading = defineComponent({
  render: () =>
    h(
      'div',
      { class: 'local-empty', style: { height: '360px' }, 'aria-busy': 'true' },
      '正在加载图表…',
    ),
});

// Component code follows the same viewport boundary as its data and rendering.
const lazyPanel = (loader: AsyncComponentLoader) =>
  defineAsyncComponent({
    loader,
    loadingComponent: PanelLoading,
    delay: 0,
  });

const CryptoMarketDetailPanel = lazyPanel(
  () => import('../components/CryptoMarketDetailPanel.vue'),
);
const BtcEtfFlowPanel = lazyPanel(() => import('../components/BtcEtfFlowPanel.vue'));
const CryptoIvTermPanel = lazyPanel(() => import('../components/CryptoIvTermPanel.vue'));
const CftcPositioningPanel = lazyPanel(() => import('../components/CftcPositioningPanel.vue'));
const GoldPositioningPanel = lazyPanel(() => import('../components/GoldPositioningPanel.vue'));
const GoldReportPanel = lazyPanel(() => import('../components/GoldReportPanel.vue'));
const GoldAnalystsPanel = lazyPanel(() => import('../components/GoldAnalystsPanel.vue'));
const CumulativeVolatilityPanel = lazyPanel(
  () => import('../components/CumulativeVolatilityPanel.vue'),
);
const GoldMarketDetailPanel = lazyPanel(() => import('../components/GoldMarketDetailPanel.vue'));
const MacroMarketDetailPanel = lazyPanel(() => import('../components/MacroMarketDetailPanel.vue'));
const FedWatchPanel = lazyPanel(() => import('../components/FedWatchPanel.vue'));
const PolymarketFedPanel = lazyPanel(() => import('../components/PolymarketFedPanel.vue'));
const MacroSeriesChart = lazyPanel(() => import('./MacroSeriesChart'));
const BitcoinHalvingPanel = lazyPanel(() => import('../components/BitcoinHalvingPanel.vue'));
const GoldOpenInterestPanel = lazyPanel(() => import('../components/GoldOpenInterestPanel.vue'));
const UrpdPanel = lazyPanel(() => import('../components/UrpdPanel.vue'));
const OptionExposurePanel = lazyPanel(() => import('../components/OptionExposurePanel.vue'));
const TreasuryWeeklySnapshotPanel = lazyPanel(
  () => import('../components/TreasuryWeeklySnapshotPanel.vue'),
);
const CentralBankGoldPanel = lazyPanel(() => import('../components/CentralBankGoldPanel.vue'));
const OptionsDistributionPanel = lazyPanel(
  () => import('../components/OptionsDistributionPanel.vue'),
);
const StablecoinPanel = lazyPanel(() => import('../components/StablecoinPanel.vue'));
const WgcEtfFlowPanel = lazyPanel(() => import('../components/WgcEtfFlowPanel.vue'));

const externalGoldResearch = {
  'etf-weekly-flows': {
    provider: 'World Gold Council',
    description: '全球及区域黄金 ETF 持仓与资金流',
    href: 'https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows',
  },
  'spdr-daily-flow': {
    provider: 'MacroMicro',
    description: 'GLD 资金流与黄金价格对照',
    href: 'https://sc.macromicro.me/collections/45/mm-gold-price/23274/gld-fund-flow',
  },
  'spdr-holdings-vs-price': {
    provider: 'SPDR Gold Shares',
    description: 'GLD 官方每日持仓及历史资料',
    href: 'https://www.spdrgoldshares.com/usa/historical-data/',
  },
  'central-bank-holders': {
    provider: 'World Gold Council',
    description: '各国官方黄金储备数据',
    href: 'https://www.gold.org/goldhub/data/gold-reserves-by-country',
  },
  'central-bank-buyers': {
    provider: 'World Gold Council',
    description: '各国官方黄金储备数据',
    href: 'https://www.gold.org/goldhub/data/gold-reserves-by-country',
  },
  'gold-vs-nominal': {
    provider: 'U.S. Treasury',
    description: '黄金与名义利率对比；当前仅保留官方利率数据入口',
    href: 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates',
  },
  'gold-vs-breakeven': {
    provider: 'U.S. Treasury',
    description: '黄金与盈亏平衡通胀对比；当前仅保留官方利率数据入口',
    href: 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates',
  },
  'gold-vs-real': {
    provider: 'U.S. Treasury',
    description: '黄金与实际利率对比；当前仅保留官方实际收益率入口',
    href: 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates',
  },
  'gold-vs-gvz': {
    provider: 'Cboe Global Markets',
    description: 'GVZ 黄金波动率指数官方入口',
    href: 'https://www.cboe.com/us/indices/dashboard/GVZ/',
  },
  'commodity-wti-curve': {
    provider: 'CME Group',
    description: 'WTI 原油期货合约链与期限结构',
    href: 'https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.html',
  },
  'commodity-brent-curve': {
    provider: 'ICE',
    description: 'Brent 原油期货合约链与期限结构',
    href: 'https://www.ice.com/products/219/Brent-Crude-Futures',
  },
  'commodity-copper-curve': {
    provider: 'London Metal Exchange',
    description: 'LME Copper 官方合约与 prompt data 入口',
    href: 'https://www.lme.com/en/metals/non-ferrous/lme-copper',
  },
  'commodity-cme-inventory': {
    provider: 'CME Group',
    description: 'NYMEX / COMEX 官方交割通知与库存报告',
    href: 'https://www.cmegroup.com/clearing/operations-and-deliveries/nymex-delivery-notices.html',
  },
  'commodity-lme-inventory': {
    provider: 'London Metal Exchange',
    description: 'LME 官方仓库、库存与报告入口',
    href: 'https://www.lme.com/en/market-data/reports-and-data/warehouse-and-stocks-reports',
  },
  'commodity-copper-spreads': {
    provider: 'LME / CME / SHFE',
    description: '铜跨市场价差的受限 leg；从 LME 官方铜页面进入',
    href: 'https://www.lme.com/en/metals/non-ferrous/lme-copper',
  },
  'commodity-brent-wti-spread': {
    provider: 'ICE / CME Group',
    description: 'Brent-WTI 价差的受限 leg；从 ICE Brent 官方页面进入',
    href: 'https://www.ice.com/products/219/Brent-Crude-Futures',
  },
  'commodity-ovx': {
    provider: 'Cboe Global Markets',
    description: 'Cboe Crude Oil ETF Volatility Index 官方入口',
    href: 'https://www.cboe.com/us/indices/dashboard/OVX/',
  },
  'commodity-cvol': {
    provider: 'CME Group',
    description: 'CME Group Volatility Indexes 官方入口',
    href: 'https://www.cmegroup.com/markets/volatility/cvol.html',
  },
} as const;

const externalMacroResearch = {
  'macro-fed-balance-structure': {
    provider: 'MacroMicro',
    description: '美联储准备金、TGA、逆回购及其他负债结构',
  },
  'macro-fedwatch': {
    provider: 'CME Group',
    description: '联邦基金期货隐含的 FOMC 目标利率概率',
  },
  'macro-polymarket-fed': {
    provider: 'Polymarket',
    description: '事件市场参与者对下一次美联储利率决议的押注',
  },
  'macro-inflation-nowcast': {
    provider: 'Cleveland Fed',
    description: '当月 CPI 与 PCE 的实时估计',
  },
  'macro-inflation-expectations': {
    provider: 'New York Fed',
    description: '消费者对未来 1 年、3 年与 5 年通胀的预期',
  },
  'macro-gdp-now': {
    provider: 'Atlanta Fed',
    description: '基于已公布经济数据更新的当季实际 GDP 增长估计',
  },
  'macro-lending-standards': {
    provider: 'Federal Reserve / MacroMicro',
    description: '银行收紧商业和工业贷款标准的净比例',
  },
} as const;

type ExternalGoldResearchKey = keyof typeof externalGoldResearch;
type ExternalMacroResearchKey = keyof typeof externalMacroResearch;

function renderExternalMacroResearch(key: ExternalMacroResearchKey) {
  const item = externalMacroResearch[key];
  return h(
    'div',
    {
      style: {
        minHeight: '240px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '14px',
        padding: '32px',
        textAlign: 'center',
        color: 'var(--color-text-2)',
      },
    },
    [
      h('span', 'External Link · reference'),
      h('strong', { style: { color: 'var(--color-text-1)', fontSize: '16px' } }, item.provider),
      h('span', item.description),
      h('small', '点击卡片右上角“参考网页”查看；完成正式采集后再替换为本地图表。'),
    ],
  );
}

function renderExternalGoldResearch(key: ExternalGoldResearchKey) {
  const item = externalGoldResearch[key];
  return h(
    'div',
    {
      style: {
        minHeight: '260px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '14px',
        padding: '32px',
        textAlign: 'center',
        color: 'var(--color-text-2)',
      },
    },
    [
      h(
        'span',
        {
          style: {
            padding: '4px 10px',
            border: '1px solid var(--color-border-2)',
            borderRadius: '999px',
            fontSize: '12px',
            letterSpacing: '0.04em',
          },
        },
        '暂无可用数据',
      ),
      h('strong', { style: { color: 'var(--color-text-1)', fontSize: '16px' } }, item.provider),
      h('span', item.description),
      h(
        'small',
        key === 'etf-weekly-flows' ||
          key === 'central-bank-buyers' ||
          key === 'central-bank-holders'
          ? '当前无法取得 WGC 的可下载数据。可访问参考网页；SPDR 单只基金持仓不能替代全球 ETF 或央行统计。'
          : '当前尚未取得可核验的数据，可访问参考网页查看原始指标。',
      ),
    ],
  );
}

export default defineComponent({
  name: 'LocalChartWidget',
  props: {
    widget: { type: Object as PropType<WidgetConfig>, required: true },
  },
  setup(props) {
    return () => {
      try {
        const key = props.widget.localKey as LocalWidgetKey;
        switch (key) {
          case 'macro-fed-balance-structure':
            return h(MacroSeriesChart, { groupId: 'fedBalance', years: 30 });
          case 'macro-fed-assets':
            return h(MacroSeriesChart, { groupId: 'fedAssets', years: 30 });
          case 'macro-cn-rates':
            return h(MacroSeriesChart, { groupId: 'cnRates', years: 20 });
          case 'macro-cn-policy-rates':
            return h(MacroSeriesChart, { groupId: 'cnPolicyRates', years: 20 });
          case 'macro-cn-money-stock':
            return h(MacroSeriesChart, {
              groupId: 'cnMoneyStock',
              years: 20,
              initiallyHiddenSeriesIds: ['cn_m2_mom', 'cn_m1_mom'],
            });
          case 'macro-cn-reserves':
            return h(MacroSeriesChart, { groupId: 'cnReserves', years: 20 });
          case 'macro-cn-rrr':
            return h(MacroSeriesChart, { groupId: 'cnRrr', years: 30 });
          case 'macro-cn-investment':
            return h(MacroSeriesChart, { groupId: 'cnInvestment', years: 20 });
          case 'macro-cn-property':
            return h(MacroSeriesChart, { groupId: 'cnProperty', years: 20 });
          case 'macro-cn-trade':
            return h(MacroSeriesChart, { groupId: 'cnTrade', years: 20 });
          case 'macro-cn-fiscal':
            return h(MacroSeriesChart, { groupId: 'cnFiscal', years: 20 });
          case 'macro-cn-profits':
            return h(MacroSeriesChart, { groupId: 'cnIndustrialProfits', years: 20 });
          case 'macro-cn-labor':
            return h(MacroSeriesChart, { groupId: 'cnLabor', years: 20 });
          case 'macro-cn-youth-labor':
            return h(MacroSeriesChart, { groupId: 'cnYouthLabor', years: 20 });
          case 'macro-cn-price-details':
            return h(MacroSeriesChart, { groupId: 'cnPriceDetails', years: 20 });
          case 'macro-cn-ppi-details':
            return h(MacroSeriesChart, { groupId: 'cnPpiDetails', years: 20 });
          case 'macro-cn-confidence':
            return h(MacroSeriesChart, { groupId: 'cnConfidence', years: 20 });
          case 'macro-cn-fx':
            return h(MacroSeriesChart, { groupId: 'cnFx', years: 20 });
          case 'macro-cn-treasury':
            return h(MacroSeriesChart, { groupId: 'cnTreasury', years: 20 });
          case 'macro-cn-growth':
            return h(MacroSeriesChart, { groupId: 'cnGrowth', years: 20 });
          case 'macro-cn-pmi':
            return h(MacroSeriesChart, { groupId: 'cnPmi', years: 20 });
          case 'macro-cn-credit':
            return h(MacroSeriesChart, {
              groupId: 'cnCredit',
              years: 20,
              barSeriesIds: ['cn_new_rmb_loans', 'cn_tsf_flow'],
            });
          case 'macro-cn-inflation':
            return h(MacroSeriesChart, { groupId: 'cnInflation', years: 20 });
          case 'macro-cn-risk-leverage':
            return h(MacroSeriesChart, { groupId: 'cnRiskLeverage', years: 20 });
          case 'macro-cn-risk-volatility':
            return h(MacroSeriesChart, { groupId: 'cnRiskVolatility', years: 20 });
          case 'macro-polymarket-fed':
            return h(PolymarketFedPanel);
          case 'macro-corporate-yields':
            return h(MacroSeriesChart, { groupId: 'corporateYields', unitLabel: '%' });
          case 'macro-inflation-nowcast':
            return h(MacroSeriesChart, { groupId: 'inflationNowcast', years: 1, unitLabel: '%' });
          case 'macro-inflation-expectations':
            return h(MacroSeriesChart, {
              groupId: 'inflationExpectations',
              years: 10,
              unitLabel: '%',
            });
          case 'macro-gdp-now':
            return h(MacroSeriesChart, { groupId: 'gdpNow', unitLabel: '% SAAR' });
          case 'macro-lending-standards':
            return h(MacroSeriesChart, { groupId: 'lendingStandards', years: 10, unitLabel: '%' });
          case 'macro-fedwatch':
            return h(FedWatchPanel);
          case 'spdr-daily-flow':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'spdrFlow',
              barSeriesIds: ['spdr_holdings_change'],
            });
          case 'china-gold-etf-flow':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'chinaGoldEtfFlow',
              barSeriesIds: ['wgc_china_etf_monthly_flow'],
            });
          case 'spdr-holdings-vs-price':
            return h(MacroSeriesChart, { dataDomain: 'commodity', groupId: 'spdrHoldings' });
          case 'etf-weekly-flows':
            return h(WgcEtfFlowPanel);
          case 'central-bank-holders':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'wgcReserves',
              presentation: 'distribution',
            });
          case 'central-bank-buyers':
            return h(CentralBankGoldPanel);
          case 'commodity-wti-curve':
          case 'commodity-brent-curve':
          case 'commodity-copper-curve':
          case 'commodity-cme-inventory':
          case 'commodity-lme-inventory':
          case 'commodity-copper-spreads':
          case 'commodity-brent-wti-spread':
          case 'commodity-ovx':
          case 'commodity-cvol':
            return renderExternalGoldResearch(key);
          case 'gold-vs-nominal':
          case 'gold-vs-breakeven':
          case 'gold-vs-gvz':
            return renderExternalGoldResearch(key);
          case 'gold-vs-real':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'goldDrivers',
              presentation: 'gold-drivers',
              initiallyHiddenSeriesIds: ['dxy'],
            });
          case 'macro-treasury-issuance':
            return h(MacroSeriesChart, { groupId: 'treasuryIssuance', unitLabel: 'USD' });
          case 'macro-net-liquidity':
            return h(MacroSeriesChart, { groupId: 'netLiquidity', unitLabel: 'USD million' });
          case 'macro-nfci':
            return h(MacroSeriesChart, { groupId: 'financialConditions', unitLabel: 'index' });
          case 'macro-vix':
            return h(MacroSeriesChart, { groupId: 'vix', unitLabel: 'index' });
          case 'gold-gvz':
            return h(MacroSeriesChart, { groupId: 'goldVolatility', unitLabel: 'index' });
          case 'crypto-strc':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'strcPrice',
              unitLabel: 'USD/share',
            });
          case 'crypto-deribit-metrics':
            return h(MacroSeriesChart, { dataDomain: 'crypto', groupId: 'deribitOptions' });
          case 'crypto-dvol':
            return h(MacroSeriesChart, { dataDomain: 'crypto', groupId: 'dvol', unitLabel: '%' });
          case 'crypto-etf-premium':
            return h('div', { class: 'local-widget-stack' }, [
              h(MacroSeriesChart, { dataDomain: 'crypto', groupId: 'etfPremium', unitLabel: '%' }),
              h(
                'small',
                { style: { color: '#64748b', padding: '0 12px' } },
                'IBIT / BITB / HODL 发行方公布的折溢价。各基金 NAV 定价窗口与数据日期可能不同。',
              ),
            ]);
          case 'crypto-gex-deribit':
            return h(OptionExposurePanel, { market: 'deribit' });
          case 'crypto-gex-ibit':
            return h(OptionExposurePanel, { market: 'ibit' });
          case 'crypto-eth-reserves':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'ethReserves',
              presentation: 'distribution',
            });
          case 'gold-shfe-curve':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'shfeGoldCurve',
              presentation: 'curve',
            });
          case 'gold-shfe-iv':
            return h('div', [
              h(MacroSeriesChart, {
                dataDomain: 'commodity',
                groupId: 'shfeGoldIv',
                presentation: 'curve',
                curveValueLabel: '隐含波动率',
                unitLabel: '%',
              }),
              h(
                'p',
                { style: { color: '#64748b', fontSize: '12px', padding: '0 12px' } },
                '交易所公布的月份波动率；平值隐波、行权价微笑曲线与历史对比暂缺。',
              ),
            ]);
          case 'gold-open-interest':
            return h(GoldOpenInterestPanel);
          case 'crypto-halving-cycles':
            return h(BitcoinHalvingPanel);
          case 'gold-borrow-fee':
            return h(MacroSeriesChart, { dataDomain: 'commodity', groupId: 'gldBorrow' });
          case 'crypto-coinbase-premium':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'coinbasePremium',
              unitLabel: '%',
            });
          case 'crypto-margin-rate':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'publicMarginRate',
              unitLabel: '% / hour',
            });
          case 'crypto-urpd':
            return h(UrpdPanel);
          case 'crypto-address-distribution':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'addressDistribution',
              presentation: 'distribution',
            });
          case 'crypto-treasuries':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'treasuries',
              presentation: 'distribution',
            });
          case 'crypto-strategy-holdings':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'strategyHoldings',
              unitLabel: 'BTC',
            });
          case 'gold-comex-inventory':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'comexGoldInventory',
              unitLabel: 'troy oz',
            });
          case 'crypto-stablecoins':
            return h(StablecoinPanel);
          case 'crypto-fear-greed':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'fearGreed',
              unitLabel: '0–100',
            });
          case 'crypto-funding':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'binanceFunding',
              barSeriesIds: ['binance_btc_funding'],
              unitLabel: '%',
            });
          case 'gold-market-detail-table':
            return h(GoldMarketDetailPanel);
          case 'macro-market-detail-table':
            return h(MacroMarketDetailPanel);
          case 'macro-treasury-yields':
            return h(MacroSeriesChart, { groupId: 'treasuryYields', years: 10, unitLabel: '%' });
          case 'macro-global-m2':
            return h(MacroSeriesChart, {
              groupId: 'globalM2Level',
              years: 10,
              unitLabel: 'USD tn',
            });
          case 'macro-global-m2-yoy':
            return h(MacroSeriesChart, { groupId: 'globalM2YoY', years: 10, unitLabel: '%' });
          case 'macro-us-pmi':
            return h(MacroSeriesChart, { groupId: 'usPmi', years: 30, unitLabel: 'index' });
          case 'macro-growth-production':
            return h(MacroSeriesChart, { groupId: 'growthProduction', years: 10, unitLabel: '%' });
          case 'macro-growth-labor':
            return h(MacroSeriesChart, { groupId: 'growthLabor', years: 2, unitLabel: 'persons' });
          case 'macro-growth-activity':
            return h(MacroSeriesChart, { groupId: 'growthActivity', years: 5, unitLabel: 'index' });
          case 'macro-actual-inflation':
            return h(MacroSeriesChart, { groupId: 'actualInflation', years: 5, unitLabel: '%' });
          case 'macro-upstream-inflation':
            return h(MacroSeriesChart, { groupId: 'upstreamInflation', years: 5, unitLabel: '%' });
          case 'macro-market-inflation':
            return h(MacroSeriesChart, { groupId: 'marketInflation', years: 5, unitLabel: '%' });
          case 'macro-rate-corridor':
            return h(MacroSeriesChart, { groupId: 'rateCorridor', years: 10, unitLabel: '%' });
          case 'macro-risk-hy-oas':
            return h(MacroSeriesChart, { groupId: 'riskHighYieldOas', years: 5, unitLabel: '%' });
          case 'macro-real-yield':
            return h(MacroSeriesChart, { groupId: 'realYield', years: 5, unitLabel: '%' });
          case 'macro-risk-credit-ratio':
            return h(MacroSeriesChart, {
              groupId: 'riskCreditRatio',
              years: 2,
              unitLabel: 'ratio',
            });
          case 'cftc-gold-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcGoldNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-gold-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcGoldPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'cftc-silver-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcSilverNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-silver-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcSilverPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'cftc-copper-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcCopperNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-copper-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcCopperPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'cftc-wti-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcWtiNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-wti-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcWtiPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'cftc-natural-gas-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcNaturalGasNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-natural-gas-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcNaturalGasPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'crypto-market-detail-table':
            return h(CryptoMarketDetailPanel);
          case 'crypto-intraday-cumulative-volatility':
            return h(CumulativeVolatilityPanel, {
              asset: 'btc',
              title: props.widget.title,
            });
          case 'gold-intraday-cumulative-volatility':
            return h(CumulativeVolatilityPanel, {
              asset: 'gold',
              title: props.widget.title,
            });
          case 'cftc-positioning':
            return h(CftcPositioningPanel);
          case 'gold-positioning':
            return h(GoldPositioningPanel);
          case 'gold-report':
            return h(GoldReportPanel);
          case 'gold-analysts':
            return h(GoldAnalystsPanel);
          case 'btc-etf-flow':
            return h(BtcEtfFlowPanel);
          case 'crypto-eth-etf-flow':
            return h(BtcEtfFlowPanel, { asset: 'eth' });
          case 'crypto-atm-iv-term':
            return h(CryptoIvTermPanel);
          case 'btc-treasury-flow':
            return h(TreasuryWeeklySnapshotPanel);
          case 'crypto-options-distribution':
            return h(OptionsDistributionPanel);
          case 'crypto-binance-eth-combined':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'binanceCombinedEth',
              years: 3,
            });
          case 'crypto-binance-open-interest':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'binanceCombinedBtc',
              years: 3,
            });
          default:
            return h('div', { class: 'local-empty' }, '该图表配置尚未接入。');
        }
      } catch (error) {
        console.error('[hedgeBoard] Local widget render failed:', props.widget.title, error);
        return h(
          'div',
          { class: 'local-empty' },
          '该研究卡片的数据格式暂未兼容，已自动跳过，不影响其他模块浏览。',
        );
      }
    };
  },
});
