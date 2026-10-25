const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const {goldFactorOptions}=load('src/views/hedgeBoard/charts/goldFactorOptions.ts');
const row=(date,gold,mid=50)=>({date,available:true,gold,mid,tips:2,yieldFactor:0.5,premium:gold/mid});
test('common dates remove artificial breaks without inventing observations; changes use percentages',()=>{
  const rows=[row('2026-01-16',100),{date:'2026-01-19',available:false,gold:110},row('2026-01-20',120,60)];
  const option=goldFactorOptions(rows,true);
  assert.equal(option.grid.length,4);
  assert.equal(option.series[0].data.length,3);
  for(const s of option.series.slice(1)) {
    assert.equal(s.data.length,2);
    assert.equal(s.data.some(p=>p[0].startsWith('2026-01-19')),false);
    assert.equal(s.data.some(p=>p[1]===null),false);
  }
  assert.ok(Math.abs(option.series.at(-1).data[1][1]-20)<1e-10);
  assert.ok(option.series[1].areaStyle);
});
test('long gaps remain visible and factor levels retain six aligned panels',()=>{
  const rows=[row('2026-01-02',100),row('2026-01-15',120)];
  const option=goldFactorOptions(rows,false);
  assert.equal(option.grid.length,6);
  assert.ok(option.series.every(s=>s.data.some(p=>p[1]===null)));
  assert.equal(rows.length,2);
});
