const test = require('node:test');
const assert = require('node:assert/strict');
const { chinaTreasuryInfoCards } = require('./load-strategy-module.cjs')()(
  'src/views/hedgeBoard/aShare/components/chinaTreasuryInfo.ts',
);
const row = (overrides = {}) => ({
  seriesId: 'cn_treasury_10y',
  unit: 'percent',
  latestValue: '1.5',
  observationDate: '2026-11-06',
  source: 'chinabond',
  status: 'ready',
  isStale: false,
  observations: [
    { date: '2026-11-06', value: '1.5' },
    { date: '2026-11-05', value: '1.42' },
    { date: '2026-11-07', value: '9' },
  ],
  ...overrides,
});
test('yield changes use percentage-point differences times 100 and same-tenor previous observations', () => {
  const cards = chinaTreasuryInfoCards([
    row(),
    row({
      seriesId: 'cn_treasury_30y',
      latestValue: '2.03',
      observations: [{ date: '2026-11-05', value: '2.04' }],
    }),
  ]);
  assert.deepEqual(
    cards.map((c) => [c.label, c.yieldLabel, c.changeLabel]),
    [
      ['中国10Y国债', '1.50%', '+8BP'],
      ['中国30Y国债', '2.03%', '-1BP'],
    ],
  );
  assert.match(cards[0].note, /2026-11-06.*中债/);
  assert.match(cards[0].title, /2026-11-05/);
});
test('missing yields or previous values remain missing, stale data retains its dated source', () => {
  assert.equal(chinaTreasuryInfoCards([])[0].yieldLabel, '—');
  assert.equal(chinaTreasuryInfoCards([row({ latestValue: null })])[0].changeLabel, '');
  assert.equal(chinaTreasuryInfoCards([row({ observations: [] })])[0].changeLabel, '—BP');
  assert.equal(chinaTreasuryInfoCards([row({ unit: 'ratio' })])[0].yieldLabel, '—');
  assert.match(chinaTreasuryInfoCards([row()], true)[0].note, /待更新/);
  assert.match(chinaTreasuryInfoCards([row({ isStale: true })])[0].note, /待更新/);
  assert.equal(chinaTreasuryInfoCards([row({ latestValue: '1.42' })])[0].changeLabel, '0BP');
});
