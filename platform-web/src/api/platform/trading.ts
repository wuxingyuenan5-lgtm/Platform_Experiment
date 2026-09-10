import axios from 'axios';
import { createStrategyApi, strategyData } from './strategyApi';
import { fetchStrategyQuery } from './strategyQueries';

import type {
  AccountResult,
  BalanceResult,
  EquityHistoryPointResult,
  CreateExecutionBatchInput,
  CredentialReferenceResult,
  CrossSpreadHistoryPointResult,
  CrossSpreadMarketCommandInput,
  CrossSpreadSnapshotResult,
  ExchangeConnectivityResult,
  ExecutionBatchResult,
  FillResult,
  InstrumentResult,
  OrderDetailResult,
  OrderResult,
  PnlResult,
  PositionResult,
  ReconciliationSummaryResult,
  RuntimeReadinessResult,
  LiveTradingSessionResult,
  StrategyAccountBindingResult,
  StrategyAccountSnapshotResult,
  StrategyDefinitionResult,
  StrategyInstanceResult,
  StrategyManagementOverviewResult,
  StrategyNavSnapshotResult,
  StrategyPnlResult,
  StrategyRunResult,
  StrategyV1ReadinessResult,
  TradingSafetyResult,
  TradingSnapshot,
} from './trading.types';

const api = createStrategyApi();

function isNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

export async function reconcileTradingOrder(orderId: string): Promise<OrderResult> {
  const response = await api.POST('/api/v1/trading/orders/{order_id}/reconcile', {
    params: { path: { order_id: orderId } },
  });
  return strategyData(response);
}

export async function createExecutionBatch(
  input: CreateExecutionBatchInput,
): Promise<ExecutionBatchResult> {
  const response = await api.POST('/api/v1/trading/execution-batches', { body: input });
  return strategyData(response);
}

export async function getExecutionBatch(batchId: string): Promise<ExecutionBatchResult> {
  const response = await api.GET('/api/v1/trading/execution-batches/{batch_id}', {
    params: { path: { batch_id: batchId } },
  });
  return strategyData(response);
}

export async function getExecutionBatches(
  strategyInstanceId?: string,
): Promise<ExecutionBatchResult[]> {
  const response = await api.GET('/api/v1/trading/execution-batches', {
    params: { query: strategyInstanceId ? { strategyInstanceId } : undefined },
  });
  return strategyData(response);
}

export async function getTradingPosition(
  accountId: string,
  instrumentId: string,
): Promise<PositionResult | null> {
  try {
    const response = await api.GET('/api/v1/accounts/{account_id}/positions/{instrument_id}', {
      params: { path: { account_id: accountId, instrument_id: instrumentId } },
    });
    return strategyData(response);
  } catch (error) {
    if (isNotFound(error)) return null;
    throw error;
  }
}

export async function getTradingPnl(
  accountId: string,
  instrumentId: string,
): Promise<PnlResult | null> {
  try {
    const response = await api.GET('/api/v1/accounts/{account_id}/pnl/{instrument_id}', {
      params: { path: { account_id: accountId, instrument_id: instrumentId } },
    });
    return strategyData(response);
  } catch (error) {
    if (isNotFound(error)) return null;
    throw error;
  }
}

export async function getAccountBalanceLatest(accountId: string): Promise<BalanceResult | null> {
  return fetchStrategyQuery(['account-balance', accountId], async (signal) => {
    try {
      return strategyData(
        await api.GET('/api/v1/accounts/{account_id}/balances/latest', {
          params: { path: { account_id: accountId } },
          signal,
        }),
      );
    } catch (error) {
      if (isNotFound(error)) return null;
      throw error;
    }
  });
}

export async function getEquityHistory(
  accountId: string,
  currency?: string,
): Promise<EquityHistoryPointResult[]> {
  return fetchStrategyQuery(['equity-history', accountId, currency], async (signal) =>
    strategyData(
      await api.GET('/api/v1/accounts/{account_id}/equity-history', {
        params: { path: { account_id: accountId }, query: { currency } },
        signal,
      }),
    ),
  );
}

export async function getTradingSnapshot(
  accountId: string,
  instrumentId: string,
): Promise<TradingSnapshot> {
  const [position, pnl] = await Promise.all([
    getTradingPosition(accountId, instrumentId),
    getTradingPnl(accountId, instrumentId),
  ]);
  return { position, pnl };
}

export async function getRuntimeReadiness(): Promise<RuntimeReadinessResult> {
  const response = await api.GET('/api/v1/system/runtime-readiness');
  return strategyData(response);
}

export async function getReconciliationSummary(): Promise<ReconciliationSummaryResult> {
  const response = await api.GET('/api/v1/ops/reconciliation-summary');
  return strategyData(response);
}

export async function getTradingSafety(): Promise<TradingSafetyResult> {
  const response = await api.GET('/api/v1/security/trading-safety');
  return strategyData(response);
}

export async function getCredentialReferences(): Promise<CredentialReferenceResult[]> {
  const response = await api.GET('/api/v1/security/credential-references');
  return strategyData(response);
}

export async function getExchangeConnectivity(): Promise<ExchangeConnectivityResult> {
  const response = await api.GET('/api/v1/security/exchange-connectivity');
  return strategyData(response);
}

export async function getCrossSpreadSnapshot(): Promise<CrossSpreadSnapshotResult> {
  const response = await api.GET('/api/v1/trading/cross-spread/snapshot');
  return strategyData(response);
}

export async function getCrossSpreadHistory(limit = 200): Promise<CrossSpreadHistoryPointResult[]> {
  const response = await api.GET('/api/v1/trading/cross-spread/history', {
    params: { query: { limit } },
  });
  return strategyData(response);
}

