import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  researchModules,
  type ChartSection,
  type ResearchModule,
  type WidgetConfig,
} from '../nativeData/dashboardClean';
import { marketTerminalConfigs, type TerminalMarketId } from '../nativeData/marketTerminal';
import {
  loadTradingToolBoardCatalog,
  type TradingToolBoardCatalogKey,
  type TradingToolCatalogSection,
} from '../tradingTools/data/catalog';

type HedgeCategory = 'macro' | 'gold' | 'crypto' | 'us' | 'global' | 'aShare';

const moduleRoutes: Record<HedgeCategory, string> = {
  macro: '/hedge-board/macro',
  us: '/hedge-board/us',
  aShare: '/hedge-board/a-share',
  global: '/hedge-board/global',
  gold: '/hedge-board/gold',
  crypto: '/hedge-board/crypto',
};

const hedgeBoardNav: ReadonlyArray<{
  id: HedgeCategory;
  label: string;
  path: string;
}> = [
  { id: 'macro', label: '宏观', path: moduleRoutes.macro },
  { id: 'gold', label: '商品', path: moduleRoutes.gold },
  { id: 'crypto', label: '加密', path: moduleRoutes.crypto },
  { id: 'us', label: '美股', path: moduleRoutes.us },
  { id: 'aShare', label: 'A股', path: moduleRoutes.aShare },
  { id: 'global', label: '全球', path: moduleRoutes.global },
];

const sectionLabelOverrides: Record<string, { title?: string }> = {
  'macro-market': { title: '宏观市场明细' },
  'macro-rates': { title: '利率' },
  'macro-liquidity': { title: '流动性' },
  'macro-inflation': { title: '通胀' },
  'macro-growth': { title: '经济' },
  'macro-risk-appetite': { title: '风险偏好' },
  'gold-flows': { title: 'ETF与资金面' },
  'gold-central-bank': { title: '央行购金' },
  'gold-main': { title: '黄金主图' },
  'gold-rates': { title: '利率与通胀' },
  'crypto-etf': { title: '加密资金面' },
};

const macroSectionOrder = [
  'macro-market',
  'macro-liquidity',
  'macro-rates',
  'macro-growth',
  'macro-inflation',
  'macro-risk-appetite',
] as const;

const researchSectionOrder: Partial<Record<HedgeCategory, readonly string[]>> = {
  macro: macroSectionOrder,
  gold: [
    'gold-market',
    'gold-main',
    'gold-flows',
    'gold-central-bank',
    'gold-rates',
    'commodity-positioning',
    'commodity-eia-inventory',
    'commodity-official-references',
  ],
  crypto: [
    'crypto-market',
    'crypto-main',
    'crypto-etf',
    'crypto-native-venue',
    'crypto-external-research',
  ],
};

const widgetTextOverrides: Record<string, { title?: string }> = {
  'etf-weekly-flows': { title: '全球各地区ETF每周流入' },
  'etf-ytd-summary': { title: '全球 ETF 年内汇总' },
  'spdr-daily-flow': { title: '金价 vs SPDR 每日流量' },
  'spdr-holdings-vs-price': { title: 'SPDR 持仓量 vs 黄金价格' },
  'central-bank-holders': { title: '官方黄金储备前十' },
  'central-bank-buyers': { title: '近一年持续增持的央行' },
};

const ETF_REFERENCE_URL = 'https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows';

