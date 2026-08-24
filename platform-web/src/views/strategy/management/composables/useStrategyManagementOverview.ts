import { computed, ref } from 'vue';

import { getStrategyManagementOverview } from '@/api/platform/trading';
import type { StrategyManagementOverviewResult } from '@/api/platform/trading.types';
import type { StrategyDeskKey } from '@/data/sample/strategy';
import { createStrategyManagementOverviewStore } from './strategyManagementOverviewState';

export function useStrategyManagementOverview() {
  const store = createStrategyManagementOverviewStore<StrategyManagementOverviewResult>(
    getStrategyManagementOverview,
  );
  const items = ref<StrategyManagementOverviewResult[]>([]);

  async function refresh() {
    await store.refresh();
    items.value = store.items.value;
  }

  const byDesk = computed(
    () =>
      Object.fromEntries(items.value.map((item) => [item.deskKey, item])) as Partial<
        Record<StrategyDeskKey, StrategyManagementOverviewResult>
      >,
  );

  return {
    items,
    byDesk,
    loading: store.loading,
    error: store.error,
    empty: store.empty,
    hasData: store.hasData,
    refresh,
  };
}
