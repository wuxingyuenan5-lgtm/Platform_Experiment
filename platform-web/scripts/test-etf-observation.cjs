const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const dir = path.resolve(__dirname, '../src/views/hedgeBoard/aShare/components/etfObservation');

function mount(options={}) {
  class FixtureDate extends Date {
    constructor(...args) { super(...(args.length ? args : (options.now || [2026, 10, 4, 14, 0, 0]))); }
    static now() { return new Date(...(options.now || [2026, 10, 4, 14, 0, 0])).getTime(); }
  }
  const nodes = new Map();
  function node(id) {
    if (nodes.has(id)) return nodes.get(id);
    const value = {id, style:{}, events:{}, textContent:'', innerHTML:'', clientHeight:420, clientWidth:800, parentElement:null,
      closest(selector) { return selector === '#' + id ? this : null; },
      addEventListener(type, fn) { this.events[type] = fn; },
      removeEventListener(type) { delete this.events[type]; },
      appendChild(child) { (this.children ||= []).push(child); },
      getBoundingClientRect: () => ({left:0, top:0}),
      parentNode:{style:{},children:[],appendChild(child){this.children.push(child);}, getBoundingClientRect:()=>({left:0,top:0})},
    };
    if ((options.hidden||[]).includes(id)) value.parentElement={tagName:'DETAILS',open:false,parentElement:null};
    nodes.set(id, value); return value;
  }
  const charts = new Map();
  const engine = {use(){}, init(el){ const chart={option:{},setOption(option){this.option=option;},getOption(){return {...this.option,xAxis:[this.option.xAxis]};},
    resize(){},dispose(){this.disposed=true;},convertFromPixel: (_, point) => point}; charts.set(el.id,chart);return chart;},
    getInstanceByDom: el => charts.get(el.id)};
  const timers = new Map(), listeners = new Map(); let timer = 0;
  const window = {setInterval(fn){timers.set(++timer,fn);return timer;},setTimeout(fn){timers.set(++timer,fn);return timer;},
    clearInterval(id){timers.delete(id);},clearTimeout(id){timers.delete(id);},
    addEventListener(type,fn){const rows=listeners.get(type)||[];rows.push(fn);listeners.set(type,rows);},
    removeEventListener(type,fn){listeners.set(type,(listeners.get(type)||[]).filter(item=>item!==fn));}};
  const rootEvents={};
  const root = {querySelector:selector=>{ const id=selector.match(/id="([^"]+)"/)[1];return (options.absent||[]).includes(id)?null:node(id); },
    querySelectorAll:()=>[...charts.keys()].map(node),addEventListener(type,fn){rootEvents[type]=fn;},removeEventListener(type){delete rootEvents[type];}};
  const exports={};
  const code=ts.transpileModule(fs.readFileSync(path.join(dir,'renderer.js'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(code,{exports,require:name=>name.includes('echarts/components')?{}:{default:engine},
    window,document:{createElement:()=>node('created-'+(++timer))},
    ResizeObserver:class {observe(){} disconnect(){}},Date:FixtureDate,Promise,Number,Math,console});
  const data={initData:{indexSymbol:'sh000300',date:'2026-10-30',times:['09:31','09:32'],bars:[1,2],closes:[3000,3001],table:[{'code': '510310', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '588000', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159915', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '510300', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '563360', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159352', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '512100', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159338', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '510500', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159949', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '588080', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '510050', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '510210', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159845', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159952', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159361', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '512050', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159633', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '560010', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159919', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '510330', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '510180', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '512500', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159629', 'name': 'fixture', 'amount': 1, 'pct': 0}, {'code': '159977', 'name': 'fixture', 'amount': 1, 'pct': 0}]},
    cumData:{intervalMinutes:5,slots:['09:30','09:35'],avg5:[0,3],avg5Days:5,avg20:[0,2],avgDays:20},
    cmpData:{support:[{date:'2026-10-29',amount:2,netflow:101}],today:{date:'2026-10-30',amount:3},latest:{date:'2026-10-30',amount:3,netflow:1}},
    dailyData:{dates:['2026-10-29','2026-10-30'],amount:[2,3],netflow:[101,1],idx:[3000,3001]},
    typData:{indexSymbol:'sh000300',slots:['09:45'],supAmt:[2],supIdx:[1],norAmt:[1],norIdx:[0]},
    broadData:{dates:['2026-10-29','2026-10-30'],cats:['沪深300'],colors:['#123456'],series:{'沪深300':[1,-1]},total:[1,-1],totalCum:[1,0]}};
  if (options.legacyIndex) { delete data.initData.indexSymbol; delete data.typData.indexSymbol; }
  if (options.cumData) data.cumData = options.cumData;
  const dispose=exports.mountEtfObservation(root,data,options.request||(()=>new Promise(()=>{})),options.rendererOptions);
  return {charts,nodes,timers,listeners,dispose,rootEvents};
}

test('all nine reference charts mount and all timers/listeners/instances dispose', () => {
  const state=mount();
  assert.equal(state.charts.size,9);
  assert.ok(state.timers.size>0);
  assert.equal(state.nodes.get('supportCount').textContent,'共1天');
  state.dispose();
  assert.equal(state.timers.size,0);
  assert.ok([...state.charts.values()].every(chart=>chart.disposed));
  assert.ok([...state.listeners.values()].every(rows=>rows.length===0));
});

test('an incomplete historical session keeps both mean legends and explains the unavailable windows', () => {
 const state=mount({cumData:{intervalMinutes:5,slots:['09:30','09:35'],avg5:[],avg5Days:0,avg20:[],avgDays:19,
   requestedDays:Array.from({length:20},(_,i)=>'day'+i),missingDays:['day19']}});
 const option=state.charts.get('chartCum').option;
 assert.deepEqual(Array.from(option.legend.data),['当日累计','近5日均值','近20日均值']);
 assert.ok(option.series[1].data.every(v=>v===null));
 assert.ok(option.series[2].data.every(v=>v===null));
 assert.match(option.title.subtext,/近5日均值待补齐（4\/5日完整）/);
 assert.match(option.title.subtext,/近20日均值待补齐（19\/20日完整）/);
 state.dispose();
});

test('the displayed prior session uses its complete original five-minute curve only on an exact date match', () => {
 const baseline={intervalMinutes:5,slots:['09:30','09:35'],prevDate:'2026-10-30',prev:[0,125],avg5:[0,3],avg5Days:5,avg20:[0,2],avgDays:20};
 const state=mount({cumData:baseline});
 const option=state.charts.get('chartCum').option;
 assert.equal(option.series[0].data[1],125);
 assert.match(option.title.subtext,/2026-10-30/);
 state.dispose();
 const mismatched=mount({cumData:{...baseline,prevDate:'2026-10-29'}});
 assert.notEqual(mismatched.charts.get('chartCum').option.series[0].data[1],125);
 mismatched.dispose();
});

test('unidentified legacy SSE prices are never relabelled as HS300', () => {
 const state=mount({legacyIndex:true});
 assert.equal(state.charts.has('chart'),false);
 assert.ok(state.charts.get('chartTypCase').option.series[1].data.every(value=>value===null));
 assert.ok(state.charts.get('chartTypNorm').option.series[1].data.every(value=>value===null));
 state.dispose();
});

test('intraday index axes show exactly two decimals without rounding source arrays', () => {
 const state=mount();
 assert.equal(state.charts.get('chart').option.yAxis[1].axisLabel.formatter(4101), '4101.00');
 assert.equal(state.charts.get('chart').option.yAxis[1].axisPointer.label.precision, 2);
 assert.equal(state.charts.get('chartTypCase').option.yAxis[1].axisLabel.formatter(-0.5), '-0.50');
 assert.equal(state.charts.get('chartTypNorm').option.yAxis[1].axisLabel.formatter(0), '0.00');
 state.dispose();
});
test('range selection sums bars and excludes the index line', () => {
  const state=mount(), el=state.nodes.get('chartDAmt');
  el.events.mousedown({button:0,clientX:0,clientY:100,preventDefault(){}});
  state.listeners.get('mousemove').forEach(fn=>fn({clientX:10,clientY:100}));
  state.listeners.get('mouseup').forEach(fn=>fn({clientX:10,clientY:100}));
  const tip=el.parentNode.children.find(child=>child.className==='brush-tip');
  assert.match(tip.textContent,/合计 5.0 亿元/);
  assert.doesNotMatch(tip.textContent,/6006/);
  state.dispose();
});
test('folded historical charts initialize only when opened and do not duplicate on reopening',()=>{
 const state=mount({hidden:['chartTypCase','chartTypNorm']});assert.equal(state.charts.has('chartTypCase'),false);
 state.nodes.get('chartTypCase').parentElement.open=true;
 state.rootEvents.toggle();assert.equal(state.charts.size,9);const chart=state.charts.get('chartTypCase');state.rootEvents.toggle();assert.equal(state.charts.get('chartTypCase'),chart);
 state.dispose();assert.equal(state.rootEvents.toggle,undefined);
});
test('daily-only view creates no intraday charts or polling timers',()=>{
 const state=mount({absent:['chart','chartCum','chartAmt','chartNf','chartTypCase','chartTypNorm']});
 assert.equal(state.charts.size,3);assert.equal(state.timers.size,0);state.dispose();
});


test('history-only support charts do not poll intraday data',()=>{
 const state=mount({absent:['chart','chartCum','chartDAmt','chartDNf','chartBroad','broadTable','chartTypCase','chartTypNorm'],rendererOptions:{live:false}});
 assert.equal(state.charts.size,2);assert.equal(state.timers.size,0);state.dispose();
});
test('table-only view renders broad flows without mounting any chart',()=>{
 const state=mount({absent:['chart','chartCum','chartAmt','chartNf','chartDAmt','chartDNf','chartBroad','chartTypCase','chartTypNorm']});
 assert.equal(state.charts.size,0);assert.equal(state.timers.size,0);assert.match(state.nodes.get('broadTable').innerHTML,/沪深300/);assert.match(state.nodes.get('broadTable').innerHTML,/-1.00/);state.dispose();
});


test('intraday auto-refresh continues without the removed status toolbar', async()=>{
 let close='3100', missing=false;
 const notices=[];
 const request=async path=>{
  if(path.startsWith('/api/kline')) return missing?[]:[{day:'2026-11-04 10:17:00',close,amount:'100000000'}];
  const codes=new URL(path,'http://localhost').searchParams.get('codes').split(',');
  return {data:{diff:codes.map(code=>({f12:code.slice(2),f14:code,f2:3000,f3:1,f6:100000000,f18:2990}))}};
 };
 const state=mount({request,absent:['tagDate','tagUpdate','tagCountdown','btnRefresh','btnPause'],rendererOptions:{onUpdateError:message=>notices.push(message)}});
 const refresh=[...state.timers.values()][0];
 refresh();await new Promise(resolve=>setImmediate(resolve));
 assert.ok(state.charts.get('chart').option.series[1].data.includes(3100));
 close='3200';refresh();await new Promise(resolve=>setImmediate(resolve));
 assert.ok(state.charts.get('chart').option.series[1].data.includes(3200));
 missing=true;refresh();await new Promise(resolve=>setImmediate(resolve));
 assert.match(notices.at(-1),/指数分时更新失败/);
 assert.ok(state.charts.get('chart').option.series[1].data.includes(3200));
 missing=false;refresh();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(notices.at(-1),'');
 state.dispose();assert.equal(state.timers.size,0);
});


test('the live basket includes the five additions and never sums a partial 24-fund minute', async()=>{
 let missing=false;
 const requested=new Set();
 const request=async path=>{
  const url=new URL(path,'http://localhost');
  if(url.pathname==='/api/kline') {
   const symbol=url.searchParams.get('symbol'); requested.add(symbol);
   return [{day:'2026-11-04 10:17:00',close:'3100',amount:missing&&symbol==='sz159977'?undefined:'100000000'}];
  }
  return {data:{diff:[]}};
 };
 const state=mount({request});
 const refresh=[...state.timers.values()][0];
 refresh();await new Promise(resolve=>setImmediate(resolve));
 assert.ok(['sh510330','sh510180','sh512500','sz159629','sz159977'].every(s=>requested.has(s)));
 assert.ok(requested.has('sh000300'));
 assert.ok(state.charts.get('chart').option.series[0].data.includes(25));
 missing=true;refresh();await new Promise(resolve=>setImmediate(resolve));
 assert.ok(!state.charts.get('chart').option.series[0].data.includes(24));
 assert.ok(!state.charts.get('chart').option.series[0].data.includes(25));
 state.dispose();
});


test('closing auction retains original close and amount while absent minutes stay null', async()=>{
 const request=async path=>{
  const url=new URL(path,'http://localhost');
  if(url.pathname==='/api/kline') {
   const index=url.searchParams.get('symbol')==='sh000300';
   const slots=index?['14:57','14:58','15:00']:['14:57','15:00'];
   return slots.map(t=>({day:'2026-11-04 '+t+':00',close:t==='15:00'?'3686.173':'3681.949',amount:t==='15:00'?'200000000':'100000000'}));
  }
  return {data:{diff:[]}};
 };
 const state=mount({request}); [...state.timers.values()][0]();await new Promise(resolve=>setImmediate(resolve));
 const option=state.charts.get('chart').option;
 const index=t=>option.xAxis.data.indexOf(t);
 assert.equal(option.series[0].data[index('14:58')],null);
 assert.equal(option.series[0].data[index('14:59')],null);
 assert.equal(option.series[0].data[index('15:00')],50);
 assert.equal(option.series[1].data[index('15:00')],3686.173);
 assert.equal(state.charts.get('chartCum').option.series[0].data.at(-1),75);
 state.dispose();
});

test('minute turnover keeps original precision before cumulative summation', async()=>{
 const request=async path=>path.startsWith('/api/kline')?['09:31','09:32','09:33','09:34','09:35'].map(t=>({day:'2026-11-04 '+t+':00',close:'3100',amount:'19600'})):{data:{diff:[]}};
 const state=mount({request}); [...state.timers.values()][0]();await new Promise(resolve=>setImmediate(resolve));
 const option=state.charts.get('chart').option;
 assert.equal(option.series[0].data[option.xAxis.data.indexOf('09:31')],0.0049);
 const cum=state.charts.get('chartCum').option;
 assert.equal(cum.series[0].data[cum.xAxis.data.indexOf('09:35')],0.02);
 assert.equal(cum.xAxis.data.length,49);
 assert.ok(cum.xAxis.data.every(time=>Number(time.slice(3))%5===0));
 assert.deepEqual(Array.from(cum.legend.data),['当日累计','近5日均值','近20日均值']);
 assert.equal(cum.series[1].data[1],3);
 assert.equal(cum.series[2].data[1],2);
 state.dispose();
});

test('before opening retains the last dated session and switches when new minutes arrive', async()=>{
 let day='2026-11-04';
 const request=async path=>path.startsWith('/api/kline')?['09:31','09:32','09:33','09:34','09:35'].map(t=>({day:day+' '+t+':00',close:'3100',amount:day==='2026-11-04'?'100000000':'200000000'})):{data:{diff:[]}};
 const state=mount({request,now:[2026,10,5,9,12,0]});
 const refresh=[...state.timers.values()][0];
 refresh();await new Promise(resolve=>setImmediate(resolve));
 let option=state.charts.get('chartCum').option;
 assert.deepEqual(Array.from(option.legend.data),['当日累计','近5日均值','近20日均值']);
 assert.equal(option.series[0].data[1],125);
 assert.match(option.title.subtext,/2026-11-04/);
 day='2026-11-05';refresh();await new Promise(resolve=>setImmediate(resolve));
 option=state.charts.get('chartCum').option;
 assert.equal(option.series[0].data[1],250);
 assert.match(option.title.subtext,/2026-11-05/);
 assert.equal(option.series.length,3);
 state.dispose();
});

test('an internal minute gap explains the truncated curve and a complete refresh restores the 15:00 total', async()=>{
 let repaired=false;
 const times=[];
 for(const [start,end] of [[571,690],[781,900]]) for(let t=start;t<=end;t++) times.push(`${String(Math.floor(t/60)).padStart(2,'0')}:${String(t%60).padStart(2,'0')}`);
 const request=async path=>{
  const url=new URL(path,'http://localhost');
  if(url.pathname!=='/api/kline') return {data:{diff:[]}};
  const symbol=url.searchParams.get('symbol');
  return times.filter(t=>repaired || symbol!=='sh512050' || t!=='11:03').map(t=>({day:'2026-11-06 '+t+':00',close:'3100',amount:symbol==='sh512050'&&t==='11:03'?'0':'100000000'}));
 };
 const state=mount({request,now:[2026,10,6,15,30,0]});
 const refresh=[...state.timers.values()][0];refresh();await new Promise(resolve=>setImmediate(resolve));
 let option=state.charts.get('chartCum').option;
 assert.match(option.title.subtext,/11:03.*等待补齐/);
 assert.equal(option.series[0].data.at(-1),null);
 repaired=true;refresh();await new Promise(resolve=>setImmediate(resolve));
 option=state.charts.get('chartCum').option;
 assert.equal(option.series[0].data.at(-1),5999);
 assert.ok(!/等待补齐/.test(option.title.subtext));
 assert.deepEqual(Array.from(option.legend.data),['当日累计','近5日均值','近20日均值']);
 state.dispose();
});
