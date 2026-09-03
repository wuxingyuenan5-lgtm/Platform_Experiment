import { defineComponent, h, type PropType } from 'vue';

import TerminalDetailPanel from '../components/TerminalDetailPanel.vue';
import CryptoMarketDetailPanel from '../components/CryptoMarketDetailPanel.vue';
import MacroMarketDetailPanel from '../components/MacroMarketDetailPanel.vue';
import { type LocalWidgetKey, type WidgetConfig } from '../nativeData/dashboardClean';
import { prepareCommodityMarketDetail } from '../nativeData/marketDetailAdapter';
import { marketTerminalConfigs } from '../nativeData/marketTerminal';
import MacroSeriesChart from './MacroSeriesChart';

const externalGoldResearch = {
  'etf-weekly-flows': {
    provider: 'World Gold Council',
    description: '全球及区域黄金 ETF 持仓与资金流',
    href: 'https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows',
  },
  'etf-ytd-summary': {
    provider: 'World Gold Council',
    description: '全球黄金 ETF 年内持仓与资金流汇总',
    href: 'https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows',
  },
  'spdr-daily-flow': {
    provider: 'SPDR Gold Shares',
    description: 'GLD 官方每日持仓及历史资料',
    href: 'https://www.spdrgoldshares.com/usa/historical-data/',
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

const externalCryptoResearch = {
  'btc-etf-flow': {
    provider: 'Farside Investors',
    description: '美国现货 BTC ETF 每日资金流',
    href: 'https://farside.co.uk/btc/',
  },
  'btc-treasury-flow': {
    provider: 'BitcoinTreasuries.net',
    description: '上市公司及机构 Bitcoin 持仓披露',
    href: 'https://bitcointreasuries.net/',
  },
  'crypto-stablecoin-supply': {
    provider: 'DefiLlama',
    description: '稳定币总市值、链与币种分布',
    href: 'https://defillama.com/stablecoins',
  },
  'crypto-options-iv': {
    provider: 'Deribit',
    description: 'BTC / ETH 波动率指数与期权市场统计',
    href: 'https://www.deribit.com/statistics/BTC/volatility-index',
  },
  'crypto-onchain': {
    provider: 'Checkonchain',
    description: 'Bitcoin 链上估值、持有者与周期指标',
    href: 'https://checkonchain.com/',
  },
  'crypto-eth-etf-flow': {
    provider: 'Farside Investors',
    description: '美国现货 ETH ETF 每日资金流',
    href: 'https://farside.co.uk/eth/',
  },
  'crypto-coinglass': {
    provider: 'CoinGlass',
    description: '跨交易所资金费率、未平仓量与清算聚合',
    href: 'https://www.coinglass.com/',
  },
  'crypto-bybit': {
    provider: 'Bybit',
    description: 'Bybit 官方衍生品市场数据入口',
    href: 'https://www.bybit.com/en/derivatives/',
  },
  'crypto-okx': {
    provider: 'OKX',
    description: 'OKX 官方永续合约市场入口',
    href: 'https://www.okx.com/markets/prices/swap',
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
type ExternalCryptoResearchKey = keyof typeof externalCryptoResearch;
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
      h('small', '点击卡片右上角“原始网页”查看；完成正式采集后再替换为本地图表。'),
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
        'External Link · permission_required',
      ),
      h('strong', { style: { color: 'var(--color-text-1)', fontSize: '16px' } }, item.provider),
      h('span', item.description),
      h('small', '请使用卡片右上角“原始网页”查看；后续接入正式采集后在此显示完整图表。'),
    ],
  );
}

function renderExternalCryptoResearch(key: ExternalCryptoResearchKey) {
  const item = externalCryptoResearch[key];
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
      h('span', 'External Link · permission_required'),
      h('strong', { style: { color: 'var(--color-text-1)', fontSize: '16px' } }, item.provider),
      h('span', item.description),
      h('small', '请使用卡片右上角“原始网页”查看；后续接入正式采集后在此显示完整图表。'),
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
          case 'macro-fedwatch':
          case 'macro-polymarket-fed':
          case 'macro-inflation-nowcast':
          case 'macro-inflation-expectations':
          case 'macro-gdp-now':
          case 'macro-lending-standards':
            return renderExternalMacroResearch(key);
          case 'spdr-daily-flow':
            return renderExternalGoldResearch(key);
          case 'spdr-holdings-vs-price':
            return renderExternalGoldResearch(key);
          case 'etf-weekly-flows':
            return renderExternalGoldResearch(key);
          case 'etf-ytd-summary':
            return renderExternalGoldResearch(key);
          case 'central-bank-holders':
            return renderExternalGoldResearch(key);
          case 'central-bank-buyers':
            return renderExternalGoldResearch(key);
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
          case 'eia-crude-stocks':
            return h(MacroSeriesChart, {
              groupId: 'eiaCrudeStocks',
              years: 5,
              unitLabel: 'thousand barrels',
              dataDomain: 'commodity',
            });
          case 'eia-products-stocks':
            return h(MacroSeriesChart, {
              groupId: 'eiaProductsStocks',
              years: 5,
              unitLabel: 'thousand barrels',
              dataDomain: 'commodity',
            });
          case 'gold-vs-nominal':
          case 'gold-vs-breakeven':
          case 'gold-vs-real':
          case 'gold-vs-gvz':
            return renderExternalGoldResearch(key);
          case 'gold-market-detail-table':
            return h(TerminalDetailPanel, {
              class: 'terminal-detail-panel--embedded',
              title: '市场明细 · 未接入字段为历史参考',
              marketId: 'gold',
              columns: marketTerminalConfigs.gold.detailColumns,
              groups: prepareCommodityMarketDetail(marketTerminalConfigs.gold.detailGroups),
              rotationButtonLabel: marketTerminalConfigs.gold.rotationButtonLabel,
              rotationHeatmap: marketTerminalConfigs.gold.rotationHeatmap,
            });
          case 'macro-market-detail-table':
            return h(MacroMarketDetailPanel);
          case 'macro-global-m2':
            return h(MacroSeriesChart, {
              groupId: 'globalM2Level',
              years: 10,
              unitLabel: 'USD tn',
            });
          case 'macro-global-m2-yoy':
            return h(MacroSeriesChart, { groupId: 'globalM2YoY', years: 10, unitLabel: '%' });
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
            return h(MacroSeriesChart, { groupId: 'rateCorridor', years: 1, unitLabel: '%' });
          case 'macro-risk-hy-oas':
            return h(MacroSeriesChart, { groupId: 'riskHighYieldOas', years: 5, unitLabel: '%' });
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
          case 'btc-etf-flow':
          case 'btc-treasury-flow':
          case 'crypto-stablecoin-supply':
          case 'crypto-options-iv':
          case 'crypto-onchain':
          case 'crypto-eth-etf-flow':
          case 'crypto-coinglass':
          case 'crypto-bybit':
          case 'crypto-okx':
            return renderExternalCryptoResearch(key);
          case 'crypto-binance-spot':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'binanceSpot',
              years: 5,
              unitLabel: 'USDT',
            });
          case 'crypto-binance-funding':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'binanceFunding',
              years: 1,
              unitLabel: '%',
            });
          case 'crypto-binance-open-interest':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'binanceOpenInterest',
              years: 1,
              unitLabel: 'USD',
            });
          case 'crypto-binance-basis':
            return h(MacroSeriesChart, {
              dataDomain: 'crypto',
              groupId: 'binancePerpetualBasis',
              years: 1,
              unitLabel: '%',
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
