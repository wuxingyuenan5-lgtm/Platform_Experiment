const assert = require('node:assert/strict');
const test = require('node:test');

let stateModulePromise;

function loadStateModule() {
  if (!stateModulePromise) {
    const moduleUrl = new URL(
      '../src/views/strategy/management/composables/strategyManagementOverviewState.ts',
      `file://${__filename.replace(/\\/g, '/')}`,
    );
    stateModulePromise = import(moduleUrl.href);
  }
  return stateModulePromise;
}

function overviewItems() {
  return [
    {
      deskKey: 'funding',
      sortOrder: 10,
      operatingStatus: 'active',
      latestRunStatus: 'completed',
    },
    {
      deskKey: 'crossSpread',
      sortOrder: 20,
      operatingStatus: 'active',
      latestRunStatus: null,
    },
    {
      deskKey: 'domesticOverseas',
      sortOrder: 30,
      operatingStatus: 'paused',
      latestRunStatus: null,
    },
    { deskKey: 'dip', sortOrder: 40, operatingStatus: 'active', latestRunStatus: null },
    {
      deskKey: 'shortLineTraderL',
      sortOrder: 50,
      operatingStatus: 'active',
      latestRunStatus: null,
    },
    {
      deskKey: 'shortLineTraderW',
      sortOrder: 60,
      operatingStatus: 'active',
      latestRunStatus: null,
    },
  ];
}

test('management overview success returns six strategies in stable order', async () => {
  const { createStrategyManagementOverviewStore } = await loadStateModule();
  const store = createStrategyManagementOverviewStore(async () => overviewItems());
  await store.refresh();

  assert.equal(store.loading.value, false);
  assert.equal(store.error.value, null);
  assert.equal(store.empty.value, false);
  assert.equal(store.hasData.value, true);
  assert.deepEqual(
    store.items.value.map((item) => item.deskKey),
    ['funding', 'crossSpread', 'domesticOverseas', 'dip', 'shortLineTraderL', 'shortLineTraderW'],
  );
});

test('management overview request failure enters error state', async () => {
  const { createStrategyManagementOverviewStore } = await loadStateModule();
  const store = createStrategyManagementOverviewStore(async () => {
    throw new Error('backend unavailable');
  });
  await store.refresh();

  assert.equal(store.loading.value, false);
  assert.equal(store.error.value, '策略管理总览暂不可用');
  assert.equal(store.empty.value, false);
  assert.equal(store.hasData.value, false);
  assert.deepEqual(store.items.value, []);
});

test('management overview empty result enters empty state', async () => {
  const { createStrategyManagementOverviewStore } = await loadStateModule();
  const store = createStrategyManagementOverviewStore(async () => []);
  await store.refresh();

  assert.equal(store.loading.value, false);
  assert.equal(store.error.value, null);
  assert.equal(store.empty.value, true);
  assert.equal(store.hasData.value, false);
  assert.deepEqual(store.items.value, []);
});

test('read-only strategy latest run null does not change active operating status', async () => {
  const { createStrategyManagementOverviewStore } = await loadStateModule();
  const store = createStrategyManagementOverviewStore(async () => overviewItems());
  await store.refresh();

  const dip = store.items.value.find((item) => item.deskKey === 'dip');
  assert.ok(dip);
  assert.equal(dip.operatingStatus, 'active');
  assert.equal(dip.latestRunStatus, null);
});

test('URL desk and section restoration remains effective', async () => {
  const { normalizeManagementSection, resolveManagementDesk } = await loadStateModule();
  const items = overviewItems();
  assert.equal(resolveManagementDesk('shortLineTraderW', items), 'shortLineTraderW');
  assert.equal(resolveManagementDesk('missingDesk', items), 'funding');
  assert.equal(normalizeManagementSection('orders'), 'orders');
  assert.equal(normalizeManagementSection('capital'), 'capital');
  assert.equal(normalizeManagementSection('something-else'), 'pnl');
});
