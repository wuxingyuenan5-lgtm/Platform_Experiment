import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  researchModules,
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
  'gold-flows': { title: 'ETF与资金面' },
  'gold-central-bank': { title: '央行购金' },
  'gold-main': { title: '黄金主图' },
  'gold-rates': { title: '利率与通胀' },
  'crypto-etf': { title: '加密资金面' },
};

const widgetTextOverrides: Record<string, { title?: string }> = {
  'etf-weekly-flows': { title: '全球各地区ETF每周流入' },
  'etf-ytd-summary': { title: '全球 ETF 年内汇总' },
  'spdr-daily-flow': { title: '金价 vs SPDR 每日流量' },
  'spdr-holdings-vs-price': { title: 'SPDR 持仓量 vs 黄金价格' },
  'central-bank-holders': { title: '官方黄金储备前十' },
  'central-bank-buyers': { title: '近一年持续增持的央行' },
};

const ETF_REFERENCE_URL =
  'https://china.gold.org/goldhub/data/gold-etfs-holdings-and-flows#from-login=1&login-type=wechat';

const widgetSourceLinks: Partial<Record<string, string>> = {
  'btc-etf-flow': 'https://sosovalue.com/zh/assets/etf/Total_Crypto_Spot_ETF_Fund_Flow?page=usBTC',
  'btc-treasury-flow': 'https://sosovalue.com/zh/assets/bitcoin-treasuries/weekly-net-inflow',
  'etf-weekly-flows': ETF_REFERENCE_URL,
  'etf-ytd-summary': ETF_REFERENCE_URL,
  'spdr-daily-flow': 'https://sc.macromicro.me/collections/45/mm-gold-price/23274/gld-fund-flow',
  'spdr-holdings-vs-price':
    'https://sc.macromicro.me/collections/45/mm-gold-price/712/spdr-gold-trust-etf-gold-price',
};

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
  const visibleSections = computed(() => activeModule.value.sections);
  const pageTitle = computed(() => `对冲基金看板 / ${activeBoardNav.value.label}`);

  function getSectionTitle(sectionId: string, fallback: string) {
    return sectionLabelOverrides[sectionId]?.title ?? fallback;
  }

  function getWidgetTitle(localKey: string | undefined, fallback: string) {
    return localKey ? widgetTextOverrides[localKey]?.title ?? fallback : fallback;
  }

  function getWidgetSourceLink(localKey: string | undefined) {
    return localKey ? widgetSourceLinks[localKey] ?? '' : '';
  }

  function selectBoardCategory(key: string) {
    const nextPath = moduleRoutes[key as HedgeCategory];
    if (nextPath) void router.push(nextPath);
  }

  function shouldHideWidgetHeader(sectionId: string, widget: WidgetConfig) {
    if (['macro-liquidity', 'gold-main', 'crypto-main'].includes(sectionId)) return true;
    return widget.kind === 'local-chart' && widget.localKey?.includes('market-detail-table');
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
