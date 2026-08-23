const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(
  path.join(
    root,
    'src/views/strategy/spread-carry/composables/useCrossSpreadExecution.ts',
  ),
  'utf8',
);
const terminalHelper = source.slice(
  source.indexOf('function isTerminalBatchStatus'),
  source.indexOf('export function useCrossSpreadExecution'),
);

assert.match(source, /type PersistedExecutionDraft =[\s\S]*kind: 'OPEN'/);
assert.match(source, /type PersistedExecutionDraft =[\s\S]*kind: 'CLOSE'/);
assert.match(source, /type PersistedExecutionDraft =[\s\S]*kind: 'CLOSE_ALL'/);
assert.match(source, /const PENDING_EXECUTION_STORAGE_KEY = 'vg\.crossSpread\.pendingExecution'/);
assert.match(terminalHelper, /function isTerminalBatchStatus\(status: string \| null \| undefined\)/);
assert.match(terminalHelper, /status === 'hedged' \|\| status === 'completed' \|\| status === 'failed'/);
assert.doesNotMatch(terminalHelper, /status === 'manual_intervention'/);
assert.doesNotMatch(terminalHelper, /status === 'result_unknown'/);
assert.match(source, /persistDraft\(draft\);[\s\S]*openCrossSpreadMarket\(\{\s*idempotencyKey: draft\.idempotencyKey/);
assert.match(source, /persistDraft\(draft\);[\s\S]*closeCrossSpreadMarket\(action\.planId,\s*\{\s*idempotencyKey: draft\.idempotencyKey/);
assert.match(source, /plans: closablePlans\.map\(\(plan\) => \(\{\s*planId: plan\.planId,\s*idempotencyKey: crypto\.randomUUID\(\)/);
assert.match(source, /for \(const planDraft of draft\.plans\) \{[\s\S]*idempotencyKey: planDraft\.idempotencyKey/);
assert.match(source, /if \(isTerminalBatchStatus\(result\.executionBatch\.status\)\) \{\s*clearDraft\(\);/);
assert.match(source, /if \(allTerminal\) \{\s*clearDraft\(\);/);

console.log('cross-spread execution recovery checks passed');
