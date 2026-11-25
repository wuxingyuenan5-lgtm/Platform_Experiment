const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const a = load('src/views/strategy/spread-carry/market-demo/statistics.ts');
const { HOUR, study } = load('src/views/strategy/spread-carry/market-demo/marketDemo.ts');
const near = (actual, expected) =>
  assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} != ${expected}`);
const series = (values) => values.map((mid, i) => ({ mid, time: (i * HOUR) / 2, session: '美国' }));
const event = (overrides = {}) => ({
  time: 0,
  direction: 'long',
  session: '美国',
  entry: 0,
  target: 3,
  hours: 0,
  mae: 0,
  status: 'censored',
  ...overrides,
});

test('distribution uses sample variance, interpolated quantiles and missing-safe moments', () => {
  const r = a.describe([0, 2, 4, 6, NaN]);
  assert.equal(r.n, 4);
  near(r.mean, 3);
  near(r.median, 3);
  near(r.std, Math.sqrt(20 / 3));
  near(r.p25, 1.5);
  near(r.p75, 4.5);
  near(r.mad, 2);
  assert.equal(r.skew, null);
  assert.equal(a.describe([]).mean, null);
  assert.equal(a.describe([1]).std, null);
  const symmetric = a.describe(Array.from({ length: 21 }, (_, i) => i - 10));
  near(symmetric.skew, 0);
  assert.ok(symmetric.excessKurtosis < 0);
  assert.equal(a.describe(Array(25).fill(3)).excessKurtosis, null);
});

test('histogram retains extremes, maximum edge, and constant distributions', () => {
  for (const values of [
    [-500, 0, 0, 10, 500],
    [2, 2, 2],
  ]) {
    const bins = a.histogram(values, 10);
    assert.equal(
      bins.reduce((sum, b) => sum + b.count, 0),
      values.length,
    );
    assert.ok(bins[0].low <= Math.min(...values));
    assert.ok(bins.at(-1).high >= Math.max(...values));
  }
  assert.deepEqual(a.histogram([]), []);
});

test('lag pairs require all intermediate observations, not just matching endpoints', () => {
  const rows = series([1, 2, 3, 4, 5, 6]);
  assert.equal(a.contiguousPairs(rows, 2).length, 4);
  const gap = rows.filter((_, i) => i !== 2);
  assert.equal(a.contiguousPairs(gap).length, 3);
  assert.equal(a.contiguousPairs(gap, 2).length, 1);
  assert.equal(a.sampleQuality(gap).breaks, 1);
  const nan = rows.map((r, i) => (i === 2 ? { ...r, mid: NaN } : r));
  assert.equal(a.contiguousPairs(nan, 2).length, 1);
});

test('rolling windows reset after gaps and do not use future observations', () => {
  const rows = series([0, 2, 4, 6, 8, 10]);
  const r = a.rollingDistribution(rows, 3);
  assert.equal(r[1].median, null);
  assert.equal(r[2].median, 2);
  assert.deepEqual(a.rollingDistribution(rows.slice(0, 3), 3), r.slice(0, 3));
  const gap = a.rollingDistribution(
    rows.map((r, i) => ({ ...r, time: r.time + (i >= 3 ? HOUR : 0) })),
    3,
  );
  assert.equal(gap[3].median, null);
  assert.equal(gap[4].median, null);
  assert.equal(gap[5].median, 8);
});

test('AR(1) half-life is in hours and withheld for non-reverting or sparse samples', () => {
  let value = 10;
  const values = Array.from({ length: 65 }, () => {
    const out = value;
    value = 1 + 0.8 * value;
    return out;
  });
  const fit = a.reversionModel(series(values));
  near(fit.slope, 0.8);
  near(fit.intercept, 1);
  near(fit.halfLife, (Math.log(0.5) / Math.log(0.8)) * 0.5);
  assert.equal(a.reversionModel(series(values.slice(0, 20))).halfLife, null);
  assert.equal(a.reversionModel(series(Array(60).fill(1))).halfLife, null);
  assert.equal(
    a.reversionModel(series(Array.from({ length: 60 }, (_, i) => 1.01 ** i))).halfLife,
    null,
  );
});

test('fixed horizons keep favorable/adverse sign, MAE/MFE and censor missing paths', () => {
  const rows = series([0, -2, 1, 4, 5]);
  const r = a.horizonOutcomes(rows, [event()], 2);
  assert.equal(r.n, 1);
  assert.equal(r.median, 5);
  assert.equal(r.mae, 2);
  assert.equal(r.mfe, 5);
  const short = a.horizonOutcomes(rows, [event({ direction: 'short', target: -3 })], 2);
  assert.equal(short.median, -5);
  assert.equal(short.mae, 5);
  assert.equal(short.mfe, 2);
  const gap = a.horizonOutcomes(
    rows.filter((_, i) => i !== 1),
    [event()],
    2,
  );
  assert.equal(gap.n, 0);
  assert.equal(gap.censored, 1);
  assert.equal(gap.median, null);
  const end = a.horizonOutcomes(rows, [event()], 8);
  assert.equal(end.n, 0);
  assert.equal(end.censored, 1);
});

test('first passage respects risk-before-recovery and known outcome before later gap', () => {
  assert.equal(a.firstPassage(series([0, -2, 4]), event(), 1, 1).status, 'risk');
  assert.equal(a.firstPassage(series([0, 4]), event(), 8, 1).status, 'target');
  assert.equal(a.firstPassage(series([0, 0.5, 1]), event(), 1, 2).status, 'timeout');
  assert.equal(a.firstPassage(series([0, 0.5]), event(), 1, 2).status, 'censored');
});

test('active event remains observable when a later session lacks a trained model', () => {
  const rows = Array.from({ length: 100 }, (_, i) => ({
    time: (i * HOUR) / 2,
    mid: i < 60 ? (i % 2 ? 1 : -1) : i < 62 ? 8 : -1,
    session: i >= 62 ? '亚洲' : '美国',
  }));
  const result = study(rows);
  assert.equal(result.events.length, 1);
  assert.equal(result.events[0].status, 'reverted');
  assert.equal(result.events[0].hours, 1);
});

test('quantity-weighted book sweep refuses an incomplete full-size average', () => {
  const book = [
    { price: 100, quantity: 1 },
    { price: 101, quantity: 2 },
    { price: 102, quantity: 5 },
  ];
  near(a.sweepBook(book, 5).vwap, 101.2);
  assert.equal(a.sweepBook(book, 9).filled, 8);
  assert.equal(a.sweepBook(book, 9).vwap, null);
  assert.equal(a.sweepBook(book, 0).complete, false);
  assert.equal(a.sweepBook(book, NaN).complete, false);
  assert.equal(a.sweepBook(a.demoBook('short', true), 5).complete, false);
  assert.ok(
    a.sweepBook(a.demoBook('long', false), 10).vwap >
      a.sweepBook(a.demoBook('long', false), 1).vwap,
  );
});

test('reopen study reports both edges of a gap without synthesizing intermediate prices', () => {
  const rows = series([2, 3, 8, 7]).map((r, i) => ({
    ...r,
    time: r.time + (i >= 2 ? HOUR : 0),
    width: i < 2 ? 1 : 2,
  }));
  const reopened = a.reopenEvents(rows);
  assert.equal(reopened.length, 1);
  assert.equal(reopened[0].gapHours, 1.5);
  assert.equal(reopened[0].change, 5);
  assert.equal(reopened[0].beforeWidth, 1);
  assert.equal(reopened[0].afterWidth, 2);
  assert.equal(a.contiguousPairs(rows).length, 2);
});
