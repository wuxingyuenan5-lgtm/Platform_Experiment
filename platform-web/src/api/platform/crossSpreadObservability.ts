import { createStrategyApi, strategyData } from './strategyApi';
import type { components } from './generated/strategy';

export type NumericValue = string | number;
export type ObservabilityState = 'complete' | 'partial' | 'unavailable';
export type ObservabilitySectionState = 'complete' | 'unavailable';
export type CrossSpreadObservabilityMode = 'fast' | 'audit';

export type VenueAccountRiskSnapshot = components['schemas']['VenueAccountRiskSnapshotResponse'];

export type VenuePositionSnapshot = components['schemas']['VenuePositionSnapshotResponse'];

export type VenueOrderSnapshot = components['schemas']['VenueOrderSnapshotResponse'];

export type VenueFillSnapshot = components['schemas']['VenueFillSnapshotResponse'];

export type CrossSpreadVenueObservability =
  components['schemas']['CrossSpreadVenueObservabilityResponse'];

export type CrossSpreadObservabilityResult =
  components['schemas']['CrossSpreadObservabilityResponse'];

const api = createStrategyApi(30_000);

export async function getCrossSpreadObservability(
  historyHours = 24,
  limit = 20,
  mode: CrossSpreadObservabilityMode = 'audit',
  signal?: AbortSignal,
): Promise<CrossSpreadObservabilityResult> {
  const response = await api.GET('/api/v1/trading/cross-spread/observability', {
    params: { query: { historyHours, limit, mode } },
    signal,
  });
  return strategyData(response);
}
