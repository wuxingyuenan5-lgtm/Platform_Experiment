import { computed, ref } from 'vue';

import { getStrategyManagementOverview } from '@/api/platform/trading';
import type { StrategyManagementOverviewResult } from '@/api/platform/trading.types';
import type { StrategyDeskKey } from '@/data/sample/strategy';

export function useStrategyManagementOverview() {
  const items = ref<StrategyManagementOverviewResult[]>([]);

  async function refresh() {
    const next = await getStrategyManagementOverview();
    items.value = [...next].sort((left, right) => left.sortOrder - right.sortOrder);
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
    refresh,
  };
}
