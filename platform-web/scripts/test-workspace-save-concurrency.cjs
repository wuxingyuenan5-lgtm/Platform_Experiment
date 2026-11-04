const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { parse, compileScript } = require('@vue/compiler-sfc');
const ts = require('typescript');
const vue = require('vue');

function workspace() {
  const file = path.join(__dirname, '../src/views/dashboard/workspace/PersonalWorkspace.vue');
  const compiled = compileScript(parse(fs.readFileSync(file, 'utf8')).descriptor, { id: 'save-test' });
  const code = ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const requests = [];
  const dependencies = {
    vue: { ...vue, onMounted() {}, onBeforeUnmount() {} },
    '@/store/modules/user': { useUserStore: () => ({ getUserInfo: { userId: 'a' }, getAuthentication: { permissions: ['research.read'] } }) },
    '@/access/userAccess': { hasPermission: () => true },
    '@/api/workspace': {
      saveWorkspace: (kind, items, rowVersion) => new Promise((resolve, reject) => requests.push({ items, rowVersion, resolve, reject })),
      loadSeriesCatalog: async () => [],
      loadWorkspace: async () => ({ items: [], rowVersion: 9 }),
    },
    './moduleCatalog': { moduleCatalog: () => [] },
    'vue-router': { useRouter: () => ({ resolve: () => ({ matched: [] }) }) },
    '@/access/routeAccess': { canAccessMatchedRoute: () => true },
  };
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', code)((name) => {
    if (name in dependencies) return dependencies[name];
    if (name.endsWith('.vue')) return {};
    throw new Error(`Missing test dependency: ${name}`);
  }, mod, mod.exports);
  const state = mod.exports.default.setup({}, { expose() {} });
  state.loading.value = false;
  state.cards.value = [
    { id: 'a', type: 'chart', title: 'A', seriesA: 'x', width: 1 },
    { id: 'b', type: 'chart', title: 'B', seriesA: 'y', width: 1 },
  ];
  return { state, requests };
}

for (const [label, edit] of [
  ['remove', (s) => s.remove('a')],
  ['reorder', (s) => s.move('b', -1)],
  ['edit', (s) => { s.cards.value[0].title = 'new title'; }],
]) {
  test(`late save preserves ${label} and next save uses acknowledged server version`, async () => {
    const { state, requests } = workspace();
    const first = state.save();
    edit(state);
    const edited = JSON.stringify(state.cards.value);
    requests[0].resolve({ items: requests[0].items, rowVersion: 1 });
    await first;
    assert.equal(JSON.stringify(state.cards.value), edited);
    assert.match(state.notice.value, /后续修改尚未保存/);
    const second = state.save();
    assert.equal(requests[1].rowVersion, 1);
    requests[1].resolve({ items: requests[1].items, rowVersion: 2 });
    await second;
    assert.equal(state.notice.value, '已保存到当前账号');
  });
}

test('duplicate save is suppressed and rejected save preserves current edits', async () => {
  const { state, requests } = workspace();
  const pending = state.save();
  await state.save();
  assert.equal(requests.length, 1);
  state.remove('a');
  requests[0].reject(new Error('conflict'));
  await pending;
  assert.deepEqual(state.cards.value.map((c) => c.id), ['b']);
  assert.match(state.error.value, /conflict/);
  assert.equal(state.saving.value, false);
});

test('new load releases save state and ignores the previous generation response', async () => {
  const { state, requests } = workspace();
  const old = state.save();
  await state.load();
  assert.equal(state.saving.value, false);
  const next = state.save();
  assert.equal(requests[1].rowVersion, 9);
  requests[0].resolve({ items: requests[0].items, rowVersion: 1 });
  await old;
  assert.equal(state.cards.value.length, 0);
  assert.equal(state.saving.value, true);
  requests[1].resolve({ items: [], rowVersion: 10 });
  await next;
  assert.equal(state.saving.value, false);
});
