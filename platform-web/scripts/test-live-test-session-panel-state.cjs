const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const ts = require('typescript');

function loadTsModule(modulePath, stubs) {
  const source = fs.readFileSync(modulePath, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
      baseUrl: path.resolve(__dirname, '..', 'src'),
      paths: { '@/*': ['*'] },
    },
    fileName: modulePath,
  }).outputText;
  const loaded = new Module(modulePath, module);
  loaded.filename = modulePath;
  loaded.paths = Module._nodeModulePaths(path.dirname(modulePath));
  const originalRequire = loaded.require.bind(loaded);
  loaded.require = (request) => {
    if (request in stubs) return stubs[request];
    return originalRequire(request);
  };
  loaded._compile(compiled, modulePath);
  return loaded.exports;
}

function baseOverview(strategyInstanceId) {
  return {
    strategyInstanceId,
    executionReadiness: {
      runnable: true,
      blockers: [],
      resultUnknownOrderCount: 0,
    },
  };
}

function baseFundingContext() {
  return {
    accountId: 'bybit-live-main',
    spotSymbol: 'BTCUSDT',
    perpetualSymbol: 'BTCUSDT-PERP',
    runtime: { liveWriteEnabled: false },
  };
}

function baseCrossObservability() {
  return {
    bybit: { symbol: 'XAUTUSDT' },
    mt5: { symbol: 'XAUUSD.s' },
  };
}

function binding(role, accountId, accountCode) {
  return { role, accountId, accountCode, status: 'active' };
}

const modulePath = path.join(
  __dirname,
  '..',
  'src/views/strategy/management/composables/liveTestSessionPanelState.ts',
);
const state = loadTsModule(modulePath, {
  '@/api/platform/fundingWorkspace': {},
  '@/api/platform/crossSpreadObservability': {},
  '@/api/platform/trading.types': {},
});

const {
  buildLiveTradingSessionPayload,
  deriveLiveTestSessionTargets,
  deriveStrategySessionView,
  findReusableLiveSession,
} = state;

{
  const targets = deriveLiveTestSessionTargets({
    selectedFunding: true,
    selectedCross: false,
    fundingOverview: baseOverview('strategy_funding_arbitrage_instance_default'),
    crossOverview: baseOverview('strategy_cross_venue_spread_instance_default'),
    fundingBindings: [binding('primary', 'bybit-live-main', 'BYBIT-LIVE-MAIN')],
    crossBindings: [],
    fundingContext: baseFundingContext(),
    crossObservability: baseCrossObservability(),
  });
  assert.equal(targets.length, 1);
  assert.equal(targets[0].accountId, 'bybit-live-main');
  assert.deepEqual(targets[0].symbols, ['BTCUSDT', 'BTCUSDT-PERP']);
}

{
  const targets = deriveLiveTestSessionTargets({
    selectedFunding: false,
    selectedCross: true,
    fundingOverview: baseOverview('strategy_funding_arbitrage_instance_default'),
    crossOverview: baseOverview('strategy_cross_venue_spread_instance_default'),
    fundingBindings: [],
    crossBindings: [
      binding('venue_a', 'bybit-live-main', 'BYBIT-LIVE-MAIN'),
      binding('mt5_leg', 'mt5-live-main', 'MT5-LIVE-MAIN'),
    ],
    fundingContext: baseFundingContext(),
    crossObservability: baseCrossObservability(),
  });
  assert.equal(targets.length, 2);
  assert.deepEqual(
    targets.map((item) => [item.role, item.accountId, item.symbolText]),
    [
      ['venue_a', 'bybit-live-main', 'XAUTUSDT'],
      ['mt5_leg', 'mt5-live-main', 'XAUUSD.S'],
    ],
  );
}

{
  const targets = deriveLiveTestSessionTargets({
    selectedFunding: true,
    selectedCross: true,
    fundingOverview: baseOverview('strategy_funding_arbitrage_instance_default'),
    crossOverview: baseOverview('strategy_cross_venue_spread_instance_default'),
    fundingBindings: [binding('primary', 'bybit-live-main', 'BYBIT-LIVE-MAIN')],
    crossBindings: [
      binding('venue_a', 'bybit-live-main', 'BYBIT-LIVE-MAIN'),
      binding('mt5_leg', 'mt5-live-main', 'MT5-LIVE-MAIN'),
    ],
    fundingContext: baseFundingContext(),
    crossObservability: baseCrossObservability(),
  });
  assert.equal(targets.length, 3);
}

