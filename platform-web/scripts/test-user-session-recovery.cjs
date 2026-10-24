const assert = require('node:assert/strict');
const test = require('node:test');
const axios = require('axios');
const { createPinia } = require('pinia');
const createLoader = require('./load-strategy-module.cjs');

function setup() {
  const pinia = createPinia();
  const load = createLoader({
    '@/store': { store: pinia },
    '@/api/platform/strategyQueries': { setStrategyQuerySession() {} },
    '@/utils/auth': { clearAuthCache() {} },
    '@/hooks/web/useI18n': { useI18n: () => ({ t: (value) => value }) },
    '@/hooks/web/useMessage': { useMessage: () => ({}) },
    '@/router': { router: {} },
    '@/store/modules/permission': {
      usePermissionStore: () => ({ setPermCodeList() {}, resetState() {} }),
    },
    'ant-design-vue': { message: { destroy() {} } },
  });
  return load('src/store/modules/user.ts').useUserStore(pinia);
}

test('fresh server verification preserves unchanged UI state and applies changed permissions', async () => {
  const original = axios.defaults.adapter;
  let requests = 0;
  let role = 'ceo';
  axios.defaults.adapter = async (config) => {
    requests++;
    return {
      config, status: 200, statusText: 'OK', headers: {},
      data: {
        user: { userId: 'owner', username: 'owner', role },
        permissions: role === 'ceo' ? ['research.write'] : ['profile.read_self'],
        session: { sessionId: 'original' }, csrfToken: 'isolated-csrf',
      },
    };
  };
  try {
    const store = setup();
    await store.hydrateSession(true);
    const info = store.getUserInfo;
    const roles = store.getRoleList;
    const authentication = store.getAuthentication;
    await store.hydrateSession(true);
    assert.equal(requests, 2);
    assert.equal(store.getUserInfo, info);
    assert.equal(store.getRoleList, roles);
    assert.equal(store.getAuthentication, authentication);
    role = 'member';
    await store.hydrateSession(true);
    assert.equal(requests, 3);
    assert.notEqual(store.getUserInfo, info);
    assert.deepEqual(store.getAuthentication.permissions, ['profile.read_self']);
    assert.deepEqual(store.getRoleList, ['member']);
  } finally {
    axios.defaults.adapter = original;
  }
});

for (const loaded of [true, false]) {
  test(`guard retains a loaded page or exposes cold-start retry: loaded=${loaded}`, async () => {
    const notifications = [];
    const store = {
      getUserInfo: {},
      getIsAuthenticated: loaded,
      getSessionUnavailable: true,
      async hydrateSession(force) { assert.equal(force, true); return false; },
    };
    const load = createLoader({
      '@/store/modules/user': { useUserStoreWithOut: () => store },
      '@/store/modules/permission': { usePermissionStoreWithOut: () => ({}) },
      '@/router/routes': { asyncRoutes: [] },
      '@/router/routes/basic': { PAGE_NOT_FOUND_ROUTE: { name: 'not-found' } },
      '@/router/constant': { PAGE_NOT_FOUND_NAME: 'not-found' },
      '@/access/routeAccess': {},
      'ant-design-vue': { notification: { warning: (value) => notifications.push(value) } },
    });
    let guard;
    load('src/router/guard/permissionGuard.ts').createPermissionGuard({
      beforeEach(callback) { guard = callback; },
    });
    const results = [];
    await guard(
      { path: '/strategy/management', fullPath: '/strategy/management?tab=capital', meta: {} },
      { path: loaded ? '/home/index' : '/' },
      (value) => results.push(value),
    );
    assert.equal(results.length, 1);
    if (loaded) {
      assert.equal(results[0], false);
    } else {
      assert.equal(results[0].path, '/login');
      assert.equal(results[0].query.redirect, '/strategy/management?tab=capital');
    }
    assert.equal(notifications.length, 1);
  });
}

for (const status of [undefined, 503, 429]) {
  test(`temporary auth read failure ${status} can recover the original cookie without login`, async () => {
    const original = axios.defaults.adapter;
    const requests = [];
    const suppliedCsrf = [];
    let unavailable = false;
    axios.defaults.adapter = async (config) => {
      requests.push([config.method, config.url]);
      suppliedCsrf.push(config.headers.get('X-CSRF-Token'));
      if (unavailable) {
        throw new axios.AxiosError('temporarily unavailable', 'ERR_NETWORK', config, null,
          status === undefined ? undefined : {
            config, status, statusText: 'Unavailable', headers: {}, data: {},
          });
      }
      return {
        config, status: 200, statusText: 'OK', headers: {},
        data: {
          user: { userId: 'owner', username: 'owner', role: 'ceo' },
          permissions: ['trading:write'], session: { sessionId: 'original' }, csrfToken: 'isolated-csrf',
        },
      };
    };
    try {
      const store = setup();
      assert.equal(await store.hydrateSession(true), true);
      assert.equal(store.getIsAuthenticated, true);
      unavailable = true;
      assert.equal(await store.hydrateSession(true), false);
      assert.equal(store.getIsAuthenticated, true);
      assert.equal(store.getSessionUnavailable, true);
      assert.equal(store.getHydrationAttempted, false);
      unavailable = false;
      assert.equal(await store.hydrateSession(true), true);
      assert.equal(store.getAuthentication.session.sessionId, 'original');
      assert.equal(store.getSessionUnavailable, false);
      assert.deepEqual(requests, [['get', '/auth/me'], ['get', '/auth/me'], ['get', '/auth/me']]);
      assert.deepEqual(suppliedCsrf, [undefined, 'isolated-csrf', 'isolated-csrf']);
    } finally {
      axios.defaults.adapter = original;
    }
  });
}

