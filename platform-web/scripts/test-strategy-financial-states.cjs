const assert = require('node:assert/strict');
const test = require('node:test');
const createLoader = require('./load-strategy-module.cjs');
const load = createLoader({ '@/data/sample/strategy': { strategyPnlProfiles: {} } });
const { financialProfile, buildPositionDistribution } = load(
  'src/views/strategy/management/composables/strategyFinancialPresentation.ts',
);

test('Cross overview uses strategy returns and never sums across missing valuation days', () => {
  const finance = { currency: 'USD', issues: [], timeline: [] };
  const day = { date: '2026-09-18', pnl: '2', quality: 'complete' };
  const input = { positions: [], dailyPnl: [{ ...day, pnl: '500' }], strategyDailyPnl: [day] };
  assert.deepEqual(financialProfile('Cross', finance, '', 'crossSpread', input).netValues, [2]);
  input.strategyDailyPnl.push({
    ...day,
    date: '2026-09-19',
    pnl: null,
    quality: 'historical_position_marks_unavailable',
  });
  const partial = financialProfile('Cross', finance, '', 'crossSpread', input);
  assert.deepEqual(partial.netValues, [2, null]);
  assert.equal(partial.curveLineLabel, '区间累计净损益');
  input.strategyDailyPnl.push({ ...day, date: '2026-09-20', pnl: '3' });
  assert.deepEqual(financialProfile('Cross', finance, '', 'crossSpread', input).netValues, [
    2,
    null,
    3,
  ]);
});

test('Funding calendar and overview never borrow shared account returns', () => {
  const accountDay = {
    date: '2026-09-18',
    currency: 'USD',
    pnl: '500',
    returnRate: '5',
    quality: 'estimated',
  };
  const summary = financialProfile('Funding', null, 'ready', 'funding', {
    positions: [],
    dailyPnl: [accountDay],
  });
  assert.deepEqual(summary.dailyPnl, []);
  assert.equal(summary.dailyPnlCurrency, '');
  assert.deepEqual(summary.netValues, []);
  const detail = financialProfile(
    'Funding',
    { currency: 'USD', issues: [], timeline: [] },
    'ready',
    'funding',
    {
      positions: [],
      dailyPnl: [accountDay],
      strategyDailyPnl: [{ ...accountDay, pnl: '2' }],
    },
  );
  assert.equal(detail.dailyPnl[0].pnl, 2);
  assert.deepEqual(detail.netValues, [2]);
});

test('Cross preserves original value currencies instead of relabelling USDT as USD', () => {
  const positions = [
    { symbol: 'XAUTUSDT', netQuantity: '1', positionValue: '3000', positionValueCurrency: 'USDT' },
    {
      symbol: 'XAUUSD.S',
      netQuantity: '-0.01',
      positionValue: '2999',
      positionValueCurrency: 'USD',
    },
  ];
  const result = buildPositionDistribution(positions, null, null, 'crossSpread');
  assert.equal(result.mixedCurrency, true);
  assert.deepEqual(
    result.groups.map((group) => group.currency),
    ['USDT', 'USD'],
  );
  assert.match(result.gross, /USDT/);
  assert.match(result.gross, /USD/);
});

test('a position without valuation is unknown, not a balanced hedge', () => {
  const result = buildPositionDistribution(
    [{ symbol: 'XAUTUSDT', netQuantity: '1', positionValue: null }],
    null,
    null,
    'crossSpread',
  );
  assert.equal(result.emptyMessage, '持仓暂无可比名义价值');
});

