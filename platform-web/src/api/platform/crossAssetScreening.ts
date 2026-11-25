import { researchRequest } from '../hedgeResearch';
import type {
  Bar,
  CapSnapshot,
  Frame,
  Security,
  Snapshot,
} from '@/views/hedgeBoard/macro/crossAsset/model';
import type { ResearchReport } from '@/views/hedgeBoard/macro/crossAsset/rules';
import type { WorkbookSnapshot } from '@/views/hedgeBoard/macro/crossAsset/workbookSnapshot';

export interface CrossAssetScreeningResponse {
  snapshot: Snapshot;
  assets: Security[];
  caps: CapSnapshot;
  calendar: number[];
  legacyResearch: ResearchReport;
  sourceRevision: string;
  sourceDate: string;
  source: string;
  mode: string;
  isStale: boolean;
  workbookSnapshot?: WorkbookSnapshot;
  workbookSnapshotUnavailable?: boolean;
}
export interface Watchlist {
  id: string;
  name: string;
  symbols: string[];
}
export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export interface BrowserState {
  watchlists: Watchlist[];
  activeWatchlist: string | null;
  filters?: Json;
  [key: string]: unknown;
}
export interface ValidatedBackup {
  snapshot: Snapshot;
  caps: CapSnapshot;
  watchlists: Watchlist[];
  activeWatchlist: string;
  preferences: Record<string, unknown>;
}
export type ScreeningArchive = CrossAssetScreeningResponse;

const FRAMES = new Set<Frame>(['1D', '3D', '1W', 'M']);
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const ISO_SECONDS = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:?\d{2})$/;
function error(message: string): never {
  throw new TypeError(`Invalid cross-asset data: ${message}`);
}
const object = (v: unknown): Record<string, unknown> =>
  v !== null && typeof v === 'object' && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : error('expected object');
const array = (v: unknown, label: string): unknown[] =>
  Array.isArray(v) ? v : error(`${label} must be an array`);
const date = (v: unknown, label: string): string => {
  if (typeof v !== 'string' || !DATE.test(v)) error(`${label} must be YYYY-MM-DD`);
  const d = new Date(`${v}T00:00:00Z`);
  if (d.toISOString().slice(0, 10) !== v) error(`${label} is not a calendar date`);
  return v as string;
};
const timestamp = (v: unknown, label: string): number => {
  if (typeof v !== 'number' || !Number.isSafeInteger(v) || v <= 0 || v >= 10_000_000_000)
    error(`${label} must be a Unix timestamp in seconds`);
  return v as number;
};
const isoSeconds = (v: unknown, label: string): string => {
  if (typeof v !== 'string' || !ISO_SECONDS.test(v) || Number.isNaN(Date.parse(v)))
    error(`${label} must be an ISO timestamp`);
  return v as string;
};
const finite = (v: unknown, label: string): number => {
  if (typeof v !== 'number' || !Number.isFinite(v)) error(`${label} must be finite`);
  return v as number;
};
const observed = (v: unknown, label: string): string => {
  if (typeof v === 'string' && DATE.test(v)) return date(v, label);
  return isoSeconds(v, label);
};
const symbols = (allowed: string[]): Set<string> =>
  new Set(allowed.filter((s) => typeof s === 'string' && s.length > 0));

