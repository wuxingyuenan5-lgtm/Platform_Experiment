import { researchRequest } from './hedgeResearch';

export interface WorkspaceCard {
  id: string;
  type: 'module' | 'chart';
  title: string;
  width: 1 | 2;
  path: string;
  seriesA: string;
  seriesB: string;
  transform: 'level' | 'index' | 'return';
  display?: 'chart' | 'table';
  start: string | null;
  end: string | null;
}
export interface CalendarEvent {
  id: string;
  date: string;
  precision: 'day' | 'around' | 'month';
  title: string;
  criterion: string;
  outcome: string;
  sourceUrl: string;
  status: 'watching' | 'confirmed' | 'cancelled';
}
export interface SeriesInfo {
  id: string;
  name: string;
  unit: string;
  frequency: string;
  group: string;
  asOf: string | null;
  source: string;
  sourceUrl: string;
}
export interface SeriesData extends SeriesInfo {
  observations: Array<{ date: string; value: number | string | null }>;
}
export const loadWorkspace = <T>(kind: 'cards' | 'events') =>
  researchRequest<{ items: T[]; rowVersion: number }>({
    method: 'GET',
    url: `/me/workspace/${kind}`,
  });
export const saveWorkspace = <T>(kind: 'cards' | 'events', items: T[], expectedVersion: number) =>
  researchRequest<{ items: T[]; rowVersion: number }>({
    method: 'PUT',
    url: `/me/workspace/${kind}`,
    data: { [kind]: items, expectedVersion },
  });
export const loadSeriesCatalog = () =>
  researchRequest<SeriesInfo[]>({ method: 'GET', url: '/research/chart-catalog' });
export const loadChartSeries = (id: string, signal?: AbortSignal) =>
  researchRequest<SeriesData>({
    method: 'GET',
    url: `/research/chart-series/${encodeURIComponent(id)}`,
    signal,
  });
