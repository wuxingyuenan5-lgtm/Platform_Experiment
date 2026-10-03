import { computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';
import {
  strategyQueryClient,
  strategyQueryKey,
  strategySession,
} from '@/api/platform/strategyQueries';
import { getStrategyManagementOverview } from '@/api/platform/trading';
import type { StrategyManagementOverviewResult } from '@/api/platform/trading.types';
import type { StrategyDeskKey } from '@/data/sample/strategy';

export function useStrategyManagementOverview() {
  const query = useQuery(
    {
      queryKey: computed(() => strategyQueryKey('management-overview')),
      queryFn: ({ signal }) => getStrategyManagementOverview(signal),
      enabled: computed(() => !!strategySession.value.userId),
    },
    strategyQueryClient,
  );
  const items = computed(() =>
    [...(query.data.value ?? [])].sort((left, right) => left.sortOrder - right.sortOrder),
  );
  const error = computed(() =>
    query.isError.value && query.data.value === undefined ? '策略管理总览暂不可用' : null,
  );
  const refreshError = computed(() =>
    query.isError.value && query.data.value !== undefined
      ? '策略管理总览刷新失败，显示上次成功结果'
      : null,
  );
  const byDesk = computed(
    () =>
      Object.fromEntries(items.value.map((item) => [item.deskKey, item])) as Partial<
        Record<StrategyDeskKey, StrategyManagementOverviewResult>
      >,
  );
  return {
    items,
    byDesk,
    // Background refresh must not unmount the desk and reset its metric/calendar controls.
    loading: computed(() => query.isFetching.value && query.data.value === undefined),
    error,
    refreshError,
    empty: computed(() => !query.isFetching.value && !error.value && !items.value.length),
    hasData: computed(() => !query.isFetching.value && !error.value && !!items.value.length),
    refresh: () => query.refetch({ cancelRefetch: false }),
  };
}
