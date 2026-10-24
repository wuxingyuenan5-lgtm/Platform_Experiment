const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');
const source = fs.readFileSync(path.join(__dirname, '../src/views/hedgeBoard/aShare/components/etfTrackingModel.ts'), 'utf8');
const output = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const mod = {exports:{}};
new vm.Script(`(function(require,module,exports){${output}\n})`).runInThisContext()(require,mod,mod.exports);
const {trailingSummary,total,alignDates,balanceChange} = mod.exports;
test('weekly return includes all five sessions and uses preceding close', () => {
 const rows = [100,101,102,103,104,110].map((price,i) => ({date:`2026-10-${String(i+9).padStart(2,'0')}`, etf_qfq_close:price,etf_qfq_turnover_est_yi:2,flow_yi:-1}));
 const result = trailingSummary(rows,5);
 assert.ok(Math.abs(result.change-10)<1e-10);
 assert.equal(result.turnover,10); assert.equal(result.flow,-5);
 assert.equal(trailingSummary(rows,21).change,null);
 assert.equal(trailingSummary(rows,21).turnover,null);
});
test('missing financing session cannot become zero or complete period total', () => {
 const rows=[{date:'2026-10-15',balance:10,net:2},{date:'2026-10-16',balance:13,net:3}];
 assert.equal(total(alignDates(rows,['2026-10-16','2026-10-19']),'net'),null);
 assert.equal(balanceChange(rows,'2026-10-16','2026-10-19','balance'),null);
 assert.equal(balanceChange(rows,'2026-10-16','2026-10-16','balance'),3);
 assert.equal(total([{date:'a',net:0},{date:'b',net:0}],'net'),0);
});
