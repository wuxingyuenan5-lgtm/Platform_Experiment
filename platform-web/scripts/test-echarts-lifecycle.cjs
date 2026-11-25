const assert = require('node:assert/strict');
const test = require('node:test');
const vue = require('vue');
const createLoader = require('./load-strategy-module.cjs');

function fixture({ motion = false } = {}) {
  const hooks = {};
  const calls = { init: 0, set: [], replace: [], clear: 0, resize: 0, dispose: 0, timers: 0, reveals: [] };
  const element = { offsetWidth: 640, offsetHeight: 0, querySelectorAll: () => [],
    animate: (frames, options) => { calls.reveals.push({ frames, options }); return { cancel() {} }; },
  };
  const instance = {
    clear: () => calls.clear++,
    setOption: (options, replace) => {
      calls.set.push(options);
      calls.replace.push(replace);
    },
    resize: () => calls.resize++,
    dispose: () => calls.dispose++,
  };
  const scope = vue.effectScope();
  const load = createLoader({
    vue: {
      ...vue,
      getCurrentInstance: () => (motion ? {} : null),
      inject: () => motion,
      onMounted: (fn) => (hooks.mount = fn),
      onBeforeUnmount: () => {},
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

test('all platform charts use ETF motion and atomically replace removed series without clearing', async () => {
  const f = fixture();
  try {
    f.element.offsetHeight = 300;
    const values = [1, null, -2];
    await f.chart.setOptions({
      series: [
        { id: 'flow', type: 'bar', data: values, animation: false, animationEasing: 'exponentialInOut', animationDuration: 1 },
        { id: 'price', data: [3] },
      ],
    });
    assert.equal(f.calls.set.at(-1).series[0].animation, true);
    assert.equal(f.calls.set.at(-1).series[0].animationEasing, 'cubicInOut');
    assert.equal(f.calls.set.at(-1).series[0].animationDuration, 1000);
    assert.equal(f.calls.set.at(-1).series[0].animationDelay, 0);
    await f.chart.setOptions({ series: [{ id: 'flow', type: 'bar', data: values }] });
    assert.equal(f.calls.init, 1);
    assert.equal(f.calls.clear, 0);
    assert.equal(f.calls.set.at(-1).series.length, 1);
    assert.deepEqual(f.calls.replace.at(-1), { notMerge: true });
    assert.deepEqual(f.calls.set.at(-1).series[0].data, values);
    assert.equal(f.calls.set.at(-1).animationDuration, 1000);
    assert.equal(f.calls.set.at(-1).animationDurationUpdate, 500);
    assert.equal(f.calls.set.at(-1).animationEasing, 'cubicInOut');
    assert.equal(f.calls.set.at(-1).animationEasingUpdate, 'cubicInOut');
  } finally {
    f.close();
  }
});

test('the real ECharts engine applies the shared cadence to dataset series and removes obsolete plots', () => {
  // Node 24 exposes navigator without a browser window; load the SSR engine in Node mode.
  const navigatorDescriptor = Object.getOwnPropertyDescriptor(global, 'navigator');
  let echarts;
  try {
    Object.defineProperty(global, 'navigator', { value: undefined, configurable: true });
    echarts = require('echarts');
  } finally {
    if (navigatorDescriptor) Object.defineProperty(global, 'navigator', navigatorDescriptor);
    else delete global.navigator;
  }
  const { motionOptions } = createLoader()('src/hooks/web/chartMotion.ts');
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 640, height: 320 });
  try {
    chart.setOption(motionOptions({
      dataset: { source: [['date', 'value'], ['2026-11-03', 1], ['2026-11-04', null]] },
      xAxis: { type: 'category' }, yAxis: {},
      series: [
        { id: 'flow', type: 'bar', animation: false },
        { id: 'old-price', type: 'line', animationDuration: 1 },
      ],
    }));
    const options = chart.getOption();
    assert.equal(options.series[0].animation, true);
    assert.equal(options.series[0].animationDuration, 1000);
    assert.equal(options.series[1].animationDurationUpdate, 500);
    assert.equal(options.series[1].animationEasingUpdate, 'cubicInOut');
    chart.setOption(motionOptions({
      xAxis: { type: 'category', data: ['a', 'b', 'c'] }, yAxis: {},
      series: [{ id: 'flow', type: 'bar', data: [2, null, -4] }],
    }), { notMerge: true });
    assert.equal(chart.getOption().series.length, 1);
    assert.deepEqual(chart.getOption().series[0].data, [2, null, -4]);
    assert.match(chart.renderToSVGString(), /<svg/);
  } finally {
    chart.dispose();
  }
});

test('dense platform charts retain a lightweight reveal while reduced-motion disables both animations', async () => {
  const f = fixture();
  try {
    f.element.offsetHeight = 300;
    await f.chart.setOptions({ series: [{ data: Array(1201).fill(1) }] });
    await vue.nextTick();
    assert.equal(f.calls.set.at(-1).animation, false);
    assert.equal(f.calls.reveals.length, 1);
    assert.equal(f.calls.reveals[0].options.duration, 1000);
    assert.equal(f.calls.reveals[0].frames[0].clipPath, 'inset(0 100% 0 0)');
    await f.chart.setOptions({ series: Array.from({length: 14}, () => ({ data: Array(730).fill(1) })) });
    await vue.nextTick();
    assert.equal(f.calls.reveals.at(-1).options.duration, 500);
    await f.chart.setOptions({ dataset: { source: Array(1201).fill({ date: '2026-11-04', value: 1 }) }, series: [{ type: 'line', animation: true }] });
    await vue.nextTick();
    assert.equal(f.calls.set.at(-1).series[0].animation, false);
    assert.equal(f.calls.reveals.length, 3);
    window.matchMedia = () => ({ matches: true });
    await f.chart.setOptions({ series: [{ data: [1] }] });
    assert.equal(f.calls.set.at(-1).animation, false);
    assert.equal(f.calls.set.at(-1).animationDurationUpdate, 0);
    assert.equal(f.calls.reveals.length, 3);
    assert.equal(f.calls.clear, 0);
  } finally {
    f.close();
  }
});

test('SVG series draw at the native ETF pace and gestures cancel queued or running animation', async () => {
  const hooks = {};
  const calls = [];
  let cancelled = 0;
  const load = createLoader({
    vue: {
      ...vue,
      getCurrentInstance: () => ({}),
      inject: () => true,
      onActivated: (fn) => (hooks.activate = fn),
      onDeactivated: (fn) => (hooks.deactivate = fn),
      onBeforeUnmount: (fn) => (hooks.unmount = fn),
    },
  });
  const element = vue.shallowRef({
    animate: (frames, options) => {
      calls.push({ kind: 'dense', frames, options });
      return { cancel: () => cancelled++ };
    },
    querySelectorAll: () => ['bar', 'line'].map((kind) => ({
      dataset: { chartKind: kind },
      animate: (frames, options) => {
        calls.push({ kind, frames, options });
        return { cancel: () => cancelled++ };
      },
    })),
  });
  global.window = {};
  try {
    const reveal = load('src/hooks/web/chartMotion.ts').useChartReveal(element);
    await reveal(100);
    assert.equal(calls[0].options.duration, 1000);
    assert.equal(calls[0].frames[0].transform, 'scaleY(0)');
    assert.equal(calls[1].frames[0].clipPath, 'inset(0 100% 0 0)');
    await reveal(100);
    assert.equal(calls[2].options.duration, 500);
    assert.equal(cancelled, 2);
    reveal.cancel();
    assert.equal(cancelled, 4);
    const pending = reveal(100);
    reveal.cancel();
    await pending;
    assert.equal(calls.length, 4);
    hooks.deactivate();
    await reveal(100);
    assert.equal(calls.length, 4);
    hooks.activate();
    await reveal(3001);
    assert.equal(calls.at(-1).kind, 'dense');
    assert.equal(calls.at(-1).options.duration, 500);
    window.matchMedia = () => ({ matches: true });
    await reveal(100);
    assert.equal(calls.length, 5);
    hooks.unmount();
  } finally {
    delete global.window;
  }
});

test('SVG charts with already-loaded data animate when mounted and when returning from a table', async () => {
  const calls = [];
  const scope = vue.effectScope();
  const element = vue.shallowRef();
  const load = createLoader({ vue: { ...vue, onBeforeUnmount() {}, onActivated() {}, onDeactivated() {} } });
  const svg = () => ({
    namespaceURI: 'http://www.w3.org/2000/svg',
    querySelectorAll: () => [],
    animate: (_frames, options) => { calls.push(options.duration); return { cancel() {} }; },
  });
  scope.run(() => load('src/hooks/web/chartMotion.ts').useChartReveal(element));
  try {
    element.value = svg();
    await vue.nextTick(); await vue.nextTick();
    assert.deepEqual(calls, [1000]);
    element.value = undefined;
    await vue.nextTick();
    element.value = svg();
    await vue.nextTick(); await vue.nextTick();
    assert.deepEqual(calls, [1000, 500]);
  } finally {
    scope.stop();
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
    assert.equal(f.calls.resize, 0);
  } finally {
    f.close();
  }
});

test('observer and visibility notifications resize only when dimensions change', async () => {
  const f = fixture();
  try {
    f.element.offsetHeight = 300;
    await f.chart.setOptions({ series: [] });
    for (let i = 0; i < 10; i++) f.chart.resize();
    assert.equal(f.calls.resize, 0);
    f.element.offsetWidth = 800;
    f.chart.resize();
    f.chart.resize();
    assert.equal(f.calls.resize, 1);
    f.element.offsetHeight = 400;
    f.chart.resize();
    assert.equal(f.calls.resize, 2);
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
