import { researchRequest, type MacroDashboardSeries } from './hedgeResearch';

export interface CycleInputs {
  indicators: Record<string, MacroDashboardSeries>;
  assets: Record<string, MacroDashboardSeries>;
  methodologyVersion: string;
}
export const readCycleInputs = (signal: AbortSignal) =>
  researchRequest<CycleInputs>({
    method: 'GET',
    url: '/research/cycles',
    signal,
  });
