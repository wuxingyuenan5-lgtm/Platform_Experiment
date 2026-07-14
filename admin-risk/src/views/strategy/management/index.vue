<template>
  <div class="strategy-management-page">
    <section class="top-toolbar">
      <div class="top-toolbar__left">
        <StrategyDeskTabs :tabs="deskTabs" v-model:activeKey="activeDesk" />
      </div>

      <div class="top-toolbar__meta">
        <CompactSegmentTabs :items="sectionTabs" v-model="activeSection" />
      </div>
    </section>

    <template v-if="activeSection === 'pnl'">
      <StrategyPnlPanel :active-desk="activeDesk" />
    </template>

    <template v-else-if="activeSection === 'capital'">
      <StrategyKpiGrid :items="capitalProfile.overview" />

      <StrategyCapitalFinanceBoard
        :risk-cards="capitalProfile.riskCards"
        :structure-cards="capitalProfile.structureCards"
      />

      <StrategyCapitalRulePanel
        v-if="capitalProfile.specialRulePanel"
        :panel="capitalProfile.specialRulePanel"
      />

      <StrategyCapitalRiskOverview
        v-if="capitalProfile.riskOverview"
        :overview="capitalProfile.riskOverview"
      />

      <StrategyRuntimePanel :cards="capitalProfile.comparisonCards" />

      <StrategyCapitalNetValueBoard :curve="capitalProfile.curve" />

      <StrategyCurveGrid
        v-if="capitalProfile.metricCurves?.length"
        :curves="capitalProfile.metricCurves"
      />
    </template>

    <template v-else>
      <section class="records-only-grid">
        <StrategyRecordsPanel
          :tabs="orderProfile.tabs"
          :tables="orderProfile.tables"
          v-model:activeTab="activeRecordTab"
        />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import CompactSegmentTabs from '../shared/CompactSegmentTabs.vue';
  import StrategyDeskTabs from './components/StrategyDeskTabs.vue';
  import StrategyKpiGrid from './components/StrategyKpiGrid.vue';
  import StrategyRuntimePanel from './components/StrategyRuntimePanel.vue';
  import StrategyCurveGrid from './components/StrategyCurveGrid.vue';
  import StrategyRecordsPanel from './components/StrategyRecordsPanel.vue';
  import StrategyCapitalFinanceBoard from './components/StrategyCapitalFinanceBoard.vue';
  import StrategyCapitalNetValueBoard from './components/StrategyCapitalNetValueBoard.vue';
  import StrategyCapitalRulePanel from './components/StrategyCapitalRulePanel.vue';
  import StrategyCapitalRiskOverview from './components/StrategyCapitalRiskOverview.vue';
  import StrategyPnlPanel from './components/StrategyPnlPanel.vue';
  import { strategyCapitalProfiles } from './mock/capital';
  import { strategyDeskOrder, strategyOrderProfiles } from './mock/orders';
  import type { StrategyDeskKey } from './types';

  const activeDesk = ref<StrategyDeskKey>('funding');
  const activeRecordTab = ref('positions');
  const activeSection = ref<'pnl' | 'capital' | 'orders'>('pnl');

  const deskTabs = strategyDeskOrder.map((key) => ({
    key,
    label: strategyOrderProfiles[key].label,
  }));

  const sectionTabs = [
    { key: 'pnl', label: '策略损益' },
    { key: 'capital', label: '账户资金' },
    { key: 'orders', label: '订单信息' },
  ];

  const orderProfile = computed(() => strategyOrderProfiles[activeDesk.value]);
  const capitalProfile = computed(() => strategyCapitalProfiles[activeDesk.value]);

  watch(
    () => activeDesk.value,
    () => {
      activeRecordTab.value = orderProfile.value.tabs[0]?.key || 'positions';
      activeSection.value = 'pnl';
    },
    { immediate: true },
  );
</script>

<style lang="less">
  @import '../shared/strategy-theme.less';
</style>

<style scoped lang="less">
  .strategy-management-page {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 6px 4px 0;
    background: var(--strategy-bg);
    color: var(--strategy-text-1);
  }

  .top-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 4px 2px 2px;
  }

  .top-toolbar__left {
    display: flex;
    align-items: center;
  }

  .top-toolbar__meta {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
  }

  .records-only-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
  }

  @media (max-width: 980px) {
    .top-toolbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .top-toolbar__meta {
      justify-content: flex-start;
    }
  }
</style>
