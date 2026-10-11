import { onActivated, onDeactivated, onMounted, onUnmounted } from 'vue';

// Shared API snapshots coalesce these callbacks into one request per domain.
export function useDashboardRefresh(load: () => Promise<void>): void {
  let timer: ReturnType<typeof setInterval> | undefined;
  let running = false;
  const refresh = async () => {
    if (running || document.visibilityState === 'hidden') return;
    running = true;
    try {
      await load();
    } finally {
      running = false;
    }
  };
  const start = () => {
    if (timer !== undefined) return;
    void refresh();
    timer = setInterval(() => void refresh(), 60_000);
    document.addEventListener('visibilitychange', refresh);
  };
  const stop = () => {
    clearInterval(timer);
    timer = undefined;
    document.removeEventListener('visibilitychange', refresh);
  };
  onMounted(start);
  onActivated(start);
  onDeactivated(stop);
  onUnmounted(stop);
}
