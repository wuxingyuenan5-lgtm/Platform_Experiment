/** Shared pure-computation contracts for the cross-asset trend monitor. */
export type Bar = {
  t: number;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
  native?: {
    source: 'NashNova';
    macd?: { dif: number; dea: number; histogram: number };
    rsi?: number;
    estimatedAmount?: number;
  };
};
export type Frame = '1D' | '3D' | '1W' | 'M';
export interface ListingEvidence {
  firstTradingDate?: string;
  regularTradingDate?: string;
  note?: string;
  url?: string;
  evidence?: string;
  verifiedAt?: string;
  symbol?: string;
  listedAt?: string;
  delistedAt?: string | null;
  source?: string;
}
export interface SnapshotSeries {
  symbol: string;
  tv: string;
  frame: Frame;
  fetchedAt: string;
  bars: Bar[];
  hasMore: boolean;
  nextDateTo: string | null;
  issues: string[];
  hash: string;
  source?: string;
  evidence?: string;
  lastBarComplete?: boolean;
  aggregation?: string;
  listing?: ListingEvidence;
  boundaryEvidence?: string;
  shortResponse?: boolean;
  totalBars?: number;
  firstTime?: number;
  parentHistory?: { first: string; hasMore?: boolean };
  intraday?: { quoteAt: string; receivedAt: string; updateMode?: string };
  rolling?: {
    asOf: string;
    dailyAsOf: string;
    expectedThrough: string;
    expectedDailyAsOf?: string;
    missing: number;
    currentGap: boolean;
  };
}
export interface Snapshot {
  version: number;
  generatedAt: string;
  fingerprint?: string;
  series: SnapshotSeries[];
  rollingSeries?: SnapshotSeries[];
  marketSession?: { open: boolean; phase: string };
  intraday?: {
    marketOpen: boolean;
    covered: number;
    total: number;
    checkedAt?: string;
    error: string;
    maxAgeSeconds: number;
  };
}
export interface UniverseAsset {
  symbol: string;
  name: string;
  english?: string;
  kind: 'stock' | 'etf';
  pool?: 'core' | 'reserve';
  category: string;
  sector: string;
  tier?: string;
  tv?: string;
  cli?: string;
  price?: number | null;
  cap?: number | null;
  adv20?: number | null;
  adv60?: number | null;
  median20?: number | null;
  return20?: number | null;
  qualified?: boolean | null;
  profile?: string;
  drivers?: string;
  risks?: string;
  reason?: string;
  benchmark?: string;
  issuer?: string;
  structure?: string;
  sources?: string[];
  provider?: string;
  sessions?: number | null;
  sp500?: boolean;
  ndx?: boolean;
  curated?: boolean;
}
export type Security = UniverseAsset;
