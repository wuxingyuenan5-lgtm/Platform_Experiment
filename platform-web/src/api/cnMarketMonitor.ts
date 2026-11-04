import { researchRequest } from './hedgeResearch';

export type MonitorValue = string | number | null;
export interface MonitorRow {
  date: string;
  [key: string]: MonitorValue | undefined;
}
export interface MonitorItem {
  code: string;
  name: string;
  history?: MonitorRow[];
  date?: string;
  previousDate?: string;
  value?: MonitorValue;
  previous?: MonitorValue;
  change?: MonitorValue;
}
export interface MonitorSource {
  status: string;
  sourceUrl: string;
  fetchedAt?: string;
  data?: MonitorRow[] | MonitorItem[];
}
export interface MarketMonitor {
  generatedAt: string | null;
  sources: Record<string, MonitorSource>;
}
export type MarketContextSection = 'risk' | 'breadth' | 'macroValue';
export const getMarketContext = (
  section: MarketContextSection | 'valuation',
  signal?: AbortSignal,
) =>
  researchRequest<MarketMonitor>({
    method: 'GET',
    url: `/research/a-share/market-monitor?section=${section}`,
    signal,
  });
export const getMarketMonitor = (signal?: AbortSignal, keys?: string[]) =>
  researchRequest<MarketMonitor>({
    method: 'GET',
    url: '/research/a-share/market-monitor',
    params: { keys: keys?.join(',') },
    signal,
  });
