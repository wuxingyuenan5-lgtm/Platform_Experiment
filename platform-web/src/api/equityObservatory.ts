import { researchRequest } from './hedgeResearch';

export type EquityValue = string | number | null;
export interface EquityPoint {
  date: string;
  value?: EquityValue;
  pe?: EquityValue;
  pb?: EquityValue;
  ps?: EquityValue;
  pcf?: EquityValue;
  erp?: EquityValue;
  close?: EquityValue;
}
export interface EquityRank {
  value: EquityValue;
  count: number;
  start: string | null;
  end: string | null;
}
export interface EquityTheme {
  name: string;
  segments: string[];
  expected: number;
  covered: number;
  medianReturn: EquityValue;
  advancingPct: EquityValue;
  members: Array<{
    code: string;
    name: string;
    segment: string;
    returnPct: EquityValue;
    date: string | null;
    themeCount: number;
    status: string;
  }>;
}
export interface EquityDistribution {
  count: number;
  peCount: number;
  pbCount: number;
  belowBookCount: number;
  belowBookPct: EquityValue;
  medianPe: EquityValue;
  medianPb: EquityValue;
  medianReturn: EquityValue;
  advancingPct: EquityValue;
  medianTurnover: EquityValue;
  nonpositivePeCount: number;
  nonpositivePbCount: number;
  top20AmountPct: EquityValue;
  top50AmountPct: EquityValue;
}
export interface EquityTrend {
  name: string;
  code?: string;
  symbols?: string;
  date: string | null;
  count: number;
  close?: EquityValue;
  deviation20?: EquityValue;
  deviation60?: EquityValue;
  deviation200?: EquityValue;
  return5?: EquityValue;
  return20?: EquityValue;
  drawdown252?: EquityValue;
  history?: EquityPoint[];
}
export interface EquityValuation {
  id: string;
  name: string;
  date: string | null;
  pe: EquityValue;
  pb: EquityValue;
  dividend: EquityValue;
  peRank: EquityRank;
  source: string;
  sourceUrl: string;
  method: string;
  status: string;
  estimated: boolean;
  history: EquityPoint[];
}
export interface EquityObservatory {
  indexCrowding?: Array<
    EquityDistribution & {
      code: string;
      name: string;
      date: string;
      membershipDate: string | null;
      expected: number;
      turnoverRank: EquityValue;
      sampleCount: number;
    }
  >;
  market: string;
  status: string;
  date?: string;
  generatedAt: string | null;
  sourceFetchedAt?: string;
  themes?: { date: string; items: EquityTheme[] };
  structure?: {
    date: string;
    closed: boolean;
    market: EquityDistribution;
    unclassifiedCount: number;
    industries: Array<
      EquityDistribution & {
        code: string;
        name: string;
        amountSharePct: EquityValue;
        shareRank: EquityValue;
        turnoverRank: EquityValue;
        sampleCount: number;
      }
    >;
  };
  structureHistory?: Array<EquityDistribution & { date: string }>;
  indices?: EquityTrend[];
  ratios?: EquityTrend[];
  crowding?: Array<{
    name: string;
    date: string;
    sharePct: EquityValue;
    turnover: EquityValue;
    shareRank: EquityValue;
    turnoverRank: EquityValue;
    count: number;
  }>;
  participation?: Array<{
    period: number;
    count: number;
    expected: number;
    value: EquityValue;
    date: string;
  }>;
  valuations?: EquityValuation[];
  reference?: {
    source?: string;
    method?: string;
    rows?: EquityPoint[];
    ranks?: Record<string, EquityRank>;
  };
  risk?: Array<{
    name: string;
    value: EquityValue;
    date: string;
    source: string;
    sourceUrl: string;
    status: string;
    history: EquityPoint[];
  }>;
  hongKong?: {
    status: string;
    date: string | null;
    value: EquityValue;
    history: EquityPoint[];
    indices?: Array<{
      name: string;
      date: string;
      value: EquityValue;
      returnPct: EquityValue;
      history: EquityPoint[];
    }>;
    components: Array<{
      id: string;
      name: string;
      weight: number;
      date: string;
      value: EquityValue;
      count: number;
      contribution: EquityValue;
      compositeDate: string | null;
      source: string;
      sourceUrl: string;
      status: string;
    }>;
  };
  sources?: Array<{
    name: string;
    status: string;
    date: string | null;
    fetchedAt?: string;
    error?: string;
  }>;
}

export const getEquityObservatory = (market: 'cn' | 'us', signal?: AbortSignal) =>
  researchRequest<EquityObservatory>({
    method: 'GET',
    url: `/research/equity-observatory/${market}`,
    signal,
  });
