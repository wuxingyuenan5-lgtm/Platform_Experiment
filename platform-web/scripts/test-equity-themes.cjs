const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const vue = require('vue');
function setup(items) {
  const source = fs.readFileSync('src/views/hedgeBoard/components/EquityThemePanel.vue', 'utf8');
  const script = source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1];
  const exports = {};
  const scope = vue.effectScope();
  const code = ts.transpileModule(script + '\nexports.state={members, sorted, order, segment, search, industry, selectedStock, stock, selectTheme};', {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  scope.run(() => vm.runInNewContext(code, {exports, defineProps:()=>({market:'us',data:{items},industries:[]}), require:name=>name==='vue'?vue:name.includes('researchWorkspace')?{useResearchViewState:(_,v)=>vue.ref(v)}:{}}));
  return {...exports.state, close:()=>scope.stop()};
}
const row = (code, segment, industry='Tech') => ({code, name:code,segment,industry,history:[{date:'2026-10-23',value:12}]});
test('theme filters deduplicate symbols, preserve segments, and clear on theme navigation', () => {
  const s=setup([{name:'A',segments:['X','Y'],members:[row('ONE','X'),row('ONE','Y'),row('TWO','X','Other')]},{name:'B',segments:['Z'],members:[row('THREE','Z')]}]);
  try {
    assert.equal(s.members.value.length,2);
    assert.equal(s.members.value[0].segments.join(','),'X,Y');
    s.segment.value='Y'; assert.equal(s.members.value.length,1);
    s.search.value='two'; assert.equal(s.members.value.length,0);
    s.selectTheme('B'); assert.equal(s.search.value,''); assert.equal(s.segment.value,'');
    assert.equal(s.members.value[0].code,'THREE');
    s.selectedStock.value='THREE'; assert.equal(s.stock.value.history.length,1);
  } finally {s.close();}
});
test('ranking excludes insufficient coverage even when its observed return is highest', () => {
  const s=setup([{name:'partial',return20:100,return20Rankable:false,members:[]},{name:'valid-low',return20:1,return20Rankable:true,members:[]},{name:'valid-high',return20:3,return20Rankable:true,members:[]}]);
  try {s.order.value='return20'; assert.equal(s.sorted.value.map(r=>r.name).join(','),'valid-high,valid-low,partial');} finally {s.close();}
});
