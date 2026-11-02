import { researchRequest } from './hedgeResearch';

export type FundValue = string | null;
export interface FundAllocation {
  date: string;
  stockPct: FundValue;
  bondPct: FundValue;
  cashPct: FundValue;
  navYuan: FundValue;
}
export interface FundEntry extends FundAllocation {
  code: string;
  name: string;
  groupName: string;
  type: string;
  classes: Array<{ code: string; name: string; type: string }>;
  manager?: string;
  company?: string;
  legalName?: string;
  benchmark?: string;
  status: string;
  aggregateEligible: boolean;
}
export interface FundSummary extends FundAllocation {
  fundCount: number;
  commonCount?: number;
  stockChangePp?: FundValue;
  navChangePct?: FundValue;
  cashPctCount?: number;
}
export interface FundIndustry {
  code: string;
  name: string;
  market: string;
  weightPct: FundValue;
  changePp?: FundValue;
  fundCount?: number;
  sampleCount?: number;
  commonCount?: number;
}
export interface FundStock {
  code: string;
  name: string;
  market: string;
  valueYuan: FundValue;
  shares: FundValue;
  weightPct?: FundValue;
  shareChangePct?: FundValue;
  valueChangePct?: FundValue;
  comparison?: string;
  fundCount?: number;
  comparableCount?: number;
}
export interface FundOverview {
  collectionStatus?: 'paused' | 'active';
  status: string;
  source?: string;
  date?: string;
  expectedPeriod: string;
  generatedAt?: string;
  dates: string[];
  expectedCount?: number;
  collectedCount?: number;
  attemptedCount?: number;
  readyCount?: number;
  summary?: FundSummary;
  industries?: FundIndustry[];
  stocks?: FundStock[];
  holdingFundCount?: number;
  history: FundSummary[];
  funds: FundEntry[];
}
export interface FundDetail {
  fund: Pick<FundEntry, 'code' | 'name' | 'type' | 'classes'>;
  status: string;
  attemptedAt: string;
  sources: Record<string, { status: string; retrievedAt?: string; sourceUrl?: string }>;
  data: {
    profile?: Pick<FundEntry, 'legalName' | 'manager' | 'company' | 'benchmark'>;
    allocations?: FundAllocation[];
    sizes?: Array<{
      date: string;
      subscriptions: FundValue;
      redemptions: FundValue;
      shares: FundValue;
      navYuan: FundValue;
    }>;
    holdings?: Array<{ date: string; coverage: string; rows: FundStock[] }>;
    industries?: Array<{ date: string; rows: FundIndustry[] }>;
    reports?: Array<{ date: string; title: string; publishedAt: string; url: string }>;
  };
}

export const readFundOverview = (period?: string, signal?: AbortSignal) =>
  researchRequest<FundOverview>({
    method: 'GET',
    url: '/research/a-share/mutual-funds',
    params: { period },
    signal,
  });
export const readFundDetail = (code: string, signal?: AbortSignal) =>
  researchRequest<FundDetail>({
    method: 'GET',
    url: `/research/a-share/mutual-funds/${code}`,
    signal,
  });
