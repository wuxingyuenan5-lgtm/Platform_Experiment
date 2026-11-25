const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { flowPeriods, flowChartOption, rangeStart, offsetFlowPeriods, flowDailyAverage } = load(
  'src/views/hedgeBoard/aShare/components/etfFlowAnalysis.ts',
);
test('daily averages retain raw precision before display rounding and preserve missing values', () => {
  assert.equal(flowDailyAverage('5060.2936499', 20).toFixed(2), '253.01');
  assert.equal(flowDailyAverage('2018.2084695', 5).toFixed(2), '403.64');
  assert.equal(flowDailyAverage('-2.3', 5).toFixed(2), '-0.46');
  assert.equal(flowDailyAverage(0, 20), 0);
  for (const value of [null, undefined, '', 'bad']) assert.equal(flowDailyAverage(value, 5), null);
  for (const count of [0, -1, 1.5]) assert.equal(flowDailyAverage(10, count), null);
});
const data = {
  dates: ['2025-12-31', '2026-01-02', '2026-01-05', '2026-01-06', '2026-02-02'],
  cats: ['沪深300', '科创50'],
  colors: ['red', 'blue'],
  series: { 沪深300: [1, 2, 3, 4, 5], 科创50: [-2, -1, 0, 1, 2] },
};
const prices = {
  hs300: { name: '沪深300', rows: data.dates.map((date, i) => ({ date, close: 4000 + i })) },
};

test('daily, Monday-based weekly and calendar monthly sums preserve complete cash totals and last close', () => {
  const daily = flowPeriods(data, prices, 'daily', 0);
  const weekly = flowPeriods(data, prices, 'weekly', 0);
  const monthly = flowPeriods(data, prices, 'monthly', 0);
  for (const rows of [daily, weekly, monthly]) {
    assert.equal(
      rows.reduce((sum, row) => sum + row.total, 0),
      15,
    );
    assert.equal(rows.at(-1).cumulative, 15);
  }
  assert.deepEqual(
    weekly.map((r) => r.date),
    ['2026-01-02', '2026-01-06', '2026-02-02'],
  );
  assert.equal(weekly[0].values['沪深300'], 3);
  assert.equal(weekly[0].prices.hs300, 4001);
  assert.equal(monthly[1].date, '2026-01-06');
  assert.equal(monthly[1].prices.hs300, 4003);
  assert.equal(monthly[1].values['沪深300'], 9);
});
test('missing members keep available period totals with coverage and never fill the source cell with zero', () => {
  const broken = structuredClone(data);
  broken.series['沪深300'][2] = null;
  const weekly = flowPeriods(broken, prices, 'weekly', 0);
  assert.equal(weekly[1].values['沪深300'], 4);
  assert.equal(weekly[1].total, 5);
  assert.equal(weekly[2].cumulative, 12);
  assert.equal(flowPeriods(broken, prices, 'daily', 0)[2].values['沪深300'], null);
  assert.match(weekly[1].qualityNote, /覆盖不完整/);
  const empty = structuredClone(data);
  empty.series['沪深300'][2] = empty.series['科创50'][2] = null;
  assert.equal(flowPeriods(empty, prices, 'daily', 0)[2].total, null);
  const coverage = structuredClone(data);
  coverage.coverage = { '2026-01-05': { '沪深300': { expected: 10, covered: 9, missingCodes: ['510300'] } } };
  const partial = flowPeriods(coverage, prices, 'daily', 0)[2];
  assert.equal(partial.total, 3);
  assert.match(flowChartOption([partial], coverage, [], 'daily').tooltip.formatter([{ dataIndex: 0, seriesIndex: 0, seriesName: '沪深300', value: 3 }]), /覆盖不完整/);
  const absentPrice = {
    hs300: { name: '沪深300', rows: prices.hs300.rows.filter((r) => r.date !== '2026-01-06') },
  };
  assert.equal(flowPeriods(data, absentPrice, 'weekly', 0)[1].prices.hs300, null);
});
test('range buttons select actual source dates and recompute the cumulative baseline', () => {
  assert.equal(rangeStart('2026-11-03', 1095), '2023-11-03');
  const rows = flowPeriods(data, prices, 'daily', 30);
  assert.equal(rows[0].date, '2026-01-05');
  assert.equal(rows[0].cumulative, 3);
  assert.equal(rows.at(-1).cumulative, 15);
});
test('cash, cumulative cash and raw index prices have separate units and legend identities', () => {
  const rows = flowPeriods(data, prices, 'daily', 0);
  const option = flowChartOption(rows, data, ['hs300'], 'daily');
  assert.equal(option.series.filter((s) => s.yAxisIndex === 2).length, 1);
  assert.equal(option.series.at(-1).name, '沪深300价格');
  assert.equal(option.series.at(-1).data[0], 4000);
  assert.equal(option.series[0].stack, 'flows');
  assert.equal(option.series.at(-2).yAxisIndex, 1);
  assert.equal(option.yAxis[2].name, '指数（点）');
});

