import { researchRequest } from './hedgeResearch';
import { getUserSystemCsrfToken } from './platform/userSystem';

export interface ObservationSummary {
  date: string | null;
  basketCount: number;
  coveredCount?: number;
  partialDates?: string[];
  flow1Yi: string | null;
  flow5Yi: string | null;
  flow20Yi: string | null;
  scaleYi: string | null;
  sharesYi: string | null;
  baseline?: {
    asof: string;
    source: string;
    note: string;
    total_value_yi: number | null;
    holders: {
      name: string;
      etf_count: number | null;
      shares_yi: number | null;
      value_yi: number | null;
      avg_pct: number | null;
    }[];
  } | null;
  baselineStatus?: string;
  futures: {
    date: string | null;
    member: string;
    netShortChange: string | null;
    status: string;
    sourceUrl?: string;
  };
}

export interface ObservationSnapshot {
  summary?: ObservationSummary;
  intradaySummary?: ObservationSummary;
  reference: Record<string, any>;
  live: { klines?: Record<string, any[]>; hq?: { data?: { diff?: any[] } } };
  sources: Record<
    string,
    {
      status: string;
      retrievedAt: string;
      sha256?: string;
      observationDate?: string;
      observationTime?: string;
      sourceLabel?: string;
      errorDetail?: string;
    }
  >;
}
let cached: { scope: string; expires: number; request: Promise<ObservationSnapshot> } | undefined;
export function getEtfObservation() {
  const scope = getUserSystemCsrfToken();
  if (cached?.scope === scope && Date.now() < cached.expires) return cached.request;
  const entry = {
    scope,
    expires: Infinity,
    request: undefined as unknown as Promise<ObservationSnapshot>,
  };
  entry.request = researchRequest<ObservationSnapshot>({
    method: 'GET',
    url: '/research/a-share/etf-observation',
  }).then(
    (data) => {
      entry.expires = Date.now() + 1000;
      return data;
    },
    (error) => {
      if (cached === entry) cached = undefined;
      throw error;
    },
  );
  cached = entry;
  return entry.request;
}
