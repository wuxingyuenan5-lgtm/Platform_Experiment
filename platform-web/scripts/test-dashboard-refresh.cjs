const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vm = require('node:vm');

function compile(file, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, '../src', file), 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const exports = {};
  vm.runInNewContext(`(function(exports){${js}\n})`, globals)(exports);
  return exports;
}

test('lazy cards share a snapshot, then reload at expiry and session change', async () => {
  let now = 0, calls = 0;
  const { loadDashboardSnapshot: load } = compile('api/dashboardSnapshotCache.ts', { Date: { now: () => now } });
  const fetch = async () => ({ revision: ++calls });
  const first = load('crypto', 'session-a', fetch);
  assert.equal(load('crypto', 'session-a', fetch), first);
  assert.equal((await first).revision, 1);
  now = 30_000;
  assert.equal((await load('crypto', 'session-a', fetch)).revision, 1);
  now = 60_000;
  assert.equal((await load('crypto', 'session-a', fetch)).revision, 2);
  assert.equal((await load('crypto', 'session-b', fetch)).revision, 3);
});

test('a rejected request can recover, and an old session rejection cannot evict a new request', async () => {
  const { loadDashboardSnapshot: load } = compile('api/dashboardSnapshotCache.ts');
  let reject;
  const old = load('macro', 'old', () => new Promise((_, fail) => { reject = fail; }));
  const fresh = load('macro', 'new', async () => ({ revision: 1 }));
  reject(new Error('expired'));
  await assert.rejects(old, /expired/);
  await fresh;
  assert.equal(load('macro', 'new', async () => assert.fail('must stay cached')), fresh);
  await assert.rejects(load('commodity', 'new', async () => { throw new Error('offline'); }), /offline/);
  assert.equal((await load('commodity', 'new', async () => ({ revision: 2 }))).revision, 2);
});

test('refresh pauses when hidden or deactivated and cleans up on unmount', async () => {
  const hooks = {}, listeners = new Map();
  let tick, calls = 0, clears = 0;
  const document = { visibilityState: 'visible', addEventListener: (n, f) => listeners.set(n, f), removeEventListener: (n) => listeners.delete(n) };
  const vue = Object.fromEntries(['onMounted', 'onActivated', 'onDeactivated', 'onUnmounted'].map(n => [n, f => hooks[n] = f]));
  const { useDashboardRefresh } = compile('views/hedgeBoard/useDashboardRefresh.ts', {
    require: () => vue, document, setInterval: f => { tick = f; return 1; }, clearInterval: () => { clears++; },
  });
  useDashboardRefresh(async () => { calls++; });
  hooks.onMounted(); hooks.onActivated();
  await new Promise(setImmediate);
  assert.equal(calls, 1);
  document.visibilityState = 'hidden'; await tick();
  assert.equal(calls, 1);
  document.visibilityState = 'visible'; await listeners.get('visibilitychange')();
  assert.equal(calls, 2);
  hooks.onDeactivated();
  assert.equal(listeners.size, 0);
  hooks.onActivated(); await new Promise(setImmediate);
  assert.equal(calls, 3);
  hooks.onUnmounted();
  assert.equal(listeners.size, 0); assert.equal(clears, 2);
});
