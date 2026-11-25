const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vm = require('node:vm');
const vue = require('vue');

function evaluate(source, modules, globals = {}) {
  const exports = {};
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  vm.runInNewContext(code, { exports, require: name => modules[name] || {}, ...globals });
  return exports;
}
const root = path.resolve(__dirname, '../src');
const flush = () => new Promise(setImmediate);

test('single-fund callers stay lightweight; the restored workspace explicitly requests group history', async () => {
  const calls = [];
  const api = evaluate(fs.readFileSync(path.join(root, 'api/etfTracking.ts'), 'utf8'), {
    './hedgeResearch': { researchRequest: async request => calls.push(request) },
  });
  await api.getEtfDetail('510310');
  await api.getEtfDetail('510310', undefined, true);
  assert.equal(calls[0].params.include_group, false);
  assert.equal(calls[1].params.include_group, true);
});

test('restored fund search, saved favorites, group data, and hidden-view reads remain independent', async () => {
  const source = fs.readFileSync(path.join(root, 'views/hedgeBoard/aShare/components/EtfDetailedWorkspace.vue'), 'utf8');
  const model = evaluate(fs.readFileSync(path.join(root, 'views/hedgeBoard/aShare/components/etfTrackingModel.ts'), 'utf8'), {});
  const hooks = {}, calls = [], saved = new Map(), cache = new Map();
  cache.set('etf:510310', { meta: { code: '510310' }, members: [] });
  const meta = code => ({ code, name: code === '510310' ? '易方达' : '华夏', display_group: '沪深300', latest_combined_ratio_pct: '10' });
  const detail = { meta: meta('510310'), groupLabel: '沪深300', series: [
    { date: '2026-11-05', etf_qfq_close: '4', flow_yi: null },
    { date: '2026-11-06', etf_qfq_close: '4.1', flow_yi: '0' },
  ], group: [{ date: '2026-11-05', flow_yi: null }, { date: '2026-11-06', flow_yi: '0' }],
    margin: [], groupMargin: [], disclosures: [], sources: {market: {status: 'ready'}},
    members: [{ meta: meta('510310'), series: [], margin: [] }, { meta: meta('510330'), series: [], margin: [] }] };
  const props = vue.reactive({ refreshKey: 0 });
  const scope = vue.effectScope();
  const s = scope.run(() => evaluate(source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1] +
    '\nexports.state = { query, filtered, favorites, toggleFavorite, onlyFavorites, detail, trendFlow, trendBlocks };', {
      vue: { ...vue, onMounted: fn => hooks.mount = fn, onBeforeUnmount: fn => hooks.unmount = fn,
        onActivated: fn => hooks.activate = fn, onDeactivated: fn => hooks.deactivate = fn },
      '@/api/etfTracking': { getEtfCatalog: async () => ({ items: [meta('510310'), meta('510330')] }),
        getEtfDetail: async (code, signal, group) => { calls.push({code, signal, group}); return detail; } },
      '@/store/modules/user': { useUserStore: () => ({getUserInfo: {userId: 'test'}}) },
      './etfTrackingModel': model,
      '../../composables/researchWorkspace': { useResearchViewState: (_key, initial) => vue.ref(initial),
        useResearchSnapshots: () => ({get: key => cache.get(key), set: (key, value) => cache.set(key, value)}) },
    }, { AbortController, defineProps: () => props, defineEmits: () => () => {},
      localStorage: {getItem: key => saved.get(key) || null, setItem: (key, value) => saved.set(key, value)},
      window: {addEventListener() {}, removeEventListener() {}} }).state);
  try {
    await flush();
    assert.equal(calls.length, 1, 'must not reuse the lightweight detail for grouped tables');
    assert.equal(calls[0].group, true);
    assert.equal(s.detail.value.members.length, 2);
    assert.equal(s.trendFlow.value, null, 'unknown flow remains missing');
    assert.equal(s.trendBlocks.value.length, 3);
    s.query.value = '华夏';
    assert.equal(s.filtered.value.length, 1);
    s.toggleFavorite('510330');
    s.onlyFavorites.value = true;
    assert.equal(s.filtered.value[0].code, '510330');
    assert.equal(saved.get('etf-tracking:test'), '["510330"]');
    hooks.deactivate();
    props.refreshKey++;
    await flush();
    assert.equal(calls.length, 1, 'inactive views must not request data');
    hooks.activate();
    await flush();
    assert.equal(calls.length, 2, 'an explicit refresh while hidden must run on reactivation');
    assert.equal(s.detail.value.members.length, 2);
    assert.equal(calls[0].signal.aborted, true);
  } finally { hooks.unmount(); scope.stop(); }
});
