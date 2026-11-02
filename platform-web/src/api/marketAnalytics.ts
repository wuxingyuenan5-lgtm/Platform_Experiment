import { researchRequest } from './hedgeResearch';

export type Value = string | number | null;
export interface AnalyticsRow {
  date: string;
  [key: string]: string | number | boolean | null | undefined;
}
export interface HistoryRisk {
  status: string;
  name: string;
  unit: string;
  instrument: string;
  start: string | null;
  asOf: string | null;
  samples: number;
  invalid: number;
  gaps: number;
  sourceUrl: string;
  referenceUrl: string;
  instruments: Array<{ id: string; name: string }>;
  summary: { price: Value; drawdown: Value; maxDrawdown: Value; cagr: Value };
  history: AnalyticsRow[];
  annual: Array<AnalyticsRow & { year: number; partial: boolean; samples: number }>;
  episodes: Array<{
    peakDate: string;
    troughDate: string;
    depth: Value;
    recoveryDate: string | null;
    daysUnderwater: number;
  }>;
}
export interface LensCard {
  id: string;
  name: string;
  category: string;
  unit: string;
  value: Value;
  date: string | null;
  change: Value;
  previousDate: string | null;
  rank: Value;
  count: number;
  historyStart: string | null;
  sourceUrl: string | null;
  status: string;
  spark: Array<{ date: string; value: Value }>;
}
export interface LiquidityLens {
  status: string;
  asOf: string | null;
  latest: AnalyticsRow | null;
  change4w: {
    date: string | null;
    previousDate: string | null;
    fed: Value;
    tga: Value;
    rrp: Value;
    net: Value;
  };
  cards: LensCard[];
  history: AnalyticsRow[];
  structure: AnalyticsRow[];
  referenceUrl: string;
}
export const getHistoryRisk = (instrument: string, signal?: AbortSignal) =>
  researchRequest<HistoryRisk>({
    method: 'GET',
    url: `/research/equity/history-risk?instrument=${encodeURIComponent(instrument)}`,
    signal,
  });
export const getLiquidityLens = (signal?: AbortSignal) =>
  researchRequest<LiquidityLens>({ method: 'GET', url: '/research/macro/liquidity-lens', signal });
