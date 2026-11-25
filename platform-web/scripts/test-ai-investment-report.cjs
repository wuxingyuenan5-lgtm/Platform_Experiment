const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const code = ts.transpileModule(
  fs.readFileSync(path.join(__dirname, '../src/views/hedgeBoard/ai/investmentReport.ts'), 'utf8'),
  {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  },
).outputText;
const mod = { exports: {} };
new Function('require', 'module', 'exports', code)(require, mod, mod.exports);
const { reportTopics, chartCsv, chartRows, drawdownSummary, drawdowns } = mod.exports;
const charts = reportTopics.flatMap((t) => t.charts);

test('report snapshots retain dates, units, source pages and original labeled values', () => {
  const byId = Object.fromEntries(charts.map((c) => [c.id, c]));
  for (const [id, date, values] of [
    ['market-cap', '2026-05', [77, 56, 45, 31, 21, 20, 14, 14]],
    ['turnover', '2026-06-02', [78, 62, 57, 51, 45, 44]],
    ['penetration', '各柱所列年份；AI最新为2026-07', [36, 32, 28, 26, 13, 10]],
  ]) {
    assert.equal(byId[id].status, 'snapshot');
    assert.equal(byId[id].asOf, date);
    assert.equal(byId[id].unit, '%');
    assert.deepEqual(byId[id].series[0].values, values);
  }
  assert.deepEqual(
    charts.filter((c) => c.status === 'snapshot').map((c) => c.id),
    ['drawdowns', 'market-cap', 'turnover', 'penetration'],
  );
});

test('selected drawdowns reproduce report means after published rounding, without dropping crisis rows', () => {
  assert.equal(drawdowns.length, 21);
  assert.equal(drawdownSummary('科网').count, 12);
  assert.equal(drawdownSummary('AI').count, 9);
  assert.equal(drawdownSummary('科网').depth.toFixed(1), '-11.5');
  assert.equal(drawdownSummary('科网').days.toFixed(1), '32.3');
  assert.equal(drawdownSummary('AI').depth.toFixed(1), '-11.4');
  assert.equal(drawdownSummary('AI').days.toFixed(1), '36.9');
  assert.equal(Math.min(...drawdowns.map((r) => r[3])), -29.5);
});

test('all topics have distinct chart ids and aligned finite series with explicit provenance', () => {
  assert.deepEqual(
    reportTopics.map((t) => t.id),
    Array.from({ length: 22 }, (_, i) => i + 1),
  );
  assert.equal(new Set(charts.map((c) => c.id)).size, charts.length);
  for (const c of charts) {
    assert.ok(c.page && c.asOf && c.unit && c.basis);
    assert.ok(['demo', 'snapshot'].includes(c.status));
    for (const s of c.series) {
      assert.equal(s.values.length, c.labels.length, c.id);
      assert.ok(
        s.values.every((v) => v === null || Number.isFinite(v)),
        c.id,
      );
      if (s.right) assert.ok(c.rightUnit, c.id);
    }
  }
  const path = charts.find((c) => c.id === 'cycle-path');
  assert.ok(
    path.series[1].values.slice(44).every((v) => v === null),
    'do not invent the future AI path',
  );
  const event = charts.find((c) => c.id === 'arr-event');
  assert.equal(event.labels[20], 'T+0');
  event.series.forEach((s) => assert.equal(s.values[20], 1, 'event baseline is exactly T0=1'));
});

test('CSV exports preserve Demo labels, source dates, dual-axis units and missingness', () => {
  for (const c of charts) {
    const csv = chartCsv(c);
    assert.ok(csv.includes(c.asOf));
    assert.ok(csv.includes('PDF第' + c.page + '页'));
    assert.ok(csv.includes(c.status === 'demo' ? 'Demo · 模拟数据' : '报告快照 · 未独立复核'));
  }
  const path = charts.find((c) => c.id === 'cycle-path');
  assert.equal(chartRows(path).at(-1).at(-1), null);
  assert.ok(chartCsv(path).split('\r\n').at(-1).endsWith(',""'));
  assert.ok(chartCsv(charts.find((c) => c.id === 'rotation-us')).includes('百分点'));
  assert.ok(chartCsv(charts.find((c) => c.id === 'global-peg')).includes('未来12个月PE（倍）'));
});
console.log(`Report coverage: ${reportTopics.length} topics / ${charts.length} charts / 2 maps.`);
