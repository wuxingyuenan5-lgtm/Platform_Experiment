import axios, { AxiosError } from 'axios';
import { getUserSystemCsrfToken } from '@/api/platform/userSystem';

export type ResearchDataStatus = 'loading' | 'ready' | 'partial' | 'no_data' | 'stale' | 'error';

export interface ResearchSourceMeta {
  source: string;
  sourceTimestamp?: string | null;
  fetchedAt: string;
  status: ResearchDataStatus;
  isStale: boolean;
  errorCode?: string | null;
  message?: string | null;
}

export interface ResearchModuleResult<T = unknown> {
  meta: ResearchSourceMeta;
  data: T;
}

export interface AShareIndexSnapshot {
  code: string;
  name: string;
  sourceSymbol: string;
  close?: string | number | null;
  turnoverYuan?: string | number | null;
  volatility20Pct?: string | number | null;
  return1dPct?: string | number | null;
  returnYtdPct?: string | number | null;
  returnQtdPct?: string | number | null;
  return1wPct?: string | number | null;
  return1mPct?: string | number | null;
  return1yPct?: string | number | null;
  distance52wHighPct?: string | number | null;
  signal1h?: string | null;
  signalDaily?: string | null;
  signal3d?: string | null;
  signalWeekly?: string | null;
  spark: Array<string | number>;
}

export interface AShareBreadthSnapshot {
  up: number;
  down: number;
  flat: number;
  limitUp: number;
  realLimitUp: number;
  limitDown: number;
  realLimitDown: number;
  activityPct?: string | number | null;
  breadthState: string;
  speculationState: string;
  tradeDate?: string | null;
}

export interface ShenwanLevel2Aggregate {
  rank: number;
  swL1Code: string;
  swL1Name: string;
  swL2Code: string;
  swL2Name: string;
  returnPct?: string | number | null;
  turnoverYuan: string | number;
  marketSharePct: string | number;
  netInflowYuan?: string | number | null;
}

export interface TurnoverThresholdIndustryCount {
  swL1Code: string;
  swL1Name: string;
  swL2Code: string;
  swL2Name: string;
  stockCount: number;
}

export interface TurnoverThresholdStock {
  securityCode: string;
  securityName: string;
  swL1Code: string;
  swL1Name: string;
  swL2Code: string;
  swL2Name: string;
  turnoverYuan: string | number;
  returnPct?: string | number | null;
}

export interface AShareResearchAggregation {
  sw2Top: ShenwanLevel2Aggregate[];
  sw2All: ShenwanLevel2Aggregate[];
  threshold: {
    thresholdYuan: string | number;
    operator: '>';
    industries: TurnoverThresholdIndustryCount[];
    stocks: TurnoverThresholdStock[];
    unmatchedSecurityCodes: string[];
  };
  unmatchedSecurityCodes: string[];
}

export interface EmotionLadderRow {
  boardCount: string;
  stockCount: number;
}

export interface EmotionStockRow {
  securityCode: string;
  securityName: string;
  boardCount: number;
  turnoverYuan?: string | number | null;
}

export interface ShortTermEmotionSnapshot {
  limitUpCount: number;
  brokenBoardCount: number;
  limitDownCount: number;
  highestBoardCount: number;
  consecutiveBoardCount: number;
  sealRatePct?: string | number | null;
  breakRatePct?: string | number | null;
  promotionRatePct?: string | number | null;
  ladder: EmotionLadderRow[];
  leaders: EmotionStockRow[];
  tradeDate?: string | null;
}

export interface AShareDashboardResponse {
  generatedAt: string;
  marketDetail: ResearchModuleResult<AShareIndexSnapshot[]>;
  breadth: ResearchModuleResult<AShareBreadthSnapshot>;
  shenwan: ResearchModuleResult<AShareResearchAggregation>;
  emotion: ResearchModuleResult<ShortTermEmotionSnapshot>;
}

export interface StockSnapshotResponse {
  securityCode: string;
  securityName?: string | null;
  generatedAt: string;
  completenessPct: string | number;
  modules: Record<string, ResearchModuleResult>;
}

export interface MacroProbabilityPoint {
  observedAt: string;
  probabilityPct: string | number;
}

export interface MacroExpectationEvent {
  eventId: string;
  category: 'monetary_policy' | 'macro' | 'geopolitics' | 'election';
  title: string;
  outcome: string;
  currentProbabilityPct: string | number;
  change1dPctPoints?: string | number | null;
  change7dPctPoints?: string | number | null;
  liquidityLabel?: string | null;
  expiryAt?: string | null;
  sourceUrl?: string | null;
  history: MacroProbabilityPoint[];
}

export interface MacroExpectationResponse {
  generatedAt: string;
  events: ResearchModuleResult<MacroExpectationEvent[]>;
}

export interface AccountWatchlistItem {
  securityCode: string;
  securityName: string;
  group: string;
}

export interface AccountWatchlistResponse {
  market: 'a_share';
  version: number;
  updatedAt?: string | null;
  items: AccountWatchlistItem[];
}

export interface ReplaceAccountWatchlistPayload {
  expectedVersion: number;
  items: AccountWatchlistItem[];
}

const researchClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

function researchError(error: unknown, fallback: string): Error {
  if (!(error instanceof AxiosError)) return error instanceof Error ? error : new Error(fallback);
  const detail = error.response?.data?.detail as
    | { message?: string; code?: string }
    | string
    | undefined;
  const responseMessage =
    (typeof detail === 'object' && detail?.message) ||
    (typeof detail === 'string' ? detail : undefined);
  const result = new Error(responseMessage || error.message || fallback) as Error & {
    status?: number;
    code?: string;
  };
  result.status = error.response?.status;
  if (typeof detail === 'object') result.code = detail?.code;
  return result;
}

async function platformGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  try {
    const response = await researchClient.get<T>(url, { params });
    return response.data;
  } catch (error) {
    throw researchError(error, '投研数据请求失败');
  }
}

export const getAShareDashboard = (thresholdYuan = 10_000_000_000) =>
  platformGet<AShareDashboardResponse>('/research/a-share/dashboard', { thresholdYuan });

export const getStockSnapshot = (code: string) =>
  platformGet<StockSnapshotResponse>(`/research/a-share/stocks/${code}/snapshot`);

export const getMacroExpectations = () =>
  platformGet<MacroExpectationResponse>('/research/macro/expectations');

export async function getAShareAccountWatchlist(): Promise<AccountWatchlistResponse> {
  try {
    const response = await researchClient.get<AccountWatchlistResponse>(
      '/me/research/a-share/watchlist',
    );
    return response.data;
  } catch (error) {
    throw researchError(error, '自选股同步失败');
  }
}

export async function replaceAShareAccountWatchlist(
  payload: ReplaceAccountWatchlistPayload,
): Promise<AccountWatchlistResponse> {
  try {
    const response = await researchClient.put<AccountWatchlistResponse>(
      '/me/research/a-share/watchlist',
      payload,
      {
        headers: { 'X-CSRF-Token': getUserSystemCsrfToken() },
      },
    );
    return response.data;
  } catch (error) {
    throw researchError(error, '自选股同步失败');
  }
}
