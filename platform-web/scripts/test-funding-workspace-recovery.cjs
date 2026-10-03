const assert = require('node:assert/strict');
const test = require('node:test');
const vue = require('vue');
const createLoader = require('./load-strategy-module.cjs');

global.window = new EventTarget();
const fixtures = new Set();
test.afterEach(() => {
  for (const fixture of fixtures) fixture.stop();
  fixtures.clear();
});

async function settle() {
  for (let index = 0; index < 8; index++) {
    await vue.nextTick();
    await new Promise(setImmediate);
  }
}

function setup({
  draft = null,
  failSubmit = false,
  submitStatus = null,
  lookupMissing = false,
} = {}) {
  const values = new Map();
  global.localStorage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
  const visibility = vue.ref('visible');
  const mounted = [],
    unmounted = [],
    submissions = [],
    reads = [];
  let state = 'executing';
  let contextBarrier, positionsBarrier;
  const executionVisible = vue.ref(true);
  let contextReads = 0,
    positionsReads = 0;
  let contextError = false;
  const user = vue.reactive({ authentication: { user: { userId: 'ceo-one', role: 'ceo' } } });
  const context = {
    accountId: 'bybit-test',
    venue: 'test',
    perpetualSymbol: 'BTCUSDT',
    spotSymbol: 'BTCUSDT',
    symbolOptions: [],
    spotQuote: { mid: '80000' },
    perpetualQuote: { mid: '79990' },
    suggestedQuantity: '0.001',
    openSizing: {
      spotQuantity: '0.001001',
      expectedSpotNetQuantity: '0.000999999',
      perpetualQuantity: '0.001',
      roundingResidualQuantity: '-0.000000001',
      spotBaseFeeRate: '0.001',
      valid: true,
      reason: null,
    },
    quantityStep: { spot: '0.000001', perpetual: '0.001' },
    minimumQuantity: { spot: '0.000001', perpetual: '0.001' },
    tickSize: { spot: '0.01', perpetual: '0.01' },
    requestedNotional: '100',
    controlledLiveReadiness: { ready: true },
    dataQualityState: 'complete',
  };
  const group = {
    instructionId: 'open-one',
    perpetualSymbol: 'BTCUSDT',
    spotSymbol: 'BTCUSDT',
    remainingClosableQuantity: '0.013',
    lifecycleState: 'active',
  };
  const response = () => ({
    instruction: { instructionId: 'instruction-one' },
    executionBatch: null,
    workspaceState: { executionState: state },
  });
  const load = createLoader({
    vue: {
      ...vue,
      onMounted: (fn) => mounted.push(fn),
      onBeforeUnmount: (fn) => unmounted.push(fn),
      onUnmounted: (fn) => unmounted.push(fn),
      onActivated() {},
      onDeactivated() {},
    },
    '@vueuse/core': { useDocumentVisibility: () => visibility, refDebounced: (value) => value },
    'ant-design-vue': { Modal: { confirm: (options) => options.onOk() } },
    '@/store/modules/user': { useUserStore: () => user },
    '@/api/platform/fundingWorkspace': {
      getFundingExecutionContext: async () => {
        contextReads += 1;
        if (contextBarrier) await contextBarrier;
        if (contextError) throw new Error('quote timeout');
        return context;
      },
      getFundingPositionGroups: async () => {
        positionsReads += 1;
        if (positionsBarrier) await positionsBarrier;
        return [
          {
            ...group,
            status: state,
            cumulativePerpetualFill: state === 'manual_intervention' ? '0.001' : '0',
            residualQuantity: state === 'manual_intervention' ? '0.001' : '0',
          },
        ];
      },
      submitFundingInstruction: async (input) => {
        submissions.push(input);
        if (failSubmit)
          throw Object.assign(new Error('submit rejected'), {
            response: submitStatus ? { status: submitStatus } : undefined,
          });
        return response();
      },
      getFundingInstructionWorkspace: async (id) => {
        reads.push(['id', id]);
        return response();
      },
      getFundingInstructionWorkspaceByIdempotency: async (id) => {
        reads.push(['key', id]);
        if (lookupMissing)
          throw Object.assign(new Error('not found'), { response: { status: 404 } });
        return response();
      },
    },
  });
  const queries = load('src/api/platform/strategyQueries.ts');
  queries.strategyQueryClient.setDefaultOptions({
    ...queries.strategyQueryClient.getDefaultOptions(),
    queries: { ...queries.strategyQueryClient.getDefaultOptions().queries, gcTime: Infinity },
  });
  queries.setStrategyQuerySession('ceo-one', 'session-one');
  const recovery = load('src/views/strategy/funding-carry/composables/fundingExecutionRecovery.ts');
  if (draft) recovery.writeFundingDraft(draft);
  const { useFundingWorkspace } = load(
    'src/views/strategy/funding-carry/composables/useFundingWorkspace.ts',
  );
  const scope = vue.effectScope();
  const workspace = scope.run(() => useFundingWorkspace(executionVisible));
  mounted.forEach((fn) => fn());
  const fixture = {
    workspace,
    recovery,
    queries,
    visibility,
    user,
    submissions,
    reads,
    context,
    executionVisible,
    readCounts: () => ({ context: contextReads, positions: positionsReads }),
    blockContext: () => {
      let release;
      contextBarrier = new Promise((resolve) => {
        release = resolve;
      });
      return () => {
        contextBarrier = null;
        release();
      };
    },
    blockPositions: () => {
      let release;
      positionsBarrier = new Promise((resolve) => {
        release = resolve;
      });
      return () => {
        positionsBarrier = null;
        release();
      };
    },
    setState: (next) => {
      state = next;
    },
    failContext: () => {
      contextError = true;
    },
    stop: () => {
      unmounted.forEach((fn) => fn());
      scope.stop();
      queries.strategyQueryClient.clear();
    },
  };
  fixtures.add(fixture);
  return fixture;
}

