const assert = require('node:assert/strict');
const test = require('node:test');
const vue = require('vue');
const createLoader = require('./load-strategy-module.cjs');

test('offscreen charts wait, mount once near viewport, and survive cached navigation', async () => {
  const observers = [];
  const original = global.IntersectionObserver;
  global.IntersectionObserver = class {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe() { this.connected = true; }
    disconnect() { this.connected = false; }
  };
  let app;
  try {
    const node = () => ({ children: [] });
    const renderer = vue.createRenderer({
      createElement: node, createText: node, createComment: node,
      setText() {}, setElementText() {}, patchProp() {},
      parentNode: (el) => el.parent, nextSibling: () => null,
      insert: (el, parent) => {
        if (el.parent) el.parent.children = el.parent.children.filter((item) => item !== el);
        el.parent = parent;
        parent.children.push(el);
      },
      remove: (el) => { el.parent.children = el.parent.children.filter((item) => item !== el); },
    });
    const VisibleChart = createLoader()('src/views/hedgeBoard/components/VisibleChart.ts').default;
    let mounts = 0;
    const active = vue.ref(true);
    const Chart = vue.defineComponent({ setup() {
      vue.onMounted(() => mounts++);
      return () => vue.h('svg');
    } });
    app = renderer.createApp({ setup: () => () => vue.h(vue.KeepAlive, null, {
      default: () => active.value
        ? vue.h(VisibleChart, null, { default: () => vue.h(Chart) })
        : vue.h('div'),
    }) });
    app.mount(node());
    assert.equal(mounts, 0, 'no chart setup or data request before intersection');
    observers[0].callback([{ isIntersecting: false }]);
    await vue.nextTick();
    assert.equal(mounts, 0);
    active.value = false;
    await vue.nextTick();
    assert.equal(observers[0].connected, false);
    active.value = true;
    await vue.nextTick();
    assert.equal(observers[1].connected, true);
    observers[1].callback([{ isIntersecting: true }]);
    await vue.nextTick();
    assert.equal(mounts, 1);
    assert.equal(observers[1].connected, false);
    active.value = false;
    await vue.nextTick();
    active.value = true;
    await vue.nextTick();
    assert.equal(mounts, 1, 'returning to the page retains the loaded chart');
    assert.equal(observers.length, 2);
  } finally {
    app?.unmount();
    global.IntersectionObserver = original;
  }
});
