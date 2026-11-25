const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '../src/views/hedgeBoard/aShare/components');
const modules = new Map();
function load(name) {
  if (modules.has(name)) return modules.get(name);
  const source = fs.readFileSync(path.join(root, name + '.ts'), 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', compiled)(
    (s) => {
      if (s.startsWith('./capitalHandbookDemo')) return load(s.slice(2));
      throw new Error('Demo must remain isolated from live dependencies: ' + s);
    },
    mod,
    mod.exports,
  );
  modules.set(name, mod.exports);
  return mod.exports;
}
const { DEMO_CATALOG, demoCategories } = load('capitalHandbookDemoCatalog');
const { buildCapitalDemo, demoPeriods } = load('capitalHandbookDemoData');
const total = (rows, key) => rows.reduce((s, r) => s + Number(r[key]), 0);
const close = (a, b) => assert.ok(Math.abs(a - b) < 0.011, `${a} != ${b}`);

test('every category renders deterministic finite demo data for every selectable period', () => {
  assert.equal(new Set(DEMO_CATALOG.map((s) => s.id)).size, DEMO_CATALOG.length);
  for (const c of demoCategories) assert.ok(DEMO_CATALOG.some((s) => s.category === c.key));
  for (const s of DEMO_CATALOG)
    for (const period of demoPeriods) {
      const d = buildCapitalDemo(s.id, period);
      assert.ok(d.rows.length > 0, s.id);
      assert.equal(new Set(d.columns.map((c) => c.label)).size, d.columns.length, s.id);
      assert.equal(new Set(d.rows.map((r) => r.date)).size, d.rows.length, s.id);
      for (const row of d.rows)
        for (const value of Object.values(row)) {
          if (typeof value === 'number') assert.ok(Number.isFinite(value), s.id);
        }
      if (d.kind === 'time') {
        assert.ok(
          d.rows.every((r, i) => r.date <= period && (!i || r.date > d.rows[i - 1].date)),
          s.id,
        );
      }
      assert.deepEqual(d, buildCapitalDemo(s.id, period));
    }
  console.log(
    `Validated ${DEMO_CATALOG.length} handbook cases across ${demoPeriods.length} periods`,
  );
});

test('scale bridges reconcile both row equations and adjacent period balances', () => {
  for (const spec of DEMO_CATALOG.filter((s) => s.recipe === 'bridge')) {
    const { rows } = buildCapitalDemo(spec.id);
    rows.forEach((r, i) => {
      close(r.closing, r.opening + r.newCapital + r.subscriptions + r.valuation);
      close(r.change, r.closing - r.opening);
      if (i) close(r.opening, rows[i - 1].closing);
    });
  }
});

test('allocation and company matrices normalize independently without negative weights', () => {
  for (const spec of DEMO_CATALOG.filter((s) =>
    ['allocation', 'attribution', 'companyMatrix', 'holderMix'].includes(s.recipe),
  )) {
    const d = buildCapitalDemo(spec.id);
    if (['allocation', 'attribution'].includes(spec.recipe)) {
      for (const key of ['previous', 'current', 'natural', 'benchmark'])
        close(total(d.rows, key), 100);
      for (const r of d.rows) {
        close(r.change, r.current - r.previous);
        close(r.residual, r.current - r.natural);
      }
    } else if (spec.recipe === 'companyMatrix') {
      for (const c of d.columns.slice(1)) close(total(d.rows, c.key), 100);
    } else {
      for (const r of d.rows)
        close(
          d.columns.slice(1).reduce((s, c) => s + r[c.key], 0),
          100,
        );
    }
  }
});

test('fund holdings use fictional securities and reconcile weights with reported amounts', () => {
  for (const id of ['fund-heavy-a']) {
    const d = buildCapitalDemo(id);
    assert.ok(total(d.rows, 'weight') < 100);
    assert.ok(d.rows.every((r, i) => r.rank === i + 1 && (!i || r.amount <= d.rows[i - 1].amount)));
    for (const r of d.rows) {
      assert.match(r.date, /^示例/);
      close(r.amount, r.weight * 85);
      close(r.change, r.weight - r.previous);
    }
  }
});

