import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import {
  UserSystemApiError,
  clearUserSystemSessionMemory,
  getUserSystemCsrfToken,
} from './userSystem';

export interface UserAdminNote {
  userId: string;
  adminNote?: string;
  rowVersion: number;
  updatedAt: string;
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
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const csrfToken = getUserSystemCsrfToken();
  if (String(config.method || 'GET').toUpperCase() === 'PATCH' && csrfToken) {
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
      '运营备注请求失败';
    if (status === 401 || SESSION_INVALIDATION_CODES.has(body?.code || '')) {
      clearUserSystemSessionMemory();
    }
    return Promise.reject(new UserSystemApiError(message, status, body?.code));
  },
);

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await client.request<T>(config);
  return response.data;
}

export async function getUserAdminNote(userId: string): Promise<UserAdminNote> {
  return request({
    method: 'GET',
    url: `/users/${encodeURIComponent(userId)}/admin-note`,
  });
}

export async function updateUserAdminNote(
  userId: string,
  adminNote: string | null,
  expectedVersion: number,
): Promise<UserAdminNote> {
  return request({
    method: 'PATCH',
    url: `/users/${encodeURIComponent(userId)}/admin-note`,
    data: { adminNote, expectedVersion },
  });
}
