const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { visiblePeriods, broadChartOption, withMarketCapRatios } = load(
  'src/views/hedgeBoard/aShare/components/broadEtfAnalysis.ts',
);
const data = [
  {
    date: '2026-01-01',
    total: '10',
    deltaUnitsYi: '1',
    unitsYi: '10',
    previousUnitsYi: '9',
    indexClose: '4000',
  },
  {
    date: '2026-04-01',
    total: '-20',
    deltaUnitsYi: '-2',
    unitsYi: '8',
    previousUnitsYi: '10',
    indexClose: '4100',
  },
  {
    date: '2026-04-02',
    total: '30',
    deltaUnitsYi: '3',
    unitsYi: '11',
    previousUnitsYi: '8',
    indexClose: '4200',
  },
];
test('cumulative shares rebase to the first complete observation without filling gaps', () => {
  assert.deepEqual(
    visiblePeriods(data, 0).map((r) => r.cumulativeUnitsYi),
    [0, -2, 1],
  );
  const range = visiblePeriods(data, 30);
  assert.deepEqual(
    range.map((r) => r.cumulativeUnitsYi),
    [0, 3],
  );
  const missing = structuredClone(data);
  missing[1].unitsYi = null;
  assert.deepEqual(
    visiblePeriods(missing, 0).map((r) => r.cumulativeUnitsYi),
    [0, null, 1],
  );
  missing[0].unitsYi = null;
  missing[2].unitsYi = null;
  assert.deepEqual(
    visiblePeriods(missing, 0).map((r) => r.cumulativeUnitsYi),
    [null, null, null],
  );
  assert.equal(data[0].cumulativeUnitsYi, undefined);
});
test('cash aggregate, cumulative shares and unnormalized index points have distinct axes', () => {
  const rows = visiblePeriods(data, 0);
  const option = broadChartOption(rows, '沪深300');
  assert.deepEqual(
    option.series.map((s) => s.yAxisIndex),
    [0, 1, 2],
  );
  assert.deepEqual(option.series[0].data, [10, -20, 30]);
  assert.deepEqual(option.series[1].data, [0, -2, 1]);
  assert.deepEqual(option.series[2].data, [4000, 4100, 4200]);
  assert.match(option.yAxis[0].name, /亿元/);
  assert.match(option.yAxis[1].name, /亿份/);
  assert.match(option.yAxis[2].name, /点/);
  assert.match(option.tooltip.formatter([{ dataIndex: 1 }]), /-2 亿份/);
  assert.equal(option.series[1].connectNulls, false);
});
test('industry collections do not borrow an unrelated index price or axis', () => {
  const option = broadChartOption(visiblePeriods(data, 0), '消费/医药', false);
  assert.equal(option.yAxis.length, 2);
  assert.equal(option.series.length, 2);
  assert.doesNotMatch(option.tooltip.formatter([{ dataIndex: 1 }]), /指数收盘/);
});

test('market cap ratio shares the main dates and tooltip without filling absent observations', () => {
  const rows = withMarketCapRatios(visiblePeriods(data, 0), [
    {date:'2026-01-01',ratioPct:'3.5'},
    {date:'2026-03-31',ratioPct:'99'},
    {date:'2026-04-02',ratioPct:'0'},
  ]);
  assert.deepEqual(rows.map(r => r.marketCapRatioPct), [3.5, null, 0]);
  const option = broadChartOption(rows, '沪深300', true, true);
  assert.equal(option.yAxis.length, 4);
  assert.deepEqual(option.series.find(s => s.name === '头部ETF市值占比').data, [3.5,null,0]);
  assert.deepEqual(option.xAxis.data, data.map(r => r.date));
  assert.match(option.tooltip.formatter([{dataIndex:1}]), /头部ETF市值占比：— %/);
  assert.match(option.tooltip.formatter([{dataIndex:2}]), /头部ETF市值占比：0 %/);
  assert.equal(data[0].marketCapRatioPct, undefined);
  assert.equal(broadChartOption(rows, '行业集合', false, true).series.length, 2);
});
