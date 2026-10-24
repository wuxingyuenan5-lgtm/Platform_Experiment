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

      <ResearchWorkspace :pages="pages" :active="activeView" :label="boardLabel">
        <EquityObservatoryPanel
          v-if="
            activeCategory === 'us' && ['themes', 'valuation', 'structure'].includes(activeView)
          "
          market="us"
          :view="activeView"
        />
        <MarketTerminalPage
          v-else-if="isTerminalCategory && activeTerminalConfig"
          :config="activeTerminalConfig"
          :market-tabs="terminalTabs"
          :view="activeView"
        />
        <MacroCalendarPanel v-else-if="activeView === 'calendar'" initially-expanded />
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
          :key="activeView"
          :module-id="activeModule.id"
          :module-label="activeModule.label"
          :formula="activeView === pages[0].key ? activeModule.formula : undefined"
          :sections="visibleSections.filter((section) => section.id === activeView)"
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
      </ResearchWorkspace>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, defineAsyncComponent } from 'vue';
  import { useRoute } from 'vue-router';
  import ResearchWorkspace from './components/ResearchWorkspace.vue';
  import { PageWrapper } from '@/components/Page';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import LocalChartWidget from './charts/LocalChartWidget';
  import HedgeResearchModule from './components/HedgeResearchModule.vue';
  import MacroCalendarPanel from './components/MacroCalendarPanel.vue';
  import WealthInformationPanel from './components/WealthInformationPanel.vue';
  import TradingViewWidget from './components/TradingViewWidget';
  import WidgetErrorBoundary from './components/WidgetErrorBoundary';
  import { useHedgeBoardPage } from './composables/useHedgeBoardPage';
  import ToolGroupSection from './tradingTools/components/ToolGroupSection.vue';

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
  const EquityObservatoryPanel = defineAsyncComponent(
    () => import('./components/EquityObservatoryPanel.vue'),
  );
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
  const pages = computed(() => {
    if (activeCategory.value === 'us')
      return [
        { key: 'overview', label: '大盘表现' },
        { key: 'themes', label: '主题产业链' },
        { key: 'valuation', label: '估值' },
        { key: 'structure', label: '结构与风险' },
        { key: 'rotation', label: '板块轮动' },
      ];
    if (activeCategory.value === 'global') return [{ key: 'details', label: '市场明细与区域轮动' }];
    return [
      ...visibleSections.value.map((section) => ({
        key: section.id,
        label: getSectionTitle(section.id, section.title),
      })),
      ...(activeCategory.value === 'macro'
        ? [
            { key: 'calendar', label: '经济日历' },
            { key: 'expectations', label: 'polymarket' },
          ]
        : []),
      ...(activeCategory.value === 'crypto' ? [{ key: 'wealth', label: '理财信息' }] : []),
      { key: 'tools', label: '研究工具' },
    ];
  });
  const activeView = computed(() => {
    const value = String(route.query.view || '');
    return pages.value.some((page) => page.key === value) ? value : pages.value[0].key;
  });
</script>

<style lang="less" src="./hedgeBoard.less"></style>
