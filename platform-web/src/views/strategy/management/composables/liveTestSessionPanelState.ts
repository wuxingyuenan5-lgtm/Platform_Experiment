import type { FundingExecutionContext } from '@/api/platform/fundingWorkspace';
import type { CrossSpreadObservabilityResult } from '@/api/platform/crossSpreadObservability';
import type {
  LiveTradingSessionResult,
  StrategyAccountBindingResult,
  StrategyManagementOverviewResult,
  TradingSafetyResult,
} from '@/api/platform/trading.types';

export interface LiveTestSessionTarget {
  targetKey: string;
  strategyLabel: 'Funding' | 'Cross';
  strategyInstanceId: string;
  role: string;
  accountId: string | null;
  accountCode: string | null;
  symbols: string[];
  symbolText: string;
  symbolSource: 'funding_execution_context' | 'cross_observability';
  missingReason: string | null;
}

export interface LiveTestPanelForm {
  expiryMinutes: string;
  maxOrderNotional: string;
  maxDailyNotional: string;
}

export interface StrategySessionView {
  strategyLabel: 'Funding' | 'Cross';
  coverageStatus: 'not_created' | 'pending' | 'approved' | 'revoked_or_expired' | 'blocked';
  ready: boolean;
  missingAccounts: string[];
  blockers: string[];
  sessionLabels: string[];
}

function normalizeSymbols(symbols: string[]): string[] {
  return Array.from(
    new Set(
      symbols
        .map((value) => value.trim())
        .filter(Boolean)
        .map((value) => value.toUpperCase()),
    ),
  ).sort();
}

function sameSymbols(left: string[], right: string[]): boolean {
  return JSON.stringify(normalizeSymbols(left)) === JSON.stringify(normalizeSymbols(right));
}

function firstActiveBinding(
  bindings: StrategyAccountBindingResult[],
  role: string,
): StrategyAccountBindingResult | null {
  return bindings.find((item) => item.role === role && item.status === 'active') ?? null;
}

function latestSessionForTarget(
  sessions: LiveTradingSessionResult[],
  target: LiveTestSessionTarget,
): LiveTradingSessionResult | null {
  const matches = sessions.filter(
    (item) =>
      item.strategyInstanceId === target.strategyInstanceId &&
      item.accountId === target.accountId &&
      sameSymbols(item.symbols, target.symbols),
  );
  if (!matches.length) return null;
  return [...matches].sort((left, right) => right.createdAt.localeCompare(left.createdAt))[0];
}

export function deriveLiveTestSessionTargets(options: {
  selectedFunding: boolean;
  selectedCross: boolean;
  fundingOverview: StrategyManagementOverviewResult | null;
  crossOverview: StrategyManagementOverviewResult | null;
  fundingBindings: StrategyAccountBindingResult[];
  crossBindings: StrategyAccountBindingResult[];
  fundingContext: FundingExecutionContext | null;
  crossObservability: CrossSpreadObservabilityResult | null;
}): LiveTestSessionTarget[] {
  const targets: LiveTestSessionTarget[] = [];

  if (options.selectedFunding && options.fundingOverview?.strategyInstanceId) {
    const binding = firstActiveBinding(options.fundingBindings, 'primary');
    const symbols = normalizeSymbols([
      options.fundingContext?.spotSymbol || '',
      options.fundingContext?.perpetualSymbol || '',
    ]);
    targets.push({
      targetKey: 'funding:primary',
      strategyLabel: 'Funding',
      strategyInstanceId: options.fundingOverview.strategyInstanceId,
      role: 'primary',
      accountId: binding?.accountId ?? null,
      accountCode: binding?.accountCode ?? null,
      symbols,
      symbolText: symbols.join(' / '),
      symbolSource: 'funding_execution_context',
      missingReason:
        binding == null
          ? 'Funding primary 账户绑定缺失'
          : symbols.length === 2
          ? null
          : 'Funding Spot/Perpetual 权威 Symbol 未就绪',
    });
  }

  if (options.selectedCross && options.crossOverview?.strategyInstanceId) {
    const bybitBinding = firstActiveBinding(options.crossBindings, 'venue_a');
    const bybitSymbol = normalizeSymbols([String(options.crossObservability?.bybit?.symbol || '')]);
    targets.push({
      targetKey: 'cross:venue_a',
      strategyLabel: 'Cross',
      strategyInstanceId: options.crossOverview.strategyInstanceId,
      role: 'venue_a',
      accountId: bybitBinding?.accountId ?? null,
      accountCode: bybitBinding?.accountCode ?? null,
      symbols: bybitSymbol,
      symbolText: bybitSymbol.join(', '),
      symbolSource: 'cross_observability',
      missingReason:
        bybitBinding == null
          ? 'Cross Bybit 账户绑定缺失'
          : bybitSymbol.length === 1
          ? null
          : 'Cross Bybit 权威 Symbol 未就绪',
    });

    const mt5Binding = firstActiveBinding(options.crossBindings, 'mt5_leg');
    const mt5Symbol = normalizeSymbols([String(options.crossObservability?.mt5?.symbol || '')]);
    targets.push({
      targetKey: 'cross:mt5_leg',
      strategyLabel: 'Cross',
      strategyInstanceId: options.crossOverview.strategyInstanceId,
      role: 'mt5_leg',
      accountId: mt5Binding?.accountId ?? null,
      accountCode: mt5Binding?.accountCode ?? null,
      symbols: mt5Symbol,
      symbolText: mt5Symbol.join(', '),
      symbolSource: 'cross_observability',
      missingReason:
        mt5Binding == null
          ? 'Cross MT5 账户绑定缺失'
          : mt5Symbol.length === 1
          ? null
          : 'Cross MT5 实际 Broker Symbol 未就绪',
    });
  }

  return targets;
}

