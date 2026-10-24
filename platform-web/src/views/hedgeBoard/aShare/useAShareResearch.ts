import { onBeforeUnmount, ref, shallowRef, watch, type Ref } from 'vue';
import { getAShareDashboard, type AShareDashboardResponse } from '@/api/hedgeResearch';

export { normalizeStockCode } from './aShareWatchlistLocalState';
export type { WatchlistItem } from './aShareWatchlistLocalState';
export type WatchlistSyncState = 'local' | 'syncing' | 'synced' | 'offline';

export function useAShareResearch(enabled: Ref<boolean>) {
  const dashboard = shallowRef<AShareDashboardResponse | null>(null);
  const dashboardLoading = ref(false);
  const dashboardError = ref('');
  let fetchedAt = 0;
  let controller: AbortController | undefined;
  let disposed = false;
  let active: Promise<void> | null = null;
  function loadDashboard(): Promise<void> {
    if (active) {
      if (controller?.signal.aborted)
        return active.then(() => {
          if (enabled.value && !disposed) return loadDashboard();
        });
      return active;
    }
    const requestController = (controller = new AbortController());
    dashboardLoading.value = true;
    dashboardError.value = '';
    active = getAShareDashboard(requestController.signal)
      .then((result) => {
        if (requestController.signal.aborted) return;
        dashboard.value = result;
        fetchedAt = Date.now();
      })
      .catch((error) => {
        if (requestController.signal.aborted) return;
        dashboardError.value = error instanceof Error ? error.message : 'A股数据加载失败，请重试';
      })
      .finally(() => {
        dashboardLoading.value = false;
        active = null;
      });
    return active;
  }
  function ensureDashboard() {
    if (enabled.value && Date.now() - fetchedAt > 60_000) return loadDashboard();
  }
  watch(
    enabled,
    (value) => {
      if (value) void ensureDashboard();
      else if (!value) controller?.abort();
    },
    { immediate: true },
  );
  onBeforeUnmount(() => {
    disposed = true;
    controller?.abort();
  });
  return { dashboard, dashboardLoading, dashboardError, loadDashboard, ensureDashboard };
}