const widgetSourceLinks: Partial<Record<string, string>> = {
  'macro-global-m2': 'https://www.macromicro.me/charts/3439/major-bank-m2-comparsion',
  'macro-fed-balance-structure':
    'https://sc.macromicro.me/collections/4238/us-federal/1320/us-fed-liabilities-structure',
  'macro-fedwatch': 'https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html',
  'macro-polymarket-fed': 'https://polymarket.com/zh/event/fed-decision-in-september-762',
  'macro-inflation-nowcast':
    'https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting',
  'macro-inflation-expectations': 'https://www.newyorkfed.org/microeconomics/sce#/inflexp-1',
  'macro-gdp-now': 'https://www.atlantafed.org/cqer/research/gdpnow',
  'macro-lending-standards': 'https://en.macromicro.me/charts/1241/us-bank-net-percent-tight-loan',
  'macro-growth-production': 'https://fred.stlouisfed.org/series/GDPC1',
  'macro-growth-labor': 'https://fred.stlouisfed.org/series/IC4WSA',
  'macro-growth-activity': 'https://fred.stlouisfed.org/series/CFNAI',
  'macro-actual-inflation': 'https://fred.stlouisfed.org/series/CPIAUCSL',
  'macro-upstream-inflation': 'https://fred.stlouisfed.org/series/PPIFIS',
  'macro-market-inflation': 'https://fred.stlouisfed.org/series/T10YIE',
  'macro-rate-corridor': 'https://www.newyorkfed.org/markets/reference-rates',
  'macro-risk-hy-oas': 'https://fred.stlouisfed.org/series/BAMLH0A0HYM2',
  'macro-risk-credit-ratio': 'https://finance.yahoo.com/quote/HYG/history/',
  'btc-etf-flow': 'https://farside.co.uk/btc/',
  'btc-treasury-flow': 'https://bitcointreasuries.net/',
  'crypto-eth-etf-flow': 'https://farside.co.uk/eth/',
  'crypto-binance-spot': 'https://www.binance.com/en/markets/overview',
  'crypto-binance-funding':
    'https://www.binance.com/en/futures/funding-history/perpetual/real-time-funding-rate',
  'crypto-binance-open-interest': 'https://www.binance.com/en/futures/BTCUSDT',
  'crypto-binance-basis': 'https://www.binance.com/en/futures/BTCUSDT',
  'crypto-stablecoin-supply': 'https://defillama.com/stablecoins',
  'crypto-options-iv': 'https://www.deribit.com/statistics/BTC/volatility-index',
  'crypto-onchain': 'https://checkonchain.com/',
  'crypto-coinglass': 'https://www.coinglass.com/',
  'crypto-bybit': 'https://www.bybit.com/en/derivatives/',
  'crypto-okx': 'https://www.okx.com/markets/prices/swap',
  'etf-weekly-flows': ETF_REFERENCE_URL,
  'etf-ytd-summary': ETF_REFERENCE_URL,
  'spdr-daily-flow': 'https://www.spdrgoldshares.com/usa/historical-data/',
  'spdr-holdings-vs-price': 'https://www.spdrgoldshares.com/usa/historical-data/',
  'central-bank-holders': 'https://www.gold.org/goldhub/data/gold-reserves-by-country',
  'central-bank-buyers': 'https://www.gold.org/goldhub/data/gold-reserves-by-country',
  'gold-vs-nominal': 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates',
  'gold-vs-breakeven': 'https://fred.stlouisfed.org/series/T10YIE',
  'gold-vs-real': 'https://fred.stlouisfed.org/series/DFII10',
  'gold-vs-gvz': 'https://www.cboe.com/us/indices/dashboard/GVZ/',
  'cftc-gold-net': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'cftc-gold-percentile': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'cftc-silver-net': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'cftc-silver-percentile': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'cftc-copper-net': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'cftc-copper-percentile': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'cftc-wti-net': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'cftc-wti-percentile': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'cftc-natural-gas-net': 'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'cftc-natural-gas-percentile':
    'https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm',
  'eia-crude-stocks': 'https://www.eia.gov/petroleum/supply/weekly/',
  'eia-products-stocks': 'https://www.eia.gov/petroleum/supply/weekly/',
  'commodity-wti-curve': 'https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.html',
  'commodity-brent-curve': 'https://www.ice.com/products/219/Brent-Crude-Futures',
  'commodity-copper-curve': 'https://www.lme.com/en/metals/non-ferrous/lme-copper',
  'commodity-cme-inventory':
    'https://www.cmegroup.com/clearing/operations-and-deliveries/nymex-delivery-notices.html',
  'commodity-lme-inventory':
    'https://www.lme.com/en/market-data/reports-and-data/warehouse-and-stocks-reports',
  'commodity-copper-spreads': 'https://www.lme.com/en/metals/non-ferrous/lme-copper',
  'commodity-brent-wti-spread': 'https://www.ice.com/products/219/Brent-Crude-Futures',
  'commodity-ovx': 'https://www.cboe.com/us/indices/dashboard/OVX/',
  'commodity-cvol': 'https://www.cmegroup.com/markets/volatility/cvol.html',
};

const marketDetailWidgetKeys = new Set([
  'macro-market-detail-table',
  'gold-market-detail-table',
  'crypto-market-detail-table',
]);

function resolveCategory(routeName: string, routePath: string): HedgeCategory {
  if (routeName === 'HedgeUsBoard' || routePath.endsWith('/us')) return 'us';
  if (routeName === 'HedgeAShareBoard' || routePath.endsWith('/a-share')) return 'aShare';
  if (routeName === 'HedgeGlobalBoard' || routePath.endsWith('/global')) return 'global';
  if (routeName === 'HedgeGoldBoard' || routePath.endsWith('/gold')) return 'gold';
  if (routeName === 'HedgeCryptoBoard' || routePath.endsWith('/crypto')) return 'crypto';
  return 'macro';
}

function scrollPageTop() {
  if (typeof window === 'undefined') return;
  nextTick(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    const scrollTargets = [
      document.querySelector('.scrollbar__wrap'),
      document.querySelector('.vben-layout-content'),
      document.querySelector('.ant-layout-content'),
      document.querySelector('.page-wrapper-content'),
    ].filter(Boolean) as HTMLElement[];
    scrollTargets.forEach((element) => {
      element.scrollTop = 0;
      element.scrollLeft = 0;
    });
  });
}

