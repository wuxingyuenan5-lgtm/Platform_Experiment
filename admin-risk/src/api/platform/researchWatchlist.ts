import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

import {
  clearUserSystemSessionMemory,
  getUserSystemCsrfToken,
  UserSystemApiError,
} from './userSystem';

export interface AccountResearchWatchlistItem {
  code: string;
  name: string;
  group: string;
}

export interface AccountResearchWatchlist {
  items: AccountResearchWatchlistItem[];
  rowVersion: number;
  updatedAt?: string | null;
}

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
      '账号自选股请求失败';
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

export async function getAccountResearchWatchlist(): Promise<AccountResearchWatchlist> {
  return request({ method: 'GET', url: '/me/research-watchlist' });
}

export async function replaceAccountResearchWatchlist(
  items: AccountResearchWatchlistItem[],
  expectedVersion: number,
): Promise<AccountResearchWatchlist> {
  const csrfToken = getUserSystemCsrfToken();
  return request({
    method: 'PUT',
    url: '/me/research-watchlist',
    data: { items, expectedVersion },
    headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : undefined,
  });
}
