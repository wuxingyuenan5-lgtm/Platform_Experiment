export type ProductDataState = 'live' | 'sample' | 'unavailable' | 'error';

export interface ProductDataEnvelope<T> {
  data: T | null;
  state: ProductDataState;
  source: string;
  asOf: string | null;
  actionable: boolean;
  message?: string;
}

export function productDataEnvelope<T>(
  value: ProductDataEnvelope<T>,
): ProductDataEnvelope<T> {
  if (value.state === 'sample' && value.actionable) {
    throw new Error('sample product data must not be actionable');
  }
  return Object.freeze({ ...value });
}