{
  const targets = deriveLiveTestSessionTargets({
    selectedFunding: false,
    selectedCross: true,
    fundingOverview: baseOverview('strategy_funding_arbitrage_instance_default'),
    crossOverview: baseOverview('strategy_cross_venue_spread_instance_default'),
    fundingBindings: [],
    crossBindings: [binding('venue_a', 'bybit-live-main', 'BYBIT-LIVE-MAIN')],
    fundingContext: baseFundingContext(),
    crossObservability: baseCrossObservability(),
  });
  const crossState = deriveStrategySessionView({
    strategyLabel: 'Cross',
    overview: baseOverview('strategy_cross_venue_spread_instance_default'),
    targets,
    sessions: [],
    tradingSafety: { liveTradingEnabled: true },
    runtimeLiveWriteEnabled: true,
    unresolvedUnknownCount: 0,
  });
  assert.equal(crossState.ready, false);
  assert.ok(crossState.blockers.includes('Cross MT5 账户绑定缺失'));
}

{
  const targets = deriveLiveTestSessionTargets({
    selectedFunding: false,
    selectedCross: true,
    fundingOverview: baseOverview('strategy_funding_arbitrage_instance_default'),
    crossOverview: baseOverview('strategy_cross_venue_spread_instance_default'),
    fundingBindings: [],
    crossBindings: [
      binding('venue_a', 'bybit-live-main', 'BYBIT-LIVE-MAIN'),
      binding('mt5_leg', 'mt5-live-main', 'MT5-LIVE-MAIN'),
    ],
    fundingContext: baseFundingContext(),
    crossObservability: baseCrossObservability(),
  });
  const form = { expiryMinutes: '15', maxOrderNotional: '100', maxDailyNotional: '200' };
  const payload = buildLiveTradingSessionPayload(targets[1], form);
  assert.deepEqual(payload.symbols, ['XAUUSD.S']);
  const existing = {
    sessionId: 'session-1',
    sessionType: 'minimum_size_acceptance',
    strategyInstanceId: targets[1].strategyInstanceId,
    accountId: 'mt5-live-main',
    symbols: ['XAUUSD.S'],
    maxOrderNotional: '100',
    maxDailyNotional: '200',
    status: 'pending',
    createdAt: '2026-08-25T00:00:00+00:00',
  };
  assert.equal(findReusableLiveSession([existing], targets[1], form).sessionId, 'session-1');
}

{
  const targets = deriveLiveTestSessionTargets({
    selectedFunding: true,
    selectedCross: false,
    fundingOverview: baseOverview('strategy_funding_arbitrage_instance_default'),
    crossOverview: baseOverview('strategy_cross_venue_spread_instance_default'),
    fundingBindings: [binding('primary', 'bybit-live-main', 'BYBIT-LIVE-MAIN')],
    crossBindings: [],
    fundingContext: baseFundingContext(),
    crossObservability: baseCrossObservability(),
  });
  const fundingState = deriveStrategySessionView({
    strategyLabel: 'Funding',
    overview: {
      ...baseOverview('strategy_funding_arbitrage_instance_default'),
      executionReadiness: { runnable: true, blockers: [], resultUnknownOrderCount: 1 },
    },
    targets,
    sessions: [
      {
        sessionId: 'session-approved',
        sessionType: 'minimum_size_acceptance',
        strategyInstanceId: 'strategy_funding_arbitrage_instance_default',
        accountId: 'bybit-live-main',
        symbols: ['BTCUSDT', 'BTCUSDT-PERP'],
        maxOrderNotional: '100',
        maxDailyNotional: '200',
        status: 'approved',
        createdAt: '2026-08-25T00:00:00+00:00',
      },
    ],
    tradingSafety: { liveTradingEnabled: false },
    runtimeLiveWriteEnabled: false,
    unresolvedUnknownCount: 1,
  });
  assert.equal(fundingState.coverageStatus, 'approved');
  assert.equal(fundingState.ready, false);
  assert.ok(fundingState.blockers.includes('Platform Live Write 关闭'));
  assert.ok(fundingState.blockers.includes('Runtime Live Write 关闭'));
  assert.ok(fundingState.blockers.includes('存在 unresolved result_unknown'));
}

{
  const targets = deriveLiveTestSessionTargets({
    selectedFunding: false,
    selectedCross: true,
    fundingOverview: baseOverview('strategy_funding_arbitrage_instance_default'),
    crossOverview: baseOverview('strategy_cross_venue_spread_instance_default'),
    fundingBindings: [],
    crossBindings: [
      binding('venue_a', 'bybit-live-main', 'BYBIT-LIVE-MAIN'),
      binding('mt5_leg', 'mt5-live-main', 'MT5-LIVE-MAIN'),
    ],
    fundingContext: baseFundingContext(),
    crossObservability: { bybit: { symbol: 'XAUTUSDT' }, mt5: { symbol: '' } },
  });
  assert.equal(targets[1].missingReason, 'Cross MT5 实际 Broker Symbol 未就绪');
}

console.log('live test session panel state behavior passed');
