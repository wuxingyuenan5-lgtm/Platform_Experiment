import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

import { clearUserSystemSessionMemory, UserSystemApiError } from '@/api/platform/userSystem';

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

export type MacroExpectationStatus = 'ready' | 'no_data' | 'not_configured' | 'stale' | 'error';

export interface MacroProbabilityPoint {
  observedAt: string;
  probability: string | number;
}

export interface MacroExpectationEvent {
  id: string;
  label: string;
  category: 'monetary_policy' | 'macro' | 'geopolitics' | 'election';
  probability: string | number;
  history: MacroProbabilityPoint[];
}

export interface MacroExpectationResponse {
  status: MacroExpectationStatus;
  source: string;
  updatedAt: string;
  events: MacroExpectationEvent[];
}

export type MarketDetailStatus = 'ready' | 'partial' | 'degraded' | 'stale' | 'no_data' | 'error';

export interface MarketDetailRow {
  id: string;
  name: string;
  symbol: string;
  status: MarketDetailStatus;
  unit: string;
  changeUnit: 'percent' | 'basis_points' | 'absolute';
  frequency: string;
  timezone: string;
  observationDate?: string | null;
  asOf?: string | null;
  source: string;
  sourceUrl?: string | null;
  methodologyVersion: string;
  qualityFlags: string[];
  close?: string | number | null;
  change1d?: string | number | null;
  change1w?: string | number | null;
  change1m?: string | number | null;
  changeQtd?: string | number | null;
  changeYtd?: string | number | null;
  change1y?: string | number | null;
  high52w?: string | number | null;
  distance52wHigh?: string | number | null;
  spark30d: Array<string | number>;
  spark90d?: Array<string | number>;
}

export interface MarketDetailResponse {
  schemaVersion: '1.0';
  marketId: string;
  status: MarketDetailStatus;
  asOf?: string | null;
  retrievedAt?: string | null;
  rows: MarketDetailRow[];
}

export interface MacroDashboardObservation {
  date: string;
  value?: string | number | null;
}

export interface MacroDashboardSeries {
  seriesId: string;
  label: string;
  status: string;
  latestValue?: string | number | null;
  unit: string;
  frequency: string;
  timezone: string;
  source: string;
  sourceSeriesId?: string | null;
  sourceUrl?: string | null;
  observationDate?: string | null;
  asOf?: string | null;
  retrievedAt?: string | null;
  isStale: boolean;
  methodologyVersion: string;
  qualityFlags: string[];
  observations: MacroDashboardObservation[];
}

export interface MacroDashboardResponse {
  schemaVersion: '1.0';
  status: string;
  asOf: string;
  groups: Record<string, MacroDashboardSeries[]>;
}

const SESSION_INVALIDATION_CODES = new Set([
  'invalid_session',
  'human_session_required',
  'account_inactive',
  'account_temporarily_locked',
  'browser_sessions_disabled',
  'session_timestamp_invalid',
]);

const client: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  withCredentials: true,
});

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const payload = error.response?.data as
      | { detail?: { code?: string; message?: string } | string; message?: string }
      | undefined;
    const detail = payload?.detail;
    const body = typeof detail === 'object' && detail ? detail : undefined;
    const status = error.response?.status;
    const code = body?.code;
    const message =
      body?.message ||
      (typeof detail === 'string' ? detail : undefined) ||
      payload?.message ||
      error.message ||
      '投研数据请求失败';
    if (status === 401 || SESSION_INVALIDATION_CODES.has(code || '')) {
      clearUserSystemSessionMemory();
    }
    return Promise.reject(new UserSystemApiError(message, status, code));
  },
);

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await client.request<T>(config);
  return response.data;
}

export const getAShareDashboard = (thresholdYuan = 10_000_000_000) =>
  request<AShareDashboardResponse>({
    method: 'GET',
    url: '/research/a-share/dashboard',
    params: { thresholdYuan },
  });

export const getStockSnapshot = (code: string) =>
  request<StockSnapshotResponse>({
    method: 'GET',
    url: `/research/a-share/stocks/${code}/snapshot`,
  });

export const getMacroExpectations = () =>
  request<MacroExpectationResponse>({
    method: 'GET',
    url: '/research/macro/expectations',
  });

export const getMarketDetail = (marketId: 'macro') =>
  request<MarketDetailResponse>({
    method: 'GET',
    url: `/research/market-detail/${marketId}`,
  });

export const getMacroDashboardV1 = () =>
  request<MacroDashboardResponse>({
    method: 'GET',
    url: '/research/macro/dashboard-v1',
  });

export const getCommodityDashboardV1 = () =>
  request<MacroDashboardResponse>({
    method: 'GET',
    url: '/research/commodity/dashboard-v1',
  });

export const getCryptoDashboardV1 = () =>
  request<MacroDashboardResponse>({
    method: 'GET',
    url: '/research/crypto/dashboard-v1',
  });
