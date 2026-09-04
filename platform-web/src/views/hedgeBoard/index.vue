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
            <button
              type="button"
              class="hedge-board__tool-board-toggle"
              :aria-expanded="toolsExpanded"
              aria-controls="hedge-board-tool-list"
              @click="toolsExpanded = !toolsExpanded"
            >
              <span>{{ toolsExpanded ? '收起' : '展开' }}</span>
              <span class="hedge-board__tool-board-chevron" aria-hidden="true">⌄</span>
            </button>
          </div>

          <div v-if="toolsExpanded" id="hedge-board-tool-list" class="hedge-board__tool-board-body">
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
  import { ref, watch } from 'vue';
  import { PageWrapper } from '@/components/Page';
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
    terminalTabs,
    useUnifiedResearchUi,
    visibleSections,
  } = useHedgeBoardPage();

  const toolsExpanded = ref(false);

  watch(activeCategory, () => {
    toolsExpanded.value = false;
  });
</script>

<style lang="less" src="./hedgeBoard.less"></style>
