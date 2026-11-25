const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const code = ts.transpileModule(fs.readFileSync(path.resolve(__dirname,
  '../src/views/hedgeBoard/aShare/components/researchFrameworkAnalysis.ts'), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
}).outputText;
const mod = { exports: {} };
new Function('require', 'module', 'exports', code)(require, mod, mod.exports);
const { financingSentiment, capitalComparison, crowdingChanges, numeric } = mod.exports;
const { weeklyResearch, researchBands, linearFit, pairedCapitalPoints } = mod.exports;

test('rank comparison aligns last trading session and Sunday to the same week without filling gaps', () => {
  const rows = mod.exports.alignedResearchRanks([
    {key:'trading', rows:[{date:'2026-10-30',rank:0},{date:'2026-11-06',rank:50,partial:true}]},
    {key:'reports', rows:[{date:'2026-11-01',rank:25},{date:'2026-11-15',rank:75}]},
  ]);
  assert.deepEqual(rows, [
    {date:'2026-11-01',trading:0,reports:25},
    {date:'2026-11-08',trading:null,reports:null},
    {date:'2026-11-15',trading:null,reports:75},
  ]);
});
test('relative coordinates use rank bands and allow values beyond 100 percent',()=>{
 const rows=[10,20,30,20,10,50].map((value,i)=>({date:String(i),value}));
 const result=researchBands(rows,3);
 const v=result.slice(-3).map(r=>r.rank);
 const mean=v.reduce((a,b)=>a+b,0)/3;
 const sd=Math.sqrt(v.reduce((a,b)=>a+(b-mean)**2,0)/3);
 assert.ok(Math.abs(result.at(-1).relative-((v.at(-1)-mean+sd)/(2*sd))*100)<1e-10);
 assert.ok(result.at(-1).relative>100);
});
test('weekly calendar distinguishes closed weeks from missing sessions',()=>{
 const rows=[{date:'2026-02-02',value:'1'},{date:'2026-02-03',value:'2'},{date:'2026-02-16',value:'4'}];
 const calendar=['2026-02-02','2026-02-03','2026-02-16','2026-02-17'];
 const result=weeklyResearch(rows,'sum','2026-02-22',calendar);
 assert.equal(result.length,2);
 assert.equal(result[0].value,'3');assert.equal(result[1].value,null,'missing known session remains null');
 assert.equal(weeklyResearch(rows,'sum','2026-02-22').length,3,'no calendar cannot certify closure');
});
test('weekly sum keeps fractional values and partial week does not enter rank',()=>{
 const result=weeklyResearch([{date:'2026-11-02',value:'0.1'},{date:'2026-11-03',value:'0.2'}],'sum','2026-11-05');
 assert.equal(result[0].value,'0.3');assert.equal(result[0].partial,true);
 assert.equal(researchBands(result,1)[0].rank,null);
});
test('rank bands need two windows and preserve zero variance',()=>{
 const result=researchBands(points(6,i=>[1,2,3,2,1,6][i]),3);
 assert.equal(result[1].rank,null);assert.equal(result[2].rank,100);
 assert.equal(result[3].relative,null);assert.ok(Math.abs(result[4].rank-100/3)<1e-10);
 assert.ok(result[5].relative>50);
 assert.equal(researchBands(points(6,()=>1),3).at(-1).relative,null);
});
test('fit needs paired observations and rejects constant inputs',()=>{
 const rows=Array.from({length:20},(_,i)=>({x:i,y:3*i-7}));
 const fit=linearFit(rows);assert.equal(fit.slope,3);assert.equal(fit.intercept,-7);assert.equal(fit.r2,1);
 assert.equal(linearFit(rows.slice(0,19)),null);assert.equal(linearFit(rows.map(r=>({...r,x:1}))),null);
 const pairs=pairedCapitalPoints([{date:'2026-01-05',etf:'1',financing:'2'},{date:'2026-01-06',etf:'3',financing:'4'},{date:'2026-01-07',etf:'5',financing:'6'}],[{date:'2026-01-05',value:100},{date:'2026-01-07',value:110}]);
 assert.equal(pairs[2].marketReturn,null,'multi-day price return is not a daily return');
});
const date = i => new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10);
const points = (n, fn) => Array.from({length:n}, (_, i) => ({date:date(i),value:fn(i)}));
const series = rows => [{seriesId:'cn_margin_financing_buy',observations:rows}];
const capital = (balances, flows) => ({macro:{cn_margin_financing_balance:{observations:balances}},etf:{rows:flows}});

