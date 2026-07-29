<template>
  <section class="research-module" :class="{ 'research-module--gold': unified }" :id="moduleId">
    <HedgeBoardSubnav
      :sections="sections"
      :module-label="moduleLabel"
      :unified="unified"
      :resolve-title="resolveSectionTitle"
      @jump="$emit('jump', $event)"
    />

    <div v-if="formula" class="formula-strip">
      <div>
        <span>核心公式</span>
        <strong>{{ formula.title }}</strong>
      </div>
    </div>

    <section
      v-for="section in sections"
      :id="section.id"
      :key="section.id"
      class="chart-section"
      :class="{ 'chart-section--gold': unified }"
    >
      <div class="chart-section__heading">
        <div>
          <h4>{{ resolveSectionTitle(section.id, section.title) }}</h4>
        </div>
      </div>

      <div class="widget-grid" :class="`widget-grid--${section.layout ?? 'three'}`">
        <article
          v-for="widget in section.widgets"
          :key="`${section.id}-${widget.title}`"
          class="widget-card"
          :class="{ 'widget-card--local-chart': widget.kind === 'local-chart' }"
        >
          <div v-if="!shouldHideWidgetHeader(section.id, widget)" class="widget-card__header">
            <div class="widget-card__header-main">
              <div class="widget-card__title-row">
                <h5>{{ resolveWidgetTitle(widget.localKey, widget.title) }}</h5>
              </div>
              <a
                v-if="resolveWidgetSourceLink(widget.localKey)"
                class="widget-card__link"
                :href="resolveWidgetSourceLink(widget.localKey)"
                target="_blank"
                rel="noopener noreferrer"
              >
                原网址
              </a>
            </div>
          </div>

          <component :is="widgetErrorBoundary" :widget-title="widget.title">
            <component
              :is="localChartWidget"
              v-if="widget.kind === 'local-chart' && widget.localKey"
              :widget="widget"
            />
            <component :is="tradingViewWidget" v-else :widget="widget" />
          </component>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
  import type { Component } from 'vue';
  import HedgeBoardSubnav from './HedgeBoardSubnav.vue';
  import type { ChartSection, LocalWidgetKey, WidgetConfig } from '../nativeData/dashboardClean';

  defineProps<{
    moduleId: string;
    moduleLabel: string;
    formula?: {
      title: string;
      description: string;
    };
    sections: readonly ChartSection[];
    unified: boolean;
    resolveSectionTitle: (sectionId: string, fallback: string) => string;
    shouldHideWidgetHeader: (sectionId: string, widget: WidgetConfig) => boolean;
    resolveWidgetTitle: (localKey: LocalWidgetKey | undefined, fallback: string) => string;
    resolveWidgetSourceLink: (localKey: LocalWidgetKey | undefined) => string | undefined;
    localChartWidget: Component;
    tradingViewWidget: Component;
    widgetErrorBoundary: Component;
  }>();

  defineEmits<{
    (event: 'jump', sectionId: string): void;
  }>();
</script>

<style scoped lang="less">
  @import '../../strategy/shared/strategy-theme.less';

  .research-module {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .research-module--gold {
    padding: 0;
    border: none;
    background: transparent;
    box-shadow: none;
  }

  .formula-strip,
  .chart-section,
  .widget-card {
    border: 1px solid var(--hedge-cool-border, rgba(193, 207, 220, 0.88));
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(243, 248, 252, 0.96)),
      #fff;
    box-shadow: 0 18px 45px rgba(31, 41, 55, 0.05);
  }

  .formula-strip,
  .chart-section {
    border-radius: 24px;
    padding: 22px;
  }

  .formula-strip {
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: 18px;
    background: linear-gradient(135deg, rgba(226, 236, 244, 0.96), rgba(248, 251, 253, 0.98));
  }

  .formula-strip span {
    display: block;
    color: var(--hedge-cool-muted, #6d8293);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
  }

  .formula-strip strong,
  .chart-section__heading h4,
  .widget-card__header h5 {
    color: var(--hedge-cool-text, #18313c);
  }

  .formula-strip strong {
    display: block;
    margin-top: 6px;
    font-size: 18px;
    font-weight: 800;
  }

  .chart-section {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .chart-section__heading h4 {
    margin: 0;
    font-size: 22px;
    font-weight: 800;
  }

  .widget-grid {
    display: grid;
    gap: 16px;
  }

  .widget-grid--hero {
    grid-template-columns: minmax(0, 1fr);
  }

  .widget-grid--two {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .widget-grid--three {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .widget-card {
    min-width: 0;
    overflow: hidden;
    border-radius: 20px;
  }

  .widget-card__header {
    padding: 14px 16px 0;
  }

  .widget-card__header-main {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .widget-card--local-chart .widget-card__header-main {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: start;
  }

  .widget-card--local-chart .widget-card__title-row {
    grid-column: 2;
    justify-self: center;
    text-align: center;
  }

  .widget-card__title-row h5 {
    margin: 0;
    font-size: 15px;
    font-weight: 800;
  }

  .widget-card--local-chart .widget-card__title-row h5 {
    font-size: 17px;
    line-height: 1.35;
  }

  .widget-card__link {
    color: var(--hedge-cool-muted, #6d8293);
    font-size: 12px;
    font-weight: 700;
    text-decoration: none;
  }

  .widget-card--local-chart .widget-card__link {
    grid-column: 3;
    justify-self: end;
  }

  .chart-section--gold {
    padding: 22px 24px 24px;
    border-radius: 20px;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 248, 252, 0.98)),
      #fff;
    box-shadow: 0 16px 36px rgba(31, 41, 55, 0.04);
  }

  @media (max-width: 1200px) {
    .widget-grid--three,
    .widget-grid--two {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 768px) {
    .formula-strip,
    .chart-section {
      padding: 18px;
      border-radius: 20px;
    }

    .formula-strip {
      grid-template-columns: 1fr;
    }
  }
</style>