test('retained industry table includes changes and percentiles while foreign flows stay quarterly', () => {
  const allocation = buildCapitalDemo('fund-sector-allocation');
  assert.ok(allocation.columns.some((c) => c.key === 'percentile'));
  assert.ok(allocation.columns.some((c) => c.key === 'change'));
  for (const row of allocation.rows) assert.ok(row.percentile >= 0 && row.percentile <= 100);
  const quarterly = buildCapitalDemo('foreign-quarter-flow');
  assert.equal(quarterly.rows.length, 12);
  assert.ok(
    quarterly.rows.every((r) => ['03-31', '06-30', '09-30', '12-31'].includes(r.date.slice(5))),
  );
});

test('flow totals reconcile', () => {
  for (const s of DEMO_CATALOG.filter((s) => ['flows', 'supply'].includes(s.recipe))) {
    const d = buildCapitalDemo(s.id);
    for (const r of d.rows)
      close(
        r.net,
        d.lines.filter((l) => l.key !== 'net').reduce((n, l) => n + r[l.key], 0),
      );
  }
});

test('foreign macro comparisons share the same dates and flow series for each report period', () => {
  const { FOREIGN_COMPARISON_IDS } = load('capitalHandbookDemoCatalog');
  for (const period of demoPeriods) {
    const datasets = FOREIGN_COMPARISON_IDS.map((id) => buildCapitalDemo(id, period));
    const base = datasets[0].rows.map((r) => [r.date, r.v0]);
    for (const dataset of datasets) {
      assert.deepEqual(
        dataset.rows.map((r) => [r.date, r.v0]),
        base,
      );
      assert.equal(dataset.lines[0].unit, '亿元');
      assert.equal(dataset.lines[1].right, true);
    }
    assert.equal(new Set(datasets.map((d) => d.lines[1].name)).size, 4);
  }
});

test('ranking columns are unique permutations and deleted scatter charts stay absent', () => {
  for (const spec of DEMO_CATALOG.filter((s) => s.recipe === 'rankHistory')) {
    const d = buildCapitalDemo(spec.id);
    for (const c of d.columns.slice(1))
      assert.deepEqual(
        d.rows
          .map((r) => r[c.key])
          .filter((v) => v != null)
          .sort((a, b) => a - b),
        Array.from({ length: spec.id === 'foreign-sector-rank' ? 10 : 25 }, (_, i) => i + 1),
      );
  }
  assert.ok(
    !DEMO_CATALOG.some((s) =>
      /ETF申赎与市场涨跌|ETF净流入与A股涨跌散点|ETF净流入与融资净流入散点/.test(s.title),
    ),
  );
  assert.throws(() => buildCapitalDemo('missing'));
  assert.throws(() => buildCapitalDemo('fund-heavy-a', 'invalid'));
});

test('inline demos retain requested categories and omit withdrawn items', () => {
  assert.equal(DEMO_CATALOG.length, 18);
  const visible = DEMO_CATALOG.map((v) => v.id);
  assert.equal(new Set(visible).size, visible.length);
  assert.deepEqual(
    DEMO_CATALOG.filter((v) => v.category === 'insurance').map((v) => v.id),
    ['insurance-sector-change', 'insurance-premium'],
  );
  assert.deepEqual(
    DEMO_CATALOG.filter((v) => v.category === 'funds').map((v) => v.id),
    ['fund-sector-allocation', 'fund-heavy-a'],
  );
  assert.ok(DEMO_CATALOG.every((e) => !['etf', 'margin', 'private', 'bank'].includes(e.category)));
  assert.deepEqual(
    DEMO_CATALOG.filter((v) => v.category === 'overview').map((v) => v.id),
    ['funding-balance'],
  );
  for (const id of [
    'fund-style-excess',
    'foreign-style',
    'etf-fees',
    'insurance-listed',
    'insurance-quarter-flow',
    'foreign-msci',
    'institution-flows',
    'etf-passive-contribution',
    'funding-market',
    'style-cycle',
  ])
    assert.ok(!visible.includes(id));
});
