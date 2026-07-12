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
      <DomesticOverseasOrdersAddon v-if="activeDesk === 'domesticOverseas'" />

      <StrategyOverviewBoard
        :overview="profile.overview"
        v-model:activePeriod="activePeriod"
      />

      <StrategyDetailPanel :detail="profile.detail" />

      <StrategyCurveGrid :curves="profile.curves" />

      <DomesticOverseasPnlAddon v-if="activeDesk === 'domesticOverseas'" />
    </template>

    <template v-else-if="activeSection === 'capital'">
      <StrategyKpiGrid :items="profile.kpis" />

      <StrategyCapitalFinanceBoard />

      <StrategyRuntimePanel
        :strategy-name="profile.strategyName"
        :gauges="profile.gauges"
        :breakdown="profile.accountBreakdown"
      />

      <StrategyCapitalNetValueBoard />

      <DomesticOverseasCapitalAddon v-if="activeDesk === 'domesticOverseas'" />
    </template>

    <template v-else>
      <section class="records-only-grid">
        <StrategyRecordsPanel
          :tabs="profile.tabs"
          :tables="profile.tables"
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
  import StrategyOverviewBoard from './components/StrategyOverviewBoard.vue';
  import StrategyDetailPanel from './components/StrategyDetailPanel.vue';
  import StrategyKpiGrid from './components/StrategyKpiGrid.vue';
  import StrategyRuntimePanel from './components/StrategyRuntimePanel.vue';
  import StrategyCurveGrid from './components/StrategyCurveGrid.vue';
  import StrategyRecordsPanel from './components/StrategyRecordsPanel.vue';
  import StrategyCapitalFinanceBoard from './components/StrategyCapitalFinanceBoard.vue';
  import StrategyCapitalNetValueBoard from './components/StrategyCapitalNetValueBoard.vue';
  import DomesticOverseasPnlAddon from './components/DomesticOverseasPnlAddon.vue';
  import DomesticOverseasCapitalAddon from './components/DomesticOverseasCapitalAddon.vue';
  import { strategyDeskOrder, strategyDeskProfiles } from './mock/data';
  import type { StrategyDeskKey, StrategyPeriodKey } from './types';

  const activeDesk = ref<StrategyDeskKey>('funding');
  const activePeriod = ref<StrategyPeriodKey>('week');
  const activeRecordTab = ref('positions');
  const activeSection = ref<'pnl' | 'capital' | 'orders'>('pnl');

  const deskTabs = strategyDeskOrder.map((key) => ({
    key,
    label: strategyDeskProfiles[key].label,
  }));

  const sectionTabs = [
    { key: 'pnl', label: '策略损益' },
    { key: 'capital', label: '账户资金' },
    { key: 'orders', label: '订单信息' },
  ];

  const profile = computed(() => strategyDeskProfiles[activeDesk.value]);

  watch(
    () => activeDesk.value,
    () => {
      activeRecordTab.value = profile.value.tabs[0]?.key || 'positions';
      activePeriod.value = 'week';
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