test('tooltip leads with the full daily cash total, excluding cumulative and index values', () => {
  const rows = flowPeriods(data, prices, 'daily', 0);
  const option = flowChartOption(rows, data, ['hs300'], 'daily');
  const text = option.tooltip.formatter([
    { dataIndex: 1, seriesIndex: 0, seriesName: '沪深300', value: 2, marker: '<i></i>' },
    { dataIndex: 1, seriesIndex: 2, seriesName: '累计净流入', value: 0 },
    { dataIndex: 1, seriesIndex: 3, seriesName: '沪深300价格', value: 4001 },
  ]);
  assert.match(
    text,
    /2026-01-02<br\/><strong>当日合计净流入：1 亿元<\/strong><br\/><i><\/i>沪深300：2 亿元/,
  );
  assert.ok(text.indexOf('当日合计净流入') < text.indexOf('累计净流入'));
  assert.match(text, /沪深300价格：4,001 点/);
});

test('tooltip totals preserve negative, zero and missing values and adapt to period and offset', () => {
  const rows = flowPeriods(data, prices, 'daily', 0);
  for (const total of [-3, 0, null]) {
    const sample = [{ ...rows[0], total }];
    const text = flowChartOption(sample, data, [], 'daily').tooltip.formatter([
      { dataIndex: 0, seriesIndex: 0, seriesName: '沪深300', value: 1 },
    ]);
    assert.ok(text.includes(`当日合计净流入：${total == null ? '—' : total} 亿元`));
  }
  for (const [level, label] of [
    ['weekly', '当周'],
    ['monthly', '当月'],
  ]) {
    const periods = flowPeriods(data, prices, level, 0);
    const text = flowChartOption(periods, data, ['hs300'], level, 1).tooltip.formatter([
      { dataIndex: 0, seriesIndex: 0, seriesName: '沪深300', value: 3 },
    ]);
    assert.ok(text.split('\n')[1].startsWith(label + '合计净流入：'));
  }
});

test('time offsets move only prices, extend the shared date axis in both directions and preserve source dates', () => {
  const rows = flowPeriods(data, prices, 'daily', 0);
  const before = structuredClone(rows);
  for (const offset of [2, -2]) {
    const shifted = offsetFlowPeriods(rows, offset, 'daily');
    const cashStart = Math.max(0, -offset);
    const priceStart = Math.max(0, offset);
    assert.equal(shifted.length, rows.length + Math.abs(offset));
    rows.forEach((row, i) => {
      assert.equal(shifted[i + cashStart].date, row.date);
      assert.equal(shifted[i + cashStart].total, row.total);
      assert.equal(shifted[i + cashStart].cumulative, row.cumulative);
      assert.deepEqual(shifted[i + priceStart].prices, row.prices);
      assert.equal(shifted[i + priceStart].priceDate, row.date);
    });
    const padding = offset > 0 ? shifted.at(-1) : shifted[0];
    assert.equal(padding.total, null);
    assert.equal(padding.cumulative, null);
    assert.ok(Object.values(padding.values).every((v) => v === null));
    assert.match(padding.date, offset > 0 ? /2026-02-02 后2交易日/ : /2025-12-31 前2交易日/);
    const option = flowChartOption(rows, data, ['hs300'], 'daily', offset);
    assert.deepEqual(
      option.xAxis.data,
      shifted.map((r) => r.date),
    );
    assert.equal(option.series.at(-1).data[priceStart], 4000);
    assert.match(option.series.at(-1).name, offset > 0 ? /后移2交易日/ : /前移2交易日/);
    const text = option.tooltip.formatter([
      {
        dataIndex: priceStart,
        seriesIndex: data.cats.length + 1,
        seriesName: option.series.at(-1).name,
        value: 4000,
      },
    ]);
    assert.match(text, /4,000 点（原日期 2025-12-31）/);
  }
  assert.deepEqual(rows, before);
  assert.strictEqual(offsetFlowPeriods(rows, 0, 'daily'), rows);
  assert.equal(flowChartOption(rows, data, [], 'daily', 2).xAxis.data.length, rows.length);
});

test('weekly and monthly offsets move aggregated closes by periods and keep missing prices as gaps', () => {
  const broken = structuredClone(prices);
  broken.hs300.rows[3].close = null;
  for (const [level, unit] of [
    ['weekly', '周'],
    ['monthly', '月'],
  ]) {
    const rows = flowPeriods(data, broken, level, 0);
    for (const offset of [1, -1]) {
      const shifted = offsetFlowPeriods(rows, offset, level);
      const priceStart = Math.max(0, offset);
      assert.equal(shifted[priceStart + 1].prices.hs300, null);
      assert.equal(shifted[priceStart + 1].priceDate, '2026-01-06');
      assert.match(offset > 0 ? shifted.at(-1).date : shifted[0].date, new RegExp(`1${unit}$`));
      const option = flowChartOption(rows, data, ['hs300', 'star50'], level, offset);
      assert.equal(option.series.at(-2).data[priceStart + 1], null);
      assert.ok(option.series.at(-1).data.every((v) => v === null));
      assert.equal(option.series.at(-2).connectNulls, false);
      assert.equal(option.yAxis[2].scale, true);
    }
  }
  assert.deepEqual(offsetFlowPeriods([], 3, 'daily'), []);
});
