import { researchRequest } from '@/api/hedgeResearch';

export interface Stock {
  currency?: 'CNY' | 'HKD';
  instrument_id: string;
  status?: string;
  observed_at?: string | null;
  history_date?: string | null;
  code?: string | null;
  exchange?: string;
  name: string;
  industry?: string;
  research_baskets?: string[];
  price?: number | null;
  change?: number | null;
  change_5d?: number | null;
  change_20d?: number | null;
  ytd?: number | null;
  amount_yi?: number | null;
  mcap_yi?: number | null;
  turnover?: number | null;
  pe_ttm?: number | null;
  pb?: number | null;
}
export type Period = 'change' | 'change_5d' | 'change_20d' | 'ytd';
export interface PoolPayload {
  meta?: { report_date?: string | null; generated_at?: string; status?: string };
  summary: {
    tracked_count: number;
    breadth: { up: number; down: number; flat: number; median?: number | null };
    avg_change?: number | null;
    total_amount_yi?: number | null;
  };
  stocks: Stock[];
  focusStocks?: Stock[];
  indices?: Array<Stock & { code: string }>;
  heatmap?: Array<Stock & { weight?: number }>;
  leaders?: {
    today?: { up: Stock[]; down: Stock[] };
    '5d'?: { up: Stock[]; down: Stock[] };
    '20d'?: { up: Stock[]; down: Stock[] };
  };
  definitions?: {
    focus_codes?: string[];
    research_baskets?: Array<{ key: string; name: string; codes?: string[]; count: number }>;
  };
}

export interface PoolFocus {
  codes: string[];
  rowVersion: number;
}
export interface StockDetail {
  stock: Stock;
  history: Array<{
    observedAt: string;
    close: number | string;
    turnoverYuan?: number | string | null;
  }>;
}
const root = '/research/a-share';
export const getStockPool = async () =>
  (await researchRequest<{ data: PoolPayload }>({ url: `${root}/stock-pool` })).data;
export const getPoolFocus = async () =>
  (await researchRequest<{ data: PoolFocus }>({ url: `${root}/stock-pool/focus` })).data;
export const savePoolFocus = async (codes: string[], expectedVersion: number) =>
  (
    await researchRequest<{ data: PoolFocus }>({
      method: 'POST',
      url: `${root}/stock-pool/focus`,
      data: { codes, expectedVersion },
    })
  ).data;
export const addPoolCodes = async (codes: string[]) =>
  (
    await researchRequest<{ data: { count: number; added: string[] } }>({
      method: 'POST',
      url: `${root}/stock-pool/add-batch`,
      data: { codes },
    })
  ).data;
export const removePoolCode = async (code: string) =>
  (
    await researchRequest<{ data: { count: number } }>({
      method: 'DELETE',
      url: `${root}/stock-pool/remove`,
      params: { instrument_id: code },
    })
  ).data;
export const getPoolStockDetail = async (code: string) =>
  (
    await researchRequest<{ data: StockDetail }>({
      url: `${root}/stocks/${encodeURIComponent(code)}/history`,
    })
  ).data;
