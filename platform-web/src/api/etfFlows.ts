import { researchRequest } from './hedgeResearch';

export interface FlowPeriod {
  flow: string | null;
  scale: string | null;
  ratio: string | null;
  complete: boolean;
  covered: number;
  expected: number;
}
export interface FlowGroup {
  name: string;
  count: number;
  current: FlowPeriod;
  previous: FlowPeriod;
  recovery: string | null;
}
export interface FlowFund extends FlowGroup {
  code: string;
  group: string;
  asset: string;
  sourceDate: string | null;
  sourceStatus: string;
  sourceUrls: string[];
  reportDate?: string;
  holdingRatio?: string;
  holdingValue?: string;
}
export interface FlowAnalysis {
  status: string;
  date: string;
  retrievedAt: string;
  start: string;
  end: string;
  previousStart: string;
  previousEnd: string;
  sessions: string[];
  funds: FlowFund[];
  groups: FlowGroup[];
  assets: FlowGroup[];
  summary: Omit<FlowGroup, 'name'>;
  source: string;
  scope: string;
}
export const getEtfFlows = (params: Record<string, string | number>, signal?: AbortSignal) =>
  researchRequest<FlowAnalysis>({
    method: 'GET',
    url: '/research/a-share/etf-flow-analysis',
    params,
    signal,
  });
