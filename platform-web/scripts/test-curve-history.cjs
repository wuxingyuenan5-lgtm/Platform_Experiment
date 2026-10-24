const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { curveDates, curveAtDate } = load('src/views/hedgeBoard/charts/curveHistory.ts');
const { buildSourceCurveOptions } = load('src/views/hedgeBoard/charts/sourceSeriesOptions.ts');
const row = (label, observations) => ({seriesId:label,label,latestValue:999,observations:observations.map(([date,value])=>({date,value}))});
test('date selection changes settlements and actual contracts without filling missing sessions',()=>{
  const history=[row('AU2610',[['2026-10-09','892.6800']]),row('AU2612',[['2026-10-09','899.10'],['2026-10-19','910.12']]),row('AU2702',[['2026-10-19','912.50']])];
  const current=history.slice(1);
  assert.deepEqual(curveDates(history,'2026-10-19'),['2026-10-09','2026-10-19']);
  const before=JSON.stringify(history);
  const past=curveAtDate(history,current,'2026-10-09','2026-10-19');
  const latest=curveAtDate(history,current,'2026-10-19','2026-10-19');
  assert.deepEqual(past.map(s=>[s.label,s.latestValue]),[['AU2610','892.6800'],['AU2612','899.10']]);
  assert.deepEqual(latest.map(s=>s.label),['AU2612','AU2702']);
  assert.deepEqual(curveAtDate(history,current,'2026-10-10','2026-10-19'),[]);
  assert.equal(buildSourceCurveOptions(past,'blue').series[0].data[0].value[0],Date.UTC(2026,9,1));
  assert.equal(buildSourceCurveOptions(latest,'blue').series[0].data[0].value[0],Date.UTC(2026,11,1));
  assert.equal(JSON.stringify(history),before);
});
test('latest manifest excludes retired contracts even if an old point has the same date; null stays null',()=>{
  const old=row('AU2610',[['2026-10-19',123]]);
  const active=row('AU2612',[['2026-10-19',null]]);
  const selected=curveAtDate([old,active],[active],'2026-10-19','2026-10-19');
  assert.equal(selected.length,1);
  assert.equal(selected[0].latestValue,null);
});
