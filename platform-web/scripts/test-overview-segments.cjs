const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../src/views/hedgeBoard/aShare/components/overviewSegments.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const output = { exports: {} };
vm.runInNewContext(`(function(exports){${compiled}\n})`, {})(output.exports);
const { overviewSegments } = output.exports;

test('missing observations break the navigator path without creating midpoint values', () => {
  assert.equal(JSON.stringify(overviewSegments([0, 2, null, undefined, 1, 0])), JSON.stringify(['0.00,18.00 20.00,2.00', '80.00,10.00 100.00,18.00']));
  assert.equal(overviewSegments([null, undefined, NaN]).length, 0);
  assert.equal(JSON.stringify(overviewSegments([0, 0])), JSON.stringify(['0.00,10.00 100.00,10.00']));
});
