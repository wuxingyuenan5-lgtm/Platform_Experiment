const assert = require('node:assert/strict');
const test = require('node:test');
const load = require('./load-strategy-module.cjs')({});
const { etfFlowDemo, demoHolders } = load('src/views/hedgeBoard/aShare/components/etfFlowDemo.ts');

test('synthetic assets reconcile to funds and never use real fund codes', () => {
  const result = etfFlowDemo({ days: 20 });
  assert.equal(result.status, 'demo');
  assert.equal(result.assets.length, 6);
  assert(result.funds.every(f => f.code.startsWith('DEMO-')));
  const funds = result.funds.reduce((s, f) => s + Number(f.current.flow), 0);
  const assets = result.assets.reduce((s, f) => s + Number(f.current.flow), 0);
  assert(Math.abs(funds - assets) < 1e-9);
  assert.deepEqual(etfFlowDemo({ days: 20 }), result);
  assert(result.previousEnd < result.start);
  assert(result.funds.every(f => f.current.expected === 20 && f.previous.expected === 20));
});

test('quarter comparison changes values and recovers earlier broad outflows', () => {
  const result = etfFlowDemo({ start: '2026-10-01', end: '2026-11-09', previous_start: '2026-01-01', previous_end: '2026-09-30' });
  const broad = result.assets.find(a => a.name === '股票宽基');
  assert(Number(broad.previous.flow) < 0 && Number(broad.current.flow) > 0);
  assert(Math.abs(Number(broad.recovery) - Number(broad.current.flow) / -Number(broad.previous.flow) * 100) < 1e-9);
  assert.notEqual(broad.current.flow, etfFlowDemo({ days: 5 }).assets.find(a => a.name === '股票宽基').current.flow);
});

test('demo holder changes reconcile and include entries and exits', () => {
  const rows = demoHolders('DEMO-02');
  assert(rows.some(h => h.state === '新进') && rows.some(h => h.state === '退出'));
  assert(rows.reduce((s, h) => s + h.after, 0) <= 100);
  assert(rows.every(h => h.delta === h.after - h.before));
});
