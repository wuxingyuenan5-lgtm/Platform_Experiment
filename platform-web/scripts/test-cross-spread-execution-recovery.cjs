const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const ts = require('typescript');

function createMemoryStorage() {
  const values = new Map();
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    removeItem(key) {
      values.delete(key);
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
}

function ref(value) {
  return { value };
}

function computed(getter) {
  return {
    get value() {
      return getter();
    },
  };
}

function loadTsModule(modulePath, stubs) {
  const source = fs.readFileSync(modulePath, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
    fileName: modulePath,
  }).outputText;
  const loaded = new Module(modulePath, module);
  loaded.filename = modulePath;
  loaded.paths = Module._nodeModulePaths(path.dirname(modulePath));
  const originalRequire = loaded.require.bind(loaded);
  loaded.require = (request) => {
    if (request in stubs) return stubs[request];
    return originalRequire(request);
  };
  loaded._compile(compiled, modulePath);
  return loaded.exports;
}

function createOptions() {
  const events = { refreshes: 0, upserts: [] };
  return {
    events,
    options: {
      qtyOz: ref(1),
      qtyInput: ref('1'),
      bybitQty: ref(1),
      mt5Lot: ref(0.1),
      quantityRules: ref(null),
      openDirection: ref('long'),
      executionMode: ref('market'),
      closeExecutionMode: ref('market'),
      takeProfitExecution: ref('market'),
      stopLossExecution: ref('market'),
      openLimitStrategy: ref('fok'),
      takeProfitLimitStrategy: ref('fok'),
      stopLossLimitStrategy: ref('fok'),
      closeLimitStrategy: ref('fok'),
      triggerSpread: ref(null),
      acceptableSpread: ref(null),
      takeProfitSpread: ref(null),
      stopLossSpread: ref(null),
      closeLimitSpread: ref(null),
      longSpread: ref(1.23),
      shortSpread: ref(-1.23),
      exitPlans: ref([
        { planId: 'plan-a', status: 'active' },
        { planId: 'plan-b', status: 'active' },
      ]),
      closeOrders: ref([
        { id: 'plan-a', qtyOz: 1, direction: 'LONG_SPREAD' },
        { id: 'plan-b', qtyOz: 2, direction: 'SHORT_SPREAD' },
      ]),
      upsertExitPlan(plan) {
        events.upserts.push(plan);
      },
      async refreshExitPlans() {
        events.refreshes += 1;
        return 'ok';
      },
      async refreshSnapshot() {
        events.refreshes += 1;
      },
      async refreshObservability() {
        events.refreshes += 1;
      },
    },
  };
}

async function main() {
  const root = path.resolve(__dirname, '..');
  const recoveryPath = path.join(
    root,
    'src/views/strategy/spread-carry/composables/crossSpreadExecutionRecovery.ts',
  );
  const composablePath = path.join(
    root,
    'src/views/strategy/spread-carry/composables/useCrossSpreadExecution.ts',
  );

  const storage = createMemoryStorage();
  global.localStorage = storage;

  const recovery = loadTsModule(recoveryPath, {});
  const openCalls = [];
  const closeCalls = [];
  const openResponses = [];
  const closeResponses = [];

  const lifecycleStub = {
    async openCrossSpreadMarket(payload) {
      openCalls.push(payload);
      assert.ok(openResponses.length > 0, 'missing open response');
      return openResponses.shift();
    },
    async closeCrossSpreadMarket(planId, payload) {
      closeCalls.push({ planId, payload });
      assert.ok(closeResponses.length > 0, 'missing close response');
      return closeResponses.shift();
    },
  };

  const composable = loadTsModule(composablePath, {
    vue: { computed, ref },
    '@/api/platform/crossSpreadLifecycle': lifecycleStub,
    './crossSpreadExecutionRecovery': recovery,
  });

  const { useCrossSpreadExecution } = composable;
  const { PENDING_EXECUTION_STORAGE_KEY, readExecutionDraft } = recovery;

  const { options } = createOptions();
  const execution = useCrossSpreadExecution(options);

  openResponses.push({ executionBatch: { status: 'executing' }, limitExecution: null });
  execution.prepareOpenDraft('long');
  await execution.confirmOrder();
  const openDraft = readExecutionDraft(storage);
  assert.equal(openCalls.length, 1);
  assert.ok(openDraft?.idempotencyKey);
  assert.equal(openCalls[0].idempotencyKey, openDraft.idempotencyKey);
  assert.notEqual(storage.getItem(PENDING_EXECUTION_STORAGE_KEY), null);

  openResponses.push({ executionBatch: { status: 'manual_intervention' }, limitExecution: null });
  await execution.resumePendingExecution();
  assert.equal(openCalls.length, 2);
  assert.equal(openCalls[1].idempotencyKey, openDraft.idempotencyKey);
  assert.equal(readExecutionDraft(storage).idempotencyKey, openDraft.idempotencyKey);

  openResponses.push({ executionBatch: { status: 'hedged' }, limitExecution: null });
  await execution.resumePendingExecution();
  assert.equal(openCalls.length, 3);
  assert.equal(openCalls[2].idempotencyKey, openDraft.idempotencyKey);
  assert.equal(readExecutionDraft(storage), null);

  closeResponses.push(
    {
      exitPlan: { planId: 'plan-a', status: 'result_unknown' },
      executionBatch: { status: 'result_unknown' },
      limitExecution: null,
    },
    {
      exitPlan: { planId: 'plan-b', status: 'manual_intervention' },
      executionBatch: { status: 'manual_intervention' },
      limitExecution: null,
    },
  );
  execution.openConfirm('CLOSE_ALL');
  await execution.confirmOrder();
  const closeAllDraft = readExecutionDraft(storage);
  assert.equal(closeCalls.length, 2);
  assert.equal(closeAllDraft.plans.length, 2);
  assert.notEqual(closeAllDraft.plans[0].idempotencyKey, closeAllDraft.plans[1].idempotencyKey);
  assert.deepEqual(
    closeCalls.map((entry) => entry.payload.idempotencyKey),
    closeAllDraft.plans.map((plan) => plan.idempotencyKey),
  );
  assert.deepEqual(readExecutionDraft(storage).plans, closeAllDraft.plans);

  closeResponses.push(
    {
      exitPlan: { planId: 'plan-a', status: 'completed' },
      executionBatch: { status: 'completed' },
      limitExecution: null,
    },
    {
      exitPlan: { planId: 'plan-b', status: 'failed' },
      executionBatch: { status: 'failed' },
      limitExecution: null,
    },
  );
  await execution.resumePendingExecution();
  assert.equal(closeCalls.length, 4);
  assert.deepEqual(
    closeCalls.slice(2).map((entry) => entry.payload.idempotencyKey),
    closeAllDraft.plans.map((plan) => plan.idempotencyKey),
  );
  assert.equal(readExecutionDraft(storage), null);

  console.log('cross-spread execution recovery behavior passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
