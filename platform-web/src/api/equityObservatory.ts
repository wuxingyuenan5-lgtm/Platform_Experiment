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
export interface ThemeMetrics {
  expected: number;
  covered: number;
  medianReturn: EquityValue;
  advancingPct: EquityValue;
  return5?: EquityValue;
  return20?: EquityValue;
  relative20?: EquityValue;
  returnPctCount?: number;
  return5Count?: number;
  return20Count?: number;
  relative20Count?: number;
  returnPctRankable?: boolean;
  return5Rankable?: boolean;
  return20Rankable?: boolean;
  relative20Rankable?: boolean;
  above20Pct?: EquityValue;
  above20Count?: number;
}
export interface ThemeMember {
  code: string;
  name: string;
  segment: string;
  returnPct: EquityValue;
  return5?: EquityValue;
  return20?: EquityValue;
  relative20?: EquityValue;
  date: string | null;
  themeCount: number;
  themes?: string[];
  industry?: string | null;
  region?: string | null;
  source?: string;
  sourceUrl?: string;
  status: string;
  history?: EquityPoint[];
}
export interface EquityTheme extends ThemeMetrics {
  name: string;
  kind?: 'theme' | 'style' | 'satellite';
  segments: string[];
  segmentMetrics?: Array<ThemeMetrics & { name: string }>;
  members: ThemeMember[];
  overlaps?: Array<{ name: string; count: number }>;
  related?: string[];
  references?: Array<{
    code: string;
    name: string;
    coverage: string;
    scope: string;
    url: string;
    date: string | null;
    return1: EquityValue;
    return5: EquityValue;
    return20: EquityValue;
  }>;
}
export interface EquityThemes {
  styles?: {
    items: EquityStyle[];
    pairs: EquityStylePair[];
  };
  date: string;
  version?: string;
  effectiveFrom?: string;
  uniqueStocks?: number;
  benchmark?: {
    code: string;
    name: string;
    date: string | null;
    return5: EquityValue;
    return20: EquityValue;
  };
  sectors?: Array<{
    code: string;
    name: string;
    date: string | null;
    return1: EquityValue;
    return5: EquityValue;
    return20: EquityValue;
  }>;
  items: EquityTheme[];
}
export interface EquityStyle {
  code: string;
  name: string;
  scope: string;
  url: string;
  date: string | null;
  status: string;
  return1: EquityValue;
  return5: EquityValue;
  return20: EquityValue;
  relative20: EquityValue;
  history: EquityPoint[];
}
export interface EquityStylePair {
  name: string;
  numerator: string;
  denominator: string;
  date: string | null;
  spread1: EquityValue;
  spread5: EquityValue;
  spread20: EquityValue;
  history: EquityPoint[];
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
export interface IndexValuationChart {
  id: string;
  name: string;
  prices: Array<{ date: string; value: EquityValue }>;
  metrics: Array<{
    id: string;
    label: string;
    unit: string;
    source?: string;
    sourceUrl?: string;
    status: string;
    history: Array<{ date: string; value: EquityValue }>;
  }>;
}
export interface ThemeCrowdingBasket {
  name: string;
  expected: number;
  priceBaseDate: string | null;
  history: Array<{
    date: string;
    amountYuan: EquityValue;
    marketAmountYuan: EquityValue;
    sharePct: EquityValue;
    shareMa5: EquityValue;
    amountCount: number;
    price: EquityValue;
    priceCount: number;
  }>;
}
export interface ThemeCrowding {
  date: string | null;
  version: string;
  effectiveFrom: string;
  items: Array<ThemeCrowdingBasket & { segments: ThemeCrowdingBasket[] }>;
}
export interface EquityObservatory {
  themeCrowding?: ThemeCrowding;
  breadth?: {
    date: string;
    expected: number;
    valid: number;
    advancing: number;
    declining: number;
    unchanged: number;
    participation: Array<{
      period: number;
      valid: number;
      abovePct: EquityValue;
      highs: number;
      lows: number;
    }>;
  };
  sectionStatus?: Partial<
    Record<'market' | 'themes' | 'valuation' | 'hongKong', 'ready' | 'stale' | 'error'>
  >;
  valuationCharts?: IndexValuationChart[];
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
  themes?: EquityThemes | null;
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