function bar(input: unknown, i: number): Bar {
  const v = object(input);
  const t = timestamp(v.t, `bars[${i}].t`);
  const o = finite(v.o, `bars[${i}].o`),
    h = finite(v.h, `bars[${i}].h`),
    l = finite(v.l, `bars[${i}].l`),
    c = finite(v.c, `bars[${i}].c`),
    volume = finite(v.v, `bars[${i}].v`);
  if (
    [o, h, l, c].some((n) => n <= 0) ||
    h < Math.max(o, c) ||
    l > Math.min(o, c) ||
    h < l ||
    volume < 0
  )
    error(`invalid OHLCV at ${i}`);
  let native: Bar['native'];
  if ('native' in v && v.native !== undefined) {
    const n = object(v.native);
    if (n.source !== 'NashNova') error(`bars[${i}].native source`);
    native = { source: 'NashNova' };
    if (n.macd !== undefined) {
      const m = object(n.macd);
      const dif = finite(m.dif, 'native.macd.dif'),
        dea = finite(m.dea, 'native.macd.dea'),
        histogram = finite(m.histogram, 'native.macd.histogram');
      if (Math.abs(dif - dea - histogram) > 0.003) error('native MACD histogram mismatch');
      native.macd = { dif, dea, histogram };
    }
    if (n.rsi !== undefined) {
      const rsi = finite(n.rsi, 'native.rsi');
      if (rsi < 0 || rsi > 100) error('native RSI range');
      native.rsi = rsi;
    }
    if (n.estimatedAmount !== undefined) {
      const amount = finite(n.estimatedAmount, 'native.estimatedAmount');
      if (amount < 0) error('native estimatedAmount');
      native.estimatedAmount = amount;
    }
  }
  const { native: _native, ...withoutNative } = v;
  return { ...withoutNative, t, o, h, l, c, v: volume, ...(native ? { native } : {}) } as Bar;
}

export function validateSnapshot(input: unknown, allowedSymbols: string[]): Snapshot {
  const root = object(input);
  if (root.version !== 1) error('snapshot.version');
  isoSeconds(root.generatedAt, 'snapshot.generatedAt');
  if (!Array.isArray(root.series) || root.series.length < 1 || root.series.length > 48)
    error('snapshot.series');
  const allowed = symbols(allowedSymbols);
  const series = array(root.series, 'snapshot.series').map((raw, si) => {
    const v = object(raw);
    if (typeof v.symbol !== 'string' || !allowed.has(v.symbol)) error(`series[${si}].symbol`);
    if (typeof v.tv !== 'string' || !v.tv) error(`series[${si}].tv`);
    if (!FRAMES.has(v.frame as Frame)) error(`series[${si}].frame`);
    isoSeconds(v.fetchedAt, `series[${si}].fetchedAt`);
    if (typeof v.hash !== 'string' || !v.hash) error(`series[${si}].hash`);
    if (!Array.isArray(v.bars) || v.bars.length < 1 || v.bars.length > 20_000)
      error(`series[${si}].bars`);
    const bars = array(v.bars, `series[${si}].bars`).map(bar);
    if (Date.parse(v.fetchedAt as string) > Date.parse(root.generatedAt as string))
      error(`series[${si}] fetchedAt is after snapshot.generatedAt`);
    if (bars.some((b) => b.t * 1000 > Date.parse(v.fetchedAt as string)))
      error(`series[${si}] bar time is after fetchedAt`);
    for (let i = 1; i < bars.length; i++)
      if (bars[i].t <= bars[i - 1].t) error(`series[${si}] bars must be strictly ordered`);
    if ('lastBarComplete' in v && typeof v.lastBarComplete !== 'boolean')
      error(`series[${si}].lastBarComplete`);
    for (const field of ['issues', 'source', 'evidence'] as const) {
      if (
        field in v &&
        field === 'issues' &&
        (!Array.isArray(v[field]) ||
          array(v[field], 'issues').some((item) => typeof item !== 'string'))
      )
        error(`series[${si}].issues`);
      if (
        field in v &&
        field !== 'issues' &&
        v[field] !== undefined &&
        typeof v[field] !== 'string'
      )
        error(`series[${si}].${field}`);
    }
    return { ...v, bars, intraday: undefined, rolling: undefined } as Snapshot['series'][number];
  });
  const identities = new Set(series.map((s) => `${s.symbol}\u0000${s.frame}`));
  if (identities.size !== series.length) error('duplicate symbol/frame series');
  const cleaned = { ...root, series, rollingSeries: undefined, intraday: undefined } as Snapshot;
  return deepCopy(cleaned);
}

