import { dataHttp, defHttp } from '@/utils/http/axios';
import {
  canonicalDecimalString,
  optionalDecimalString,
  optionalString,
  ProductDataContractError,
  requireProductList,
  requireProductRecord,
  unwrapProductPayload,
  type DecimalString,
} from '@/api/platform/productDataState';

const DATA_SERVICE = 'data-service';
const RISK_SERVICE = 'risk-service';
const NOTIFICATION_SERVICE = 'notification-service';

export interface DataAccount {
  id: number;
  name: string;
  account_type: string;
  account_address: string;
  initial_capital: DecimalString;
  parent_id?: number;
  arbitrary_flag: boolean;
  owner_id?: number;
  status: string;
  created_at: string;
  updated_at: string;
  total_asset?: DecimalString;
  available_fund?: DecimalString;
  asset_updated_at?: string;
  has_api_key?: boolean;
  has_api_secret?: boolean;
  checkCode?: string;
  platform?: string;
  accountName?: string;
}

export interface NetValuePoint {
  created_at: string;
  account_id?: number;
  total_asset: DecimalString;
  available_fund: DecimalString;
  unit_net_worth: DecimalString;
  current_drawdown: DecimalString;
}

export interface SyncResult {
  account_id: number;
  account_name: string;
  account_type?: string;
  total_asset: DecimalString;
  available_fund: DecimalString;
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
  total_asset: DecimalString;
  available_fund: DecimalString;
  synced_at: string;
  update_frequency: string;
  results: SyncResult[];
}

export interface DataServiceHealth {
  status: string;
  service: string;
  update_frequency: string;
  as_of?: string;
}

export interface TotalAssetSummary {
  total_asset?: DecimalString;
  total?: DecimalString;
  updated_at?: string;
}

export interface ProductRatioItem {
  name: string;
  value: DecimalString;
  valueUSD?: DecimalString;
  percent: DecimalString;
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
  rate?: DecimalString;
  symbol?: string;
  updated_at?: string;
}

function recordList(
  payload: unknown,
  source: string,
  aliases: string[] = [],
): Record<string, unknown>[] {
  const unwrapped = unwrapProductPayload(payload, source);
  if (Array.isArray(unwrapped)) {
    return unwrapped.map((item, index) => {
      if (item === null || typeof item !== 'object' || Array.isArray(item)) {
        throw new ProductDataContractError(
          'provider_invalid_payload',
          `${source}第${index + 1}项不是有效对象`,
          source,
        );
      }
      return item as Record<string, unknown>;
    });
  }
  if (unwrapped !== null && typeof unwrapped === 'object') {
    const record = unwrapped as Record<string, unknown>;
    for (const alias of aliases) {
      if (alias in record) return recordList(record[alias], source);
    }
  }
  requireProductList(unwrapped, source);
  return [];
}

function integerValue(value: unknown, field: string, source: string): number {
  if (typeof value !== 'number' || !Number.isInteger(value)) {
    throw new ProductDataContractError(
      'provider_invalid_integer',
      `${source}字段${field}不是有效整数`,
      source,
    );
  }
  return value;
}

