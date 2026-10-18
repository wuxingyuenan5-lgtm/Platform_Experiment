<template>
  <section class="research-module" :class="{ 'research-module--gold': unified }" :id="moduleId">
    <HedgeBoardSubnav
      :sections="navigationSections"
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
      :class="{
        'chart-section--gold': unified,
        'market-detail-section-shell': isMarketDetailSection(section),
      }"
    >
      <div
        class="chart-section__heading"
        :class="{ 'market-detail-section-heading': isMarketDetailSection(section) }"
      >
        <div>
          <h4>{{ resolveSectionTitle(section.id, section.title) }}</h4>
        </div>
        <button
          v-if="isCollapsibleSection(section)"
          type="button"
          class="section-toggle market-detail-section-toggle"
          :aria-expanded="isMarketDetailExpanded(section.id)"
          :aria-controls="`${section.id}-content`"
          @click="toggleMarketDetailSection(section.id)"
        >
          {{ isMarketDetailExpanded(section.id) ? '收起' : '展开' }}
        </button>
      </div>

      <div
        v-if="!isCollapsibleSection(section) || isMarketDetailExpanded(section.id)"
        :id="`${section.id}-content`"
        class="widget-grid"
        :class="`widget-grid--${section.layout ?? 'three'}`"
      >
        <ChartExpand
          v-for="widget in orderedWidgets(section)"
          :title="resolveWidgetTitle(widget.localKey, widget.title)"
          :enabled="widget.kind !== 'external-link'"
          :key="`${section.id}-${widget.title}`"
          class="widget-card"
          :class="{
            'widget-card--local-chart': widget.kind === 'local-chart',
            'widget-card--reference': widget.kind === 'external-link',
            'widget-card--expandable': widget.kind !== 'external-link',
            'widget-card--wide':
              widget.localKey === 'macro-global-m2' ||
              widget.localKey === 'macro-fed-balance-structure' ||
              widget.localKey === 'etf-weekly-flows' ||
              widget.localKey === 'crypto-strategy-holdings',
            'widget-card--macro-fedwatch': widget.localKey === 'macro-fedwatch',
            'widget-card--macro-polymarket-fed': widget.localKey === 'macro-polymarket-fed',
            'widget-card--halving': widget.localKey === 'crypto-halving-cycles',
            'widget-card--urpd': widget.localKey === 'crypto-urpd',
            'widget-card--etf-premium': widget.localKey === 'crypto-etf-premium',
            'widget-card--cftc': widget.localKey === 'cftc-positioning',
          }"
        >
          <div v-if="!shouldHideWidgetHeader(section.id, widget)" class="widget-card__header">
            <div class="widget-card__header-main">
              <div class="widget-card__title-row">
                <h5>{{ resolveWidgetTitle(widget.localKey, widget.title) }}</h5>
              </div>
              <div class="widget-card__actions">
                <button
                  v-if="widget.deferUntilExpanded"
                  type="button"
                  class="widget-card__defer-toggle"
                  :aria-expanded="isDeferredWidgetExpanded(section.id, widget)"
                  @click="toggleDeferredWidget(section.id, widget)"
                >
                  {{ isDeferredWidgetExpanded(section.id, widget) ? '收起' : '展开加载' }}
                </button>
                <a
                  v-if="resolveWidgetSourceLink(widget)"
                  class="widget-card__link"
                  :href="resolveWidgetSourceLink(widget)"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ widget.sourceLinkLabel ?? '参考网页 ↗' }}
                </a>
                <a
                  v-for="link in widget.referenceLinks ?? []"
                  :key="link.href"
                  class="widget-card__link"
                  :href="link.href"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ link.label }} ↗
                </a>
              </div>
            </div>
          </div>

          <component :is="widgetErrorBoundary" :widget-title="widget.title">
            <div
              v-if="widget.deferUntilExpanded && !isDeferredWidgetExpanded(section.id, widget)"
              class="deferred-widget-placeholder"
            >
              <strong>默认折叠</strong>
              <span>点击“展开加载”后读取 CFTC 周度持仓历史</span>
            </div>
            <div v-else-if="widget.kind === 'external-link'" class="external-reference-card">
              <p>{{ widget.subtitle }}</p>
            </div>
            <VisibleChart
              v-else-if="widget.kind === 'local-chart' && widget.localKey"
              :height="widget.height"
            >
              <component :is="localChartWidget" :widget="widget" />
            </VisibleChart>
            <component :is="tradingViewWidget" v-else :widget="widget" />
          </component>
        </ChartExpand>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, type Component } from 'vue';
  import HedgeBoardSubnav from './HedgeBoardSubnav.vue';
  import VisibleChart from './VisibleChart';
  import ChartExpand from './ChartExpand.vue';
  import type { ChartSection, LocalWidgetKey, WidgetConfig } from '../nativeData/dashboardClean';

  const props = defineProps<{
    moduleId: string;
    moduleLabel: string;
    formula?: {
      title: string;
      description: string;
    };
    sections: readonly ChartSection[];
    trailingNavigationSections?: ReadonlyArray<{ id: string; title: string }>;
    unified: boolean;
    resolveSectionTitle: (sectionId: string, fallback: string) => string;
    shouldHideWidgetHeader: (sectionId: string, widget: WidgetConfig) => boolean;
    resolveWidgetTitle: (localKey: LocalWidgetKey | undefined, fallback: string) => string;
    resolveWidgetSourceLink: (widget: WidgetConfig) => string | undefined;
    localChartWidget: Component;
    tradingViewWidget: Component;
    widgetErrorBoundary: Component;
  }>();

  function orderedWidgets(section: ChartSection) {
    return [
      ...section.widgets.filter((widget) => widget.localKey === 'etf-weekly-flows'),
      ...section.widgets.filter(
        (widget) => widget.kind !== 'external-link' && widget.localKey !== 'etf-weekly-flows',
      ),
      ...section.widgets.filter((widget) => widget.kind === 'external-link'),
    ];
  }

  const navigationSections = computed(() => [
    ...props.sections,
    ...(props.trailingNavigationSections ?? []),
  ]);

  const expandedMarketDetailSectionIds = ref<string[]>([]);
  const expandedDeferredWidgetIds = ref<string[]>([]);

  function deferredWidgetId(sectionId: string, widget: WidgetConfig) {
    return `${sectionId}-${widget.localKey ?? widget.title}`;
  }

  function isDeferredWidgetExpanded(sectionId: string, widget: WidgetConfig) {
    return expandedDeferredWidgetIds.value.includes(deferredWidgetId(sectionId, widget));
  }

  function toggleDeferredWidget(sectionId: string, widget: WidgetConfig) {
    const id = deferredWidgetId(sectionId, widget);
    expandedDeferredWidgetIds.value = isDeferredWidgetExpanded(sectionId, widget)
      ? expandedDeferredWidgetIds.value.filter((item) => item !== id)
      : [...expandedDeferredWidgetIds.value, id];
  }

  function isCollapsibleSection(section: ChartSection) {
    return isMarketDetailSection(section) || section.id === 'gold-research-analysts';
  }

  function isMarketDetailSection(section: ChartSection) {
    return section.widgets.some((widget) => widget.localKey?.endsWith('-market-detail-table'));
  }

  function isMarketDetailExpanded(sectionId: string) {
    return expandedMarketDetailSectionIds.value.includes(sectionId);
  }

  function toggleMarketDetailSection(sectionId: string) {
    expandedMarketDetailSectionIds.value = isMarketDetailExpanded(sectionId)
      ? expandedMarketDetailSectionIds.value.filter((id) => id !== sectionId)
      : [...expandedMarketDetailSectionIds.value, sectionId];
  }

  defineEmits<{
    (event: 'jump', sectionId: string): void;
  }>();