export function validateCaps(input: unknown, allowedStockSymbols: string[]): CapSnapshot {
  const root = object(input);
  const capDate = date(root.date, 'caps.date');
  const rawDates = Array.isArray(root.dates) ? root.dates : [capDate];
  const dates = array(rawDates, 'caps.dates').map((v, i) => date(v, `caps.dates[${i}]`));
  if (new Set(dates).size !== dates.length) error('duplicate cap dates');
  const allowed = symbols(allowedStockSymbols);
  const rowsIn = object(root.rows);
  const rows: Record<string, CapSnapshot['rows'][string]> = {};
  for (const [symbol, raw] of Object.entries(rowsIn)) {
    if (!allowed.has(symbol)) error(`caps.rows.${symbol}`);
    const v = object(raw);
    if (v.symbol !== symbol) error(`${symbol}.symbol mismatch`);
    if (v.currency !== 'USD') error(`${symbol}.currency`);
    const value = finite(v.value, `${symbol}.value`);
    if (value <= 0) error(`${symbol}.value`);
    rows[symbol] = {
      ...v,
      symbol,
      value,
      currency: 'USD',
      observedAt: observed(v.observedAt, `${symbol}.observedAt`),
      date: date(v.date, `${symbol}.date`),
      source:
        typeof v.source === 'string' && v.source.length > 0 ? v.source : error(`${symbol}.source`),
      field: typeof v.field === 'string' && v.field.length > 0 ? v.field : error(`${symbol}.field`),
    } as CapSnapshot['rows'][string];
  }
  if (
    typeof root.total !== 'number' ||
    !Number.isFinite(root.total) ||
    root.total < 0 ||
    typeof root.method !== 'string'
  )
    error('caps totals');
  if (root.checkedAt !== null && root.checkedAt !== undefined)
    isoSeconds(root.checkedAt, 'caps.checkedAt');
  return deepCopy({
    ...root,
    date: capDate,
    dates,
    rows,
    total: root.total,
    method: root.method,
    checkedAt: root.checkedAt ?? null,
  } as CapSnapshot);
}

export function validateWatchlists(input: unknown, allowedSymbols: string[]): Watchlist[] {
  if (
    !Array.isArray(input) ||
    input.length > 101 ||
    input.filter((value) => value?.id !== 'favorites').length > 100
  )
    error('watchlists');
  const allowed = symbols(allowedSymbols);
  const ids = new Set<string>(),
    names = new Set<string>();
  return input.map((raw, i) => {
    const v = object(raw);
    const rawMembers = v.symbols ?? v.members;
    if (
      typeof v.id !== 'string' ||
      !v.id ||
      ids.has(v.id) ||
      typeof v.name !== 'string' ||
      !v.name.trim() ||
      v.name.length > 40 ||
      names.has(v.name.toLocaleLowerCase()) ||
      !Array.isArray(rawMembers)
    )
      error(`watchlists[${i}]`);
    ids.add(v.id);
    names.add(v.name.toLocaleLowerCase());
    const members = array(rawMembers, `watchlists[${i}].symbols`).map((entry: unknown) => {
      const s = typeof entry === 'string' ? entry : object(entry).symbol;
      if (typeof s !== 'string' || !allowed.has(s)) error(`watchlists[${i}] symbol`);
      return s;
    });
    if (new Set(members).size !== members.length) error(`watchlists[${i}] duplicate symbol`);
    return { id: v.id, name: v.name, symbols: members };
  });
}

