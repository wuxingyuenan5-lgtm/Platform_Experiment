const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { initialChartYears, macroDisplayLabel } = load(
  'src/views/hedgeBoard/charts/macroChartDefaults.ts',
);
const { researchModules } = load('src/views/hedgeBoard/nativeData/dashboardClean.ts');

test('US employment and consumption requirements remain visible in the economy catalogue', () => {
  const growth = researchModules
    .find((m) => m.id === 'macro')
    .sections.find((s) => s.id === 'macro-growth');
  const keys = growth.widgets.map((w) => w.localKey);
  for (const key of [
    'macro-us-employment',
    'macro-us-unemployment',
    'macro-us-consumption',
    'macro-us-real-retail',
    'macro-us-consumption-momentum',
    'macro-us-profit-expectations',
    'macro-cn-retail',
  ])
    assert.equal(keys.filter((k) => k === key).length, 1, key);
  assert.ok(keys.indexOf('macro-us-employment') < keys.indexOf('macro-us-consumption'));
  assert.ok(keys.indexOf('macro-us-unemployment') < keys.indexOf('macro-us-consumption'));
});

test('macro defaults honor per-chart windows instead of a blanket five years', () => {
  const groups = {
    netLiquidity: 3,
    fedBalance: 10,
    fedAssets: 10,
    treasuryYields: 1,
    rateCorridor: 0.25,
    corporateYields: 3,
    riskHighYieldOas: 1,
    realYield: 1,
    cnPolicyRates: 3,
    cnRates: 3,
    cnTreasury: 3,
    actualInflation: 3,
    upstreamInflation: 3,
    inflationNowcast: 3,
    inflationExpectations: 3,
    marketInflation: 1,
    vix: 1,
    riskCreditRatio: 1,
    cnRiskLeverage: 1,
    cnRiskVolatility: 1,
  };
  for (const [group, years] of Object.entries(groups))
    assert.equal(initialChartYears(group, 'macro', 'time'), years, group);
  assert.equal(initialChartYears('usEmployment', 'macro', 'time'), 5);
});
test('macro overrides do not change commodity and crypto defaults', () => {
  assert.equal(initialChartYears('fedAssets', 'commodity', 'time'), 3);
  assert.equal(initialChartYears('goldDrivers', 'commodity', 'gold-drivers'), 1);
  assert.equal(initialChartYears('coinbasePremium', 'crypto', 'time'), 0.25);
  assert.equal(initialChartYears('binanceCombinedBTC', 'crypto', 'time'), 0.25);
});
test('treasury names use requested abbreviations without changing other series', () => {
  assert.deepEqual(
    ['3m', '2y', '5y', '10y', '30y'].map((m) =>
      macroDisplayLabel('treasuryYields', `us_treasury_${m}`, 'original'),
    ),
    ['US03MY', 'US2Y', 'US5Y', 'US10Y', 'US30Y'],
  );
  assert.equal(macroDisplayLabel('cnTreasury', 'cn_treasury_10y', '中国10Y'), '中国10Y');
});
