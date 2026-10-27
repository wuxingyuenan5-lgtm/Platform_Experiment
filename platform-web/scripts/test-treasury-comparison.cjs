const test = require('node:test');
const assert = require('node:assert/strict');
const loader = require('./load-strategy-module.cjs')();
const {buildTreasuryComparisonOptions, TREASURY_LINES} = loader('src/views/hedgeBoard/charts/treasuryComparisonOptions.ts');

test('two synchronized panes use the five yields and three requested spreads', () => {
  const series = TREASURY_LINES.map(([seriesId]) => ({seriesId, observations:[{date:'2026-10-23',value:seriesId==='dff'?3.88:0},{date:'2026-10-26',value:seriesId==='us_treasury_3m'?null:0.35}]}));
  series[0].observations.push({date:'2026-10-24',value:3.88});
  const options = buildTreasuryComparisonOptions(series);
  assert.equal(options.series.length,8);
  assert.deepEqual(options.xAxis[0].data,['2026-10-23','2026-10-26']);
  assert.deepEqual(options.xAxis[1].data,options.xAxis[0].data);
  assert.deepEqual(options.series.map(s=>s.yAxisIndex),[0,0,0,0,0,1,1,1]);
  assert.equal(options.series[1].data[1],null);
  assert.equal(options.series[0].step,'end');
  assert.ok(options.yAxis.every(a=>a.scale && a.position==='right'));
  assert.deepEqual(options.dataZoom[1].xAxisIndex,[0,1]);
  assert.equal(options.series[5].markLine.data[0].yAxis,0);
});
