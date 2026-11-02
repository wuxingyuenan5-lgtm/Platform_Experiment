const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const dir = path.resolve(__dirname, '../src/views/hedgeBoard/aShare/components/etfObservation');

function mount() {
  const nodes = new Map();
  function node(id) {
    if (nodes.has(id)) return nodes.get(id);
    const value = {id, style:{}, events:{}, textContent:'', innerHTML:'', clientHeight:420,
      addEventListener(type, fn) { this.events[type] = fn; },
      removeEventListener(type) { delete this.events[type]; },
      appendChild(child) { (this.children ||= []).push(child); },
      getBoundingClientRect: () => ({left:0, top:0}),
      parentNode:{style:{},children:[],appendChild(child){this.children.push(child);}, getBoundingClientRect:()=>({left:0,top:0})},
    };
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
  const root = {querySelector:selector=>node(selector.match(/id="([^"]+)"/)[1]),
    querySelectorAll:()=>[...charts.keys()].map(node),addEventListener(){},removeEventListener(){}};
  const exports={};
  const code=ts.transpileModule(fs.readFileSync(path.join(dir,'renderer.js'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(code,{exports,require:name=>name.includes('echarts/components')?{}:{default:engine},
    window,document:{createElement:()=>node('created-'+(++timer))},
    ResizeObserver:class {observe(){} disconnect(){}},Date,Promise,Number,Math,console});
  const data={initData:{date:'2026-10-30',times:['09:31','09:32'],bars:[1,2],closes:[3000,3001],table:[]},
    cumData:{prevDate:'2026-10-30',prev:[1,2],avg20:[1,2],avgDays:20},
    cmpData:{support:[{date:'2026-10-29',amount:2,netflow:101}],today:{date:'2026-10-30',amount:3},latest:{date:'2026-10-30',amount:3,netflow:1}},
    dailyData:{dates:['2026-10-29','2026-10-30'],amount:[2,3],netflow:[101,1],idx:[3000,3001]},
    typData:{slots:['09:45'],supAmt:[2],supIdx:[1],norAmt:[1],norIdx:[0]},
    broadData:{dates:['2026-10-29','2026-10-30'],cats:['沪深300'],colors:['#123456'],series:{'沪深300':[1,-1]},total:[1,-1],totalCum:[1,0]}};
  const dispose=exports.mountEtfObservation(root,data,()=>new Promise(()=>{}));
  return {charts,nodes,timers,listeners,dispose};
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
test('pause and resume are scoped to this ETF board', () => {
  const state=mount(), button=state.nodes.get('btnPause');
  button.events.click.call(button);
  assert.equal(button.textContent,'恢复自动刷新');
  button.events.click.call(button);
  assert.equal(button.textContent,'暂停自动刷新');
  state.dispose();
});