test('sentiment needs 60 inputs, uses sums rather than averages, percentile needs 252 values', () => {
  const result = financingSentiment(series(points(311, () => '100')));
  assert.equal(result[58].sentiment, null);
  assert.ok(Math.abs(result[59].sentiment - 100/3) < 1e-10);
  assert.equal(result[309].rank, null);
  assert.equal(result[310].rank, 100, 'empirical <= percentile includes all tied observations');
  const varying = financingSentiment(series(points(60, i => i < 40 ? '1' : '2')));
  assert.equal(varying.at(-1).sentiment, 50);
});
test('sentiment preserves zero, missing days, conflicting duplicates, and never compresses a gap', () => {
  const rows = points(65, () => 100);
  rows.splice(40,1);
  const completeCalendar = {seriesId:'cn_margin_total_balance',observations:points(65, () => 1000)};
  assert.equal(financingSentiment([...series(rows),completeCalendar]).at(-1).sentiment, null);
  const duplicated = points(60, () => 100);
  duplicated.push({date:date(20),value:200});
  assert.equal(financingSentiment(series(duplicated)).at(-1).sentiment, null);
  assert.equal(financingSentiment(series(points(60, () => 0))).at(-1).sentiment, null);
  assert.equal(financingSentiment(series(points(60, i => i >= 40 ? 0 : 1))).at(-1).sentiment, 0);
  assert.equal(numeric(null), null); assert.equal(numeric(''), null); assert.equal(numeric('  '), null);
});
test('same-window money totals preserve decimal precision and exclude starting balance day', () => {
  const result = capitalComparison(capital(
    points(6, i => ['0.1','0.2','0.3','0.4','0.5','0.6'][i]),
    points(6, () => '0.1'),
  ), 5);
  assert.equal(result.totalEtf, '0.5');
  assert.equal(result.totalFinancing, '0.5');
  assert.equal(result.start,date(1)); assert.equal(result.end,date(5));
  assert.equal(result.correlation,null);
  assert.equal(result.relationship,'ETF净申购 · 融资余额增加');
});
test('lagging source stays on latest union date with missing total, not a false common-date success', () => {
  const result = capitalComparison(capital(points(6,i=>i),points(5,()=>1)),5);
  assert.equal(result.end,date(5)); assert.equal(result.etfCount,4);
  assert.equal(result.totalEtf,null); assert.equal(result.totalFinancing,'5');
  assert.equal(result.relationship,'窗口数据不足');
  const gap = points(6,i=>i).filter(r=>r.date!==date(3));
  const incomplete = capitalComparison(capital(gap,points(6,()=>1)),5);
  assert.equal(incomplete.rows[3].financing,null);
  assert.equal(incomplete.rows[4].financing,null,'must not use a two-day balance jump as one-day change');
  assert.equal(incomplete.totalFinancing,null);
});
test('correlation requires 20 paired daily changes and nonconstant series', () => {
  const result = capitalComparison(capital(points(61,i=>i*i),points(61,i=>-(2*i-1))),60);
  assert.equal(result.pairs,60); assert.ok(Math.abs(result.correlation+1)<1e-12);
  assert.equal(result.relationship,'ETF净赎回 · 融资余额增加');
  assert.equal(capitalComparison(capital(points(61,i=>i),points(61,()=>0)),60).correlation,null);
  assert.equal(capitalComparison(capital([],[]),20).totalEtf,null);
});
test('industry changes use identical endpoints and never substitute an older valid value', () => {
  const items = [{code:'a',name:'A',history:points(21,i=>i).map(r=>({date:r.date,amount:r.value}))},
    {code:'b',name:'B',history:points(20,i=>i).map(r=>({date:r.date,amount:r.value}))}];
  const result = crowdingChanges(items,'amount',20);
  assert.equal(result.date,date(20)); assert.equal(result.baseDate,date(0));
  assert.equal(result.rows[0].value,20); assert.equal(result.rows[0].change,20);
  assert.equal(result.rows[1].value,null); assert.equal(result.rows[1].change,null);
  assert.equal(crowdingChanges(items,'turnover',20).rows[0].value,null);
  assert.equal(crowdingChanges(items,'amount',30).rows[0].change,null);
});