</script>

<style scoped lang="less">
  @import '../../strategy/shared/strategy-theme.less';
  @import './marketDetailSection.less';

  @container research-section (max-width: 1440px) {
    .widget-grid--three {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @container research-section (max-width: 960px) {
    .widget-card--etf-premium {
      grid-column: 1 / -1;
    }

    .widget-grid--three,
    .widget-grid--two {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 768px) {
    .formula-strip,
    .chart-section {
      padding: 12px;
      border-radius: 14px;
    }

    .formula-strip {
      grid-template-columns: 1fr;
    }
  }

  .research-module {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .external-reference-card {
    padding: 8px 18px 16px;
    color: var(--hedge-cool-muted, #6d8293);
    font-size: 13px;
    line-height: 1.65;
  }

  .external-reference-card p {
    margin: 0 0 10px;
    color: var(--hedge-cool-text, #18313c);
    font-size: 14px;
    font-weight: 650;
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
    border: 1px solid var(--hedge-cool-border, rgb(193 207 220 / 88%));
    background: linear-gradient(180deg, rgb(255 255 255 / 95%), rgb(243 248 252 / 96%)), #fff;
    box-shadow: 0 18px 45px rgb(31 41 55 / 5%);
  }

  /* FedWatch is a full-width matrix; keep Polymarket on the following grid row. */
  .widget-card--macro-fedwatch {
    grid-column: 1 / -1;
  }

  .widget-card--macro-polymarket-fed {
    grid-column: 1 / -1;
  }

  .widget-card--halving,
  .widget-card--urpd {
    grid-column: 1 / -1;
  }

  .widget-card--etf-premium {
    grid-column: span 2;
  }

  .formula-strip,
  .chart-section {
    padding: 16px;
    border-radius: 16px;
  }

  .formula-strip {
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: 18px;
    background: linear-gradient(135deg, rgb(226 236 244 / 96%), rgb(248 251 253 / 98%));
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
    container: research-section / inline-size;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .chart-section__heading h4 {
    margin: 0;
    font-size: 18px;
    font-weight: 800;
  }

  .chart-section__heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .section-toggle {
    min-height: 32px;
    padding: 5px 12px;
    border: 1px solid rgb(109 130 147 / 28%);
    border-radius: 999px;
    background: #fff;
    color: var(--hedge-cool-muted, #526b7d);
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }

  .section-toggle:hover,
  .section-toggle:focus-visible {
    border-color: rgb(22 93 255 / 42%);
    outline: none;
    background: rgb(22 93 255 / 6%);
    color: #165dff;
  }

  .widget-grid {
    display: grid;
    gap: 16px;
    align-items: start;
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
    border-radius: 14px;
  }

  .widget-card__header {
    padding: 18px 20px 0;
  }

  .widget-card--expandable .widget-card__header-main {
    padding-right: 40px;
  }

  .widget-card__header-main {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .widget-card--local-chart .widget-card__header-main {
    display: flex;
    flex-wrap: wrap;
    align-items: start;
    padding-bottom: 12px;
  }

  .widget-card--local-chart .widget-card__title-row {
    flex: 1 1 190px;
    text-align: left;
  }

  .widget-card__title-row h5 {
    margin: 0;
    font-size: 15px;
    font-weight: 800;
  }

  .widget-card--local-chart .widget-card__title-row h5 {
    font-size: 16px;
    line-height: 1.35;
  }

  .widget-card__actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px;
  }

  .widget-card__defer-toggle {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 4px 9px;
    border: 1px solid rgb(22 93 255 / 28%);
    border-radius: 999px;
    background: rgb(22 93 255 / 5%);
    color: #165dff;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }

  .widget-card__defer-toggle:hover,
  .widget-card__defer-toggle:focus-visible {
    border-color: rgb(22 93 255 / 52%);
    outline: none;
    background: rgb(22 93 255 / 10%);
  }

  .deferred-widget-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 116px;
    padding: 18px;
    color: var(--hedge-cool-muted, #6d8293);
    font-size: 12px;
    text-align: center;
    gap: 7px;
  }

  .deferred-widget-placeholder strong {
    color: var(--hedge-cool-text, #18313c);
    font-size: 14px;
  }

  .widget-card__link {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 4px 9px;
    transition: border-color 0.18s ease, color 0.18s ease, background 0.18s ease;
    border: 1px solid rgb(109 130 147 / 28%);
    border-radius: 999px;
    color: var(--hedge-cool-muted, #526b7d);
    font-size: 12px;
    font-weight: 700;
    text-decoration: none;
  }

  .widget-card__link:hover,
  .widget-card__link:focus-visible {
    border-color: rgb(22 93 255 / 42%);
    outline: none;
    background: rgb(22 93 255 / 6%);
    color: #165dff;
  }

  .widget-card--local-chart .widget-card__actions {
    flex: 0 1 auto;
  }

  .widget-card--cftc {
    grid-column: 1 / -1;
  }

  #crypto-external-research-content {
    align-items: stretch;
  }

  #crypto-external-research-content :deep(.source-series-summary .source-series-legend) {
    min-height: 96px;
  }

  .chart-section--gold {
    padding: 16px;
    border-radius: 16px;
    background: linear-gradient(180deg, rgb(255 255 255 / 98%), rgb(243 248 252 / 98%)), #fff;
    box-shadow: 0 16px 36px rgb(31 41 55 / 4%);
  }

  .widget-card--wide {
    grid-column: 1 / -1;
  }

  .widget-card--reference {
    box-shadow: none;
  }
</style>
