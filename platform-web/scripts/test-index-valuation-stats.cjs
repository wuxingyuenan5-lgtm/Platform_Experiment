const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const output = ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/views/hedgeBoard/components/indexValuationStats.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const scope={exports:{},Date,Map,Number,Math};vm.runInNewContext(output,scope);
const {valuationStats,valuationWindow}=scope.exports;
const daily=(count,value)=>Array.from({length:count},(_,i)=>({date:new Date(Date.UTC(2025,0,1+i)).toISOString().slice(0,10),value}));
test('constant history is midpoint, not 100th percentile',()=>{
 const rows=daily(260,'10');assert.equal(valuationStats(rows,5,rows.at(-1).date).rank,50);
});
test('daily samples below 252 do not produce a rank',()=>{
 const rows=daily(251,'10');const s=valuationStats(rows,5,rows.at(-1).date);assert.equal(s.rank,null);assert.equal(s.count,251);
});
test('valuation negatives excluded; zero dividend retained',()=>{
 const rows=daily(260,0);assert.equal(valuationStats(rows,5,rows.at(-1).date).count,0);assert.equal(valuationStats(rows,5,rows.at(-1).date,true).rank,50);
 rows[0].value=-1;assert.equal(valuationStats(rows,5,rows.at(-1).date,true).count,259);
});
test('as-of truncates future observations and quantiles',()=>{
 const rows=daily(260,10);rows.at(-1).value=1000;const s=valuationStats(rows,5,rows.at(-2).date);assert.equal(s.max,10);assert.equal(s.rank,50);assert.equal(s.latest.date,rows.at(-2).date);
});
test('latest missing value never silently carries prior value',()=>{
 const rows=daily(260,10);rows.at(-1).value=null;assert.equal(valuationStats(rows,5,rows.at(-1).date).rank,null);
});
test('anniversary clamps leap day and observations deduplicate',()=>{
 const rows=[{date:'2023-02-27',value:1},{date:'2023-02-28',value:2},{date:'2023-02-28',value:3},{date:'2024-02-29',value:4}];
 const s=valuationWindow(rows,1,'2024-02-29');assert.equal(s.length,2);assert.equal(s[0].date,'2023-02-28');assert.equal(s[0].value,3);
});
test('monthly and quarterly minimum samples are respected',()=>{
 const rows=Array.from({length:36},(_,i)=>({date:new Date(Date.UTC(2020,i,1)).toISOString().slice(0,10),value:10}));assert.equal(valuationStats(rows,5,rows.at(-1).date).rank,50);assert.equal(valuationStats(rows.slice(1),5,rows.at(-1).date).rank,null);
});

test('display sampling keeps actual dates, last null, and calendar week across year end',()=>{
 const rows=[{date:'2025-12-31',value:10},{date:'2026-01-02',value:null},{date:'2026-01-05',value:12},{date:'2026-01-30',value:13}];
 const week=scope.exports.valuationSample(rows,'week');
 assert.equal(week.length,3);assert.equal(week[0].date,'2026-01-02');assert.equal(week[0].value,null);
 const month=scope.exports.valuationSample(rows,'month');assert.equal(month.length,2);assert.equal(month[1].date,'2026-01-30');
 assert.equal(scope.exports.valuationSample(rows,'observation').length,4);
});
