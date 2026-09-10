const assert = require('node:assert/strict');
const test = require('node:test');
const createLoader = require('./load-strategy-module.cjs');

test('overlapping reads share one request; account and session boundaries do not', async () => {
  const load = createLoader();
  const { setStrategyQuerySession, fetchStrategyQuery, strategyQueryClient } = load(
    'src/api/platform/strategyQueries.ts',
  );
  setStrategyQuerySession('ceo', 'session-one');
  let release;
  let calls = 0;
  const loader = () => {
    calls++;
    return new Promise((resolve) => {
      release = resolve;
    });
  };
  const first = fetchStrategyQuery(['balance', 'account-a'], loader);
  const duplicate = fetchStrategyQuery(['balance', 'account-a'], loader);
  await Promise.resolve();
  assert.equal(calls, 1);
  release('0.123456789012345678');
  assert.deepEqual(await Promise.all([first, duplicate]), [
    '0.123456789012345678',
    '0.123456789012345678',
  ]);
  assert.equal(await fetchStrategyQuery(['balance', 'account-b'], async () => 'other'), 'other');
  setStrategyQuerySession('member', 'session-two');
  assert.equal(strategyQueryClient.getQueryCache().getAll().length, 0);
  assert.equal(
    await fetchStrategyQuery(['balance', 'account-a'], async () => 'new-user'),
    'new-user',
  );
  strategyQueryClient.clear();
});

test('logout cancels an in-flight read and cannot publish its late result', async () => {
  const load = createLoader();
  const { setStrategyQuerySession, fetchStrategyQuery, strategyQueryClient } = load(
    'src/api/platform/strategyQueries.ts',
  );
  setStrategyQuerySession('ceo', 'session');
  let release, signal;
  const pending = fetchStrategyQuery(['orders', 'account-a'], (value) => {
    signal = value;
    return new Promise((resolve) => {
      release = resolve;
    });
  });
  const rejected = assert.rejects(pending);
  setStrategyQuerySession();
  assert.equal(signal.aborted, true);
  release([{ secret: 'old-session-order' }]);
  await rejected;
  assert.equal(strategyQueryClient.getQueryCache().getAll().length, 0);
});

test('read errors are surfaced once without retry or reconnect replay', async () => {
  const load = createLoader();
  const { fetchStrategyQuery, strategyQueryClient } = load('src/api/platform/strategyQueries.ts');
  let calls = 0;
  await assert.rejects(
    fetchStrategyQuery(['failed-read'], async () => {
      calls++;
      throw new Error('timeout');
    }),
    /timeout/,
  );
  assert.equal(calls, 1);
  assert.equal(strategyQueryClient.getDefaultOptions().queries.refetchOnReconnect, false);
  strategyQueryClient.clear();
});

test('generated request preserves Decimal, CSRF, encoded identity and exactly one write', async () => {
  const requests = [];
  const load = createLoader({
    './userSystem': { getUserSystemCsrfToken: () => 'csrf-test-token' },
  });
  const axios = require('axios');
  const original = axios.defaults.adapter;
  axios.defaults.adapter = async (config) => {
    requests.push(config);
    if (config.method === 'post') throw new axios.AxiosError('timeout', 'ETIMEDOUT', config);
    return { data: '{}', status: 200, statusText: 'OK', headers: {}, config };
  };
  try {
    const { createStrategyApi } = load('src/api/platform/strategyApi.ts');
    const api = createStrategyApi();
    await api.GET('/api/v1/trading/funding/instructions/{instruction_id}', {
      params: { path: { instruction_id: 'funding/a b' } },
    });
    assert.match(requests[0].url, /funding%2Fa%20b$/);
    await assert.rejects(
      api.POST('/api/v1/trading/funding/instructions', {
        body: {
          action: 'open',
          idempotencyKey: 'same-intent',
          perpetualSymbol: 'BTCUSDT',
          spotSymbol: 'BTCUSDT',
          quantity: '0.123456789012345678',
        },
      }),
      /timeout/,
    );
    const writes = requests.filter((item) => item.method === 'post');
    assert.equal(writes.length, 1);
    assert.equal(JSON.parse(writes[0].data).quantity, '0.123456789012345678');
    assert.equal(writes[0].headers.get('X-CSRF-Token'), 'csrf-test-token');
    assert.equal(writes[0].withCredentials, true);
  } finally {
    axios.defaults.adapter = original;
  }
});

test('session change while serializing a write prevents dispatch under the next login', async () => {
  let options;
  let calls = 0;
  const load = createLoader({
    'openapi-fetch': (config) => {
      options = config;
      return { use() {} };
    },
    './strategyClient': {
      createStrategyClient: () => ({
        request: async () => {
          calls++;
        },
      }),
    },
  });
  const { setStrategyQuerySession } = load('src/api/platform/strategyQueries.ts');
  setStrategyQuerySession('first-user', 'first-session');
  load('src/api/platform/strategyApi.ts').createStrategyApi();
  let release;
  const request = new Request('http://localhost/api/v1/trading/funding/instructions', {
    method: 'POST',
    body: '{}',
  });
  request.text = () =>
    new Promise((resolve) => {
      release = resolve;
    });
  const pending = options.fetch(request);
  setStrategyQuerySession('next-user', 'next-session');
  release('{}');
  await assert.rejects(pending, /登录状态已变更/);
  assert.equal(calls, 0);
});

test('generated text transport preserves structured rejection detail and HTTP identity', async () => {
  const axios = require('axios');
  const original = axios.defaults.adapter;
  let calls = 0;
  axios.defaults.adapter = async (config) => {
    calls++;
    throw new axios.AxiosError(
      'Request failed with status code 423',
      'ERR_BAD_REQUEST',
      config,
      null,
      {
        data: JSON.stringify({ detail: 'Trading gate is closed' }),
        status: 423,
        statusText: 'Locked',
        headers: {},
        config,
      },
    );
  };
  try {
    const load = createLoader({ './userSystem': { getUserSystemCsrfToken: () => 'csrf' } });
    const { createStrategyApi } = load('src/api/platform/strategyApi.ts');
    await assert.rejects(
      createStrategyApi().POST('/api/v1/trading/cross-spread/preflight', {
        body: { action: 'OPEN_LONG', quantityOz: '1' },
      }),
      (error) => {
        assert.equal(error.response.status, 423);
        assert.equal(error.response.data.detail, 'Trading gate is closed');
        assert.equal(error.code, 'ERR_BAD_REQUEST');
        return true;
      },
    );
    assert.equal(calls, 1);
  } finally {
    axios.defaults.adapter = original;
  }
});
