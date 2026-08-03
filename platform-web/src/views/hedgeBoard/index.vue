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

      <ProductDataStatusAlert
        v-if="staticDesignWidgets.length"
        :meta="staticDesignMeta"
        class="hedge-board__data-state"
      />

      <MarketTerminalPage
        v-if="isTerminalCategory && activeTerminalConfig"
        :config="activeTerminalConfig"
        :market-tabs="terminalTabs"
      />

      <div
        v-else
        class="terminal-content"
        :class="{ 'terminal-content--gold': useUnifiedResearchUi }"
      >
        <HedgeResearchModule
          :module-id="activeModule.id"
          :module-label="activeModule.label"
          :formula="activeModule.formula"
          :sections="visibleSections"
          :unified="useUnifiedResearchUi"
          :resolve-section-title="getSectionTitle"
          :should-hide-widget-header="shouldHideWidgetHeader"
          :resolve-widget-title="getWidgetTitle"
          :resolve-widget-source-link="getWidgetSourceLink"
          :local-chart-widget="LocalChartWidget"
          :trading-view-widget="TradingViewWidget"
          :widget-error-boundary="WidgetErrorBoundary"
          @jump="jumpToSection"
        />

        <section v-if="activeTradingToolCatalog" class="hedge-board__tool-board">
          <div class="hedge-board__tool-board-head">
            <h3>{{ activeTradingToolCatalog.title }}</h3>
          </div>

          <div class="hedge-board__tool-board-body">
            <ToolGroupSection
              v-for="group in activeTradingToolCatalog.groups"
              :key="group.id"
              :group="group"
            />
          </div>
        </section>
      </div>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import type { ProductDataMeta } from '@/api/platform/productDataState';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import LocalChartWidget from './charts/LocalChartWidget';
  import HedgeResearchModule from './components/HedgeResearchModule.vue';
  import MarketTerminalPage from './components/MarketTerminalPage.vue';
  import TradingViewWidget from './components/TradingViewWidget';
  import WidgetErrorBoundary from './components/WidgetErrorBoundary';
  import { useHedgeBoardPage } from './composables/useHedgeBoardPage';
  import ToolGroupSection from './tradingTools/components/ToolGroupSection.vue';

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
    jumpToSection,
    pageTitle,
    selectBoardCategory,
    shouldHideWidgetHeader,
    staticDesignWidgets,
    terminalTabs,
    useUnifiedResearchUi,
    visibleSections,
  } = useHedgeBoardPage();

  const staticDesignMeta = computed<ProductDataMeta>(() => ({
    status: 'not_configured',
    source: `hedge-board:${activeCategory.value}:static-design`,
    timezone: 'source-defined',
    unit: 'market research widget',
    precision: 'decimal-string-required',
    errorCode: 'static_design_isolated',
    message: `${staticDesignWidgets.value.length}个仅有静态设计稿、没有Provider Owner的图表已从正式数据展示中隔离；TradingView和已注册Research Provider组件继续可用。`,
  }));
</script>

<style lang="less" src="./hedgeBoard.less"></style>
<style scoped>
  .hedge-board__data-state {
    margin: 0 0 16px;
  }
</style>
