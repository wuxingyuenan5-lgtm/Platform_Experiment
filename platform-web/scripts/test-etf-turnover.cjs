const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const base=path.resolve(__dirname,'../src/views/hedgeBoard/aShare/components/etfTurnover');

function fixture(){
 const items=Array.from({length:24},(_,i)=>({code:String(510300+i),tcode:'sh'+(510300+i),name:'ETF'+String(i).padStart(2,'0'),index:'沪深300',group:i<20?'core':'watch',huijin_yi:24-i,amount_yi:i+1,avg20_yi:20,mktcap_yi:100,pct:1,outer_lots:200,inner_lots:100,shares_yi:50,date:'20261105',ts:'20261105110000',shape:[['09:35',0.1],['11:30',0.5],['15:00',1]],hist:[{date:'2026-11-03',amount_yi:2}],subscr_net_yi:null}));
 const history={};for(let i=0;i<100;i++){const d=new Date(Date.UTC(2026,6,1+i)).toISOString().slice(0,10).replaceAll('-','');history[d]=Object.fromEntries(items.slice(0,20).map(x=>[x.code,50+i]));}
 return {data:{generated_at:'2026-11-04 17:20:17',trade_date:'20261104',items,shares_history:history},sources:{live:{status:'ready'},baseline:{status:'ready'}}};
}

function mount(){
 const nodes=new Map(),timers=new Map(),listeners=new Map(),rootEvents={};let timer=0,calls=0,chartRenders=0;
 function node(id){
  if(nodes.has(id))return nodes.get(id);
  const n={id,innerHTML:'',textContent:'',value:id==='sort'?'huijin':id==='scope'?'all':'',checked:true,style:{},events:{},className:'',children:[],classList:{add(){},remove(){}},
   addEventListener(t,fn){this.events[t]=fn;},getBoundingClientRect:()=>({width:800,left:0,top:0}),setAttribute(){},appendChild(c){this.children.push(c);},scrollIntoView(){this.scrolled=true;},
   querySelector:s=>node(id+s),querySelectorAll:()=>[],getAttribute:k=>k==='data-target'?(id==='rngDelta'?'delta':'index'):null};
  if(id==='mgrid')n.children=[0,1,2,3].map(i=>({querySelector:()=>node('metric'+i)}));
  if(id==='rngDelta'||id==='rngIndex')n.querySelectorAll=()=>[60,120,242].map(range=>{const b=node(id+range);b.getAttribute=()=>String(range);return b;});
  nodes.set(id,n);return n;
 }
 const root={querySelector:s=>node(s.match(/id="([^"]+)"/)[1]),querySelectorAll:()=>[node('svg1'),node('svg2')],addEventListener(t,fn){rootEvents[t]=fn;},removeEventListener(t){delete rootEvents[t];}};
 const window={setTimeout(fn){timers.set(++timer,fn);return timer;},clearTimeout(id){timers.delete(id);}};
 const document={hidden:false,addEventListener(t,f){listeners.set(t,f);},removeEventListener(t){listeners.delete(t);}};
 class Clock extends Date{constructor(...args){super(...(args.length?args:['2026-11-05T11:00:00+08:00']));}}
 const exports={};const code=ts.transpileModule(fs.readFileSync(path.join(base,'renderer.js'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 vm.runInNewContext(code,{exports,window,document,Date:Clock,Intl,console,ResizeObserver:class{observe(){}disconnect(){}}});
 const initial=fixture();let next=structuredClone(initial),failure=false;
 const dispose=exports.mountEtfTurnover(root,initial,async()=>{calls++;if(failure)throw Error('offline');return next;},{onCharts(){chartRenders++;}});
 return {nodes,timers,listeners,rootEvents,dispose,document,initial,setNext(v){next=v;},fail(){failure=true;},get calls(){return calls;},get chartRenders(){return chartRenders;}};
}

test('reference group filters, search and ordering retain all 24 original members',()=>{
 const s=mount(),body=s.nodes.get('tbody');
 assert.equal((body.innerHTML.match(/class="code num"/g)||[]).length,24);
 s.nodes.get('scope').value='watch';s.nodes.get('scope').events.change();
 assert.equal((body.innerHTML.match(/class="code num"/g)||[]).length,4);
 assert.ok(!body.innerHTML.includes('ETF00'));
 s.nodes.get('q').value='ETF22';s.nodes.get('q').events.input();
 assert.equal((body.innerHTML.match(/class="code num"/g)||[]).length,1);
 s.nodes.get('scope').value='all';s.nodes.get('q').value='';s.nodes.get('sort').value='amount';s.nodes.get('sort').events.change();
 assert.ok(body.innerHTML.indexOf('ETF19')<body.innerHTML.indexOf('ETF00'));
 assert.ok(body.innerHTML.indexOf('ETF23')<body.innerHTML.indexOf('ETF20'));
 assert.ok(s.nodes.get('chartDelta').innerHTML.includes('<svg'));
 assert.ok(s.nodes.get('chartIndex').innerHTML.includes('<svg'));
 const old=s.nodes.get('chartDeltaNote').innerHTML;
 s.nodes.get('rngDelta60').events.click.call(s.nodes.get('rngDelta60'));
 assert.notEqual(s.nodes.get('chartDeltaNote').innerHTML,old);
 assert.ok(s.nodes.get('chartDeltaNote').innerHTML.includes('60 个交易日'));
 let prevented=false;s.rootEvents.click({target:{closest:()=>({})},preventDefault(){prevented=true;}});
 assert.equal(prevented,true);assert.equal(s.nodes.get('notes').scrolled,true);
 s.dispose();assert.equal(s.timers.size,0);assert.equal(s.listeners.size,0);
 assert.equal(Object.keys(s.rootEvents).length,0);
});

test('refresh reads local snapshots, retains charts for unchanged history and cleans paused work',async()=>{
 const s=mount(),before=s.chartRenders;
 const next=fixture();next.data.items[0].amount_yi=999;
 s.setNext(next);await s.nodes.get('refresh').events.click();
 assert.ok(s.nodes.get('tbody').innerHTML.includes('999.00'));
 assert.equal(s.chartRenders,before);
 assert.equal(s.calls,1);
 s.fail();await s.nodes.get('refresh').events.click();
 assert.ok(s.nodes.get('tbody').innerHTML.includes('999.00'));
 s.document.hidden=true;await s.nodes.get('refresh').events.click();assert.equal(s.calls,2);
 s.dispose.pause();assert.equal(s.timers.size,0);
 await s.nodes.get('refresh').events.click();assert.equal(s.calls,2);
 s.dispose();assert.equal(s.listeners.size,0);
});
