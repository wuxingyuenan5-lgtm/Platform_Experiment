const assert = require('node:assert/strict');
const test = require('node:test');
const vue = require('vue');
const createLoader = require('./load-strategy-module.cjs');

function fixture() {
  const hooks = {};
  const calls = { init: 0, set: [], clear: 0, resize: 0, dispose: 0, timers: 0 };
  const element = { offsetWidth: 640, offsetHeight: 0 };
  const instance = {
    clear: () => calls.clear++,
    setOption: (options) => calls.set.push(options),
    resize: () => calls.resize++,
    dispose: () => calls.dispose++,
  };
  const scope = vue.effectScope();
  const load = createLoader({
    vue: {
      ...vue,
      onMounted: (fn) => (hooks.mount = fn),
      onActivated: (fn) => (hooks.activate = fn),
      onDeactivated: (fn) => (hooks.deactivate = fn),
    },
    '@vben/hooks': { useTimeoutFn: () => calls.timers++ },
    '@vueuse/core': {
      tryOnUnmounted: (fn) => (hooks.unmount = fn),
      useDebounceFn: (fn) => fn,
    },
    '@/hooks/event/useEventListener': { useEventListener: () => ({ removeEvent() {} }) },
    '@/hooks/event/useBreakpoint': {
      useBreakpoint: () => ({ widthRef: vue.ref(1200), screenEnum: { MD: 768 } }),
    },
    '@/hooks/setting/useRootSetting': {
      useRootSetting: () => ({ getDarkMode: vue.ref('light') }),
    },
    '@/hooks/setting/useMenuSetting': {
      useMenuSetting: () => ({ getCollapsed: vue.ref(false) }),
    },
    '@/utils/lib/echarts': {
      init: () => {
        calls.init++;
        return instance;
      },
    },
  });
  global.window = {};
  const chart = scope.run(() => load('src/hooks/web/useECharts.ts').useECharts(vue.ref(element)));
  return {
    chart,
    calls,
    hooks,
    element,
    close: () => {
      hooks.unmount();
      scope.stop();
      delete global.window;
    },
  };
}

test('hidden chart schedules no retries and applies only latest options when shown', async () => {
  const f = fixture();
  try {
    await f.chart.setOptions({ series: [{ data: [1] }] });
    await f.chart.setOptions({ series: [{ data: [2] }] });
    assert.equal(f.calls.timers, 0);
    assert.equal(f.calls.init, 0);
    f.element.offsetHeight = 300;
    f.chart.resize();
    assert.equal(f.calls.init, 1);
    assert.equal(f.calls.set.length, 1);
    assert.deepEqual(f.calls.set[0].series[0].data, [2]);
    assert.equal(vue.isProxy(f.calls.set[0]), false);
  } finally {
    f.close();
  }
});

test('cached page pauses updates and resize; reactivation applies queued data', async () => {
  const f = fixture();
  try {
    f.element.offsetHeight = 300;
    await f.chart.setOptions({ series: [] });
    f.hooks.deactivate();
    await f.chart.setOptions({ series: [{ data: [3] }] });
    f.chart.resize();
    assert.equal(f.calls.set.length, 1);
    assert.equal(f.calls.resize, 0);
    f.hooks.activate();
    await vue.nextTick();
    assert.equal(f.calls.set.length, 2);
    assert.equal(f.calls.init, 1);
    assert.equal(f.calls.resize, 1);
  } finally {
    f.close();
  }
});

test('late responses cannot recreate disposed charts and clear=false stays respected', async () => {
  const f = fixture();
  try {
    f.element.offsetHeight = 300;
    await f.chart.setOptions({ series: [] }, false);
    assert.equal(f.calls.clear, 0);
    f.hooks.unmount();
    await f.chart.setOptions({ series: [] });
    f.chart.getInstance();
    assert.equal(f.calls.init, 1);
    assert.equal(f.calls.set.length, 1);
  } finally {
    f.close();
  }
});

test('offscreen charts retain data without painting and resume near the viewport', async () => {
  let intersect;
  let disconnected = false;
  global.IntersectionObserver = class {
    constructor(callback, options) {
      intersect = callback;
      assert.equal(options.rootMargin, '300px');
    }
    observe() {}
    disconnect() {
      disconnected = true;
    }
  };
  const f = fixture();
  try {
    f.element.offsetHeight = 300;
    f.hooks.mount();
    await f.chart.setOptions({ series: [{ data: [1] }] });
    assert.equal(f.chart.getInstance(), null);
    assert.equal(f.calls.init, 0);
    intersect([{ isIntersecting: true }]);
    assert.equal(f.calls.init, 1);
    assert.equal(f.calls.set.length, 1);
    intersect([{ isIntersecting: false }]);
    await f.chart.setOptions({ series: [{ data: [2] }] });
    await f.chart.setOptions({ series: [{ data: [3] }] });
    const resizeCount = f.calls.resize;
    f.chart.resize();
    assert.equal(f.calls.resize, resizeCount);
    assert.equal(f.calls.set.length, 1);
    intersect([{ isIntersecting: true }]);
    assert.equal(f.calls.init, 1);
    assert.equal(f.calls.set.length, 2);
    assert.deepEqual(f.calls.set[1].series[0].data, [3]);
    f.hooks.unmount();
    intersect([{ isIntersecting: true }]);
    assert.equal(f.calls.set.length, 2);
    assert.equal(disconnected, true);
  } finally {
    f.close();
    delete global.IntersectionObserver;
  }
});
