import { dataHttp, defHttp } from '@/utils/http/axios';

export interface DataAccount {
  id: number;
  name: string;
  account_type: string;
  account_address: string;
  initial_capital: number;
  parent_id?: number;
  arbitrary_flag: boolean;
  owner_id?: number;
  status: string;
  created_at: string;
  updated_at: string;
  total_asset?: number;
  available_fund?: number;
  asset_updated_at?: string;
  api_key?: string;
  api_secret?: string;
  has_api_key?: boolean;
  has_api_secret?: boolean;
  checkCode?: string;
  platform?: string;
  accountName?: string;
}

export interface NetValuePoint {
  created_at: string;
  account_id?: number;
  total_asset: number;
  available_fund: number;
  unit_net_worth: number;
  current_drawdown: number;
}

export interface SyncResult {
  account_id: number;
  account_name: string;
  account_type?: string;
  total_asset: number;
  available_fund: number;
  synced_at: string;
  update_frequency: string;
  data_source: string;
  status?: string;
  message?: string;
}

export interface SyncAccountsResult {
  synced: number;
  failed: number;
  skipped: number;
  total_asset: number;
  available_fund: number;
  synced_at: string;
  update_frequency: string;
  results: SyncResult[];
}

export interface DataServiceHealth {
  status: string;
  service: string;
  update_frequency: string;
}

export interface TotalAssetSummary {
  total_asset?: number;
  total?: number;
  updated_at?: string;
}

export interface ProductRatioItem {
  name: string;
  value: number;
  valueUSD?: number;
  percent: number;
}

export interface RiskRecord {
  id?: number;
  title?: string;
  content?: string;
  status?: string;
  severity?: string;
  created_at?: string;
}

export interface NotificationMessage {
  id?: number | string;
  message_id?: number | string;
  title?: string;
  subject?: string;
  content?: string;
  message?: string;
  description?: string;
  status?: string;
  read?: boolean;
  isRead?: boolean;
  created_at?: string;
  createdAt?: string;
}

export interface ExchangeInfo {
  rate?: number;
  symbol?: string;
  updated_at?: string;
}

function unwrap<T>(payload: any, fallback: T): T {
  if (!payload) return fallback;
  if (payload.retCode === 0 && 'data' in payload) return payload.data as T;
  if (payload.code === 0 && 'data' in payload) return payload.data as T;
  if ('result' in payload) return payload.result as T;
  if ('data' in payload) return payload.data as T;
  return payload as T;
}

export function getDataHealth() {
  return dataHttp.get({ url: '/health' }).then((res) => unwrap<DataServiceHealth>(res, {
    status: 'unknown',
    service: 'data-service',
    update_frequency: '-',
  }));
}

export function getAccounts() {
  return dataHttp.get({ url: '/api/v1/accounts' }).then((res) => unwrap<DataAccount[]>(res, []));
}

export function createAccount(data: Partial<DataAccount>) {
  return dataHttp.post({ url: '/api/v1/accounts', data }).then((res) => unwrap<DataAccount>(res, {} as DataAccount));
}

export function deleteAccount(id: number) {
  return dataHttp.delete({ url: `/api/v1/accounts/${id}` }).then((res) => unwrap<any>(res, {}));
}

export function triggerAccountSync() {
  return dataHttp
    .post({ url: '/api/v1/data/sync' })
    .then((res) => unwrap<SyncAccountsResult>(res, {} as SyncAccountsResult));
}

export function getTotalAssetSummary() {
  return dataHttp.get({ url: '/api/v1/data/total' }).then((res) => unwrap<TotalAssetSummary>(res, {}));
}

export function getNetValueHistory(params?: {
  account_id?: number;
  accountId?: number;
  checkCode?: string;
  platform?: string;
  limit?: number;
  sample_minutes?: number;
  sampleMinutes?: number;
  from?: string;
  to?: string;
}) {
  return dataHttp
    .get({ url: '/api/v1/data/net-value', params })
    .then((res) => unwrap<NetValuePoint[]>(res, []));
}

export function getProductRatio() {
  return dataHttp
    .get({ url: '/product/nav/productRatio' })
    .then((res) => unwrap<ProductRatioItem[]>(res, []));
}

export function getExchangeInfo(params?: any) {
  return dataHttp
    .get({ url: '/exchange/', params })
    .then((res) => unwrap<ExchangeInfo>(res, {}));
}

export function getRiskRecordList(params?: any) {
  return defHttp.get({ url: '/risk/api/v1/risk-records/', params }).then((res) => {
    const data = unwrap<any>(res, {});
    if (Array.isArray(data)) return data as RiskRecord[];
    if (Array.isArray(data.items)) return data.items as RiskRecord[];
    if (Array.isArray(data.list)) return data.list as RiskRecord[];
    return [] as RiskRecord[];
  });
}

export function getNotificationList(params?: any) {
  return defHttp.get({ url: '/notifications/api/v1/messages/', params }).then((res) => {
    const data = unwrap<any>(res, {});
    if (Array.isArray(data)) return data as NotificationMessage[];
    if (Array.isArray(data.items)) return data.items as NotificationMessage[];
    return [] as NotificationMessage[];
  });
}
