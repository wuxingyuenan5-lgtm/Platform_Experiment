import Decimal from 'decimal.js';

export type DecimalString = string;
export type ProductDataStatus =
  | 'ready'
  | 'no_data'
  | 'unavailable'
  | 'stale'
  | 'not_configured'
  | 'unsupported';

export interface ProductDataMeta {
  status: ProductDataStatus;
  source: string;
  asOf?: string;
  timezone?: string;
  currency?: string;
  unit?: string;
  precision?: string;
  freshness?: string;
  errorCode?: string;
  message?: string;
  degraded?: boolean;
  fallbackSource?: string;
}

export interface ProductDataResult<T> {
  data: T;
  meta: ProductDataMeta;
}

export class ProductDataContractError extends Error {
  readonly code: string;
  readonly source: string;

  constructor(code: string, message: string, source: string) {
    super(message);
    this.name = 'ProductDataContractError';
    this.code = code;
    this.source = source;
  }
}

export function unwrapProductPayload(payload: unknown, source: string): unknown {
  if (payload === null || payload === undefined) {
    throw new ProductDataContractError('provider_empty_payload', `${source}未返回数据`, source);
  }
  if (typeof payload !== 'object') return payload;

  const value = payload as Record<string, unknown>;
  const retCode = value.retCode;
  const code = value.code;
  if (typeof retCode === 'number' && retCode !== 0) {
    throw new ProductDataContractError(
      'provider_error_response',
      `${source}返回错误状态 ${retCode}`,
      source,
    );
  }
  if (typeof code === 'number' && code !== 0) {
    throw new ProductDataContractError(
      'provider_error_response',
      `${source}返回错误状态 ${code}`,
      source,
    );
  }
  if ('data' in value) return value.data;
  if ('result' in value) return value.result;
  return payload;
}

export function requireProductRecord(payload: unknown, source: string): Record<string, unknown> {
  const value = unwrapProductPayload(payload, source);
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new ProductDataContractError(
      'provider_invalid_payload',
      `${source}返回了无效对象`,
      source,
    );
  }
  return value as Record<string, unknown>;
}

export function requireProductList(payload: unknown, source: string): unknown[] {
  const value = unwrapProductPayload(payload, source);
  if (!Array.isArray(value)) {
    throw new ProductDataContractError(
      'provider_invalid_payload',
      `${source}返回了无效列表`,
      source,
    );
  }
  return value;
}

export function canonicalDecimalString(
  value: unknown,
  field: string,
  source: string,
): DecimalString {
  if (typeof value !== 'string' && typeof value !== 'number') {
    throw new ProductDataContractError(
      'provider_invalid_decimal',
      `${source}字段${field}不是有效Decimal`,
      source,
    );
  }
  const raw = typeof value === 'string' ? value.trim() : String(value);
  if (!raw) {
    throw new ProductDataContractError(
      'provider_invalid_decimal',
      `${source}字段${field}为空`,
      source,
    );
  }
  try {
    const decimal = new Decimal(raw);
    if (!decimal.isFinite()) throw new Error('not finite');
    return decimal.toFixed();
  } catch {
    throw new ProductDataContractError(
      'provider_invalid_decimal',
      `${source}字段${field}不是有效Decimal`,
      source,
    );
  }
}

export function optionalDecimalString(
  value: unknown,
  field: string,
  source: string,
): DecimalString | undefined {
  if (value === null || value === undefined || value === '') return undefined;
  return canonicalDecimalString(value, field, source);
}

export function optionalString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

export function unavailableMeta(
  source: string,
  error: unknown,
  overrides: Partial<ProductDataMeta> = {},
): ProductDataMeta {
  const contractError = error instanceof ProductDataContractError ? error : undefined;
  return {
    status: 'unavailable',
    source,
    errorCode: contractError?.code || 'request_failed',
    message: error instanceof Error ? error.message : `${source}暂时不可用`,
    degraded: false,
    ...overrides,
  };
}

export function notConfiguredMeta(
  source: string,
  message = '该正式页面尚未配置生产数据源',
): ProductDataMeta {
  return {
    status: 'not_configured',
    source,
    errorCode: 'data_source_not_configured',
    message,
    degraded: false,
  };
}
