import { researchRequest, type MacroDashboardSeries } from './hedgeResearch';

export type SeasonalAsset =
  | 'gold'
  | 'btc'
  | 'us-spy'
  | 'us-ndx'
  | 'us-dow'
  | 'cn-hs300'
  | 'cn-csi1000'
  | 'cn-chinext'
  | 'cn-star50';
export interface SeasonalHistory extends MacroDashboardSeries {
  tradingDates?: string[];
}

export const readSeasonalHistory = (asset: SeasonalAsset, signal: AbortSignal) =>
  researchRequest<SeasonalHistory>({
    method: 'GET',
    url: `/research/seasonality/${asset}`,
    signal,
  });
