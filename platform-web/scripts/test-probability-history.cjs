const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../src/views/hedgeBoard/macro/probabilityHistory.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const output = { exports: {} };
vm.runInNewContext(`(function(exports){${compiled}\n})`, {})(output.exports);
const { probabilityHistory } = output.exports;
const point = (day, value) => ({ observedAt: `2026-10-${String(day).padStart(2, '0')}T00:00:00Z`, probability: value });

test('history uses elapsed time and preserves real zero while excluding missing values', () => {
  const result = probabilityHistory([point(11, 50), point(1, 0), point(2, 10), point(3, null), point(4, '')]);
  assert.equal(result.count, 3);
  assert.equal(result.points, '0.00,72.00 22.00,64.80 220.00,36.00');
  assert.equal(result.change1d, null);
  assert.equal(result.change7d, null);
});

test('missing history draws no line and one observation is a point', () => {
  assert.equal(probabilityHistory([]).points, '');
  const result = probabilityHistory([point(1, 0)]);
  assert.equal(result.single.x, 110);
  assert.equal(result.single.y, 72);
  assert.equal(result.change1d, null);
});

test('daily changes use the last observation at or before the comparison time', () => {
  const result = probabilityHistory([point(1, 20), point(7, 40), point(8, 42)]);
  assert.equal(result.change1d, 2);
  assert.equal(result.change7d, 22);
});
