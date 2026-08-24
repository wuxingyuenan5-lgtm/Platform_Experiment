import { computed, ref } from 'vue';

export type ManagementSection = 'pnl' | 'capital' | 'orders';

export interface StrategyManagementOverviewLike {
  deskKey: string;
  sortOrder: number;
}

export function normalizeManagementSection(value: unknown): ManagementSection {
  return value === 'capital' || value === 'orders' ? value : 'pnl';
}

export function resolveManagementDesk<T extends StrategyManagementOverviewLike>(
  requestedDesk: unknown,
  items: T[],
): string | null {
  const available = items.map((item) => item.deskKey);
  if (!available.length) return null;
  if (typeof requestedDesk === 'string' && available.includes(requestedDesk)) {
    return requestedDesk;
  }
  return available[0];
}

export function createStrategyManagementOverviewStore<T extends StrategyManagementOverviewLike>(
  loader: () => Promise<T[]>,
) {
  const items = ref<T[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function refresh() {
    loading.value = true;
    error.value = null;
    try {
      const next = await loader();
      items.value = [...next].sort((left, right) => left.sortOrder - right.sortOrder);
    } catch {
      items.value = [];
      error.value = '策略管理总览暂不可用';
    } finally {
      loading.value = false;
    }
  }

  const empty = computed(() => !loading.value && error.value === null && items.value.length === 0);
  const hasData = computed(() => !loading.value && error.value === null && items.value.length > 0);

  return {
    items,
    loading,
    error,
    empty,
    hasData,
    refresh,
  };
}
