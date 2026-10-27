const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const vue = require('vue');
const {parse,compileScript} = require('@vue/compiler-sfc');
const loader = require('./load-strategy-module.cjs')();
const Boundary = loader('src/views/hedgeBoard/components/WidgetErrorBoundary.ts').default;

function mount(data, view, brokenTheme = false) {
  const file = 'src/views/hedgeBoard/components/EquityObservatoryPanel.vue';
  const descriptor = parse(fs.readFileSync(file,'utf8')).descriptor;
  const script = compileScript(descriptor,{id:'failure-isolation',inlineTemplate:true}).content;
  const code = ts.transpileModule(script,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
  const mod={exports:{}};
  const stub = (name, broken=false) => ({name,setup:()=>()=>{if(broken && brokenTheme)throw Error('injected chart failure');return vue.h('div',name);}});
  new Function('require','module','exports','window','document',code)((name)=> {
    if(name==='vue')return vue;
    if(name.includes('api/equityObservatory'))return {getEquityObservatory:async()=>data};
    if(name.includes('researchWorkspace'))return {useResearchSnapshots:()=>({get:()=>data,set(){}}),useResearchViewState:(_,x)=>vue.ref(x)};
    if(name.includes('WidgetErrorBoundary'))return {__esModule:true,default:Boundary};
    return {__esModule:true,default:stub(name.split('/').pop(),name.includes('EquityThemePanel')&&brokenTheme)};
  },mod,mod.exports,{setInterval:()=>1,clearInterval(){}},{hidden:false});
  const renderer=vue.createRenderer({
    createElement:type=>({type,children:[],parent:null}),createText:text=>({type:'text',text}),createComment:()=>({type:'comment'}),
    setText:(n,t)=>n.text=t,setElementText:(n,t)=>{n.text=t;n.children=[];},patchProp(){},
    insert(n,p,a){if(n.parent){const i=n.parent.children.indexOf(n);if(i>=0)n.parent.children.splice(i,1);}n.parent=p;const i=a?p.children.indexOf(a):-1;if(i>=0)p.children.splice(i,0,n);else p.children.push(n);},
    remove(n){const i=n.parent?.children.indexOf(n);if(i>=0)n.parent.children.splice(i,1);},parentNode:n=>n.parent,nextSibling:n=>{const a=n.parent?.children||[];return a[a.indexOf(n)+1]||null;}
  });
  const root={children:[]};const app=renderer.createApp(mod.exports.default,{market:'us',view});
  app.config.warnHandler=()=>{};app.mount(root);
  function text(n){return (n.text||'')+(n.children||[]).map(text).join(' ');}
  return {text:()=>text(root),recover:()=>{brokenTheme=false;data.generatedAt='next';},close:()=>app.unmount()};
}
const partial={market:'us',status:'partial',date:'2026-10-26',themes:null,valuationCharts:[{id:'SPX'}],structure:null,participation:[{period:20,value:50,count:5,expected:11}],ratios:[],sources:[]};
test('valuation renders when themes are absent',async()=>{
  const s=mount(partial,'valuation');await vue.nextTick();assert.match(s.text(),/IndexValuationPanel/);s.close();
});
test('structure renders when themes are absent',async()=>{
  const s=mount(partial,'structure');await vue.nextTick();assert.match(s.text(),/行业ETF站上20日均线/);s.close();
});
test('one throwing theme component leaves valuation and structure mounted',async()=>{
  const s=mount({...partial,themes:{date:'2026-10-26',items:[]}},undefined,true);
  await vue.nextTick();await vue.nextTick();assert.match(s.text(),/主题与行业.*暂不可用/);assert.match(s.text(),/IndexValuationPanel/);assert.match(s.text(),/行业ETF站上20日均线/);s.close();
});

test('a new published theme snapshot recovers a previously failed subtree',async()=>{
 const data=vue.reactive({...partial,themes:{date:'2026-10-26',items:[]},generatedAt:'first'});
 const s=mount(data,undefined,true);await vue.nextTick();await vue.nextTick();
 assert.match(s.text(),/主题与行业.*暂不可用/);
 s.recover();await vue.nextTick();await vue.nextTick();
 assert.match(s.text(),/EquityThemePanel/);assert.doesNotMatch(s.text(),/主题与行业.*暂不可用/);s.close();
});
