import createClient from 'openapi-fetch';
import axios from 'axios';
import type { paths } from './generated/strategy';
import { createStrategyClient } from './strategyClient';
import { strategyQueryClient, strategyQueryKey, strategySession } from './strategyQueries';
import { clearUserSystemSessionMemory } from './userSystem';

const SESSION_ERROR_CODES = new Set([
  'invalid_session',
  'human_session_required',
  'csrf_required',
  'csrf_invalid',
  'account_inactive',
  'account_temporarily_locked',
  'browser_sessions_disabled',
  'session_timestamp_invalid',
]);

function readableStrategyError(error: unknown): string {
  if (!error || typeof error !== 'object') return '策略数据暂不可用';
  const detail = (error as { detail?: unknown }).detail;
  if (detail && typeof detail === 'object') {
    const code = String((detail as { code?: unknown }).code || '');
    const message = String((detail as { message?: unknown }).message || '');
    if (SESSION_ERROR_CODES.has(code)) {
      clearUserSystemSessionMemory();
      return code === 'csrf_required' || code === 'csrf_invalid'
        ? '登录校验已失效，请刷新页面或重新登录后再提交。'
        : '登录会话已失效，请重新登录后再提交价差指令。';
    }
    if (message) return message;
  }
  if (typeof detail === 'string' && detail) return detail;
  const message = (error as { message?: unknown }).message;
  return typeof message === 'string' && message ? message : '策略数据暂不可用';
}

/** Generated paths/types, with the existing session, CSRF and timeout transport. */
export function createStrategyApi(timeout = 10_000) {
  const transport = createStrategyClient(timeout);
  const api = createClient<paths>({
    baseUrl: typeof location === 'undefined' ? 'http://localhost' : location.origin,
    async fetch(request) {
      const generation = strategySession.value.generation;
      const headers: Record<string, string> = {};
      request.headers.forEach((value, key) => {
        headers[key] = value;
      });
      const body = request.body === null ? undefined : await request.text();
      if (generation !== strategySession.value.generation) throw new Error('登录状态已变更');
      const response = await transport
        .request<string>({
          url: request.url,
          method: request.method,
          headers,
          data: body,
          signal: request.signal,
          responseType: 'text',
          transformResponse: [(value) => value],
        })
        .catch((error: unknown) => {
          // The text transport preserves exact successful payloads. Decode error
          // JSON too so callers retain both the HTTP status and business reason.
          if (axios.isAxiosError(error) && typeof error.response?.data === 'string') {
            try {
              error.response.data = JSON.parse(error.response.data);
            } catch {
              // A non-JSON upstream error retains its original response and status.
            }
          }
          throw error;
        });
      if (generation !== strategySession.value.generation) throw new Error('登录状态已变更');
      // Preserve Axios errors for existing UI recovery. No request is retried here.
      return new Response(response.status === 204 ? null : response.data, {
        status: response.status,
        headers: { 'Content-Type': 'application/json' },
      });
    },
  });
  api.use({
    onResponse({ request, response }) {
      if (request.method !== 'GET' && response.ok) {
        void strategyQueryClient.invalidateQueries({ queryKey: strategyQueryKey() });
      }
    },
  });
  return api;
}

export function strategyData<T>(response: { data?: T; error?: unknown }): T {
  if (response.data === undefined) throw new Error(readableStrategyError(response.error));
  return response.data;
}
