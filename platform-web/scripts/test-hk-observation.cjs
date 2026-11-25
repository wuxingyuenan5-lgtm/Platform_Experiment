const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const filename = path.resolve(
  __dirname,
  '../src/views/hedgeBoard/aShare/components/hongKongAnalysis.ts',
);
const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const mod = { exports: {} };
new Function('require', 'module', 'exports', code)(require, mod, mod.exports);
const { compareHongKong } = mod.exports;

test('Hong Kong comparison uses common sessions and does not carry holiday prices', () => {
  const hk = [
    { date: '2026-09-30', value: '100' },
    { date: '2026-10-02', value: '110' },
    { date: '2026-10-08', value: '120' },
  ];
  const cn = [
    { date: '2026-09-30', value: '200' },
    { date: '2026-10-08', value: '210' },
  ];
  const result = compareHongKong(hk, cn, 365);
  assert.deepEqual(
    result.rows.map((r) => r.date),
    ['2026-09-30', '2026-10-08'],
  );
  assert.equal(result.rows[1].hongKong, 120);
  assert.equal(result.rows[1].mainland, 105);
  assert.equal(result.baseDate, '2026-09-30');
});

test('comparison retains null gaps and rebases on selected range, not the full history', () => {
  const hk = [
    { date: '2025-01-01', value: 50 },
    { date: '2026-01-01', value: 100 },
    { date: '2026-01-02', value: null },
    { date: '2026-01-03', value: 110 },
  ];
  const cn = [
    { date: '2025-01-01', value: 100 },
    { date: '2026-01-01', value: 200 },
    { date: '2026-01-02', value: 210 },
    { date: '2026-01-03', value: 220 },
  ];
  const result = compareHongKong(hk, cn, 90);
  assert.equal(result.baseDate, '2026-01-01');
  assert.equal(result.rows[0].hongKong, 100);
  assert.equal(result.rows[1].hongKong, null);
  assert.equal(result.rows[1].mainland, 105);
  assert.ok(Math.abs(result.rows[2].hongKong - 110) < 1e-12);
  assert.equal(compareHongKong(hk, cn, 0).baseDate, '2025-01-01');
  assert.deepEqual(compareHongKong(hk, [], 365), { rows: [], baseDate: null });
});

test('invalid price is missing and never becomes an infinite normalized value', () => {
  const hk = [
    { date: '2026-01-01', value: 0 },
    { date: '2026-01-02', value: 100 },
    { date: '2026-01-03', value: 'NaN' },
  ];
  const cn = hk.map((r) => ({ ...r, value: 200 }));
  const result = compareHongKong(hk, cn, 365);
  assert.equal(result.baseDate, '2026-01-02');
  assert.equal(result.rows[0].hongKong, null);
  assert.equal(result.rows[2].hongKong, null);
});
