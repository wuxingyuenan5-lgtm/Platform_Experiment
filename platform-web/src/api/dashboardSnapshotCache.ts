import type { MacroDashboardResponse } from './hedgeResearch';

const snapshots = new Map<
  string,
  { expiresAt: number; request: Promise<MacroDashboardResponse> }
>();
let sessionScope = '';

// A minute covers staggered lazy mounts without pinning a page to an old production run.
export function loadDashboardSnapshot(
  key: string,
  scope: string,
  load: () => Promise<MacroDashboardResponse>,
): Promise<MacroDashboardResponse> {
  if (scope !== sessionScope) {
    snapshots.clear();
    sessionScope = scope;
  }
  const existing = snapshots.get(key);
  if (existing && Date.now() < existing.expiresAt) return existing.request;
  const expiresAt = Date.now() + 60_000;
  const entry = {
    expiresAt: Infinity,
    request: undefined as unknown as Promise<MacroDashboardResponse>,
  };
  entry.request = load().then(
    (data) => {
      entry.expiresAt = expiresAt;
      return data;
    },
    (error) => {
      if (snapshots.get(key) === entry) snapshots.delete(key);
      throw error;
    },
  );
  snapshots.set(key, entry);
  return entry.request;
}
