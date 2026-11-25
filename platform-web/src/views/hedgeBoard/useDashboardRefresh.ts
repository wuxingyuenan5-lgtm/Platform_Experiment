import { onActivated, onDeactivated, onMounted, onUnmounted } from 'vue';

interface RefreshOptions {
  intervalMs?: number;
  immediate?: boolean;
  enabled?: () => boolean;
}

// Shared API snapshots coalesce reads; timers exist only for active, visible pages.
export function useDashboardRefresh(
  load: () => Promise<void>,
  { intervalMs = 60_000, immediate = true, enabled = () => true }: RefreshOptions = {},
): void {
  let timer: ReturnType<typeof setInterval> | undefined;
  let running = false;
  let active = false;
  let initialized = false;
  let lastStarted = -Infinity;
  const refresh = async () => {
    if (
      !active ||
      running ||
      document.visibilityState === 'hidden' ||
      !enabled() ||
      Date.now() - lastStarted < intervalMs
    )
      return;
    lastStarted = Date.now();
    running = true;
    try {
      await load();
    } finally {
      running = false;
    }
  };
  const stopTimer = () => {
    clearInterval(timer);
    timer = undefined;
  };
  const visibilityChanged = () => {
    stopTimer();
    if (!active || document.visibilityState === 'hidden') return;
    void refresh();
    timer = setInterval(() => void refresh(), intervalMs);
  };
  const start = () => {
    if (active) return;
    active = true;
    if (!initialized && !immediate) lastStarted = Date.now();
    initialized = true;
    document.addEventListener('visibilitychange', visibilityChanged);
    visibilityChanged();
  };
  const stop = () => {
    active = false;
    stopTimer();
    document.removeEventListener('visibilitychange', visibilityChanged);
  };
  onMounted(start);
  onActivated(start);
  onDeactivated(stop);
  onUnmounted(stop);
}
