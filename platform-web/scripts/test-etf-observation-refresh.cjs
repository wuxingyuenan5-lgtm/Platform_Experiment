const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const { flowDailyAverage } = require('./load-strategy-module.cjs')()('src/views/hedgeBoard/aShare/components/etfFlowAnalysis.ts');

function setup(mode = 'daily') {
  const text = fs.readFileSync(path.resolve(__dirname, '../src/views/hedgeBoard/aShare/components/EtfObservationPanel.vue'), 'utf8');
  const script = text.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1];
  const hooks = {}, timers = new Map(), events = new Map(), emitted = [];
  const props = { mode };
  let calls = 0, serial = 0;
  let data = { reference: {
    dailyData: { dates: ['2026-11-03'], amount: [10] },
    broadData: { dates: ['2026-11-03'], cats:['A','B'], series:{A:[100], B:[2.0737401]} },
    broadInnovationRatio:{rows:[{date:'2026-11-03',turnoverPct:'35.63'}]},
  }, summary: { date: '2026-11-03',basketCount:220,flow1Yi:'102.0737401',flow5Yi:'510.3687005',flow20Yi:'2041.474802' },
    intradaySummary:{date:'2026-11-03',basketCount:25,flow1Yi:'67.4980719'},
    sources: { reference: { sha256: 'a', status: 'ready' } }, live: {} };
  const document = { hidden: false, addEventListener: (name, fn) => events.set(name, fn), removeEventListener: name => events.delete(name) };
  const cell = value => ({ value });
  const vue = { ref: cell, shallowRef: cell, computed: fn => ({ get value() { return fn(); } }), nextTick: async () => {},
    onMounted: fn => hooks.mount = fn, onBeforeUnmount: fn => hooks.unmount = fn,
    onActivated: fn => hooks.activate = fn, onDeactivated: fn => hooks.deactivate = fn,
    watch: (_, fn) => hooks.refreshKey = fn };
  const output = {};
  const code = ts.transpileModule(script + '\nObject.assign(exports, {snapshot, provenance, summaryCards, error});', {compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }}).outputText;
  vm.runInNewContext(code, { exports: output, defineProps: () => props, defineEmits: () => event => emitted.push(event), withDefaults: value => value, document, Date, URL, console, structuredClone,
    setInterval: fn => { timers.set(++serial, fn); return serial; }, clearInterval: id => timers.delete(id),
    require: name => name === 'vue' ? vue : name === './etfFlowAnalysis' ? { flowDailyAverage } : name === '@/api/etfObservation' ? {getEtfObservation: async () => { calls++; return structuredClone(data); }} : {} });
  return { hooks, timers, events, emitted, document, output, get calls() { return calls; }, update: value => data = value, data: () => data };
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test('daily refresh pauses with cached tabs and removes timers/listeners on unmount', async () => {
  const s = setup(); s.hooks.mount(); await settle();
  assert.equal(s.calls, 1); assert.equal(s.timers.size, 1);
  s.hooks.deactivate(); assert.equal(s.timers.size, 0);
  await s.events.get('visibilitychange')(); assert.equal(s.calls, 1);
  s.hooks.activate(); await settle(); assert.equal(s.calls, 2); assert.equal(s.timers.size, 1);
  s.hooks.unmount(); assert.equal(s.timers.size, 0); assert.equal(s.events.size, 0);
});

test('unchanged revisions retain the snapshot and hidden pages do no periodic reads', async () => {
  const s = setup(); s.hooks.mount(); await settle();
  const original = s.output.snapshot.value;
  await [...s.timers.values()][0](); assert.equal(s.calls, 2);
  assert.equal(s.output.snapshot.value, original);
  s.document.hidden = true; await [...s.timers.values()][0](); assert.equal(s.calls, 2);
  s.document.hidden = false;
  const next = structuredClone(s.data()); next.sources.reference.sha256 = 'b';
  next.reference.dailyData.dates.push('2026-11-04'); next.reference.dailyData.amount.push(20);
  s.update(next); await s.events.get('visibilitychange')();
  assert.notEqual(s.output.snapshot.value, original);
  assert.match(s.output.provenance.value, /宽基ETF统计 · 220只 · 净申购完整日至 2026-11-03/);
  assert.doesNotMatch(s.output.provenance.value, /25只|成交额截至/);
  s.hooks.unmount();
});

test('the existing refresh key rereads archived data', async () => {
  const s = setup(); s.hooks.mount(); await settle();
  await s.hooks.refreshKey(); assert.equal(s.calls, 2);
  assert.deepEqual(s.emitted, ['ready', 'ready']);
  s.hooks.unmount();
});

test('overview cards use broad totals and intraday cards keep the fixed pool', async () => {
  const broad=setup(); broad.hooks.mount(); await settle();
  assert.equal(broad.output.error.value,'');
  const cards=broad.output.summaryCards.value;
  assert.equal(cards.length,5);
  assert.equal(cards[0].value,'+102.07 亿元');
  assert.match(cards[0].detail,/220只/);
  assert.ok(cards.every(card=>!card.label.includes('25只')));
  assert.equal(cards[3].label,'双创成交额比例');
  assert.equal(cards[3].value,'35.63%');
  assert.match(cards[3].definition,/宽基ETF目录/);
  broad.hooks.unmount();
  const fixed=setup('intraday'); fixed.hooks.mount(); await settle();
  const intraday=fixed.output.summaryCards.value;
  assert.equal(intraday[0].value,'+67.50 亿元');
  assert.match(intraday[0].label,/25只ETF/);
  assert.equal(intraday[3].label,'双创成交额比例');
  fixed.hooks.unmount();
});
