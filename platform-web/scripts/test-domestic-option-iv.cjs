const test = require('node:test');
const assert = require('node:assert/strict');
const vue = require('vue');
const createLoader = require('./load-strategy-module.cjs');

function setup(request) {
  const provided = new Map();
  const module = createLoader({
    vue: {
      ...vue,
      provide: (key, state) => provided.set(key, state),
      inject: (key) => provided.get(key),
      onBeforeUnmount() {},
    },
    '@/api/hedgeResearch': { researchRequest: request },
  })('src/views/hedgeBoard/aShare/components/useDomesticFinancing.ts');
  const provider = module.provideDomesticFinancing();
  return { provider, card: module.useDomesticOptionIv(), chart: module.useDomesticOptionIv() };
}

test('overview and derivatives share the selected underlying, exact changes and one request', async () => {
  let requests = 0;
  const { provider, card, chart } = setup(async () => {
    requests++;
    return {
      iv: {
        rows: [
          {
            date: '2026-11-20',
            underlying: 'IO',
            month: '2612',
            main: true,
            value: '20.352478',
            contracts: ['call', 'put'],
          },
          {
            date: '2026-11-19',
            underlying: 'IO',
            month: '2611',
            main: true,
            value: '22.810003',
            contracts: ['call', 'put'],
          },
          {
            date: '2026-11-20',
            underlying: 'IO',
            month: '2701',
            main: false,
            value: '99',
            contracts: [],
          },
          { date: '2026-11-20', underlying: '510050', month: '2612', value: '25.1', contracts: [] },
        ],
      },
      ivIndices: [
        { name: '沪深300', underlyings: ['IO'], rows: [{ date: '2026-11-19', close: '4000' }] },
        { name: '上证50', underlyings: ['510050'], rows: [] },
      ],
    };
  });
  await Promise.all([card.load(), chart.load()]);
  assert.equal(requests, 1);
  assert.equal(card.underlying.value, 'IO');
  assert.equal(card.summary.value.value, '20.35%');
  assert.equal(card.summary.value.change, '-2.46个百分点');
  assert.equal(card.summary.value.previousDate, '2026-11-19');
  assert.equal(chart.ivRows.value.at(-1).indexClose, null);
  chart.underlying.value = '510050';
  assert.equal(card.underlying.value, '510050');
  assert.equal(card.summary.value.name, '上证50');
  assert.equal(card.summary.value.change, '—');
  await card.load();
  assert.equal(requests, 1);
  provider.reset();
  assert.equal(chart.underlying.value, 'IO');
  assert.equal(card.summary.value.value, '—');
});

test('reset rejects completion from the previous account request', async () => {
  let finish;
  const { provider, card } = setup(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const pending = card.load();
  provider.reset();
  finish({ iv: { rows: [] }, ivIndices: [] });
  await pending;
  assert.equal(provider.data.value, undefined);
  assert.equal(provider.loading.value, false);
});
