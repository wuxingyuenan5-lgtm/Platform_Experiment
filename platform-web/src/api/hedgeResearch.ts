import { loadDashboardSnapshot } from './dashboardSnapshotCache';

import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

import {
  clearUserSystemSessionMemory,
  getCurrentAuthentication,
  getUserSystemCsrfToken,
  UserSystemApiError,
} from '@/api/platform/userSystem';

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

export interface AShareLiveSectorFundFlowRow {
  sectorCode: string;
  name: string;
  returnPct?: string | number | null;
  netInflowYuan: string | number;
  inflowYuan: string | number;
  outflowYuan: string | number;
  firmCount?: number | null;
}

export interface AShareLiveSectorFundFlowResponse {
  status: ResearchDataStatus;
  isStale: boolean;
  message?: string | null;
  fetchedAt: string;
  source: string;
  rows: AShareLiveSectorFundFlowRow[];
}

export interface AShareMarketTurnoverRow {
  securityCode: string;
  securityName: string;
  price?: number | null;
  returnPct?: number | null;
  turnoverYuan: number;
  marketCapYuan?: number | null;
  industry?: string | null;
}

export interface AShareMarketTurnoverResponse {
  status: ResearchDataStatus;
  isStale: boolean;
  message?: string | null;
  fetchedAt: string;
  source: string;
  dailyObservedAt?: string | null;
  highTurnoverCount?: number | null;
  highTurnoverRows?: AShareMarketTurnoverRow[];
  historyDates?: string[];
  historyCounts?: number[];
  historyIndustries?: Array<{ industry: string; counts: number[]; historyTotal: number }>;
  historicalRows?: Array<AShareMarketTurnoverRow & { observedAt: string }>;
  history?: Array<{
    observedAt: string;
    totalAmountYuan?: string | number | null;
    amountChangePct?: string | number | null;
    source?: string | null;
  }>;
  rows: AShareMarketTurnoverRow[];
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
  history?: Array<{
    observedAt: string;
    close: string | number;
    turnoverYuan?: string | number | null;
  }>;
}

export interface AShareBreadthSnapshot {
  up: number;
  down: number;
  flat: number;
  limitUp: number | null;
  realLimitUp: number | null;
  limitDown: number | null;
  realLimitDown: number | null;
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
  crowding?: ResearchModuleResult<{
    history?: Array<{
      date: string;
      targets: Record<
        string,
        {
          amount100m?: number | null;
          amountShareOfA?: number | null;
          turnoverPct?: number | null;
          price?: number | null;
          priceIndexCode?: string | null;
        }
      >;
      combined?: { amount100m?: number | null; amountShareOfA?: number | null };
    }>;
    latest?: {
      date: string;
      targets: Record<
        string,
        {
          amount100m?: number | null;
          amountShareOfA?: number | null;
          turnoverPct?: number | null;
          price?: number | null;
          priceIndexCode?: string | null;
        }
      >;
      combined?: { amount100m?: number | null; amountShareOfA?: number | null };
    };
    innovationHistory?: Array<{
      date: string;
      amount100m?: number | null;
      amountShareOfA?: number | null;
      turnoverPct?: number | null;
      price?: number | null;
    }>;
  }> | null;
  marketHistory?: Array<{
    observedAt: string;
    source?: string | null;
    up?: number | null;
    down?: number | null;
    flat?: number | null;
    limitUp?: number | null;
    limitDown?: number | null;
    totalAmountYuan?: string | number | null;
    amountChangePct?: string | number | null;
    marketBreadthPct?: string | number | null;
    csi300Close?: string | number | null;
    communicationPrice?: string | number | null;
    innovationPrice?: string | number | null;
  }>;
}

export interface AShareMarketHistoryRow {
  observedAt: string;
  totalAmountYuan?: string | number | null;
  amountChangePct?: string | number | null;
  source?: string | null;
}

export interface AShareMarketHistoryResponse {
  rows: AShareMarketHistoryRow[];
  coverageStart?: string | null;
  coverageEnd?: string | null;
  tradingDays: number;
  total: number;
  page: number;
  pageSize: number;
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
  originalLabel?: string | null;
  category: 'monetary_policy' | 'macro' | 'geopolitics' | 'election';
  probability: string | number;
  sourceUrl?: string | null;
  expiryAt?: string | null;
  history: MacroProbabilityPoint[];
}