function pendingDraft() {
  return {
    idempotencyKey: 'original-intent',
    ownerUserId: 'ceo-one',
    action: 'open',
    perpetualSymbol: 'BTCUSDT',
    spotSymbol: 'BTCUSDT',
    quantity: '0.001',
    state: 'submitting',
  };
}

test('reload recovers the original intent by read and never resubmits it', async () => {
  const fixture = setup({ draft: pendingDraft() });
  await settle();
  assert.deepEqual(fixture.reads[0], ['key', 'original-intent']);
  assert.equal(fixture.submissions.length, 0);
  assert.equal(fixture.workspace.pendingDraft.value.instructionId, 'instruction-one');
  assert.equal(fixture.workspace.canSubmit.value, false);
  fixture.setState('completed');
  await fixture.workspace.refreshInstruction();
  await settle();
  assert.equal(fixture.recovery.readFundingDraft(), null);
  assert.equal(fixture.workspace.pendingDraft.value, null);
});

test('partial close keeps its target and Decimal quantity; unknown result stays pending', async () => {
  const fixture = setup();
  await settle();
  fixture.workspace.selectCloseInstruction('open-one');
  assert.equal(fixture.workspace.canClose.value, true);
  fixture.setState('result_unknown');
  await fixture.workspace.submit('close');
  await settle();
  assert.equal(fixture.submissions.length, 1);
  assert.equal(fixture.submissions[0].targetOpenInstructionId, 'open-one');
  assert.equal(fixture.submissions[0].quantity, '0.013');
  assert.equal(fixture.workspace.pendingDraft.value.state, 'result_unknown');
  await fixture.workspace.submit('close');
  assert.equal(fixture.submissions.length, 1);
  window.dispatchEvent(new Event('online'));
  await settle();
  assert.equal(fixture.submissions.length, 1);
  assert.equal(fixture.workspace.pendingDraft.value.state, 'result_unknown');
});

