const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { mapSnapshot, narrativeMap, narrativeLines } = load(
  'src/views/hedgeBoard/macro/narrativeOptions.ts',
);
const drivers = [
  {
    id: 'a',
    label: '强美元',
    group: 'FX',
    history: [
      { date: '2026-09-01', score: 1, momentum: 0.1 },
      { date: '2026-10-01', score: 2, momentum: 0.3 },
      { date: '2026-10-20', score: 99, momentum: 9 },
    ],
  },
];
test('focused tooltip shows only selected theme and escapes markup', () => {
  const options = narrativeLines(drivers, '2026-10-03', 5, 'a');
  const html = options.tooltip.formatter([
    { seriesName: '强美元', value: ['2026-10-01', 2] },
    { seriesName: 'another', value: ['2026-10-01', 3] },
  ]);
  assert.ok(html.includes('2026-10-01') && html.includes('强美元') && !html.includes('another'));
  const all = narrativeLines(drivers, '2026-10-03', 5, '').tooltip.formatter([
    { seriesName: '<img>', value: ['2026-10-01', 2] },
  ]);
  assert.ok(all.includes('&lt;img&gt;') && !all.includes('<img>'));
});
test('historical map never uses future observations or values older than14 days', () => {
  assert.equal(mapSnapshot(drivers, '2026-10-03')[0].point.score, 2);
  assert.equal(mapSnapshot(drivers, '2026-10-18').length, 0);
  assert.equal(mapSnapshot(drivers, '2026-08-01').length, 0);
});
test('map scales axes around visible points and preserves labels', () => {
  const map = narrativeMap(drivers, '2026-10-20');
  assert.ok(map.domain.x > 99 && map.domain.y > 9);
  assert.equal(map.points[0].driver.label, '强美元');
  assert.ok(map.points[0].labelX >= 70 && map.points[0].labelX < 1035);
});
test('trajectory shares as-of cutoff and inserts breaks across missing ranges', () => {
  const result = narrativeLines(drivers, '2026-10-03', 5, 'a');
  assert.equal(result.series[0].lineStyle.width, 2.5);
  assert.equal(result.series[0].data.length, 3);
  assert.equal(result.series[0].data[1][1], null);
  assert.equal(result.series[0].data.at(-1)[1], 2);
});