export interface FomcMeeting {
  id: string;
  slug: string;
  label: string;
  meetingDate: string;
  expiryAt: string;
  updatedAt: string;
  closed: boolean;
  status: string;
  sourceUrl: string;
  outcomes: Array<{
    id: string;
    label: string;
    probability: number;
    history: MacroProbabilityPoint[];
  }>;
}

export interface MacroExpectationResponse {
  fomcStatus?: MacroExpectationStatus;
  fomcMeetings?: FomcMeeting[];
  status: MacroExpectationStatus;
  source: string;
  updatedAt: string;
  sourceUrl?: string | null;
  events: MacroExpectationEvent[];
}

export type MarketDetailStatus = 'ready' | 'partial' | 'degraded' | 'stale' | 'no_data' | 'error';

export interface MarketDetailRow {
  currency?: string | null;
  priceKind?: 'intraday' | 'close' | 'observation';
  history?: Array<{ date: string; value: string }>;
  sampleSize?: number | null;
  expectedSampleSize?: number | null;
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
  signals?: Partial<Record<'d10' | 'd20' | 'd50' | 'd200' | 'x2050' | 'x50200', string | null>>;
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
  priceLower?: string | number | null;
  priceUpper?: string | number | null;
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

export interface OptionExposureLeg {
  symbol: string;
  expiry: string;
  strike: string | number;
  side: 'call' | 'put';
  openInterest: string | number;
  gamma: string | number;
  underlyingPrice: string | number;
  multiplier: string | number;
  exposureUsd: string | number;
}

export interface OptionExposureSnapshot {
  market: 'deribit' | 'ibit';
  status: string;
  source: string;
  sourceUrl: string;
  collectedAt: string;
  asOf: string | null;
  underlyingLastTradeAt: string | null;
  underlyingPrice: string | number;
  totalContracts: number;
  excludedContracts: number;
  totalOpenInterest: string | number;
  includedOpenInterest: string | number;
  qualityFlags: string[];
  legs: OptionExposureLeg[];
}

export interface MacroDashboardResponse {
  schemaVersion: '1.0';
  status: string;
  asOf: string;
  groups: Record<string, MacroDashboardSeries[]>;
  optionDistribution?: {
    asOf?: string;
    status?: string;
    rows?: Array<{
      instrument: string;
      expiry: string;
      strike: number;
      side: string;
      openInterest: number;
      volume: number;
      underlyingPrice: number | null;
    }>;
  };
  optionExposure?: Record<string, OptionExposureSnapshot>;
}

const loadDashboard = (key: string, url: string) =>
  loadDashboardSnapshot(key, getUserSystemCsrfToken(), () =>
    researchRequest<MacroDashboardResponse>({
      method: 'GET',
      url,
      headers: { 'Cache-Control': 'no-cache' },
    }),
  );

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

client.interceptors.request.use(async (config) => {
  if (!['get', 'head', 'options'].includes((config.method || 'get').toLowerCase())) {
    if (!getUserSystemCsrfToken()) await getCurrentAuthentication();
    const csrf = getUserSystemCsrfToken();
    if (csrf) config.headers.set('X-CSRF-Token', csrf);
  }
  return config;
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

export async function researchRequest<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await client.request<T>(config);
  return response.data;
}

export interface MarketLayoutGroup {
  label: string;
  rows: Array<{ id: string; name: string; symbol: string; tvSymbol?: string }>;
}

export interface MarketLayoutResponse {
  groups: MarketLayoutGroup[] | null;
  rowVersion: number;
  updatedAt: string | null;
}

export const getMarketLayout = (marketId: string) =>
  researchRequest<MarketLayoutResponse>({
    method: 'GET',
    url: `/me/research-market-layout/${marketId}`,
  });

export const saveMarketLayout = (
  marketId: string,
  groups: MarketLayoutGroup[] | null,
  expectedVersion: number,
) =>
  researchRequest<MarketLayoutResponse>({
    method: 'PUT',
    url: `/me/research-market-layout/${marketId}`,
    data: { groups, expectedVersion },
  });

export const getAShareDashboard = (signal?: AbortSignal) =>
  researchRequest<AShareDashboardResponse>({
    method: 'GET',
    url: '/research/a-share/dashboard',
    signal,
  });

export const getAShareLiveSectorFundFlow = (signal?: AbortSignal) =>
  researchRequest<AShareLiveSectorFundFlowResponse>({
    method: 'GET',
    url: '/research/a-share/live-sector-flow',
    signal,
  });

export const getAShareLiveMarketTurnover = (signal?: AbortSignal) =>
  researchRequest<AShareMarketTurnoverResponse>({
    method: 'GET',
    url: '/research/a-share/live-market-turnover',
    signal,
  });

export const getAShareMarketHistory = (page = 1, pageSize = 100, signal?: AbortSignal) =>
  researchRequest<AShareMarketHistoryResponse>({
    method: 'GET',
    url: '/research/a-share/market-history',
    signal,
    params: { page, page_size: pageSize },
  });

export const refreshAShareResearch = () =>
  researchRequest<{ data: { status: string } }>({
    method: 'POST',
    url: '/research/a-share/refresh',
    timeout: 360_000,
  });

export const getStockSnapshot = (code: string) =>
  researchRequest<StockSnapshotResponse>({
    method: 'GET',
    url: `/research/a-share/stocks/${code}/snapshot`,
  });

export const getMacroExpectations = (signal?: AbortSignal) =>
  researchRequest<MacroExpectationResponse>({
    method: 'GET',
    url: '/research/macro/expectations',
    signal,
  });

export const getMarketDetail = (
  marketId: 'macro' | 'gold' | 'crypto' | 'us' | 'global',
  signal?: AbortSignal,
) =>
  researchRequest<MarketDetailResponse>({
    method: 'GET',
    url: `/research/market-detail/${marketId}`,
    signal,
  });

export interface CrossAssetComparison {
  status: string;
  days: number;
  dates: string[];
  unavailable: string[];
  yieldChangeBp: string | null;
  yieldDates: string[];
  assets: Array<{
    id: string;
    label: string;
    source: string;
    asOf: string;
    status: string;
    normalized: string[];
    returnPct: string;
    drawdownPct: string;
    correlation20: string | null;
    downsideMeanPct: string | null;
    downsideSamples: number;
  }>;
}
export const getCrossAssetComparison = (days: number) =>
  researchRequest<CrossAssetComparison>({
    method: 'GET',
    url: '/research/cross-asset',
    params: { days },
  });

export const getMacroDashboardV1 = () => loadDashboard('macro', '/research/macro/dashboard-v1');

export const getCommodityDashboardV1 = () =>
  loadDashboard('commodity', '/research/commodity/dashboard-v1');

export const getCryptoDashboardV1 = () => loadDashboard('crypto', '/research/crypto/dashboard-v1');

export interface FedWatchMeeting {
  date: string;
  contract?: string;
  probabilities: Record<string, number>;
}

export interface FedWatchZqPricing {
  code: string;
  month: string;
  monthISO: string;
  settle: number | null;
}

export interface FedWatchData {
  methodology?: string | null;
  probabilityUnit?: 'percent' | null;
  quoteAsOf?: string | null;
  missingMeetings?: string[] | null;
  effr: number | null;
  currentTarget: string | null;
  observedAt: string | null;
  settlementSource?: string | null;
  zqPricing: FedWatchZqPricing[];
  meetings: FedWatchMeeting[];
}

export interface CryptoEtfFlowData {
  observedAt: string | null;
  tickers: string[];
  flowUnit?: 'BTC' | 'ETH' | string;
  priceSource?: string | null;
  days: Array<{
    date: string;
    flows: Record<string, number | null>;
    totalFlow?: number | null;
    cumulativeFlow?: number | null;
    price?: number | null;
  }>;
  status?: string;
  lastError?: string | null;
}

export interface CryptoIvTermPoint {
  expiry: string;
  daysToExpiry: number;
  tenor: string;
  iv: number;
}

export interface CryptoIvTermData {
  index: number | null;
  observedAt: string | null;
  term: CryptoIvTermPoint[];
}

export interface CryptoIvDvolPoint {
  ts: number;
  value: number;
}

export interface CryptoIvDvolData {
  latest: number | null;
  history: CryptoIvDvolPoint[];
}

export interface CryptoIvSnapshotTenor {
  tenor: string;
  iv: number;
  expiry: string;
  daysToExpiry: number;
  strike?: number | null;
}

export interface CryptoIvSnapshotData {
  index: number | null;
  dvol: number | null;
  observedAt: string | null;
  tenors: CryptoIvSnapshotTenor[];
}

export interface CryptoIvHistoryPoint {
  observedAt: string;
  iv: number | null;
}

export interface CryptoIvHistoryStats {
  current: number | null;
  rangeLow: number | null;
  rangeHigh: number | null;
  historyLow: number | null;
  historyHigh: number | null;
  count: number;
}

export interface CryptoIvHistoryData {
  tenor: string;
  history: CryptoIvHistoryPoint[];
  stats: CryptoIvHistoryStats;
}

export type CumulativeVolatilityInterval = '15m' | '1h' | '4h';

export interface CumulativeVolatilityPoint {
  timestamp: string;
  session: 'asia' | 'europe' | 'americas';
  sessionDate: string;
  value: string | number;
  /** Backend-derived close used for the price overlay. */
  price?: string | number | null;
  /** First valid Americas-session close for this UTC session date. */
  priceBaseline?: string | number | null;
  /** Close relative to the Americas baseline, in percent. */
  priceChangePct?: string | number | null;
}

export interface CumulativeVolatilityData {
  schemaVersion: '1.0';
  asset: 'btc' | 'gold';
  interval: CumulativeVolatilityInterval;
  baseInterval: '15m';
  timezone: 'UTC';
  source: string;
  asOf: string | null;
  availableFrom: string | null;
  availableTo: string | null;
  isStale: boolean;
  message?: string | null;
  points: CumulativeVolatilityPoint[];
}

export interface CumulativeVolatilityResponse {
  data: CumulativeVolatilityData;
}

export const getMacroFedwatch = () =>
  researchRequest<{ data: FedWatchData }>({
    method: 'GET',
    url: '/research/macro/fedwatch',
  });

export type CryptoEtfAsset = 'btc' | 'eth';

export const getCryptoEtfFlow = (asset: CryptoEtfAsset = 'btc') =>
  researchRequest<{ data: CryptoEtfFlowData }>({
    method: 'GET',
    url: asset === 'eth' ? '/research/crypto/eth-etf-flow' : '/research/crypto/etf-flow',
  });

export const getCryptoIvTerm = () =>
  researchRequest<{ data: CryptoIvTermData }>({
    method: 'GET',
    url: '/research/crypto/iv-term',
  });

export const getCryptoIvDvol = (days: number = 30) =>
  researchRequest<{ data: CryptoIvDvolData }>({
    method: 'GET',
    url: '/research/crypto/iv-dvol',
    params: { days },
  });

export const getCryptoIvSnapshot = () =>
  researchRequest<{ data: CryptoIvSnapshotData }>({
    method: 'GET',
    url: '/research/crypto/iv-snapshot',
  });

export const getCryptoIvHistory = (tenor: '1M' | '3M' | '6M' | '1Y', days: number = 365) =>
  researchRequest<{ data: CryptoIvHistoryData }>({
    method: 'GET',
    url: '/research/crypto/iv-history',
    params: { tenor, days },
  });

export const getCumulativeVolatility = (
  asset: 'btc' | 'gold',
  days: number = 7,
  interval: CumulativeVolatilityInterval = '15m',
  window?: { start: string; end: string },
) =>
  researchRequest<CumulativeVolatilityResponse>({
    method: 'GET',
    url: '/research/cumulative-volatility',
    params: { asset, days, interval, ...window },
  });

export const getTreasuryWeeklySnapshot = () =>
  researchRequest<{
    status: string;
    observedAt: string | null;
    sourceUrl: string;
    dataPath: string | null;
  }>({ method: 'GET', url: '/research/crypto/treasury-weekly-snapshot' });
