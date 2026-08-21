<template>
  <div class="strategy-management-page" data-testid="strategy-management-original-structure">
    <section class="strategy-top-toolbar">
      <div class="strategy-top-toolbar__left">
        <CompactSegmentTabs :items="deskTabs" v-model="activeDesk" />
      </div>

      <div class="strategy-top-toolbar__meta">
        <CompactSegmentTabs :items="sectionTabs" v-model="activeSection" />
      </div>
    </section>

    <template v-if="activeSection === 'pnl'">
      <StrategyPnlPanel :active-desk="activeDesk" :live-profile="activePnlProfile" />
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
  import { computed, onMounted, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  import CompactSegmentTabs from '../shared/CompactSegmentTabs.vue';
  import { useCrossSpreadFinance } from './composables/useCrossSpreadFinance';
  import { useCrossSpreadRecords } from './composables/useCrossSpreadRecords';
  import { useStrategyAccountSnapshots } from './composables/useStrategyAccountSnapshots';
  import StrategyKpiGrid from './components/StrategyKpiGrid.vue';
  import StrategyRuntimePanel from './components/StrategyRuntimePanel.vue';
  import StrategyCurveGrid from './components/StrategyCurveGrid.vue';
  import StrategyRecordsPanel from './components/StrategyRecordsPanel.vue';
  import StrategyCapitalFinanceBoard from './components/StrategyCapitalFinanceBoard.vue';
  import StrategyCapitalNetValueBoard from './components/StrategyCapitalNetValueBoard.vue';
  import StrategyCapitalRulePanel from './components/StrategyCapitalRulePanel.vue';
  import StrategyCapitalRiskOverview from './components/StrategyCapitalRiskOverview.vue';
  import StrategyPnlPanel from './components/StrategyPnlPanel.vue';
  import {
    strategyCapitalProfiles,
    strategyDeskOrder,
    strategyOrderProfiles,
    type StrategyDeskKey,
  } from '@/data/sample/strategy';

  const route = useRoute();
  const activeDesk = ref<StrategyDeskKey>(
    route.query.desk === 'crossSpread' ? 'crossSpread' : 'funding',
  );
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

  const {
    tabs: liveCrossSpreadTabs,
    tables: liveCrossSpreadTables,
    refresh: refreshCrossSpreadRecords,
  } = useCrossSpreadRecords();

  const {
    pnlProfile,
    refresh: refreshCrossSpreadFinance,
    liveCapitalProfile,
  } = useCrossSpreadFinance();

  const {
    capitalProfiles: accountCapitalProfiles,
    isAccountStrategy,
    orderProfiles: accountOrderProfiles,
    pnlProfiles: accountPnlProfiles,
    refresh: refreshAccountSnapshots,
  } = useStrategyAccountSnapshots();

  const activePnlProfile = computed(() => {
    if (activeDesk.value === 'crossSpread') return pnlProfile.value;
    return isAccountStrategy(activeDesk.value) ? accountPnlProfiles.value[activeDesk.value] : null;
  });

  const orderProfile = computed(() => {
    if (activeDesk.value === 'crossSpread') {
      return {
        label: strategyOrderProfiles.crossSpread.label,
        tabs: liveCrossSpreadTabs,
        tables: liveCrossSpreadTables.value,
      };
    }
    if (isAccountStrategy(activeDesk.value)) {
      return accountOrderProfiles.value[activeDesk.value];
    }
    return strategyOrderProfiles[activeDesk.value];
  });
  const capitalProfile = computed(() => {
    const base = strategyCapitalProfiles[activeDesk.value];
    if (activeDesk.value === 'crossSpread') return liveCapitalProfile.value;
    return isAccountStrategy(activeDesk.value)
      ? accountCapitalProfiles.value[activeDesk.value]
      : base;
  });

  onMounted(() => {
    void refreshCrossSpreadRecords();
    void refreshCrossSpreadFinance();
    void refreshAccountSnapshots();
  });

  watch(
    () => activeDesk.value,
    () => {
      if (activeDesk.value === 'crossSpread') {
        void refreshCrossSpreadRecords();
        void refreshCrossSpreadFinance();
      }
      if (isAccountStrategy(activeDesk.value)) {
        void refreshAccountSnapshots(activeDesk.value);
      }
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

  .records-only-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
  }
</style>
