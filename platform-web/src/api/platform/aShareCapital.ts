import { researchRequest, type MacroDashboardSeries } from '@/api/hedgeResearch';

export interface CapitalRow {
  date: string;
  [key: string]: string | number | null | undefined;
}
export interface CapitalSource {
  label: string;
  provider: string;
  sourceUrl: string;
  status: string;
  isStale: boolean;
  fetchedAt?: string;
  observationDate?: string;
  windowStart?: string;
  windowEnd?: string;
  rows: CapitalRow[];
}
export interface CapitalDashboard {
  broadEtf?: import('../etfObservation').ObservationSummary & { status: string };
  comparisons?: {
    marginChange5d: string | null;
    etfFlow5d: string | null;
    rateSpreadBp: string | null;
  };
  asOf: string;
  sources: Record<string, CapitalSource>;
  institutions?: Record<string, CapitalSource>;
  handbook?: {
    source?: string;
    fetchedAt?: string;
    asOf?: string;
    institutions?: CapitalRow[];
    holdings?: CapitalRow[];
    margins?: CapitalRow[];
    issues?: CapitalRow[];
    bank?: CapitalRow[];
    residents?: CapitalRow[];
    residentMarket?: CapitalRow[];
    foreign?: CapitalRow[];
    foreignValueShare?: CapitalRow[];
    northIndustryReports?: {
      date: string;
      tradeDate: string;
      eligibleCount: number;
      coveredCount: number;
      rows: { name: string; valueYi: string; stocks: number; weightPct: string }[];
    }[];
    fundIndustryBenchmarks?: {
      date: string;
      tradeDate: string;
      rows: { name: string; weightPct: string }[];
    }[];
    capitalEvents?: Record<string, { rows: CapitalRow[]; through: string; fetchedAt: string }>;
    fundStockReports?: {
      date: string;
      fetchedAt: string;
      method?: 'css';
      rows: {
        code: string;
        name: string;
        valueYi: string;
        fundCount: string | null;
        shareChangeWan: string | null;
      }[];
    }[];
    social?: CapitalRow[];
    pension?: CapitalRow[];
    occupationalPension?: CapitalRow[];
    publicSources?: Record<string, { status: string; fetchedAt?: string; sourceUrl?: string }>;
    publicFetchedAt?: string;
  };
  macro: Record<string, MacroDashboardSeries>;
  moneyCreditGap: CapitalRow[];
  unlockWeeks: CapitalRow[];
  etf: {
    status?: string;
    retrievedAt?: string;
    sourceUrl?: string;
    sourceLabel?: string;
    nativeFrom?: string;
    rows: CapitalRow[];
  };
}
export const getAShareCapital = (signal: AbortSignal) =>
  researchRequest<CapitalDashboard>({ method: 'GET', url: '/research/a-share/capital', signal });
