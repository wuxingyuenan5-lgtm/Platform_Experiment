const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { factorAttribution, optionStructure } = load(
  'src/views/hedgeBoard/components/goldStructureAnalysis.ts',
);
const row = (date, mid, tips, yieldFactor, premium) => ({
  date,
  available: true,
  mid,
  tips,
  yieldFactor,
  premium,
  gold: mid * tips * yieldFactor * premium,
});
test('four log contributions reconcile and remain distinct from simple return', () => {
  const a = factorAttribution([
    row('2026-01-01', 100, 2, 0.5, 1),
    row('2026-02-01', 110, 2.1, 0.45, 1.2),
  ]);
  assert.ok(Math.abs(a.difference) < 1e-10);
  assert.ok(Math.abs(a.gold - 100 * Math.log(1.2474)) < 1e-10);
  assert.ok(Math.abs(a.priceReturn - 24.74) < 1e-10);
});
test('invalid endpoints excluded with actual dates; insufficient data unavailable', () => {
  const valid = row('2026-01-02', 100, 2, 0.5, 1);
  assert.equal(factorAttribution([{ ...valid, mid: 0 }, valid]), null);
  const a = factorAttribution([
    { ...valid, date: '2026-01-01', available: false },
    valid,
    row('2026-01-03', 101, 2, 0.5, 1),
  ]);
  assert.equal(a.first, '2026-01-02');
  assert.equal(a.count, 2);
});
test('option summary preserves absent side and separates volume from OI', () => {
  const a = optionStructure(
    [{ strike: 100, volume: 5, openInterest: 10 }],
    [{ strike: 105, volume: 2, openInterest: 20 }],
  );
  assert.equal(a.oiRatio, 2);
  assert.equal(a.callVolume, 5);
  assert.equal(a.rows[0].putOi, null);
  assert.equal(optionStructure([], []), null);
  assert.equal(
    optionStructure(
      [{ strike: 100, volume: 0, openInterest: 0 }],
      [{ strike: 100, volume: 0, openInterest: 2 }],
    ).oiRatio,
    null,
  );
});
test('duplicate or malformed chains do not produce credible summaries', () => {
  const r = { strike: 100, volume: 5, openInterest: 10 };
  assert.equal(optionStructure([r, r], [r]), null);
  assert.equal(optionStructure([{ ...r, openInterest: -1 }], [r]), null);
});
