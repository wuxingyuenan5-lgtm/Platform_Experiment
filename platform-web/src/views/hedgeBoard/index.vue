<template>
  <PageWrapper :title="pageTitle">
    <div class="hedge-board">
      <section class="strategy-top-toolbar">
        <div class="strategy-top-toolbar__left">
          <CompactSegmentTabs
            :items="hedgeBoardTabs"
            :model-value="activeCategory"
            @update:model-value="selectBoardCategory"
          />
        </div>
      </section>

      <ResearchWorkspace
        :pages="pages"
        :active="workspaceView"
        :sidebar-active="isMacroDetail ? 'macro-details' : activeView"
        :label="boardLabel"
      >
        <div v-if="isMacroDetail" class="macro-detail-navigation">
          <nav class="macro-detail-tabs" aria-label="宏观详情分类">
            <RouterLink
              v-for="item in macroDetailPages"
              :key="item.key"
              :to="{
                path: route.path,
                query: {
                  ...route.query,
                  view: 'macro-details',
                  section: item.key,
                  subsection: undefined,
                },
              }"
              :aria-current="activeView === item.key ? 'page' : undefined"
              >{{ item.label }}</RouterLink
            >
          </nav>
          <nav
            v-if="detailGroups.length"
            class="macro-detail-tabs macro-detail-subtabs"
            aria-label="宏观详情子分类"
          >
            <RouterLink
              v-for="item in detailGroups"
              :key="item.key"
              :to="{
                path: route.path,
                query: {
                  ...route.query,
                  view: 'macro-details',
                  section: activeView,
                  subsection: item.key,
                },
              }"
              :aria-current="activeDetailGroup === item.key ? 'page' : undefined"
              >{{ item.label }}</RouterLink
            >
          </nav>
        </div>
        <LiquidityDashboard
          v-if="
            activeCategory === 'macro' &&
            activeView === 'macro-liquidity' &&
            activeDetailGroup === 'global'
          "
        />
        <ChinaLiquidityPanel
          v-if="
            activeCategory === 'macro' &&
            activeView === 'macro-liquidity' &&
            activeDetailGroup === 'cn'
          "
        />
        <template
          v-if="
            activeCategory === 'us' && ['themes', 'valuation', 'structure'].includes(activeView)
          "
        >
          <EquityObservatoryPanel market="us" :view="activeView" />
          <MarketTerminalPage
            v-if="activeView === 'themes' && activeTerminalConfig"
            :config="activeTerminalConfig"
            :market-tabs="terminalTabs"
            view="themes"
          />
          <IndexValuationSnapshot v-if="activeView === 'themes'" />
          <Sp500ResearchPanel v-if="activeView === 'structure'" />
          <HistoryRiskPanel v-if="activeView === 'structure'" />
          <VisibleChart v-if="activeView === 'structure'" :height="600"
            ><MarketSeasonalityPanel market="us"
          /></VisibleChart>
        </template>
        <AiIndustryPanel v-else-if="activeCategory === 'us' && activeView === 'ai'" />
        <UsOptionsStressPanel
          v-else-if="activeCategory === 'us' && activeView === 'options-stress'"
        />
        <MarketTerminalPage
          v-else-if="isTerminalCategory && activeTerminalConfig"
          :config="activeTerminalConfig"
          :market-tabs="terminalTabs"
          :view="activeView"
        />
        <MacroNarrativePanel
          v-else-if="activeCategory === 'macro' && activeView === 'narratives'"
        />
        <MacroCyclePanel v-else-if="activeCategory === 'macro' && activeView === 'cycles'" />
        <CrossAssetScreener
          v-else-if="activeCategory === 'macro' && activeView === 'cross-asset-screening'"
        />
        <ViewpointTrackingPanel
          v-else-if="activeCategory === 'macro' && activeView === 'viewpoints'"
        />
        <MacroExpectationPanel v-else-if="activeView === 'expectations'" initially-expanded />
        <WealthInformationPanel v-else-if="activeView === 'wealth'" initially-expanded />
        <section
          v-else-if="activeView === 'tools' && activeTradingToolCatalog"
          class="hedge-board__tool-board"
        >
          <div class="hedge-board__tool-board-head"
            ><h3>{{ activeTradingToolCatalog.title }}</h3></div
          >
          <div class="hedge-board__tool-board-body"
            ><ToolGroupSection
              v-for="group in activeTradingToolCatalog.groups"
              :key="group.id"
              :group="group"
          /></div>
        </section>
        <HedgeResearchModule
          v-else
          :key="workspaceView"
          :hide-headings="isMacroDetail"
          :module-id="activeModule.id"
          :module-label="activeModule.label"
          :formula="activeView === pages[0].key ? activeModule.formula : undefined"
          :sections="detailSections"
          standalone
          :unified="useUnifiedResearchUi"
          :resolve-section-title="getSectionTitle"
          :should-hide-widget-header="shouldHideWidgetHeader"
          :resolve-widget-title="getWidgetTitle"
          :resolve-widget-source-link="getWidgetSourceLink"
          :local-chart-widget="LocalChartWidget"
          :trading-view-widget="TradingViewWidget"
          :widget-error-boundary="WidgetErrorBoundary"
        />
        <WeeklyIndicatorSupplement
          v-if="isMacroDetail && hasWeeklyDetail(activeView, activeDetailGroup)"
          :key="'weekly-' + workspaceView"
          :detail-group="activeDetailGroup"
          :section="activeView"
        />
        <MacroCalendarPanel v-if="activeCategory === 'macro' && activeView === 'macro-market'" />
        <VisibleChart v-if="activeCategory === 'global'" :height="600"
          ><MacroCyclePanel mode="rotation"
        /></VisibleChart>
      </ResearchWorkspace>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, defineAsyncComponent } from 'vue';
  import { RouterLink, useRoute } from 'vue-router';
  import ResearchWorkspace from './components/ResearchWorkspace.vue';
  import { PageWrapper } from '@/components/Page';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import LocalChartWidget from './charts/LocalChartWidget';
  import HedgeResearchModule from './components/HedgeResearchModule.vue';
  import MacroCalendarPanel from './components/MacroCalendarPanel.vue';
  import WealthInformationPanel from './components/WealthInformationPanel.vue';
  import TradingViewWidget from './components/TradingViewWidget';
  import WidgetErrorBoundary from './components/WidgetErrorBoundary';
  import VisibleChart from './components/VisibleChart';
  import { macroDetailGroups, hasWeeklyDetail } from './macro/detailGroups';
  import { useHedgeBoardPage } from './composables/useHedgeBoardPage';
  import ToolGroupSection from './tradingTools/components/ToolGroupSection.vue';

  const MarketSeasonalityPanel = defineAsyncComponent(
    () => import('./components/MarketSeasonalityPanel.vue'),
  );

  const MarketTerminalPage = defineAsyncComponent(
    () => import('./components/MarketTerminalPage.vue'),
  );

  const {
    activeCategory,
    activeModule,
    activeTerminalConfig,
    activeTradingToolCatalog,
    getSectionTitle,
    getWidgetSourceLink,
    getWidgetTitle,
    hedgeBoardTabs,
    isTerminalCategory,
    pageTitle,
    selectBoardCategory,
    shouldHideWidgetHeader,
    terminalTabs,
    useUnifiedResearchUi,
    visibleSections,
  } = useHedgeBoardPage();

  const MacroExpectationPanel = defineAsyncComponent(
    () => import('./macro/MacroExpectationPanel.vue'),
  );
  const MacroNarrativePanel = defineAsyncComponent(() => import('./macro/MacroNarrativePanel.vue'));
  const MacroCyclePanel = defineAsyncComponent(() => import('./macro/MacroCyclePanel.vue'));
  const ViewpointTrackingPanel = defineAsyncComponent(
    () => import('./components/ViewpointTrackingPanel.vue'),
  );
  const CrossAssetScreener = defineAsyncComponent(() => import('./macro/CrossAssetScreener.vue'));
  const EquityObservatoryPanel = defineAsyncComponent(
    () => import('./components/EquityObservatoryPanel.vue'),
  );
  const IndexValuationSnapshot = defineAsyncComponent(
    () => import('./components/IndexValuationSnapshot.vue'),
  );
  const AiIndustryPanel = defineAsyncComponent(() => import('./ai/AiIndustryPanel.vue'));
  const UsOptionsStressPanel = defineAsyncComponent(
    () => import('./components/UsOptionsStressPanel.vue'),
  );
  const ChinaLiquidityPanel = defineAsyncComponent(() => import('./macro/ChinaLiquidityPanel.vue'));
  const LiquidityDashboard = defineAsyncComponent(() => import('./macro/LiquidityDashboard.vue'));
  const WeeklyIndicatorSupplement = defineAsyncComponent(
    () => import('./macro/WeeklyIndicatorSupplement.vue'),
  );
  const Sp500ResearchPanel = defineAsyncComponent(
    () => import('./components/Sp500ResearchPanel.vue'),
  );
  const HistoryRiskPanel = defineAsyncComponent(() => import('./components/HistoryRiskPanel.vue'));
  const route = useRoute();
  const boardLabel = computed(
    () =>
      ({
        macro: '宏观研究',
        gold: '商品研究',
        crypto: '加密研究',
        us: '美股研究',
        global: '全球市场',
        aShare: 'A股研究',
      }[activeCategory.value]),
  );
  const macroDetailPages = computed(() => [
    ...visibleSections.value
      .filter((section) => section.id !== 'macro-market')
      .map((section) => ({ key: section.id, label: getSectionTitle(section.id, section.title) })),
    { key: 'expectations', label: 'polymarket' },
  ]);
  const pages = computed(() => {
    if (activeCategory.value === 'macro')
      return [
        { key: 'macro-market', label: '市场总览' },
        { key: 'narratives', label: '宏观主题与叙事' },
        { key: 'cross-asset-screening', label: '跨资产筛选' },
        { key: 'macro-details', label: '宏观详情' },
        { key: 'cycles', label: '周期分析' },
        { key: 'viewpoints', label: '观点跟踪' },
        { key: 'tools', label: '研究工具' },
      ];
    if (activeCategory.value === 'us')
      return [
        { key: 'overview', label: '市场总览' },
        { key: 'themes', label: '主题研究' },
        { key: 'ai', label: 'AI产业' },
        { key: 'valuation', label: '估值' },
        { key: 'structure', label: '结构与风险' },
        { key: 'options-stress', label: '期权与流动性压力' },
      ];
    if (activeCategory.value === 'global') return [{ key: 'details', label: '市场明细与区域轮动' }];
    return [
      ...visibleSections.value.map((section) => ({
        key: section.id,
        label: getSectionTitle(section.id, section.title),
      })),
      ...(activeCategory.value === 'crypto' ? [{ key: 'wealth', label: '理财信息' }] : []),
      { key: 'tools', label: '研究工具' },
    ];
  });
  const activeView = computed(() => {
    const value = String(route.query.view || '');
    if (activeCategory.value === 'macro') {
      if (value === 'macro-details') {
        const section = String(route.query.section || '');
        return macroDetailPages.value.some((page) => page.key === section)
          ? section
          : macroDetailPages.value[0].key;
      }
      // Existing bookmarked detail links still open the same content.
      if (macroDetailPages.value.some((page) => page.key === value)) return value;
    }
    return pages.value.some((page) => page.key === value) ? value : pages.value[0].key;
  });
  const detailGroups = computed(() =>
    isMacroDetail.value ? macroDetailGroups[activeView.value] || [] : [],
  );
  const activeDetailGroup = computed(() => {
    const requested = String(route.query.subsection || '');
    return (
      detailGroups.value.find((group) => group.key === requested)?.key ||
      detailGroups.value[0]?.key ||
      ''
    );
  });
  const workspaceView = computed(() =>
    isMacroDetail.value ? `${activeView.value}:${activeDetailGroup.value}` : activeView.value,
  );
  const detailSections = computed(() =>
    visibleSections.value
      .filter((section) => section.id === activeView.value)
      .map((section) => ({
        ...section,
        widgets: section.widgets.filter((widget) => {
          const group = detailGroups.value.find((item) => item.key === activeDetailGroup.value);
          return !group || group.includes(widget);
        }),
      })),
  );
  const isMacroDetail = computed(
    () =>
      activeCategory.value === 'macro' &&
      macroDetailPages.value.some((page) => page.key === activeView.value),
  );
</script>

<style lang="less" src="./hedgeBoard.less"></style>

<style scoped lang="less">
  .macro-detail-navigation {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px 24px;
    margin-bottom: 16px;
    padding: 6px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
  }

  .macro-detail-subtabs {
    margin-left: auto;
  }

  .macro-detail-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;

    a {
      padding: 8px 14px;
      border-radius: 7px;
      color: var(--strategy-text-2);
      font-size: 13px;
    }

    a[aria-current='page'] {
      background: var(--strategy-accent-soft);
      color: var(--strategy-accent-strong);
      font-weight: 600;
    }

    a:focus-visible {
      outline: 2px solid var(--strategy-accent);
      outline-offset: 2px;
    }
  }
</style>
