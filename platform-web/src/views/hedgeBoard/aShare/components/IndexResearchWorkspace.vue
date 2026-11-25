<template>
  <section class="object-workspace" aria-label="指数与风格研究">
    <nav class="object-tabs" aria-label="指数与风格视角">
      <button
        v-for="item in tabs"
        :key="item.key"
        :aria-pressed="tab === item.key"
        @click="tab = item.key"
        >{{ item.label }}</button
      >
    </nav>
    <div v-show="tab === 'valuation'" class="index-panels">
      <KeepAlive
        ><EquityObservatoryPanel
          v-if="tab === 'valuation'"
          market="cn"
          view="valuation"
          :refresh-key="refreshKey"
        >
          <template #valuation="{ charts }">
            <IndexValuationPanel
              :charts="charts"
              :refresh-key="refreshKey"
              :selection="valuationSelection"
              initial-comparison-open
              hide-style-groups
            />
          </template> </EquityObservatoryPanel
      ></KeepAlive>
    </div>
    <div v-if="tab === 'breadth'" class="index-panels">
      <EquityObservatoryPanel
        market="cn"
        view="crowding"
        crowding-scope="indices"
        embedded
        :refresh-key="refreshKey"
      />
      <EquityObservatoryPanel
        market="cn"
        view="crowding"
        crowding-scope="market"
        :refresh-key="refreshKey"
      >
        <template #breadth-history="{ snapshot, stale, breadthRanks }">
          <MarketContextPanel
            section="breadth"
            breadth-part="history"
            :breadth-snapshot="snapshot"
            :breadth-ranks="breadthRanks"
            :snapshot-stale="stale"
            :refresh-key="refreshKey"
          />
        </template>
        <template #concentration-history="{ snapshot, stale }">
          <MarketMonitorPanel
            section="congestion"
            embedded
            :concentration-snapshot="snapshot"
            :snapshot-stale="stale"
            :refresh-key="refreshKey"
          />
        </template>
      </EquityObservatoryPanel>
    </div>
    <section v-if="tab === 'style'" class="object-card style-card">
      <EquityThemePanel
        v-if="data?.themes"
        market="cn"
        view="styles"
        embedded
        compact-style
        :data="data.themes"
        :industries="data.structure?.industries || []"
      />
      <p v-else class="object-source">暂无可用风格观察数据。</p>
    </section>
    <EquityObservatoryPanel
      v-if="tab === 'style'"
      market="cn"
      view="valuation"
      embedded
      :refresh-key="refreshKey"
    >
      <template #valuation="{ charts }">
        <IndexValuationGroupTable
          v-for="group in styleGroups"
          :key="group.name"
          :group="group"
          :charts="styleValuationData(charts).chartsById"
          :as-of="styleValuationData(charts).asOf"
          :selected-id="valuationSelection?.index"
          @select="openValuation"
        />
      </template>
    </EquityObservatoryPanel>
  </section>
</template>
<script setup lang="ts">
  import { defineAsyncComponent, shallowRef } from 'vue';
  import type { EquityObservatory, IndexValuationChart } from '@/api/equityObservatory';
  import { observationGroups } from '../../components/indexValuationSnapshot';

  const IndexValuationPanel = defineAsyncComponent(
    () => import('../../components/IndexValuationPanel.vue'),
  );
  const IndexValuationGroupTable = defineAsyncComponent(
    () => import('../../components/IndexValuationGroupTable.vue'),
  );

  const EquityObservatoryPanel = defineAsyncComponent(
    () => import('../../components/EquityObservatoryPanel.vue'),
  );
  const EquityThemePanel = defineAsyncComponent(
    () => import('../../components/EquityThemePanel.vue'),
  );
  const MarketMonitorPanel = defineAsyncComponent(() => import('./MarketMonitorPanel.vue'));
  const MarketContextPanel = defineAsyncComponent(() => import('./MarketContextPanel.vue'));
  defineProps<{ data: EquityObservatory | null; refreshKey: number }>();
  const tab = defineModel<string>({ required: true });
  const styleGroups = observationGroups.slice(1);
  const valuationSelection = shallowRef<{ index: string; metric?: string }>();
  function openValuation(index: string, metric?: string) {
    valuationSelection.value = { index, metric };
    tab.value = 'valuation';
  }
  function styleValuationData(charts: IndexValuationChart[]) {
    const asOf = charts.reduce((latest, chart) => {
      for (const metric of chart.metrics) {
        const day = metric.history.at(-1)?.date;
        if (day && day > latest) latest = day;
      }
      return latest;
    }, '');
    return { chartsById: new Map(charts.map((chart) => [chart.id, chart])), asOf };
  }
  const tabs = [
    { key: 'valuation', label: '大盘估值' },
    { key: 'breadth', label: '广度与拥挤度' },
    { key: 'style', label: '风格轮动' },
  ];
</script>
<style scoped src="./objectResearch.css"></style>

<style scoped>
  .index-panels {
    display: grid;
    min-width: 0;
    gap: 12px;
  }

  .style-card {
    container: style-panel / inline-size;
    padding: 14px;
  }

  :deep(.market-breadth-wide > .monitor.monitor--embedded) {
    margin: 0;
  }

  :deep(.market-breadth-grid > section .financing-chart) {
    margin: 0;
    padding: 14px;
  }

  :deep(.market-breadth-grid > section),
  :deep(.market-breadth-grid .financing-chart),
  :deep(.market-breadth-grid .data-scroll) {
    min-width: 0;
    max-width: 100%;
  }

  :deep(.market-breadth-grid .data-scroll) {
    overflow-x: auto;
  }

  :deep(.market-breadth-grid .financing-chart > header) {
    justify-content: flex-start;
    gap: 6px 10px;
  }

  :deep(.market-breadth-grid .financing-chart .ranges) {
    margin-left: auto;
  }

  :deep(.market-breadth-grid .chart-summary-line) {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 2px 14px;
    min-width: 0;
    padding: 3px 0;
    color: #526a82;
    font-variant-numeric: tabular-nums;
  }

  :deep(.market-breadth-grid .chart-summary-line > *) {
    white-space: nowrap;
  }

  :deep(.market-breadth-grid .chart-summary-line strong) {
    margin-left: 3px;
    color: #17324d;
    font-size: 13px;
  }

  :deep(.market-breadth-grid .chart-summary-line time) {
    color: #677e93;
  }
</style>