for (const [status, code] of [[401, 'invalid_session'], [403, 'account_inactive']]) {
  test(`definitive rejection ${code} still requires login`, async () => {
    const original = axios.defaults.adapter;
    let requests = 0;
    axios.defaults.adapter = async (config) => {
      requests++;
      throw new axios.AxiosError('rejected', 'ERR_BAD_REQUEST', config, null, {
        config, status, statusText: 'Rejected', headers: {}, data: { detail: { code } },
      });
    };
    try {
      const store = setup();
      assert.equal(await store.hydrateSession(true), false);
      assert.equal(store.getIsAuthenticated, false);
      assert.equal(store.getHydrationAttempted, true);
      assert.equal(await store.hydrateSession(true), false);
      assert.equal(requests, 1);
    } finally {
      axios.defaults.adapter = original;
    }
  });
}

for (const [code, expected] of [
  ['invalid_session', '登录会话已失效，请重新登录后再提交价差指令。'],
  ['csrf_invalid', '登录校验已失效，请刷新页面或重新登录后再提交。'],
]) {
  test(`strategy api presents ${code} as an actionable login message`, () => {
    let cleared = 0;
    const load = createLoader({
      'openapi-fetch': { __esModule: true, default: () => ({ use() {} }) },
      './strategyClient': { createStrategyClient: () => ({}) },
      './strategyQueries': {
        strategyQueryClient: { invalidateQueries() {} },
        strategyQueryKey: () => ['strategy'],
        strategySession: { value: { generation: 0 } },
      },
      './userSystem': { clearUserSystemSessionMemory: () => { cleared++; } },
    });
    const { strategyData } = load('src/api/platform/strategyApi.ts');
    assert.throws(
      () => strategyData({ error: { detail: { code, message: 'Browser session is invalid' } } }),
      (error) => {
        assert.equal(error.message, expected);
        assert.doesNotMatch(error.message, /Browser session|invalid_session|csrf_invalid|\{/);
        return true;
      },
    );
    assert.equal(cleared, 1);
  });
}

test('connection failure renders a session retry, then restores the original destination', async () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const ts = require('typescript');
  const vue = require('vue');
  const { parse, compileScript } = require('@vue/compiler-sfc');
  const { renderToString } = require('vue/server-renderer');
  const filename = path.resolve(__dirname, '../src/views/sys/login/LoginForm.vue');
  const { descriptor } = parse(fs.readFileSync(filename, 'utf8'), { filename });
  const compiled = compileScript(descriptor, { id: 'session-recovery', inlineTemplate: true });
  const code = ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  let retry;
  const destinations = [];
  const store = {
    getHydrationAttempted: false,
    getUserInfo: { homePath: '/home/index' },
    async hydrateSession() { return true; },
  };
  const wrapper = (tag) => ({ setup: (_, { slots }) => () => vue.h(tag, {}, slots.default?.()) });
  const Form = Object.assign(wrapper('form'), { Item: wrapper('label') });
  const Input = Object.assign(wrapper('input'), { Password: wrapper('input') });
  const mocks = {
    'vue-router': {
      useRoute: () => ({ query: { redirect: '/strategy/spread-carry' } }),
      useRouter: () => ({ replace: async (value) => destinations.push(value) }),
    },
    'ant-design-vue': {
      Form, Input,
      Button: { setup: (_, { attrs, slots }) => {
        retry = attrs.onClick;
        return () => vue.h('button', {}, slots.default?.());
      } },
    },
    '@/hooks/web/useI18n': { useI18n: () => ({ t: (value) => value }) },
    '@/hooks/web/useMessage': { useMessage: () => ({ createMessage: { destroy() {} } }) },
    '@/store/modules/user': { useUserStore: () => store },
    './useLogin': {
      LoginStateEnum: { LOGIN: 'login' }, useLoginState: () => ({ getLoginState: vue.ref('login') }),
      useFormRules: () => ({}), useFormValid: () => ({}),
    },
    '@/hooks/web/useDesign': { useDesign: () => ({ prefixCls: 'login' }) },
    '@/api/platform/userSystem': { UserSystemApiError: Error },
  };
  const module = { exports: {} };
  new Function('require', 'module', 'exports', code)(
    (name) => mocks[name] || require(name), module, module.exports,
  );
  const html = await renderToString(vue.createSSRApp(module.exports.default));
  assert.match(html, /重试连接/);
  assert.doesNotMatch(html, /请输入账号|请输入密码/);
  await retry();
  assert.deepEqual(destinations, ['/strategy/spread-carry']);
  store.getHydrationAttempted = true;
  const rejectedHtml = await renderToString(vue.createSSRApp(module.exports.default));
  assert.doesNotMatch(rejectedHtml, /重试连接/);
  assert.match(rejectedHtml, /请输入账号/);
});
