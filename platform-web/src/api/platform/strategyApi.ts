import createClient from 'openapi-fetch';
import axios from 'axios';
import type { paths } from './generated/strategy';
import { createStrategyClient } from './strategyClient';
import { strategyQueryClient, strategyQueryKey, strategySession } from './strategyQueries';

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

export function strategyData<T>(response: { data?: T }): T {
  if (response.data === undefined) throw new Error('策略数据暂不可用');
  return response.data;
}