function booleanValue(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

function stringValue(value: unknown, field: string, source: string): string {
  const result = optionalString(value);
  if (!result) {
    throw new ProductDataContractError(
      'provider_invalid_string',
      `${source}字段${field}为空`,
      source,
    );
  }
  return result;
}

function normalizeAccount(value: Record<string, unknown>): DataAccount {
  return {
    id: integerValue(value.id, 'id', DATA_SERVICE),
    name: stringValue(value.name, 'name', DATA_SERVICE),
    account_type: stringValue(value.account_type, 'account_type', DATA_SERVICE),
    account_address: optionalString(value.account_address) || '',
    initial_capital: canonicalDecimalString(
      value.initial_capital ?? '0',
      'initial_capital',
      DATA_SERVICE,
    ),
    parent_id: typeof value.parent_id === 'number' ? value.parent_id : undefined,
    arbitrary_flag: booleanValue(value.arbitrary_flag),
    owner_id: typeof value.owner_id === 'number' ? value.owner_id : undefined,
    status: optionalString(value.status) || 'unknown',
    created_at: optionalString(value.created_at) || '',
    updated_at: optionalString(value.updated_at) || '',
    total_asset: optionalDecimalString(value.total_asset, 'total_asset', DATA_SERVICE),
    available_fund: optionalDecimalString(value.available_fund, 'available_fund', DATA_SERVICE),
    asset_updated_at: optionalString(value.asset_updated_at),
    has_api_key: typeof value.has_api_key === 'boolean' ? value.has_api_key : undefined,
    has_api_secret: typeof value.has_api_secret === 'boolean' ? value.has_api_secret : undefined,
    checkCode: optionalString(value.checkCode),
    platform: optionalString(value.platform),
    accountName: optionalString(value.accountName),
  };
}

function normalizeNetValue(value: Record<string, unknown>): NetValuePoint {
  return {
    created_at: stringValue(value.created_at, 'created_at', DATA_SERVICE),
    account_id: typeof value.account_id === 'number' ? value.account_id : undefined,
    total_asset: canonicalDecimalString(value.total_asset, 'total_asset', DATA_SERVICE),
    available_fund: canonicalDecimalString(value.available_fund, 'available_fund', DATA_SERVICE),
    unit_net_worth: canonicalDecimalString(value.unit_net_worth, 'unit_net_worth', DATA_SERVICE),
    current_drawdown: canonicalDecimalString(
      value.current_drawdown,
      'current_drawdown',
      DATA_SERVICE,
    ),
  };
}

function normalizeSyncResult(value: Record<string, unknown>): SyncResult {
  return {
    account_id: integerValue(value.account_id, 'account_id', DATA_SERVICE),
    account_name: stringValue(value.account_name, 'account_name', DATA_SERVICE),
    account_type: optionalString(value.account_type),
    total_asset: canonicalDecimalString(value.total_asset, 'total_asset', DATA_SERVICE),
    available_fund: canonicalDecimalString(value.available_fund, 'available_fund', DATA_SERVICE),
    synced_at: stringValue(value.synced_at, 'synced_at', DATA_SERVICE),
    update_frequency: optionalString(value.update_frequency) || 'unknown',
    data_source: optionalString(value.data_source) || DATA_SERVICE,
    status: optionalString(value.status),
    message: optionalString(value.message),
  };
}

export function getDataHealth() {
  return dataHttp.get({ url: '/health' }).then((payload) => {
    const value = requireProductRecord(payload, DATA_SERVICE);
    return {
      status: stringValue(value.status, 'status', DATA_SERVICE),
      service: optionalString(value.service) || DATA_SERVICE,
      update_frequency: optionalString(value.update_frequency) || 'unknown',
      as_of: optionalString(value.as_of ?? value.updated_at),
    } satisfies DataServiceHealth;
  });
}

export function getAccounts() {
  return dataHttp
    .get({ url: '/api/v1/accounts' })
    .then((payload) => recordList(payload, DATA_SERVICE, ['items', 'list']).map(normalizeAccount));
}

export function createAccount(data: Partial<DataAccount>) {
  return dataHttp
    .post({ url: '/api/v1/accounts', data })
    .then((payload) => normalizeAccount(requireProductRecord(payload, DATA_SERVICE)));
}

export function deleteAccount(id: number) {
  return dataHttp
    .delete({ url: `/api/v1/accounts/${id}` })
    .then((payload) => requireProductRecord(payload, DATA_SERVICE));
}

export function triggerAccountSync() {
  return dataHttp.post({ url: '/api/v1/data/sync' }).then((payload) => {
    const value = requireProductRecord(payload, DATA_SERVICE);
    return {
      synced: integerValue(value.synced, 'synced', DATA_SERVICE),
      failed: integerValue(value.failed, 'failed', DATA_SERVICE),
      skipped: integerValue(value.skipped, 'skipped', DATA_SERVICE),
      total_asset: canonicalDecimalString(value.total_asset, 'total_asset', DATA_SERVICE),
      available_fund: canonicalDecimalString(value.available_fund, 'available_fund', DATA_SERVICE),
      synced_at: stringValue(value.synced_at, 'synced_at', DATA_SERVICE),
      update_frequency: optionalString(value.update_frequency) || 'unknown',
      results: recordList(value.results, DATA_SERVICE).map(normalizeSyncResult),
    } satisfies SyncAccountsResult;
  });
}

export function getTotalAssetSummary() {
  return dataHttp.get({ url: '/api/v1/data/total' }).then((payload) => {
    const value = requireProductRecord(payload, DATA_SERVICE);
    return {
      total_asset: optionalDecimalString(value.total_asset, 'total_asset', DATA_SERVICE),
      total: optionalDecimalString(value.total, 'total', DATA_SERVICE),
      updated_at: optionalString(value.updated_at),
    } satisfies TotalAssetSummary;
  });
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
    .then((payload) => recordList(payload, DATA_SERVICE, ['items', 'list']).map(normalizeNetValue));
}

export function getProductRatio() {
  return dataHttp.get({ url: '/product/nav/productRatio' }).then((payload) =>
    recordList(payload, DATA_SERVICE, ['items', 'list']).map((value) => ({
      name: stringValue(value.name, 'name', DATA_SERVICE),
      value: canonicalDecimalString(value.value, 'value', DATA_SERVICE),
      valueUSD: optionalDecimalString(value.valueUSD, 'valueUSD', DATA_SERVICE),
      percent: canonicalDecimalString(value.percent, 'percent', DATA_SERVICE),
    })),
  );
}

export function getExchangeInfo(params?: Record<string, unknown>) {
  return dataHttp.get({ url: '/exchange/', params }).then((payload) => {
    const value = requireProductRecord(payload, DATA_SERVICE);
    return {
      rate: optionalDecimalString(value.rate, 'rate', DATA_SERVICE),
      symbol: optionalString(value.symbol),
      updated_at: optionalString(value.updated_at),
    } satisfies ExchangeInfo;
  });
}

export function getRiskRecordList(params?: Record<string, unknown>) {
  return defHttp.get({ url: '/risk/api/v1/risk-records/', params }).then((payload) =>
    recordList(payload, RISK_SERVICE, ['items', 'list']).map((value) => ({
      id: typeof value.id === 'number' ? value.id : undefined,
      title: optionalString(value.title),
      content: optionalString(value.content),
      status: optionalString(value.status),
      severity: optionalString(value.severity),
      created_at: optionalString(value.created_at),
    })),
  );
}

export function getNotificationList(params?: Record<string, unknown>) {
  return defHttp.get({ url: '/notifications/api/v1/messages/', params }).then((payload) =>
    recordList(payload, NOTIFICATION_SERVICE, ['items', 'list']).map((value) => ({
      id:
        typeof value.id === 'number' || typeof value.id === 'string'
          ? value.id
          : undefined,
      message_id:
        typeof value.message_id === 'number' || typeof value.message_id === 'string'
          ? value.message_id
          : undefined,
      title: optionalString(value.title),
      subject: optionalString(value.subject),
      content: optionalString(value.content),
      message: optionalString(value.message),
      description: optionalString(value.description),
      status: optionalString(value.status),
      read: typeof value.read === 'boolean' ? value.read : undefined,
      isRead: typeof value.isRead === 'boolean' ? value.isRead : undefined,
      created_at: optionalString(value.created_at),
      createdAt: optionalString(value.createdAt),
    })),
  );
}
