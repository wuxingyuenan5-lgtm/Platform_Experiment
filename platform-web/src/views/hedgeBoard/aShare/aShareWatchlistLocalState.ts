export interface WatchlistItem {
  code: string;
  name: string;
  group: string;
}

const WATCHLIST_STORAGE_KEY = 'vg_a_share_watchlist_v1';
const WATCHLIST_DIRTY_STORAGE_KEY = 'vg_a_share_watchlist_dirty_v1';
const DEFAULT_WATCHLIST: WatchlistItem[] = [
  { code: '600519', name: '贵州茅台', group: '核心观察' },
  { code: '300750', name: '宁德时代', group: '核心观察' },
];

export function normalizeStockCode(value: string) {
  const compact = value.trim().toUpperCase().replace(/\s+/g, '');
  const match = compact.match(/^(?:(?:SH|SZ|BJ)[.:-]?)?(\d{6})(?:[.:-]?(?:SH|SZ|BJ))?$/);
  return match?.[1] || '';
}

function normalizeWatchlistItem(item: unknown): WatchlistItem | null {
  if (!item || typeof item !== 'object') return null;
  const record = item as Record<string, unknown>;
  const code = typeof record.code === 'string' ? normalizeStockCode(record.code) : '';
  if (!code) return null;
  const name = typeof record.name === 'string' ? record.name.trim() : '';
  const group = typeof record.group === 'string' ? record.group.trim() : '';
  return {
    code,
    name: name || code,
    group: group || '默认分组',
  };
}

export function normalizeWatchlistItems(payload: unknown): WatchlistItem[] {
  if (!Array.isArray(payload)) return [];
  const seen = new Set<string>();
  return payload.reduce<WatchlistItem[]>((items, candidate) => {
    const normalized = normalizeWatchlistItem(candidate);
    if (!normalized || seen.has(normalized.code)) return items;
    seen.add(normalized.code);
    items.push(normalized);
    return items;
  }, []);
}

export function readWatchlist(): WatchlistItem[] {
  if (typeof window === 'undefined') return [...DEFAULT_WATCHLIST];
  try {
    const stored = window.localStorage.getItem(WATCHLIST_STORAGE_KEY);
    if (stored === null) return [...DEFAULT_WATCHLIST];
    const payload = JSON.parse(stored);
    if (!Array.isArray(payload)) return [...DEFAULT_WATCHLIST];
    return normalizeWatchlistItems(payload);
  } catch {
    return [...DEFAULT_WATCHLIST];
  }
}

export function writeWatchlist(items: WatchlistItem[]) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(items));
  } catch {
    // Keep the in-memory watchlist usable when browser storage is unavailable.
  }
}

export function readWatchlistDirty() {
  if (typeof window === 'undefined') return false;
  return window.localStorage.getItem(WATCHLIST_DIRTY_STORAGE_KEY) === '1';
}

export function writeWatchlistDirty(value: boolean) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(WATCHLIST_DIRTY_STORAGE_KEY, value ? '1' : '0');
  } catch {
    // The account API remains the source of truth when browser storage is unavailable.
  }
}
