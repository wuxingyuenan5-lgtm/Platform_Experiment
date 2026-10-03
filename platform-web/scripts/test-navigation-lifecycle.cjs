const assert = require('node:assert/strict');
const test = require('node:test');
const vue = require('vue');
const { createRouter, createMemoryHistory } = require('vue-router');
const createLoader = require('./load-strategy-module.cjs');

function loadProgressGuard(progress) {
  return createLoader({
    '@/hooks/setting/useTransitionSetting': {
      useTransitionSetting: () => ({
        getOpenNProgress: vue.ref(false),
        getOpenPageLoading: vue.ref(true),
      }),
    },
    '@/utils/http/axios/axiosCancel': {},
    'ant-design-vue': {},
    '@/utils/log': {},
    '@/logics/mitt/routeChange': {},
    './permissionGuard': {},
    './stateGuard': {},
    './paramMenuGuard': {},
    '@/settings/projectSetting': {},
    nprogress: progress,
  })('src/router/guard/index.ts').createProgressGuard;
}

test('warm navigation shows progress during verification and clears on success or error', async () => {
  const calls = [];
  const router = createRouter({
    history: createMemoryHistory(),
    routes: ['/one', '/two', '/error'].map((path) => ({
      path,
      component: {},
      meta: { loaded: true },
    })),
  });
  loadProgressGuard({ start: () => calls.push('start'), done: () => calls.push('done') })(router);
  let release;
  router.beforeResolve((to) => {
    if (to.path === '/two') return new Promise((resolve) => (release = resolve));
    if (to.path === '/error') throw new Error('chunk unavailable');
  });
  await router.push('/one');
  const pending = router.push('/two');
  while (!release) await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(calls, ['start', 'done', 'start']);
  release();
  await pending;
  assert.deepEqual(calls, ['start', 'done', 'start', 'done']);
  await assert.rejects(router.push('/error'), /chunk unavailable/);
  assert.deepEqual(calls.slice(-2), ['start', 'done']);
});

test('cancelled old navigation cannot clear newer progress', () => {
  const hooks = {};
  let completed = 0;
  loadProgressGuard({ start() {}, done: () => completed++ })({
    beforeEach: (fn) => (hooks.before = fn),
    afterEach: (fn) => (hooks.after = fn),
    onError: (fn) => (hooks.error = fn),
  });
  const older = { path: '/one' };
  const newer = { path: '/two' };
  hooks.before(older);
  hooks.before(newer);
  hooks.after(older);
  assert.equal(completed, 0);
  hooks.after(newer);
  assert.equal(completed, 1);
});

test('strategy query switching keeps component state; other routes keep their existing identity', async () => {
  const { getPageKey } = createLoader()('src/layouts/page/transition.ts');
  let mounts = 0;
  let unmounts = 0;
  const node = () => ({ children: [] });
  const renderer = vue.createRenderer({
    createElement: node,
    createText: node,
    createComment: node,
    setText() {},
    setElementText() {},
    patchProp() {},
    parentNode: (el) => el.parent,
    nextSibling: () => null,
    insert: (el, parent) => {
      el.parent = parent;
      parent.children.push(el);
    },
    remove: (el) => {
      el.parent.children = el.parent.children.filter((item) => item !== el);
    },
  });
  const Page = vue.defineComponent({
    setup() {
      vue.onMounted(() => mounts++);
      vue.onUnmounted(() => unmounts++);
      return () => vue.h('section');
    },
  });
  const route = vue.reactive({
    path: '/strategy/management',
    fullPath: '/strategy/management?section=capital',
    meta: { reuseOnQueryChange: true },
  });
  const app = renderer.createApp({ render: () => vue.h(Page, { key: getPageKey(route) }) });
  app.mount(node());
  route.fullPath = '/strategy/management?section=pnl';
  await vue.nextTick();
  assert.equal(mounts, 1);
  assert.equal(unmounts, 0);
  route.path = '/other';
  route.fullPath = '/other?record=1';
  route.meta.reuseOnQueryChange = false;
  await vue.nextTick();
  route.fullPath = '/other?record=2';
  await vue.nextTick();
  assert.equal(mounts, 3);
  assert.equal(unmounts, 2);
  app.unmount();
});