export function useHedgeBoardPage() {
  const route = useRoute();
  const router = useRouter();

  const hedgeBoardTabs = computed(() =>
    hedgeBoardNav.map((item) => ({ key: item.id, label: item.label })),
  );
  const activeCategory = computed<HedgeCategory>(() =>
    resolveCategory(String(route.name ?? ''), route.path),
  );
  const isTerminalCategory = computed(() =>
    ['us', 'global', 'aShare'].includes(activeCategory.value),
  );
  const activeTerminalConfig = computed(() =>
    isTerminalCategory.value
      ? marketTerminalConfigs[activeCategory.value as TerminalMarketId]
      : null,
  );
  const terminalTabs = computed(() => {
    if (activeCategory.value === 'aShare') {
      return [{ id: 'aShare' as TerminalMarketId, label: 'A股', path: moduleRoutes.aShare }];
    }
    return [
      { id: 'us' as TerminalMarketId, label: '美股', path: moduleRoutes.us },
      { id: 'global' as TerminalMarketId, label: '全球', path: moduleRoutes.global },
    ];
  });
  const activeBoardNav = computed(
    () => hedgeBoardNav.find((item) => item.id === activeCategory.value) ?? hedgeBoardNav[0],
  );
  const activeModule = computed<ResearchModule>(
    () =>
      researchModules.find((module) => module.id === activeCategory.value) ?? researchModules[0],
  );
  const activeTradingToolCatalog = ref<TradingToolCatalogSection | null>(null);
  let tradingToolCatalogRequestId = 0;

  watch(
    activeCategory,
    async (category) => {
      if (!['macro', 'gold', 'crypto'].includes(category)) {
        activeTradingToolCatalog.value = null;
        return;
      }
      const requestId = ++tradingToolCatalogRequestId;
      const catalog = await loadTradingToolBoardCatalog(category as TradingToolBoardCatalogKey);
      if (requestId === tradingToolCatalogRequestId) activeTradingToolCatalog.value = catalog;
    },
    { immediate: true },
  );

  const useUnifiedResearchUi = computed(() => true);
  const visibleSections = computed<ChartSection[]>(() => {
    const sections = activeModule.value.sections;
    const sectionOrder = researchSectionOrder[activeCategory.value];
    if (!sectionOrder) return sections;

    const sectionsById = new Map(sections.map((section) => [section.id, section]));
    const orderedSectionIds = new Set<string>(sectionOrder);
    const orderedSections = sectionOrder.flatMap((sectionId) => {
      const section = sectionsById.get(sectionId);
      return section ? [section] : [];
    });

    return [
      ...orderedSections,
      ...sections.filter((section) => !orderedSectionIds.has(section.id)),
    ];
  });
  const pageTitle = computed(() => `对冲基金看板 / ${activeBoardNav.value.label}`);

  function getSectionTitle(sectionId: string, fallback: string) {
    return sectionLabelOverrides[sectionId]?.title ?? fallback;
  }

  function getWidgetTitle(localKey: string | undefined, fallback: string) {
    return localKey ? widgetTextOverrides[localKey]?.title ?? fallback : fallback;
  }

  function getWidgetSourceLink(widget: WidgetConfig) {
    return widget.sourceUrl || (widget.localKey ? widgetSourceLinks[widget.localKey] ?? '' : '');
  }

  function selectBoardCategory(key: string) {
    const nextPath = moduleRoutes[key as HedgeCategory];
    if (nextPath) void router.push(nextPath);
  }

  function shouldHideWidgetHeader(sectionId: string, widget: WidgetConfig) {
    const localKey = widget.localKey;
    if (['macro-liquidity', 'gold-main', 'crypto-main'].includes(sectionId)) {
      return widget.kind !== 'local-chart' && !getWidgetSourceLink(widget);
    }
    if (!localKey) return false;
    return (
      ['macro-market', 'gold-market', 'crypto-market'].includes(sectionId) &&
      widget.kind === 'local-chart' &&
      marketDetailWidgetKeys.has(localKey)
    );
  }

  function jumpToSection(sectionId: string) {
    nextTick(() => {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  watch(() => route.fullPath, scrollPageTop, { immediate: true });
  onMounted(() => {
    if (typeof window !== 'undefined' && 'scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }
    scrollPageTop();
  });

  return {
    activeCategory,
    activeModule,
    activeTerminalConfig,
    activeTradingToolCatalog,
    getSectionTitle,
    getWidgetSourceLink,
    getWidgetTitle,
    hedgeBoardTabs,
    isTerminalCategory,
    jumpToSection,
    pageTitle,
    selectBoardCategory,
    shouldHideWidgetHeader,
    terminalTabs,
    useUnifiedResearchUi,
    visibleSections,
  };
}
