const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { periodValues, periodDelta, pulseMonths, pulseColor } = load('src/views/hedgeBoard/macro/economicPulse.ts');
const series = (frequency, rows) => ({ frequency, observations: rows.map(([date, value]) => ({date, value})) });

test('monthly changes do not bridge missing months or treat null as zero', () => {
  assert.equal(periodDelta(series('monthly', [['2026-01-01', 1], ['2026-03-01', 3]])), null);
  assert.equal(periodDelta(series('monthly', [['2026-02-01', null], ['2026-03-01', 0]])), null);
  assert.equal(periodDelta(series('monthly', [['2026-02-01', 1], ['2026-03-01', 0]])), -1);
});
test('quarterly values stay in native months and use the exact prior quarter', () => {
  const row = series('quarterly', [['2026-01-01', 1], ['2026-04-01', 1.5]]);
  assert.equal(periodDelta(row), 0.5);
  assert.equal(periodValues(row).has('2026-02'), false);
  assert.equal(periodDelta(series('quarterly', [['2025-10-01', 1], ['2026-04-01', 2]])), null);
});
test('calendar rolls years and heatmap preserves absent or insufficient observations', () => {
  assert.deepEqual(Array.from(pulseMonths('2026-01', 3)), ['2026-01', '2025-12', '2025-11']);
  assert.equal(pulseColor(null, [1,2,3,4,5,6]), 'transparent');
  assert.equal(pulseColor(0, [0,0,0,0,0,0]), 'transparent');
  assert.equal(pulseColor(1, [1,2]), 'transparent');
  assert.match(pulseColor(6, [1,2,3,4,5,6]), /220, 38, 38/);
});
