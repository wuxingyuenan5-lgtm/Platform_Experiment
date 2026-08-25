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

function watch(_sources, callback) {
  callback();
}

function createFakeTimers() {
  let now = 0;
  let nextId = 1;
  const queue = [];

  function setTimeoutStub(fn, delay = 0) {
    const id = nextId++;
    queue.push({ id, at: now + delay, fn });
    queue.sort((left, right) => left.at - right.at || left.id - right.id);
    return id;
  }

  function clearTimeoutStub(id) {
    const index = queue.findIndex((item) => item.id === id);
    if (index >= 0) queue.splice(index, 1);
  }

  async function advance(ms) {
    now += ms;
    while (queue.length && queue[0].at <= now) {
      const item = queue.shift();
      await item.fn();
    }
  }

  return { setTimeoutStub, clearTimeoutStub, advance };
}

function createEventTarget(initialVisibility = 'visible') {
  const listeners = new Map();
  return {
    visibilityState: initialVisibility,
    addEventListener(type, handler) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(handler);
    },
    removeEventListener(type, handler) {
      listeners.get(type)?.delete(handler);
    },
    dispatch(type) {
      for (const handler of listeners.get(type) || []) {
        handler();
      }
    },
    listenerCount(type) {
      return (listeners.get(type) || new Set()).size;
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

async function flushMicrotasks() {
  await Promise.resolve();
  await Promise.resolve();
}

async function main() {
  const root = path.resolve(__dirname, '..');
  const recoveryPath = path.join(
    root,
    'src/views/strategy/funding-carry/composables/fundingExecutionRecovery.ts',
  );
  const composablePath = path.join(
    root,
    'src/views/strategy/funding-carry/composables/useFundingWorkspace.ts',
  );
  const pagePath = path.join(root, 'src/views/strategy/funding-carry/index.vue');

  const pageSource = fs.readFileSync(pagePath, 'utf8');
  assert.equal(pageSource.includes('@/data/sample/funding'), false);

  const storage = createMemoryStorage();
  const timers = createFakeTimers();
  const documentStub = createEventTarget('visible');
  const windowStub = createEventTarget();
  const mountedHandlers = [];
  const unmountedHandlers = [];

  global.localStorage = storage;
  global.setTimeout = timers.setTimeoutStub;
  global.clearTimeout = timers.clearTimeoutStub;
  global.document = documentStub;
  global.window = windowStub;

  const recovery = loadTsModule(recoveryPath, {});
  const executionContextCalls = [];
  const submitCalls = [];
  const workspaceCalls = [];
  const groups = [
    {
      instructionId: 'open-1',
      openInstructionId: 'open-1',
      perpetualSymbol: 'BTCUSDT',
      spotSymbol: 'BTCUSDT',
      hedgedQuantity: '0.020',
      authoritativeClosedQuantity: '0.005',
      pendingCloseQuantity: '0.002',
      resultUnknownReservedQuantity: '0',
      remainingClosableQuantity: '0.013',
      lifecycleState: 'active',
      status: 'reconciling',
      workspaceState: { executionState: 'reconciling' },
    },
    {
      instructionId: 'open-history-1',
      openInstructionId: 'open-history-1',
      perpetualSymbol: 'ETHUSDT',
      spotSymbol: 'ETHUSDT',
      hedgedQuantity: '1.000',
      authoritativeClosedQuantity: '1.000',
      pendingCloseQuantity: '0',
      resultUnknownReservedQuantity: '0',
      remainingClosableQuantity: '0',
      lifecycleState: 'history',
      status: 'completed',
      workspaceState: { executionState: 'completed' },
    },
  ];
  const workspaceByInstruction = new Map([
    [
      'instruction-open-1',
      [
        {
          instruction: { instructionId: 'instruction-open-1' },
          workspaceState: { executionState: 'executing' },
        },
        {
          instruction: { instructionId: 'instruction-open-1' },
          workspaceState: { executionState: 'reconciling' },
        },
        {
          instruction: { instructionId: 'instruction-open-1' },
          workspaceState: { executionState: 'completed' },
        },
      ],
    ],
    [
      'instruction-close-1',
      [
        {
          instruction: { instructionId: 'instruction-close-1' },
          workspaceState: { executionState: 'result_unknown' },
        },
      ],
    ],
  ]);

  const apiStub = {
    async getFundingExecutionContext(params) {
      executionContextCalls.push(params);
      return {
        accountId: 'bybit-live-main',
        venue: 'CRYPTO_TEST',
        spotSymbol: 'BTCUSDT',
        perpetualSymbol: 'BTCUSDT',
        symbolOptions: [
          {
            baseAsset: 'BTC',
            quoteCurrency: 'USDT',
            perpetualSymbol: 'BTCUSDT',
            spotSymbol: 'BTCUSDT',
            perpetualInstrumentId: 'instrument_btc_perp',
            spotInstrumentId: 'instrument_btc_spot',
          },
        ],
        spotQuote: { mid: '80000' },
        perpetualQuote: { mid: '79990' },
        suggestedQuantity: '0.001',
        requestedNotional: params?.notional ?? '100',
        activeReservation: {
          currency: 'USDT',
          activeReserved: '0',
          fundingReserved: '0',
          crossReserved: '0',
          fundingAvailable: '1000',
        },
        sharedResourceClaims: [],
        controlledLiveReadiness: { ready: true },
        runtime: { liveWriteEnabled: false },
        dataQualityState: 'complete',
        asOf: '2026-08-25T00:00:00Z',
      };
    },
    async getFundingPositionGroups(scope) {
      assert.equal(scope, 'all');
      return groups;
    },
    async submitFundingInstruction(payload) {
      submitCalls.push(payload);
      if (payload.action === 'open') {
        return {
          instruction: { instructionId: 'instruction-open-1' },
          workspaceState: { executionState: 'executing' },
        };
      }
      return {
        instruction: { instructionId: 'instruction-close-1' },
        workspaceState: { executionState: 'result_unknown' },
      };
    },
    async getFundingInstructionWorkspace(instructionId) {
      workspaceCalls.push(['instruction', instructionId]);
      const queue = workspaceByInstruction.get(instructionId) || [];
      return (
        queue.shift() || {
          instruction: { instructionId },
          workspaceState: { executionState: 'completed' },
        }
      );
    },
    async getFundingInstructionWorkspaceByIdempotency(idempotencyKey) {
      workspaceCalls.push(['idempotency', idempotencyKey]);
      return {
        instruction: { instructionId: 'instruction-open-1' },
        workspaceState: { executionState: 'executing' },
      };
    },
  };

  const composable = loadTsModule(composablePath, {
    vue: {
      computed,
      ref,
      watch,
      onMounted: (handler) => mountedHandlers.push(handler),
      onBeforeUnmount: (handler) => unmountedHandlers.push(handler),
    },
    '@/api/platform/fundingWorkspace': apiStub,
    './fundingExecutionRecovery': recovery,
  });

  const { useFundingWorkspace } = composable;
  const { readFundingDraft, writeFundingDraft } = recovery;

  writeFundingDraft(
    {
      idempotencyKey: 'funding:recover-open-1',
      action: 'open',
      perpetualSymbol: 'BTCUSDT',
      spotSymbol: 'BTCUSDT',
      quantity: '0.001',
      state: 'executing',
    },
    storage,
  );

  const workspace = useFundingWorkspace();
  for (const handler of mountedHandlers) {
    handler();
  }
  await flushMicrotasks();
  if (!workspaceCalls.length) {
    await workspace.refreshAll();
  }

  assert.equal(workspace.quantityInput.value, '0.001');
  assert.equal(workspace.selectedCloseInstructionId.value, 'open-1');
  assert.equal(workspaceCalls[0][0], 'idempotency');
  assert.equal(workspace.pendingDraft.value.instructionId, 'instruction-open-1');

  await workspace.submit('open');
  let draft = readFundingDraft(storage);
  assert.equal(submitCalls[0].action, 'open');
  assert.match(submitCalls[0].idempotencyKey, /^funding:/);
  assert.equal(draft.instructionId, 'instruction-open-1');
  assert.equal(draft.state, 'executing');

  await timers.advance(1000);
  await flushMicrotasks();
  draft = readFundingDraft(storage);
  assert.equal(draft.state, 'reconciling');

  documentStub.visibilityState = 'hidden';
  documentStub.dispatch('visibilitychange');
  const callsWhileHidden = workspaceCalls.length;
  await timers.advance(3000);
  await flushMicrotasks();
  assert.equal(workspaceCalls.length, callsWhileHidden);

  documentStub.visibilityState = 'visible';
  documentStub.dispatch('visibilitychange');
  await flushMicrotasks();
  assert.equal(readFundingDraft(storage), null);

  workspace.selectCloseInstruction('open-1');
  await workspace.submit('close');
  draft = readFundingDraft(storage);
  assert.equal(submitCalls[1].action, 'close');
  assert.equal(submitCalls[1].targetOpenInstructionId, 'open-1');
  assert.equal(submitCalls[1].quantity, '0.013');
  assert.equal(draft.state, 'result_unknown');

  windowStub.dispatch('online');
  await flushMicrotasks();
  assert.equal(workspace.pendingDraft.value.state, 'result_unknown');

  assert.equal(documentStub.listenerCount('visibilitychange'), 1);
  assert.equal(windowStub.listenerCount('online'), 1);
  for (const handler of unmountedHandlers) {
    handler();
  }
  assert.equal(documentStub.listenerCount('visibilitychange'), 0);
  assert.equal(windowStub.listenerCount('online'), 0);

  console.log('funding workspace recovery behavior passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
