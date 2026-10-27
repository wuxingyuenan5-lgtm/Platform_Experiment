const test=require('node:test'), assert=require('node:assert/strict');
const loader=require('./load-strategy-module.cjs')();
const {seasonalRows}=loader('src/views/hedgeBoard/charts/seasonality.ts');
test('calendar returns compound, missing months stay null, and partial year uses observed close',()=>{
 const rows=seasonalRows([{date:'2023-12-29',value:100},{date:'2024-01-31',value:110},{date:'2024-02-29',value:99},{date:'2024-03-29',value:0},{date:'2024-04-30',value:120},{date:'2024-05-30',value:126}]);
 const r=rows.find(r=>r.year===2024);
 assert.ok(Math.abs(r.months[0]-10)<1e-10);assert.ok(Math.abs(r.months[1]+10)<1e-10);
 assert.equal(r.months[2],null);assert.equal(r.months[3],null);assert.ok(Math.abs(r.months[4]-5)<1e-10);
 assert.ok(Math.abs(r.annual-26)<1e-10);assert.equal(r.curve.length,4);assert.equal(r.partial, new Date().getUTCFullYear()===2024);
 const full=seasonalRows([{date:'2023-12-29',value:100},{date:'2024-01-31',value:110},{date:'2024-02-29',value:99}]).at(-1);
 assert.ok(Math.abs(full.annual+1)<1e-10);assert.equal(full.latest,'2024-02-29');
});
