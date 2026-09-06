import { getUserSystemCsrfToken } from '@/api/platform/userSystem';

const CONNECTION_KEY = 'vg-financial-ai-mode-v1';
const LEGACY_SECRET_KEYS = ['vg-financial-ai-connection-v2', 'vg-financial-ai-connection-v3'];
export type FinancialAiMode = 'api' | 'subscription';
export type FinancialAiCli = 'claude' | 'qwen' | 'deepseek' | 'codex';
export interface FinancialAiConnection {
  mode: FinancialAiMode;
  cli: FinancialAiCli;
  backendAccessKey?: string;
}
export interface AiCapability {
  key: string;
  name: string;
  available: boolean;
  status: string;
  latencyMs?: number;
}
export interface FinancialAiDeployment {
  configured: boolean;
  hasApiKey: boolean;
  provider: string;
  baseUrl: string;
  model: string;
  message: string;
}
export interface RadarItem {
  title: string;
  url: string;
  source: string;
  publishedAt: string;
}
export interface RadarIndustry {
  key: string;
  name: string;
  accent: string;
  items: RadarItem[];
}
export interface RadarPartialFailure {
  group: string;
  source: string;
  message: string;
}
export interface GlobalStockSnapshot {
  symbol: string;
  sourceSymbol: string;
  name: string;
  market?: string;
  currency?: string;
  price?: number;
  previousClose?: number;
  changePct?: number;
  open?: number;
  dayHigh?: number;
  dayLow?: number;
  volume?: number;
  amount?: number;
  marketCap?: number;
  metrics?: {
    reportDate?: string;
    revenue?: number;
    revenueYoy?: number;
    netProfit?: number;
    eps?: number;
    roe?: number;
    grossMargin?: number;
    netMargin?: number;
    debtRatio?: number;
  };
  fiftyTwoWeekHigh?: number;
  fiftyTwoWeekLow?: number;
  chart: Array<{
    time: string;
    open?: number;
    high?: number;
    low?: number;
    close: number;
    volume?: number;
  }>;
  source: string;
  sourceUrl: string;
  period?: '60m' | 'day' | 'week' | 'month';
}
export interface FinancialAiConnectionInput {
  provider: string;
  baseUrl: string;
  model: string;
  apiKey: string;
}
const defaultConnection = (): FinancialAiConnection => ({ mode: 'api', cli: 'codex' });
export function loadFinancialAiConnection(): FinancialAiConnection {
  try {
    return {
      ...defaultConnection(),
      ...JSON.parse(window.localStorage.getItem(CONNECTION_KEY) || '{}'),
    };
  } catch {
    return defaultConnection();
  }
}
export function saveFinancialAiConnection(value: FinancialAiConnection) {
  window.localStorage.setItem(CONNECTION_KEY, JSON.stringify(value));
}
export function clearFinancialAiConnection() {
  window.localStorage.removeItem(CONNECTION_KEY);
}
export async function purgeLegacyBrowserAiSecrets() {
  LEGACY_SECRET_KEYS.forEach((key) => window.localStorage.removeItem(key));
  await new Promise<void>((resolve) => {
    const request = window.indexedDB?.deleteDatabase('variable-global-financial-ai');
    if (!request) return resolve();
    request.onsuccess = request.onerror = request.onblocked = () => resolve();
  });
}
function requestHeaders() {
  const csrf = getUserSystemCsrfToken();
  const backendAccessKey = loadFinancialAiConnection().backendAccessKey?.trim();
  return {
    'Content-Type': 'application/json',
    ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
    ...(backendAccessKey ? { 'X-Financial-Ai-Access-Key': backendAccessKey } : {}),
  };
}
async function fetchWithSessionRecovery(input: RequestInfo | URL, init: RequestInit) {
  const response = await fetch(input, init);
  if (response.status !== 401) return response;
  const payload = (await response
    .clone()
    .json()
    .catch(() => null)) as { detail?: { code?: string } } | null;
  if (payload?.detail?.code !== 'invalid_session') return response;
  await fetch('/api/v1/auth/logout', {
    method: 'POST',
    credentials: 'include',
    headers: requestHeaders(),
  });
  return fetch(input, init);
}
export async function streamFinancialAi(
  prompt: string,
  context: unknown,
  onDelta: (value: string) => void,
  signal?: AbortSignal,
) {
  const connection = loadFinancialAiConnection();
  const response = await fetchWithSessionRecovery('/api/v1/financial-ai/chat', {
    method: 'POST',
    credentials: 'include',
    signal,
    headers: requestHeaders(),
    body: JSON.stringify({
      connection,
      prompt,
      context: JSON.stringify(context, null, 2).slice(0, 48_000),
    }),
  });
  if (!response.ok || !response.body)
    throw new Error((await response.text()) || `AI 请求失败（HTTP ${response.status}）`);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = '';
  for (;;) {
    const { done, value } = await reader.read();
    pending += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = pending.split('\n');
    pending = lines.pop() || '';
    for (const line of lines) {
      if (!line) continue;
      const event = JSON.parse(line) as { type: string; text?: string; message?: string };
      if (event.type === 'delta' && event.text) onDelta(event.text);
      if (event.type === 'error') throw new Error(event.message || 'AI 服务返回错误');
    }
    if (done) return;
  }
}
export async function testFinancialAiConnection(connection = loadFinancialAiConnection()) {
  const response = await fetchWithSessionRecovery('/api/v1/financial-ai/test-connection', {
    method: 'POST',
    credentials: 'include',
    headers: requestHeaders(),
    body: JSON.stringify(connection),
  });
  const body = (await response.json().catch(() => ({}))) as {
    ok?: boolean;
    message?: string;
    detail?: string | { message?: string };
  };
  const detail = typeof body.detail === 'string' ? body.detail : body.detail?.message;
  if (!response.ok || !body.ok)
    throw new Error(body.message || detail || `连接测试失败（HTTP ${response.status}）`);
  return body;
}
export async function getSavedFinancialAiConnection(): Promise<FinancialAiDeployment> {
  const response = await fetchWithSessionRecovery('/api/v1/financial-ai/connection', {
    credentials: 'include',
    headers: requestHeaders(),
  });
  if (!response.ok) throw new Error('读取本机 AI 配置失败');
  return response.json();
}
export async function saveFinancialAiApiConnection(value: FinancialAiConnectionInput) {
  const response = await fetchWithSessionRecovery('/api/v1/financial-ai/connection', {
    method: 'PUT',
    credentials: 'include',
    headers: requestHeaders(),
    body: JSON.stringify({
      provider: value.provider,
      base_url: value.baseUrl,
      model: value.model,
      api_key: value.apiKey || null,
    }),
  });
  const body = (await response.json().catch(() => ({}))) as FinancialAiDeployment & {
    detail?: string;
  };
  if (!response.ok) throw new Error(body.detail || '本机 AI 配置保存失败');
  return body;
}
export async function clearSavedFinancialAiConnection(): Promise<FinancialAiDeployment> {
  const response = await fetchWithSessionRecovery('/api/v1/financial-ai/connection', {
    method: 'DELETE',
    credentials: 'include',
    headers: requestHeaders(),
  });
  const body = (await response.json().catch(() => ({}))) as FinancialAiDeployment & {
    detail?: string;
  };
  if (!response.ok) throw new Error(body.detail || '本机 AI 配置清除失败');
  return body;
}
export async function getFinancialAiCapabilities(): Promise<{
  cli: AiCapability[];
  providers: AiCapability[];
  deployment: FinancialAiDeployment;
}> {
  const response = await fetchWithSessionRecovery('/api/v1/financial-ai/capabilities', {
    credentials: 'include',
    headers: requestHeaders(),
  });
  if (!response.ok) throw new Error('状态检测失败');
  return response.json();
}
export async function getNewsRadar(refresh = false): Promise<{
  generatedAt: string;
  industries: RadarIndustry[];
  partialFailures: RadarPartialFailure[];
}> {
  const response = await fetchWithSessionRecovery(
    `/api/v1/financial-ai/news-radar?refresh=${refresh}`,
    { credentials: 'include', headers: requestHeaders() },
  );
  if (!response.ok) throw new Error(`资讯雷达加载失败（HTTP ${response.status}）`);
  return response.json();
}
export async function getGlobalStock(
  symbol: string,
  period: '60m' | 'day' | 'week' | 'month' = 'day',
): Promise<GlobalStockSnapshot> {
  const response = await fetchWithSessionRecovery(
    `/api/v1/financial-ai/global-stock/${encodeURIComponent(symbol)}?period=${period}`,
    { credentials: 'include', headers: requestHeaders() },
  );
  if (!response.ok) throw new Error(`全球证券行情加载失败（HTTP ${response.status}）`);
  return response.json();
}
