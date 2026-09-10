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

for (const status of [undefined, 503, 429]) {
  test(`temporary auth read failure ${status} can recover the original cookie without login`, async () => {
    const original = axios.defaults.adapter;
    const requests = [];
    let unavailable = true;
    axios.defaults.adapter = async (config) => {
      requests.push([config.method, config.url]);
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
      assert.equal(await store.hydrateSession(true), false);
      assert.equal(store.getIsAuthenticated, false);
      assert.equal(store.getHydrationAttempted, false);
      unavailable = false;
      assert.equal(await store.hydrateSession(true), true);
      assert.equal(store.getAuthentication.session.sessionId, 'original');
      assert.deepEqual(requests, [['get', '/auth/me'], ['get', '/auth/me']]);
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