export function validateBackup(value: unknown, assets: Security[]): ValidatedBackup {
  let root: unknown = value;
  if (typeof root === 'string') {
    try {
      root = JSON.parse(root);
    } catch {
      error('backup JSON');
    }
  }
  const v = object(root);
  if (
    v.version !== 1 ||
    (v.format !== 'wave-monitor-portable' && v.format !== 'global-variable-cross-asset')
  )
    error('unsupported backup format');
  const allowed = assets.map((a) => a.symbol);
  const snapshot = validateSnapshot(v.snapshot ?? v.archive, allowed);
  const stockSymbols = assets.filter((a) => a.kind === 'stock').map((a) => a.symbol);
  const caps = validateCaps(v.caps, stockSymbols);
  const state = v.format === 'wave-monitor-portable' ? object(v.state) : v;
  const rawLists = state.watchlists ?? [];
  let lists = validateWatchlists(rawLists, allowed);
  const favorites = state.favorites;
  if (Array.isArray(favorites) && !lists.some((x) => x.id === 'favorites')) {
    const favoriteName =
      typeof state.favoriteListName === 'string' && state.favoriteListName.trim()
        ? state.favoriteListName
        : '默认自选';
    lists = [
      ...lists,
      {
        id: 'favorites',
        name: favoriteName,
        symbols: validateWatchlists(
          [{ id: 'favorites', name: favoriteName, symbols: favorites }],
          allowed,
        )[0].symbols,
      },
    ];
  }
  lists = validateWatchlists(lists, allowed);
  const activeValue = state.activeWatchlist ?? state.activeWatchlistId ?? '';
  if (typeof activeValue !== 'string') error('activeWatchlist');
  if (activeValue !== '' && !lists.some((x) => x.id === activeValue))
    error('activeWatchlist missing');
  const prefs = decodePreferences(v.preferences);
  if (v.format === 'wave-monitor-portable' && state.holdings !== undefined)
    prefs.holdingSymbols = [
      ...new Set(
        array(state.holdings, 'holdings').map((row) => {
          const symbol = object(row).symbol;
          if (typeof symbol !== 'string' || !allowed.includes(symbol)) error('holdings symbol');
          return symbol;
        }),
      ),
    ];
  return {
    snapshot: deepCopy(snapshot),
    caps: deepCopy(caps),
    watchlists: deepCopy(lists),
    activeWatchlist: activeValue,
    preferences: deepCopy(prefs),
  };
}

function decodePreferences(value: unknown): Record<string, unknown> {
  if (value === undefined || value === null) return {};
  let parsed: unknown = value;
  if (typeof value === 'string') {
    try {
      parsed = JSON.parse(value);
    } catch {
      error('preferences JSON');
    }
  }
  const source = object(parsed);
  if (!Object.keys(source).some((key) => key.startsWith('wave-monitor-portable:'))) return source;
  const result: Record<string, unknown> = {};
  for (const [key, raw] of Object.entries(source)) {
    if (typeof raw !== 'string') continue;
    let item: unknown;
    try {
      item = JSON.parse(raw);
    } catch {
      continue;
    }
    if (key.includes('monitor-filters')) {
      const filter = object(item);
      result.filters = filter.filters ?? filter;
      result.sort = filter.sort;
    } else if (key.includes('monitor-assets')) result.assetScreen = item;
    else if (key.includes('monitor-presets')) result.presets = item;
    else if (key.includes('monitor:')) result.chart = item;
  }
  return result;
}

function deepCopy<T>(value: T): T {
  if (typeof structuredClone === 'function') return structuredClone(value);
  return JSON.parse(JSON.stringify(value)) as T;
}

export function getCrossAssetScreening(signal?: AbortSignal) {
  return researchRequest<CrossAssetScreeningResponse>({
    method: 'GET',
    url: '/research/macro/cross-asset-screening',
    signal,
  });
}

const DB = 'global-variable-cross-asset';
const STORE = 'market-data';
function openDb(): Promise<IDBDatabase> {
  if (typeof indexedDB === 'undefined') return Promise.reject(new Error('IndexedDB unavailable'));
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error || new Error('IndexedDB open failed'));
  });
}
export async function persistScreeningData(
  account: string,
  snapshot: Snapshot,
  caps: CapSnapshot,
): Promise<void> {
  if (!account) throw new Error('account is required');
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put({ snapshot, caps }, account);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error('IndexedDB write failed'));
      tx.onabort = () => reject(tx.error || new Error('IndexedDB write aborted'));
    });
  } finally {
    db.close();
  }
}
export async function readScreeningData(
  account: string,
): Promise<{ snapshot: Snapshot; caps: CapSnapshot } | null> {
  if (!account) throw new Error('account is required');
  const db = await openDb();
  try {
    return await new Promise((resolve, reject) => {
      const req = db.transaction(STORE, 'readonly').objectStore(STORE).get(account);
      req.onsuccess = () => resolve(req.result ?? null);
      req.onerror = () => reject(req.error || new Error('IndexedDB read failed'));
    });
  } finally {
    db.close();
  }
}
