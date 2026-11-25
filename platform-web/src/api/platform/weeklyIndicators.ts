import { researchRequest, type MacroDashboardSeries } from '@/api/hedgeResearch';

export interface WeeklyIndicator {
  id: string;
  label: string;
  unit: string;
  frequency: string;
  section: string;
  group: string;
  definition: string;
  reportTitle: string;
  reportDate: string;
  page: number;
  series: MacroDashboardSeries;
}

export interface WeeklySupplement {
  batchId: string;
  section: string;
  updatedAt: string | null;
  items: WeeklyIndicator[];
}

export const getWeeklySupplement = (section: string, signal: AbortSignal, indicator?: string) =>
  researchRequest<WeeklySupplement>({
    method: 'GET',
    url: '/research/macro/weekly-supplement',
    params: { section, ...(indicator ? { indicator } : {}) },
    signal,
  });
