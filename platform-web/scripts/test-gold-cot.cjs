const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { cotChanges, cotHistoryOptions } = load('src/views/hedgeBoard/charts/goldCotOptions.ts');
const row = (date, oi, long, short, spreading) => ({date,openInterest:oi,categories:{managed:{label:'管理机构',long,short,spreading}}});
test('changes preserve signed long/short changes and separate spreads from directional OI', () => {
  const changes=cotChanges(row('2026-10-13',100,30,10,5),row('2026-10-20',90,25,12,8));
  assert.deepEqual(changes.map(r=>[r.long,r.short]),[[-10,-10],[-13,-13],[3,3],[-5,2],[3,3]]);
});
test('managed positions include spreading on both sides; missing spread is not zero', () => {
  const rows=[row('2026-10-13',100,30,10,5),row('2026-10-20',200,60,20,null)];
  const options=cotHistoryOptions(rows,[{date:'2026-10-14',value:'4000'}],'2026-10-13','2026-10-20');
  assert.deepEqual(options.series[1].data.map(p=>p[1]),[35,null]);
  assert.deepEqual(options.series[2].data.map(p=>p[1]),[15,null]);
  assert.equal(options.series[0].data.length,1);
  assert.equal(options.series[0].data[0][0],'2026-10-14T00:00:00Z');
  assert.equal(options.series[1].yAxisIndex,1);
  assert.equal(options.series[0].yAxisIndex,0);
});