test('a manual pause refreshes the filled leg and residual without releasing or replaying the draft', async () => {
  const fixture = setup({ draft: pendingDraft() });
  await settle();
  assert.equal(fixture.workspace.positionGroups.value[0].cumulativePerpetualFill, '0');
  fixture.setState('manual_intervention');
  await fixture.workspace.refreshInstruction();
  await settle();
  assert.equal(fixture.workspace.positionGroups.value[0].status, 'manual_intervention');
  assert.equal(fixture.workspace.positionGroups.value[0].cumulativePerpetualFill, '0.001');
  assert.equal(fixture.workspace.positionGroups.value[0].residualQuantity, '0.001');
  assert.equal(fixture.workspace.pendingDraft.value.state, 'manual_intervention');
  assert.equal(fixture.workspace.canSubmit.value, false);
  assert.equal(fixture.submissions.length, 0);
});

test('a timed-out submit retains one identity and recovers with GET only', async () => {
  const fixture = setup({ failSubmit: true });
  await settle();
  await fixture.workspace.submit('open');
  await settle();
  assert.equal(fixture.submissions.length, 1);
  const identity = fixture.submissions[0].idempotencyKey;
  assert.equal(fixture.recovery.readFundingDraft().idempotencyKey, identity);
  await fixture.workspace.refreshInstruction();
  await settle();
  assert.equal(fixture.submissions.length, 1);
  assert.equal(fixture.workspace.pendingDraft.value.idempotencyKey, identity);
});

test('failed market refresh blocks trading and a new user cannot inherit the draft', async () => {
  const fixture = setup();
  await settle();
  assert.equal(fixture.workspace.canSubmit.value, true);
  fixture.failContext();
  await fixture.workspace.refreshContext();
  await settle();
  assert.equal(fixture.workspace.canSubmit.value, false);
  fixture.recovery.writeFundingDraft(pendingDraft());
  fixture.user.authentication = { user: { userId: 'member-two', role: 'member' } };
  fixture.queries.setStrategyQuerySession('member-two', 'session-two');
  await settle();
  assert.equal(fixture.workspace.pendingDraft.value, null);
  assert.equal(fixture.workspace.activeInstruction.value, null);
  assert.equal(fixture.workspace.canSubmit.value, false);
});

test('background polling stops while hidden and unmount releases its observers', async () => {
  const fixture = setup({ draft: pendingDraft() });
  await settle();
  fixture.visibility.value = 'hidden';
  await settle();
  const count = fixture.reads.length;
  await new Promise((resolve) => setTimeout(resolve, 3_100));
  await settle();
  assert.equal(fixture.reads.length, count);
  fixture.visibility.value = 'visible';
  await settle();
  assert.ok(fixture.reads.length > count);
  fixture.stop();
  fixtures.delete(fixture);
  assert.equal(fixture.queries.strategyQueryClient.getQueryCache().getAll().length, 0);
});

test('a persisted rejection clears the draft and never resubmits', async () => {
  const fixture = setup({ draft: pendingDraft() });
  fixture.setState('failed');
  await settle();
  await fixture.workspace.refreshInstruction();
  await settle();
  assert.equal(fixture.workspace.pendingDraft.value, null);
  assert.equal(fixture.workspace.workspaceState.value, 'failed');
  assert.equal(fixture.recovery.readFundingDraft(), null);
  assert.equal(fixture.submissions.length, 0);
});

test('an explicit rejection only releases the draft after a read proves no instruction exists', async () => {
  const fixture = setup({ failSubmit: true, submitStatus: 422, lookupMissing: true });
  await settle();
  await fixture.workspace.submit('open');
  await settle();
  assert.equal(fixture.submissions.length, 1);
  assert.ok(fixture.reads.length > 0);
  assert.equal(fixture.workspace.pendingDraft.value, null);
});

