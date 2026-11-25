<template>
  <div class="research-page">
    <div v-if="needsDashboard && dashboardError" class="dashboard-error" role="alert">
      {{ dashboardError }}<button type="button" @click="refreshAll">重试</button>
    </div>
    <p v-if="needsDashboard && !dashboard && dashboardLoading" role="status"
      >正在读取{{ pageTitle }}…</p
    >
    <template v-if="activePage === 'overview'">
      <AShareMarketOverviewSection
        :dashboard="dashboard"
        :refresh-key="refreshKey"
        @query="emit('query', $event)"
        @ready="ready"
      >
        <AShareLegacyTerminalSection :dashboard="dashboard" view="details" />
      </AShareMarketOverviewSection>
    </template>
    <ThemeValuationCrowdingPanel
      v-else-if="activePage === 'themes'"
      :refresh-key="refreshKey"
      @ready="ready"
    />
    <TimingRadarPanel
      v-else-if="activePage === 'timing-radar'"
      :refresh-key="refreshKey"
      @ready="ready"
    />
    <VibeStockPoolSection
      v-else-if="activePage === 'stocks'"
      :refresh-key="refreshKey"
      @query="emit('query', $event)"
      @ready="ready"
    />
    <CapitalPanel v-else-if="activePage === 'capital'" :refresh-key="refreshKey" @ready="ready" />
    <DomesticFinancingPanel
      v-else-if="activePage === 'derivatives'"
      mode="derivatives"
      :refresh-key="refreshKey"
      @ready="ready"
    />
    <EquityObservatoryPanel
      v-else
      market="cn"
      :view="activePage"
      :refresh-key="refreshKey"
      @ready="ready"
    />
    <template v-if="!pageLoading">
      <VisibleChart v-if="activePage === 'overview'" :height="600"
        ><MarketSeasonalityPanel market="cn"
      /></VisibleChart>
    </template>
  </div>
</template>
<script setup lang="ts">
  import { computed, defineAsyncComponent, onActivated, onDeactivated, ref, watch } from 'vue';
  import type { AShareDashboardResponse } from '@/api/hedgeResearch';
  import VisibleChart from '../components/VisibleChart';

  const AShareLegacyTerminalSection = defineAsyncComponent(
    () => import('./components/AShareLegacyTerminalSection.vue'),
  );
  const ThemeValuationCrowdingPanel = defineAsyncComponent(
    () => import('./components/ThemeValuationCrowdingPanel.vue'),
  );
  const TimingRadarPanel = defineAsyncComponent(() => import('./components/TimingRadarPanel.vue'));
  const AShareMarketOverviewSection = defineAsyncComponent(
    () => import('./components/AShareMarketOverviewParitySection.vue'),
  );
  const VibeStockPoolSection = defineAsyncComponent(
    () => import('./components/VibeStockPoolSection.vue'),
  );
  const EquityObservatoryPanel = defineAsyncComponent(
    () => import('../components/EquityObservatoryPanel.vue'),
  );
  const CapitalPanel = defineAsyncComponent(() => import('./components/CapitalPanel.vue'));
  const DomesticFinancingPanel = defineAsyncComponent(
    () => import('./components/DomesticFinancingPanel.vue'),
  );
  const MarketSeasonalityPanel = defineAsyncComponent(
    () => import('../components/MarketSeasonalityPanel.vue'),
  );
  const props = defineProps<{
    page: string;
    title: string;
    dashboard: AShareDashboardResponse | null;
    dashboardError: string;
    dashboardLoading: boolean;
    refreshKey: number;
  }>();
  const emit = defineEmits<{
    ready: [page: string, readAt: number];
    query: [code: string];
    refresh: [];
  }>();
  const activePage = computed(() => props.page);
  const needsDashboard = computed(() => props.page === 'overview');
  const pageTitle = computed(() => props.title);
  const pageLoading = ref(true);
  const active = ref(true);
  let readAt = 0;
  function ready() {
    pageLoading.value = false;
    readAt = Date.now();
    if (active.value) emit('ready', props.page, readAt);
  }
  function refreshAll() {
    emit('refresh');
  }
  watch(
    () => props.dashboardLoading,
    (loading) => {
      if (props.page === 'overview' && !loading) ready();
    },
  );
  onDeactivated(() => {
    active.value = false;
  });
  onActivated(() => {
    active.value = true;
    if (!pageLoading.value) emit('ready', props.page, readAt);
  });
</script>
<style scoped>
  .dashboard-error {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 16px;
    border: 1px solid #f5d6b5;
    border-radius: 8px;
    background: #fff8ed;
    color: #8f5517;
  }

  .dashboard-error button {
    border: 0;
    background: transparent;
    color: inherit;
    cursor: pointer;
  }
</style>
