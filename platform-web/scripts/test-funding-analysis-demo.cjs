const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const vm = require('node:vm');
const code = ts.transpileModule(
  fs.readFileSync('src/views/strategy/funding-carry/analysisDemo/model.ts', 'utf8'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } },
).outputText;
const moduleExports = {};
vm.runInNewContext(code, { exports: moduleExports });
const { pairs, history, statistics, evaluate, snapshot } = moduleExports;
const defaults = {
  notional: 100000,
  days: 7,
  fundingScale: 100,
  basisMove: 3,
  depthLoss: 0,
  priceShock: 15,
  reservePct: 25,
};
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-8, `${a} != ${b}`);

test('eight-hour and four-hour settlements use their own calendars; histories end at the labelled snapshot', () => {
  for (const p of pairs) {
    const h = history(p);
    assert.equal(h.length, (30 * 24) / p.hours);
    assert.equal(h.at(-1).time, snapshot);
    assert.equal(h.at(-1).time - h.at(-2).time, p.hours * 3600000);
    const actual24 = h.filter((r) => r.time > snapshot - 86400000).reduce((s, r) => s + r.value, 0);
    near(statistics(p).day, actual24);
    assert.equal(evaluate(p, defaults).settlements, (7 * 24) / p.hours);
  }
});

test('net PnL reconciles to cashflows and returns use spot capital plus independent reserve', () => {
  const r = evaluate(pairs[0], defaults);
  near(r.quantity, 1.25);
  near(r.funding, 294);
  near(r.basis, -30);
  near(r.fees, 120);
  near(r.impact, 24.444444444444443);
  near(r.net, 119.55555555555556);
  near(r.capital, 125000);
  near(r.returnPct, (r.net / 125000) * 100);
  near(r.cashNeed, 15000 + 30 + 575 + 60 + r.impact / 2);
  assert.equal(r.status, '可研究');
});

test('basis up is a loss; favorable basis cannot make zero or negative funding pass positive-carry eligibility', () => {
  const up = evaluate(pairs[0], { ...defaults, basisMove: 20 });
  const down = evaluate(pairs[0], { ...defaults, basisMove: -20 });
  near(down.net - up.net, 400);
  const zero = evaluate(pairs[0], { ...defaults, basisMove: -50, fundingScale: 0 });
  assert.ok(zero.net > 0);
  assert.equal(zero.gates[1].pass, false);
  assert.equal(zero.breakEven, null);
  assert.equal(evaluate(pairs[0], { ...defaults, fundingScale: -50 }).status, '暂缓');
});

test('capacity and cash remain independent hard constraints even with profitable carry', () => {
  const thin = evaluate(pairs[3], { ...defaults, depthLoss: 80 });
  assert.ok(thin.net > 0);
  assert.equal(thin.covered, false);
  assert.equal(thin.status, '暂缓');
  const jump = evaluate(pairs[0], { ...defaults, priceShock: 35 });
  assert.ok(jump.net > 0);
  assert.ok(jump.cashLeft < 0);
  assert.equal(jump.status, '暂缓');
  assert.equal(evaluate(pairs[6], defaults).status, '待核验');
});
