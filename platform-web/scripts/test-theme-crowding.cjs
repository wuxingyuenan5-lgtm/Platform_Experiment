const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const vue = require('vue');

test('theme and segment navigation keeps sparse shares and prices aligned', () => {
  const history = [
    {date:'2026-10-27',sharePct:null,shareMa5:null,price:'100'},
    {date:'2026-10-28',sharePct:'1.2',shareMa5:null,price:null},
  ];
  const props = vue.reactive({data:{items:[
    {name:'A',history,segments:[{name:'X',history:[{...history[1],sharePct:'0.2',price:'105'}]}]},
    {name:'B',history,segments:[]},
  ]}});
  const script = fs.readFileSync('src/views/hedgeBoard/components/ThemeCrowdingPanel.vue','utf8').match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1];
  const exports = {};
  const scope = vue.effectScope();
  const code = ts.transpileModule(script+'\nexports.state={active,segment,selected,chartSeries,lastPrice,latest,selectTheme};',{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  scope.run(()=>vm.runInNewContext(code,{exports,defineProps:()=>props,require:name=>name==='vue'?vue:name.includes('researchWorkspace')?{useResearchViewState:(_,v)=>vue.ref(v)}:{}}));
  const s=exports.state;
  try {
    assert.equal(s.active.value.name,'A');
    assert.equal(s.lastPrice.value.date,'2026-10-27');
    assert.equal(s.latest.value.date,'2026-10-28');
    assert.deepEqual(Array.from(s.chartSeries.value[0].values),[null,1.2]);
    assert.deepEqual(Array.from(s.chartSeries.value[2].values),[100,null]);
    s.segment.value='X';
    assert.equal(s.selected.value.name,'X');
    assert.equal(s.chartSeries.value[0].values[0],0.2);
    s.selectTheme('B');
    assert.equal(s.segment.value,'');
    assert.equal(s.selected.value.name,'B');
  } finally {scope.stop();}
});
