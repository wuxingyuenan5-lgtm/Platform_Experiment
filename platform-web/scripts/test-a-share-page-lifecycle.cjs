const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vue = require('vue');
const ts = require('typescript');
const { parse, compileScript } = require('@vue/compiler-sfc');

test('cached embedded research pages recreate their document after activation and keep the sandbox', async () => {
  const filename = path.resolve(
    __dirname,
    '../src/views/hedgeBoard/aShare/components/NationalEtfPanel.vue',
  );
  const compiled = compileScript(parse(fs.readFileSync(filename, 'utf8')).descriptor, {
    id: 'national-cache-test',
    inlineTemplate: true,
  });
  const code = ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', code)(require, mod, mod.exports);
  const previousWindow = global.window;
  const listeners = new Set();
  global.window = {
    addEventListener: (_, fn) => listeners.add(fn),
    removeEventListener: (_, fn) => listeners.delete(fn),
  };
  const node = (tag) => ({ tag, props: {}, children: [], parent: null });
  const renderer = vue.createRenderer({
    createElement: node,
    createText: node,
    createComment: node,
    setText() {},
    setElementText() {},
    patchProp: (el, key, _, value) => {
      el.props[key] = value;
    },
    parentNode: (el) => el.parent,
    nextSibling: () => null,
    insert(el, parent) {
      if (el.parent) el.parent.children = el.parent.children.filter((n) => n !== el);
      el.parent = parent;
      parent.children.push(el);
    },
    remove(el) {
      if (el.parent) el.parent.children = el.parent.children.filter((n) => n !== el);
      el.parent = null;
    },
  });
  const shown = vue.ref(true),
    root = node('root');
  const other = vue.defineComponent({ render: () => vue.h('div') });
  const app = renderer.createApp({
    render: () =>
      vue.h(
        vue.KeepAlive,
        { max: 2 },
        {
          default: () =>
            shown.value ? vue.h(mod.exports.default, { view: 'futures' }) : vue.h(other),
        },
      ),
  });
  const flush = async () => {
    await vue.nextTick();
    await new Promise(setImmediate);
  };
  try {
    app.mount(root);
    await flush();
    const initial = root.children.find((n) => n.tag === 'iframe');
    assert.equal(initial.props.sandbox, 'allow-scripts');
    assert.equal(initial.props.src, '/api/v1/research/a-share/national-etf/page?view=futures');
    shown.value = false;
    await flush();
    shown.value = true;
    await flush();
    const returned = root.children.find((n) => n.tag === 'iframe');
    assert.notEqual(returned, initial);
    assert.equal(returned.props.sandbox, 'allow-scripts');
    assert.equal(listeners.size, 1);
  } finally {
    app.unmount();
    global.window = previousWindow;
  }
  assert.equal(listeners.size, 0);
});

test('A-share page returns reuse instances without making the last data read look newer', async () => {
  const loaded = [],
    events = [];
  const panel = vue.defineComponent({
    props: ['refreshKey'],
    emits: ['ready'],
    setup(props, { emit }) {
      const record = { ready: () => emit('ready'), removed: false };
      loaded.push(record);
      vue.onMounted(record.ready);
      vue.watch(() => props.refreshKey, record.ready);
      vue.onUnmounted(() => {
        record.removed = true;
      });
      return () => vue.h('article');
    },
  });
  const filename = path.resolve(__dirname, '../src/views/hedgeBoard/aShare/ASharePageContent.vue');
  const compiled = compileScript(parse(fs.readFileSync(filename, 'utf8')).descriptor, {
    id: 'a-share-page-test',
    inlineTemplate: true,
  });
  const code = ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', code)(
    (name) => {
      if (name === 'vue') return { ...vue, defineAsyncComponent: () => panel };
      if (name.endsWith('VisibleChart'))
        return vue.defineComponent({
          setup:
            (_, { slots }) =>
            () =>
              vue.h('div', slots.default?.()),
        });
      throw new Error('Unexpected dependency: ' + name);
    },
    mod,
    mod.exports,
  );
  const node = () => ({ children: [], parent: null });
  const renderer = vue.createRenderer({
    createElement: node,
    createText: node,
    createComment: node,
    setText() {},
    setElementText() {},
    patchProp() {},
    parentNode: (el) => el.parent,
    nextSibling: () => null,
    insert(el, parent) {
      if (el.parent) el.parent.children = el.parent.children.filter((n) => n !== el);
      el.parent = parent;
      parent.children.push(el);
    },
    remove(el) {
      if (el.parent) el.parent.children = el.parent.children.filter((n) => n !== el);
      el.parent = null;
    },
  });
  const current = vue.ref('etf'),
    refreshKey = vue.ref(0);
  const app = renderer.createApp({
    render: () =>
      vue.h(
        vue.KeepAlive,
        { max: 3 },
        {
          default: () =>
            vue.h(mod.exports.default, {
              key: current.value,
              page: current.value,
              title: current.value,
              dashboard: null,
              dashboardError: '',
              dashboardLoading: false,
              refreshKey: refreshKey.value,
              onReady: (...e) => events.push(e),
            }),
        },
      ),
  });
  const flush = async () => {
    await vue.nextTick();
    await new Promise(setImmediate);
  };
  app.mount(node());
  try {
    await flush();
    const initialRead = events.at(-1)[1];
    current.value = 'capital';
    await flush();
    assert.equal(events.at(-1)[0], 'capital');
    const count = events.length;
    loaded[0].ready();
    await flush();
    assert.equal(events.length, count, 'inactive late response must not notify the active page');
    current.value = 'etf';
    await flush();
    assert.equal(loaded.length, 2);
    const readBeforeReturn = events.at(-1)[1];
    assert.ok(readBeforeReturn >= initialRead);
    current.value = 'capital';
    await flush();
    current.value = 'etf';
    await flush();
    assert.equal(events.at(-1)[1], readBeforeReturn, 'return alone must not extend freshness');
    refreshKey.value++;
    await flush();
    assert.equal(loaded.length, 2, 'refresh must update existing content');
  } finally {
    app.unmount();
  }
  assert.equal(
    loaded.every((r) => r.removed),
    true,
  );
});
