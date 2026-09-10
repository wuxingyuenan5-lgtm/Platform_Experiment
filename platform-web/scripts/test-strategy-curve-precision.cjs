const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const file = path.resolve(
  __dirname,
  '../src/views/strategy/management/composables/strategyCurvePrecision.ts',
);
const compiled = new Module(file);
compiled._compile(
  ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText,
  file,
);
const { samplePnlCurve } = compiled.exports;
const profile = {
  timestamps: [
    '2026-09-06T15:59:00Z',
    '2026-09-06T16:00:00Z',
    '2026-09-06T16:03:00Z',
    '2026-09-06T16:05:00Z',
    '2026-09-07T16:00:00Z',
  ],
  xLabels: [],
  netValues: [1, 2, 3, 5, 9],
  dailyReturns: [],
  breakdownSeries: [{ name: '待计算', data: [] }],
  detailCurves: [{ title: '基差收益', data: [] }],
};
test('daily and weekly sampling follows Shanghai calendar and keeps period close', () => {
  assert.deepEqual(samplePnlCurve(profile, 'day').netValues, [1, 5, 9]);
  assert.deepEqual(samplePnlCurve(profile, 'week').netValues, [1, 9]);
});
test('intraday sampling preserves true observations without inventing missing points', () => {
  const result = samplePnlCurve(profile, '5min');
  assert.deepEqual(result.netValues, [1, 3, 5, 9]);
  assert.deepEqual(samplePnlCurve(profile, 'hour').netValues, [1, 5, 9]);
  assert.deepEqual(result.detailCurves[0].data, []);
  assert.deepEqual(result.breakdownSeries[0].data, []);
  assert.equal(profile.netValues.length, 5);
});
