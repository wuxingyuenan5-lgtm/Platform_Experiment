const test = require('node:test');
const assert = require('node:assert/strict');
const { structureRows, structureWindow, buildMarketStructureOptions } =
  require('./load-strategy-module.cjs')()(
    'src/views/hedgeBoard/aShare/components/marketStructureChart.ts',
  );

test('structure coverage excludes leading index-only dates, treats zero as data, and preserves interior missingness', () => {
  const input = [
    { date: '2026-01-05', advance: null, decline: null, csi300Close: 4100 },
    { date: '2026-01-02', csi300Close: 4000 },
    { date: '2026-01-03', limit_up: 0, csi300Close: 4010 },
    {
      date: '2026-01-04',
      advance: 1000,
      decline: 2000,
      limit_up: 30,
      limit_down: 4,
      csi300Close: 4020,
    },
  ];
  const rows = structureRows(input);
  assert.deepEqual(
    rows.map((r) => r.date),
    ['2026-01-03', '2026-01-04', '2026-01-05'],
  );
  assert.deepEqual(structureRows([{ date: '2026-01-01', csi300Close: 4000 }]), []);
  const options = buildMarketStructureOptions(rows, 0);
  const series = (name) => options.series.find((s) => s.name === name);
  assert.deepEqual(series('下跌家数').data, [null, -2000, null]);
  assert.deepEqual(series('跌停家数（全A）').data, [null, -4, null]);
  assert.deepEqual(series('涨停家数（全A）').data, [0, 30, null]);
  assert.deepEqual(series('沪深300').data, [4010, 4020, 4100]);
  assert.equal(series('沪深300').connectNulls, false);
  assert.equal(input[0].date, '2026-01-05');
});

test('90-day and calendar-year ranges anchor to the last observation, including leap years', () => {
  const rows = [
    '2021-01-01',
    '2021-03-01',
    '2023-03-01',
    '2023-12-01',
    '2023-12-03',
    '2024-03-01',
  ].map((date) => ({ date }));
  assert.deepEqual(structureWindow(rows, 90), { startValue: 4, endValue: 5 });
  assert.deepEqual(structureWindow(rows, 365), { startValue: 2, endValue: 5 });
  assert.deepEqual(structureWindow(rows, 1095), { startValue: 1, endValue: 5 });
  assert.deepEqual(structureWindow(rows, 0), { startValue: 0, endValue: 5 });
  const options = buildMarketStructureOptions(rows, 90);
  assert.deepEqual(
    options.dataZoom.map((z) => [z.type, z.startValue, z.endValue]),
    [
      ['inside', 4, 5],
      ['slider', 4, 5],
    ],
  );
  assert.equal(options.dataZoom[0].zoomOnMouseWheel, 'ctrl');
  assert.equal(options.xAxis.axisLabel.hideOverlap, true);
});

test('preserves count axes while letting the hidden price axis follow the visible window', () => {
  const reference = [
    { date: '2020-01-02', csi300Close: 2000 },
    {
      date: '2021-01-04',
      advance: 2000,
      decline: 1000,
      limit_up: 50,
      limit_down: 4,
      csi300Close: 4000,
    },
    {
      date: '2026-11-06',
      advance: 1000,
      decline: 3000,
      limit_up: 20,
      limit_down: 10,
      csi300Close: 3500,
    },
  ];
  const rows = structureRows(reference);
  for (const range of [90, 365, 1095, 0]) {
    const option = buildMarketStructureOptions(rows, range);
    assert.deepEqual(
      option.yAxis.slice(0, 2).map((axis) => [axis.min, axis.max, axis.interval]),
      [
        [-6000, 6000, 2000],
        [-300, 300, 100],
      ],
    );
    assert.equal(option.yAxis[0].axisLabel.formatter(-4000), '-4,000');
    assert.equal(option.yAxis[1].axisLabel.formatter(-200), '-200');
    for (const axis of option.yAxis.slice(0, 2)) {
      assert.equal(axis.axisLabel.showMinLabel, false);
      assert.equal(axis.axisLabel.showMaxLabel, false);
    }
    assert.deepEqual([option.yAxis[2].min, option.yAxis[2].max], ['dataMin', 'dataMax']);
    assert.equal(option.yAxis[2].scale, true);
    assert.deepEqual(option.xAxis.data, ['2021-01-04', '2026-11-06']);
    const benchmark = option.series.find((series) => series.name === '沪深300');
    assert.equal(benchmark.itemStyle.color, '#000000');
    assert.equal(benchmark.lineStyle.width, 2.5);
    for (const series of option.series.filter((series) => series.yAxisIndex === 1))
      assert.equal(series.lineStyle.width, 3);
  }
});

test('zero and negative index prices stay missing rather than flattening the price scale', () => {
  const rows = [0, -1, null, 3500, 3540].map((csi300Close, i) => ({
    date: `2026-11-0${i + 1}`,
    advance: 100,
    csi300Close,
  }));
  const option = buildMarketStructureOptions(rows, 90);
  assert.deepEqual(option.series.find((series) => series.name === '沪深300').data, [
    null,
    null,
    null,
    3500,
    3540,
  ]);
});
