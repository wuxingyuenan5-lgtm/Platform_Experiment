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
  global.localStorage = storage;
  global.setTimeout = (fn) => {
    fn();
    return 1;
  };
  global.clearTimeout = () => {};

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
      remainingClosableQuantity: '0.015',
      status: 'completed',
      workspaceState: { executionState: 'completed' },
    },
  ];
  const workspaceResponses = [
    {
      instruction: { instructionId: 'instruction-open-1' },
      workspaceState: { executionState: 'executing' },
    },
    {
      instruction: { instructionId: 'instruction-open-1' },
      workspaceState: { executionState: 'result_unknown' },
    },
    {
      instruction: { instructionId: 'instruction-open-1' },
      workspaceState: { executionState: 'completed' },
    },
  ];

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
    async getFundingPositionGroups() {
      return groups;
    },
    async submitFundingInstruction(payload) {
      submitCalls.push(payload);
      return workspaceResponses.shift();
    },
    async getFundingInstructionWorkspace(instructionId) {
      workspaceCalls.push(instructionId);
      return workspaceResponses.shift();
    },
  };

  const composable = loadTsModule(composablePath, {
    vue: { computed, ref, watch },
    '@/api/platform/fundingWorkspace': apiStub,
    './fundingExecutionRecovery': recovery,
  });

  const { useFundingWorkspace } = composable;
  const { readFundingDraft } = recovery;
  const workspace = useFundingWorkspace();

  await workspace.refreshAll();
  assert.equal(workspace.quantityInput.value, '0.001');
  assert.equal(executionContextCalls.length >= 1, true);

  await workspace.submit('open');
  let draft = readFundingDraft(storage);
  assert.equal(submitCalls[0].action, 'open');
  assert.match(submitCalls[0].idempotencyKey, /^funding:/);
  assert.equal(draft.instructionId, 'instruction-open-1');
  assert.equal(draft.state, 'executing');

  await workspace.refreshInstruction();
  draft = readFundingDraft(storage);
  assert.equal(workspaceCalls.length, 1);
  assert.equal(draft.state, 'result_unknown');

  await workspace.refreshInstruction();
  assert.equal(readFundingDraft(storage), null);

  workspaceResponses.push({
    instruction: { instructionId: 'instruction-close-1' },
    workspaceState: { executionState: 'executing' },
  });
  workspace.selectCloseInstruction('open-1');
  await workspace.submit('close');
  assert.equal(submitCalls[1].action, 'close');
  assert.equal(submitCalls[1].targetOpenInstructionId, 'open-1');
  assert.equal(submitCalls[1].quantity, '0.015');

  console.log('funding workspace recovery behavior passed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
