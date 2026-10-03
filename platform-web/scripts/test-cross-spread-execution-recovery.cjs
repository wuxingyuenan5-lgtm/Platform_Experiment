const assert = require('node:assert/strict');

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

function watch(source, callback, options) {
  if (options?.immediate) callback(source());
  return () => {};
}

function settleAsyncWork() {
  return new Promise((resolve) => setImmediate(resolve));
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

const test = require('node:test');
const createLoader = require('./load-strategy-module.cjs');

function fixture() {
  global.localStorage = createMemoryStorage();
  const writes = [],
    reads = [];
  const state = {
    preflight: async () => ({}),
    open: async () => ({ executionBatch: { status: 'hedged' } }),
    close: async () => ({ exitPlan: {}, executionBatch: { status: 'hedged' } }),
    lookup: async () => null,
    batch: async () => {
      throw new Error('Unexpected batch read');
    },
  };
  const load = createLoader({
    vue: { ref, computed, watch },
    '@/store/modules/user': { useUserStore: () => ({ authentication: { user: { role: 'ceo' } } }) },
    '@/api/platform/crossSpreadLifecycle': {
      prepareCrossSpreadExecution: (...args) => state.preflight(...args),
      openCrossSpreadMarket: async (payload) => {
        writes.push({ kind: 'open', payload });
        return state.open(payload);
      },
      closeCrossSpreadMarket: async (planId, payload) => {
        writes.push({ kind: 'close', planId, payload });
        return state.close(planId, payload);
      },
      getCrossSpreadInstruction: async (key) => {
        reads.push(key);
        return state.lookup(key);
      },
    },
    '@/api/platform/trading': { getExecutionBatch: (...args) => state.batch(...args) },
  });
  const recovery = load(
    'src/views/strategy/spread-carry/composables/crossSpreadExecutionRecovery.ts',
  );
  const { useCrossSpreadExecution } = load(
    'src/views/strategy/spread-carry/composables/useCrossSpreadExecution.ts',
  );
  const { options } = createOptions();
  const execution = useCrossSpreadExecution(options);
  return {
    writes,
    reads,
    state,
    options,
    execution,
    recovery,
    remount: () => useCrossSpreadExecution(options),
  };
}

const rejection = () => ({
  response: { status: 409, data: { detail: 'Limit not satisfied; no order submitted' } },
});

test('known filled/rejected close hands off to abnormal handling without locking the browser draft', async () => {
  const f = fixture();
  f.state.close = async () => ({
    exitPlan: {},
    executionBatch: {
      status: 'manual_intervention',
      failureReason: 'MT5 rejected',
      legs: [{ status: 'filled' }, { status: 'failed' }],
    },
  });
  f.execution.openConfirm('CLOSE:plan-a');
  await settleAsyncWork();
  await f.execution.confirmOrder();
  assert.equal(f.recovery.readExecutionDraft(), null);
  assert.equal(f.execution.executionMessageTone.value, 'is-error');
  assert.equal(f.writes.length, 1);
});

test('MT5 recovery confirmation and request retain original identity and describe only remaining leg', async () => {
  const f = fixture();
  Object.assign(f.options.closeOrders.value[0], {
    isAbnormal: true,
    mt5Only: true,
    remainingMt5Lots: 0.01,
    mt5PositionId: 'ticket-target',
    recoveryIdempotencyKey: 'original-close',
  });
  let preflight;
  f.state.preflight = async (request) => {
    preflight = request;
  };
  f.execution.openConfirm('CLOSE:plan-a');
  await settleAsyncWork();
  assert.equal(preflight.exitPlanId, 'plan-a');
  assert.match(f.execution.confirmSummary.value.legs, /BYBIT 已成交，不再下单/);
  assert.match(f.execution.confirmSummary.value.legs, /MT5 0.01 手 · Ticket ticket-target/);
  await f.execution.confirmOrder();
  assert.equal(f.writes[0].payload.idempotencyKey, 'original-close');
});

test('normal close-all excludes abnormal groups', async () => {
  const f = fixture();
  f.options.closeOrders.value[0].isAbnormal = true;
  f.execution.openConfirm('CLOSE_ALL');
  await settleAsyncWork();
  await f.execution.confirmOrder();
  assert.deepEqual(
    f.writes.map((write) => write.planId),
    ['plan-b'],
  );
});

test('cancel and late preflight cannot authorize or contaminate the next confirmation', async () => {
  const f = fixture();
  let rejectOld;
  f.state.preflight = () =>
    new Promise((resolve, reject) => {
      rejectOld = reject;
    });
  f.execution.prepareOpenDraft('long');
  f.execution.cancelConfirmation();
  f.state.preflight = async () => ({});
  f.execution.prepareOpenDraft('short');
  await settleAsyncWork();
  rejectOld(rejection());
  await settleAsyncWork();
  assert.equal(f.execution.confirmGuardMessage.value, '');
  f.options.qtyOz.value = 9;
  assert.equal(f.execution.confirmSummary.value.qty, '1');
  await Promise.all([f.execution.confirmOrder(), f.execution.confirmOrder()]);
  assert.equal(f.writes.length, 1);
  assert.equal(f.writes[0].payload.quantityOz, '1');
  assert.equal(f.writes[0].payload.direction, 'SHORT_SPREAD');
});

test('preflight rejection blocks execution and cancel removes its error', async () => {
  const f = fixture();
  f.state.preflight = async () => {
    throw rejection();
  };
  f.execution.prepareOpenDraft('long');
  await settleAsyncWork();
  await f.execution.confirmOrder();
  assert.match(f.execution.confirmGuardMessage.value, /Limit not satisfied/);
  assert.equal(f.writes.length, 0);
  assert.equal(f.recovery.readExecutionDraft(), null);
  f.execution.cancelConfirmation();
  assert.equal(f.execution.confirmGuardMessage.value, '');
  assert.equal(f.execution.executionMessage.value, '');
});

test('lost response and remount only read the original identity; unknown and absent remain pending', async () => {
  const f = fixture();
  f.state.open = async () => {
    throw new Error('timeout');
  };
  f.execution.prepareOpenDraft('long');
  await settleAsyncWork();
  await f.execution.confirmOrder();
  const key = f.recovery.readExecutionDraft().idempotencyKey;
  await f.execution.resumePendingExecution();
  assert.equal(f.recovery.readExecutionDraft().idempotencyKey, key);
  assert.equal(f.writes.length, 1);
  f.state.lookup = async () => ({
    instructionId: 'original',
    status: 'executing',
    executionBatchId: 'batch',
  });
  f.state.batch = async () => ({
    batchId: 'batch',
    strategyInstanceId: 'strategy_cross_venue_spread_instance_default',
    idempotencyKey: `instruction:${key}`,
    status: 'manual_intervention',
  });
  const recovered = f.remount();
  await settleAsyncWork();
  assert.equal(f.recovery.readExecutionDraft().idempotencyKey, key);
  f.state.batch = async () => ({
    batchId: 'batch',
    strategyInstanceId: 'strategy_cross_venue_spread_instance_default',
    idempotencyKey: `instruction:${key}`,
    status: 'hedged',
  });
  await recovered.resumePendingExecution();
  assert.equal(f.recovery.readExecutionDraft(), null);
  assert.equal(f.writes.length, 1);
  assert.ok(f.reads.every((value) => value === key));
});

test('only explicit rejection plus authoritative absence releases an unaccepted intent', async () => {
  const f = fixture();
  f.state.open = async () => {
    throw rejection();
  };
  f.execution.prepareOpenDraft('long');
  await settleAsyncWork();
  await f.execution.confirmOrder();
  assert.equal(f.recovery.readExecutionDraft(), null);
  assert.equal(f.reads.length, 1);
  f.state.lookup = async () => {
    throw new Error('disconnected');
  };
  f.execution.prepareOpenDraft('long');
  await settleAsyncWork();
  await f.execution.confirmOrder();
  assert.ok(f.recovery.readExecutionDraft());
  f.state.lookup = async () => ({
    instructionId: 'original',
    status: 'executing',
    executionBatchId: 'batch',
  });
  f.state.batch = async () => ({
    batchId: 'wrong-batch',
    strategyInstanceId: 'strategy_cross_venue_spread_instance_default',
    status: 'hedged',
  });
  await f.execution.resumePendingExecution();
  assert.ok(f.recovery.readExecutionDraft());
  assert.match(f.execution.executionMessage.value, /身份不一致/);
  assert.equal(f.writes.length, 2);
});

test('an absent original instruction can release the local lock without placing a new order', async () => {
  const f = fixture();
  f.recovery.persistExecutionDraft({
    kind: 'CLOSE',
    idempotencyKey: 'old-close-key',
    planId: 'plan-a',
    payload: { quantityOz: '1', executionMode: 'market', limitStrategy: 'fok' },
  });
  await f.execution.resumePendingExecution();
  assert.equal(f.execution.pendingDraftAbsent.value, true);
  assert.ok(f.recovery.readExecutionDraft());
  await f.execution.clearUnreceivedPendingExecution();
  assert.equal(f.recovery.readExecutionDraft(), null);
  assert.deepEqual(f.reads, ['old-close-key', 'old-close-key', 'old-close-key']);
  assert.equal(f.writes.length, 0);
});

test('clicking close verifies an absent old instruction and opens the normal confirmation', async () => {
  const f = fixture();
  f.recovery.persistExecutionDraft({
    kind: 'CLOSE',
    idempotencyKey: 'old-close-key',
    planId: 'plan-a',
    payload: { quantityOz: '1', executionMode: 'market', limitStrategy: 'fok' },
  });
  await f.execution.resumePendingExecution();
  await f.execution.openConfirm('CLOSE_ALL');
  assert.equal(f.recovery.readExecutionDraft(), null);
  assert.equal(f.execution.confirmVisible.value, true);
  assert.equal(f.writes.length, 0);
  assert.deepEqual(f.reads, ['old-close-key', 'old-close-key', 'old-close-key']);
});

test('clicking close keeps the old lock if the final verification fails', async () => {
  const f = fixture();
  f.recovery.persistExecutionDraft({
    kind: 'CLOSE',
    idempotencyKey: 'old-close-key',
    planId: 'plan-a',
    payload: { quantityOz: '1', executionMode: 'market', limitStrategy: 'fok' },
  });
  await f.execution.resumePendingExecution();
  f.state.lookup = async () => {
    throw new Error('read failed');
  };
  await f.execution.openConfirm('CLOSE_ALL');
  assert.ok(f.recovery.readExecutionDraft());
  assert.equal(f.execution.confirmVisible.value, false);
  assert.equal(f.writes.length, 0);
});

test('partial close recovery preserves quantity and never resubmits the close', async () => {
  const f = fixture();
  f.state.close = async () => ({ exitPlan: {}, executionBatch: { status: 'manual_intervention' } });
  f.execution.openPartialClose('plan-b', 0.5);
  await settleAsyncWork();
  await f.execution.confirmOrder();
  const draft = f.recovery.readExecutionDraft();
  assert.equal(draft.payload.quantityOz, '0.5');
  f.state.lookup = async () => ({
    instructionId: 'close',
    status: 'completed',
    executionBatchId: 'batch',
  });
  f.state.batch = async () => ({
    batchId: 'batch',
    strategyInstanceId: 'strategy_cross_venue_spread_instance_default',
    idempotencyKey: `instruction:${draft.idempotencyKey}`,
    status: 'hedged',
  });
  await f.execution.resumePendingExecution();
  assert.equal(f.writes.length, 1);
  assert.equal(f.writes[0].planId, 'plan-b');
  assert.equal(f.writes[0].payload.quantityOz, '0.5');
  assert.equal(f.recovery.readExecutionDraft(), null);
});

test('batch close interruption does not dispatch later groups during recovery', async () => {
  const f = fixture();
  f.state.close = async () => ({ exitPlan: {}, executionBatch: { status: 'manual_intervention' } });
  f.execution.openConfirm('CLOSE_ALL');
  await settleAsyncWork();
  await f.execution.confirmOrder();
  const draft = f.recovery.readExecutionDraft();
  assert.equal(f.writes.length, 1);
  assert.equal(draft.plans[0].submitted, true);
  assert.equal(draft.plans[1].submitted, false);
  f.state.lookup = async () => ({
    instructionId: 'first-close',
    status: 'completed',
    executionBatchId: 'batch',
  });
  f.state.batch = async () => ({
    batchId: 'batch',
    strategyInstanceId: 'strategy_cross_venue_spread_instance_default',
    idempotencyKey: `instruction:${draft.plans[0].idempotencyKey}`,
    status: 'hedged',
  });
  await f.execution.resumePendingExecution();
  assert.deepEqual(f.reads, [draft.plans[0].idempotencyKey]);
  assert.equal(f.writes.length, 1);
  assert.equal(f.recovery.readExecutionDraft(), null);
});

test('chase confirmation freezes adverse tolerance and exit settings in the original intent', async () => {
  const f = fixture();
  f.options.executionMode.value = 'limit';
  f.options.openLimitStrategy.value = 'post_only_chase';
  f.options.triggerSpread.value = -10;
  f.options.acceptableSpread.value = 5;
  f.execution.prepareOpenDraft('long');
  await settleAsyncWork();
  f.options.acceptableSpread.value = 20;
  await f.execution.confirmOrder();
  assert.equal(f.writes.length, 1);
  assert.equal(f.writes[0].payload.limitSpread, '-10');
  assert.equal(f.writes[0].payload.maxAdverseSpread, '5');
  assert.equal(f.writes[0].payload.takeProfitMaxAdverseSpread, '5');
  assert.equal(f.writes[0].payload.stopLossMaxAdverseSpread, '5');
});

test('spread-triggered market selection retains threshold and is distinct from immediate market', async () => {
  const f = fixture();
  f.options.closeExecutionMode.value = 'limit';
  f.options.closeLimitStrategy.value = 'market';
  f.options.closeLimitSpread.value = -10;
  f.options.acceptableSpread.value = 0;
  f.execution.openConfirm('CLOSE:plan-a');
  await settleAsyncWork();
  assert.match(f.execution.confirmSummary.value.mode, /触发后市价/);
  await f.execution.confirmOrder();
  assert.equal(f.writes[0].payload.executionMode, 'limit');
  assert.equal(f.writes[0].payload.limitStrategy, 'market');
  assert.equal(f.writes[0].payload.limitSpread, '-10');
  assert.equal(f.writes[0].payload.maxAdverseSpread, '0');
});