export function buildLiveTradingSessionPayload(
  target: LiveTestSessionTarget,
  form: LiveTestPanelForm,
) {
  const now = new Date();
  const startsAt = new Date(now.getTime() + 60_000);
  const endsAt = new Date(startsAt.getTime() + Number(form.expiryMinutes || '15') * 60_000);
  const readOnlyVerifiedAt = new Date(now.getTime() - 5 * 60_000);
  return {
    idempotencyKey: `live-session:${target.strategyInstanceId}:${
      target.accountId
    }:${target.symbols.join('|')}:${form.expiryMinutes}:${form.maxOrderNotional}:${
      form.maxDailyNotional
    }`,
    sessionType: 'minimum_size_acceptance' as const,
    strategyInstanceId: target.strategyInstanceId,
    accountId: String(target.accountId || ''),
    symbols: normalizeSymbols(target.symbols),
    sides: ['buy', 'sell'] as Array<'buy' | 'sell'>,
    orderTypes: ['market', 'limit'] as Array<'market' | 'limit'>,
    startsAt: startsAt.toISOString(),
    endsAt: endsAt.toISOString(),
    maxOrderNotional: form.maxOrderNotional,
    maxDailyNotional: form.maxDailyNotional,
    readOnlyVerifiedAt: readOnlyVerifiedAt.toISOString(),
    evidenceReference: 'ui://strategy-management/live-test-session',
    reason: 'CEO controlled-live test session',
  };
}

export function findReusableLiveSession(
  sessions: LiveTradingSessionResult[],
  target: LiveTestSessionTarget,
  form: LiveTestPanelForm,
): LiveTradingSessionResult | null {
  return (
    sessions.find(
      (item) =>
        item.strategyInstanceId === target.strategyInstanceId &&
        item.accountId === target.accountId &&
        sameSymbols(item.symbols, target.symbols) &&
        item.sessionType === 'minimum_size_acceptance' &&
        item.maxOrderNotional === form.maxOrderNotional &&
        item.maxDailyNotional === form.maxDailyNotional &&
        (item.status === 'pending' || item.status === 'approved'),
    ) ?? null
  );
}

export function deriveStrategySessionView(options: {
  strategyLabel: 'Funding' | 'Cross';
  overview: StrategyManagementOverviewResult | null;
  targets: LiveTestSessionTarget[];
  sessions: LiveTradingSessionResult[];
  tradingSafety: TradingSafetyResult | null;
  runtimeLiveWriteEnabled: boolean;
  unresolvedUnknownCount: number;
}): StrategySessionView {
  const targetSessions = options.targets
    .map((target) => ({ target, session: latestSessionForTarget(options.sessions, target) }))
    .filter((item) => item.target.strategyLabel === options.strategyLabel);
  const blockers = new Set<string>();
  const missingAccounts: string[] = [];

  for (const item of targetSessions) {
    if (item.target.missingReason) {
      blockers.add(item.target.missingReason);
      missingAccounts.push(item.target.role);
      continue;
    }
    if (item.session == null) {
      missingAccounts.push(item.target.role);
    }
  }

  if (options.overview?.executionReadiness?.runnable !== true) {
    for (const blocker of options.overview?.executionReadiness?.blockers || []) {
      blockers.add(blocker);
    }
  }
  if (options.unresolvedUnknownCount > 0) {
    blockers.add('存在 unresolved result_unknown');
  }
  if (!options.tradingSafety?.liveTradingEnabled) {
    blockers.add('Platform Live Write 关闭');
  }
  if (!options.runtimeLiveWriteEnabled) {
    blockers.add('Runtime Live Write 关闭');
  }

  const statuses = targetSessions.map((item) => item.session?.status ?? 'not_created');
  let coverageStatus: StrategySessionView['coverageStatus'] = 'not_created';
  if (blockers.size > 0 && statuses.every((status) => status === 'not_created')) {
    coverageStatus = 'blocked';
  } else if (statuses.some((status) => status === 'approved')) {
    coverageStatus = statuses.every((status) => status === 'approved') ? 'approved' : 'pending';
  } else if (statuses.some((status) => status === 'pending')) {
    coverageStatus = 'pending';
  } else if (statuses.some((status) => status === 'revoked' || status === 'expired')) {
    coverageStatus = 'revoked_or_expired';
  }

  const ready =
    targetSessions.length > 0 &&
    missingAccounts.length === 0 &&
    blockers.size === 0 &&
    targetSessions.every((item) => item.session?.status === 'approved');

  return {
    strategyLabel: options.strategyLabel,
    coverageStatus,
    ready,
    missingAccounts,
    blockers: Array.from(blockers),
    sessionLabels: targetSessions.map((item) => {
      const account = item.target.accountCode || item.target.accountId || item.target.role;
      const status = item.session?.status || 'not_created';
      return `${item.target.role}:${account}:${status}`;
    }),
  };
}
