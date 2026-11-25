const assert = require('node:assert/strict');
const test = require('node:test');
const createLoader = require('./load-strategy-module.cjs');

async function withRefresh(load, options, verify) {
  const hooks = {};
  const timers = new Map();
  const listeners = new Set();
  const previous = {
    document: global.document,
    setInterval: global.setInterval,
    clearInterval: global.clearInterval,
    now: Date.now,
  };
  let time = 0;
  let timerId = 0;
  global.document = {
    visibilityState: 'visible',
    addEventListener: (_, callback) => listeners.add(callback),
    removeEventListener: (_, callback) => listeners.delete(callback),
  };
  global.setInterval = (callback, interval) => {
    timers.set(++timerId, { callback, interval });
    return timerId;
  };
  global.clearInterval = (id) => timers.delete(id);
  Date.now = () => time;
  const lifecycle = Object.fromEntries(
    ['onMounted', 'onActivated', 'onDeactivated', 'onUnmounted'].map((name) => [
      name,
      (callback) => {
        hooks[name] = callback;
      },
    ]),
  );
  const { useDashboardRefresh } = createLoader({ vue: lifecycle })(
    'src/views/hedgeBoard/useDashboardRefresh.ts',
  );
  const flush = () => new Promise(setImmediate);
  try {
    useDashboardRefresh(load, options);
    await verify({
      hooks,
      timers,
      listeners,
      flush,
      advance: (ms) => {
        time += ms;
      },
      tick: async () => {
        for (const { callback } of [...timers.values()]) callback();
        await flush();
      },
      visible: async (value) => {
        document.visibilityState = value ? 'visible' : 'hidden';
        for (const callback of [...listeners]) callback();
        await flush();
      },
    });
  } finally {
    hooks.onUnmounted?.();
    global.document = previous.document;
    global.setInterval = previous.setInterval;
    global.clearInterval = previous.clearInterval;
    Date.now = previous.now;
  }
}

test('hidden pages stop their timer, resume one overdue read, and avoid fresh duplicates', async () => {
  let reads = 0;
  await withRefresh(
    async () => {
      reads++;
    },
    {},
    async (h) => {
      h.hooks.onMounted();
      h.hooks.onActivated();
      await h.flush();
      assert.equal(reads, 1);
      assert.equal(h.timers.size, 1);
      await h.visible(false);
      assert.equal(h.timers.size, 0);
      h.advance(30_000);
      await h.visible(true);
      assert.equal(reads, 1);
      await h.visible(false);
      h.advance(40_000);
      await h.visible(true);
      assert.equal(reads, 2);
      await h.visible(true);
      assert.equal(reads, 2);
      h.hooks.onDeactivated();
      assert.equal(h.listeners.size, 0);
      assert.equal(h.timers.size, 0);
      h.advance(60_000);
      await h.tick();
      assert.equal(reads, 2);
      h.hooks.onActivated();
      await h.flush();
      assert.equal(reads, 3);
      h.hooks.onUnmounted();
      assert.equal(h.listeners.size, 0);
      assert.equal(h.timers.size, 0);
    },
  );
});

test('initially hidden charts wait until visible and overlapping reads never accumulate', async () => {
  let reads = 0;
  let finish;
  await withRefresh(
    () => {
      reads++;
      return new Promise((resolve) => {
        finish = resolve;
      });
    },
    {},
    async (h) => {
      await h.visible(false);
      h.hooks.onMounted();
      assert.equal(reads, 0);
      assert.equal(h.timers.size, 0);
      await h.visible(true);
      assert.equal(reads, 1);
      h.advance(60_000);
      await h.tick();
      assert.equal(reads, 1);
      finish();
      await h.flush();
      await h.tick();
      assert.equal(reads, 2);
      finish();
      await h.flush();
    },
  );
});

test('manual initial loading, custom cadence and enabled guards preserve existing call paths', async () => {
  let reads = 0;
  let enabled = false;
  await withRefresh(
    async () => {
      reads++;
    },
    {
      immediate: false,
      intervalMs: 300_000,
      enabled: () => enabled,
    },
    async (h) => {
      h.hooks.onMounted();
      await h.flush();
      assert.equal(reads, 0);
      assert.equal([...h.timers.values()][0].interval, 300_000);
      h.advance(300_000);
      await h.tick();
      assert.equal(reads, 0);
      enabled = true;
      await h.tick();
      assert.equal(reads, 1);
      h.hooks.onDeactivated();
      h.hooks.onActivated();
      await h.flush();
      assert.equal(reads, 1);
    },
  );
});