test('FOK carries the user price while malformed prices and quantities cannot submit', async () => {
  const fixture = setup();
  await settle();
  fixture.workspace.executionPolicy.value = 'fok';
  assert.equal(fixture.workspace.canSubmit.value, false);
  fixture.workspace.perpetualLimitPriceInput.value = '80000.001';
  assert.equal(fixture.workspace.canSubmit.value, false);
  fixture.workspace.perpetualLimitPriceInput.value = '80000.01';
  assert.equal(fixture.workspace.canSubmit.value, true);
  await fixture.workspace.submit('open');
  assert.equal(fixture.submissions[0].executionPolicy, 'fok');
  assert.equal(fixture.submissions[0].perpetualLimitPrice, '80000.01');
});

test('partial close shortcuts round down to the venue step and retain the selected group', async () => {
  const fixture = setup();
  await settle();
  fixture.workspace.selectCloseInstruction('open-one');
  fixture.workspace.selectCloseFraction(25);
  assert.equal(fixture.workspace.closeQuantityInput.value, '0.003');
  fixture.workspace.selectCloseFraction(100);
  assert.equal(fixture.workspace.closeQuantityInput.value, '0.013');
  assert.equal(fixture.workspace.selectedCloseInstructionId.value, 'open-one');
  fixture.workspace.closeQuantityInput.value = '0.0135';
  assert.equal(fixture.workspace.canClose.value, false);
});

test('open retains the authoritative perpetual target and distinct fee-adjusted spot sizing', async () => {
  const fixture = setup();
  await settle();
  assert.equal(fixture.workspace.quantityInput.value, '0.001');
  assert.equal(fixture.context.openSizing.spotQuantity, '0.001001');
  assert.equal(fixture.workspace.canSubmit.value, true);
  await fixture.workspace.submit('open');
  assert.equal(fixture.submissions[0].quantity, '0.001');
  assert.equal(fixture.submissions[0].expectedPerpetualQuantity, '0.001');
  assert.equal(fixture.recovery.readFundingDraft().expectedPerpetualQuantity, '0.001');
});

test('editing quantity invalidates the old sizing until the matching preview returns', async () => {
  const fixture = setup();
  await settle();
  fixture.workspace.quantityInput.value = '0.002';
  assert.equal(fixture.workspace.canSubmit.value, false);
  await settle();
  assert.equal(fixture.workspace.canSubmit.value, false);
  await fixture.workspace.submit('open');
  assert.equal(fixture.submissions.length, 0);
});

test('background refresh retains a still-fresh preview without blocking input', async () => {
  const fixture = setup();
  await settle();
  assert.equal(fixture.workspace.canSubmit.value, true);
  const release = fixture.blockContext();
  const pending = fixture.workspace.refreshContext();
  await settle();
  assert.equal(fixture.workspace.loading.value, true);
  assert.equal(fixture.workspace.canSubmit.value, true);
  fixture.workspace.notionalInput.value = '200';
  assert.equal(fixture.workspace.canSubmit.value, false);
  release();
  await pending;
});

test('accepted submission feedback does not wait for the positions table', async () => {
  const fixture = setup();
  await settle();
  fixture.setState('accepted');
  const release = fixture.blockPositions();
  let timeout;
  try {
    const result = await Promise.race([
      fixture.workspace.submit('open'),
      new Promise((_, reject) => {
        timeout = setTimeout(() => reject(new Error('table blocks receipt')), 500);
      }),
    ]);
    assert.equal(result.workspaceState.executionState, 'accepted');
    assert.equal(fixture.workspace.submitting.value, false);
    assert.equal(fixture.workspace.pendingDraft.value.state, 'accepted');
    assert.equal(fixture.submissions.length, 1);
  } finally {
    clearTimeout(timeout);
    release();
  }
  await settle();
});

test('analysis section pauses execution market and position polling', async () => {
  const fixture = setup();
  await settle();
  fixture.executionVisible.value = false;
  await settle();
  const before = fixture.readCounts();
  await new Promise((resolve) => setTimeout(resolve, 3_100));
  assert.deepEqual(fixture.readCounts(), before);
  fixture.executionVisible.value = true;
  await settle();
  assert.ok(fixture.readCounts().context > before.context);
  assert.ok(fixture.readCounts().positions > before.positions);
});
