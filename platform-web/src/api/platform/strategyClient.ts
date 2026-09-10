import axios, { type AxiosInstance } from 'axios';
import { getUserSystemCsrfToken } from './userSystem';

/** Strategy reads and writes use the same browser session as the signed-in CEO. */
export function createStrategyClient(timeout = 10_000): AxiosInstance {
  const client = axios.create({ baseURL: '/api/v1', timeout, withCredentials: true });
  client.interceptors.request.use((config) => {
    if (!['GET', 'HEAD', 'OPTIONS'].includes((config.method || 'GET').toUpperCase())) {
      const token = getUserSystemCsrfToken();
      if (token) config.headers.set('X-CSRF-Token', token);
    }
    return config;
  });
  return client;
}
