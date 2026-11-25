const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const vue=require('vue');
const {parse,compileScript}=require('@vue/compiler-sfc');
const seasonal=require('./load-strategy-module.cjs')()('src/views/hedgeBoard/charts/seasonality.ts');

function mount(reader,asset='cn-hs300') {
 let refresh,unmount,options;
 const filename=path.resolve(__dirname,'../src/views/hedgeBoard/components/SeasonalityPanel.vue');
 const script=compileScript(parse(fs.readFileSync(filename,'utf8')).descriptor,{id:'monthly-market'}).content;
 const code=ts.transpileModule(script,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const mod={exports:{}};
 new Function('require','module','exports',code)(name=>{
  if(name==='vue')return {...vue,onBeforeUnmount:fn=>{unmount=fn;}};
  if(name==='@/api/seasonality')return {readSeasonalHistory:reader};
  if(name==='@/hooks/web/useECharts')return {useECharts:()=>({setOptions:o=>{options=o;}})};
  if(name==='../useDashboardRefresh')return {useDashboardRefresh:fn=>{refresh=fn;}};
  if(name==='../charts/seasonality')return seasonal;
  if(name.endsWith('.vue'))return {};
  throw Error(name);
 },mod,mod.exports);
 const scope=vue.effectScope();
 const state=scope.run(()=>mod.exports.default.setup(vue.reactive({asset}),{expose(){}}));
 return {state,refresh:()=>refresh(),get options(){return options;},close(){unmount();scope.stop();}};
}
const flush=async()=>{await vue.nextTick();await new Promise(setImmediate);};

test('selected market keeps native metadata and shares BTC monthly/annual calculations',async()=>{
 const observed=[];
 const doc={label:'沪深300',source:'东方财富指数日行情',status:'ready',observations:[{date:'2023-12-29',value:'100'},{date:'2024-01-31',value:'110'},{date:'2024-02-29',value:'121'}]};
 const panel=mount(async(asset,signal)=>{observed.push([asset,signal]);return doc;});
 try{
  await panel.refresh();
  assert.equal(observed[0][0],'cn-hs300');assert.equal(observed[0][1].aborted,false);
  assert.equal(panel.state.source.value.label,'沪深300');
  const row=panel.state.rows.value.find(r=>r.year===2024);
  assert.ok(Math.abs(row.months[0]-10)<1e-9);assert.ok(Math.abs(row.annual-21)<1e-9);
  panel.state.view.value='chart';await flush();
  assert.equal(panel.options.xAxis.data.length,366);
  assert.ok(panel.options.series.some(s=>s.name==='2024'));
  assert.equal(panel.state.loading.value,false);
 }finally{panel.close();}
});

test('switching away aborts the old asset request and cannot publish its late result',async()=>{
 let release,signal;
 const panel=mount((asset,s)=>{signal=s;return new Promise(resolve=>{release=resolve;});},'us-ndx');
 const reading=panel.refresh();panel.close();
 assert.equal(signal.aborted,true);
 release({label:'纳斯达克100指数',observations:[{date:'2026-11-04',value:100}]});await reading;
 assert.equal(panel.state.source.value,undefined);
});

test('average aligns short market closures without filling long gaps or future dates',async()=>{
 const panel=mount(async()=>({status:'ready',observations:[
  {date:'2022-12-30',value:100},
  {date:'2023-01-02',value:110},{date:'2023-01-06',value:120},
  {date:'2023-01-09',value:130},{date:'2023-01-20',value:140},
  {date:'2023-12-29',value:100},
  {date:'2024-01-02',value:120},{date:'2024-01-05',value:140},
  {date:'2024-01-08',value:150},{date:'2024-01-09',value:160},
 ]}));
 try {
  await panel.refresh();panel.state.view.value='chart';panel.state.average.value=true;await flush();
  const avg=panel.options.series.find(s=>s.name==='平均').data;
  const at=day=>avg[panel.options.xAxis.data.indexOf(day)];
  assert.ok(Math.abs(at('01-06')-30)<1e-9);
  assert.ok(Math.abs(at('01-07')-30)<1e-9);
  assert.equal(at('01-10'),null);
  assert.ok(Math.abs(at('01-20')-40)<1e-9);
 } finally {panel.close();}
});

test('CN annual chart connects a long holiday but breaks across a missing trading session', async()=>{
 const panel=mount(async()=>({status:'ready',tradingDates:[
  '2023-12-29','2024-09-27','2024-09-30','2024-10-08','2024-10-09','2024-10-10','2024-10-11',
 ],observations:[
  {date:'2023-12-29',value:100},{date:'2024-09-27',value:105},{date:'2024-09-30',value:110},
  {date:'2024-10-08',value:115},{date:'2024-10-09',value:null},
  {date:'2024-10-10',value:120},{date:'2024-10-11',value:125},
 ]}));
 try {
  await panel.refresh();panel.state.view.value='chart';panel.state.average.value=true;await flush();
  const year=panel.options.series.filter(s=>s.name==='2024');
  const average=panel.options.series.find(s=>s.name==='平均');
  const at=(s,day)=>s.data[panel.options.xAxis.data.indexOf(day)];
  const near=(actual,expected)=>assert.ok(Math.abs(actual-expected)<1e-9);
  assert.equal(year.length,2);
  near(at(year[0],'09-30'),10);near(at(year[0],'10-08'),15);
  assert.equal(at(year[0],'10-04'),null);
  assert.equal(at(year[0],'10-10'),null);near(at(year[1],'10-10'),20);
  near(at(average,'10-04'),10);
  assert.equal(at(average,'10-09'),null);
  assert.equal(at(average,'10-12'),null);
 } finally {panel.close();}
});
