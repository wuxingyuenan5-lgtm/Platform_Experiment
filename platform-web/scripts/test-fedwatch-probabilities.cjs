'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const test=require('node:test');
const vm=require('node:vm');
const ts=require('typescript');
const source=fs.readFileSync(path.join(__dirname,'../src/views/hedgeBoard/components/FedWatchPanel.vue'),'utf8');
const script=source.split('<script setup lang="ts">')[1].split('</script>')[0];
const declarations=ts.createSourceFile('panel.ts',script,ts.ScriptTarget.Latest,true).statements.filter(s=>ts.isFunctionDeclaration(s)&&['formatProbability','formatPct','normalizeProbability'].includes(s.name?.text)).map(s=>s.getText()).join('\n');
const code=ts.transpileModule(declarations,{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText;
const context=vm.createContext({});vm.runInContext(code,context);
test('percent probabilities below one are never inflated as fractions',()=>{
 for(const [value,label] of [[0,'0.00%'],[0.5,'0.50%'],[1,'1.00%'],[2.46,'2.46%'],[97.54,'97.54%'],[100,'100.00%']]){
  assert.equal(context.formatProbability(value),label);assert.equal(context.formatPct(value),label);
 }
 assert.equal(context.formatProbability(undefined),'0.00%');
});
