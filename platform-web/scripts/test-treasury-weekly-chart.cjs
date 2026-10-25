const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { buildTreasuryWeeklyOptions } = load('src/views/hedgeBoard/charts/treasuryWeeklyOptions.ts');
const weeks = [
  { weekDate: '2026-05-04', netFlowDisplay: '-$2M', netBtc: null, netBtcDisplay: 'null', btcPriceUsd: '80000', btcPriceDisplay: '$80,000', companies: [{name:'A',value:'-2000000',display:'-$2M'}] },
  { weekDate: '2026-05-11', netFlowDisplay: '$3M', netBtc: '35', netBtcDisplay: '35', btcPriceUsd: '82000', btcPriceDisplay: '$82,000', companies: [{name:'B',value:'3000000',display:'$3M'}] },
];
test('company stack preserves sells and missing values; quantity and price have separate axes', () => {
  const option = buildTreasuryWeeklyOptions(weeks,'2026-05-04','2026-05-11');
  assert.deepEqual(option.series.map(s=>s.yAxisIndex), [0,0,2,1]);
  assert.deepEqual(option.series[0].data,[-2000000,null]);
  assert.deepEqual(option.series[1].data,[null,3000000]);
  assert.deepEqual(option.series[2].data,[null,35]);
  assert.ok(option.series.slice(0,2).every(s=>s.stack==='companies' && s.stackStrategy==='samesign'));
  assert.equal(option.yAxis[1].scale,true);
  assert.ok(option.dataZoom.every(z=>z.filterMode==='filter'));
});
test('tooltip retains source precision and all company detail; arbitrary dates map to week indices', () => {
  const option = buildTreasuryWeeklyOptions(weeks,'2026-05-06','2026-05-15');
  assert.equal(option.dataZoom[0].startValue,1);
  assert.equal(option.dataZoom[0].endValue,1);
  const tip=option.tooltip.formatter([{axisValue:'2026-05-04'}]);
  assert.match(tip,/A：-\$2M/);
  assert.match(tip,/单周比特币总净流入：—/);
  assert.match(tip,/\$80,000/);
  assert.equal(option.tooltip.renderMode,'richText');
});