export async function submitCrossSpreadMarketCommand(
  input: CrossSpreadMarketCommandInput,
): Promise<ExecutionBatchResult> {
  const response = await api.POST('/api/v1/trading/cross-spread/market-command', { body: input });
  return strategyData(response);
}

export async function getStrategyDefinitions(): Promise<StrategyDefinitionResult[]> {
  const response = await api.GET('/api/v1/strategies/definitions');
  return strategyData(response);
}

export async function getStrategyInstances(): Promise<StrategyInstanceResult[]> {
  const response = await api.GET('/api/v1/strategies/instances');
  return strategyData(response);
}

export async function getStrategyManagementOverview(
  signal?: AbortSignal,
): Promise<StrategyManagementOverviewResult[]> {
  const response = await api.GET('/api/v1/strategies/management-overview', { signal });
  return strategyData(response);
}

export async function getStrategyAccountBindings(
  strategyInstanceId: string,
): Promise<StrategyAccountBindingResult[]> {
  const response = await api.GET('/api/v1/strategies/instances/{strategy_instance_id}/accounts', {
    params: { path: { strategy_instance_id: strategyInstanceId } },
  });
  return strategyData(response);
}

export async function getStrategyAccountSnapshot(
  strategyInstanceId: string,
  accountId?: string,
  signal?: AbortSignal,
): Promise<StrategyAccountSnapshotResult> {
  const response = await api.GET(
    '/api/v1/strategies/instances/{strategy_instance_id}/account-snapshot',
    {
      params: {
        path: { strategy_instance_id: strategyInstanceId },
        query: accountId ? { accountId } : undefined,
      },
      signal,
    },
  );
  return strategyData(response);
}

export async function getStrategyRuns(strategyInstanceId: string): Promise<StrategyRunResult[]> {
  const response = await api.GET('/api/v1/strategies/instances/{strategy_instance_id}/runs', {
    params: { path: { strategy_instance_id: strategyInstanceId } },
  });
  return strategyData(response);
}

export async function getStrategyV1Readiness(
  strategyInstanceId: string,
): Promise<StrategyV1ReadinessResult> {
  const response = await api.GET(
    '/api/v1/strategies/instances/{strategy_instance_id}/v1-readiness',
    { params: { path: { strategy_instance_id: strategyInstanceId } } },
  );
  return strategyData(response);
}

export async function getLiveTradingSessions(): Promise<LiveTradingSessionResult[]> {
  const response = await api.GET('/api/v1/live-trading/sessions');
  return strategyData(response);
}

export async function createLiveTradingSession(input: {
  idempotencyKey: string;
  sessionType: 'minimum_size_acceptance' | 'existing_limits' | 'scale_change';
  strategyInstanceId: string;
  accountId: string;
  symbols: string[];
  sides: Array<'buy' | 'sell'>;
  orderTypes: Array<'market' | 'limit'>;
  startsAt: string;
  endsAt: string;
  maxOrderNotional: string;
  maxDailyNotional: string;
  readOnlyVerifiedAt: string;
  evidenceReference: string;
  reason: string;
}): Promise<LiveTradingSessionResult> {
  const response = await api.POST('/api/v1/live-trading/sessions', { body: input });
  return strategyData(response);
}

export async function approveLiveTradingSession(
  sessionId: string,
  reason: string,
): Promise<LiveTradingSessionResult> {
  const response = await api.POST('/api/v1/live-trading/sessions/{session_id}/approve', {
    params: { path: { session_id: sessionId } },
    body: { reason },
  });
  return strategyData(response);
}

export async function revokeLiveTradingSession(
  sessionId: string,
  reason: string,
): Promise<LiveTradingSessionResult> {
  const response = await api.POST('/api/v1/live-trading/sessions/{session_id}/revoke', {
    params: { path: { session_id: sessionId } },
    body: { reason },
  });
  return strategyData(response);
}

export async function getAccounts(): Promise<AccountResult[]> {
  const response = await api.GET('/api/v1/accounts');
  return strategyData(response);
}

export async function getInstruments(): Promise<InstrumentResult[]> {
  const response = await api.GET('/api/v1/instruments');
  return strategyData(response);
}

export async function getOrders(strategyInstanceId?: string): Promise<OrderDetailResult[]> {
  return fetchStrategyQuery(['orders', strategyInstanceId], async (signal) =>
    strategyData(
      await api.GET('/api/v1/trading/orders', {
        params: { query: { strategyInstanceId } },
        signal,
      }),
    ),
  );
}

export async function getFills(strategyInstanceId?: string): Promise<FillResult[]> {
  return fetchStrategyQuery(['fills', strategyInstanceId], async (signal) =>
    strategyData(
      await api.GET('/api/v1/trading/fills', {
        params: { query: { strategyInstanceId } },
        signal,
      }),
    ),
  );
}

export async function getStrategyPnl(strategyInstanceId: string): Promise<StrategyPnlResult> {
  const response = await api.GET('/api/v1/strategies/instances/{strategy_instance_id}/pnl', {
    params: { path: { strategy_instance_id: strategyInstanceId } },
  });
  return strategyData(response);
}

export async function getStrategyNavSnapshots(
  strategyInstanceId: string,
): Promise<StrategyNavSnapshotResult[]> {
  const response = await api.GET(
    '/api/v1/strategies/instances/{strategy_instance_id}/nav-snapshots',
    { params: { path: { strategy_instance_id: strategyInstanceId } } },
  );
  return strategyData(response);
}
