const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const ts = require('typescript');
const vue = require('vue');
const { parse, compileScript } = require('vue/compiler-sfc');

function mountPanel(api) {
  const filename = path.resolve(__dirname, '../src/views/hedgeBoard/components/TerminalDetailPanel.vue');
  const { descriptor } = parse(fs.readFileSync(filename, 'utf8'), { filename });
  const source = compileScript(descriptor, { id: 'market-layout-test' }).content;
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const user = vue.reactive({ getUserInfo: { userId: 'alice' } });
  const cleanups = [];
  const mocks = {
    vue: { ...vue, onBeforeUnmount(fn) { cleanups.push(fn); } },
    '@/api/hedgeResearch': api,
    '@/store/modules/user': { useUserStore: () => user },
  };
  const module = { exports: {} };
  new Function('require', 'module', 'exports', code)((name) => mocks[name] || require(name), module, module.exports);
  const props = vue.reactive({ marketId: 'us', readonly: false, columns: [], rotationHeatmap: [], groups: [{
    label: '指数', rows: [{ id: 'us-spy', name: '标普', symbol: 'SPY', spark: [10,11], price: '$11', d1: '+1%' }],
  }] });
  const scope = vue.effectScope();
  const panel = scope.run(() => module.exports.default.setup(props, { expose() {}, emit() {} }));
  return { panel, props, user, close() { cleanups.forEach(fn => fn()); scope.stop(); } };
}

const settle = async () => { await vue.nextTick(); await new Promise(resolve => setImmediate(resolve)); };

test('market preferences persist only metadata; failed writes rollback and empty/reset survive', async () => {
  let saved = null, version = 0, fail = false;
  const m = mountPanel({
    async getMarketLayout() { return { groups: saved, rowVersion: version }; },
    async saveMarketLayout(market, groups, expectedVersion) {
      assert.equal(market, 'us'); assert.equal(expectedVersion, version);
      if (fail) throw new Error('offline');
      saved = groups; version++;
      return { groups, rowVersion: version };
    },
  });
  try {
    await settle();
    await m.panel.persistGroups();
    assert.deepEqual(Object.keys(saved[0].rows[0]).sort(), ['id','name','symbol','tvSymbol']);
    assert.equal(m.panel.editableGroups.value[0].rows[0].price, '$11');
    fail = true;
    m.panel.editableGroups.value[0].rows = [];
    await m.panel.persistGroups();
    assert.equal(m.panel.editableGroups.value[0].rows.length, 1);
    assert.match(m.panel.layoutMessage.value, /保存失败/);
    fail = false;
    m.panel.editableGroups.value = [];
    await m.panel.persistGroups();
    await m.panel.loadLayout();
    assert.deepEqual(m.panel.editableGroups.value, []);
    await m.panel.persistGroups(true);
    assert.equal(saved, null);
    assert.equal(m.panel.editableGroups.value[0].rows.length, 1);
  } finally { m.close(); }
});

test('late response from the previous account cannot replace the new account layout', async () => {
  let resolveFirst;
  let reads = 0;
  const m = mountPanel({
    getMarketLayout() {
      reads++;
      return reads === 1 ? new Promise(resolve => { resolveFirst = resolve; }) : Promise.resolve({ groups: [], rowVersion: 2 });
    },
  });
  try {
    m.user.getUserInfo.userId = 'bob';
    await settle();
    resolveFirst({ groups: [{label:'Private',rows:[]}], rowVersion: 9 });
    await settle();
    assert.equal(m.panel.layoutVersion.value, 2);
    assert.deepEqual(m.panel.editableGroups.value, []);
  } finally { m.close(); }
});

test('version conflict reloads the account list and never retries a stale replacement', async () => {
  let reads = 0, writes = 0;
  const m = mountPanel({
    async getMarketLayout() { return { groups: reads++ ? [] : null, rowVersion: reads }; },
    async saveMarketLayout() { writes++; throw { status: 409 }; },
  });
  try {
    await settle();
    await m.panel.persistGroups();
    assert.equal(writes, 1);
    assert.deepEqual(m.panel.editableGroups.value, []);
    assert.equal(m.panel.layoutSaving.value, false);
    assert.match(m.panel.layoutMessage.value, /其他页面更新/);
  } finally { m.close(); }
});


test('research writes restore missing in-memory CSRF after reload and fail closed', async () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../src/api/hedgeResearch.ts'), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  let interceptor, token = '', refreshes = 0, fail = false;
  const client = { interceptors: { request: { use(fn) { interceptor = fn; } }, response: { use() {} } } };
  const module = { exports: {} };
  new Function('require', 'module', 'exports', code)((name) => {
    if (name === 'axios') return { default: { create: () => client } };
    if (name === '@/api/platform/userSystem') return {
      getUserSystemCsrfToken: () => token,
      async getCurrentAuthentication() { refreshes++; if (fail) throw new Error('session expired'); token = 'current-csrf'; },
      clearUserSystemSessionMemory() { token = ''; }, UserSystemApiError: Error,
    };
    return require(name);
  }, module, module.exports);
  const headers = new Map();
  await interceptor({method:'GET',headers});
  assert.equal(refreshes, 0);
  await interceptor({method:'PUT',headers});
  assert.equal(refreshes, 1);
  assert.equal(headers.get('X-CSRF-Token'), 'current-csrf');
  await interceptor({method:'PUT',headers});
  assert.equal(refreshes, 1);
  token = ''; fail = true;
  await assert.rejects(interceptor({method:'PUT',headers:new Map()}), /session expired/);
});
