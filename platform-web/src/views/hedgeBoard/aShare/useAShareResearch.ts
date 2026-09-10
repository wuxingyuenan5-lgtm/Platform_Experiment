import { onMounted, ref, shallowRef } from 'vue';
import { getAShareDashboard, type AShareDashboardResponse } from '@/api/hedgeResearch';

export { normalizeStockCode } from './aShareWatchlistLocalState';
export type { WatchlistItem } from './aShareWatchlistLocalState';
export type WatchlistSyncState = 'local' | 'syncing' | 'synced' | 'offline';

export function useAShareResearch() {
  const dashboard = shallowRef<AShareDashboardResponse | null>(null);
  const dashboardLoading = ref(false);
  const dashboardError = ref('');
  let active: Promise<void> | null = null;
  function loadDashboard(): Promise<void> {
    if (active) return active;
    dashboardLoading.value = true;
    dashboardError.value = '';
    active = getAShareDashboard()
      .then((result) => {
        dashboard.value = result;
      })
      .catch((error) => {
        dashboardError.value = error instanceof Error ? error.message : 'A股数据加载失败，请重试';
      })
      .finally(() => {
        dashboardLoading.value = false;
        active = null;
      });
    return active;
  }
  onMounted(() => void loadDashboard());
  return { dashboard, dashboardLoading, dashboardError, loadDashboard };
}
