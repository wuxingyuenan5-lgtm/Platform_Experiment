import { researchRequest } from './hedgeResearch';

export interface EtfTurnoverSnapshot {
  data: Record<string, any> | null;
  sources: Record<
    string,
    { status?: string; retrievedAt?: string; sha256?: string; observationTime?: string }
  >;
}

export const getEtfTurnover = (signal: AbortSignal) =>
  researchRequest<EtfTurnoverSnapshot>({
    method: 'GET',
    url: '/research/a-share/etf-turnover',
    signal,
  });
