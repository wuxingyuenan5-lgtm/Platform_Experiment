import { researchRequest } from './hedgeResearch';
import { getUserSystemCsrfToken } from './platform/userSystem';

export interface ObservationSnapshot {
  reference: Record<string, any>;
  live: { klines?: Record<string, any[]>; hq?: { data?: { diff?: any[] } } };
  sources: Record<string, { status: string; retrievedAt: string; observationDate?: string }>;
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
