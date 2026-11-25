import type { Security } from './types';

export type { Bar, Frame, Snapshot, SnapshotSeries, Security, UniverseAsset } from './types';
export type AssetInfo = Pick<Security, 'symbol' | 'kind' | 'category' | 'structure'>;
export interface CapRow {
  symbol: string;
  value: number;
  currency: string;
  observedAt: string;
  date: string;
  source: string;
  field: string;
}
export interface CapSnapshot {
  date: string;
  dates: string[];
  rows: Record<string, CapRow>;
  total: number;
  method: string;
  checkedAt: string | null;
}
