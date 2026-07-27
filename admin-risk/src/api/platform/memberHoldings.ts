import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import {
  UserSystemApiError,
  clearUserSystemSessionMemory,
  getUserSystemCsrfToken,
} from './userSystem';

export type HoldingSource = 'manual_admin' | 'migration' | 'external_import';
export type ManualHoldingSource = 'manual_admin';
export type HoldingStatus = 'active' | 'closed';
export type NavStatus = 'available' | 'stale' | 'unavailable';

export interface FundSummary {
  fundId: string;
  fundName: string;
  fundCode?: string;
  baseCurrency: string;
}

export interface MemberHolding {
  holdingId: string;
  memberUserId: string;
  fundId: string;
  fundName: string;
  fundCode?: string;
  currency: string;
  shareQuantity: string;
  latestUnitNav?: string;
  marketValue?: string;
  cumulativeInvested: string;
  cumulativeReturn?: string;
  returnRate?: string;
  navStatus: NavStatus;
  navValuationTime?: string;
  confirmedAt?: string;
  asOf: string;
  source: HoldingSource;
  status: HoldingStatus;
  rowVersion: number;
  updatedAt: string;
}

export interface UpsertMemberHoldingPayload {
  shareQuantity: string;
  cumulativeInvested: string;
  confirmedAt?: string;
  asOf: string;
  source?: ManualHoldingSource;
  status?: HoldingStatus;
  expectedVersion?: number;
}

export interface UpsertFundNavPayload {
  unitNav: string;
  valuationTime: string;
  currency: string;
  source?: ManualHoldingSource;
  fundCode?: string;
}

export interface FundNavMutationResult {
  fund: FundSummary;
  unitNav: string;
  valuationTime: string;
  currency: string;
  source: HoldingSource;
}

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);
const SESSION_INVALIDATION_CODES = new Set([
  'invalid_session',
  'human_session_required',
  'csrf_required',
  'csrf_invalid',
  'account_inactive',
  'account_temporarily_locked',
  'browser_sessions_disabled',
  'session_timestamp_invalid',
]);
const client: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 15_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const method = String(config.method || 'GET').toUpperCase();
  const csrfToken = getUserSystemCsrfToken();
  if (!SAFE_METHODS.has(method) && csrfToken) {
    config.headers.set('X-CSRF-Token', csrfToken);
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
    const message =
      body?.message ||
      (typeof detail === 'string' ? detail : undefined) ||
      payload?.message ||
      error.message ||
      '持仓请求失败';
    const legacyCsrfFailure =
      status === 403 &&
      typeof detail === 'string' &&
      (detail.includes('CSRF token') || detail.includes('browser session'));
    if (status === 401 || SESSION_INVALIDATION_CODES.has(body?.code || '') || legacyCsrfFailure) {
      clearUserSystemSessionMemory();
    }
    return Promise.reject(new UserSystemApiError(message, status, body?.code));
  },
);

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await client.request<T>(config);
  return response.data;
}

export async function getSelfMemberHoldings(): Promise<MemberHolding[]> {
  const result = await request<{ items: MemberHolding[] }>({
    method: 'GET',
    url: '/me/holdings',
  });
  return result.items;
}

export async function getAdminMemberHoldings(userId: string): Promise<MemberHolding[]> {
  const result = await request<{ items: MemberHolding[] }>({
    method: 'GET',
    url: `/users/${encodeURIComponent(userId)}/holdings`,
  });
  return result.items;
}

export async function listHoldingFunds(): Promise<FundSummary[]> {
  const result = await request<{ items: FundSummary[] }>({
    method: 'GET',
    url: '/users/holdings/funds',
  });
  return result.items;
}

export async function putAdminMemberHolding(
  userId: string,
  fundId: string,
  payload: UpsertMemberHoldingPayload,
): Promise<MemberHolding> {
  return request({
    method: 'PUT',
    url: `/users/${encodeURIComponent(userId)}/holdings/${encodeURIComponent(fundId)}`,
    data: payload,
  });
}

export async function putHoldingFundNav(
  fundId: string,
  payload: UpsertFundNavPayload,
): Promise<FundNavMutationResult> {
  return request({
    method: 'PUT',
    url: `/users/holdings/funds/${encodeURIComponent(fundId)}/nav`,
    data: payload,
  });
}
