const snapshots = new Map<string, { expiresAt: number; request: Promise<unknown> }>();
let sessionScope = '';

// A minute covers staggered lazy mounts without pinning a page to an old production run.
export function loadDashboardSnapshot<T>(
  key: string,
  scope: string,
  load: () => Promise<T>,
): Promise<T> {
  if (scope !== sessionScope) {
    snapshots.clear();
    sessionScope = scope;
  }
  const existing = snapshots.get(key);
  if (existing && Date.now() < existing.expiresAt) return existing.request as Promise<T>;
  const expiresAt = Date.now() + 60_000;
  const entry = {
    expiresAt: Infinity,
    request: undefined as unknown as Promise<T>,
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
