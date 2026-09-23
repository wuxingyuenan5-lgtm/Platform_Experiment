import { createStrategyApi, strategyData } from './strategyApi';
import type { components } from './generated/strategy';

export type ResearchResponse = components['schemas']['ResearchResponse'];
export type ResearchScenario = components['schemas']['Scenario'];
export type ResearchExperiment = components['schemas']['Experiment'];
const api = createStrategyApi(30_000);

export async function researchCatalog() {
  return strategyData(await api.GET('/api/v1/research/strategies/catalog'));
}
export async function researchStatus() {
  return strategyData(await api.GET('/api/v1/research/strategies/data-status'));
}
export async function researchLatest(pair: string) {
  return strategyData(
    await api.GET('/api/v1/research/strategies/pairs/{pair}/latest', {
      params: { path: { pair } },
    }),
  );
}
export async function researchSeries(
  pair: string,
  from: string,
  to: string,
  view: 'all' | 'valid',
  resolution: '1s' | '15m' | '1h' | '8h' | '1d' | 'event' = '1s',
  symbol = 'BTC',
) {
  return strategyData(
    await api.GET('/api/v1/research/strategies/pairs/{pair}/series', {
      params: { path: { pair }, query: { from, to, view, resolution, symbol } },
    }),
  );
}
export async function researchFunding(
  query: {
    symbols?: string;
    search?: string;
    sort?: 'default' | 'name' | 'rate_desc' | 'rate_asc';
    from?: string;
    to?: string;
  } = {},
) {
  return strategyData(
    await api.GET('/api/v1/research/strategies/funding/board', { params: { query } }),
  );
}
export async function researchHistory(
  pair: string,
  from: string,
  to: string,
  symbol = 'BTC',
  resolution: '1h' | '8h' | '1d' = '1h',
) {
  return strategyData(
    await api.GET('/api/v1/research/strategies/pairs/{pair}/history', {
      params: { path: { pair }, query: { from, to, symbol, resolution } },
    }),
  );
}
export async function researchScenario(body: ResearchScenario) {
  return strategyData(await api.POST('/api/v1/research/strategies/scenario', { body }));
}
export async function researchRun(body: ResearchExperiment) {
  return strategyData(await api.POST('/api/v1/research/strategies/experiments', { body }));
}
export async function researchResult(run_id: string) {
  return strategyData(
    await api.GET('/api/v1/research/strategies/experiments/{run_id}', {
      params: { path: { run_id } },
    }),
  );
}
export async function researchReplay(run_id: string, event_id: string) {
  return strategyData(
    await api.GET('/api/v1/research/strategies/experiments/{run_id}/events/{event_id}/replay', {
      params: { path: { run_id, event_id } },
    }),
  );
}
export async function researchDraft(body: components['schemas']['DraftRequest']) {
  return strategyData(await api.POST('/api/v1/research/strategies/drafts', { body }));
}

export async function researchReadDraft(draft_id: string) {
  return strategyData(
    await api.GET('/api/v1/research/strategies/drafts/{draft_id}', {
      params: { path: { draft_id } },
    }),
  );
}
export async function researchCancel(run_id: string) {
  return strategyData(
    await api.POST('/api/v1/research/strategies/experiments/{run_id}/cancel', {
      params: { path: { run_id } },
    }),
  );
}
