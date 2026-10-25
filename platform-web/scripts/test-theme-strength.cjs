const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { themeStrengthRows, strengthRanking, strengthMatrix } = load(
  'src/views/hedgeBoard/components/themeStrength.ts',
);
const theme = (name, daily, r5, r20, extra = {}) => ({
  name,
  expected: 5,
  covered: 5,
  medianReturn: daily,
  return5: r5,
  return20: r20,
  returnPctRankable: true,
  return5Rankable: true,
  return20Rankable: true,
  ...extra,
});
test('theme returns use percentage-point source units and independent period coverage; style references are excluded', () => {
  const rows = themeStrengthRows([
    theme('A', '2', '-5', '20'),
    theme('B', 0, 99, null, { return5Rankable: false }),
    theme('C', 99, 'bad', 100, { returnPctRankable: false }),
    theme('ETF风格', 100, 200, 300, { kind: 'style' }),
  ]);
  assert.equal(rows.length, 3);
  assert.deepEqual(
    rows.map((r) => [r.change, r.change_5d, r.change_20d]),
    [
      [0.02, -0.05, 0.2],
      [0, null, null],
      [null, null, 1],
    ],
  );
  assert.deepEqual(
    strengthRanking(rows, 'change').up.map((r) => r.name),
    ['A', 'B'],
  );
  assert.deepEqual(
    strengthRanking(rows, 'change_5d').down.map((r) => r.name),
    ['A'],
  );
  assert.deepEqual(
    strengthRanking(rows, 'change_20d').up.map((r) => r.name),
    ['C', 'A'],
  );
});
test('matrix excludes incomplete periods, counts all four quadrants and stays inside the stock-pool chart bounds', () => {
  const rows = themeStrengthRows([
    theme('领涨', 2, 0, 10),
    theme('改善', 2, 0, -10),
    theme('转弱', -2, 0, 10),
    theme('领跌', -2, 0, -10),
    theme('缺失', null, 0, 10),
  ]);
  const result = strengthMatrix(rows);
  assert.deepEqual(result.quadrants, { leader: 1, improving: 1, weakening: 1, lagging: 1 });
  assert.equal(result.points.length, 4);
  assert.ok(result.points.every((p) => p.x >= 52 && p.x <= 948 && p.y >= 52 && p.y <= 368));
});
test('empty and zero-only data produce finite matrix axes without inventing rankings', () => {
  assert.deepEqual(strengthRanking([], 'change'), { up: [], down: [] });
  assert.deepEqual(strengthMatrix([]).points, []);
  const result = strengthMatrix(themeStrengthRows([theme('持平', 0, 0, 0)]));
  assert.equal(result.points[0].x, 500);
  assert.equal(result.points[0].y, 210);
});

test('clustered matrix points retain separate bounded name labels', () => {
  const points = strengthMatrix(
    themeStrengthRows(Array.from({ length: 9 }, (_, i) => theme(`主题名称${i}`, 1, 1, 1))),
  ).points;
  assert.equal(points.length, 9);
  assert.equal(new Set(points.map((p) => `${p.labelX}:${p.labelY}`)).size, 9);
  assert.ok(
    points.every((p) => p.labelX >= 58 && p.labelX <= 942 && p.labelY >= 90 && p.labelY <= 340),
  );
});
