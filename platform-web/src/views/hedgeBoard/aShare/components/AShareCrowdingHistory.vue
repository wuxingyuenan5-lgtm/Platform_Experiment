<template>
  <p v-if="dashboardError" role="alert">{{ dashboardError }}</p>
  <AShareMarketOverviewParitySection v-else mode="crowding" :dashboard="dashboard" />
</template>
<script setup lang="ts">
  import { computed, watch } from 'vue';
  import { useAShareResearch } from '../useAShareResearch';
  import AShareMarketOverviewParitySection from './AShareMarketOverviewParitySection.vue';

  const props = defineProps<{ refreshKey?: number }>();
  const { dashboard, dashboardError, loadDashboard } = useAShareResearch(computed(() => true));
  watch(
    () => props.refreshKey,
    () => void loadDashboard(),
  );
</script>