test('current snapshot remains empty even when full historical finance still has positions', async () => {
  const vue = require('vue');
  const loader = createLoader({
    '@/data/sample/strategy': { strategyPnlProfiles: {} },
    '@/api/platform/trading': {
      getStrategyAccountSnapshot: async () => ({
        accountId: 'read-only',
        accountCode: 'fixture',
        snapshotScope: 'account',
        positions: [],
        orders: [],
        fills: [],
        fillsTotal: 0,
        equityHistory: [],
        dailyPnl: [],
        syncStatus: 'ready',
        asOf: '2026-09-19T08:00:00Z',
        finance: {
          positions: [
            { symbol: 'OLD', netQuantity: '1', positionValue: '999', positionValueCurrency: 'USD' },
          ],
          timeline: [],
          byCurrency: [],
        },
      }),
    },
  });
  const scope = vue.effectScope();
  const state = scope.run(() =>
    loader(
      'src/views/strategy/management/composables/useStrategyAccountSnapshots.ts',
    ).useStrategyAccountSnapshots(),
  );
  try {
    await state.refresh('shortLineTraderL', 'pnl');
    await vue.nextTick();
    assert.deepEqual(state.pnlProfiles.value.shortLineTraderL.positionDistribution.slices, []);
  } finally {
    scope.stop();
    loader('src/api/platform/strategyQueries.ts').strategyQueryClient.clear();
  }
});

test('Cross closed days do not reset the cumulative baseline or create reopening profit', () => {
  const points = [
    { date: '2026-09-18', pnl: '2', quality: 'estimated' },
    { date: '2026-09-19', pnl: null, quality: 'market_closed' },
    { date: '2026-09-20', pnl: null, quality: 'market_closed' },
    { date: '2026-09-21', pnl: '0', quality: 'estimated' },
  ];
  const p = financialProfile(
    'Cross',
    { currency: 'USDT', issues: [], timeline: [] },
    '',
    'crossSpread',
    { positions: [], strategyDailyPnl: points },
  );
  assert.deepEqual(p.netValues, [2, 2]);
  assert.deepEqual(p.dailyReturns, [2, 0]);
  const { buildPnlCalendar } = load(
    'src/views/strategy/management/composables/strategyPnlCalendar.ts',
  );
  const calendar = buildPnlCalendar(p.dailyPnl, 'USDT', 'daily', { year: 2026, month: 9 });
  assert.equal(calendar.cells.find((c) => c.key === '2026-09-19').amount, '休市');
});

test('Cross total-assets modes default to open-session history while risk stays live', async () => {
  const loader = createLoader({
    '@/data/sample/strategy': { strategyPnlProfiles: {} },
    '@/views/strategy/shared/strategyRegistry': {
      getStrategyManifest: () => ({ category: 'hedged' }),
    },
    '@/api/platform/strategyQueries': { fetchStrategyQuery: (_key, fn) => fn() },
    '@/api/platform/trading': {
      getStrategyAccountBindings: async () => [{ accountId: 'bybit-live-main', status: 'active' }],
      getStrategyPnl: async () => ({
        currency: 'USDT',
        issues: [],
        timeline: [],
        strategyDailyPnl: [],
      }),
      getStrategyAccountSnapshot: async () => ({
        accountId: 'bybit-live-main',
        accountCode: 'BYBIT-LIVE-001',
        positions: [],
        syncStatus: 'ready',
        accountRisk: {
          assetScope: 'unified_trading',
          currency: 'USD',
          totalAssets: '90',
          unrealizedPnl: '-10',
        },
        balance: { currency: 'USD', equity: '90' },
        equityHistory: [
          {
            asOf: '2026-09-20T00:00:00Z',
            totalAssets: '90',
            equity: '90',
            totalAssetsDrawdown: '-10',
          },
        ],
        sessionEquityHistory: [
          {
            asOf: '2026-09-18T20:00:00Z',
            totalAssets: '100',
            equity: '100',
            totalAssetsDrawdown: '0',
          },
        ],
      }),
    },
  });
  const state = loader(
    'src/views/strategy/management/composables/useCrossSpreadFinance.ts',
  ).useCrossSpreadFinance();
  await state.refresh('capital');
  const profile = state.liveCapitalProfile.value;
  assert.equal(profile.curve.defaultMode, 'mt5_open');
  assert.deepEqual(profile.curve.metricSeries['totalAssets:mt5_open'].netValueData, [100]);
  assert.deepEqual(profile.curve.metricSeries.totalAssets.netValueData, [90]);
  assert.deepEqual(profile.curve.metricSeries['totalAssets:mt5_open'].drawdownData, [0]);
  assert.ok(
    profile.riskCards.some((c) => c.label.includes('账户浮盈亏') && c.value.includes('-10')),
  );
});
