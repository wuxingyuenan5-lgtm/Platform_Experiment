const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
function load(name) {
  const code = ts.transpileModule(
    fs.readFileSync(
      path.join(__dirname, '../src/views/hedgeBoard/components', name + '.ts'),
      'utf8',
    ),
    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } },
  ).outputText;
  const scope = { exports: {}, require: () => load('indexValuationStats') };
  vm.runInNewContext(code, scope);
  return scope.exports;
}
const { relativeValuation, scenarioReturn, valuationAnchor, researchStats } =
  load('valuationResearch');
const metric = (history) => ({ id: 'pe', history });
test('relative valuation uses exact common dates and keeps explicit invalid values', () => {
  const a = metric([
    { date: '2026-01-01', value: 10 },
    { date: '2026-01-02', value: 20 },
    { date: '2026-01-03', value: null },
    { date: '2026-01-04', value: 30 },
  ]);
  const b = metric([
    { date: '2026-01-02', value: 10 },
    { date: '2026-01-03', value: 0 },
    { date: '2026-01-04', value: 5 },
  ]);
  const rows = relativeValuation(a, b, 3, '2026-01-03');
  assert.equal(
    JSON.stringify(rows),
    JSON.stringify([
      { date: '2026-01-02', value: 2 },
      { date: '2026-01-03', value: null },
    ]),
  );
  assert.equal(relativeValuation(a, undefined, 3, '2026-01-03').length, 0);
});
test('scenario includes the earnings and multiple interaction, including total earnings loss', () => {
  assert.ok(Math.abs(scenarioReturn(10, 16, 20) + 12) < 1e-10);
  assert.equal(scenarioReturn(0, 20, 20), 0);
  assert.equal(scenarioReturn(-100, 20, 20), -100);
  assert.equal(scenarioReturn(10, 20, 0), null);
});
test('scenario anchor never pairs latest valuation with a different price date or future data', () => {
  const chart = {
    prices: [
      { date: '2026-01-01', value: 100 },
      { date: '2026-01-03', value: 150 },
    ],
    metrics: [
      metric([
        { date: '2026-01-02', value: 20 },
        { date: '2026-01-03', value: 30 },
      ]),
    ],
  };
  const a = valuationAnchor(chart, '2026-01-02');
  assert.equal(a.pe, 20);
  assert.equal(a.price, null);
  chart.metrics[0].history[0].value = null;
  assert.equal(valuationAnchor(chart, '2026-01-02').pe, null);
});
test('zero dividends remain valid and short samples cannot claim historical rank', () => {
  const m = { id: 'dividend', history: [{ date: '2026-01-01', value: 0 }] };
  const s = researchStats(m, 3, '2026-01-01');
  assert.equal(s.count, 1);
  assert.equal(s.rank, null);
});
const { earningsToOffset } = load('valuationResearch');
test('earnings growth exactly offsets PE compression, not a sum of percentages', () => {
  const growth = earningsToOffset(25, 20);
  assert.equal(growth, 25);
  assert.equal(scenarioReturn(growth, 20, 25), 0);
  assert.ok(Math.abs(earningsToOffset(20, 25) + 20) < 1e-10);
});
test('missing, nonpositive and nonfinite inputs do not generate pressure estimates', () => {
  for (const input of [null, 0, -2, Infinity, NaN]) {
    assert.equal(earningsToOffset(input, 20), null);
    assert.equal(earningsToOffset(20, input), null);
  }
  assert.equal(scenarioReturn(Infinity, 20, 20), null);
});
