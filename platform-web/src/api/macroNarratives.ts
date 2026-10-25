import { researchRequest } from './hedgeResearch';

export interface NarrativePoint {
  date: string;
  score: number;
  momentum: number | null;
}
export interface NarrativeSource {
  id: string;
  label: string;
  direction: number;
  transform: string;
  source: string;
  url: string | null;
  date: string | null;
  status: string;
}
export interface NarrativeDriver {
  id: string;
  label: string;
  group: string;
  meaning: string;
  status: string;
  sources: NarrativeSource[];
  missing: string[];
  history: NarrativePoint[];
  date: string | null;
}
export interface StateEvidence {
  dimension: string;
  id: string | null;
  label: string | null;
  value: string | null;
  date: string | null;
  unit: string;
  delta: string | null;
  status: string;
  source: string;
  url: string | null;
}
export interface MacroNarratives {
  version: string;
  asOf: string | null;
  status: string;
  dates: string[];
  drivers: NarrativeDriver[];
  states: Array<{ market: string; evidence: StateEvidence[] }>;
}
export const getMacroNarratives = (signal?: AbortSignal) =>
  researchRequest<MacroNarratives>({
    method: 'GET',
    url: '/research/macro/narratives',
    signal,
  });
