const test = require('node:test');
const assert = require('node:assert/strict');
const a = require('./load-strategy-module.cjs')()('src/views/hedgeBoard/charts/cycleAnalysis.ts');
const p = (date, value) => ({ date, value });
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} != ${expected}`);

test('seasonal distribution excludes unfinished months, absent baselines and stale month endpoints', () => {
 const input = [p('2023-12-29',100),p('2024-01-31',110),p('2024-02-29',110),p('2024-03-05',130),p('2024-04-30',140),p('2024-05-03',150)];
 const rows = a.monthlyDistributions(input,2024,2024);
 assert.equal(rows[0].n,1);close(rows[0].median,10);
 assert.equal(rows[1].win,0);assert.equal(rows[2].n,0);assert.equal(rows[3].n,0);assert.equal(rows[4].n,0);
 assert.equal(a.distribution([]).mean,null);
 assert.equal(a.quantile([0,10,20,30],.25),7.5);
});
test('drawdown identifies complete and right-censored episodes without using future recovery', () => {
 const input = [p('2024-01-01',100),p('2024-01-02',80),p('2024-01-03',90),p('2024-01-04',100),p('2024-01-05',110),p('2024-01-06',77)];
 const d = a.drawdownCycles(input,20);
 assert.equal(d.episodes.length,2);close(d.current,-30);
 assert.deepEqual(d.episodes.map(e=>[e.recovered,e.fallingDays,e.recoveryDays,e.underwaterDays]),[[true,1,2,3],[false,1,null,1]]);
 assert.equal(d.recoveryMedian,3);assert.equal(a.drawdownCycles(input,25).episodes.length,1);
 assert.equal(a.drawdownCycles([]).current,null);
 const missing = a.drawdownCycles([p('2024-01-01',100),p('2024-02-01',75),p('2024-02-02',100)],20);
 assert.equal(missing.recoveryMedian,null);assert.ok(missing.episodes[0].curve.some(p=>p.value===null));
});
test('economic regimes require consecutive months, retain zero boundaries and use signed changes', () => {
 const g=[p('2024-01-01',0),p('2024-02-01',1),p('2024-03-01',2),p('2024-04-01',3),p('2024-05-01',1)];
 const c=[p('2024-01-01',3),p('2024-02-01',2),p('2024-03-01',1),p('2024-04-01',0),p('2024-05-01',1)];
 assert.deepEqual(a.economicRegimes(g,c).map(r=>r.regime),[0,-1]);
 assert.equal(a.economicRegimes(g.filter(p=>p.date!=='2024-02-01'),c).length,0);
 assert.equal(a.driverRegimes(g,c)[0].regime,0);
});
test('conditional price returns require complete months and never substitute latest partial month', () => {
 const prices=[p('2023-12-29',100),p('2024-01-31',110),p('2024-02-29',121),p('2024-03-31',133.1),p('2024-04-30',146.41),p('2024-05-01',150)];
 close(a.monthReturn(prices,'2024-01',0),10);close(a.monthReturn(prices,'2024-01',3),33.1);
 assert.equal(a.monthReturn(prices,'2024-02',3),null);
 assert.equal(a.monthReturn(prices.filter(p=>p.date!=='2024-03-31'),'2024-01',3),null);
 const stats=a.conditionalReturns(prices,[{month:'2024-01',regime:0},{month:'2024-05',regime:0}],0);
 assert.equal(stats[0].n,1);close(stats[0].mean,10);assert.equal(stats[1].n,0);
});
test('policy event direction changes once per cycle and event returns retain expiry and data gaps', () => {
 const rates=Array.from({length:6},(_,i)=>p(`2024-01-0${i+1}`,[5,5,4.75,4.5,4.5,4.75][i]));
 const turns=a.policyTurns(rates);assert.deepEqual(turns.events.map(e=>[e.date,e.direction]),[['2024-01-03',-1],['2024-01-06',1]]);
 const prices=Array.from({length:34},(_,i)=>p(new Date(Date.UTC(2024,0,29+i)).toISOString().slice(0,10),100+i));
 close(a.eventReturn(prices,'2024-01-31',1),(131/101-1)*100);
 assert.equal(a.eventReturn(prices,'2024-01-31',3),null);
 assert.equal(a.eventReturn(prices.filter((_,i)=>i<5||i>20),'2024-01-31',1),null);
});
test('rotation ranks a fixed cohort at identical completed month endpoints and rejects missing legs', () => {
 const dates=['2023-12-29','2024-01-31','2024-02-29','2024-03-31','2024-04-02'];
 const inputs=[{id:'stock',observations:dates.map((d,i)=>p(d,100+i*10))},{id:'gold',observations:dates.map((d,i)=>p(d,100+i*5))}];
 const r=a.rotation(inputs,3);assert.equal(r.latest.month,'2024-03');assert.equal(r.latest.ranks[0].id,'stock');close(r.latest.ranks[0].value,30);
 assert.equal(a.rotation([...inputs,{id:'missing',observations:[]}],3).latest,undefined);
 assert.equal(a.rotation([{...inputs[0],observations:inputs[0].observations.filter(p=>p.date!=='2024-02-29')},inputs[1]],3).latest,undefined);
});
test('correlation uses common contiguous return intervals and requires the full window',()=>{
 const days=Array.from({length:65},(_,i)=>new Date(Date.UTC(2024,0,i+1)).toISOString().slice(0,10));
 const values=days.map((_,i)=>100*Math.exp(i*.01+Math.sin(i)*.03));
 const inputs=[{id:'a',observations:days.map((d,i)=>p(d,values[i]))},{id:'b',observations:days.map((d,i)=>p(d,values[i]*2))}];
 const r=a.correlationWindows(inputs);close(r.pairs[0].n20,1);close(r.pairs[0].n60,1);
 const short=inputs.map(s=>({...s,observations:s.observations.slice(-25)}));
 assert.equal(a.correlationWindows(short).pairs[0].n60,null);
 const gap=inputs.map(s=>({...s,observations:s.observations.filter((_,i)=>i<40||i>50)}));
 assert.equal(a.correlationWindows(gap).pairs[0].n20,null);
});
test('polling keeps chosen drawdown comparisons while changing threshold resets the cohort',async()=>{
 const fs=require('node:fs'),path=require('node:path'),ts=require('typescript'),vue=require('vue');
 const {parse,compileScript}=require('@vue/compiler-sfc');
 const file=path.resolve(__dirname,'../src/views/hedgeBoard/components/DrawdownCyclePanel.vue');
 const script=compileScript(parse(fs.readFileSync(file,'utf8')).descriptor,{id:'drawdown-poll'}).content;
 const code=ts.transpileModule(script,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const mod={exports:{}};
 new Function('require','module','exports',code)(name=>{
  if(name==='vue')return vue;
  if(name==='@/hooks/web/useECharts')return {useECharts:()=>({setOptions(){}})};
  if(name==='../charts/cycleAnalysis')return a;
  throw Error(name);
 },mod,mod.exports);
 const props=vue.reactive({observations:[p('2024-01-01',100),p('2024-01-02',80),p('2024-01-03',100),p('2024-01-04',70)]});
 const scope=vue.effectScope(),state=scope.run(()=>mod.exports.default.setup(props,{expose(){}}));
 try {
  await vue.nextTick();state.toggle('2024-01-03');
  assert.deepEqual(state.selected.value,['2024-01-01']);
  props.observations=[...props.observations,p('2024-01-05',75)];await vue.nextTick();
  assert.deepEqual(state.selected.value,['2024-01-01']);
  state.threshold.value=30;await vue.nextTick();
  assert.deepEqual(state.selected.value,['2024-01-03']);
 } finally {scope.stop();}
});
